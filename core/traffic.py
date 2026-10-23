#!/usr/bin/env python3
"""
XForwarder - Native Traffic Accounting & Bandwidth Monitoring Subsystem.
Zero-pip dependency standard library module (sqlite3, socket, subprocess, json, time, threading).

Features:
- Precision per-port traffic accounting across HAProxy, NFTables, and Nginx.
- Precision per-tunnel interface accounting (/proc/net/dev).
- Delta Engine: Immune to service reloads, server reboots, and counter resets.
- Pre-aggregated SQLite hourly rollups (traffic_hourly) in metrics.db.
- Fast analytical queries: 24h (Hourly), 7d/30d (Daily), 8w (Weekly), 12m (Monthly).
- Granular reset capability (billing cycle markers and optional historical wipe).
"""

import os
import sys
import time
import json
import socket
import sqlite3
import threading
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Set

DEFAULT_DB_DIR = "/etc/xforwarder"
LEGACY_DB_DIR = "/etc/forward-manager"
DB_FILENAME = "metrics.db"
TRAFFIC_RETENTION_DAYS = 90


def get_traffic_db_path() -> str:
    """Resolves the persistent SQLite database path for traffic metrics."""
    env_path = os.environ.get("XFWD_METRICS_PATH")
    if env_path:
        return env_path

    if os.path.exists(DEFAULT_DB_DIR) and os.path.isdir(DEFAULT_DB_DIR):
        return os.path.join(DEFAULT_DB_DIR, DB_FILENAME)
    if os.path.exists(LEGACY_DB_DIR) and os.path.isdir(LEGACY_DB_DIR):
        return os.path.join(LEGACY_DB_DIR, DB_FILENAME)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(base_dir, "config")
    if os.path.exists(config_dir):
        return os.path.join(config_dir, DB_FILENAME)

    return os.path.join(DEFAULT_DB_DIR, DB_FILENAME)


def init_traffic_db(db_path: Optional[str] = None) -> None:
    """Initializes the traffic tables and indices in SQLite with WAL mode."""
    path = db_path or get_traffic_db_path()
    db_dir = os.path.dirname(path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            pass

    try:
        conn = sqlite3.connect(path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")

            # Hourly aggregated traffic rollup table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traffic_hourly (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    period_start INTEGER NOT NULL,
                    rx_bytes INTEGER DEFAULT 0,
                    tx_bytes INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    PRIMARY KEY (entity_type, entity_id, period_start)
                );
            """)

            # Billing cycle reset markers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traffic_resets (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    reset_timestamp REAL NOT NULL,
                    reset_offset_rx INTEGER DEFAULT 0,
                    reset_offset_tx INTEGER DEFAULT 0,
                    PRIMARY KEY (entity_type, entity_id)
                );
            """)

            try:
                cursor.execute("ALTER TABLE traffic_resets ADD COLUMN reset_offset_rx INTEGER DEFAULT 0;")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE traffic_resets ADD COLUMN reset_offset_tx INTEGER DEFAULT 0;")
            except Exception:
                pass

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_period ON traffic_hourly(period_start);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_entity_lookup ON traffic_hourly(entity_type, entity_id, period_start);")
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] Failed to initialize traffic tables at {path}: {e}", file=sys.stderr)


def parse_proc_net_dev(content: str) -> Dict[str, Dict[str, int]]:
    """
    Parses /proc/net/dev content string into a dictionary of interface statistics.
    Returns: {iface_name: {'rx_bytes': int, 'tx_bytes': int, 'rx_packets': int, 'tx_packets': int}}
    """
    result = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        parts = line.split(":", 1)
        iface = parts[0].strip()
        data = parts[1].split()
        if len(data) >= 9:
            try:
                rx_bytes = int(data[0])
                rx_packets = int(data[1])
                tx_bytes = int(data[8])
                tx_packets = int(data[9]) if len(data) > 9 else 0
                result[iface] = {
                    "rx_bytes": rx_bytes,
                    "tx_bytes": tx_bytes,
                    "rx_packets": rx_packets,
                    "tx_packets": tx_packets,
                }
            except (ValueError, IndexError):
                continue
    return result


def read_proc_net_dev() -> Dict[str, Dict[str, int]]:
    """Reads interface statistics directly from /proc/net/dev (kernel virtual filesystem)."""
    if sys.platform == "win32" or not os.path.exists("/proc/net/dev"):
        return {}
    try:
        with open("/proc/net/dev", "r", encoding="utf-8", errors="replace") as f:
            return parse_proc_net_dev(f.read())
    except Exception:
        return {}


def classify_tunnel_type(iface_name: str) -> str:
    """
    Classifies a tunnel network interface name into its canonical protocol type:
    - 'gre': GRE tunnels (gre*, gretap*)
    - 'ipip': IPIP tunnels (ipip*, tunl*)
    - 'wireguard': WireGuard / AmneziaWG (awg*, wg*)
    - 'faketcp': FakeTCP streams (ftcp*)
    - '6to4': IPv6 over IPv4 tunnels (sit*, ip6tnl*, ip6gre*)
    - 'vxlan': Overlay networks (vxlan*, gnv*)
    - 'tunnel_other': Generic/custom tunnel interface
    """
    name = (iface_name or "").lower().strip()
    if name.startswith("gre"):
        return "gre"
    elif name.startswith("ipip") or name.startswith("tunl"):
        return "ipip"
    elif name.startswith("awg") or name.startswith("wg"):
        return "wireguard"
    elif name.startswith("ftcp") or name.startswith("tcp"):
        return "faketcp"
    elif name.startswith("sit") or name.startswith("ip6"):
        return "6to4"
    elif name.startswith("gnv") or name.startswith("vxlan"):
        return "vxlan"
    return "tunnel_other"


TUNNEL_TYPE_LABELS: Dict[str, str] = {
    "direct_ipv6": "Direct IPv6 Relay (HAProxy)",
    "tunnel_dnat": "Kernel Tunnel DNAT (NFTables)",
    "gre": "GRE Tunnel (gre*)",
    "ipip": "IPIP Tunnel (ipip*)",
    "wireguard": "WireGuard / AWG (awg*)",
    "faketcp": "FakeTCP Tunnel (ftcp*)",
    "6to4": "6to4 IPv6 Tunnel (sit*)",
    "vxlan": "VXLAN Overlay (vxlan*)",
    "tunnel_other": "Other Tunnel Interfaces"
}


def parse_haproxy_stats_csv(csv_text: str) -> Dict[int, Dict[str, int]]:
    """
    Parses HAProxy CSV output from 'show stat' command.
    Looks for listen blocks named 'fwd_<port>' and extracts bin (Bytes In) and bout (Bytes Out).
    In HAProxy perspective:
    - bin (bytes in) = data uploaded by client to HAProxy (RX)
    - bout (bytes out) = data downloaded by client from HAProxy (TX)
    Returns: {port: {'rx_bytes': int, 'tx_bytes': int}}
    """
    port_stats: Dict[int, Dict[str, int]] = {}
    lines = csv_text.strip().splitlines()
    if not lines:
        return port_stats

    header = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            header = [h.strip() for h in line.lstrip("#").split(",")]
            continue

        parts = [p.strip() for p in line.split(",")]
        if not header or len(parts) < 10:
            continue

        row = dict(zip(header, parts))
        pxname = row.get("pxname", "")
        svname = row.get("svname", "")

        # Look for listener or frontend/backend matching fwd_<port>
        if pxname.startswith("fwd_"):
            try:
                port_str = pxname.split("_", 1)[1]
                port = int(port_str)
            except (ValueError, IndexError):
                continue

            # In HAProxy 'listen' block, svname is typically 'FRONTEND' or 'BACKEND'
            # FRONTEND provides client-side bin and bout accurately
            if svname in ("FRONTEND", "srv_" + str(port)) or svname.startswith("srv_"):
                bin_bytes = int(row.get("bin", 0) or 0)
                bout_bytes = int(row.get("bout", 0) or 0)

                if port not in port_stats:
                    port_stats[port] = {"rx_bytes": 0, "tx_bytes": 0}

                if svname == "FRONTEND":
                    port_stats[port]["rx_bytes"] = bin_bytes
                    port_stats[port]["tx_bytes"] = bout_bytes
                elif port_stats[port]["rx_bytes"] == 0 and port_stats[port]["tx_bytes"] == 0:
                    port_stats[port]["rx_bytes"] = bin_bytes
                    port_stats[port]["tx_bytes"] = bout_bytes

    return port_stats


def read_haproxy_port_stats(sock_path: str = "/run/haproxy/admin.sock") -> Dict[int, Dict[str, int]]:
    """Communicates with HAProxy Runtime API socket to read per-port byte counters."""
    if sys.platform == "win32" or not os.path.exists(sock_path):
        return {}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.6)
            s.connect(sock_path)
            s.sendall(b"show stat\n")
            chunks = []
            while True:
                data = s.recv(8192)
                if not data:
                    break
                chunks.append(data)
                if len(data) < 8192:
                    break
            raw_csv = b"".join(chunks).decode("utf-8", errors="replace")
            return parse_haproxy_stats_csv(raw_csv)
    except Exception:
        return {}


def parse_nftables_counters_json(json_text: str) -> Dict[int, Dict[str, int]]:
    """
    Parses 'nft -j list counters' JSON output.
    Looks for named counters 'cnt_in_<port>' (RX) and 'cnt_out_<port>' (TX).
    Returns: {port: {'rx_bytes': int, 'tx_bytes': int}}
    """
    port_stats: Dict[int, Dict[str, int]] = {}
    if not json_text or not json_text.strip():
        return port_stats

    try:
        data = json.loads(json_text)
        items = data.get("nftables", [])
        for item in items:
            c = item.get("counter")
            if not isinstance(c, dict):
                continue
            name = c.get("name", "")
            bytes_cnt = int(c.get("bytes", 0))

            if name.startswith("cnt_in_"):
                try:
                    port = int(name.split("cnt_in_")[1])
                    if port not in port_stats:
                        port_stats[port] = {"rx_bytes": 0, "tx_bytes": 0}
                    port_stats[port]["rx_bytes"] = bytes_cnt
                except ValueError:
                    pass
            elif name.startswith("cnt_out_"):
                try:
                    port = int(name.split("cnt_out_")[1])
                    if port not in port_stats:
                        port_stats[port] = {"rx_bytes": 0, "tx_bytes": 0}
                    port_stats[port]["tx_bytes"] = bytes_cnt
                except ValueError:
                    pass
    except Exception:
        pass

    return port_stats


def read_nftables_port_stats() -> Dict[int, Dict[str, int]]:
    """Runs 'nft -j list counters table ip xfwd_orchestrator' to read kernel DNAT byte counters."""
    if sys.platform == "win32":
        return {}
    combined: Dict[int, Dict[str, int]] = {}
    for table_family in ("ip", "ip6"):
        try:
            cmd = ["nft", "-j", "list", "counters", "table", table_family, "xfwd_orchestrator"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout:
                parsed = parse_nftables_counters_json(res.stdout)
                for port, stats in parsed.items():
                    if port not in combined:
                        combined[port] = {"rx_bytes": 0, "tx_bytes": 0}
                    combined[port]["rx_bytes"] += stats["rx_bytes"]
                    combined[port]["tx_bytes"] += stats["tx_bytes"]
        except Exception:
            pass
    return combined


class TrafficCollector:
    """
    Thread-safe delta traffic accounting collector.
    Periodically samples HAProxy, NFTables, and Tunnel interfaces,
    computes deltas, and updates SQLite hourly pre-aggregated rollups.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_traffic_db_path()
        self.lock = threading.Lock()
        self._last_counters: Dict[str, Dict[str, int]] = {}
        self._last_collect_time: float = 0.0
        init_traffic_db(self.db_path)

    def collect_cycle(
        self,
        ports: Optional[List[int]] = None,
        tunnel_ifaces: Optional[List[str]] = None,
        haproxy_sock: str = "/run/haproxy/admin.sock"
    ) -> Dict[str, Any]:
        """
        Executes one collection cycle:
        1. Reads current raw counters from HAProxy, NFTables, and /proc/net/dev.
        2. Calculates delta bytes for each entity source since the previous cycle.
        3. Upserts deltas into SQLite traffic_hourly table.
        Returns a summary dictionary of recorded deltas.
        """
        now = time.time()
        hour_start = int(now // 3600) * 3600

        # Sample raw counters
        raw_haproxy = read_haproxy_port_stats(haproxy_sock)
        raw_nft = read_nftables_port_stats()
        raw_net_dev = read_proc_net_dev()

        deltas: Dict[Tuple[str, str], Dict[str, int]] = {}

        def _record_delta(etype: str, eid: str, rx_d: int, tx_d: int) -> None:
            if rx_d <= 0 and tx_d <= 0:
                return
            ekey = (etype, str(eid))
            if ekey not in deltas:
                deltas[ekey] = {"rx": 0, "tx": 0}
            deltas[ekey]["rx"] += max(0, rx_d)
            deltas[ekey]["tx"] += max(0, tx_d)

        with self.lock:
            # 1. Process Ports (HAProxy source - Direct IPv6 Relay)
            for port, stats in raw_haproxy.items():
                if ports is not None and port not in ports:
                    continue
                key = f"port:{port}:haproxy"
                prev = self._last_counters.get(key)
                rx_delta = stats["rx_bytes"] - prev["rx_bytes"] if prev and stats["rx_bytes"] >= prev["rx_bytes"] else stats["rx_bytes"]
                tx_delta = stats["tx_bytes"] - prev["tx_bytes"] if prev and stats["tx_bytes"] >= prev["tx_bytes"] else stats["tx_bytes"]

                # If first sampling ever, set baseline without inflating delta
                if prev is None:
                    rx_delta = 0
                    tx_delta = 0

                self._last_counters[key] = {"rx_bytes": stats["rx_bytes"], "tx_bytes": stats["tx_bytes"]}

                _record_delta("port", str(port), rx_delta, tx_delta)
                _record_delta("port_path", f"{port}:haproxy", rx_delta, tx_delta)
                _record_delta("method", "haproxy", rx_delta, tx_delta)
                _record_delta("tunnel_type", "direct_ipv6", rx_delta, tx_delta)

            # 2. Process Ports (NFTables source - Kernel Tunnel DNAT)
            for port, stats in raw_nft.items():
                if ports is not None and port not in ports:
                    continue
                key = f"port:{port}:nftables"
                prev = self._last_counters.get(key)
                rx_delta = stats["rx_bytes"] - prev["rx_bytes"] if prev and stats["rx_bytes"] >= prev["rx_bytes"] else stats["rx_bytes"]
                tx_delta = stats["tx_bytes"] - prev["tx_bytes"] if prev and stats["tx_bytes"] >= prev["tx_bytes"] else stats["tx_bytes"]

                if prev is None:
                    rx_delta = 0
                    tx_delta = 0

                self._last_counters[key] = {"rx_bytes": stats["rx_bytes"], "tx_bytes": stats["tx_bytes"]}

                _record_delta("port", str(port), rx_delta, tx_delta)
                _record_delta("port_path", f"{port}:nftables", rx_delta, tx_delta)
                _record_delta("method", "nftables", rx_delta, tx_delta)
                _record_delta("tunnel_type", "tunnel_dnat", rx_delta, tx_delta)

            # 3. Process Tunnels from /proc/net/dev
            for iface, stats in raw_net_dev.items():
                if tunnel_ifaces is not None and iface not in tunnel_ifaces:
                    continue
                # Skip loopback or primary wan if not specified
                if iface in ("lo", "docker0"):
                    continue

                key = f"tunnel:{iface}"
                prev = self._last_counters.get(key)
                rx_delta = stats["rx_bytes"] - prev["rx_bytes"] if prev and stats["rx_bytes"] >= prev["rx_bytes"] else stats["rx_bytes"]
                tx_delta = stats["tx_bytes"] - prev["tx_bytes"] if prev and stats["tx_bytes"] >= prev["tx_bytes"] else stats["tx_bytes"]

                if prev is None:
                    rx_delta = 0
                    tx_delta = 0

                self._last_counters[key] = {"rx_bytes": stats["rx_bytes"], "tx_bytes": stats["tx_bytes"]}

                _record_delta("tunnel", iface, rx_delta, tx_delta)
                ttype = classify_tunnel_type(iface)
                _record_delta("tunnel_type", ttype, rx_delta, tx_delta)

            self._last_collect_time = now

        # Upsert deltas into SQLite
        recorded_count = 0
        if deltas:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                try:
                    cursor = conn.cursor()
                    for (etype, eid), d in deltas.items():
                        rx_val = d["rx"]
                        tx_val = d["tx"]
                        total_val = rx_val + tx_val
                        if total_val <= 0:
                            continue
                        cursor.execute("""
                            INSERT INTO traffic_hourly (entity_type, entity_id, period_start, rx_bytes, tx_bytes, total_bytes)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(entity_type, entity_id, period_start) DO UPDATE SET
                                rx_bytes = rx_bytes + excluded.rx_bytes,
                                tx_bytes = tx_bytes + excluded.tx_bytes,
                                total_bytes = total_bytes + excluded.total_bytes;
                        """, (etype, eid, hour_start, rx_val, tx_val, total_val))
                        recorded_count += 1
                    conn.commit()
                finally:
                    conn.close()
            except Exception as e:
                print(f"[WARN] Failed to write traffic deltas to SQLite: {e}", file=sys.stderr)

        return {
            "timestamp": now,
            "period_start": hour_start,
            "entities_updated": recorded_count,
            "deltas": {f"{k[0]}:{k[1]}": v for k, v in deltas.items()}
        }


def get_traffic_resets(db_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Returns a map of { 'entity_type:entity_id': {'reset_timestamp': float, 'offset_rx': int, 'offset_tx': int} }."""
    path = db_path or get_traffic_db_path()
    resets: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(path):
        return resets
    try:
        conn = sqlite3.connect(path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx FROM traffic_resets;")
            for etype, eid, r_ts, off_rx, off_tx in cursor.fetchall():
                resets[f"{etype}:{eid}"] = {
                    "reset_timestamp": float(r_ts or 0.0),
                    "offset_rx": int(off_rx or 0),
                    "offset_tx": int(off_tx or 0)
                }
        finally:
            conn.close()
    except Exception:
        pass
    return resets


def reset_traffic_counter(
    entity_type: str,
    entity_id: str,
    wipe_history: bool = False,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resets traffic counter for a port or tunnel.
    - Default (wipe_history=False): Stores current total usage as a baseline offset.
      Current cycle usage drops to 0, while historical analytical charts remain intact.
    - Wipe history (wipe_history=True): Sets reset_timestamp AND deletes records from traffic_hourly.
    Supports entity_id = 'all' to reset all entities of that type.
    """
    path = db_path or get_traffic_db_path()
    init_traffic_db(path)
    now = time.time()

    clean_type = entity_type.strip().lower()
    clean_id = entity_id.strip()

    try:
        conn = sqlite3.connect(path, timeout=5.0)
        try:
            cursor = conn.cursor()

            if clean_id.lower() == "all" or clean_type == "all":
                if clean_type == "all":
                    cursor.execute("SELECT sum(rx_bytes), sum(tx_bytes) FROM traffic_hourly;")
                    row = cursor.fetchone()
                    tot_rx = int(row[0] or 0) if row else 0
                    tot_tx = int(row[1] or 0) if row else 0

                    cursor.execute("DELETE FROM traffic_resets;")
                    if wipe_history:
                        cursor.execute("DELETE FROM traffic_hourly;")
                        cursor.execute("""
                            INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                            VALUES ('all', 'all', ?, 0, 0);
                        """, (now,))
                    else:
                        cursor.execute("""
                            INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                            VALUES ('all', 'all', ?, ?, ?);
                        """, (now, tot_rx, tot_tx))
                        # Record individual baseline offsets so single entity queries remain accurate
                        cursor.execute("SELECT entity_type, entity_id, sum(rx_bytes), sum(tx_bytes) FROM traffic_hourly GROUP BY entity_type, entity_id;")
                        for et, ei, erx, etx in cursor.fetchall():
                            cursor.execute("""
                                INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                                    reset_timestamp = excluded.reset_timestamp,
                                    reset_offset_rx = excluded.reset_offset_rx,
                                    reset_offset_tx = excluded.reset_offset_tx;
                            """, (et, ei, now, int(erx or 0), int(etx or 0)))
                else:
                    cursor.execute("SELECT sum(rx_bytes), sum(tx_bytes) FROM traffic_hourly WHERE entity_type = ?;", (clean_type,))
                    row = cursor.fetchone()
                    tot_rx = int(row[0] or 0) if row else 0
                    tot_tx = int(row[1] or 0) if row else 0

                    cursor.execute("DELETE FROM traffic_resets WHERE entity_type = ?;", (clean_type,))
                    if wipe_history:
                        cursor.execute("DELETE FROM traffic_hourly WHERE entity_type = ?;", (clean_type,))
                        cursor.execute("""
                            INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                            VALUES (?, 'all', ?, 0, 0);
                        """, (clean_type, now))
                    else:
                        cursor.execute("""
                            INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                            VALUES (?, 'all', ?, ?, ?);
                        """, (clean_type, now, tot_rx, tot_tx))
                        cursor.execute("SELECT entity_id, sum(rx_bytes), sum(tx_bytes) FROM traffic_hourly WHERE entity_type = ? GROUP BY entity_id;", (clean_type,))
                        for ei, erx, etx in cursor.fetchall():
                            cursor.execute("""
                                INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                                    reset_timestamp = excluded.reset_timestamp,
                                    reset_offset_rx = excluded.reset_offset_rx,
                                    reset_offset_tx = excluded.reset_offset_tx;
                            """, (clean_type, ei, now, int(erx or 0), int(etx or 0)))
            else:
                cursor.execute("SELECT sum(rx_bytes), sum(tx_bytes) FROM traffic_hourly WHERE entity_type = ? AND entity_id = ?;", (clean_type, clean_id))
                row = cursor.fetchone()
                tot_rx = int(row[0] or 0) if row else 0
                tot_tx = int(row[1] or 0) if row else 0
                off_rx = 0 if wipe_history else tot_rx
                off_tx = 0 if wipe_history else tot_tx

                cursor.execute("""
                    INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                        reset_timestamp = excluded.reset_timestamp,
                        reset_offset_rx = excluded.reset_offset_rx,
                        reset_offset_tx = excluded.reset_offset_tx;
                """, (clean_type, clean_id, now, off_rx, off_tx))
                if clean_type == "port":
                    cursor.execute("SELECT entity_id, sum(rx_bytes), sum(tx_bytes) FROM traffic_hourly WHERE entity_type = 'port_path' AND entity_id LIKE ? GROUP BY entity_id;", (f"{clean_id}:%",))
                    for sub_eid, s_rx, s_tx in cursor.fetchall():
                        s_off_rx = 0 if wipe_history else int(s_rx or 0)
                        s_off_tx = 0 if wipe_history else int(s_tx or 0)
                        cursor.execute("""
                            INSERT INTO traffic_resets (entity_type, entity_id, reset_timestamp, reset_offset_rx, reset_offset_tx)
                            VALUES ('port_path', ?, ?, ?, ?)
                            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                                reset_timestamp = excluded.reset_timestamp,
                                reset_offset_rx = excluded.reset_offset_rx,
                                reset_offset_tx = excluded.reset_offset_tx;
                        """, (sub_eid, now, s_off_rx, s_off_tx))
                    if wipe_history:
                        cursor.execute("DELETE FROM traffic_hourly WHERE entity_type = 'port_path' AND entity_id LIKE ?;", (f"{clean_id}:%",))

                if wipe_history:
                    cursor.execute("DELETE FROM traffic_hourly WHERE entity_type = ? AND entity_id = ?;", (clean_type, clean_id))

            conn.commit()
            return {
                "success": True,
                "entity_type": clean_type,
                "entity_id": clean_id,
                "reset_timestamp": now,
                "wiped_history": wipe_history
            }
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_traffic_summary(
    period: str = "24h",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries traffic summary and per-entity metrics across specified period:
    - '24h': Last 24 hours
    - '7d': Last 7 days
    - '30d': Last 30 days
    - '12m': Last 12 months (365 days)
    Returns:
    - total_rx, total_tx, total_bytes
    - cycle_rx, cycle_tx, cycle_bytes (calculated since reset_timestamp)
    - entities: { entity_key: { rx, tx, total, cycle_total, reset_timestamp } }
    """
    path = db_path or get_traffic_db_path()
    now = time.time()

    period_seconds_map = {
        "24h": 86400,
        "7d": 7 * 86400,
        "30d": 30 * 86400,
        "12m": 365 * 86400
    }
    p_sec = period_seconds_map.get(period, 86400)
    cutoff_ts = int(now - p_sec)

    resets = get_traffic_resets(path)
    global_reset = resets.get("all:all", {})

    summary = {
        "period": period,
        "cutoff_timestamp": cutoff_ts,
        "now_timestamp": now,
        "total_rx": 0,
        "total_tx": 0,
        "total_bytes": 0,
        "cycle_rx": 0,
        "cycle_tx": 0,
        "cycle_bytes": 0,
        "entities": {}
    }

    if not os.path.exists(path):
        return summary

    try:
        conn = sqlite3.connect(path, timeout=5.0)
        try:
            cursor = conn.cursor()

            query = """
                SELECT entity_type, entity_id, period_start, rx_bytes, tx_bytes, total_bytes
                FROM traffic_hourly
                WHERE period_start >= ?
            """
            params: List[Any] = [cutoff_ts]

            clean_etype = entity_type.strip().lower() if entity_type else ""
            clean_eid = entity_id.strip() if entity_id else ""

            if clean_etype and clean_etype != "all":
                query += " AND entity_type = ?"
                params.append(clean_etype)
            else:
                # When all entities requested, limit main summary query to 'port' and 'tunnel' so we don't double count sub-rollups
                query += " AND entity_type IN ('port', 'tunnel')"

            if clean_eid and clean_eid.lower() != "all":
                query += " AND entity_id = ?"
                params.append(clean_eid)

            query += " ORDER BY period_start ASC;"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            for etype, eid, p_start, rx, tx, tot in rows:
                key = f"{etype}:{eid}"

                if key not in summary["entities"]:
                    e_reset_info = resets.get(key, resets.get(f"{etype}:all", global_reset))
                    r_ts = e_reset_info.get("reset_timestamp", 0.0) if isinstance(e_reset_info, dict) else float(e_reset_info or 0.0)
                    off_rx = e_reset_info.get("offset_rx", 0) if isinstance(e_reset_info, dict) else 0
                    off_tx = e_reset_info.get("offset_tx", 0) if isinstance(e_reset_info, dict) else 0

                    summary["entities"][key] = {
                        "entity_type": etype,
                        "entity_id": eid,
                        "rx_bytes": 0,
                        "tx_bytes": 0,
                        "total_bytes": 0,
                        "cycle_rx": 0,
                        "cycle_tx": 0,
                        "cycle_bytes": 0,
                        "reset_timestamp": r_ts,
                        "_offset_rx": off_rx,
                        "_offset_tx": off_tx
                    }

                e_entry = summary["entities"][key]
                e_entry["rx_bytes"] += rx
                e_entry["tx_bytes"] += tx
                e_entry["total_bytes"] += tot

                summary["total_rx"] += rx
                summary["total_tx"] += tx
                summary["total_bytes"] += tot

            # Compute cycle values after all bucket rows are aggregated
            for key, e_entry in summary["entities"].items():
                c_rx = max(0, e_entry["rx_bytes"] - e_entry["_offset_rx"])
                c_tx = max(0, e_entry["tx_bytes"] - e_entry["_offset_tx"])
                e_entry["cycle_rx"] = c_rx
                e_entry["cycle_tx"] = c_tx
                e_entry["cycle_bytes"] = c_rx + c_tx
                del e_entry["_offset_rx"]
                del e_entry["_offset_tx"]

                summary["cycle_rx"] += c_rx
                summary["cycle_tx"] += c_tx
                summary["cycle_bytes"] += (c_rx + c_tx)

            # If a specific entity was requested, reflect that entity's stats directly in top-level fields
            if clean_etype and clean_eid and clean_eid.lower() != "all":
                target_key = f"{clean_etype}:{clean_eid}"
                ent = summary["entities"].get(target_key)
                if ent:
                    summary["cycle_rx"] = ent["cycle_rx"]
                    summary["cycle_tx"] = ent["cycle_tx"]
                    summary["cycle_bytes"] = ent["cycle_bytes"]
                    summary["cycle_total"] = ent["cycle_bytes"]
                    summary["total_rx"] = ent["rx_bytes"]
                    summary["total_tx"] = ent["tx_bytes"]
                    summary["total_bytes"] = ent["total_bytes"]
                    summary["reset_timestamp"] = ent.get("reset_timestamp", 0.0)
            else:
                summary["cycle_total"] = summary["cycle_bytes"]
                summary["reset_timestamp"] = global_reset.get("reset_timestamp", 0.0) if isinstance(global_reset, dict) else float(global_reset or 0.0)

            # 1. Path breakdown for a specific port (HAProxy vs NFTables)
            if clean_etype == "port" and clean_eid and clean_eid != "all":
                cursor.execute("""
                    SELECT entity_id, sum(rx_bytes), sum(tx_bytes), sum(total_bytes)
                    FROM traffic_hourly
                    WHERE entity_type = 'port_path' AND entity_id LIKE ? AND period_start >= ?
                    GROUP BY entity_id;
                """, (f"{clean_eid}:%", cutoff_ts))
                p_tot_sum = summary["total_bytes"]
                path_list = []
                for peid, prx, ptx, ptot in cursor.fetchall():
                    sub_key = peid.split(":", 1)[1] if ":" in peid else peid
                    lbl = "Direct IPv6 (HAProxy Relay)" if sub_key == "haproxy" else ("Kernel Tunnel DNAT (NFTables)" if sub_key == "nftables" else sub_key)
                    pct = round((float(ptot) / p_tot_sum * 100.0), 1) if p_tot_sum > 0 else 0.0
                    path_list.append({
                        "key": sub_key,
                        "label": lbl,
                        "rx_bytes": int(prx or 0),
                        "tx_bytes": int(ptx or 0),
                        "total_bytes": int(ptot or 0),
                        "percentage": pct
                    })
                summary["path_breakdown"] = path_list

            # 2. Global Breakdown by Forwarding Method & Tunnel Type
            elif not clean_etype or clean_etype == "all":
                type_breakdown = []
                port_sum = sum(e["total_bytes"] for k, e in summary["entities"].items() if e["entity_type"] == "port")
                cursor.execute("""
                    SELECT entity_id, sum(rx_bytes), sum(tx_bytes), sum(total_bytes)
                    FROM traffic_hourly
                    WHERE entity_type = 'method' AND period_start >= ?
                    GROUP BY entity_id;
                """, (cutoff_ts,))
                for meid, mrx, mtx, mtot in cursor.fetchall():
                    lbl = "Direct IPv6 Relay (HAProxy)" if meid == "haproxy" else ("Kernel Tunnel DNAT (NFTables)" if meid == "nftables" else meid)
                    pct = round((float(mtot) / port_sum * 100.0), 1) if port_sum > 0 else 0.0
                    type_breakdown.append({
                        "key": f"method:{meid}",
                        "label": lbl,
                        "rx_bytes": int(mrx or 0),
                        "tx_bytes": int(mtx or 0),
                        "total_bytes": int(mtot or 0),
                        "percentage": pct
                    })

                cursor.execute("""
                    SELECT entity_id, sum(rx_bytes), sum(tx_bytes), sum(total_bytes)
                    FROM traffic_hourly
                    WHERE entity_type = 'tunnel_type' AND entity_id NOT IN ('direct_ipv6', 'tunnel_dnat') AND period_start >= ?
                    GROUP BY entity_id;
                """, (cutoff_ts,))
                tunnel_sum = sum(e["total_bytes"] for k, e in summary["entities"].items() if e["entity_type"] == "tunnel")
                for teid, trx, ttx, ttot in cursor.fetchall():
                    lbl = TUNNEL_TYPE_LABELS.get(teid, f"Tunnel ({teid})")
                    pct = round((float(ttot) / tunnel_sum * 100.0), 1) if tunnel_sum > 0 else 0.0
                    type_breakdown.append({
                        "key": f"tunnel_type:{teid}",
                        "label": lbl,
                        "rx_bytes": int(trx or 0),
                        "tx_bytes": int(ttx or 0),
                        "total_bytes": int(ttot or 0),
                        "percentage": pct
                    })
                summary["type_breakdown"] = type_breakdown

        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] Failed to query traffic summary: {e}", file=sys.stderr)

    return summary


def get_traffic_timeseries(
    period: str = "24h",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns grouped time-series buckets for interactive charts:
    - '24h': 24 hourly buckets
    - '7d' / '30d': Daily buckets (strftime %Y-%m-%d)
    - '12m': Monthly buckets (strftime %Y-%m)
    """
    path = db_path or get_traffic_db_path()
    now = time.time()

    period_seconds_map = {
        "24h": 86400,
        "7d": 7 * 86400,
        "30d": 30 * 86400,
        "12m": 365 * 86400
    }
    p_sec = period_seconds_map.get(period, 86400)
    cutoff_ts = int(now - p_sec)

    timeseries: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return timeseries

    try:
        conn = sqlite3.connect(path, timeout=5.0)
        try:
            cursor = conn.cursor()

            # Choose grouping bucket by period
            if period == "24h":
                group_fmt = "%Y-%m-%d %H:00"
            elif period in ("7d", "30d"):
                group_fmt = "%Y-%m-%d"
            else:  # 12m
                group_fmt = "%Y-%m"

            query = f"""
                SELECT
                    strftime('{group_fmt}', period_start, 'unixepoch') AS bucket_label,
                    min(period_start) AS bucket_start,
                    sum(rx_bytes) AS rx,
                    sum(tx_bytes) AS tx,
                    sum(total_bytes) AS tot
                FROM traffic_hourly
                WHERE period_start >= ?
            """
            params: List[Any] = [cutoff_ts]

            clean_etype = entity_type.strip().lower() if entity_type else ""
            clean_eid = entity_id.strip() if entity_id else ""

            if clean_etype and clean_etype != "all":
                query += " AND entity_type = ?"
                params.append(clean_etype)
            else:
                query += " AND entity_type IN ('port', 'tunnel')"

            if clean_eid and clean_eid.lower() != "all":
                query += " AND entity_id = ?"
                params.append(clean_eid)

            query += f" GROUP BY strftime('{group_fmt}', period_start, 'unixepoch') ORDER BY bucket_start ASC;"

            cursor.execute(query, params)
            for label, b_start, rx, tx, tot in cursor.fetchall():
                timeseries.append({
                    "label": label,
                    "period": label,
                    "timestamp": b_start,
                    "rx_bytes": int(rx or 0),
                    "tx_bytes": int(tx or 0),
                    "total_bytes": int(tot or 0)
                })
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] Failed to query traffic timeseries: {e}", file=sys.stderr)

    return timeseries


def prune_old_traffic_records(retention_days: int = TRAFFIC_RETENTION_DAYS, db_path: Optional[str] = None) -> int:
    """Removes traffic records older than retention_days (default 90 days)."""
    path = db_path or get_traffic_db_path()
    if not os.path.exists(path):
        return 0
    cutoff = int(time.time() - (retention_days * 86400))
    deleted = 0
    try:
        conn = sqlite3.connect(path, timeout=5.0)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM traffic_hourly WHERE period_start < ?;", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass
    return deleted

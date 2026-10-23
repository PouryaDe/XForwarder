#!/usr/bin/env python3
"""
XForwarder - Network Quality & Packet Loss Monitoring Subsystem.
Zero-pip dependency standard library module (sqlite3, subprocess, re, time).

Features:
- Precise 50-probe packet loss measurement: `ping [ip] -c 50 -i 0.2`
- Deduplicated target discovery across all configured ports and rules
- 15-minute background scheduled rounds
- SQLite time-series storage with automatic 30-day retention pruning
- Multi-tier timeline aggregation (24h, 7d, 30d) and disruption incident tracking
"""

import os
import sys
import re
import time
import json
import sqlite3
import threading
import subprocess
import ipaddress
from typing import Dict, List, Any, Optional, Tuple, Set


DEFAULT_DB_DIR = "/etc/xforwarder"
LEGACY_DB_DIR = "/etc/forward-manager"
DB_FILENAME = "metrics.db"
RETENTION_DAYS = 30
LOSS_CHECK_INTERVAL_SECONDS = 900  # 15 minutes


def get_metrics_db_path() -> str:
    """Resolves the persistent SQLite database path for network metrics."""
    env_path = os.environ.get("XFWD_METRICS_PATH")
    if env_path:
        return env_path

    # Check if primary config directory exists
    if os.path.exists(DEFAULT_DB_DIR) and os.path.isdir(DEFAULT_DB_DIR):
        return os.path.join(DEFAULT_DB_DIR, DB_FILENAME)
    if os.path.exists(LEGACY_DB_DIR) and os.path.isdir(LEGACY_DB_DIR):
        return os.path.join(LEGACY_DB_DIR, DB_FILENAME)

    # Local fallback for development / test environments
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(base_dir, "config")
    if os.path.exists(config_dir):
        return os.path.join(config_dir, DB_FILENAME)

    return os.path.join(DEFAULT_DB_DIR, DB_FILENAME)


def init_metrics_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite schema with WAL journal mode and indexing."""
    path = db_path or get_metrics_db_path()
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ping_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    latency_ms REAL,
                    min_lat REAL,
                    max_lat REAL,
                    packet_loss REAL NOT NULL,
                    packets_sent INTEGER NOT NULL,
                    packets_received INTEGER NOT NULL,
                    is_disrupted INTEGER NOT NULL,
                    error TEXT
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_target_ts ON ping_history(target, timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_ts ON ping_history(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_disrupted ON ping_history(is_disrupted, timestamp);")
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] Failed to initialize metrics database at {path}: {e}", file=sys.stderr)


HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def sanitize_target_host(target: str) -> str:
    """
    Strictly validates and sanitizes destination target to prevent command/argument injection.
    Allows only valid IPv4, IPv6, or RFC-compliant hostnames.
    Rejects strings with leading dashes, quotes, semicolons, or invalid formats.
    """
    clean = (target or "").strip().strip("[]")
    if not clean or clean.startswith("-") or clean.startswith("."):
        return ""

    # 1. Validate IPv4 or IPv6
    try:
        ipaddress.ip_address(clean)
        return clean
    except ValueError:
        pass

    # 2. Reject all-numeric dotted quad that failed IP validation
    parts = clean.split(".")
    if all(p.isdigit() for p in parts):
        return ""

    # 3. Check RFC hostname (TLD cannot be purely numeric per RFC 3696)
    if HOSTNAME_REGEX.match(clean):
        if len(parts) > 1 and parts[-1].isdigit():
            return ""
        return clean

    return ""


def parse_ping_output(stdout_text: str, returncode: int, sent_default: int = 50) -> Dict[str, Any]:
    """
    Robust regex parser for standard Linux (iputils) and Windows ping statistics.
    Extracts sent, received, loss percentage, and min/avg/max latencies.
    """
    text = stdout_text or ""

    # 1. Packet statistics
    sent = sent_default
    received = 0
    loss_pct = 100.0

    # Linux: "50 packets transmitted, 49 received, 2% packet loss"
    m_pkts = re.search(r'(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received', text)
    if m_pkts:
        sent = int(m_pkts.group(1))
        received = int(m_pkts.group(2))
    else:
        # Windows: "Packets: Sent = 50, Received = 48, Lost = 2 (4% loss)"
        m_win_pkts = re.search(r'Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+)', text)
        if m_win_pkts:
            sent = int(m_win_pkts.group(1))
            received = int(m_win_pkts.group(2))

    # Loss percentage
    m_loss = re.search(r'(\d+(?:\.\d+)?)%\s+(?:packet\s+)?loss', text, re.IGNORECASE)
    if m_loss:
        loss_pct = float(m_loss.group(1))
    elif sent > 0:
        loss_pct = round(((sent - received) / sent) * 100.0, 1)

    # 2. Round-trip Latency & Jitter
    avg_lat: Optional[float] = None
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    jitter_ms: float = 0.0

    # Linux: "rtt min/avg/max/mdev = 13.912/14.502/16.120/0.450 ms"
    m_rtt = re.search(r'min/avg/max(?:/mdev)?\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)(?:/([\d.]+))?', text)
    if m_rtt:
        try:
            min_lat = round(float(m_rtt.group(1)), 1)
            avg_lat = round(float(m_rtt.group(2)), 1)
            max_lat = round(float(m_rtt.group(3)), 1)
            if m_rtt.group(4):
                jitter_ms = round(float(m_rtt.group(4)), 1)
            elif max_lat is not None and min_lat is not None:
                jitter_ms = round((max_lat - min_lat) / 2.0, 1)
        except ValueError:
            pass
    else:
        # Windows: "Minimum = 12ms, Maximum = 18ms, Average = 14ms"
        m_win_rtt = re.search(r'Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms', text, re.IGNORECASE)
        if m_win_rtt:
            try:
                min_lat = float(m_win_rtt.group(1))
                max_lat = float(m_win_rtt.group(2))
                avg_lat = float(m_win_rtt.group(3))
                jitter_ms = round((max_lat - min_lat) / 2.0, 1)
            except ValueError:
                pass
        else:
            # Single sample Windows: "Average = 14ms"
            m_avg = re.search(r'Average\s*=\s*(\d+)ms', text, re.IGNORECASE)
            if m_avg:
                try:
                    avg_lat = float(m_avg.group(1))
                except ValueError:
                    pass

    # Determine health & disruption state
    healthy = (received > 0 and loss_pct < 100.0)
    is_disrupted = 1 if (loss_pct > 0.0 or not healthy or returncode != 0) else 0

    return {
        "healthy": healthy,
        "packets_sent": sent,
        "packets_received": received,
        "packet_loss": loss_pct,
        "latency_ms": avg_lat,
        "min_lat": min_lat,
        "max_lat": max_lat,
        "jitter_ms": jitter_ms,
        "is_disrupted": is_disrupted
    }


def measure_packet_loss_50(
    target: str,
    iface: Optional[str] = None,
    count: int = 50,
    interval: float = 0.2,
    timeout_sec: int = 25,
    save_to_db: bool = True,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes precise packet loss test using `ping [ip] -c 50 -i 0.2`.
    On Linux, strictly uses `-c 50 -i 0.2 -W 1`.
    Returns complete metrics dictionary and automatically records into SQLite when save_to_db is True.
    """
    clean_target = sanitize_target_host(target)
    # Enforce safe parameter boundaries
    safe_count = max(1, min(int(count) if str(count).isdigit() else 50, 200))
    safe_interval = max(0.1, min(float(interval) if str(interval).replace('.', '', 1).isdigit() else 0.2, 5.0))
    safe_timeout = max(2, min(int(timeout_sec) if str(timeout_sec).isdigit() else 25, 120))

    if not clean_target:
        return {
            "target": target,
            "healthy": False,
            "packet_loss": 100.0,
            "latency_ms": None,
            "min_lat": None,
            "max_lat": None,
            "packets_sent": safe_count,
            "packets_received": 0,
            "is_disrupted": 1,
            "error": "Invalid target host or IP address"
        }

    # Construct the ping command
    if sys.platform == "win32":
        # Windows ping does not support sub-second interval -i; use -n and fast timeout
        cmd = ["ping", "-n", str(safe_count), "-w", "500", clean_target]
    else:
        # Standard Linux iputils ping with -c 50 -i 0.2 -W 1
        cmd = ["ping", "-c", str(safe_count), "-i", str(safe_interval), "-W", "1"]
        if iface:
            clean_iface = str(iface).strip()
            if clean_iface and not clean_iface.startswith("-") and re.match(r'^[a-zA-Z0-9_.-]+$', clean_iface):
                cmd.extend(["-I", clean_iface])
        cmd.append(clean_target)

    start_t = time.time()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec
        )
        parsed = parse_ping_output(proc.stdout, proc.returncode, sent_default=count)
        error_msg = ""
        if proc.returncode != 0 and parsed["packets_received"] == 0:
            error_msg = proc.stderr.strip() or "Destination host unreachable"
    except subprocess.TimeoutExpired:
        parsed = {
            "healthy": False,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss": 100.0,
            "latency_ms": None,
            "min_lat": None,
            "max_lat": None,
            "is_disrupted": 1
        }
        error_msg = f"Ping probe timed out after {timeout_sec}s"
    except Exception as e:
        parsed = {
            "healthy": False,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss": 100.0,
            "latency_ms": None,
            "min_lat": None,
            "max_lat": None,
            "is_disrupted": 1
        }
        error_msg = str(e)

    result = {
        "target": clean_target,
        "healthy": parsed["healthy"],
        "packet_loss": parsed["packet_loss"],
        "latency_ms": parsed["latency_ms"],
        "min_lat": parsed["min_lat"],
        "max_lat": parsed["max_lat"],
        "packets_sent": parsed["packets_sent"],
        "packets_received": parsed["packets_received"],
        "is_disrupted": parsed["is_disrupted"],
        "timestamp": time.time(),
        "duration_sec": round(time.time() - start_t, 2),
        "error": error_msg
    }

    if save_to_db:
        record_ping_result(clean_target, result, db_path=db_path)

    return result


def record_ping_result(target: str, res: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Inserts a ping metric probe result into SQLite database."""
    path = db_path or get_metrics_db_path()
    init_metrics_db(path)

    try:
        conn = sqlite3.connect(path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ping_history (
                    target, timestamp, latency_ms, min_lat, max_lat,
                    packet_loss, packets_sent, packets_received, is_disrupted, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                target,
                res.get("timestamp", time.time()),
                res.get("latency_ms"),
                res.get("min_lat"),
                res.get("max_lat"),
                float(res.get("packet_loss", 0.0)),
                int(res.get("packets_sent", 50)),
                int(res.get("packets_received", 0)),
                int(res.get("is_disrupted", 0)),
                res.get("error", "")
            ))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] Failed to record ping metric for {target}: {e}", file=sys.stderr)


def prune_old_metrics(retention_days: int = RETENTION_DAYS, db_path: Optional[str] = None) -> int:
    """Prunes records older than retention_days (default: 30 days) to prevent disk bloat."""
    path = db_path or get_metrics_db_path()
    if not os.path.exists(path):
        return 0

    cutoff_ts = time.time() - (retention_days * 86400)
    pruned = 0
    try:
        conn = sqlite3.connect(path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ping_history WHERE timestamp < ?;", (cutoff_ts,))
            pruned = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[WARN] Failed to prune old metrics: {e}", file=sys.stderr)
    return pruned


def get_unique_targets_from_config(cfg: Dict[str, Any]) -> List[str]:
    """
    Extracts all unique destination targets across all forwarding rules.
    Guarantees that an IP referenced across multiple ports is tested only ONCE.
    """
    unique_targets: Set[str] = set()
    rules = cfg.get("rules", [])
    if not isinstance(rules, list):
        return []

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        destinations = rule.get("destinations", [])
        if not isinstance(destinations, list):
            continue
        for dest in destinations:
            if not isinstance(dest, dict):
                continue
            raw_target = dest.get("target")
            clean = sanitize_target_host(raw_target)
            if clean:
                unique_targets.add(clean)

    return sorted(list(unique_targets))


def run_scheduled_ping_round(cfg: Dict[str, Any], db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Executes one 15-minute scheduled round across all unique targets.
    Automatically prunes entries older than 30 days.
    """
    targets = get_unique_targets_from_config(cfg)
    results: List[Dict[str, Any]] = []

    for target in targets:
        try:
            res = measure_packet_loss_50(target, count=50, interval=0.2, save_to_db=True, db_path=db_path)
            results.append(res)
        except Exception as e:
            print(f"[ERROR] Error probing target {target} in scheduled round: {e}", file=sys.stderr)

    # Prune data older than 30 days
    prune_old_metrics(RETENTION_DAYS, db_path=db_path)

    return results


def get_metrics_history(
    target: Optional[str] = None,
    time_range_hours: int = 24,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries historical metrics for visualization in dashboard.
    Returns:
    - Tracked targets list
    - High-level KPIs (quality score %, average latency, peak loss, disruption events count)
    - 15-minute or hourly time-bucketed timeline slots
    - Recent disruption events list with timestamps
    """
    path = db_path or get_metrics_db_path()
    if not os.path.exists(path):
        return {
            "targets": [],
            "summary": {
                "total_probes": 0,
                "disrupted_probes": 0,
                "clean_probes": 0,
                "quality_pct": 100.0,
                "avg_latency_ms": 0.0,
                "avg_loss_pct": 0.0,
                "peak_loss_pct": 0.0,
                "disruption_count": 0
            },
            "timeline": [],
            "recent_disruptions": [],
            "hours": time_range_hours
        }

    since_ts = time.time() - (time_range_hours * 3600)

    try:
        conn = sqlite3.connect(path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            # 1. Distinct targets
            cursor.execute("SELECT DISTINCT target FROM ping_history ORDER BY target;")
            all_targets = [row["target"] for row in cursor.fetchall()]

            # 2. Filter query
            query_base = "FROM ping_history WHERE timestamp >= ?"
            params: List[Any] = [since_ts]
            if target and target != "all":
                clean_target = sanitize_target_host(target)
                if clean_target:
                    query_base += " AND target = ?"
                    params.append(clean_target)

            # 3. Overall Summary Stats
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_probes,
                    SUM(CASE WHEN is_disrupted = 1 THEN 1 ELSE 0 END) as disrupted_probes,
                    AVG(latency_ms) as avg_latency_ms,
                    AVG(packet_loss) as avg_loss_pct,
                    MAX(packet_loss) as peak_loss_pct
                {query_base}
            """, params)
            sum_row = cursor.fetchone()

            total_probes = sum_row["total_probes"] if sum_row and sum_row["total_probes"] else 0
            disrupted_probes = sum_row["disrupted_probes"] if sum_row and sum_row["disrupted_probes"] else 0
            clean_probes = total_probes - disrupted_probes
            quality_pct = round((clean_probes / total_probes) * 100.0, 1) if total_probes > 0 else 100.0
            avg_lat = round(sum_row["avg_latency_ms"], 1) if sum_row and sum_row["avg_latency_ms"] is not None else 0.0
            avg_loss = round(sum_row["avg_loss_pct"], 1) if sum_row and sum_row["avg_loss_pct"] is not None else 0.0
            peak_loss = round(sum_row["peak_loss_pct"], 1) if sum_row and sum_row["peak_loss_pct"] is not None else 0.0

            # 4. Recent Disruption Events (latest 50)
            cursor.execute(f"""
                SELECT id, target, timestamp, latency_ms, min_lat, max_lat,
                       packet_loss, packets_sent, packets_received, error
                {query_base} AND is_disrupted = 1
                ORDER BY timestamp DESC
                LIMIT 50;
            """, params)
            disruptions = []
            for r in cursor.fetchall():
                ts = r["timestamp"]
                disruptions.append({
                    "id": r["id"],
                    "target": r["target"],
                    "timestamp": ts,
                    "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                    "latency_ms": r["latency_ms"],
                    "packet_loss": r["packet_loss"],
                    "packets_sent": r["packets_sent"],
                    "packets_received": r["packets_received"],
                    "error": r["error"] or ("Packet loss detected" if r["packet_loss"] > 0 else "Unreachable")
                })

            # 5. Timeline grouping
            # If range <= 24h: group into 15-minute buckets (900s)
            # If range <= 7d (168h): group into 1-hour buckets (3600s)
            # If range > 7d: group into 6-hour buckets (21600s)
            bucket_sec = 900 if time_range_hours <= 24 else (3600 if time_range_hours <= 168 else 21600)

            cursor.execute(f"""
                SELECT
                    (CAST(timestamp / {bucket_sec} AS INTEGER) * {bucket_sec}) as bucket_ts,
                    COUNT(*) as count,
                    SUM(CASE WHEN is_disrupted = 1 THEN 1 ELSE 0 END) as disrupted_count,
                    AVG(latency_ms) as avg_lat,
                    AVG(packet_loss) as avg_loss,
                    MAX(packet_loss) as peak_loss
                {query_base}
                GROUP BY bucket_ts
                ORDER BY bucket_ts ASC;
            """, params)

            timeline = []
            for b in cursor.fetchall():
                b_ts = b["bucket_ts"]
                b_disrupted = (b["disrupted_count"] or 0) > 0
                avg_b_loss = round(b["avg_loss"] or 0.0, 1)
                peak_b_loss = round(b["peak_loss"] or 0.0, 1)
                timeline.append({
                    "timestamp": b_ts,
                    "time_str": time.strftime("%H:%M" if time_range_hours <= 24 else "%m-%d %H:%M", time.localtime(b_ts)),
                    "date_str": time.strftime("%Y-%m-%d", time.localtime(b_ts)),
                    "probe_count": b["count"],
                    "disrupted_count": b["disrupted_count"] or 0,
                    "is_disrupted": b_disrupted,
                    "avg_latency_ms": round(b["avg_lat"], 1) if b["avg_lat"] is not None else None,
                    "avg_loss_pct": avg_b_loss,
                    "peak_loss_pct": peak_b_loss
                })

            return {
                "targets": all_targets,
                "summary": {
                    "total_probes": total_probes,
                    "disrupted_probes": disrupted_probes,
                    "clean_probes": clean_probes,
                    "quality_pct": quality_pct,
                    "avg_latency_ms": avg_lat,
                    "avg_loss_pct": avg_loss,
                    "peak_loss_pct": peak_loss,
                    "disruption_count": len(disruptions)
                },
                "timeline": timeline,
                "recent_disruptions": disruptions,
                "hours": time_range_hours,
                "active_target": target or "all"
            }
        finally:
            conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to query metrics history: {e}", file=sys.stderr)
        return {
            "targets": [],
            "summary": {
                "total_probes": 0,
                "disrupted_probes": 0,
                "clean_probes": 0,
                "quality_pct": 100.0,
                "avg_latency_ms": 0.0,
                "avg_loss_pct": 0.0,
                "peak_loss_pct": 0.0,
                "disruption_count": 0
            },
            "timeline": [],
            "recent_disruptions": [],
            "hours": time_range_hours,
            "error": str(e)
        }


class LossMonitorScheduler:
    """
    Background daemon thread that triggers 50-probe packet loss rounds every 15 minutes.
    Deduplicates target testing across all rules and retains 30 days of data.
    """

    def __init__(self, config_loader_fn, interval_seconds: int = LOSS_CHECK_INTERVAL_SECONDS, db_path: Optional[str] = None):
        self.config_loader_fn = config_loader_fn
        self.interval_seconds = interval_seconds
        self.db_path = db_path
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._wake_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="LossMonitorScheduler")
        self._thread.start()
        print(f"[INFO] 15-Minute Packet Loss Monitor started (Interval: {self.interval_seconds}s, Retention: {RETENTION_DAYS} days).")

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def trigger_now(self) -> None:
        """Triggers an immediate round out of schedule without terminating the worker."""
        self._wake_event.set()

    def _run_loop(self) -> None:
        # Initial wait of 10s to let main engine finish startup sync, wakeable early or stoppable
        if self._wake_event.wait(timeout=10):
            if self._stop_event.is_set():
                return
            self._wake_event.clear()

        while not self._stop_event.is_set():
            try:
                cfg = self.config_loader_fn() if callable(self.config_loader_fn) else {}
                if isinstance(cfg, dict):
                    run_scheduled_ping_round(cfg, db_path=self.db_path)
            except Exception as e:
                print(f"[ERROR] Exception in LossMonitorScheduler round: {e}", file=sys.stderr)

            # Wait for next 15-minute interval or early manual trigger or shutdown
            self._wake_event.clear()
            self._wake_event.wait(timeout=self.interval_seconds)
            if self._stop_event.is_set():
                break

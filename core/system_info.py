#!/usr/bin/env python3
"""
XForwarder - Host Telemetry & Topology Inspector
Provides real-time system resource metrics, services lifecycle states,
and network interface & tunnel topology discovery.
"""

import os
import sys
import json
import time
import socket
import shutil
import threading
import subprocess
from typing import Dict, Any, Tuple, Optional, List

from core.config_manager import load_config

_VERSION_CACHE: Dict[str, str] = {}
_PREV_NET_IO: Dict[str, Any] = {"rx": 0, "tx": 0, "time": 0.0}
_NET_IO_LOCK = threading.Lock()

_SERVICES_CACHE: Dict[str, Any] = {"data": None, "expires": 0}
_SERVICES_LOCK = threading.Lock()

_NET_CACHE: Dict[str, Any] = {"data": None, "expires": 0}
_NET_LOCK = threading.Lock()

# Linux kernel fallback devices and container bridges that must never appear in topology
DEFAULT_IGNORED_INTERFACES = frozenset({
    "lo",
    # Linux kernel fallback tunnel devices (created automatically on module load)
    "gre0",
    "gretap0",
    "erspan0",
    "tunl0",
    "sit0",
    "ip6tnl0",
    "ip6gre0",
    "ip6erspan0",
    # System dummy / traffic control fallback devices
    "dummy0",
    "teql0",
})


def is_ignored_interface(ifname: str) -> bool:
    """Returns True if the interface is a system loopback, default kernel fallback tunnel, or container bridge."""
    if not ifname:
        return True
    lower = ifname.lower().strip()
    if not lower:
        return True
    if lower in DEFAULT_IGNORED_INTERFACES:
        return True
    if lower.startswith(("docker", "veth", "virbr", "br-")):
        return True
    return False


def ping_target(target: str, iface: Optional[str] = None) -> Tuple[bool, Optional[float]]:
    """Safe bounded ping probe with strict character whitelisting."""
    if not target or not all(c in "0123456789abcdefABCDEF:.-" for c in target):
        return False, None
    try:
        start = time.perf_counter()
        if sys.platform == "win32":
            cmd = ["ping", "-n", "1", "-w", "1000", target]
        else:
            cmd = ["ping", "-c", "1", "-W", "1"]
            if iface:
                cmd.extend(["-I", iface])
            cmd.append(target)
        res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res == 0:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return True, elapsed
    except Exception:
        pass
    return False, None


def get_system_stats() -> dict:
    """Collects host hardware metrics (RAM, CPU, sockets, network rate)."""
    stats = {
        "ram_used_mb": 0,
        "ram_total_mb": 0,
        "ram_percent": 0,
        "cpu_percent": 0,
        "load_1": 0.0,
        "load_5": 0.0,
        "load_15": 0.0,
        "load_str": "0.00",
        "tcp_connections": 0,
        "udp_connections": 0,
        "net_rx_mb": 0.0,
        "net_tx_mb": 0.0,
        "net_total_mb": 0.0,
        "net_rx_rate_kb": 0.0,
        "net_tx_rate_kb": 0.0,
        "net_rx_rate_mb": 0.0,
        "net_tx_rate_mb": 0.0
    }
    # 1. RAM Usage
    if os.path.exists("/proc/meminfo"):
        try:
            mem = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        mem[parts[0].strip()] = parts[1].strip().split()[0]
            total_kb = float(mem.get("MemTotal", 0))
            avail_kb = float(mem.get("MemAvailable", mem.get("MemFree", 0)))
            used_kb = max(0.0, total_kb - avail_kb)
            if total_kb > 0:
                stats["ram_total_mb"] = int(round(total_kb / 1024))
                stats["ram_used_mb"] = int(round(used_kb / 1024))
                stats["ram_percent"] = round((used_kb / total_kb) * 100, 1)
        except Exception:
            pass

    # 2. System Load & CPU Usage
    if os.path.exists("/proc/loadavg"):
        try:
            with open("/proc/loadavg", "r", encoding="utf-8") as f:
                parts = f.read().split()
                if len(parts) >= 3:
                    l1 = float(parts[0])
                    l5 = float(parts[1])
                    l15 = float(parts[2])
                    stats["load_1"] = l1
                    stats["load_5"] = l5
                    stats["load_15"] = l15
                    stats["load_str"] = f"{l1:.2f}"
                    cpu_count = os.cpu_count() or 1
                    stats["cpu_percent"] = min(100.0, round((l1 / cpu_count) * 100, 1))
        except Exception:
            pass

    # 3. Active TCP & UDP Socket Counts (via /proc/net/sockstat and sockstat6)
    tcp_count = 0
    udp_count = 0
    for s_path in ("/proc/net/sockstat", "/proc/net/sockstat6"):
        if os.path.exists(s_path):
            try:
                with open(s_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TCP:") or line.startswith("TCP6:"):
                            kvs = line.split()
                            for idx in range(1, len(kvs) - 1, 2):
                                if kvs[idx] == "inuse":
                                    tcp_count += int(kvs[idx + 1])
                        elif line.startswith("UDP:") or line.startswith("UDP6:"):
                            kvs = line.split()
                            for idx in range(1, len(kvs) - 1, 2):
                                if kvs[idx] == "inuse":
                                    udp_count += int(kvs[idx + 1])
            except Exception:
                pass
    stats["tcp_connections"] = tcp_count
    stats["udp_connections"] = udp_count

    # 4. Total Network Traffic & Live Speed (RX & TX in MB, excluding loopback)
    if os.path.exists("/proc/net/dev"):
        try:
            total_rx_bytes = 0
            total_tx_bytes = 0
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    iface, data = line.split(":", 1)
                    if is_ignored_interface(iface.strip()):
                        continue
                    fields = data.split()
                    if len(fields) >= 9:
                        try:
                            rx_b = int(fields[0])
                            tx_b = int(fields[8])
                            total_rx_bytes += rx_b
                            total_tx_bytes += tx_b
                        except (ValueError, IndexError):
                            continue

            # Convert cumulative transfer strictly to Megabytes (1 MB = 1024 * 1024 bytes)
            stats["net_rx_mb"] = round(total_rx_bytes / (1024 * 1024), 2)
            stats["net_tx_mb"] = round(total_tx_bytes / (1024 * 1024), 2)
            stats["net_total_mb"] = round((total_rx_bytes + total_tx_bytes) / (1024 * 1024), 2)

            now = time.time()
            with _NET_IO_LOCK:
                if _PREV_NET_IO["time"] > 0:
                    dt = max(0.2, now - _PREV_NET_IO["time"])
                    drx = max(0, total_rx_bytes - _PREV_NET_IO["rx"])
                    dtx = max(0, total_tx_bytes - _PREV_NET_IO["tx"])
                    stats["net_rx_rate_kb"] = round((drx / 1024) / dt, 1)
                    stats["net_tx_rate_kb"] = round((dtx / 1024) / dt, 1)
                    stats["net_rx_rate_mb"] = round((drx / (1024 * 1024)) / dt, 2)
                    stats["net_tx_rate_mb"] = round((dtx / (1024 * 1024)) / dt, 2)
                else:
                    stats["net_rx_rate_kb"] = 0.0
                    stats["net_tx_rate_kb"] = 0.0
                    stats["net_rx_rate_mb"] = 0.0
                    stats["net_tx_rate_mb"] = 0.0

                _PREV_NET_IO["rx"] = total_rx_bytes
                _PREV_NET_IO["tx"] = total_tx_bytes
                _PREV_NET_IO["time"] = now
        except Exception:
            pass

    return stats


def get_services_status() -> Dict[str, Any]:
    """
    Inspects whether NFTables, HAProxy, and Nginx are installed and active on the host system.
    Cached for 6.0 seconds to prevent unnecessary subprocess spawning on low-resource relay servers.
    """
    now = time.time()
    with _SERVICES_LOCK:
        if _SERVICES_CACHE["data"] and now < _SERVICES_CACHE["expires"]:
            return _SERVICES_CACHE["data"]

    status = {
        "nftables": {
            "installed": False,
            "active": False,
            "table_active": False,
            "version": None,
            "details": "Not Installed"
        },
        "haproxy": {
            "installed": False,
            "active": False,
            "version": None,
            "details": "Not Installed"
        },
        "nginx": {
            "installed": False,
            "active": False,
            "version": None,
            "details": "Not Installed"
        }
    }

    # 1. NFTables Check
    nft_bin = shutil.which("nft")
    if not nft_bin:
        for p in ("/usr/sbin/nft", "/sbin/nft", "/usr/bin/nft"):
            if os.path.exists(p) and os.access(p, os.X_OK):
                nft_bin = p
                break

    if nft_bin:
        status["nftables"]["installed"] = True
        if "nftables" in _VERSION_CACHE:
            status["nftables"]["version"] = _VERSION_CACHE["nftables"]
        else:
            try:
                res_v = subprocess.run([nft_bin, "--version"], capture_output=True, text=True, timeout=1.0)
                if res_v.returncode == 0:
                    v_line = res_v.stdout.strip().split("\n")[0]
                    v_val = v_line.replace("nftables", "").strip().split()[0]
                    status["nftables"]["version"] = v_val
                    _VERSION_CACHE["nftables"] = v_val
            except Exception:
                pass

        try:
            res_t = subprocess.run([nft_bin, "list", "tables"], capture_output=True, text=True, timeout=1.0)
            if res_t.returncode == 0:
                status["nftables"]["active"] = True
                if "table ip xfwd_orchestrator" in res_t.stdout or "table ip6 xfwd_orchestrator" in res_t.stdout:
                    status["nftables"]["table_active"] = True
                    status["nftables"]["details"] = "Active & Orchestrator Loaded"
                else:
                    status["nftables"]["details"] = "Active (Table Idle)"
            else:
                status["nftables"]["details"] = "Installed (Inactive)"
        except Exception:
            status["nftables"]["details"] = "Installed (Check Failed)"
    else:
        status["nftables"]["details"] = "Not Installed"

    # 2. HAProxy Check
    haproxy_bin = shutil.which("haproxy")
    if not haproxy_bin:
        for p in ("/usr/sbin/haproxy", "/sbin/haproxy", "/usr/bin/haproxy"):
            if os.path.exists(p) and os.access(p, os.X_OK):
                haproxy_bin = p
                break

    if haproxy_bin:
        status["haproxy"]["installed"] = True
        if "haproxy" in _VERSION_CACHE:
            status["haproxy"]["version"] = _VERSION_CACHE["haproxy"]
        else:
            try:
                res_v = subprocess.run([haproxy_bin, "-v"], capture_output=True, text=True, timeout=1.0)
                if res_v.returncode == 0:
                    v_line = res_v.stdout.strip().split("\n")[0]
                    for token in v_line.split():
                        if token.replace(".", "").isdigit() or "dev" in token:
                            status["haproxy"]["version"] = token
                            _VERSION_CACHE["haproxy"] = token
                            break
            except Exception:
                pass

        is_active = False
        try:
            res_s = subprocess.run(["systemctl", "is-active", "haproxy"], capture_output=True, text=True, timeout=1.0)
            if res_s.returncode == 0 and res_s.stdout.strip() == "active":
                is_active = True
        except Exception:
            pass

        if not is_active:
            try:
                res_p = subprocess.run(["pgrep", "-x", "haproxy"], capture_output=True, text=True, timeout=1.0)
                if res_p.returncode == 0 and res_p.stdout.strip():
                    is_active = True
            except Exception:
                pass

        status["haproxy"]["active"] = is_active
        ver_str = f" ({status['haproxy']['version']})" if status["haproxy"]["version"] else ""
        status["haproxy"]["details"] = f"Active & Running{ver_str}" if is_active else f"Installed (Stopped / Standby){ver_str}"
    else:
        status["haproxy"]["details"] = "Not Installed"

    # 3. Nginx Check
    nginx_bin = shutil.which("nginx")
    if not nginx_bin:
        for p in ("/usr/sbin/nginx", "/sbin/nginx", "/usr/bin/nginx"):
            if os.path.exists(p) and os.access(p, os.X_OK):
                nginx_bin = p
                break

    if nginx_bin:
        status["nginx"]["installed"] = True
        if "nginx" in _VERSION_CACHE:
            status["nginx"]["version"] = _VERSION_CACHE["nginx"]
        else:
            try:
                res_v = subprocess.run([nginx_bin, "-v"], capture_output=True, text=True, timeout=1.0)
                v_out = (res_v.stderr or res_v.stdout or "").strip()
                if "nginx/" in v_out:
                    v_val = v_out.split("nginx/")[1].split()[0]
                    status["nginx"]["version"] = v_val
                    _VERSION_CACHE["nginx"] = v_val
            except Exception:
                pass

        is_active = False
        try:
            res_s = subprocess.run(["systemctl", "is-active", "nginx"], capture_output=True, text=True, timeout=1.0)
            if res_s.returncode == 0 and res_s.stdout.strip() == "active":
                is_active = True
        except Exception:
            pass

        if not is_active:
            try:
                res_p = subprocess.run(["pgrep", "-x", "nginx"], capture_output=True, text=True, timeout=1.0)
                if res_p.returncode == 0 and res_p.stdout.strip():
                    is_active = True
            except Exception:
                pass

        status["nginx"]["active"] = is_active
        ver_str = f" ({status['nginx']['version']})" if status["nginx"]["version"] else ""
        status["nginx"]["details"] = f"Active & Running{ver_str}" if is_active else f"Installed (Stopped / Standby){ver_str}"
    else:
        status["nginx"]["details"] = "Not Installed"

    with _SERVICES_LOCK:
        _SERVICES_CACHE["data"] = status
        _SERVICES_CACHE["expires"] = now + 6.0

    return status


def get_network_interfaces_info(config_loader_fn: Optional[Any] = None) -> Dict[str, Any]:
    """
    Discovers all network interfaces, identifying server WAN IPs and all tunnel/virtual interfaces
    (e.g. ipip, gre, ftcp, awg, wireguard) with real-time ping probes and caching.
    """
    now = time.time()
    with _NET_LOCK:
        if _NET_CACHE["data"] and now < _NET_CACHE["expires"]:
            return _NET_CACHE["data"]

    server_ips: List[Dict[str, Any]] = []
    tunnel_interfaces: List[Dict[str, Any]] = []
    primary_iface = "eth0"

    # 1. Detect primary WAN interface
    cfg_fn = config_loader_fn or load_config
    cfg = cfg_fn()
    cfg_wan = cfg.get("wan_interface", "auto")
    if cfg_wan and cfg_wan != "auto":
        primary_iface = cfg_wan
    elif sys.platform != "win32":
        try:
            out = subprocess.check_output(["ip", "-o", "route", "show", "default"], text=True, stderr=subprocess.DEVNULL).strip()
            parts = out.split()
            if "dev" in parts:
                idx = parts.index("dev")
                if idx + 1 < len(parts):
                    primary_iface = parts[idx + 1]
        except Exception:
            pass

    # 2. Get interface list via ip -j addr show (modern iproute2)
    if_data = []
    if sys.platform != "win32":
        try:
            out = subprocess.check_output(["ip", "-j", "addr", "show"], text=True, stderr=subprocess.DEVNULL)
            if_data = json.loads(out)
        except Exception:
            pass

        # Fallback to ip -o addr show if ip -j failed
        if not if_data:
            try:
                out = subprocess.check_output(["ip", "-o", "addr", "show"], text=True, stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    tokens = line.split()
                    if len(tokens) >= 4:
                        ifname = tokens[1].strip()
                        if is_ignored_interface(ifname):
                            continue
                        family = tokens[2].strip()
                        if family not in ("inet", "inet6"):
                            continue
                        local = ""
                        peer = ""
                        if "peer" in tokens:
                            p_idx = tokens.index("peer")
                            local = tokens[p_idx - 1].split("/")[0]
                            peer = tokens[p_idx + 1].split("/")[0]
                        else:
                            local = tokens[3].split("/")[0]

                        found = next((x for x in if_data if x["ifname"] == ifname), None)
                        if not found:
                            found = {"ifname": ifname, "flags": ["UP"], "operstate": "UP", "addr_info": []}
                            if_data.append(found)
                        found["addr_info"].append({
                            "family": family,
                            "local": local,
                            "address": peer,
                            "scope": "global" if "scope global" in line else "local"
                        })
            except Exception:
                pass

    # Collect known rule destination targets to match unpeered tunnels
    known_targets = []
    for r in cfg.get("rules", []):
        for d in r.get("destinations", []):
            t = str(d.get("target", "")).strip()
            if t and t not in known_targets:
                known_targets.append(t)

    # Process discovered interfaces
    for item in if_data:
        ifname = item.get("ifname", "")
        if is_ignored_interface(ifname):
            continue

        flags = item.get("flags", [])
        is_up = ("UP" in flags) or (item.get("operstate", "").upper() == "UP")
        addr_info = item.get("addr_info", [])

        # Filter and categorize
        if ifname == primary_iface:
            # Server WAN interface IP(s)
            for a in addr_info:
                ip = a.get("local", "")
                family = a.get("family", "")
                scope = a.get("scope", "")
                if ip and scope == "global" and not ip.startswith("fe80:") and not ip.startswith("127."):
                    server_ips.append({
                        "ip": ip,
                        "version": 6 if family == "inet6" else 4,
                        "interface": ifname,
                        "is_primary": True
                    })
        else:
            # Secondary / Tunnel Interface
            local_ip = ""
            peer_ip = ""
            ip_version = 4
            for a in addr_info:
                if a.get("scope") == "global" or not local_ip:
                    local_ip = a.get("local", "")
                    addr = a.get("address", "")
                    if addr and addr != local_ip:
                        peer_ip = addr
                    if a.get("family") == "inet6":
                        ip_version = 6

            # Determine tunnel friendly type
            link_type = item.get("link_type", "")
            lower_name = ifname.lower()
            if "ipip" in lower_name or link_type == "ipip":
                friendly_type = "IPIP Tunnel"
            elif "gre" in lower_name or link_type == "gre":
                friendly_type = "GRE Tunnel"
            elif "ftcp" in lower_name:
                friendly_type = "FakeTCP Tunnel"
            elif "awg" in lower_name:
                friendly_type = "AmneziaWG Tunnel"
            elif "wg" in lower_name or link_type == "wireguard":
                friendly_type = "WireGuard Tunnel"
            elif "tun" in lower_name:
                friendly_type = "L3 Tunnel"
            elif "tap" in lower_name:
                friendly_type = "L2 TAP"
            elif "gnv" in lower_name or "geneve" in link_type:
                friendly_type = "Geneve Tunnel"
            elif "vxlan" in lower_name or "vxlan" in link_type:
                friendly_type = "VXLAN Tunnel"
            else:
                friendly_type = "Virtual / Tunnel"

            # Determine best ping target and peer endpoint
            target_to_ping = peer_ip
            if not target_to_ping and local_ip:
                if ip_version == 4:
                    parts = local_ip.split(".")
                    if len(parts) == 4:
                        prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
                        matched = next((kt for kt in known_targets if kt.startswith(prefix) and kt != local_ip), None)
                        if matched:
                            target_to_ping = matched
                        else:
                            try:
                                last_oct = int(parts[3])
                                if last_oct % 4 == 1:
                                    target_to_ping = f"{prefix}{last_oct + 1}"
                                elif last_oct % 4 == 2:
                                    target_to_ping = f"{prefix}{last_oct - 1}"
                            except ValueError:
                                pass
                elif ip_version == 6:
                    matched = next((kt for kt in known_targets if kt != local_ip and kt.split("::")[0] == local_ip.split("::")[0]), None)
                    if matched:
                        target_to_ping = matched
                    elif local_ip.endswith("::1"):
                        target_to_ping = local_ip[:-1] + "2"
                    elif local_ip.endswith("::2"):
                        target_to_ping = local_ip[:-1] + "1"

            if target_to_ping and not peer_ip:
                peer_ip = target_to_ping

            if not local_ip and not peer_ip and not is_up:
                continue

            tunnel_interfaces.append({
                "name": ifname,
                "ip": local_ip or "No IP assigned",
                "peer_ip": peer_ip,
                "version": ip_version,
                "state": "UP" if is_up else "DOWN",
                "type": friendly_type,
                "mtu": item.get("mtu", 1500),
                "target_to_ping": target_to_ping,
                "reachable": False,
                "latency_ms": None
            })

    # Ping tunnels in parallel (bounded timeout)
    threads = []
    def do_ping(tunnel):
        target = tunnel.get("target_to_ping")
        if target and tunnel.get("state") == "UP":
            ok, lat = ping_target(target, tunnel.get("name"))
            tunnel["reachable"] = ok
            tunnel["latency_ms"] = lat
        else:
            tunnel["reachable"] = False
            tunnel["latency_ms"] = None

    for t_info in tunnel_interfaces:
        th = threading.Thread(target=do_ping, args=(t_info,), daemon=True)
        threads.append(th)
        th.start()

    for th in threads:
        th.join(timeout=1.2)

    if not server_ips:
        try:
            hostname = socket.gethostname()
            host_ips = socket.gethostbyname_ex(hostname)[2]
            for hip in host_ips:
                if not hip.startswith("127.") and not hip.startswith("169.254."):
                    server_ips.append({
                        "ip": hip,
                        "version": 4,
                        "interface": primary_iface,
                        "is_primary": True
                    })
        except Exception:
            pass

    result = {
        "primary_interface": primary_iface,
        "server_ips": server_ips,
        "tunnel_interfaces": tunnel_interfaces,
        "updated_at": now
    }

    with _NET_LOCK:
        _NET_CACHE["data"] = result
        _NET_CACHE["expires"] = now + 20.0  # 20-second cache TTL

    return result

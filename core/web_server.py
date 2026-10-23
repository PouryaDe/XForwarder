#!/usr/bin/env python3
"""
XForwarder - 24/7 Always-Online Web Server
Provides a secure English dashboard with session authentication (Username & Password).
"""

import os
import sys
import time
import json
import hashlib
import hmac
import secrets
import socket
import ssl
import subprocess
import threading
import ipaddress
import re
import shutil
import gzip
import signal
import tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
from typing import Optional, Dict, Tuple, Any, List

_STATIC_CACHE: Dict[str, dict] = {}
_STATIC_LOCK = threading.Lock()
_VERSION_CACHE: Dict[str, str] = {}

PID_FILE_CANDIDATES = [
    "/run/xforwarder/engine.pid",
    "/run/forward-manager/engine.pid",
    os.path.join(tempfile.gettempdir(), "xforwarder_engine.pid"),
]


def notify_engine_wakeup():
    """Signals core engine to immediately evaluate routing changes without waiting for interval."""
    if hasattr(signal, "SIGUSR1"):
        for pid_file in PID_FILE_CANDIDATES:
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, "r", encoding="utf-8") as f:
                        pid = int(f.read().strip())
                    os.kill(pid, signal.SIGUSR1)
                    break
                except Exception:
                    pass


def sync_rules_and_notify(max_retries: int = 2) -> Tuple[bool, List[str]]:
    try:
        from engine import sync_system_rules
    except ImportError:
        from core.engine import sync_system_rules
    res = sync_system_rules(max_retries=max_retries)
    notify_engine_wakeup()
    return res



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

WEB_DIR = os.path.join(BASE_DIR, "web")
CONFIG_PATH = "/etc/xforwarder/config.json"
LEGACY_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
STATE_FILE_PATH = "/run/xforwarder/state.json"
LEGACY_STATE_FILE_PATH = "/run/forward-manager/state.json"

ACTIVE_SESSIONS: Dict[str, dict] = {}
SESSION_LOCK = threading.Lock()
SESSION_TTL_HOURS = 24
SESSION_IDLE_TIMEOUT_SECONDS = 14400  # 4 hours idle limit
MAX_ACTIVE_SESSIONS = 50


def get_sessions_file_path() -> str:
    """Returns persistent sessions storage path in /run/xforwarder or system temp."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "sessions.json")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/sessions.json"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_sessions.json")


def load_sessions_from_disk():
    """Loads active, unexpired sessions from disk to survive daemon restarts."""
    path = get_sessions_file_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            now = time.time()
            valid = {}
            for tok, sess in data.items():
                if isinstance(sess, dict) and sess.get("expires_at", 0) > now:
                    valid[tok] = sess
            with SESSION_LOCK:
                ACTIVE_SESSIONS.update(valid)
    except Exception:
        pass


def save_sessions_to_disk():
    """Atomically persists active sessions to disk."""
    path = get_sessions_file_path()
    now = time.time()
    with SESSION_LOCK:
        data_to_save = {k: v for k, v in ACTIVE_SESSIONS.items() if v.get("expires_at", 0) > now}
    try:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f)
        os.replace(tmp, path)
    except Exception:
        pass


# Restore sessions on startup
load_sessions_from_disk()

# Rate Limiting & Brute-Force Shield State
FAILED_LOGIN_ATTEMPTS: Dict[str, dict] = {}
RATE_LIMIT_LOCK = threading.Lock()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes lockout
WINDOW_DURATION = 300   # 5 minutes failure evaluation window

try:
    from engine import XForwarderEngine
    migrate_config = XForwarderEngine.migrate_and_normalize_config
except ImportError:
    try:
        from core.engine import XForwarderEngine
        migrate_config = XForwarderEngine.migrate_and_normalize_config
    except ImportError:
        migrate_config = None


def get_config_path() -> str:
    env_override = os.environ.get("XFWD_CONFIG_PATH")
    if env_override:
        return env_override
    if os.path.exists(CONFIG_PATH):
        return CONFIG_PATH
    if os.path.exists(LEGACY_CONFIG_PATH):
        return LEGACY_CONFIG_PATH
    if os.path.exists(LOCAL_CONFIG_PATH):
        return LOCAL_CONFIG_PATH
    return CONFIG_PATH


def load_config() -> dict:
    path = get_config_path()
    cfg = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    if not isinstance(cfg, dict):
        cfg = {
            "schema_version": 2,
            "wan_interface": "auto",
            "check_interval_seconds": 8,
            "failure_threshold": 3,
            "recovery_threshold": 3,
            "web": {
                "bind_host": "0.0.0.0",
                "port": 8090,
                "secret_path": "xfwd-admin",
                "auth": {
                    "username": "admin",
                    "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918" # admin
                }
            },
            "rules": []
        }
    if migrate_config:
        cfg, modified = migrate_config(cfg)
        if modified and os.path.exists(path):
            save_config(cfg)
    return cfg


def save_config(cfg: dict) -> bool:
    path = get_config_path()
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}", file=sys.stderr)
        return False


def export_config_data(cfg: dict = None) -> dict:
    """Returns a sanitized export representation of the configuration, omitting sensitive credentials."""
    if cfg is None:
        cfg = load_config()
    return {
        "_comment": "XForwarder Configuration Backup",
        "exported_at": int(time.time()),
        "version": cfg.get("schema_version", 2),
        "wan_interface": cfg.get("wan_interface", "auto"),
        "check_interval_seconds": cfg.get("check_interval_seconds", 8),
        "failure_threshold": cfg.get("failure_threshold", 3),
        "recovery_threshold": cfg.get("recovery_threshold", 3),
        "fast_failover_enabled": cfg.get("fast_failover_enabled", True),
        "max_acceptable_loss": cfg.get("max_acceptable_loss", 25),
        "cooldown_seconds": cfg.get("cooldown_seconds", 60),
        "hysteresis_percent": cfg.get("hysteresis_percent", 10),
        "loss_penalty_weight": cfg.get("loss_penalty_weight", 10),
        "fast_probe_burst": cfg.get("fast_probe_burst", 3),
        "rules": cfg.get("rules", [])
    }


def import_config_data(imported_raw, mode: str = "merge") -> tuple:
    """Validates, migrates, backs up, and applies an imported configuration dictionary or rules list.
    Returns (success: bool, error_msg: str, info_dict: dict).
    """
    if mode not in ("merge", "replace"):
        mode = "merge"

    # Support raw rules array as valid import payload
    if isinstance(imported_raw, list):
        imported_raw = {"rules": imported_raw}
    elif not isinstance(imported_raw, dict):
        return False, "Invalid configuration payload. Must be a JSON object or rules array.", {}

    if migrate_config:
        imported_cfg, _ = migrate_config(imported_raw)
    else:
        imported_cfg = imported_raw

    imported_rules = imported_cfg.get("rules", [])
    if not isinstance(imported_rules, list):
        return False, "'rules' property must be a list", {}

    current_cfg = load_config()
    web_port = current_cfg.get("web", {}).get("port", 8090)

    validated_rules = []
    seen_ports = set()
    for r in imported_rules:
        if not isinstance(r, dict):
            continue
        try:
            port = int(r.get("port", 0))
        except (ValueError, TypeError):
            continue
        if port <= 0 or port > 65535:
            return False, f"Invalid port number: {port}", {}
        if port == web_port:
            return False, f"Port {port} is reserved for the XForwarder Web Dashboard", {}
        if port in seen_ports:
            return False, f"Duplicate port {port} found in imported rules", {}
        seen_ports.add(port)

        # Ensure consistent rule ID and initial priority
        if not r.get("id"):
            r["id"] = f"rule-{port}"
        if "active_priority" not in r:
            r["active_priority"] = 1

        valid, err = validate_rule(r)
        if not valid:
            return False, f"Rule for port {port} is invalid: {err}", {}
        validated_rules.append(r)

    # Atomic Pre-Update Backup
    cfg_path = get_config_path()
    bak_path = f"{cfg_path}.bak.{int(time.time())}"
    try:
        bak_tmp = f"{bak_path}.tmp.{os.getpid()}"
        with open(bak_tmp, "w", encoding="utf-8") as bf:
            json.dump(current_cfg, bf, indent=2, ensure_ascii=False)
        os.replace(bak_tmp, bak_path)
    except Exception as e:
        print(f"[WARN] Failed to write pre-import backup {bak_path}: {e}", file=sys.stderr)

    if mode == "replace":
        current_cfg["rules"] = validated_rules
        if "wan_interface" in imported_cfg and imported_cfg["wan_interface"]:
            current_cfg["wan_interface"] = imported_cfg["wan_interface"]
        for param in ("check_interval_seconds", "failure_threshold", "recovery_threshold",
                      "fast_failover_enabled", "max_acceptable_loss", "cooldown_seconds",
                      "hysteresis_percent", "loss_penalty_weight", "fast_probe_burst"):
            if param in imported_cfg:
                current_cfg[param] = imported_cfg[param]
    else:  # merge
        current_rules = current_cfg.get("rules", [])
        rules_map = {r.get("port"): r for r in current_rules if isinstance(r, dict)}
        for vr in validated_rules:
            rules_map[vr["port"]] = vr
        current_cfg["rules"] = list(rules_map.values())

    if save_config(current_cfg):
        return True, "", {
            "mode": mode,
            "count": len(current_cfg.get("rules", [])),
            "imported_count": len(validated_rules),
            "backup": os.path.basename(bak_path)
        }
    return False, "Failed to save configuration", {}



def load_state() -> dict:
    for path in [STATE_FILE_PATH, LEGACY_STATE_FILE_PATH]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def update_state_rules(rule_updates: Dict[str, dict]) -> None:
    """Synchronizes active_priority and force_override in state.json atomically."""
    for path in [STATE_FILE_PATH, LEGACY_STATE_FILE_PATH]:
        s_dir = os.path.dirname(path)
        if not os.path.exists(path) and not os.path.exists(s_dir):
            continue
        try:
            st = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    st = json.load(f)
            if not isinstance(st, dict):
                st = {}
            rt = st.setdefault("runtime", {})
            rs = rt.setdefault("rules_state", {})
            for r_id, vals in rule_updates.items():
                r_entry = rs.setdefault(r_id, {})
                r_entry.update(vals)
            tmp_p = f"{path}.tmp.{os.getpid()}"
            with open(tmp_p, "w", encoding="utf-8") as tf:
                json.dump(st, tf, indent=2, ensure_ascii=False)
            os.replace(tmp_p, path)
            break
        except Exception:
            pass


_PREV_NET_IO: Dict[str, Any] = {"rx": 0, "tx": 0, "time": 0.0}
_NET_IO_LOCK = threading.Lock()


def get_system_stats() -> dict:
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
                    # Live speed in MB/s (Megabytes per second)
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


_SERVICES_CACHE: Dict[str, Any] = {"data": None, "expires": 0}
_SERVICES_LOCK = threading.Lock()


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
                if "xfwd_orchestrator" in res_t.stdout or "fwdman_orchestrator" in res_t.stdout:
                    status["nftables"]["table_active"] = True
                    status["nftables"]["details"] = "Active (table ip/ip6 xfwd_orchestrator loaded)"
                else:
                    status["nftables"]["details"] = "Kernel Ready (No active ruleset yet)"
            else:
                status["nftables"]["details"] = "Installed (Kernel module inactive or permission denied)"
        except Exception:
            status["nftables"]["details"] = "Installed (Check error)"
    else:
        status["nftables"]["details"] = "Not Installed"

    # 2. HAProxy Check
    haproxy_bin = shutil.which("haproxy")
    if not haproxy_bin:
        for p in ("/usr/sbin/haproxy", "/usr/bin/haproxy"):
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
                    line = res_v.stdout.strip().split("\n")[0]
                    if "version" in line:
                        v_val = line.split("version")[1].strip().split()[0]
                        status["haproxy"]["version"] = v_val
                        _VERSION_CACHE["haproxy"] = v_val
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
        for p in ("/usr/sbin/nginx", "/usr/bin/nginx"):
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
                v_text = (res_v.stderr or res_v.stdout or "").strip()
                if "nginx/" in v_text:
                    v_val = v_text.split("nginx/")[1].strip().split()[0]
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


# ── System Version & Automated Update Subsystem ──

APP_VERSION = "1.3.1"
_REMOTE_VERSION_CACHE: Dict[str, Any] = {"data": None, "expires": 0}
_REMOTE_VERSION_LOCK = threading.Lock()

_UPDATE_STATE: Dict[str, Any] = {
    "status": "idle",  # "idle", "running", "completed", "failed"
    "start_time": 0.0,
    "pid": None,
    "error": None
}
_UPDATE_LOCK = threading.Lock()


def get_update_state_file_path() -> str:
    """Returns persistent update state file path in /run/xforwarder or system temp."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "update_state.json")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/update_state.json"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_update_state.json")


def save_update_state(state: dict):
    """Atomically persists update progress state to disk."""
    path = get_update_state_file_path()
    try:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except Exception:
        pass


def load_update_state():
    """Loads update progress state across daemon reloads."""
    path = get_update_state_file_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                with _UPDATE_LOCK:
                    _UPDATE_STATE.update(data)
        except Exception:
            pass


load_update_state()


def get_installed_version() -> str:
    """Reads script version from xforwarder.sh or returns default APP_VERSION."""
    script_candidates = [
        "/opt/xforwarder/xforwarder.sh",
        os.path.join(BASE_DIR, "xforwarder.sh"),
        "/usr/local/bin/xforwarder"
    ]
    for s in script_candidates:
        if os.path.exists(s):
            try:
                with open(s, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("SCRIPT_VERSION="):
                            v = line.split("=")[1].strip().strip('"').strip("'")
                            if v:
                                return v
            except Exception:
                pass
    return APP_VERSION


def get_local_version_info() -> dict:
    """Inspects local git repository, .commit metadata files, or installed package version."""
    version = get_installed_version()
    info = {
        "version": version,
        "commit": None,
        "commit_date": None,
        "is_git": False
    }

    # 1. Read persistent metadata written during xforwarder install/update
    commit_file_candidates = [
        os.path.join(BASE_DIR, ".commit"),
        "/opt/xforwarder/.commit",
        "/etc/xforwarder/.commit",
    ]
    for c_path in commit_file_candidates:
        if os.path.isfile(c_path):
            try:
                with open(c_path, "r", encoding="utf-8", errors="replace") as f:
                    c_val = f.read().strip()
                if c_val:
                    info["commit"] = c_val[:7]
                    d_path = c_path.replace(".commit", ".commit_date")
                    if os.path.isfile(d_path):
                        with open(d_path, "r", encoding="utf-8", errors="replace") as df:
                            info["commit_date"] = df.read().strip()
                    break
            except Exception:
                pass

    # 2. Check local git repositories if commit not determined yet or for active git checkouts
    git_dirs = [
        BASE_DIR,
        "/opt/xforwarder",
        os.path.join(os.path.dirname(BASE_DIR), "XForwarder"),
        os.path.join(os.path.dirname(BASE_DIR), "Forward-Manager"),
        "/root/XForwarder",
        "/root/Forward-Manager",
    ]
    for g_dir in git_dirs:
        if os.path.isdir(os.path.join(g_dir, ".git")):
            try:
                res = subprocess.run(
                    ["git", "-C", g_dir, "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=2.0
                )
                if res.returncode == 0 and res.stdout.strip():
                    info["commit"] = res.stdout.strip()
                    info["is_git"] = True
                    res_date = subprocess.run(
                        ["git", "-C", g_dir, "log", "-1", "--format=%cd", "--date=short"],
                        capture_output=True, text=True, timeout=2.0
                    )
                    if res_date.returncode == 0 and res_date.stdout.strip():
                        info["commit_date"] = res_date.stdout.strip()
                    break
            except Exception:
                pass

    return info


def get_remote_version_info(force: bool = False) -> dict:
    """Checks remote GitHub repository for the latest commit on main.
    Uses GitHub REST API with an automatic zero-quota git ls-remote fallback
    to prevent HTTP 403 Rate Limit Exceeded errors on public/shared IPs.
    """
    now = time.time()
    with _REMOTE_VERSION_LOCK:
        if not force and _REMOTE_VERSION_CACHE["data"] and now < _REMOTE_VERSION_CACHE["expires"]:
            return _REMOTE_VERSION_CACHE["data"]

    remote = {
        "remote_commit": None,
        "remote_commit_msg": None,
        "remote_date": None,
        "repo_url": "https://github.com/PouryaDe/XForwarder",
        "checked_at": int(now),
        "error": None
    }

    api_success = False
    url = "https://api.github.com/repos/PouryaDe/XForwarder/commits/main"
    headers = {
        "User-Agent": "XForwarder-Updater/1.0",
        "Accept": "application/vnd.github.v3+json"
    }
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token.strip()}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw)
                sha = body.get("sha", "")
                remote["remote_commit"] = sha[:7] if sha else None
                commit_info = body.get("commit", {})
                msg = commit_info.get("message", "").strip().split("\n")[0]
                remote["remote_commit_msg"] = msg
                author_date = commit_info.get("author", {}).get("date") or commit_info.get("committer", {}).get("date", "")
                if author_date:
                    remote["remote_date"] = author_date[:10]
                api_success = True
    except Exception as e:
        remote["error"] = str(e)

    # Resilient fallback: If GitHub REST API is rate-limited (HTTP 403) or unreachable,
    # use Git Smart HTTP (git ls-remote) which has ZERO REST quota restrictions.
    if not api_success:
        try:
            res = subprocess.run(
                ["git", "ls-remote", "https://github.com/PouryaDe/XForwarder.git", "refs/heads/main"],
                capture_output=True, text=True, timeout=5.0
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split()
                if parts and len(parts[0]) >= 7:
                    remote["remote_commit"] = parts[0][:7]
                    remote["remote_commit_msg"] = "Latest release on main"
                    remote["error"] = None  # Clear error since git ls-remote succeeded
                    api_success = True
        except Exception:
            pass

    with _REMOTE_VERSION_LOCK:
        _REMOTE_VERSION_CACHE["data"] = remote
        _REMOTE_VERSION_CACHE["expires"] = now + (180.0 if api_success else 30.0)

    return remote


def get_full_version_status(force: bool = False) -> dict:
    """Returns composite version status comparing local and remote GitHub states."""
    local_info = get_local_version_info()
    remote_info = get_remote_version_info(force=force)

    update_available = False
    local_commit = (local_info.get("commit") or "").lower()
    remote_commit = (remote_info.get("remote_commit") or "").lower()

    if remote_commit:
        if local_commit:
            if local_commit != remote_commit:
                update_available = True
        else:
            # If local commit is unrecorded on server, compare versions or suggest update
            update_available = True

    return {
        "ok": True,
        "current_version": local_info["version"],
        "current_commit": local_info["commit"],
        "current_date": local_info["commit_date"],
        "is_git": local_info["is_git"],
        "remote_commit": remote_info.get("remote_commit"),
        "remote_commit_msg": remote_info.get("remote_commit_msg"),
        "remote_date": remote_info.get("remote_date"),
        "repo_url": remote_info.get("repo_url"),
        "checked_at": remote_info.get("checked_at"),
        "update_available": update_available,
        "check_error": remote_info.get("error")
    }


def get_update_log_path() -> str:
    """Resolves path to update log file in /run/xforwarder or system tempdir."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "update.log")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/update.log"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_update.log")


def get_script_path() -> Optional[str]:
    """Finds executable xforwarder.sh on host."""
    candidates = [
        "/opt/xforwarder/xforwarder.sh",
        os.path.join(BASE_DIR, "xforwarder.sh"),
        "/usr/local/bin/xforwarder",
        "/usr/local/bin/xfwd"
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def start_system_update() -> Tuple[bool, str]:
    """
    Triggers an unattended background update via systemd-run or detached process.
    Prevents cgroup termination when xforwarder-web is reloaded.
    """
    with _UPDATE_LOCK:
        now = time.time()
        if _UPDATE_STATE["status"] == "running" and (now - _UPDATE_STATE["start_time"]) < 180:
            return False, "An update is already in progress"

        script = get_script_path()
        if not script:
            return False, "XForwarder update script (xforwarder.sh) not found on host"

        log_path = get_update_log_path()
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== XForwarder Update Initiated at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.flush()
        except Exception as e:
            return False, f"Failed to initialize update log: {e}"

        _UPDATE_STATE["status"] = "running"
        _UPDATE_STATE["start_time"] = now
        _UPDATE_STATE["error"] = None
        save_update_state(_UPDATE_STATE)

        has_systemd_run = bool(shutil.which("systemd-run"))
        ts = int(now)

        def _worker():
            try:
                cmd_str = f"DEBIAN_FRONTEND=noninteractive bash '{script}' update >> '{log_path}' 2>&1"
                if has_systemd_run:
                    unit_name = f"xfwd-updater-{ts}"
                    run_cmd = [
                        "systemd-run",
                        f"--unit={unit_name}",
                        "--description=XForwarder Web Update",
                        "bash", "-c", cmd_str
                    ]
                    res = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10.0)
                    if res.returncode != 0:
                        subprocess.Popen(["bash", "-c", cmd_str], start_new_session=True)
                else:
                    if sys.platform == "win32":
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write("[OK] XForwarder updated successfully! All services are active and running.\n")
                        with _UPDATE_LOCK:
                            _UPDATE_STATE["status"] = "completed"
                            save_update_state(_UPDATE_STATE)
                    else:
                        subprocess.Popen(["bash", "-c", cmd_str], start_new_session=True)
            except Exception as ex:
                with _UPDATE_LOCK:
                    _UPDATE_STATE["status"] = "failed"
                    _UPDATE_STATE["error"] = str(ex)
                    save_update_state(_UPDATE_STATE)
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n[ERROR] Update runner failure: {ex}\n")
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return True, "Update initiated"


def get_update_status() -> dict:
    """Returns current update execution state and sanitized log output."""
    log_path = get_update_log_path()
    raw_log = ""
    mtime = 0.0
    if os.path.exists(log_path):
        try:
            mtime = os.path.getmtime(log_path)
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                raw_log = f.read()
        except Exception:
            pass

    clean_log = re.sub(r'\x1b\[[0-9;]*m', '', raw_log)
    now = time.time()

    with _UPDATE_LOCK:
        mem_status = _UPDATE_STATE["status"]
        start_time = _UPDATE_STATE["start_time"]

    status = "idle"
    # Consider completed only if finished within recent 180s or part of this active session
    is_recent_success = "XForwarder updated successfully!" in clean_log and (
        (start_time > 0 and mtime >= start_time - 5) or (mtime > 0 and (now - mtime) < 180)
    )
    if is_recent_success:
        status = "completed"
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "completed"
            save_update_state(_UPDATE_STATE)
    elif mem_status == "running":
        if (now - start_time) > 300:
            status = "failed"
            with _UPDATE_LOCK:
                _UPDATE_STATE["status"] = "failed"
                save_update_state(_UPDATE_STATE)
        else:
            status = "running"
    elif mtime > 0 and (now - mtime) < 45 and (start_time == 0 or (now - start_time) < 300):
        status = "running"
    elif ("Could not pull updates" in clean_log or "Failed to install" in clean_log or "[ERROR]" in clean_log) and (
        (start_time > 0 and mtime >= start_time - 5) or (mtime > 0 and (now - mtime) < 180)
    ):
        status = "failed"
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "failed"
            save_update_state(_UPDATE_STATE)
    else:
        status = "idle"

    return {
        "ok": True,
        "status": status,
        "log": clean_log,
        "updated_at": mtime
    }


def restart_services_action(service: str) -> Tuple[bool, str, bool]:
    """
    Executes controlled service restart or reload.
    Supports: 'all', 'engine', 'web', 'haproxy', 'nginx', 'nftables'.
    Returns: (success: bool, message: str, is_reconnecting: bool)
    """
    valid_services = {"all", "engine", "web", "haproxy", "nginx", "nftables"}
    svc = str(service or "all").lower().strip()
    if svc not in valid_services:
        return False, f"Invalid service identifier '{service}'. Allowed: {', '.join(sorted(valid_services))}", False

    has_systemctl = bool(shutil.which("systemctl"))
    if sys.platform == "win32" or not has_systemctl:
        if svc in ("all", "web"):
            return True, f"Service '{svc}' restarted (mock)", True
        elif svc == "nftables":
            sync_rules_and_notify()
            return True, "NFTables ruleset synchronized (mock)", False
        return True, f"Service '{svc}' reloaded successfully (mock)", False

    if svc == "nftables":
        ok, errs = sync_rules_and_notify()
        if ok:
            return True, "NFTables table 'xfwd_orchestrator' re-synchronized successfully", False
        return False, f"Failed to synchronize NFTables: {', '.join(errs)}", False

    if svc == "haproxy":
        res = subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "HAProxy relay service reloaded successfully", False
        return False, f"HAProxy reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "nginx":
        res = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "Nginx stream proxy engine reloaded successfully", False
        return False, f"Nginx reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "engine":
        svc_name = "xforwarder.service"
        res = subprocess.run(["systemctl", "restart", svc_name], capture_output=True, text=True, timeout=10.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "forward-manager.service"], capture_output=True, text=True, timeout=10.0)
        if res.returncode == 0:
            notify_engine_wakeup()
            return True, "XForwarder Core Failover Engine restarted successfully", False
        return False, f"Failed to restart core engine: {res.stderr.strip() or res.stdout.strip()}", False

    if svc in ("web", "all"):
        if svc == "all":
            subprocess.run(["systemctl", "restart", "xforwarder.service"], capture_output=True, timeout=5.0)
            subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, timeout=5.0)
            subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, timeout=5.0)

        def _delayed_web_restart():
            time.sleep(0.6)
            if shutil.which("systemd-run"):
                subprocess.run(
                    ["systemd-run", "--unit=xfwd-restart-job", "systemctl", "restart", "xforwarder-web.service"],
                    capture_output=True
                )
            else:
                subprocess.run(["systemctl", "restart", "xforwarder-web.service"], capture_output=True)

        threading.Thread(target=_delayed_web_restart, daemon=True).start()
        msg = "All XForwarder services are restarting" if svc == "all" else "Web Dashboard service is restarting"
        return True, f"{msg}. Reconnecting in ~2 seconds...", True

    return False, "Unknown action", False


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


def get_network_interfaces_info() -> Dict[str, Any]:
    """
    Discovers all network interfaces, identifying server WAN IPs and all tunnel/virtual interfaces
    (e.g. ipip, gre, ftcp, awg, wireguard) with real-time ping probes and caching.
    """
    global _NET_CACHE
    now = time.time()
    with _NET_LOCK:
        if _NET_CACHE["data"] and now < _NET_CACHE["expires"]:
            return _NET_CACHE["data"]

    server_ips: List[Dict[str, Any]] = []
    tunnel_interfaces: List[Dict[str, Any]] = []
    primary_iface = "eth0"

    # 1. Detect primary WAN interface
    cfg = load_config()
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

            # Determine best ping target and peer endpoint:
            # 1. Explicit kernel peer IP (addr_info address / peer)
            # 2. Configured destination target matching same /24 subnet
            # 3. Bilateral point-to-point tunnel convention (.1 <-> .2 and standard /30 pairs)
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

            # Skip unconfigured inactive interfaces with no IP and state DOWN
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

    # Fallback if no server IPs detected (e.g. local dev environment)
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


PBKDF2_ITERATIONS = 100000


def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    """Generates a secure PBKDF2-HMAC-SHA256 salted password hash."""
    if not salt_hex:
        salt_hex = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt_hex}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> Tuple[bool, bool]:
    """
    Verifies password against stored hash using constant-time comparison.
    Returns: (is_valid, needs_rehash)
    Backward compatible with legacy SHA-256 with automatic seamless upgrade to PBKDF2.
    """
    if not stored_hash or not password or not isinstance(password, str):
        return False, False

    # Modern salted PBKDF2-HMAC-SHA256 format
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) == 3:
                header, salt_hex, expected_hex = parts
                iters = int(header.split(":")[-1])
                salt_bytes = bytes.fromhex(salt_hex)
                derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iters)
                return hmac.compare_digest(derived.hex(), expected_hex), False
        except Exception:
            return False, False

    # Legacy plain SHA-256 hash (64 hex characters)
    legacy_test = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hmac.compare_digest(legacy_test, stored_hash):
        return True, True  # Valid, but triggers self-healing upgrade to salted PBKDF2!

    return False, False


def check_rate_limit(client_ip: str) -> Tuple[bool, int, int]:
    """Checks if client IP is currently rate-limited. Returns (is_locked, remaining_seconds, fail_count)."""
    now = time.time()
    with RATE_LIMIT_LOCK:
        record = FAILED_LOGIN_ATTEMPTS.get(client_ip)
        if not record:
            return False, 0, 0

        lockout_until = record.get("lockout_until", 0)
        if now < lockout_until:
            remaining = int(lockout_until - now)
            return True, remaining, record.get("count", 0)

        # If evaluation window expired and not locked out, clear record
        if now > record.get("first_attempt", 0) + WINDOW_DURATION:
            FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)
            return False, 0, 0

        return False, 0, record.get("count", 0)


def record_failed_login(client_ip: str) -> Tuple[bool, int, int]:
    """Records a failed login attempt and calculates lockout status."""
    now = time.time()
    with RATE_LIMIT_LOCK:
        record = FAILED_LOGIN_ATTEMPTS.get(client_ip)
        if not record or now > record.get("first_attempt", 0) + WINDOW_DURATION:
            record = {"count": 1, "first_attempt": now, "lockout_until": 0}
        else:
            record["count"] += 1

        is_locked = False
        remaining = 0
        if record["count"] >= MAX_FAILED_ATTEMPTS:
            record["lockout_until"] = now + LOCKOUT_DURATION
            is_locked = True
            remaining = LOCKOUT_DURATION

        FAILED_LOGIN_ATTEMPTS[client_ip] = record

        # Prune expired entries if dict is growing
        if len(FAILED_LOGIN_ATTEMPTS) > 100:
            stale = [k for k, v in FAILED_LOGIN_ATTEMPTS.items() if now > v.get("lockout_until", 0) and now > v.get("first_attempt", 0) + WINDOW_DURATION]
            for k in stale:
                FAILED_LOGIN_ATTEMPTS.pop(k, None)

        return is_locked, remaining, record["count"]


def reset_rate_limit(client_ip: str):
    """Clears failed login counter on successful authentication."""
    with RATE_LIMIT_LOCK:
        FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)


HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def is_valid_target(target: str) -> bool:
    """Strictly validates if a destination target is a valid IPv4, IPv6, or RFC hostname."""
    clean = target.strip().strip("[]")
    if not clean:
        return False
    # Check IPv4 or IPv6
    try:
        ipaddress.ip_address(clean)
        return True
    except ValueError:
        pass

    # If it is an all-numeric dotted quad that failed IP validation, it is invalid
    parts = clean.split(".")
    if all(p.isdigit() for p in parts):
        return False

    # Check RFC hostname (TLD cannot be purely numeric per RFC 3696)
    if HOSTNAME_REGEX.match(clean):
        if len(parts) > 1 and parts[-1].isdigit():
            return False
        return True
    return False


def validate_rule(body: dict) -> Tuple[bool, str]:
    if not isinstance(body, dict):
        return False, "Invalid JSON body"

    port = body.get("port")
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535"
        body["port"] = port
    except (ValueError, TypeError):
        return False, "Port must be a valid integer"

    proto = str(body.get("protocol", "both")).lower()
    if proto not in ("tcp", "udp", "both"):
        return False, "Protocol must be 'tcp', 'udp', or 'both'"
    body["protocol"] = proto

    # Normalize and sanitize category (optional group name, max 48 chars, reject shell/injection chars)
    category = str(body.get("category", "") or "").strip()
    if len(category) > 48:
        return False, "Category name must not exceed 48 characters"
    if any(c in category for c in "<>\";`$\\") or any(ord(c) < 32 for c in category):
        return False, "Category name contains invalid characters"
    body["category"] = category

    # Sanitize created_at timestamp with NaN, Inf, and boundary protection
    try:
        created_at = float(body.get("created_at", 0))
        if created_at != created_at or created_at < 0 or created_at > 4102444800 or abs(created_at) == float("inf"):
            created_at = 0.0
    except (ValueError, TypeError):
        created_at = 0.0
    body["created_at"] = created_at

    dests = body.get("destinations", [])
    if not isinstance(dests, list) or len(dests) == 0:
        return False, "At least one destination is required"

    for d in dests:
        if not isinstance(d, dict):
            return False, "Invalid destination item"
        target = str(d.get("target", "")).strip()
        if not target:
            return False, "Destination target cannot be empty"

        # Disallow control characters or shell injection hazards
        if any(c in target for c in ";&|`$ \t\n\r<>\"'"):
            return False, "Destination target contains invalid characters"

        if not is_valid_target(target):
            return False, f"Invalid destination target '{target}'. Must be a valid IPv4, IPv6, or hostname"

        d_type = str(d.get("type", "")).lower().strip()
        if not d_type:
            clean_t = target.strip("[]")
            if ":" in clean_t:
                d_type = "haproxy"
            elif clean_t.startswith("10.") or clean_t.startswith("192.168.") or clean_t.startswith("172."):
                d_type = "nftables"
            else:
                d_type = "nginx"
            d["type"] = d_type
        elif d_type not in ("haproxy", "nftables", "nginx"):
            return False, "Destination type must be 'haproxy', 'nftables', or 'nginx'"
        d["type"] = d_type

        if d_type == "haproxy":
            clean_target = target.strip("[]")
            try:
                ip_obj = ipaddress.ip_address(clean_target)
                if ip_obj.version != 6:
                    return False, f"HAProxy destination target must be a valid IPv6 address (got IPv4 '{target}')"
            except ValueError:
                return False, f"HAProxy destination target must be a valid IPv6 address (got '{target}')"

        d_port = d.get("port", port)
        try:
            d_port = int(d_port)
            if d_port < 1 or d_port > 65535:
                return False, "Destination port must be between 1 and 65535"
            d["port"] = d_port
        except (ValueError, TypeError):
            return False, "Destination port must be a valid integer"

        prio = d.get("priority", 1)
        try:
            prio = int(prio)
            if prio < 1:
                return False, "Destination priority must be 1 or greater"
            d["priority"] = prio
        except (ValueError, TypeError):
            return False, "Destination priority must be a valid integer"

    return True, ""


def is_haproxy_listening(port: int) -> bool:
    """Returns True if the process currently listening on port is HAProxy (which XForwarder manages)."""
    try:
        res = subprocess.run(["ss", "-tlpn", f"sport = :{port}"], capture_output=True, text=True, timeout=1.0)
        if "haproxy" in res.stdout.lower():
            return True
    except Exception:
        pass
    return False


def is_nginx_listening(port: int) -> bool:
    """Returns True if the process currently listening on port is Nginx (which XForwarder manages)."""
    try:
        res = subprocess.run(["ss", "-tlpn", f"sport = :{port}"], capture_output=True, text=True, timeout=1.0)
        if "nginx" in res.stdout.lower():
            return True
    except Exception:
        pass
    return False


def is_port_in_use_by_external_service(port: int, current_rule_id: str, existing_rules: list) -> bool:
    """Checks if a port is actively bound by an external non-managed process not managed by this rule."""
    for r in existing_rules:
        if r.get("id") == current_rule_id and r.get("port") == port:
            return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                # If connected, check if it's managed by XForwarder (HAProxy or Nginx)
                if is_haproxy_listening(port) or is_nginx_listening(port):
                    return False
                return True
    except Exception:
        pass
    return False


class XForwarderWebHandler(BaseHTTPRequestHandler):
    server_instance: 'XForwarderWebServer'
    server_version = "XForwarder-Shield/2.0"
    sys_version = ""

    def apply_security_headers(self, cookie_token: Optional[str] = None, include_cache_control: bool = True):
        """Applies comprehensive OWASP recommended security headers."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        )
        if include_cache_control:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")

        is_https = self.headers.get("X-Forwarded-Proto") == "https" or (
            hasattr(self, "server_instance") and getattr(self.server_instance, "is_ssl", False)
        )
        secure_flag = "; Secure" if is_https else ""

        if is_https:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        if cookie_token:
            self.send_header("Set-Cookie", f"xfwd_session={cookie_token}; Path=/; HttpOnly; SameSite=Strict{secure_flag}")
        elif cookie_token == "":
            self.send_header("Set-Cookie", f"xfwd_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Strict{secure_flag}")
            self.send_header("Set-Cookie", f"fwdman_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Strict{secure_flag}")

    def send_json(self, data: dict, status: int = 200, cookie_token: Optional[str] = None):
        body = json.dumps(data).encode("utf-8")
        accept_encoding = self.headers.get("Accept-Encoding", "")
        use_gzip = "gzip" in accept_encoding and len(body) > 512
        if use_gzip:
            body = gzip.compress(body)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        if status == 429 and isinstance(data, dict) and "remaining_seconds" in data:
            self.send_header("Retry-After", str(data["remaining_seconds"]))
        self.apply_security_headers(cookie_token=cookie_token)
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path: str, content_type: str):
        if not os.path.exists(file_path):
            self.send_error(404, "File Not Found")
            return

        stat = os.stat(file_path)
        mtime = int(stat.st_mtime)
        size = stat.st_size
        etag = f'W/"{mtime}-{size}"'

        # Conditional request (ETag / 304 Not Modified)
        if_none_match = self.headers.get("If-None-Match", "").strip()
        if if_none_match and if_none_match == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.apply_security_headers(include_cache_control=False)
            self.end_headers()
            return

        # In-memory cached asset retrieval
        with _STATIC_LOCK:
            entry = _STATIC_CACHE.get(file_path)
            if not entry or entry["mtime"] != mtime:
                with open(file_path, "rb") as f:
                    raw_content = f.read()
                gz_content = gzip.compress(raw_content) if len(raw_content) > 512 else None
                entry = {
                    "mtime": mtime,
                    "etag": etag,
                    "content": raw_content,
                    "gz_content": gz_content
                }
                _STATIC_CACHE[file_path] = entry

        accept_encoding = self.headers.get("Accept-Encoding", "")
        can_gzip = "gzip" in accept_encoding and entry["gz_content"] is not None

        content = entry["gz_content"] if can_gzip else entry["content"]

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if can_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.apply_security_headers(include_cache_control=False)
        self.end_headers()
        self.wfile.write(content)

    def get_client_ip(self) -> str:
        """Extracts remote client IP with reverse-proxy support."""
        cf_ip = self.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()
        xfwd = self.headers.get("X-Forwarded-For")
        if xfwd:
            return xfwd.split(",")[0].strip()
        return self.client_address[0]

    def check_origin(self) -> bool:
        """Validates Origin/Referer headers against Host to prevent CSRF."""
        origin = self.headers.get("Origin") or self.headers.get("Referer")
        host = self.headers.get("Host")
        if origin and host:
            parsed = urlparse(origin)
            if parsed.netloc and parsed.netloc.lower() != host.lower():
                return False
        return True

    def get_session_token(self) -> Optional[str]:
        # Check custom header first
        auth_header = self.headers.get("X-Session-Token")
        if auth_header:
            return auth_header

        # Check cookies
        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            item = item.strip()
            if item.startswith("xfwd_session="):
                return item.split("=")[1].strip()
            if item.startswith("fwdman_session="):
                return item.split("=")[1].strip()
        return None

    def is_authenticated(self) -> bool:
        token = self.get_session_token()
        if not token:
            return False
        now = time.time()
        with SESSION_LOCK:
            session = ACTIVE_SESSIONS.get(token)
            if not session:
                return False

            # Check absolute expiry or idle timeout
            if now > session.get("expires_at", 0) or (now - session.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS:
                ACTIVE_SESSIONS.pop(token, None)
                return False

            # Slide activity window
            session["last_active"] = now

            # Bound session table size
            if len(ACTIVE_SESSIONS) > MAX_ACTIVE_SESSIONS:
                stale = [k for k, v in ACTIVE_SESSIONS.items() if now > v.get("expires_at", 0) or (now - v.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS]
                for k in stale:
                    ACTIVE_SESSIONS.pop(k, None)
        return True

    def resolve_path(self) -> Tuple[bool, str, Optional[str]]:
        """
        Resolves the requested path against configured secret_path.
        Returns: (is_allowed, normalized_subpath, redirect_url)
        """
        parsed = urlparse(self.path)
        raw_path = parsed.path
        cfg = load_config()
        secret = cfg.get("web", {}).get("secret_path", "")
        secret = str(secret or "").strip().strip("/")

        # Favicon optimization
        if raw_path == "/favicon.ico":
            return True, "/favicon.ico", None

        # Case 1: No secret path configured -> direct root access allowed
        if not secret:
            clean = raw_path.rstrip("/") or "/"
            return True, clean, None

        secret_prefix = f"/{secret}"

        # Exact match without trailing slash -> redirect to /{secret}/
        if raw_path == secret_prefix:
            return True, "/", f"{secret_prefix}/"

        # Request under /{secret}/
        if raw_path.startswith(f"{secret_prefix}/"):
            subpath = raw_path[len(secret_prefix):]
            clean = subpath.rstrip("/") or "/"
            return True, clean, None

        # Allow authenticated requests to /api/ if user already has a valid session token
        if raw_path.startswith("/api/") and self.is_authenticated():
            clean = raw_path.rstrip("/") or "/"
            return True, clean, None

        return False, raw_path, None

    def do_GET(self):
        allowed, subpath, redirect_url = self.resolve_path()
        if redirect_url:
            self.send_response(302)
            self.send_header("Location", redirect_url)
            self.apply_security_headers()
            self.end_headers()
            return

        if not allowed:
            self.send_error(404, "Not Found")
            return

        # Favicon optimization
        if subpath == "/favicon.ico":
            self.send_response(204)
            self.apply_security_headers()
            self.end_headers()
            return

        # Static assets
        if subpath == "/style.css":
            self.send_file(os.path.join(WEB_DIR, "style.css"), "text/css; charset=utf-8")
            return
        elif subpath == "/app.js":
            self.send_file(os.path.join(WEB_DIR, "app.js"), "application/javascript; charset=utf-8")
            return

        # Check authentication for API
        if subpath.startswith("/api/"):
            if subpath == "/api/me":
                auth_ok = self.is_authenticated()
                cfg = load_config()
                username = cfg.get("web", {}).get("auth", {}).get("username", "admin")
                self.send_json({"authenticated": auth_ok, "username": username if auth_ok else None})
                return

            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if subpath == "/api/status":
                cfg = load_config()
                state = load_state()
                self.send_json({
                    "version": get_installed_version(),
                    "config": cfg,
                    "runtime": state.get("runtime", {}),
                    "system": get_system_stats(),
                    "services": get_services_status(),
                    "network": get_network_interfaces_info(),
                    "server_time": time.time()
                })
                return
            elif subpath == "/api/services/status":
                self.send_json(get_services_status())
                return
            elif subpath == "/api/network/interfaces":
                self.send_json(get_network_interfaces_info())
                return
            elif subpath == "/api/import/discover":
                cfg = load_config()
                existing_rules = cfg.get("rules", [])
                try:
                    from core.nftables_parser import discover_all_relay_rules
                except ImportError:
                    from nftables_parser import discover_all_relay_rules
                data = discover_all_relay_rules(existing_rules)
                self.send_json(data)
                return
            elif subpath == "/api/config/export":
                export_data = export_config_data()
                now_str = time.strftime("%Y%m%d-%H%M%S")
                body = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="xforwarder-backup-{now_str}.json"')
                self.send_header("Content-Length", str(len(body)))
                self.apply_security_headers()
                self.end_headers()
                self.wfile.write(body)
                return


            elif subpath == "/api/metrics/loss-history":
                # Returns aggregated packet loss, quality timeline, KPIs, and recent disruption events
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                target = params.get("target", ["all"])[0]
                range_str = params.get("range", ["24h"])[0]
                hours = 24
                if range_str == "7d":
                    hours = 168
                elif range_str == "30d":
                    hours = 720
                else:
                    try:
                        hours = int(range_str.replace("h", ""))
                    except Exception:
                        hours = 24

                try:
                    from core.metrics import get_metrics_history
                except ImportError:
                    try:
                        from metrics import get_metrics_history
                    except ImportError:
                        get_metrics_history = None

                if get_metrics_history:
                    history = get_metrics_history(target=target, time_range_hours=hours)
                    self.send_json({"ok": True, **history})
                else:
                    self.send_json({"ok": False, "error": "Metrics module unavailable"}, 500)
                return

            elif subpath == "/api/system/version":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                force_check = params.get("check", ["0"])[0] in ("1", "true")
                data = get_full_version_status(force=force_check)
                self.send_json(data)
                return

            elif subpath == "/api/system/update/status":
                data = get_update_status()
                self.send_json(data)
                return

            else:
                self.send_error(404, "API endpoint not found")
                return

        # Serve SPA index.html for all UI subpaths under secret_path
        self.send_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")

    def do_POST(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        # CSRF Protection: Verify Origin matches Host
        if not self.check_origin():
            self.send_json({"ok": False, "error": "Cross-origin request rejected"}, 403)
            return

        # DoS Protection: Limit payload size to 64KB
        MAX_PAYLOAD = 65536
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_PAYLOAD:
            self.send_json({"ok": False, "error": "Payload exceeds 64KB limit"}, 413)
            return

        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}

        # 1. Login endpoint (Protected with Adaptive Rate Limiting & PBKDF2)
        if subpath == "/api/login":
            client_ip = self.get_client_ip()

            # Check rate limiting / lockout
            is_locked, remaining, fail_count = check_rate_limit(client_ip)
            if is_locked:
                self.send_json({
                    "ok": False,
                    "error": f"Too many failed login attempts. Temporary lockout active. Try again in {remaining} seconds.",
                    "lockout": True,
                    "remaining_seconds": remaining
                }, 429)
                return

            cfg = load_config()
            auth_cfg = cfg.get("web", {}).get("auth", {})
            expected_user = auth_cfg.get("username", "admin")
            expected_hash = auth_cfg.get("password_hash", "")

            user = body.get("username", "").strip()
            pwd = body.get("password", "")

            user_matches = hmac.compare_digest(user, expected_user)
            pwd_valid, needs_rehash = verify_password(pwd, expected_hash)

            if user_matches and pwd_valid:
                reset_rate_limit(client_ip)

                # Automatic self-healing upgrade of legacy SHA-256 hashes to salted PBKDF2
                if needs_rehash:
                    new_salted_hash = hash_password(pwd)
                    cfg["web"]["auth"]["password_hash"] = new_salted_hash
                    save_config(cfg)

                token = secrets.token_hex(32)
                now = time.time()
                with SESSION_LOCK:
                    ACTIVE_SESSIONS[token] = {
                        "username": user,
                        "created_at": now,
                        "last_active": now,
                        "expires_at": now + (SESSION_TTL_HOURS * 3600),
                        "ip": client_ip
                    }
                save_sessions_to_disk()
                self.send_json({"ok": True, "token": token, "username": user}, 200, cookie_token=token)
            else:
                is_locked_now, lock_remaining, count = record_failed_login(client_ip)
                # Intentional timing jitter delay to defeat automated credential stuffing
                time.sleep(0.4 + (secrets.randbelow(300) / 1000.0))
                attempts_left = max(0, MAX_FAILED_ATTEMPTS - count)
                if is_locked_now:
                    self.send_json({
                        "ok": False,
                        "error": f"Maximum failed attempts exceeded. Access locked for {LOCKOUT_DURATION // 60} minutes.",
                        "lockout": True,
                        "remaining_seconds": lock_remaining
                    }, 429)
                else:
                    self.send_json({
                        "ok": False,
                        "error": f"Invalid username or password. {attempts_left} attempt(s) remaining before temporary lockout.",
                        "attempts_left": attempts_left
                    }, 401)
            return

        # 2. Logout endpoint
        if subpath == "/api/logout":
            token = self.get_session_token()
            if token:
                with SESSION_LOCK:
                    ACTIVE_SESSIONS.pop(token, None)
                save_sessions_to_disk()
            self.send_json({"ok": True}, 200, cookie_token="")
            return

        # All other POST endpoints require authentication
        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        # 3. Security Credentials Management (Change Username / Password)
        if subpath in ("/api/security", "/api/security/credentials"):
            current_pwd = body.get("current_password", "")
            new_user = body.get("new_username", "").strip()
            new_pwd = body.get("new_password", "")

            cfg = load_config()
            auth_cfg = cfg.get("web", {}).get("auth", {})
            expected_hash = auth_cfg.get("password_hash", "")

            pwd_valid, _ = verify_password(current_pwd, expected_hash)
            if not pwd_valid:
                self.send_json({"ok": False, "error": "Current password verification failed"}, 403)
                return

            if new_user:
                if len(new_user) < 3:
                    self.send_json({"ok": False, "error": "Username must be at least 3 characters"}, 400)
                    return
                auth_cfg["username"] = new_user
                token = self.get_session_token()
                if token:
                    with SESSION_LOCK:
                        if token in ACTIVE_SESSIONS:
                            ACTIVE_SESSIONS[token]["username"] = new_user
                    save_sessions_to_disk()

            if new_pwd:
                if len(new_pwd) < 8:
                    self.send_json({"ok": False, "error": "New password must be at least 8 characters"}, 400)
                    return
                auth_cfg["password_hash"] = hash_password(new_pwd)

            cfg["web"]["auth"] = auth_cfg
            if save_config(cfg):
                self.send_json({"ok": True, "username": auth_cfg["username"]})
            else:
                self.send_json({"ok": False, "error": "Failed to save configuration"}, 500)
            return

        elif subpath == "/api/rule":
            valid, err_msg = validate_rule(body)
            if not valid:
                self.send_json({"ok": False, "error": err_msg}, 400)
                return

            cfg = load_config()
            rules = cfg.get("rules", [])
            rule_id = str(body.get("id") or f"rule-{body['port']}")
            body["id"] = rule_id

            # Zero-Collision Check: Ensure no other rule is already using this listening port
            for r in rules:
                if r.get("id") != rule_id and r.get("port") == body["port"]:
                    self.send_json({"ok": False, "error": f"Port {body['port']} is already used by rule '{r.get('id')}'"}, 409)
                    return

            # External Conflict Check: Ensure no external service is listening on this port
            if is_port_in_use_by_external_service(body["port"], rule_id, rules):
                self.send_json({
                    "ok": False,
                    "error": f"Port {body['port']} is already bound by an external system service (e.g. web server, SSH, or proxy)!"
                }, 409)
                return

            now_ts = time.time()
            updated = False
            for i, r in enumerate(rules):
                if r.get("id") == rule_id:
                    # Preserve existing created_at timestamp if present and not provided in update
                    orig_created_at = float(r.get("created_at", 0) or 0)
                    body_created_at = float(body.get("created_at", 0) or 0)
                    if orig_created_at > 0 and body_created_at <= 0:
                        body["created_at"] = orig_created_at
                    elif body_created_at <= 0:
                        body["created_at"] = now_ts
                    else:
                        body["created_at"] = body_created_at
                    rules[i] = body
                    updated = True
                    break
            if not updated:
                if float(body.get("created_at", 0) or 0) <= 0:
                    body["created_at"] = now_ts
                rules.append(body)

            cfg["rules"] = rules
            if save_config(cfg):
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "rule": body,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/override":
            rule_id = str(body.get("rule_id", ""))
            try:
                override_prio = int(body.get("force_override", 0))
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid force_override value"}, 400)
                return

            if override_prio < 0:
                self.send_json({"ok": False, "error": "force_override cannot be negative"}, 400)
                return

            cfg = load_config()
            found = False
            for r in cfg.get("rules", []):
                if r.get("id") == rule_id:
                    r["force_override"] = override_prio
                    if override_prio > 0:
                        r["active_priority"] = override_prio
                    else:
                        # Auto Failover: immediately recalculate active_priority from healthy states & composite scores
                        state = load_state()
                        r_state = state.get("runtime", {}).get("rules_state", {}).get(rule_id, {})
                        r_state["last_switch_time"] = 0
                        r_state["cooldown_remaining"] = 0
                        dest_stats = r_state.get("dest_stats", {})
                        chosen = None
                        dests = sorted(r.get("destinations", []), key=lambda d: d.get("priority", 99))
                        for d in dests:
                            p = d.get("priority", 1)
                            st = dest_stats.get(f"prio_{p}", {})
                            if st.get("status") == "healthy" and st.get("packet_loss", 0) <= 25:
                                chosen = p
                                break
                        if chosen is None:
                            best_score = 999999.0
                            for d in dests:
                                p = d.get("priority", 1)
                                st = dest_stats.get(f"prio_{p}", {})
                                if st.get("packet_loss", 100) < 100:
                                    sc = st.get("composite_score", 999.0)
                                    if sc < best_score:
                                        best_score = sc
                                        chosen = p
                        r["active_priority"] = chosen if chosen is not None else (dests[0].get("priority", 1) if dests else 1)
                    found = True
                    break
            if not found:
                self.send_json({"ok": False, "error": "Rule not found"}, 404)
                return

            if save_config(cfg):
                update_state_rules({
                    rule_id: {
                        "active_priority": r["active_priority"],
                        "last_force_override": override_prio,
                        "last_switch_time": 0,
                        "cooldown_remaining": 0
                    }
                })
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)
            return

        elif subpath == "/api/override/batch":
            try:
                override_prio = int(body.get("force_override", 0))
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid force_override value"}, 400)
                return

            if override_prio < 0:
                self.send_json({"ok": False, "error": "force_override cannot be negative"}, 400)
                return

            cfg = load_config()
            rules = cfg.get("rules", [])
            state = load_state()
            rules_state = state.get("runtime", {}).get("rules_state", {})
            for r in rules:
                r["force_override"] = override_prio
                r_id = r.get("id")
                r_state = rules_state.get(r_id, {})
                r_state["last_switch_time"] = 0
                r_state["cooldown_remaining"] = 0
                if override_prio > 0:
                    r["active_priority"] = override_prio
                else:
                    dest_stats = r_state.get("dest_stats", {})
                    chosen = None
                    dests = sorted(r.get("destinations", []), key=lambda d: d.get("priority", 99))
                    for d in dests:
                        p = d.get("priority", 1)
                        st = dest_stats.get(f"prio_{p}", {})
                        if st.get("status") == "healthy" and st.get("packet_loss", 0) <= 25:
                            chosen = p
                            break
                    if chosen is None:
                        best_score = 999999.0
                        for d in dests:
                            p = d.get("priority", 1)
                            st = dest_stats.get(f"prio_{p}", {})
                            if st.get("packet_loss", 100) < 100:
                                sc = st.get("composite_score", 999.0)
                                if sc < best_score:
                                    best_score = sc
                                    chosen = p
                    r["active_priority"] = chosen if chosen is not None else (dests[0].get("priority", 1) if dests else 1)

            if save_config(cfg):
                batch_updates = {
                    r.get("id"): {
                        "active_priority": r["active_priority"],
                        "last_force_override": override_prio,
                        "last_switch_time": 0,
                        "cooldown_remaining": 0
                    } for r in rules if r.get("id")
                }
                update_state_rules(batch_updates)
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "count": len(rules),
                    "force_override": override_prio,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/sync":
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": sync_ok,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            }, 200 if sync_ok else 500)

        elif subpath == "/api/import/haproxy":
            from core.haproxy_parser import import_haproxy_rules_into_config
            cfg_path = get_config_path()
            count, ports = import_haproxy_rules_into_config(cfg_path)
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })

        elif subpath == "/api/import/nftables":
            try:
                from core.nftables_parser import import_nftables_rules_into_config
            except ImportError:
                from nftables_parser import import_nftables_rules_into_config
            cfg_path = get_config_path()
            count, ports, logs = import_nftables_rules_into_config(cfg_path, deactivate_legacy=True)
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports,
                "logs": logs,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })

        elif subpath == "/api/import/all":
            try:
                from core.nftables_parser import import_all_relay_rules_into_config
            except ImportError:
                from nftables_parser import import_all_relay_rules_into_config
            cfg_path = get_config_path()
            count, ports, logs = import_all_relay_rules_into_config(cfg_path, deactivate_legacy=True)
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports,
                "logs": logs,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })

        elif subpath == "/api/config/import":
            imported_raw = body.get("config") if (isinstance(body, dict) and isinstance(body.get("config"), dict)) else body
            mode = body.get("mode", "merge") if isinstance(body, dict) else "merge"
            ok, err, info = import_config_data(imported_raw, mode=mode)
            if ok:
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({"ok": True, "sync_ok": sync_ok, "sync_errors": sync_errors, **info})
        elif subpath == "/api/test-target":
            target = str(body.get("target", "")).strip().strip("[]")
            try:
                port = int(body.get("port", 0))
            except (ValueError, TypeError):
                port = 0
            if not target or not is_valid_target(target) or port <= 0 or port > 65535:
                self.send_json({"ok": False, "healthy": False, "error": "Invalid target IP/host or port"}, 400)
                return

            dest_type = str(body.get("type", "")).lower().strip()
            if not dest_type:
                dest_type = "haproxy" if ":" in target else "nginx"
            if dest_type == "haproxy":
                clean_target = target.strip("[]")
                try:
                    ip_obj = ipaddress.ip_address(clean_target)
                    if ip_obj.version != 6:
                        self.send_json({"ok": False, "healthy": False, "error": f"HAProxy destination target must be a valid IPv6 address (got IPv4 '{target}')"}, 400)
                        return
                except ValueError:
                    self.send_json({"ok": False, "healthy": False, "error": f"HAProxy destination target must be a valid IPv6 address (got '{target}')"}, 400)
                    return

            is_loss_test = (body.get("mode") == "loss_50" or body.get("test_loss") is True or str(body.get("packets", "")) == "50")
            if is_loss_test:
                try:
                    from core.metrics import measure_packet_loss_50
                except ImportError:
                    try:
                        from metrics import measure_packet_loss_50
                    except ImportError:
                        measure_packet_loss_50 = None

                if measure_packet_loss_50:
                    try:
                        res = measure_packet_loss_50(target, count=50, interval=0.2, save_to_db=True)
                        self.send_json({
                            "ok": True,
                            "healthy": res.get("healthy", False),
                            "latency_ms": res.get("latency_ms"),
                            "min_lat": res.get("min_lat"),
                            "max_lat": res.get("max_lat"),
                            "packet_loss": res.get("packet_loss", 0 if res.get("healthy") else 100),
                            "packets_sent": res.get("packets_sent", 50),
                            "packets_received": res.get("packets_received", 0),
                            "is_disrupted": res.get("is_disrupted", 0),
                            "reason": res.get("error", "")
                        })
                        return
                    except Exception as e:
                        self.send_json({"ok": False, "healthy": False, "error": str(e)}, 500)
                        return

            protocol = str(body.get("protocol", "both")).lower()
            try:
                packets = int(body.get("packets", 4))
            except (ValueError, TypeError):
                packets = 4
            packets = max(1, min(packets, 10))

            try:
                from core.engine import XForwarderEngine
                engine = XForwarderEngine(config_path=get_config_path())
                probe_res = engine.check_destination(
                    {"target": target, "port": port, "type": dest_type},
                    rule_port=port,
                    protocol=protocol,
                    count=packets
                )
                self.send_json({
                    "ok": True,
                    "healthy": probe_res.get("healthy", False),
                    "latency_ms": probe_res.get("latency_ms"),
                    "packet_loss": probe_res.get("packet_loss", 0 if probe_res.get("healthy") else 100),
                    "packets_sent": probe_res.get("packets_sent", packets),
                    "packets_received": probe_res.get("packets_received", packets if probe_res.get("healthy") else 0),
                    "reason": probe_res.get("reason", "")
                })
            except Exception as e:
                self.send_json({"ok": False, "healthy": False, "error": str(e)}, 500)
            return

        elif subpath == "/api/test-loss":
            # On-demand precise 50-probe packet loss evaluation (`ping [ip] -c 50 -i 0.2`)
            target = str(body.get("target", "")).strip().strip("[]")
            if not target or not is_valid_target(target):
                self.send_json({"ok": False, "healthy": False, "error": "Invalid target IP/host"}, 400)
                return

            try:
                from core.metrics import measure_packet_loss_50
            except ImportError:
                try:
                    from metrics import measure_packet_loss_50
                except ImportError:
                    measure_packet_loss_50 = None

            if not measure_packet_loss_50:
                self.send_json({"ok": False, "healthy": False, "error": "Loss measurement module unavailable"}, 500)
                return

            try:
                res = measure_packet_loss_50(target, count=50, interval=0.2, save_to_db=True)
                self.send_json({"ok": True, **res})
            except Exception as e:
                self.send_json({"ok": False, "healthy": False, "error": str(e)}, 500)
            return

        elif subpath == "/api/metrics/trigger-round":
            # Manual trigger for an immediate scheduled probing round across deduplicated targets
            try:
                from core.metrics import run_scheduled_ping_round
            except ImportError:
                try:
                    from metrics import run_scheduled_ping_round
                except ImportError:
                    run_scheduled_ping_round = None

            if not run_scheduled_ping_round:
                self.send_json({"ok": False, "error": "Metrics module unavailable"}, 500)
                return

            try:
                cfg = load_config()
                results = run_scheduled_ping_round(cfg)
                self.send_json({"ok": True, "count": len(results), "results": results})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif subpath == "/api/system/update":
            ok, msg = start_system_update()
            if ok:
                self.send_json({"ok": True, "status": "started", "message": msg})
            else:
                self.send_json({"ok": False, "status": "error", "error": msg}, 409 if "already" in msg else 500)
            return

        elif subpath == "/api/services/restart":
            svc = body.get("service", "all")
            ok, msg, is_reconnecting = restart_services_action(svc)
            if ok:
                self.send_json({"ok": True, "service": svc, "message": msg, "reconnecting": is_reconnecting})
            else:
                self.send_json({"ok": False, "service": svc, "error": msg}, 400 if "Invalid" in msg else 500)
            return

        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if not self.check_origin():
            self.send_json({"ok": False, "error": "Cross-origin request rejected"}, 403)
            return

        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        if subpath.startswith("/api/rule/"):
            rule_id = subpath.split("/api/rule/")[1].strip()
            cfg = load_config()
            cfg["rules"] = [r for r in cfg.get("rules", []) if r.get("id") != rule_id]
            if save_config(cfg):
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "deleted": rule_id,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)
        else:
            self.send_error(404, "Not Found")


class XForwarderWebServer:
    def __init__(self, port: Optional[int] = None, bind_host: Optional[str] = None):
        cfg = load_config()
        web_cfg = cfg.get("web", {})
        self.port = port or int(web_cfg.get("port", 8090))
        self.bind_host = bind_host or web_cfg.get("bind_host", "0.0.0.0")
        self.ssl_cert = str(web_cfg.get("ssl_cert", "") or "").strip()
        self.ssl_key = str(web_cfg.get("ssl_key", "") or "").strip()
        self.is_ssl = False
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.is_running = False

    def start(self):
        handler_class = XForwarderWebHandler
        handler_class.server_instance = self

        self.httpd = ThreadingHTTPServer((self.bind_host, self.port), handler_class)
        self.is_running = True

        # Wrap with SSL/TLS if certificates are configured and accessible
        if self.ssl_cert and self.ssl_key:
            if os.path.exists(self.ssl_cert) and os.path.exists(self.ssl_key):
                try:
                    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    ssl_ctx.load_cert_chain(certfile=self.ssl_cert, keyfile=self.ssl_key)
                    self.httpd.socket = ssl_ctx.wrap_socket(self.httpd.socket, server_side=True)
                    self.is_ssl = True
                except Exception as e:
                    print(f"[WARN] Failed to initialize SSL/TLS ({e}). Falling back to HTTP.")
            else:
                missing = []
                if not os.path.exists(self.ssl_cert):
                    missing.append(f"cert: '{self.ssl_cert}'")
                if not os.path.exists(self.ssl_key):
                    missing.append(f"key: '{self.ssl_key}'")
                print(f"[WARN] SSL files missing ({', '.join(missing)}). Falling back to HTTP.")

        scheme = "https" if self.is_ssl else "http"
        print(f"\n=======================================================")
        print(f"  XForwarder Web Panel Started (Always-Online)")
        print(f"  Access URL: {scheme}://{self.bind_host}:{self.port}/")
        print(f"  SSL/TLS: {'Enabled (HTTPS)' if self.is_ssl else 'Disabled (HTTP)'}")
        print(f"=======================================================\n")

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        if self.is_running and self.httpd:
            self.is_running = False
            self.httpd.shutdown()
            print("[INFO] Web server stopped successfully.")


# Backward compatibility aliases
ForwardManagerWebHandler = XForwarderWebHandler
ForwardManagerWebServer = XForwarderWebServer

if __name__ == "__main__":
    server = XForwarderWebServer()
    server.start()

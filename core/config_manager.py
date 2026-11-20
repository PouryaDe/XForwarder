#!/usr/bin/env python3
"""
XForwarder - Configuration & State Manager
Provides centralized schema migrations, atomic persistence, validation, and import/export capabilities.
"""

import os
import sys
import json
import time
import tempfile
import re
import ipaddress
import socket
import subprocess
from typing import Dict, Any, Tuple, Optional, List, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = "/etc/xforwarder/config.json"
LEGACY_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
STATE_FILE_PATH = "/run/xforwarder/state.json"
LEGACY_STATE_FILE_PATH = "/run/forward-manager/state.json"

HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def get_config_path(override_path: Optional[str] = None) -> str:
    """Resolves active configuration file path with environmental and fallback precedence."""
    if override_path:
        return override_path
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


def get_state_file_path(override_path: Optional[str] = None) -> str:
    """Resolves active state file path with legacy and system temp fallbacks."""
    if override_path:
        return override_path
    env_override = os.environ.get("XFWD_STATE_PATH")
    if env_override:
        return env_override
    for path in [STATE_FILE_PATH, LEGACY_STATE_FILE_PATH]:
        if os.path.exists(path) or os.path.exists(os.path.dirname(path)):
            return path
    return os.path.join(tempfile.gettempdir(), "xforwarder_state.json")


def _coerce_bool(val: Any, default: bool = False) -> bool:
    """Safely converts boolean, string, or numeric values to bool, preventing 'false'/'0' string pitfalls."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        clean = val.strip().lower()
        if clean in ("true", "1", "yes", "on"):
            return True
        if clean in ("false", "0", "no", "off", ""):
            return False
    return bool(val)


def migrate_and_normalize_config(cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Automatically migrates and normalizes legacy configuration schemas for seamless backward compatibility."""
    if not isinstance(cfg, dict):
        cfg = {}

    modified = False

    current_version = int(cfg.get("schema_version", 1))
    if current_version < 3:
        # Upgrade defaults from v2 to v3 if untouched by user
        if cfg.get("hysteresis_percent") == 10:
            cfg["hysteresis_percent"] = 20
        if cfg.get("loss_penalty_weight") == 10:
            cfg["loss_penalty_weight"] = 20
        cfg["schema_version"] = 3
        modified = True
    elif cfg.get("schema_version") != 3:
        cfg["schema_version"] = 3
        modified = True

    defaults = {
        "wan_interface": "auto",
        "check_interval_seconds": 8,
        "probe_count": 10,
        "probe_interval_ms": 200,
        "quality_window_seconds": 300,
        "failure_threshold": 3,
        "recovery_threshold": 3,
        "fast_failover_enabled": True,
        "max_acceptable_loss": 25,
        "critical_loss_percent": 30,
        "cooldown_seconds": 60,
        "min_hold_seconds": 600,
        "switch_confirm_seconds": 120,
        "hysteresis_percent": 20,
        "loss_penalty_weight": 20,
        "jitter_penalty_weight": 2,
        "priority_bias_ms": 0,
        "fast_probe_burst": 5,
        "target_probe_interval_seconds": 60,
        "fast_liveness_interval_seconds": 15,
        "max_primary_latency_ms": 150
    }
    for k, v in defaults.items():
        if k not in cfg:
            cfg[k] = v
            modified = True

    # Normalize failover & anti-flap parameters
    try:
        val = max(2, min(int(cfg.get("check_interval_seconds", 8)), 120))
        if cfg.get("check_interval_seconds") != val:
            cfg["check_interval_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["check_interval_seconds"] = 8
        modified = True

    try:
        val = max(5, min(int(cfg.get("target_probe_interval_seconds", 60)), 3600))
        if cfg.get("target_probe_interval_seconds") != val:
            cfg["target_probe_interval_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["target_probe_interval_seconds"] = 60
        modified = True

    try:
        val = max(5, min(int(cfg.get("fast_liveness_interval_seconds", 15)), 300))
        if cfg.get("fast_liveness_interval_seconds") != val:
            cfg["fast_liveness_interval_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["fast_liveness_interval_seconds"] = 15
        modified = True

    try:
        val = max(5, min(int(cfg.get("probe_count", 10)), 20))
        if cfg.get("probe_count") != val:
            cfg["probe_count"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["probe_count"] = 10
        modified = True

    try:
        val = max(200, min(int(cfg.get("probe_interval_ms", 200)), 1000))
        if cfg.get("probe_interval_ms") != val:
            cfg["probe_interval_ms"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["probe_interval_ms"] = 200
        modified = True

    try:
        val = max(60, min(int(cfg.get("quality_window_seconds", 300)), 1800))
        if cfg.get("quality_window_seconds") != val:
            cfg["quality_window_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["quality_window_seconds"] = 300
        modified = True

    try:
        val = max(1, min(int(cfg.get("failure_threshold", 3)), 10))
        if cfg.get("failure_threshold") != val:
            cfg["failure_threshold"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["failure_threshold"] = 3
        modified = True

    try:
        val = max(1, min(int(cfg.get("recovery_threshold", 3)), 10))
        if cfg.get("recovery_threshold") != val:
            cfg["recovery_threshold"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["recovery_threshold"] = 3
        modified = True

    try:
        val = max(5, min(int(cfg.get("max_acceptable_loss", 25)), 90))
        if cfg.get("max_acceptable_loss") != val:
            cfg["max_acceptable_loss"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["max_acceptable_loss"] = 25
        modified = True

    try:
        val = max(10, min(int(cfg.get("critical_loss_percent", 30)), 90))
        if cfg.get("critical_loss_percent") != val:
            cfg["critical_loss_percent"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["critical_loss_percent"] = 30
        modified = True

    try:
        val = max(10, min(int(cfg.get("cooldown_seconds", 60)), 600))
        if cfg.get("cooldown_seconds") != val:
            cfg["cooldown_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["cooldown_seconds"] = 60
        modified = True

    try:
        val = max(60, min(int(cfg.get("min_hold_seconds", 600)), 3600))
        if cfg.get("min_hold_seconds") != val:
            cfg["min_hold_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["min_hold_seconds"] = 600
        modified = True

    try:
        val = max(30, min(int(cfg.get("switch_confirm_seconds", 120)), 900))
        if cfg.get("switch_confirm_seconds") != val:
            cfg["switch_confirm_seconds"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["switch_confirm_seconds"] = 120
        modified = True

    try:
        val = max(0, min(float(cfg.get("hysteresis_percent", 20)), 50))
        if cfg.get("hysteresis_percent") != val:
            cfg["hysteresis_percent"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["hysteresis_percent"] = 20
        modified = True

    try:
        val = max(1, min(int(cfg.get("loss_penalty_weight", 20)), 50))
        if cfg.get("loss_penalty_weight") != val:
            cfg["loss_penalty_weight"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["loss_penalty_weight"] = 20
        modified = True

    try:
        val = max(0, min(int(cfg.get("jitter_penalty_weight", 2)), 10))
        if cfg.get("jitter_penalty_weight") != val:
            cfg["jitter_penalty_weight"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["jitter_penalty_weight"] = 2
        modified = True

    try:
        val = max(0, min(int(cfg.get("priority_bias_ms", 0)), 200))
        if cfg.get("priority_bias_ms") != val:
            cfg["priority_bias_ms"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["priority_bias_ms"] = 0
        modified = True

    try:
        val = max(1, min(int(cfg.get("fast_probe_burst", 5)), 10))
        if cfg.get("fast_probe_burst") != val:
            cfg["fast_probe_burst"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["fast_probe_burst"] = 5
        modified = True

    try:
        val = max(50, min(int(cfg.get("max_primary_latency_ms", 150)), 1000))
        if cfg.get("max_primary_latency_ms") != val:
            cfg["max_primary_latency_ms"] = val
            modified = True
    except (ValueError, TypeError):
        cfg["max_primary_latency_ms"] = 150
        modified = True

    if not isinstance(cfg.get("fast_failover_enabled"), bool):
        cfg["fast_failover_enabled"] = bool(cfg.get("fast_failover_enabled", True))
        modified = True

    if "web" not in cfg or not isinstance(cfg["web"], dict):
        cfg["web"] = {}
        modified = True
    web = cfg["web"]

    web_defaults = {
        "bind_host": "0.0.0.0",
        "port": 8090,
        "secret_path": "xfwd-admin",
        "ssl_cert": "",
        "ssl_key": ""
    }
    for k, v in web_defaults.items():
        if k not in web:
            web[k] = v
            modified = True

    # Normalize secret path (strip leading/trailing slashes and whitespace)
    clean_secret = str(web.get("secret_path", "xfwd-admin") or "").strip().strip("/")
    if web.get("secret_path") != clean_secret:
        web["secret_path"] = clean_secret
        modified = True

    # Normalize web port
    try:
        web_port = int(web.get("port", 8090))
        if web.get("port") != web_port:
            web["port"] = web_port
            modified = True
    except (ValueError, TypeError):
        web["port"] = 8090
        modified = True

    # Normalize SSL cert/key paths
    clean_cert = str(web.get("ssl_cert", "") or "").strip()
    if web.get("ssl_cert") != clean_cert:
        web["ssl_cert"] = clean_cert
        modified = True

    clean_key = str(web.get("ssl_key", "") or "").strip()
    if web.get("ssl_key") != clean_key:
        web["ssl_key"] = clean_key
        modified = True

    if "auth" not in web or not isinstance(web["auth"], dict):
        web["auth"] = {}
        modified = True
    auth = web["auth"]
    if "username" not in auth:
        auth["username"] = "admin"
        modified = True
    if "password_hash" not in auth:
        auth["password_hash"] = ""
        modified = True

    if "rules" not in cfg or not isinstance(cfg["rules"], list):
        cfg["rules"] = []
        modified = True

    for rule in cfg["rules"]:
        if not isinstance(rule, dict):
            continue

        # Normalize excluded_ports (optional NFTables != exception list) and shorthand `!= ...`
        raw_port_val = str(rule.get("port") or "").strip()
        if raw_port_val.startswith("!="):
            shorthand_excl, _ = parse_excluded_ports(raw_port_val)
            if shorthand_excl:
                rule["excluded_ports"] = shorthand_excl
                rule["port"] = 1
                rule["port_range"] = "1-65535"
                modified = True
        if "excluded_ports" in rule:
            parsed_excl, _ = parse_excluded_ports(rule.get("excluded_ports"))
            if parsed_excl:
                if rule.get("excluded_ports") != parsed_excl:
                    rule["excluded_ports"] = parsed_excl
                    modified = True
                if not rule.get("port_range") and not rule.get("port"):
                    rule["port"] = 1
                    rule["port_range"] = "1-65535"
                    modified = True
            else:
                rule.pop("excluded_ports", None)
                modified = True

        # Normalize port / port_range
        sp, ep, prange = get_rule_port_bounds(rule)
        if sp is not None:
            port = sp
            if rule.get("port") != port:
                rule["port"] = port
                modified = True
            if prange and rule.get("port_range") != prange:
                rule["port_range"] = prange
                modified = True
            elif not prange and "port_range" in rule:
                rule.pop("port_range", None)
                modified = True
        else:
            try:
                port = int(rule.get("port", 0))
                if rule.get("port") != port:
                    rule["port"] = port
                    modified = True
            except (ValueError, TypeError):
                port = 0

        if not rule.get("id"):
            rule["id"] = f"rule-{prange or port}"
            modified = True

        proto = str(rule.get("protocol", "both")).lower()
        if proto not in ("tcp", "udp", "both"):
            proto = "both"
        if rule.get("protocol") != proto:
            rule["protocol"] = proto
            modified = True

        try:
            act_prio = int(rule.get("active_priority", 1))
        except (ValueError, TypeError):
            act_prio = 1
        if rule.get("active_priority") != act_prio:
            rule["active_priority"] = act_prio
            modified = True

        try:
            force_ovr = int(rule.get("force_override", 0))
        except (ValueError, TypeError):
            force_ovr = 0
        if rule.get("force_override") != force_ovr:
            rule["force_override"] = force_ovr
            modified = True

        # Normalize category (default empty string, max 48 chars, sanitize control/dangerous chars)
        raw_category = str(rule.get("category", "") or "").strip()[:48]
        clean_category = "".join(c for c in raw_category if ord(c) >= 32 and c not in "<>\";`$\\")
        if "category" not in rule:
            rule["category"] = clean_category
            modified = True
        elif rule.get("category") != clean_category:
            rule["category"] = clean_category
            modified = True

        # Normalize registration timestamp (created_at with NaN, Inf, and boundary protection)
        try:
            created_at = float(rule.get("created_at", 0))
            if created_at != created_at or created_at < 0 or created_at > 4102444800 or abs(created_at) == float("inf"):
                created_at = 0.0
        except (ValueError, TypeError):
            created_at = 0.0
        if "created_at" not in rule:
            rule["created_at"] = created_at
            modified = True
        elif rule.get("created_at") != created_at:
            rule["created_at"] = created_at
            modified = True

        dests = rule.get("destinations", [])
        if not isinstance(dests, list):
            dests = []
            rule["destinations"] = dests
            modified = True

        for d in dests:
            if not isinstance(d, dict):
                continue

            try:
                prio = int(d.get("priority", 1))
            except (ValueError, TypeError):
                prio = 1
            if d.get("priority") != prio:
                d["priority"] = prio
                modified = True

            raw_dport = d.get("port_range") or d.get("port")
            if raw_dport is not None and str(raw_dport).strip() != "":
                dsp, dep, drange = parse_port_spec(raw_dport)
                if dsp is not None:
                    d_port = dsp
                    if d.get("port") != d_port:
                        d["port"] = d_port
                        modified = True
                    if drange and d.get("port_range") != drange:
                        d["port_range"] = drange
                        modified = True
                    elif not drange and "port_range" in d:
                        d.pop("port_range", None)
                        modified = True
                else:
                    if d.get("port") != port:
                        d["port"] = port
                        modified = True
            else:
                if d.get("port") != port:
                    d["port"] = port
                    modified = True
                if prange and d.get("port_range") != prange:
                    d["port_range"] = prange
                    modified = True

            if "comment" not in d:
                d["comment"] = ""
                modified = True

            dtype = str(d.get("type", "")).lower().strip()
            if not dtype:
                target = str(d.get("target", "")).strip()
                if ":" in target:
                    dtype = "haproxy"
                elif target.startswith("10.") or target.startswith("192.168.") or target.startswith("172."):
                    dtype = "nftables"
                else:
                    dtype = "nginx"
                d["type"] = dtype
                modified = True
            elif d.get("type") != dtype:
                d["type"] = dtype
                modified = True

            if "target" in d:
                clean_target = str(d["target"]).strip().strip("[]")
                if d["target"] != clean_target:
                    d["target"] = clean_target
                    modified = True

            has_pp = _coerce_bool(d.get("proxy_protocol", False) or d.get("send_proxy", False), False)
            if d.get("proxy_protocol") != has_pp:
                d["proxy_protocol"] = has_pp
                modified = True

            is_enabled = _coerce_bool(d.get("enabled"), True)
            if "enabled" not in d:
                d["enabled"] = is_enabled
                modified = True
            elif d.get("enabled") != is_enabled:
                d["enabled"] = is_enabled
                modified = True

            is_relay = _coerce_bool(d.get("is_relay"), False)
            if "is_relay" not in d:
                d["is_relay"] = is_relay
                modified = True
            elif d.get("is_relay") != is_relay:
                d["is_relay"] = is_relay
                modified = True

    return cfg, modified


def load_config(config_path: Optional[str] = None) -> dict:
    """Loads configuration with automated self-healing schema migration."""
    path = get_config_path(config_path)
    cfg = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    if not isinstance(cfg, dict):
        cfg = {
            "schema_version": 3,
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
                    "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # admin
                }
            },
            "rules": []
        }
    cfg, modified = migrate_and_normalize_config(cfg)
    if modified and os.path.exists(path):
        save_config(cfg, config_path=path)
    return cfg


def save_config(cfg: dict, config_path: Optional[str] = None) -> bool:
    """Atomically writes configuration to disk using a temporary file and os.replace."""
    path = get_config_path(config_path)
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


def load_state(state_path: Optional[str] = None) -> dict:
    """Loads ephemeral runtime state from disk."""
    path = get_state_file_path(state_path)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def update_state_rules(rule_updates: Dict[str, dict], state_path: Optional[str] = None) -> None:
    """Synchronizes active_priority and force_override in state.json atomically."""
    path = get_state_file_path(state_path)
    s_dir = os.path.dirname(path)
    if not os.path.exists(path) and not os.path.exists(s_dir):
        return
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
    except Exception:
        pass


from typing import Dict, Any, Optional, Tuple, List

PORT_RANGE_REGEX = re.compile(r"^\s*(\d{1,5})\s*-\s*(\d{1,5})\s*$")


def parse_port_spec(val: Any) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Parses a single port (int/str) or port range ('start-end').
    Returns (start_port, end_port, range_str_or_None).
    Normalizes single-port ranges ('443-443') to (443, 443, None).
    Returns (None, None, None) when invalid.
    """
    if val is None or isinstance(val, bool):
        return None, None, None
    if isinstance(val, int):
        return (val, val, None) if 1 <= val <= 65535 else (None, None, None)

    s = str(val).strip()
    if not s:
        return None, None, None

    m = PORT_RANGE_REGEX.match(s)
    if m:
        sp, ep = int(m.group(1)), int(m.group(2))
        if not (1 <= sp <= ep <= 65535):
            return None, None, None
        if sp == ep:
            return sp, sp, None
        return sp, ep, f"{sp}-{ep}"

    try:
        p = int(s)
        if 1 <= p <= 65535:
            return p, p, None
    except ValueError:
        pass
    return None, None, None


def get_rule_port_bounds(rule: dict) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """Extracts canonical (start_port, end_port, port_range_str) from a rule dict."""
    if not isinstance(rule, dict):
        return None, None, None
    raw_range = rule.get("port_range")
    if raw_range:
        sp, ep, rstr = parse_port_spec(raw_range)
        if sp is not None:
            return sp, ep, rstr
    return parse_port_spec(rule.get("port"))


def ports_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Returns True when two closed port intervals [a_start, a_end] and [b_start, b_end] intersect."""
    return not (a_end < b_start or b_end < a_start)


def split_port_interval_excluding(start_p: int, end_p: int, excluded: Set[int]) -> List[Tuple[int, int]]:
    """
    Splits closed interval [start_p, end_p] into maximal contiguous sub-intervals
    excluding any port in `excluded`, clamped to valid ports 1..65535.
    """
    lo = max(1, int(start_p))
    hi = min(65535, int(end_p))
    if lo > hi:
        return []
    cuts = sorted(
        p for p in (excluded or set())
        if isinstance(p, int) and not isinstance(p, bool) and lo <= p <= hi
    )
    if not cuts:
        return [(lo, hi)]
    intervals: List[Tuple[int, int]] = []
    cursor = lo
    for p in cuts:
        if p > cursor:
            intervals.append((cursor, p - 1))
        if p + 1 > cursor:
            cursor = p + 1
    if cursor <= hi:
        intervals.append((cursor, hi))
    return intervals


def get_protected_ports(config: Optional[Dict[str, Any]] = None) -> Set[int]:
    """Returns system-critical ports (SSH 22 and configured Web UI port) that must never be DNAT-hijacked."""
    protected: Set[int] = {22}
    web_port = 8090
    if isinstance(config, dict):
        try:
            web_port = int((config.get("web") or {}).get("port", 8090) or 8090)
        except (TypeError, ValueError):
            web_port = 8090
    if 1 <= web_port <= 65535:
        protected.add(web_port)
    else:
        protected.add(8090)
    return protected


def parse_excluded_ports(raw_excl: Any, expand_limit: int = 1000) -> Tuple[Optional[List[int]], Optional[str]]:
    """
    Parses excluded ports from a list of ints/strings or comma/space-separated text
    (e.g. '22, 443, 1001' or '!= { 22, 443 }'). Returns (sorted_unique_ports, error_msg).
    """
    if raw_excl is None or raw_excl == "" or raw_excl == []:
        return [], None

    tokens: List[str] = []
    if isinstance(raw_excl, list):
        for item in raw_excl:
            if isinstance(item, bool):
                return None, "Invalid boolean port in excluded_ports"
            tokens.append(str(item).strip())
    elif isinstance(raw_excl, str):
        cleaned = raw_excl.strip()
        if cleaned.startswith("!="):
            cleaned = cleaned[2:].strip()
        cleaned = cleaned.strip("{}").strip()
        if not cleaned:
            return [], None
        tokens = [tok.strip() for tok in re.split(r"[,\s]+", cleaned) if tok.strip()]
    else:
        return None, "excluded_ports must be a list of ports or comma-separated string"

    ports: Set[int] = set()
    for tok in tokens:
        if "-" in tok:
            parts = tok.split("-", 1)
            try:
                sp, ep = int(parts[0].strip()), int(parts[1].strip())
            except ValueError:
                return None, f"Invalid excluded port range '{tok}'"
            if not (1 <= sp <= ep <= 65535):
                return None, f"Excluded port range '{tok}' must be within 1-65535"
            if (ep - sp) > expand_limit:
                return None, f"Excluded port range '{tok}' is too large (max {expand_limit} ports)"
            ports.update(range(sp, ep + 1))
        else:
            if not tok.isdigit():
                return None, f"Invalid excluded port '{tok}'"
            p = int(tok)
            if not (1 <= p <= 65535):
                return None, f"Excluded port {p} must be between 1 and 65535"
            ports.add(p)

    return sorted(ports), None


def rules_ports_overlap(rule_a: dict, rule_b: dict) -> bool:
    """
    Returns True if two rules actually conflict on any active port, respecting
    excluded_ports so e.g. a dedicated rule on :443 coexists cleanly with `1-65535 != [22, 443, 1001]`.
    """
    sa, ea, _ = get_rule_port_bounds(rule_a)
    sb, eb, _ = get_rule_port_bounds(rule_b)
    if sa is None or ea is None or sb is None or eb is None:
        return False
    if not ports_overlap(sa, ea, sb, eb):
        return False

    excl_a = set(rule_a.get("excluded_ports") or [])
    excl_b = set(rule_b.get("excluded_ports") or [])
    if excl_a and (eb - sb) <= 2000 and all(p in excl_a for p in range(sb, eb + 1)):
        return False
    if excl_b and (ea - sa) <= 2000 and all(p in excl_b for p in range(sa, ea + 1)):
        return False
    return True


def is_valid_target(target: str) -> bool:
    """Strictly validates if a destination target is a valid IPv4, IPv6, or RFC hostname."""
    if not target or not isinstance(target, str):
        return False
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
    """Validates forwarding rule schema and destination attributes (single port or NFTables range)."""
    if not isinstance(body, dict):
        return False, "Invalid JSON body"

    raw_port = body.get("port_range") if body.get("port_range") else body.get("port")
    raw_port_str = str(raw_port).strip() if raw_port is not None else ""
    if raw_port_str.startswith("!="):
        # Support shorthand `!= 22, 443, 1001` syntax -> normalize to all ports 1-65535 with exclusions
        shorthand_excl, excl_err = parse_excluded_ports(raw_port_str)
        if excl_err or not shorthand_excl:
            return False, excl_err or "Specify at least one valid port to exclude (e.g. '!= 22, 443')"
        start_p, end_p, port_range_str = 1, 65535, "1-65535"
        body["excluded_ports"] = shorthand_excl
    elif "excluded_ports" in body and body.get("excluded_ports") not in (None, "", []):
        parsed_excl, excl_err = parse_excluded_ports(body.get("excluded_ports"))
        if excl_err:
            return False, excl_err
        body["excluded_ports"] = parsed_excl
        if not raw_port_str:
            start_p, end_p, port_range_str = 1, 65535, "1-65535"
        else:
            start_p, end_p, port_range_str = parse_port_spec(raw_port)
            if start_p is None:
                return False, "Port must be between 1 and 65535 (or a valid range 'start-end')"
            if not port_range_str:
                return False, "Excluded ports (!=) require an inbound port range (e.g. 1-65535)"
    else:
        body.pop("excluded_ports", None)
        start_p, end_p, port_range_str = parse_port_spec(raw_port)
        if start_p is None:
            return False, "Port must be between 1 and 65535 (or a valid range 'start-end')"

    body["port"] = start_p
    if port_range_str:
        body["port_range"] = port_range_str
    else:
        body.pop("port_range", None)

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
            if port_range_str:
                d_type = "nftables"
            elif ":" in clean_t:
                d_type = "haproxy"
            elif clean_t.startswith("10.") or clean_t.startswith("192.168.") or clean_t.startswith("172."):
                d_type = "nftables"
            else:
                d_type = "nginx"
            d["type"] = d_type
        elif d_type not in ("haproxy", "nftables", "nginx"):
            return False, "Destination type must be 'haproxy', 'nftables', or 'nginx'"
        d["type"] = d_type

        if port_range_str and d_type != "nftables":
            return False, f"Port ranges / exclusions ({port_range_str}) are only supported for 'nftables' destinations (not '{d_type}')"

        if d_type == "haproxy":
            clean_target = target.strip("[]")
            try:
                ip_obj = ipaddress.ip_address(clean_target)
                if ip_obj.version != 6:
                    return False, f"HAProxy destination target must be a valid IPv6 address (got IPv4 '{target}')"
            except ValueError:
                return False, f"HAProxy destination target must be a valid IPv6 address (got '{target}')"
        elif d_type == "nftables":
            # NFTables kernel DNAT rules require raw numeric IPv4 or IPv6 addresses.
            # Hostnames/domains cause syntax errors during atomic ruleset commit ('nft -c -f').
            clean_target = target.strip("[]")
            try:
                ipaddress.ip_address(clean_target)
            except ValueError:
                return False, f"NFTables destination target must be a valid IPv4 or IPv6 address (got '{target}')"

        raw_dport = d.get("port_range") if d.get("port_range") else d.get("port")
        if raw_dport is None or str(raw_dport).strip() == "":
            d["port"] = start_p
            if port_range_str:
                d["port_range"] = port_range_str
            else:
                d.pop("port_range", None)
        else:
            d_sp, d_ep, d_range_str = parse_port_spec(raw_dport)
            if d_sp is None:
                return False, "Destination port must be between 1 and 65535 (or a valid matching range)"
            if d_range_str:
                if d_type != "nftables":
                    return False, f"Destination port range '{d_range_str}' is only supported for 'nftables' (not '{d_type}')"
                if not port_range_str or d_range_str != port_range_str:
                    return False, f"NFTables outbound port range must match inbound range ({port_range_str or start_p}) or be a single target port"
                d["port"] = d_sp
                d["port_range"] = d_range_str
            else:
                d["port"] = d_sp
                d.pop("port_range", None)

        prio = d.get("priority", 1)
        try:
            prio = int(prio)
            if prio < 1:
                return False, "Destination priority must be 1 or greater"
            d["priority"] = prio
        except (ValueError, TypeError):
            return False, "Destination priority must be a valid integer"

        d["enabled"] = _coerce_bool(d.get("enabled"), True)
        d["is_relay"] = _coerce_bool(d.get("is_relay"), False)

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
    """Checks if a port is actively bound by an external non-managed process."""
    for r in existing_rules:
        if r.get("id") == current_rule_id and r.get("port") == port:
            return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                if is_haproxy_listening(port) or is_nginx_listening(port):
                    return False
                return True
    except Exception:
        pass
    return False


def export_config_data(cfg: Optional[dict] = None) -> dict:
    """Returns a sanitized export representation of the configuration, omitting sensitive credentials."""
    if cfg is None:
        cfg = load_config()
    return {
        "_comment": "XForwarder Configuration Backup",
        "exported_at": int(time.time()),
        "version": cfg.get("schema_version", 3),
        "wan_interface": cfg.get("wan_interface", "auto"),
        "check_interval_seconds": cfg.get("check_interval_seconds", 8),
        "probe_count": cfg.get("probe_count", 10),
        "probe_interval_ms": cfg.get("probe_interval_ms", 200),
        "quality_window_seconds": cfg.get("quality_window_seconds", 300),
        "failure_threshold": cfg.get("failure_threshold", 3),
        "recovery_threshold": cfg.get("recovery_threshold", 3),
        "fast_failover_enabled": cfg.get("fast_failover_enabled", True),
        "max_acceptable_loss": cfg.get("max_acceptable_loss", 25),
        "critical_loss_percent": cfg.get("critical_loss_percent", 30),
        "cooldown_seconds": cfg.get("cooldown_seconds", 60),
        "min_hold_seconds": cfg.get("min_hold_seconds", 600),
        "switch_confirm_seconds": cfg.get("switch_confirm_seconds", 120),
        "hysteresis_percent": cfg.get("hysteresis_percent", 20),
        "loss_penalty_weight": cfg.get("loss_penalty_weight", 20),
        "jitter_penalty_weight": cfg.get("jitter_penalty_weight", 2),
        "priority_bias_ms": cfg.get("priority_bias_ms", 0),
        "fast_probe_burst": cfg.get("fast_probe_burst", 5),
        "target_probe_interval_seconds": cfg.get("target_probe_interval_seconds", 60),
        "fast_liveness_interval_seconds": cfg.get("fast_liveness_interval_seconds", 15),
        "max_primary_latency_ms": cfg.get("max_primary_latency_ms", 150),
        "rules": cfg.get("rules", [])
    }


def import_config_data(imported_raw: Any, mode: str = "merge") -> Tuple[bool, str, dict]:
    """Validates, migrates, backs up, and applies an imported configuration dictionary or rules list."""
    if mode not in ("merge", "replace"):
        mode = "merge"

    # Support raw JSON string, rules array, or single rule dict as valid import payload
    if isinstance(imported_raw, str):
        try:
            imported_raw = json.loads(imported_raw)
        except Exception as e:
            return False, f"Invalid JSON string payload: Must be a valid JSON object or rules array ({e})", {}

    if isinstance(imported_raw, list):
        imported_raw = {"rules": imported_raw}
    elif isinstance(imported_raw, dict) and "rules" not in imported_raw and (
        "port" in imported_raw or "port_range" in imported_raw or "excluded_ports" in imported_raw
    ):
        imported_raw = {"rules": [imported_raw]}
    elif not isinstance(imported_raw, dict):
        return False, "Invalid configuration payload. Must be a JSON object, rules array, or rule object.", {}

    imported_cfg, _ = migrate_and_normalize_config(imported_raw)
    imported_rules = imported_cfg.get("rules", [])
    if not isinstance(imported_rules, list):
        return False, "'rules' property must be a list", {}

    current_cfg = load_config()
    web_port = current_cfg.get("web", {}).get("port", 8090)

    validated_rules = []
    seen_rules: List[dict] = []
    for r in imported_rules:
        if not isinstance(r, dict):
            continue
        sp, ep, prange = get_rule_port_bounds(r)
        if sp is None:
            return False, f"Invalid port number/range: {r.get('port_range') or r.get('port')}", {}
        label = f"!={','.join(map(str, r['excluded_ports']))}" if r.get("excluded_ports") else (prange or str(sp))
        if not r.get("excluded_ports") and sp <= web_port <= ep:
            return False, f"Port {web_port} is reserved for the XForwarder Web Dashboard", {}
        if any(rules_ports_overlap(r, existing_r) for existing_r in seen_rules):
            if sp == ep and any(get_rule_port_bounds(er)[:2] == (sp, ep) for er in seen_rules):
                return False, f"Duplicate port {label} found in imported rules", {}
            return False, f"Duplicate port range {label} overlaps another rule in imported rules", {}
        seen_rules.append(r)

        # Ensure consistent rule ID and initial priority
        if not r.get("id"):
            r["id"] = f"rule-{label}"
        if "active_priority" not in r:
            r["active_priority"] = 1

        valid, err = validate_rule(r)
        if not valid:
            return False, f"Rule for port {label} is invalid: {err}", {}
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
        for param in (
            "check_interval_seconds", "failure_threshold", "recovery_threshold",
            "fast_failover_enabled", "max_acceptable_loss", "cooldown_seconds",
            "hysteresis_percent", "loss_penalty_weight", "fast_probe_burst",
            "probe_count", "probe_interval_ms", "quality_window_seconds",
            "critical_loss_percent", "min_hold_seconds", "switch_confirm_seconds",
            "jitter_penalty_weight", "priority_bias_ms",
        ):
            if param in imported_cfg:
                current_cfg[param] = imported_cfg[param]
    else:  # merge
        current_rules = current_cfg.get("rules", [])
        rules_map = {str(r.get("port_range") or r.get("port")): r for r in current_rules if isinstance(r, dict)}
        for vr in validated_rules:
            rules_map[str(vr.get("port_range") or vr.get("port"))] = vr
        current_cfg["rules"] = list(rules_map.values())

    if save_config(current_cfg):
        return True, "", {
            "mode": mode,
            "count": len(current_cfg.get("rules", [])),
            "imported_count": len(validated_rules),
            "backup": os.path.basename(bak_path)
        }
    return False, "Failed to save configuration", {}

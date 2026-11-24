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
from urllib.parse import urlparse
from typing import Dict, Any, Tuple, Optional, List, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = "/etc/xforwarder/config.json"
LEGACY_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
STATE_FILE_PATH = "/run/xforwarder/state.json"
LEGACY_STATE_FILE_PATH = "/run/forward-manager/state.json"

HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")
IFACE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.\-]{0,14}$")
NFTABLES_TYPES = ("nftables", "nftables_dsr", "nftables_dsr_relay", "nftables_dsr_synack", "nftables_dsr_direct")
VALID_DEST_TYPES = ("haproxy", "nftables", "nftables_dsr", "nftables_dsr_relay", "nftables_dsr_synack", "nftables_dsr_direct", "nginx")
LB_SUPPORTED_TYPES = ("nftables", "nginx")
VALID_LB_MODES_NFT = ("ip_hash", "round_robin", "random")
VALID_LB_MODES_NGINX = ("ip_hash", "least_conn", "round_robin", "random")
MAX_LB_TARGETS = 16
VALID_UPDATE_TRANSPORT_MODES = ("auto", "direct", "iface", "proxy", "mirror")
VALID_PROXY_SCHEMES = ("http", "https", "socks5", "socks5h", "socks4")
_UNSAFE_URL_CHARS = set(";`$\\\"'<>|&\r\n\t ")


def _has_unsafe_url_chars(val: str) -> bool:
    """Returns True if a URL/proxy string contains control chars or shell metacharacters."""
    return any(ord(c) < 32 or ord(c) == 127 or c in _UNSAFE_URL_CHARS for c in val)


def validate_update_transport_config(raw: Any, require_target: bool = True) -> Tuple[bool, str, Dict[str, str]]:
    """Validates and normalizes `system_update` transport configuration against injection and malformed URLs."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return False, "system_update configuration must be an object", {}

    mode = str(raw.get("transport_mode", "auto") or "auto").strip().lower()
    if mode not in VALID_UPDATE_TRANSPORT_MODES:
        return False, f"Invalid transport_mode '{mode}'. Allowed: {', '.join(VALID_UPDATE_TRANSPORT_MODES)}", {}

    tunnel_iface = str(raw.get("tunnel_iface", "") or "").strip()
    if tunnel_iface:
        if not IFACE_NAME_REGEX.fullmatch(tunnel_iface):
            return False, f"Invalid tunnel_iface '{tunnel_iface}'", {}
    elif require_target and mode == "iface":
        return False, "tunnel_iface is required when transport_mode is 'iface'", {}

    proxy_url = str(raw.get("proxy_url", "") or "").strip()[:256]
    if proxy_url:
        if _has_unsafe_url_chars(proxy_url):
            return False, "Invalid characters in proxy_url", {}
        try:
            parsed = urlparse(proxy_url)
            if parsed.scheme.lower() not in VALID_PROXY_SCHEMES:
                return False, "proxy_url scheme must be socks5h, socks5, socks4, http, or https", {}
            if not parsed.hostname:
                return False, "proxy_url must include a valid host", {}
            if parsed.port is not None and not (1 <= parsed.port <= 65535):
                return False, "proxy_url port must be between 1 and 65535", {}
        except ValueError as e:
            return False, f"Invalid proxy_url: {e}", {}
    elif require_target and mode == "proxy":
        return False, "proxy_url is required when transport_mode is 'proxy'", {}

    mirror_url = str(raw.get("mirror_url", "") or "").strip()[:256]
    if mirror_url:
        if _has_unsafe_url_chars(mirror_url):
            return False, "Invalid characters in mirror_url", {}
        try:
            parsed = urlparse(mirror_url)
            if parsed.scheme.lower() not in ("http", "https"):
                return False, "mirror_url scheme must be http or https", {}
            if not parsed.hostname:
                return False, "mirror_url must include a valid host", {}
            if parsed.port is not None and not (1 <= parsed.port <= 65535):
                return False, "mirror_url port must be between 1 and 65535", {}
        except ValueError as e:
            return False, f"Invalid mirror_url: {e}", {}
    elif require_target and mode == "mirror":
        return False, "mirror_url is required when transport_mode is 'mirror'", {}

    clean = {
        "transport_mode": mode,
        "tunnel_iface": tunnel_iface,
        "proxy_url": proxy_url,
        "mirror_url": mirror_url,
    }
    return True, "", clean


def normalize_update_transport_config(raw: Any) -> Dict[str, str]:
    """Self-healing normalizer for `system_update` block inside config.json."""
    default_cfg = {
        "transport_mode": "auto",
        "tunnel_iface": "",
        "proxy_url": "",
        "mirror_url": "",
    }
    if not isinstance(raw, dict):
        return default_cfg
    mode = str(raw.get("transport_mode", "auto") or "auto").strip().lower()
    if mode not in VALID_UPDATE_TRANSPORT_MODES:
        mode = "auto"

    iface = str(raw.get("tunnel_iface", "") or "").strip()
    if iface and not IFACE_NAME_REGEX.fullmatch(iface):
        iface = ""

    proxy_url = str(raw.get("proxy_url", "") or "").strip()[:256]
    if proxy_url:
        ok_p, _, _ = validate_update_transport_config({"transport_mode": "proxy", "proxy_url": proxy_url}, require_target=False)
        if not ok_p:
            proxy_url = ""

    mirror_url = str(raw.get("mirror_url", "") or "").strip()[:256]
    if mirror_url:
        ok_m, _, _ = validate_update_transport_config({"transport_mode": "mirror", "mirror_url": mirror_url}, require_target=False)
        if not ok_m:
            mirror_url = ""

    return {
        "transport_mode": mode,
        "tunnel_iface": iface,
        "proxy_url": proxy_url,
        "mirror_url": mirror_url,
    }


def is_nftables_type(dest_type: Any) -> bool:
    """Returns True for standard NFTables DNAT as well as NFTables DSR modes."""
    return str(dest_type or "").lower().strip() in NFTABLES_TYPES


def sanitize_comment(raw: Any, max_len: int = 64) -> str:
    """Sanitizes user comments/labels against control chars and config/HTML delimiters."""
    s = str(raw or "").strip()[:max_len]
    return "".join(c for c in s if ord(c) >= 32 and c not in "<>\";`$\\{}")


def get_destination_backends(
    dest: Dict[str, Any],
    default_port: Optional[int] = None,
    default_port_range: Optional[str] = None,
    only_enabled: bool = True
) -> List[Dict[str, Any]]:
    """
    Returns normalized backend target entries for a destination.
    Supports both single-target destinations and load-balanced pools (`lb_enabled=True`).
    """
    if not isinstance(dest, dict):
        return []

    d_type = str(dest.get("type", "")).lower().strip()
    d_port = dest.get("port") if dest.get("port") is not None else default_port
    d_range = dest.get("port_range") or default_port_range
    d_iface = str(dest.get("tunnel_iface") or "").strip()

    if _coerce_bool(dest.get("lb_enabled"), False) and d_type in LB_SUPPORTED_TYPES:
        raw_members = dest.get("lb_targets")
        if isinstance(raw_members, list) and len(raw_members) > 0:
            members: List[Dict[str, Any]] = []
            for m in raw_members:
                if not isinstance(m, dict):
                    continue
                m_enabled = _coerce_bool(m.get("enabled"), True)
                if only_enabled and not m_enabled:
                    continue
                m_target = str(m.get("target", "")).strip().strip("[]")
                if not m_target:
                    continue
                m_port = m.get("port") if m.get("port") is not None else d_port
                try:
                    m_port_int = int(m_port) if m_port is not None and str(m_port).strip() != "" else None
                except (ValueError, TypeError):
                    m_port_int = None
                m_range = m.get("port_range")
                if not m_range and m.get("port") is None and d_range:
                    m_range = d_range
                try:
                    w = max(1, min(int(m.get("weight", 1)), 100))
                except (ValueError, TypeError):
                    w = 1
                m_iface = str(m.get("tunnel_iface") or "").strip()
                if d_type == "nftables" and not m_iface:
                    m_iface = d_iface
                elif d_type != "nftables":
                    m_iface = ""
                members.append({
                    "target": m_target,
                    "port": m_port_int,
                    "port_range": m_range,
                    "weight": w,
                    "tunnel_iface": m_iface,
                    "enabled": m_enabled,
                    "comment": sanitize_comment(m.get("comment", ""))
                })
            if members or only_enabled:
                return members

    d_enabled = _coerce_bool(dest.get("enabled"), True)
    if only_enabled and not d_enabled:
        return []
    raw_t = str(dest.get("target", "")).strip().strip("[]")
    if not raw_t:
        return []
    try:
        d_port_int = int(d_port) if d_port is not None and str(d_port).strip() != "" else None
    except (ValueError, TypeError):
        d_port_int = None
    return [{
        "target": raw_t,
        "port": d_port_int,
        "port_range": d_range,
        "weight": 1,
        "tunnel_iface": d_iface if d_type in ("nftables", "nftables_dsr", "nftables_dsr_synack") else "",
        "enabled": d_enabled,
        "comment": sanitize_comment(dest.get("comment", ""))
    }]


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

    if "api_keys" not in web or not isinstance(web["api_keys"], list):
        web["api_keys"] = []
        modified = True
    else:
        norm_keys = []
        for idx, k_item in enumerate(web["api_keys"]):
            if not isinstance(k_item, dict):
                modified = True
                continue
            k_id = str(k_item.get("id") or f"key_{idx + 1}").strip()
            k_name = sanitize_comment(k_item.get("name", "API Key")) or "API Key"
            k_prefix = str(k_item.get("prefix") or "xfwd_...").strip()[:32]
            k_hash = str(k_item.get("key_hash") or "").strip()
            if not k_hash:
                modified = True
                continue
            k_scope = str(k_item.get("scope") or "admin").strip().lower()
            if k_scope not in ("read", "write", "admin"):
                k_scope = "admin"
            k_enabled = _coerce_bool(k_item.get("enabled"), True)
            try:
                k_created = float(k_item.get("created_at") or 0.0)
            except (ValueError, TypeError):
                k_created = 0.0
            try:
                k_expires = float(k_item.get("expires_at") or 0.0)
            except (ValueError, TypeError):
                k_expires = 0.0
            try:
                k_last = float(k_item.get("last_used_at") or 0.0)
            except (ValueError, TypeError):
                k_last = 0.0
            norm_entry = {
                "id": k_id,
                "name": k_name,
                "prefix": k_prefix,
                "key_hash": k_hash,
                "scope": k_scope,
                "enabled": k_enabled,
                "created_at": k_created,
                "expires_at": k_expires,
                "last_used_at": k_last,
            }
            if norm_entry != k_item:
                modified = True
            norm_keys.append(norm_entry)
        if web["api_keys"] != norm_keys:
            web["api_keys"] = norm_keys
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
            else:
                clean_c = sanitize_comment(d.get("comment", ""))
                if d.get("comment") != clean_c:
                    d["comment"] = clean_c
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

            for ip_key in ("spoof_ip", "snat_ip"):
                if ip_key in d:
                    clean_ip = str(d.get(ip_key) or "").strip().strip("[]")
                    if not clean_ip:
                        d.pop(ip_key, None)
                        modified = True
                    elif d.get(ip_key) != clean_ip:
                        d[ip_key] = clean_ip
                        modified = True

            if "ingress_iface" in d:
                clean_in_if = str(d.get("ingress_iface") or "").strip()
                if not clean_in_if:
                    d.pop("ingress_iface", None)
                    modified = True
                elif d.get("ingress_iface") != clean_in_if:
                    d["ingress_iface"] = clean_in_if
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

            # Normalize load-balancing pool fields (backward-compatible opt-in)
            lb_enabled = _coerce_bool(d.get("lb_enabled"), False)
            if lb_enabled and dtype in LB_SUPPORTED_TYPES and isinstance(d.get("lb_targets"), list) and len(d["lb_targets"]) > 0:
                valid_modes = VALID_LB_MODES_NFT if dtype == "nftables" else VALID_LB_MODES_NGINX
                lb_mode = str(d.get("lb_mode") or "ip_hash").lower().strip()
                if lb_mode not in valid_modes:
                    lb_mode = "ip_hash"
                if d.get("lb_enabled") is not True:
                    d["lb_enabled"] = True
                    modified = True
                if d.get("lb_mode") != lb_mode:
                    d["lb_mode"] = lb_mode
                    modified = True
                norm_members: List[Dict[str, Any]] = []
                for m in d["lb_targets"][:MAX_LB_TARGETS]:
                    if not isinstance(m, dict):
                        modified = True
                        continue
                    m_target = str(m.get("target", "")).strip().strip("[]")
                    if not m_target:
                        modified = True
                        continue
                    m_obj: Dict[str, Any] = {
                        "target": m_target,
                        "weight": 1,
                        "enabled": _coerce_bool(m.get("enabled"), True),
                        "comment": sanitize_comment(m.get("comment", ""))
                    }
                    try:
                        m_obj["weight"] = max(1, min(int(m.get("weight", 1)), 100))
                    except (ValueError, TypeError):
                        m_obj["weight"] = 1
                    raw_mport = m.get("port_range") or m.get("port")
                    if raw_mport is not None and str(raw_mport).strip() != "":
                        msp, _, mrange = parse_port_spec(raw_mport)
                        if msp is not None:
                            m_obj["port"] = msp
                            if mrange:
                                m_obj["port_range"] = mrange
                        else:
                            m_obj["port"] = d.get("port", port)
                            if prange:
                                m_obj["port_range"] = prange
                    else:
                        m_obj["port"] = d.get("port", port)
                        if prange:
                            m_obj["port_range"] = prange
                    m_iface = str(m.get("tunnel_iface") or "").strip()
                    if dtype == "nftables" and m_iface:
                        m_obj["tunnel_iface"] = m_iface
                    norm_members.append(m_obj)
                if norm_members:
                    if d.get("lb_targets") != norm_members:
                        d["lb_targets"] = norm_members
                        modified = True
                    primary_m = next((x for x in norm_members if x.get("enabled", True)), norm_members[0])
                    if d.get("target") != primary_m["target"]:
                        d["target"] = primary_m["target"]
                        modified = True
                    if d.get("port") != primary_m.get("port"):
                        d["port"] = primary_m.get("port")
                        modified = True
                else:
                    for lb_k in ("lb_enabled", "lb_mode", "lb_targets"):
                        if lb_k in d:
                            d.pop(lb_k, None)
                            modified = True
            else:
                for lb_k in ("lb_enabled", "lb_mode", "lb_targets"):
                    if lb_k in d:
                        d.pop(lb_k, None)
                        modified = True

    norm_update = normalize_update_transport_config(cfg.get("system_update"))
    if cfg.get("system_update") != norm_update:
        cfg["system_update"] = norm_update
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


def _mutate_state_rules(mutator, state_path: Optional[str] = None) -> None:
    """Atomically loads, mutates, and persists runtime.rules_state in state.json."""
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
        mutator(rs)
        tmp_p = f"{path}.tmp.{os.getpid()}"
        with open(tmp_p, "w", encoding="utf-8") as tf:
            json.dump(st, tf, indent=2, ensure_ascii=False)
        os.replace(tmp_p, path)
    except Exception:
        pass


def update_state_rules(rule_updates: Dict[str, dict], state_path: Optional[str] = None) -> None:
    """Synchronizes active_priority and force_override in state.json atomically."""
    def _apply(rs: dict) -> None:
        for r_id, vals in rule_updates.items():
            r_entry = rs.setdefault(r_id, {})
            r_entry.update(vals)
    _mutate_state_rules(_apply, state_path=state_path)


def remove_state_rules(rule_ids: List[str], state_path: Optional[str] = None) -> None:
    """Purges deleted rule IDs from runtime.rules_state atomically so future rules start clean."""
    if not rule_ids:
        return
    def _purge(rs: dict) -> None:
        for r_id in rule_ids:
            rs.pop(r_id, None)
    _mutate_state_rules(_purge, state_path=state_path)


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

    # Validate optional per-rule failover/latency overrides
    if "force_override" in body and body.get("force_override") is not None:
        if isinstance(body.get("force_override"), bool):
            return False, "force_override must be a non-negative integer"
        try:
            fov = int(body.get("force_override", 0))
            if fov < 0:
                return False, "force_override cannot be negative"
            body["force_override"] = fov
        except (ValueError, TypeError):
            return False, "force_override must be a non-negative integer"

    if "active_priority" in body and body.get("active_priority") is not None:
        if isinstance(body.get("active_priority"), bool):
            return False, "active_priority must be a positive integer"
        try:
            ap = int(body.get("active_priority", 1))
            if ap < 1:
                return False, "active_priority must be 1 or greater"
            body["active_priority"] = ap
        except (ValueError, TypeError):
            return False, "active_priority must be a positive integer"

    if "max_primary_latency_ms" in body:
        raw_mpl = body.get("max_primary_latency_ms")
        if raw_mpl is None or raw_mpl == "":
            body.pop("max_primary_latency_ms", None)
        elif isinstance(raw_mpl, bool):
            return False, "max_primary_latency_ms must be an integer between 50 and 1000"
        else:
            try:
                mpl = int(raw_mpl)
                if not (50 <= mpl <= 1000):
                    return False, "max_primary_latency_ms must be between 50 and 1000"
                body["max_primary_latency_ms"] = mpl
            except (ValueError, TypeError):
                return False, "max_primary_latency_ms must be an integer between 50 and 1000"

    dests = body.get("destinations", [])
    if not isinstance(dests, list) or len(dests) == 0:
        return False, "At least one destination is required"

    for d in dests:
        if not isinstance(d, dict):
            return False, "Invalid destination item"
        d["comment"] = sanitize_comment(d.get("comment", ""))
        lb_enabled = _coerce_bool(d.get("lb_enabled"), False)

        # Peek at type early so LB pools can auto-sync primary target before top-level validation
        raw_d_type = str(d.get("type", "")).lower().strip()
        if lb_enabled:
            if not raw_d_type:
                raw_d_type = "nftables" if port_range_str else "nginx"
            if raw_d_type not in LB_SUPPORTED_TYPES:
                return False, f"Load balancing is only supported for 'nftables' and 'nginx' (not '{raw_d_type}')"
            d["type"] = raw_d_type
            raw_lb_targets = d.get("lb_targets")
            if not isinstance(raw_lb_targets, list) or len(raw_lb_targets) < 2:
                return False, "Load balancing requires at least 2 backend targets"
            if len(raw_lb_targets) > MAX_LB_TARGETS:
                return False, f"Load-balanced pool cannot exceed {MAX_LB_TARGETS} targets"

            valid_modes = VALID_LB_MODES_NFT if raw_d_type == "nftables" else VALID_LB_MODES_NGINX
            lb_mode = str(d.get("lb_mode") or "ip_hash").lower().strip()
            if lb_mode not in valid_modes:
                return False, f"Invalid load-balancing mode '{lb_mode}' for {raw_d_type}. Allowed: {', '.join(valid_modes)}"
            d["lb_enabled"] = True
            d["lb_mode"] = lb_mode

            seen_endpoints: Set[Tuple[str, Any]] = set()
            nft_ip_versions: Set[int] = set()
            range_port_modes: Set[str] = set()
            enabled_members_count = 0
            sanitized_members: List[Dict[str, Any]] = []

            for m_idx, m in enumerate(raw_lb_targets):
                if not isinstance(m, dict):
                    return False, f"Invalid load-balance target item at #{m_idx + 1}"
                m_target = str(m.get("target", "")).strip()
                if not m_target:
                    return False, f"Load-balance target #{m_idx + 1} cannot be empty"
                if any(c in m_target for c in ";&|`$ \t\n\r<>\"'"):
                    return False, f"Load-balance target #{m_idx + 1} contains invalid characters"
                if not is_valid_target(m_target):
                    return False, f"Invalid load-balance target '{m_target}'. Must be a valid IPv4, IPv6, or hostname"

                clean_m_target = m_target.strip("[]")
                if raw_d_type == "nftables":
                    try:
                        m_ip_obj = ipaddress.ip_address(clean_m_target)
                        nft_ip_versions.add(m_ip_obj.version)
                    except ValueError:
                        return False, f"NFTables load-balance target must be a valid IPv4 or IPv6 address (got '{m_target}')"
                    if len(nft_ip_versions) > 1:
                        return False, "NFTables load-balanced pool requires all targets to use the same IP version (all IPv4 or all IPv6)"

                raw_mport = m.get("port_range") if m.get("port_range") else m.get("port")
                m_obj: Dict[str, Any] = {
                    "target": clean_m_target,
                    "enabled": _coerce_bool(m.get("enabled"), True),
                    "comment": sanitize_comment(m.get("comment", ""))
                }
                if m_obj["enabled"]:
                    enabled_members_count += 1

                if raw_mport is None or str(raw_mport).strip() == "":
                    m_obj["port"] = start_p
                    if port_range_str:
                        m_obj["port_range"] = port_range_str
                        range_port_modes.add("range")
                else:
                    m_sp, _, m_range_str = parse_port_spec(raw_mport)
                    if m_sp is None:
                        return False, f"Load-balance target #{m_idx + 1} port must be between 1 and 65535 (or a valid matching range)"
                    if m_range_str:
                        if raw_d_type != "nftables":
                            return False, f"Destination port range '{m_range_str}' is only supported for 'nftables'"
                        if not port_range_str or m_range_str != port_range_str:
                            return False, f"NFTables outbound port range must match inbound range ({port_range_str or start_p}) or be a single target port"
                        m_obj["port"] = m_sp
                        m_obj["port_range"] = m_range_str
                        range_port_modes.add("range")
                    else:
                        m_obj["port"] = m_sp
                        if port_range_str:
                            range_port_modes.add("fixed")

                if port_range_str and raw_d_type == "nftables" and len(range_port_modes) > 1:
                    return False, "NFTables range load-balanced pool requires all targets to either preserve the 1:1 range or target a single port"

                ep_key = (clean_m_target.lower(), m_obj.get("port_range") or m_obj["port"])
                if ep_key in seen_endpoints:
                    return False, f"Duplicate backend endpoint '{clean_m_target}:{ep_key[1]}' in load-balanced pool"
                seen_endpoints.add(ep_key)

                try:
                    m_weight = int(m.get("weight", 1))
                except (ValueError, TypeError):
                    return False, f"Load-balance target #{m_idx + 1} weight must be an integer"
                if m_weight < 1 or m_weight > 100:
                    return False, f"Load-balance target #{m_idx + 1} weight must be between 1 and 100"
                m_obj["weight"] = m_weight

                raw_m_iface = str(m.get("tunnel_iface") or "").strip()
                if raw_m_iface and raw_d_type == "nftables":
                    if not IFACE_NAME_REGEX.match(raw_m_iface):
                        return False, f"Invalid tunnel interface '{raw_m_iface}' on load-balance target #{m_idx + 1}"
                    m_obj["tunnel_iface"] = raw_m_iface

                sanitized_members.append(m_obj)

            if enabled_members_count < 1:
                return False, "Load-balanced pool must have at least 1 enabled target"

            d["lb_targets"] = sanitized_members
            primary_m = next((x for x in sanitized_members if x["enabled"]), sanitized_members[0])
            d["target"] = primary_m["target"]
            d["port"] = primary_m["port"]
            if primary_m.get("port_range"):
                d["port_range"] = primary_m["port_range"]
            else:
                d.pop("port_range", None)
            if primary_m.get("tunnel_iface") and not d.get("tunnel_iface"):
                d["tunnel_iface"] = primary_m["tunnel_iface"]
        else:
            d.pop("lb_enabled", None)
            d.pop("lb_mode", None)
            d.pop("lb_targets", None)

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
        elif d_type not in VALID_DEST_TYPES:
            return False, "Destination type must be 'haproxy', 'nftables', 'nftables_dsr', 'nftables_dsr_relay', 'nftables_dsr_synack', 'nftables_dsr_direct', or 'nginx'"
        d["type"] = d_type

        if port_range_str and not is_nftables_type(d_type):
            return False, f"Port ranges / exclusions ({port_range_str}) are only supported for 'nftables' destinations (not '{d_type}')"

        if d_type in ("nftables_dsr_synack", "nftables_dsr_direct"):
            if port_range_str or body.get("excluded_ports"):
                return False, f"Port ranges / exclusions are not supported for '{d_type}' (single TCP port only)"
            if proto != "tcp":
                return False, "NFTables DSR (SYN-ACK / Direct) supports TCP only — set rule protocol to 'tcp'"

        target_ip_obj = None
        if d_type == "haproxy":
            clean_target = target.strip("[]")
            try:
                ip_obj = ipaddress.ip_address(clean_target)
                if ip_obj.version != 6:
                    return False, f"HAProxy destination target must be a valid IPv6 address (got IPv4 '{target}')"
            except ValueError:
                return False, f"HAProxy destination target must be a valid IPv6 address (got '{target}')"
        elif is_nftables_type(d_type):
            # NFTables kernel rules require raw numeric IPv4 or IPv6 addresses.
            # Hostnames/domains cause syntax errors during atomic ruleset commit ('nft -c -f').
            clean_target = target.strip("[]")
            try:
                target_ip_obj = ipaddress.ip_address(clean_target)
            except ValueError:
                return False, f"NFTables destination target must be a valid IPv4 or IPv6 address (got '{target}')"
            if d_type in ("nftables_dsr_synack", "nftables_dsr_direct") and target_ip_obj.version != 4:
                return False, f"'{d_type}' currently supports IPv4 targets only (got IPv6 '{target}')"

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
                if not is_nftables_type(d_type):
                    return False, f"Destination port range '{d_range_str}' is only supported for 'nftables' (not '{d_type}')"
                if not port_range_str or d_range_str != port_range_str:
                    return False, f"NFTables outbound port range must match inbound range ({port_range_str or start_p}) or be a single target port"
                d["port"] = d_sp
                d["port_range"] = d_range_str
            else:
                if d_type == "nftables_dsr" and (port_range_str or d_sp != start_p):
                    return False, f"NFTables DSR (stateless) requires destination port to match inbound port ({port_range_str or start_p})"
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

        # Optional custom outbound tunnel interface (NFTables masquerade + ping -I isolation)
        raw_iface = str(d.get("tunnel_iface") or "").strip()
        if raw_iface:
            if d_type not in ("nftables", "nftables_dsr", "nftables_dsr_synack"):
                d.pop("tunnel_iface", None)
            elif not IFACE_NAME_REGEX.match(raw_iface):
                return False, f"Invalid tunnel interface '{raw_iface}'. Must be 1-15 alphanumeric, '.', '_', or '-' characters"
            else:
                d["tunnel_iface"] = raw_iface
        else:
            d.pop("tunnel_iface", None)

        # DSR fields: spoof_ip (required for nftables_dsr_relay / nftables_dsr_direct,
        # optional ingress IP filter/rewrite for nftables_dsr / nftables_dsr_synack),
        # ingress_iface (optional for nftables_dsr_relay, required for nftables_dsr_direct),
        # snat_ip (optional explicit SNAT IP for nftables_dsr_relay).
        raw_spoof_ip = str(d.get("spoof_ip") or "").strip().strip("[]")
        if d_type in ("nftables_dsr", "nftables_dsr_relay", "nftables_dsr_synack", "nftables_dsr_direct"):
            if raw_spoof_ip:
                try:
                    spoof_obj = ipaddress.ip_address(raw_spoof_ip)
                except ValueError:
                    return False, f"Invalid Spoof/Ingress IP '{raw_spoof_ip}'. Must be a valid IPv4 or IPv6 address"
                if target_ip_obj is not None and spoof_obj.version != target_ip_obj.version:
                    return False, f"Spoof/Ingress IP '{raw_spoof_ip}' must match target IP version (IPv{target_ip_obj.version})"
                d["spoof_ip"] = raw_spoof_ip
            elif d_type == "nftables_dsr_relay":
                return False, "NFTables DSR Relay requires 'spoof_ip' (the Iran/ingress server public IP)"
            elif d_type == "nftables_dsr_direct":
                return False, "NFTables DSR Direct requires 'spoof_ip' (the Iran/ingress server public IP)"
            else:
                d.pop("spoof_ip", None)
        else:
            d.pop("spoof_ip", None)

        raw_in_iface = str(d.get("ingress_iface") or "").strip()
        if d_type in ("nftables_dsr_relay", "nftables_dsr_direct"):
            if raw_in_iface:
                if not IFACE_NAME_REGEX.match(raw_in_iface):
                    return False, f"Invalid inbound tunnel interface '{raw_in_iface}'. Must be 1-15 alphanumeric, '.', '_', or '-' characters"
                d["ingress_iface"] = raw_in_iface
            elif d_type == "nftables_dsr_direct":
                return False, "NFTables DSR Direct (Outside) requires 'ingress_iface' (the tunnel interface receiving traffic from Iran)"
            else:
                d.pop("ingress_iface", None)
        else:
            d.pop("ingress_iface", None)

        raw_snat_ip = str(d.get("snat_ip") or "").strip().strip("[]")
        if d_type == "nftables_dsr_relay" and raw_snat_ip:
            try:
                snat_obj = ipaddress.ip_address(raw_snat_ip)
            except ValueError:
                return False, f"Invalid SNAT IP '{raw_snat_ip}'. Must be a valid IPv4 or IPv6 address"
            if target_ip_obj is not None and snat_obj.version != target_ip_obj.version:
                return False, f"SNAT IP '{raw_snat_ip}' must match target IP version (IPv{target_ip_obj.version})"
            d["snat_ip"] = raw_snat_ip
        else:
            d.pop("snat_ip", None)

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


def sanitize_config_for_api(cfg: Optional[dict]) -> dict:
    """Returns a copy of configuration with password hashes and API key hashes redacted."""
    if not isinstance(cfg, dict):
        return {}
    clean = json.loads(json.dumps(cfg))
    web = clean.get("web")
    if isinstance(web, dict):
        auth = web.get("auth")
        if isinstance(auth, dict) and "password_hash" in auth:
            auth.pop("password_hash", None)
        if isinstance(web.get("api_keys"), list):
            safe_keys = []
            for k in web["api_keys"]:
                if isinstance(k, dict):
                    k_copy = {fn: fv for fn, fv in k.items() if fn != "key_hash"}
                    safe_keys.append(k_copy)
            web["api_keys"] = safe_keys
    return clean


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

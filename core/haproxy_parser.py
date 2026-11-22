#!/usr/bin/env python3
"""
XForwarder - HAProxy Configuration Parser & Importer
Discovers and extracts pre-existing HAProxy forwarding ports,
targets, and protocols to seamlessly import them into XForwarder.
100% Native Python 3 standard library.
"""

import os
import sys
import re
import glob
import json
import time
import shutil
import ipaddress
import logging
from typing import List, Dict, Any, Tuple, Optional, Set

try:
    from core.config_manager import (
        rules_ports_overlap, get_rule_port_bounds, get_protected_ports, validate_rule
    )
except ImportError:
    from config_manager import (
        rules_ports_overlap, get_rule_port_bounds, get_protected_ports, validate_rule
    )

logger = logging.getLogger("xforwarder.haproxy_parser")

BIND_PORT_REGEX = re.compile(
    r"^\s*bind\s+(?:(?:(?:\*|0\.0\.0\.0|::|\[::\]|[0-9\.]+|\[[0-9a-fA-F:]+\]):)?|(?:\s*))(\d{1,5})\b",
    re.IGNORECASE
)

SERVER_REGEX = re.compile(
    r"^\s*server\s+\S+\s+(\[[0-9a-fA-F:]+\]|[0-9\.]+|[a-zA-Z0-9\.\-_]+)(?::(\d{1,5}))?",
    re.IGNORECASE
)

DEFAULT_BACKEND_REGEX = re.compile(
    r"^\s*default_backend\s+(\S+)",
    re.IGNORECASE
)

USE_BACKEND_REGEX = re.compile(
    r"^\s*use_backend\s+(\S+)",
    re.IGNORECASE
)


def parse_haproxy_content(content: str) -> List[Dict[str, Any]]:
    """
    Parses HAProxy configuration text and extracts list/frontend rules.
    Returns a list of XForwarder-compatible rule dictionaries.
    """
    lines = content.splitlines()

    sections: List[Dict[str, Any]] = []
    current_sec: Optional[Dict[str, Any]] = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Check section headers
        parts = line.split()
        header = parts[0].lower()
        if header in ("listen", "frontend", "backend"):
            sec_name = parts[1] if len(parts) > 1 else f"sec_{len(sections)}"
            current_sec = {
                "type": header,
                "name": sec_name,
                "bind_ports": [],
                "servers": [],
                "backends": [],
                "mode": "tcp"
            }
            sections.append(current_sec)
            continue

        if current_sec is None:
            continue

        # Check mode
        if header == "mode" and len(parts) > 1:
            current_sec["mode"] = parts[1].lower()
            continue

        # Check bind
        bind_match = BIND_PORT_REGEX.match(line)
        if bind_match:
            try:
                p = int(bind_match.group(1))
                if 1 <= p <= 65535 and p not in current_sec["bind_ports"]:
                    current_sec["bind_ports"].append(p)
            except (ValueError, TypeError):
                pass
            continue

        # Check server
        srv_match = SERVER_REGEX.match(line)
        if srv_match:
            raw_target = srv_match.group(1).strip().strip("[]")
            raw_port = srv_match.group(2)
            has_send_proxy = bool(re.search(r"\bsend-proxy(-v2)?\b", line, re.IGNORECASE))
            current_sec["servers"].append({
                "target": raw_target,
                "port": int(raw_port) if raw_port else None,
                "proxy_protocol": has_send_proxy
            })
            continue

        # Check backend pointers
        def_be = DEFAULT_BACKEND_REGEX.match(line)
        if def_be:
            current_sec["backends"].append(def_be.group(1))
            continue
        use_be = USE_BACKEND_REGEX.match(line)
        if use_be:
            current_sec["backends"].append(use_be.group(1))
            continue

    # Map backends by name for frontend resolution
    backends_by_name = {
        s["name"]: s for s in sections if s["type"] == "backend"
    }

    rules: List[Dict[str, Any]] = []
    seen_ports = set()

    for sec in sections:
        sec_type = sec["type"]
        sec_name = sec["name"]

        # Case 1: listen block (has both bind and server)
        if sec_type == "listen":
            for port in sec["bind_ports"]:
                if port in seen_ports:
                    continue
                srv = sec["servers"][0] if sec["servers"] else None
                if not srv or not srv.get("target"):
                    continue

                target = srv["target"]
                target_port = srv.get("port") or port
                proxy_protocol = bool(srv.get("proxy_protocol", False))

                rules.append(_build_xforwarder_rule(port, target, target_port, sec_name, proxy_protocol))
                seen_ports.add(port)

        # Case 2: frontend block (resolves to backend)
        elif sec_type == "frontend":
            for port in sec["bind_ports"]:
                if port in seen_ports:
                    continue

                # Find associated backend
                target = None
                target_port = port
                proxy_protocol = False
                for be_name in sec["backends"]:
                    be = backends_by_name.get(be_name)
                    if be and be["servers"]:
                        srv = be["servers"][0]
                        target = srv.get("target")
                        target_port = srv.get("port") or port
                        proxy_protocol = bool(srv.get("proxy_protocol", False))
                        break

                if target:
                    rules.append(_build_xforwarder_rule(port, target, target_port, sec_name, proxy_protocol))
                    seen_ports.add(port)

    return rules


def _build_xforwarder_rule(port: int, target: str, target_port: int, sec_name: str, proxy_protocol: bool = False) -> Dict[str, Any]:
    """Constructs a valid XForwarder rule from an HAProxy section without injecting phantom backup IPs."""
    clean_target = str(target or "").strip().strip("[]")
    is_ipv6 = False
    is_numeric_ip = False
    try:
        ip_obj = ipaddress.ip_address(clean_target)
        is_ipv6 = (ip_obj.version == 6)
        is_numeric_ip = True
    except ValueError:
        pass

    # In XForwarder, HAProxy type is IPv6-only; IPv4 routes map to Nginx (or NFTables if IPv4 IP and Nginx absent)
    if is_ipv6:
        dest_type = "haproxy"
    elif shutil.which("nginx") or not is_numeric_ip:
        dest_type = "nginx"
    else:
        dest_type = "nftables"

    return {
        "id": f"rule-{port}",
        "port": port,
        "protocol": "both",
        "active_priority": 1,
        "force_override": 0,
        "destinations": [
            {
                "priority": 1,
                "type": dest_type,
                "target": clean_target,
                "port": target_port,
                "proxy_protocol": proxy_protocol if dest_type == "haproxy" else False,
                "enabled": True,
                "is_relay": False,
                "comment": f"Imported from HAProxy ({sec_name})"
            }
        ]
    }


def _is_xforwarder_managed_haproxy(file_path: str) -> bool:
    """Returns True if file_path starts with an XForwarder-generated header."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(512)
        return "# Generated by XForwarder" in head
    except Exception:
        return False


def parse_haproxy_file(file_path: str) -> List[Dict[str, Any]]:
    """Safely reads and parses an unmanaged HAProxy config file (skips XForwarder-generated files)."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "# Generated by XForwarder" in content[:512]:
            return []
        return parse_haproxy_content(content)
    except Exception as e:
        logger.warning(f"Failed to read HAProxy file {file_path}: {e}")
        return []


def find_candidate_haproxy_files() -> List[str]:
    """
    Finds unmanaged /etc/haproxy/haproxy.cfg and legacy backup files.
    Skips .bak* files once XForwarder already owns /etc/haproxy/haproxy.cfg so deleted rules never re-appear.
    """
    candidates = []
    main_cfg = "/etc/haproxy/haproxy.cfg"
    if os.path.exists(main_cfg):
        if _is_xforwarder_managed_haproxy(main_cfg):
            # Panel already took over HAProxy; do not re-discover deleted rules from old .bak files
            return []
        candidates.append(main_cfg)

    bak_patterns = [
        "/etc/haproxy/haproxy.cfg.bak*",
        "/etc/haproxy/*.bak",
        "/etc/haproxy/*.backup"
    ]
    baks = []
    for pattern in bak_patterns:
        baks.extend(glob.glob(pattern))

    baks = sorted(set(baks), key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    candidates.extend(baks)
    return candidates


def archive_legacy_haproxy_files(backup_dir: str = "/etc/xforwarder/backups") -> List[str]:
    """Moves legacy HAProxy backup files out of /etc/haproxy/ into /etc/xforwarder/backups/."""
    logs: List[str] = []
    bak_patterns = [
        "/etc/haproxy/haproxy.cfg.bak*",
        "/etc/haproxy/*.bak",
        "/etc/haproxy/*.backup"
    ]
    found: List[str] = []
    for pat in bak_patterns:
        for p in glob.glob(pat):
            if os.path.isfile(p) and p not in found:
                found.append(p)
    if not found:
        return logs

    ts = time.strftime("%Y%m%d_%H%M%S")
    dest_dir = os.path.join(backup_dir, f"legacy_haproxy_{ts}")
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create HAProxy archive dir {dest_dir}: {e}")
        return logs

    for src in found:
        try:
            dst = os.path.join(dest_dir, os.path.basename(src))
            shutil.move(src, dst)
            logs.append(f"Archived legacy HAProxy backup {src} -> {dst}")
        except Exception as e:
            logger.warning(f"Failed to archive {src}: {e}")
    return logs


def discover_importable_rules(
    existing_rules: Optional[List[Dict[str, Any]]] = None,
    protected_ports: Optional[Set[int]] = None
) -> List[Dict[str, Any]]:
    """
    Scans candidate HAProxy configs and returns rules whose port does not overlap
    existing_rules (including ranges and exclusions) or protected_ports.
    """
    configured_rules: List[Dict[str, Any]] = [
        r for r in (existing_rules or [])
        if isinstance(r, dict) and get_rule_port_bounds(r)[0] is not None
    ]
    prot = set(protected_ports or {22})
    discovered_rules: List[Dict[str, Any]] = []

    for path in find_candidate_haproxy_files():
        for r in parse_haproxy_file(path):
            p = r.get("port")
            if not p or p in prot:
                continue
            if any(rules_ports_overlap(r, ex) for ex in configured_rules):
                continue
            if any(rules_ports_overlap(r, disc) for disc in discovered_rules):
                continue
            ok, _ = validate_rule(dict(r))
            if ok:
                discovered_rules.append(r)

    return discovered_rules


def import_haproxy_rules_into_config(
    config_path: str,
    protected_ports: Optional[Set[int]] = None,
    archive_legacy: bool = True
) -> Tuple[int, List[int]]:
    """
    Discovers unimported HAProxy rules and appends them to config_path atomically.
    Archives legacy HAProxy backups so deleted panel rules cannot reappear.
    Returns (imported_count, list_of_imported_ports).
    """
    if not os.path.exists(config_path):
        return 0, []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"Cannot read config file {config_path}: {e}")
        return 0, []

    rules = cfg.get("rules", [])
    eff_prot = protected_ports if protected_ports is not None else get_protected_ports(cfg)
    importable = discover_importable_rules(rules, protected_ports=eff_prot)

    if not importable:
        return 0, []

    imported_ports = []
    for r in importable:
        clean_r = {k: v for k, v in r.items() if not k.startswith("_")}
        rules.append(clean_r)
        imported_ports.append(clean_r["port"])

    cfg["rules"] = rules

    # Atomic write
    tmp_path = f"{config_path}.tmp.{os.getpid()}"
    try:
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, config_path)
        if archive_legacy:
            archive_legacy_haproxy_files()
        return len(imported_ports), imported_ports
    except Exception as e:
        logger.error(f"Failed to save imported rules to {config_path}: {e}")
        return 0, []

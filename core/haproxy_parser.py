#!/usr/bin/env python3
"""
XForwarder - HAProxy Configuration Parser & Importer
Discovers and extracts pre-existing HAProxy forwarding ports,
targets, and protocols to seamlessly import them into XForwarder.
100% Native Python 3 standard library.
"""

import os
import re
import glob
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

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
            current_sec["servers"].append({
                "target": raw_target,
                "port": int(raw_port) if raw_port else None
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

                rules.append(_build_xforwarder_rule(port, target, target_port, sec_name))
                seen_ports.add(port)

        # Case 2: frontend block (resolves to backend)
        elif sec_type == "frontend":
            for port in sec["bind_ports"]:
                if port in seen_ports:
                    continue

                # Find associated backend
                target = None
                target_port = port
                for be_name in sec["backends"]:
                    be = backends_by_name.get(be_name)
                    if be and be["servers"]:
                        srv = be["servers"][0]
                        target = srv.get("target")
                        target_port = srv.get("port") or port
                        break

                if target:
                    rules.append(_build_xforwarder_rule(port, target, target_port, sec_name))
                    seen_ports.add(port)

    return rules


def _build_xforwarder_rule(port: int, target: str, target_port: int, sec_name: str) -> Dict[str, Any]:
    return {
        "id": f"rule-{port}",
        "port": port,
        "protocol": "both",
        "active_priority": 1,
        "force_override": 0,
        "destinations": [
            {
                "priority": 1,
                "type": "haproxy",
                "target": target,
                "port": target_port,
                "comment": f"Imported from HAProxy ({sec_name})"
            },
            {
                "priority": 2,
                "type": "nftables",
                "target": "10.88.1.2",
                "port": target_port,
                "comment": "Backup Tunnel"
            }
        ]
    }


def parse_haproxy_file(file_path: str) -> List[Dict[str, Any]]:
    """Safely reads and parses a HAProxy config file."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return parse_haproxy_content(content)
    except Exception as e:
        logger.warning(f"Failed to read HAProxy file {file_path}: {e}")
        return []


def find_candidate_haproxy_files() -> List[str]:
    """Finds existing /etc/haproxy/haproxy.cfg and backup files sorted by modification time."""
    candidates = []

    # 1. Main active config
    main_cfg = "/etc/haproxy/haproxy.cfg"
    if os.path.exists(main_cfg):
        candidates.append(main_cfg)

    # 2. Backup files in /etc/haproxy/
    bak_patterns = [
        "/etc/haproxy/haproxy.cfg.bak*",
        "/etc/haproxy/*.bak",
        "/etc/haproxy/*.backup"
    ]
    baks = []
    for pattern in bak_patterns:
        baks.extend(glob.glob(pattern))

    # Sort backups by modification time (newest first)
    baks = sorted(set(baks), key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    candidates.extend(baks)

    return candidates


def discover_importable_rules(existing_rules: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Scans candidate HAProxy configs and returns rules for ports NOT currently in existing_rules.
    """
    configured_ports = set()
    if existing_rules:
        for r in existing_rules:
            if "port" in r:
                try:
                    configured_ports.add(int(r["port"]))
                except (ValueError, TypeError):
                    pass

    discovered_rules: List[Dict[str, Any]] = []
    discovered_ports = set()

    for path in find_candidate_haproxy_files():
        rules = parse_haproxy_file(path)
        for r in rules:
            p = r.get("port")
            if p and p not in configured_ports and p not in discovered_ports:
                discovered_rules.append(r)
                discovered_ports.add(p)

    return discovered_rules


def import_haproxy_rules_into_config(config_path: str) -> Tuple[int, List[int]]:
    """
    Discovers unimported HAProxy rules and appends them to config_path atomically.
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
    importable = discover_importable_rules(rules)

    if not importable:
        return 0, []

    imported_ports = []
    for r in importable:
        rules.append(r)
        imported_ports.append(r["port"])

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
        return len(imported_ports), imported_ports
    except Exception as e:
        logger.error(f"Failed to save imported rules to {config_path}: {e}")
        return 0, []

#!/usr/bin/env python3
"""
XForwarder - NFTables & Kernel DNAT Configuration Parser & Importer
Discovers and extracts pre-existing active NFTables and iptables DNAT rules,
inbound ports, and destination targets to seamlessly import them into XForwarder.
Provides automatic backup and safe deactivation of legacy rules to eliminate port collisions.
100% Native Python 3 standard library.
"""

import os
import re
import glob
import json
import shutil
import subprocess
import time
import logging
import ipaddress
from typing import List, Dict, Any, Tuple, Optional, Set

logger = logging.getLogger("xforwarder.nftables_parser")

MANAGED_TABLES = {"xfwd_orchestrator", "fwdman_orchestrator"}

# Matches textual DNAT targets:
# Examples:
#   dnat to 10.88.1.2:8443
#   dnat to [2001:db8::1]:8443
#   dnat ip to 10.88.1.2:8443
#   dnat ip6 to [2001:db8::1]:8443
#   dnat to 10.88.1.2
DNAT_TARGET_REGEX = re.compile(
    r"\bdnat(?:\s+(?:ip|ip6))?\s+to\s+(?:\[([0-9a-fA-F:]+)\]|([0-9\.]+)|([a-zA-Z0-9\.\-_]+))(?::(\d{1,5}))?",
    re.IGNORECASE
)

# Matches port expressions in textual NFTables:
# Examples:
#   tcp dport 8443
#   udp dport 2083
#   th dport 8443
#   dport 8443
DPORT_REGEX = re.compile(
    r"(?:(tcp|udp|th)\s+)?dport\s+(\d{1,5})\b",
    re.IGNORECASE
)

# Matches port range expressions in textual NFTables:
# Examples:
#   tcp dport 8000-8010
DPORT_RANGE_REGEX = re.compile(
    r"(?:(tcp|udp|th)\s+)?dport\s+(\d{1,5})\s*-\s*(\d{1,5})\b",
    re.IGNORECASE
)

# Matches multiport sets in textual NFTables:
# Examples:
#   tcp dport { 80, 443, 8443 }
DPORT_SET_REGEX = re.compile(
    r"(?:(tcp|udp|th)\s+)?dport\s*\{\s*([0-9,\s\-]+)\s*\}",
    re.IGNORECASE
)

# Matches rule handle at line end:
# Example: # handle 12
HANDLE_REGEX = re.compile(
    r"#\s*handle\s+(\d+)\b",
    re.IGNORECASE
)

# Matches iptables DNAT rules:
# Example: -A PREROUTING -p tcp -m tcp --dport 8443 -j DNAT --to-destination 10.88.1.2:8443
IPTABLES_DNAT_REGEX = re.compile(
    r"(?:-A|--append)\s+(\S+).*(?:-p|--protocol)\s+(tcp|udp)\b.*(?:--dport|--dports)\s+(\d{1,5})\b.*-j\s+DNAT\s+--to-destination\s+(?:\[([0-9a-fA-F:]+)\]|([0-9\.]+))(?::(\d{1,5}))?",
    re.IGNORECASE
)


def _is_valid_target(target: str) -> bool:
    """Validates that a destination target is a safe IPv4, IPv6, or valid hostname without shell injection characters."""
    clean = str(target or "").strip().strip("[]")
    if not clean or any(c in clean for c in ";&|`$ \t\n\r<>\"'\\/"):
        return False
    try:
        ipaddress.ip_address(clean)
        return True
    except ValueError:
        return bool(re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\.\-_]{0,253}[a-zA-Z0-9])?$", clean))


def _build_xforwarder_rule_from_nftables(
    port: int,
    target: str,
    target_port: int,
    protocol: str = "both",
    table_name: str = "nat",
    chain_name: str = "prerouting",
    family: str = "ip",
    handle: Optional[int] = None,
    raw_rule: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Constructs a valid XForwarder rule dictionary from an extracted NFTables rule.
    Sets Priority 2 (NFTables) as active with the detected target,
    and creates a compatible Priority 1 primary destination.
    Returns None if target is invalid or malicious.
    """
    clean_target = target.strip().strip("[]")
    if not _is_valid_target(clean_target):
        return None

    if not (1 <= port <= 65535) or not (1 <= target_port <= 65535):
        return None

    is_ipv6 = ":" in clean_target
    p1_type = "haproxy" if is_ipv6 else "nginx"
    p1_comment = f"Auto-configured Primary for port {port}"

    return {
        "id": f"rule-{port}",
        "port": port,
        "protocol": protocol,
        "active_priority": 2,
        "force_override": 0,
        "destinations": [
            {
                "priority": 1,
                "type": p1_type,
                "target": clean_target,
                "port": target_port,
                "proxy_protocol": False,
                "comment": p1_comment
            },
            {
                "priority": 2,
                "type": "nftables",
                "target": clean_target,
                "port": target_port,
                "proxy_protocol": False,
                "comment": f"Imported from NFTables ({family} {table_name}/{chain_name})"
            }
        ],
        "_meta": {
            "source": "nftables",
            "family": family,
            "table": table_name,
            "chain": chain_name,
            "handle": handle,
            "raw_rule": raw_rule.strip()
        }
    }


def parse_nftables_json(data: dict) -> List[Dict[str, Any]]:
    """
    Parses 'nft -j list ruleset' output dictionary.
    Extracts DNAT rules from unmanaged tables.
    """
    rules: List[Dict[str, Any]] = []
    seen_ports: Set[int] = set()

    nft_items = data.get("nftables", [])
    if not isinstance(nft_items, list):
        return []

    for item in nft_items:
        rule_info = item.get("rule")
        if not rule_info:
            continue

        table_name = str(rule_info.get("table", "")).strip()
        chain_name = str(rule_info.get("chain", "")).strip()
        family = str(rule_info.get("family", "ip")).strip()
        handle = rule_info.get("handle")

        # Skip XForwarder managed tables
        if table_name.lower() in MANAGED_TABLES:
            continue

        exprs = rule_info.get("expr", [])
        if not isinstance(exprs, list):
            continue

        dnat_info = None
        ports: List[int] = []
        rule_proto = "both"

        for expr in exprs:
            if not isinstance(expr, dict):
                continue

            # Check dnat expression
            if "dnat" in expr:
                dnat_info = expr["dnat"]
                continue

            # Check matches
            if "match" in expr:
                m = expr["match"]
                left = m.get("left", {})
                right = m.get("right")

                # Match on payload dport
                if isinstance(left, dict) and "payload" in left:
                    payload = left["payload"]
                    field = payload.get("field", "")
                    proto = payload.get("protocol", "")
                    if field == "dport":
                        if proto in ("tcp", "udp"):
                            rule_proto = proto
                        if isinstance(right, int):
                            ports.append(right)
                        elif isinstance(right, str):
                            try:
                                ports.append(int(right))
                            except ValueError:
                                pass
                        elif isinstance(right, list):
                            for p in right:
                                try:
                                    ports.append(int(p))
                                except (ValueError, TypeError):
                                    pass
                        elif isinstance(right, dict):
                            if "set" in right:
                                for p in right["set"]:
                                    try:
                                        ports.append(int(p))
                                    except (ValueError, TypeError):
                                        pass
                            elif "range" in right and isinstance(right["range"], list) and len(right["range"]) == 2:
                                try:
                                    start_p = int(right["range"][0])
                                    end_p = int(right["range"][1])
                                    if 1 <= start_p <= end_p <= 65535 and (end_p - start_p) <= 100:
                                        ports.extend(range(start_p, end_p + 1))
                                except (ValueError, TypeError):
                                    pass

                # Match on meta l4proto
                if isinstance(left, dict) and "meta" in left:
                    key = left["meta"].get("key", "")
                    if key == "l4proto":
                        if isinstance(right, str) and right in ("tcp", "udp"):
                            rule_proto = right
                        elif isinstance(right, list) and set(right) == {"tcp", "udp"}:
                            rule_proto = "both"

        if not dnat_info or not ports:
            continue

        target_addr = str(dnat_info.get("addr", "")).strip().strip("[]")
        target_port_val = dnat_info.get("port")

        if not target_addr:
            continue

        for p in ports:
            if p in seen_ports or not (1 <= p <= 65535):
                continue
            t_port = int(target_port_val) if target_port_val else p
            if not (1 <= t_port <= 65535):
                t_port = p

            rule_obj = _build_xforwarder_rule_from_nftables(
                port=p,
                target=target_addr,
                target_port=t_port,
                protocol=rule_proto,
                table_name=table_name,
                chain_name=chain_name,
                family=family,
                handle=handle,
                raw_rule=json.dumps(rule_info)
            )
            if rule_obj:
                rules.append(rule_obj)
                seen_ports.add(p)

    return rules


def parse_nftables_text(content: str) -> List[Dict[str, Any]]:
    """
    Parses textual NFTables ruleset (e.g. from 'nft -a list ruleset' or '/etc/nftables.conf').
    Tracks table/chain nesting and extracts DNAT rules with handles.
    """
    rules: List[Dict[str, Any]] = []
    seen_ports: Set[int] = set()

    current_family = "ip"
    current_table = ""
    current_chain = ""
    brace_depth = 0
    table_depth = -1
    chain_depth = -1

    table_header_regex = re.compile(r"^table\s+(ip|ip6|inet)\s+(\S+)", re.IGNORECASE)
    chain_header_regex = re.compile(r"^chain\s+(\S+)", re.IGNORECASE)

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Count braces to track scope
        open_braces = line.count("{")
        close_braces = line.count("}")

        t_match = table_header_regex.search(line)
        if t_match:
            current_family = t_match.group(1).lower()
            current_table = t_match.group(2).lower()
            table_depth = brace_depth
            current_chain = ""

        c_match = chain_header_regex.search(line)
        if c_match:
            current_chain = c_match.group(1)
            chain_depth = brace_depth

        brace_depth += open_braces - close_braces
        if brace_depth <= table_depth:
            current_table = ""
            table_depth = -1
        if brace_depth <= chain_depth:
            current_chain = ""
            chain_depth = -1

        # Skip comments or XForwarder's own tables
        if line.startswith("#") or current_table in MANAGED_TABLES:
            continue

        # Check if line contains a DNAT action
        dnat_match = DNAT_TARGET_REGEX.search(line)
        if not dnat_match:
            continue

        target = (dnat_match.group(1) or dnat_match.group(2) or dnat_match.group(3) or "").strip().strip("[]")
        raw_t_port = dnat_match.group(4)
        if not target:
            continue

        # Extract handle if present
        h_match = HANDLE_REGEX.search(line)
        handle = int(h_match.group(1)) if h_match else None

        # Extract protocol
        proto = "both"
        lower_line = line.lower()
        if "meta l4proto { tcp, udp }" in lower_line:
            proto = "both"
        elif "tcp dport" in lower_line or "ip protocol tcp" in lower_line or "meta l4proto tcp" in lower_line:
            proto = "tcp"
        elif "udp dport" in lower_line or "ip protocol udp" in lower_line or "meta l4proto udp" in lower_line:
            proto = "udp"

        # Extract listening port(s)
        extracted_ports: List[int] = []

        range_match = DPORT_RANGE_REGEX.search(line)
        if range_match:
            proto_override = range_match.group(1)
            if proto_override and proto_override.lower() in ("tcp", "udp"):
                proto = proto_override.lower()
            try:
                start_p = int(range_match.group(2))
                end_p = int(range_match.group(3))
                if 1 <= start_p <= end_p <= 65535 and (end_p - start_p) <= 100:
                    extracted_ports.extend(range(start_p, end_p + 1))
            except ValueError:
                pass

        if not extracted_ports:
            set_match = DPORT_SET_REGEX.search(line)
            if set_match:
                proto_override = set_match.group(1)
                if proto_override and proto_override.lower() in ("tcp", "udp"):
                    proto = proto_override.lower()
                for token in set_match.group(2).split(","):
                    token = token.strip()
                    if "-" in token:
                        parts = token.split("-")
                        try:
                            sp, ep = int(parts[0].strip()), int(parts[1].strip())
                            if 1 <= sp <= ep <= 65535 and (ep - sp) <= 100:
                                extracted_ports.extend(range(sp, ep + 1))
                        except ValueError:
                            pass
                    else:
                        try:
                            p = int(token)
                            if 1 <= p <= 65535:
                                extracted_ports.append(p)
                        except ValueError:
                            pass
            else:
                dport_match = DPORT_REGEX.search(line)
                if dport_match:
                    proto_override = dport_match.group(1)
                    if proto_override and proto_override.lower() in ("tcp", "udp"):
                        proto = proto_override.lower()
                    try:
                        p = int(dport_match.group(2))
                        if 1 <= p <= 65535:
                            extracted_ports.append(p)
                    except ValueError:
                        pass

        for p in extracted_ports:
            if p in seen_ports:
                continue
            target_port = int(raw_t_port) if raw_t_port else p
            if not (1 <= target_port <= 65535):
                target_port = p

            rule_obj = _build_xforwarder_rule_from_nftables(
                port=p,
                target=target,
                target_port=target_port,
                protocol=proto,
                table_name=current_table or "nat",
                chain_name=current_chain or "prerouting",
                family=current_family,
                handle=handle,
                raw_rule=line
            )
            if rule_obj:
                rules.append(rule_obj)
                seen_ports.add(p)

    return rules


def parse_iptables_text(content: str) -> List[Dict[str, Any]]:
    """
    Parses 'iptables-save' or saved iptables rules text and extracts DNAT rules.
    """
    rules: List[Dict[str, Any]] = []
    seen_ports: Set[int] = set()

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(":"):
            continue

        match = IPTABLES_DNAT_REGEX.search(line)
        if match:
            chain = match.group(1)
            proto = match.group(2).lower()
            port = int(match.group(3))
            target = (match.group(4) or match.group(5) or "").strip()
            raw_t_port = match.group(6)
            target_port = int(raw_t_port) if raw_t_port else port

            if port in seen_ports or not target or not (1 <= port <= 65535):
                continue

            rule_obj = _build_xforwarder_rule_from_nftables(
                port=port,
                target=target,
                target_port=target_port,
                protocol=proto,
                table_name="nat",
                chain_name=chain,
                family="ip",
                handle=None,
                raw_rule=line
            )
            if rule_obj:
                rules.append(rule_obj)
                seen_ports.add(port)

    return rules


def get_live_nftables_rules() -> List[Dict[str, Any]]:
    """
    Queries the running Linux kernel for active NFTables (and iptables) rules.
    Uses 'nft -j list ruleset' and 'nft -a list ruleset'.
    """
    rules: List[Dict[str, Any]] = []
    seen_ports: Set[int] = set()

    # 1. Try 'nft -a list ruleset' (text with handles - highest fidelity for deconfliction)
    if shutil.which("nft"):
        try:
            res_a = subprocess.run(
                ["nft", "-a", "list", "ruleset"],
                capture_output=True, text=True, timeout=3.0
            )
            if res_a.returncode == 0 and res_a.stdout.strip():
                text_rules = parse_nftables_text(res_a.stdout)
                for r in text_rules:
                    p = r["port"]
                    if p not in seen_ports:
                        rules.append(r)
                        seen_ports.add(p)
        except Exception as e:
            logger.debug(f"nft -a list ruleset error: {e}")

    # 2. Try 'nft -j list ruleset' (JSON format for additional structured safety)
    if shutil.which("nft"):
        try:
            res_j = subprocess.run(
                ["nft", "-j", "list", "ruleset"],
                capture_output=True, text=True, timeout=3.0
            )
            if res_j.returncode == 0 and res_j.stdout.strip():
                try:
                    data = json.loads(res_j.stdout)
                    json_rules = parse_nftables_json(data)
                    for r in json_rules:
                        p = r["port"]
                        if p not in seen_ports:
                            rules.append(r)
                            seen_ports.add(p)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"nft -j list ruleset error: {e}")

    # 3. Check iptables-save if iptables is installed and has PREROUTING DNAT rules
    if shutil.which("iptables-save"):
        try:
            res_ipt = subprocess.run(
                ["iptables-save"],
                capture_output=True, text=True, timeout=2.0
            )
            if res_ipt.returncode == 0 and res_ipt.stdout.strip():
                ipt_rules = parse_iptables_text(res_ipt.stdout)
                for r in ipt_rules:
                    p = r["port"]
                    if p not in seen_ports:
                        rules.append(r)
                        seen_ports.add(p)
        except Exception as e:
            logger.debug(f"iptables-save error: {e}")

    return rules


def find_candidate_nftables_files() -> List[str]:
    """
    Finds persistent NFTables and iptables configuration files on the host filesystem.
    """
    candidates: List[str] = []
    file_patterns = [
        "/etc/nftables.conf",
        "/etc/nftables.conf.bak*",
        "/etc/sysconfig/nftables.conf",
        "/etc/nftables/*.nft",
        "/etc/nftables.conf.d/*.nft",
        "/etc/iptables/rules.v4",
        "/etc/iptables.rules"
    ]
    for pattern in file_patterns:
        for p in glob.glob(pattern):
            if os.path.isfile(p) and p not in candidates:
                candidates.append(p)
    return candidates


def discover_importable_nftables_rules(existing_rules: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Scans live kernel rules and persistent files for NFTables forwarding rules.
    Returns rules for ports that are NOT yet in existing_rules.
    """
    configured_ports: Set[int] = set()
    if existing_rules:
        for r in existing_rules:
            if "port" in r:
                try:
                    configured_ports.add(int(r["port"]))
                except (ValueError, TypeError):
                    pass

    discovered_rules: List[Dict[str, Any]] = []
    discovered_ports: Set[int] = set()

    # 1. Live kernel rules (highest priority)
    live_rules = get_live_nftables_rules()
    for r in live_rules:
        p = r.get("port")
        if p and p not in configured_ports and p not in discovered_ports:
            discovered_rules.append(r)
            discovered_ports.add(p)

    # 2. Config files
    for path in find_candidate_nftables_files():
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "iptables" in path:
                file_rules = parse_iptables_text(content)
            else:
                file_rules = parse_nftables_text(content)

            for r in file_rules:
                p = r.get("port")
                if p and p not in configured_ports and p not in discovered_ports:
                    discovered_rules.append(r)
                    discovered_ports.add(p)
        except Exception as e:
            logger.warning(f"Error reading NFTables candidate file {path}: {e}")

    return discovered_rules


def backup_legacy_nftables() -> Optional[str]:
    """
    Saves an atomic snapshot of current nftables (and iptables) ruleset
    before any deactivation occurs. Returns the backup file path.
    """
    backup_dir = "/etc/xforwarder/backups"
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception:
        backup_dir = "/tmp/xforwarder_backups"
        os.makedirs(backup_dir, exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"legacy_nftables_{ts}.nft")

    content = []
    if shutil.which("nft"):
        try:
            res = subprocess.run(["nft", "list", "ruleset"], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                content.append("# NFTables Ruleset Snapshot")
                content.append(res.stdout)
        except Exception:
            pass

    if shutil.which("iptables-save"):
        try:
            res_ipt = subprocess.run(["iptables-save"], capture_output=True, text=True, timeout=2.0)
            if res_ipt.returncode == 0:
                content.append("\n# iptables-save Snapshot")
                content.append(res_ipt.stdout)
        except Exception:
            pass

    if not content:
        return None

    try:
        tmp_path = f"{backup_file}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        os.replace(tmp_path, backup_file)
        return backup_file
    except Exception as e:
        logger.warning(f"Failed to create legacy NFTables backup: {e}")
        return None


def deactivate_legacy_rules(imported_rules: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """
    Safely deletes the imported DNAT rules from legacy external tables
    to guarantee zero collision with XForwarder's managed tables.
    Returns (deactivated_count, list_of_log_messages).
    """
    deactivated = 0
    logs: List[str] = []

    # Map ports to rules to assist with live lookup if handle is missing
    ports_needing_lookup: Set[int] = set()
    for r in imported_rules:
        if not r.get("_meta", {}).get("handle"):
            p = r.get("port")
            if p:
                ports_needing_lookup.add(int(p))

    # If any rule lacked a handle, try to discover live handles in the kernel
    live_handles: Dict[int, Dict[str, Any]] = {}
    if ports_needing_lookup and shutil.which("nft"):
        try:
            live_rules = get_live_nftables_rules()
            for lr in live_rules:
                lp = lr.get("port")
                lh = lr.get("_meta", {}).get("handle")
                if lp in ports_needing_lookup and lh:
                    live_handles[lp] = lr.get("_meta", {})
        except Exception:
            pass

    for r in imported_rules:
        meta = r.get("_meta", {})
        port = r.get("port")
        if not port:
            continue

        handle = meta.get("handle")
        table = meta.get("table", "")
        chain = meta.get("chain", "")
        family = meta.get("family", "ip")

        # Supplement with live handle if discovered
        if not handle and port in live_handles:
            live_meta = live_handles[port]
            handle = live_meta.get("handle")
            table = live_meta.get("table", table)
            chain = live_meta.get("chain", chain)
            family = live_meta.get("family", family)

        # Sanitize arguments strictly
        if family not in ("ip", "ip6", "inet"):
            continue

        if table and not re.match(r"^[a-zA-Z0-9_\-]+$", table):
            continue
        if chain and not re.match(r"^[a-zA-Z0-9_\-]+$", chain):
            continue

        # 1. Handle-based deletion in NFTables (atomic & non-disruptive)
        if handle and table and chain and shutil.which("nft"):
            try:
                cmd = ["nft", "delete", "rule", family, table, chain, "handle", str(int(handle))]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0:
                    deactivated += 1
                    logs.append(f"Deactivated legacy rule for port {port} via handle {handle} in {family} {table}/{chain}")
                    continue
                else:
                    logs.append(f"Warning: nft delete rule returned {res.returncode} for port {port}: {res.stderr.strip()}")
            except Exception as e:
                logs.append(f"Error deactivating nft handle {handle}: {e}")

        # 2. Iptables fallback deletion
        if shutil.which("iptables") and port:
            try:
                check_cmd = ["iptables", "-t", "nat", "-S", "PREROUTING"]
                res_s = subprocess.run(check_cmd, capture_output=True, text=True, timeout=2.0)
                if res_s.returncode == 0:
                    for line in res_s.stdout.splitlines():
                        if f"--dport {port}" in line and "-j DNAT" in line:
                            del_args = line.replace("-A PREROUTING", "-D PREROUTING").split()
                            del_cmd = ["iptables", "-t", "nat"] + del_args
                            subprocess.run(del_cmd, capture_output=True, timeout=2.0)
                            deactivated += 1
                            logs.append(f"Deactivated matching legacy iptables rule for port {port}")
                            break
            except Exception as e:
                logs.append(f"Error deactivating iptables rule for port {port}: {e}")

    return deactivated, logs


def deactivate_legacy_rules_for_ports(ports: Set[int]) -> Tuple[int, List[str]]:
    """
    Deactivates any active unmanaged kernel DNAT rules for the specified ports.
    Used during unified import to ensure HAProxy ports do not suffer kernel hook interference.
    """
    if not ports:
        return 0, []

    mock_rules: List[Dict[str, Any]] = []
    live = get_live_nftables_rules()
    for lr in live:
        if lr.get("port") in ports:
            mock_rules.append(lr)

    if not mock_rules:
        # Create minimal port stubs for iptables fallback
        mock_rules = [{"port": p, "_meta": {}} for p in ports]

    return deactivate_legacy_rules(mock_rules)


def import_nftables_rules_into_config(
    config_path: str,
    deactivate_legacy: bool = True
) -> Tuple[int, List[int], List[str]]:
    """
    Discovers unimported NFTables rules and atomically merges them into config_path.
    If deactivate_legacy is True, automatically backs up the old ruleset and deactivates
    the imported rules to prevent port collisions.
    Returns (imported_count, list_of_imported_ports, log_messages).
    """
    logs: List[str] = []
    if not os.path.exists(config_path):
        return 0, [], ["Config file does not exist"]

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"Cannot read config file {config_path}: {e}")
        return 0, [], [f"Error reading config: {e}"]

    rules = cfg.get("rules", [])
    importable = discover_importable_nftables_rules(rules)

    if not importable:
        return 0, [], ["No new unimported NFTables rules found"]

    # Optional legacy rule backup and deactivation
    if deactivate_legacy:
        backup_file = backup_legacy_nftables()
        if backup_file:
            logs.append(f"Created legacy ruleset backup at: {backup_file}")
        deact_count, deact_logs = deactivate_legacy_rules(importable)
        logs.extend(deact_logs)

    imported_ports: List[int] = []
    for r in importable:
        # Clean private _meta before persisting to config.json
        clean_rule = {k: v for k, v in r.items() if not k.startswith("_")}
        rules.append(clean_rule)
        imported_ports.append(clean_rule["port"])

    cfg["rules"] = rules

    # Atomic write to config.json
    tmp_path = f"{config_path}.tmp.{os.getpid()}"
    try:
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, config_path)
        logs.append(f"Successfully saved {len(imported_ports)} rule(s) to {config_path}")
        return len(imported_ports), imported_ports, logs
    except Exception as e:
        logger.error(f"Failed to save imported rules to {config_path}: {e}")
        return 0, [], [f"Failed to save config: {e}"]


def discover_all_relay_rules(existing_rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Unified discovery scanning both HAProxy configurations and active NFTables rules.
    Returns structured results with per-source metrics.
    """
    configured_ports: Set[int] = set()
    if existing_rules:
        for r in existing_rules:
            if "port" in r:
                try:
                    configured_ports.add(int(r["port"]))
                except (ValueError, TypeError):
                    pass

    # 1. HAProxy rules
    from core.haproxy_parser import discover_importable_rules as discover_haproxy
    ha_rules = discover_haproxy(existing_rules)
    for r in ha_rules:
        r["_source"] = "haproxy"

    ha_ports = {r["port"] for r in ha_rules if "port" in r}

    # 2. NFTables rules (exclude already found HAProxy ports to avoid double discovery)
    all_known = list(existing_rules or []) + ha_rules
    nft_rules = discover_importable_nftables_rules(all_known)
    for r in nft_rules:
        r["_source"] = "nftables"

    nft_ports = {r["port"] for r in nft_rules if "port" in r}

    combined = ha_rules + nft_rules
    combined_ports = sorted(list(ha_ports | nft_ports))

    return {
        "available": bool(combined),
        "count": len(combined),
        "ports": combined_ports,
        "rules": combined,
        "sources": {
            "haproxy": len(ha_rules),
            "nftables": len(nft_rules)
        }
    }


def import_all_relay_rules_into_config(
    config_path: str,
    deactivate_legacy: bool = True
) -> Tuple[int, List[int], List[str]]:
    """
    Imports both unmanaged HAProxy and NFTables rules into config_path in a single atomic operation.
    Cleans up any legacy kernel DNAT rules for all imported ports to eliminate hook collision.
    """
    from core.haproxy_parser import import_haproxy_rules_into_config

    all_logs: List[str] = []
    total_ports: List[int] = []

    # 1. Backup legacy rules before modifying anything
    if deactivate_legacy:
        backup_file = backup_legacy_nftables()
        if backup_file:
            all_logs.append(f"Created legacy ruleset backup at: {backup_file}")

    # 2. Import HAProxy rules
    h_count, h_ports = import_haproxy_rules_into_config(config_path)
    if h_count > 0:
        all_logs.append(f"Imported {h_count} HAProxy rule(s): {h_ports}")
        total_ports.extend(h_ports)

    # 3. Import NFTables rules (pass deactivate_legacy=False because we deactivate all ports together)
    n_count, n_ports, n_logs = import_nftables_rules_into_config(config_path, deactivate_legacy=False)
    if n_count > 0:
        all_logs.append(f"Imported {n_count} NFTables rule(s): {n_ports}")
        total_ports.extend(n_ports)
    all_logs.extend(n_logs)

    # 4. Deactivate any active legacy DNAT rules matching ANY imported ports (Zero-Collision Guarantee)
    if deactivate_legacy and total_ports:
        deact_count, deact_logs = deactivate_legacy_rules_for_ports(set(total_ports))
        all_logs.extend(deact_logs)

    return len(total_ports), total_ports, all_logs

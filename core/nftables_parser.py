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
from typing import List, Dict, Any, Tuple, Optional, Set, Union

try:
    from core.config_manager import (
        get_rule_port_bounds, ports_overlap, rules_ports_overlap,
        split_port_interval_excluding, get_protected_ports
    )
except ImportError:
    from config_manager import (
        get_rule_port_bounds, ports_overlap, rules_ports_overlap,
        split_port_interval_excluding, get_protected_ports
    )

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

# Matches negated multiport exclusion sets in textual NFTables:
# Examples:
#   tcp dport != { 22, 443, 1001 }
#   udp dport != { 22, 443, 1001 }
DPORT_NEGATED_SET_REGEX = re.compile(
    r"(?:(tcp|udp|th)\s+)?dport\s*!=\s*\{\s*([0-9,\s\-]+)\s*\}",
    re.IGNORECASE
)

# Matches negated single port or range in textual NFTables:
# Examples:
#   tcp dport != 22
#   udp dport != 8000-8010
DPORT_NEGATED_SINGLE_REGEX = re.compile(
    r"(?:(tcp|udp|th)\s+)?dport\s*!=\s*(\d{1,5})(?:\s*-\s*(\d{1,5}))?\b",
    re.IGNORECASE
)

# Matches multiport sets in textual NFTables:
# Examples:
#   tcp dport { 80, 443, 8443 }
DPORT_SET_REGEX = re.compile(
    r"(?:(tcp|udp|th)\s+)?dport\s*\{\s*([0-9,\s\-]+)\s*\}",
    re.IGNORECASE
)

# Matches jhash map DNAT targets:
# Example:
#   dnat to jhash ip saddr mod 3 map { 0 : 10.81.2.2, 1 : 10.81.3.2, 2 : 10.81.10.2 }
DNAT_JHASH_MAP_REGEX = re.compile(
    r"\bdnat(?:\s+(?:ip|ip6))?\s+to\s+jhash\b.*?map\s*\{\s*([^}]+)\s*\}",
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


def _invert_excluded_ports_to_ranges(excluded: Set[int]) -> List[Tuple[int, int]]:
    """
    Converts a set of excluded ports (from `dport != { ... }`) into complementary
    contiguous [start, end] port intervals inside 1..65535.
    """
    return split_port_interval_excluding(1, 65535, excluded)


def _apply_protected_port_splits(
    rules: List[Dict[str, Any]],
    protected_ports: Optional[Set[int]]
) -> List[Dict[str, Any]]:
    """
    Splits or drops discovered/imported rules overlapping protected system ports
    (such as SSH 22 or XForwarder Web Dashboard port) so importing broad ranges
    like 1002-65535 never locks out management access. Preserves `_meta.source_spec`
    and handles so legacy rules still deactivate cleanly.
    """
    if not protected_ports:
        return rules

    safe_rules: List[Dict[str, Any]] = []
    for r in rules:
        # Wildcard excluded-port rules protect management ports dynamically in kernel DNAT without fragmenting cards
        if r.get("excluded_ports"):
            safe_rules.append(r)
            continue
        sp, ep, _ = get_rule_port_bounds(r)
        if sp is None or ep is None:
            continue
        sub_intervals = split_port_interval_excluding(sp, ep, protected_ports)
        if not sub_intervals:
            continue
        if len(sub_intervals) == 1 and sub_intervals[0] == (sp, ep):
            safe_rules.append(r)
            continue

        orig_spec = str(r.get("port_range") or r.get("port") or "")
        base_id = str(r.get("id") or f"Imported NFTables {orig_spec}")
        orig_meta = dict(r.get("_meta") or {})
        if orig_spec and "source_spec" not in orig_meta:
            orig_meta["source_spec"] = orig_spec

        for sub_s, sub_e in sub_intervals:
            new_dests = []
            for d in r.get("destinations", []):
                nd = dict(d)
                # Preserve explicit fixed single-port redirects; adjust 1:1 range destinations to sub-interval
                if sub_s == sub_e:
                    if nd.get("port_range") or nd.get("port") is None or nd.get("port") == sp:
                        nd["port"] = sub_s
                    nd.pop("port_range", None)
                else:
                    if nd.get("port_range") or nd.get("port") is None or nd.get("port") == sp:
                        nd["port"] = sub_s
                        nd["port_range"] = f"{sub_s}-{sub_e}"
                new_dests.append(nd)

            sub_rule: Dict[str, Any] = {
                "id": f"{base_id} ({sub_s})" if sub_s == sub_e else f"{base_id} ({sub_s}-{sub_e})",
                "port": sub_s,
                "protocol": r.get("protocol", "both"),
                "active_priority": r.get("active_priority", 1),
                "destinations": new_dests,
                "_meta": dict(orig_meta),
            }
            if sub_s < sub_e:
                sub_rule["port_range"] = f"{sub_s}-{sub_e}"
            if "_source" in r:
                sub_rule["_source"] = r["_source"]
            safe_rules.append(sub_rule)
    return safe_rules


def _parse_port_tokens(expr_body: str, expand_limit: int = 100) -> Set[int]:
    """Parses comma-separated port numbers and ranges from a set expression body."""
    ports: Set[int] = set()
    for token in expr_body.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-", 1)
            try:
                sp, ep = int(parts[0].strip()), int(parts[1].strip())
                if 1 <= sp <= ep <= 65535 and (ep - sp) <= expand_limit:
                    ports.update(range(sp, ep + 1))
            except ValueError:
                pass
        else:
            try:
                p = int(token)
                if 1 <= p <= 65535:
                    ports.add(p)
            except ValueError:
                pass
    return ports


def _build_xforwarder_range_rule_from_nftables(
    start_port: int,
    end_port: int,
    targets: List[str],
    target_port: Optional[int] = None,
    protocol: str = "both",
    table_name: str = "nat",
    chain_name: str = "prerouting",
    family: str = "ip",
    handle: Optional[int] = None,
    handles: Optional[List[int]] = None,
    raw_rule: str = "",
    excluded_ports: Optional[List[int]] = None
) -> Optional[Dict[str, Any]]:
    """
    Constructs an NFTables-only XForwarder port-range (or wildcard != excluded) rule
    from an extracted range or negated-set DNAT rule.
    """
    if not (1 <= start_port < end_port <= 65535):
        return None
    clean_targets: List[str] = []
    for t in targets:
        ct = str(t or "").strip().strip("[]")
        if _is_valid_target(ct) and ct not in clean_targets:
            try:
                ipaddress.ip_address(ct)
                clean_targets.append(ct)
            except ValueError:
                pass
    if not clean_targets:
        return None

    range_str = f"{start_port}-{end_port}"
    dests: List[Dict[str, Any]] = []
    for idx, ct in enumerate(clean_targets, start=1):
        d_entry: Dict[str, Any] = {
            "priority": idx,
            "type": "nftables",
            "target": ct,
            "port": int(target_port) if target_port and 1 <= target_port <= 65535 else start_port,
            "proxy_protocol": False,
            "is_relay": idx > 1,
            "enabled": True,
            "comment": f"Imported from NFTables ({family} {table_name}/{chain_name})"
        }
        if not target_port:
            d_entry["port_range"] = range_str
        dests.append(d_entry)

    meta_handles = list(handles or ([] if handle is None else [handle]))
    excl_sorted = sorted({int(p) for p in (excluded_ports or []) if isinstance(p, int) and not isinstance(p, bool) and 1 <= p <= 65535})
    rule_id = (
        f"rule-excl-{'-'.join(str(p) for p in excl_sorted[:5])}"
        if excl_sorted else f"rule-{range_str}"
    )
    rule_dict: Dict[str, Any] = {
        "id": rule_id,
        "port": start_port,
        "port_range": range_str,
        "protocol": protocol,
        "active_priority": 1,
        "force_override": 0,
        "destinations": dests,
        "_meta": {
            "source": "nftables",
            "family": family,
            "table": table_name,
            "chain": chain_name,
            "port_range": range_str,
            "handle": meta_handles[0] if meta_handles else handle,
            "handles": meta_handles,
            "raw_rule": raw_rule.strip()
        }
    }
    if excl_sorted:
        rule_dict["excluded_ports"] = excl_sorted
        rule_dict["_meta"]["excluded_ports"] = excl_sorted
    return rule_dict


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


def _merge_or_append_rule(
    rules: List[Dict[str, Any]],
    rule_index: Dict[Any, int],
    key: Any,
    rule_obj: Optional[Dict[str, Any]],
    proto: str,
    handle: Optional[int]
) -> None:
    """Appends a new rule or merges protocol/handle when TCP & UDP rules share the exact key."""
    if not rule_obj:
        return
    if key in rule_index:
        existing = rules[rule_index[key]]
        ex_proto = existing.get("protocol", "both")
        if ex_proto != proto and {ex_proto, proto} <= {"tcp", "udp"}:
            existing["protocol"] = "both"
        meta = existing.setdefault("_meta", {})
        handles = meta.setdefault("handles", [])
        if meta.get("handle") is not None and meta["handle"] not in handles:
            handles.append(meta["handle"])
        if handle is not None and handle not in handles:
            handles.append(handle)
        return
    rule_index[key] = len(rules)
    rules.append(rule_obj)


def parse_nftables_json(data: dict) -> List[Dict[str, Any]]:
    """
    Parses 'nft -j list ruleset' output dictionary.
    Extracts single-port, range, and excluded-set (`!= { ... }`) DNAT rules from unmanaged tables.
    """
    rules: List[Dict[str, Any]] = []
    rule_index: Dict[Any, int] = {}

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
        range_intervals: List[Tuple[int, int]] = []
        excluded_ports: Set[int] = set()
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
                op = str(m.get("op", "==")).strip()
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
                        is_negated = (op == "!=")
                        bucket = excluded_ports if is_negated else None

                        def _add_int(val):
                            try:
                                p_val = int(val)
                                if 1 <= p_val <= 65535:
                                    if is_negated:
                                        bucket.add(p_val)
                                    else:
                                        ports.append(p_val)
                            except (ValueError, TypeError):
                                pass

                        def _add_range_item(item_pair):
                            if isinstance(item_pair, list) and len(item_pair) == 2:
                                try:
                                    sp, ep = int(item_pair[0]), int(item_pair[1])
                                    if 1 <= sp <= ep <= 65535:
                                        if is_negated:
                                            if (ep - sp) <= 1000:
                                                bucket.update(range(sp, ep + 1))
                                        elif (ep - sp) <= 100 and sp < ep:
                                            range_intervals.append((sp, ep))
                                        elif sp < ep:
                                            range_intervals.append((sp, ep))
                                        else:
                                            ports.append(sp)
                                except (ValueError, TypeError):
                                    pass

                        if isinstance(right, (int, str)):
                            _add_int(right)
                        elif isinstance(right, list):
                            for entry in right:
                                _add_int(entry)
                        elif isinstance(right, dict):
                            if "set" in right:
                                for entry in right["set"]:
                                    if isinstance(entry, dict) and "range" in entry:
                                        _add_range_item(entry["range"])
                                    else:
                                        _add_int(entry)
                            elif "range" in right:
                                _add_range_item(right["range"])

                # Match on meta l4proto
                if isinstance(left, dict) and "meta" in left:
                    key = left["meta"].get("key", "")
                    if key == "l4proto":
                        if isinstance(right, str) and right in ("tcp", "udp"):
                            rule_proto = right
                        elif isinstance(right, list) and set(right) == {"tcp", "udp"}:
                            rule_proto = "both"

        if not dnat_info:
            continue

        raw_addr = dnat_info.get("addr", "")
        target_addrs: List[str] = []
        if isinstance(raw_addr, str) and raw_addr.strip():
            target_addrs = [raw_addr.strip().strip("[]")]
        elif isinstance(raw_addr, dict) and "map" in raw_addr:
            # Handle jhash map targets when present in structured nft JSON
            map_data = raw_addr.get("map", {}).get("data", {})
            if isinstance(map_data, dict) and isinstance(map_data.get("set"), list):
                for entry in map_data["set"]:
                    if isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str):
                        target_addrs.append(entry[1].strip().strip("[]"))

        if not target_addrs:
            continue

        target_port_val = dnat_info.get("port")
        raw_rule_json = json.dumps(rule_info)

        # Unified wildcard exclusion rule from negated `dport != { ... }`
        if excluded_ports:
            excl_sorted = sorted(excluded_ports)
            t_port = int(target_port_val) if target_port_val else None
            rule_obj = _build_xforwarder_range_rule_from_nftables(
                start_port=1, end_port=65535, targets=target_addrs, target_port=t_port,
                protocol=rule_proto, table_name=table_name, chain_name=chain_name,
                family=family, handle=handle, raw_rule=raw_rule_json,
                excluded_ports=excl_sorted
            )
            _merge_or_append_rule(
                rules, rule_index, ("excl", tuple(excl_sorted), tuple(target_addrs), t_port),
                rule_obj, rule_proto, handle
            )

        # Direct range rules
        for sp, ep in range_intervals:
            if (ep - sp) <= 100 and target_port_val:
                for p in range(sp, ep + 1):
                    t_port = int(target_port_val)
                    rule_obj = _build_xforwarder_rule_from_nftables(
                        port=p, target=target_addrs[0], target_port=t_port, protocol=rule_proto,
                        table_name=table_name, chain_name=chain_name, family=family,
                        handle=handle, raw_rule=raw_rule_json
                    )
                    _merge_or_append_rule(rules, rule_index, (p, p, target_addrs[0], t_port), rule_obj, rule_proto, handle)
            else:
                t_port = int(target_port_val) if target_port_val else None
                rule_obj = _build_xforwarder_range_rule_from_nftables(
                    start_port=sp, end_port=ep, targets=target_addrs, target_port=t_port,
                    protocol=rule_proto, table_name=table_name, chain_name=chain_name,
                    family=family, handle=handle, raw_rule=raw_rule_json
                )
                _merge_or_append_rule(rules, rule_index, (sp, ep, tuple(target_addrs), t_port), rule_obj, rule_proto, handle)

        # Single / set ports
        for p in ports:
            if not (1 <= p <= 65535):
                continue
            t_port = int(target_port_val) if target_port_val else p
            if not (1 <= t_port <= 65535):
                t_port = p
            rule_obj = _build_xforwarder_rule_from_nftables(
                port=p, target=target_addrs[0], target_port=t_port, protocol=rule_proto,
                table_name=table_name, chain_name=chain_name, family=family,
                handle=handle, raw_rule=raw_rule_json
            )
            _merge_or_append_rule(rules, rule_index, (p, p, target_addrs[0], t_port), rule_obj, rule_proto, handle)

    return rules


def parse_nftables_text(content: str) -> List[Dict[str, Any]]:
    """
    Parses textual NFTables ruleset (e.g. from 'nft -a list ruleset' or '/etc/nftables.conf').
    Tracks table/chain nesting and extracts single-port, range, and `dport != { ... }` DNAT rules.
    """
    rules: List[Dict[str, Any]] = []
    rule_index: Dict[Any, int] = {}

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

        # Check if line contains a DNAT target or jhash map target
        targets: List[str] = []
        raw_t_port = None
        dnat_match = DNAT_TARGET_REGEX.search(line)
        if dnat_match:
            t_single = (dnat_match.group(1) or dnat_match.group(2) or dnat_match.group(3) or "").strip().strip("[]")
            if t_single.lower() == "jhash":
                jhash_match = DNAT_JHASH_MAP_REGEX.search(line)
                if jhash_match:
                    for pair in jhash_match.group(1).split(","):
                        if ":" in pair:
                            cand = pair.split(":", 1)[1].strip().strip("[]")
                            if _is_valid_target(cand):
                                targets.append(cand)
            elif t_single and _is_valid_target(t_single):
                targets = [t_single]
                raw_t_port = dnat_match.group(4)

        if not targets:
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

        tbl = current_table or "nat"
        chn = current_chain or "prerouting"
        t_port_int = int(raw_t_port) if raw_t_port else None

        # 1. Negated exclusion set (`dport != { 22, 443, 1001 }`) or single (`dport != 22`)
        neg_set_match = DPORT_NEGATED_SET_REGEX.search(line)
        neg_single_match = DPORT_NEGATED_SINGLE_REGEX.search(line) if not neg_set_match else None
        if neg_set_match or neg_single_match:
            excluded_ports: Set[int] = set()
            if neg_set_match:
                p_ovr = neg_set_match.group(1)
                if p_ovr and p_ovr.lower() in ("tcp", "udp"):
                    proto = p_ovr.lower()
                excluded_ports = _parse_port_tokens(neg_set_match.group(2), expand_limit=1000)
            else:
                p_ovr = neg_single_match.group(1)
                if p_ovr and p_ovr.lower() in ("tcp", "udp"):
                    proto = p_ovr.lower()
                sp = int(neg_single_match.group(2))
                ep = int(neg_single_match.group(3)) if neg_single_match.group(3) else sp
                if 1 <= sp <= ep <= 65535 and (ep - sp) <= 1000:
                    excluded_ports.update(range(sp, ep + 1))

            excl_sorted = sorted(excluded_ports)
            rule_obj = _build_xforwarder_range_rule_from_nftables(
                start_port=1, end_port=65535, targets=targets, target_port=t_port_int,
                protocol=proto, table_name=tbl, chain_name=chn, family=current_family,
                handle=handle, raw_rule=line, excluded_ports=excl_sorted
            )
            _merge_or_append_rule(
                rules, rule_index, ("excl", tuple(excl_sorted), tuple(targets), t_port_int),
                rule_obj, proto, handle
            )
            continue

        # 2. Positive port range (`tcp dport 10000-20000` or `9000-9003`)
        range_match = DPORT_RANGE_REGEX.search(line)
        if range_match:
            proto_override = range_match.group(1)
            if proto_override and proto_override.lower() in ("tcp", "udp"):
                proto = proto_override.lower()
            try:
                start_p = int(range_match.group(2))
                end_p = int(range_match.group(3))
            except ValueError:
                start_p = end_p = 0
            if 1 <= start_p < end_p <= 65535:
                if (end_p - start_p) <= 100 and t_port_int:
                    for p in range(start_p, end_p + 1):
                        rule_obj = _build_xforwarder_rule_from_nftables(
                            port=p, target=targets[0], target_port=t_port_int, protocol=proto,
                            table_name=tbl, chain_name=chn, family=current_family,
                            handle=handle, raw_rule=line
                        )
                        _merge_or_append_rule(rules, rule_index, (p, p, targets[0], t_port_int), rule_obj, proto, handle)
                else:
                    rule_obj = _build_xforwarder_range_rule_from_nftables(
                        start_port=start_p, end_port=end_p, targets=targets, target_port=t_port_int,
                        protocol=proto, table_name=tbl, chain_name=chn, family=current_family,
                        handle=handle, raw_rule=line
                    )
                    _merge_or_append_rule(rules, rule_index, (start_p, end_p, tuple(targets), t_port_int), rule_obj, proto, handle)
                continue

        # 3. Multiport sets & single ports
        extracted_ports: List[int] = []
        set_match = DPORT_SET_REGEX.search(line)
        if set_match:
            proto_override = set_match.group(1)
            if proto_override and proto_override.lower() in ("tcp", "udp"):
                proto = proto_override.lower()
            extracted_ports = sorted(_parse_port_tokens(set_match.group(2), expand_limit=100))
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
            target_port = t_port_int if (t_port_int and 1 <= t_port_int <= 65535) else p
            rule_obj = _build_xforwarder_rule_from_nftables(
                port=p, target=targets[0], target_port=target_port, protocol=proto,
                table_name=tbl, chain_name=chn, family=current_family,
                handle=handle, raw_rule=line
            )
            _merge_or_append_rule(rules, rule_index, (p, p, targets[0], target_port), rule_obj, proto, handle)

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
    Uses 'nft -a list ruleset' and 'nft -j list ruleset'.
    """
    rules: List[Dict[str, Any]] = []
    seen_specs: Set[str] = set()

    def _rule_spec(r: Dict[str, Any]) -> str:
        if r.get("excluded_ports"):
            return "!=" + ",".join(str(p) for p in r["excluded_ports"])
        return str(r.get("port_range") or r.get("port") or "")

    # 1. Try 'nft -a list ruleset' (text with handles - highest fidelity for deconfliction)
    if shutil.which("nft"):
        try:
            res_a = subprocess.run(
                ["nft", "-a", "list", "ruleset"],
                capture_output=True, text=True, timeout=3.0
            )
            if res_a.returncode == 0 and res_a.stdout.strip():
                for r in parse_nftables_text(res_a.stdout):
                    spec = _rule_spec(r)
                    if spec and spec not in seen_specs:
                        rules.append(r)
                        seen_specs.add(spec)
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
                    for r in parse_nftables_json(data):
                        spec = _rule_spec(r)
                        if spec and spec not in seen_specs:
                            rules.append(r)
                            seen_specs.add(spec)
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
                for r in parse_iptables_text(res_ipt.stdout):
                    spec = _rule_spec(r)
                    if spec and spec not in seen_specs:
                        rules.append(r)
                        seen_specs.add(spec)
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
        "/etc/nftables.d/*.nft",
        "/etc/nftables.conf.d/*.nft",
        "/etc/iptables/rules.v4",
        "/etc/iptables.rules"
    ]
    for pattern in file_patterns:
        for p in glob.glob(pattern):
            if os.path.isfile(p) and p not in candidates:
                candidates.append(p)
    return candidates


def discover_importable_nftables_rules(
    existing_rules: Optional[List[Dict[str, Any]]] = None,
    protected_ports: Optional[Set[int]] = None
) -> List[Dict[str, Any]]:
    """
    Scans live kernel rules and persistent files for NFTables forwarding rules.
    Returns rules whose port/range does not overlap existing_rules, automatically
    splitting ranges around any protected_ports (e.g., SSH 22 and web dashboard port).
    """
    configured_rules: List[Dict[str, Any]] = [
        r for r in (existing_rules or [])
        if isinstance(r, dict) and get_rule_port_bounds(r)[0] is not None
    ]
    discovered_rules: List[Dict[str, Any]] = []

    def _conflicts_existing_or_discovered(r: Dict[str, Any]) -> bool:
        sp, ep, _ = get_rule_port_bounds(r)
        if sp is None or ep is None:
            return True
        if any(rules_ports_overlap(r, existing) for existing in configured_rules):
            return True
        if any(rules_ports_overlap(r, disc) for disc in discovered_rules):
            return True
        return False

    # 1. Live kernel rules (highest priority)
    for r in _apply_protected_port_splits(get_live_nftables_rules(), protected_ports):
        if not _conflicts_existing_or_discovered(r):
            discovered_rules.append(r)

    # 2. Config files
    for path in find_candidate_nftables_files():
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            file_rules = parse_iptables_text(content) if "iptables" in path else parse_nftables_text(content)
            for r in _apply_protected_port_splits(file_rules, protected_ports):
                if not _conflicts_existing_or_discovered(r):
                    discovered_rules.append(r)
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
    Safely deletes imported DNAT rules from legacy external tables via exact handles
    to guarantee zero collision with XForwarder's managed tables.
    Returns (deactivated_count, list_of_log_messages).
    """
    deactivated = 0
    logs: List[str] = []
    deleted_handles: Set[Tuple[str, str, str, int]] = set()

    # Map specs to rules to assist with live lookup if handle is missing
    specs_needing_lookup: Set[str] = set()
    for r in imported_rules:
        meta = r.get("_meta", {})
        if not meta.get("handle") and not meta.get("handles"):
            spec = str(meta.get("source_spec") or r.get("port_range") or r.get("port") or "")
            if spec:
                specs_needing_lookup.add(spec)

    # If any rule lacked a handle, query live handles in the kernel
    live_handles: Dict[str, Dict[str, Any]] = {}
    if specs_needing_lookup and shutil.which("nft"):
        try:
            for lr in get_live_nftables_rules():
                spec = str(lr.get("port_range") or lr.get("port") or "")
                lmeta = lr.get("_meta", {})
                if spec in specs_needing_lookup and (lmeta.get("handle") or lmeta.get("handles")):
                    live_handles[spec] = lmeta
        except Exception:
            pass

    for r in imported_rules:
        meta = r.get("_meta", {})
        port_label = r.get("port_range") or r.get("port")
        spec_key = str(port_label or "")
        source_key = str(meta.get("source_spec") or spec_key)
        if not spec_key:
            continue

        handles = list(meta.get("handles") or [])
        if not handles and meta.get("handle") is not None:
            handles.append(meta.get("handle"))
        table = meta.get("table", "")
        chain = meta.get("chain", "")
        family = meta.get("family", "ip")

        # Supplement with live handles if discovered
        if not handles and source_key in live_handles:
            live_meta = live_handles[source_key]
            handles = list(live_meta.get("handles") or [])
            if not handles and live_meta.get("handle") is not None:
                handles.append(live_meta.get("handle"))
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

        # 1. Handle-based deletion in NFTables (atomic, deduplicated per kernel handle)
        if handles and table and chain and shutil.which("nft"):
            for h in handles:
                try:
                    h_int = int(h)
                except (ValueError, TypeError):
                    continue
                h_key = (family, table, chain, h_int)
                if h_key in deleted_handles:
                    continue
                deleted_handles.add(h_key)
                try:
                    cmd = ["nft", "delete", "rule", family, table, chain, "handle", str(h_int)]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
                    if res.returncode == 0:
                        deactivated += 1
                        logs.append(f"Deactivated legacy rule for {spec_key} via handle {h_int} in {family} {table}/{chain}")
                    else:
                        logs.append(f"Warning: nft delete rule returned {res.returncode} for {spec_key}: {res.stderr.strip()}")
                except Exception as e:
                    logs.append(f"Error deactivating nft handle {h_int}: {e}")
            continue

        # 2. Iptables fallback deletion (single ports only)
        if shutil.which("iptables") and not r.get("port_range") and r.get("port"):
            p_single = r["port"]
            try:
                check_cmd = ["iptables", "-t", "nat", "-S", "PREROUTING"]
                res_s = subprocess.run(check_cmd, capture_output=True, text=True, timeout=2.0)
                if res_s.returncode == 0:
                    for line in res_s.stdout.splitlines():
                        if f"--dport {p_single}" in line and "-j DNAT" in line:
                            del_args = line.replace("-A PREROUTING", "-D PREROUTING").split()
                            del_cmd = ["iptables", "-t", "nat"] + del_args
                            subprocess.run(del_cmd, capture_output=True, timeout=2.0)
                            deactivated += 1
                            logs.append(f"Deactivated matching legacy iptables rule for port {p_single}")
                            break
            except Exception as e:
                logs.append(f"Error deactivating iptables rule for port {p_single}: {e}")

    return deactivated, logs


def deactivate_legacy_rules_for_ports(ports: Set[Union[int, str]]) -> Tuple[int, List[str]]:
    """
    Deactivates any active unmanaged kernel DNAT rules matching the specified ports or ranges.
    """
    if not ports:
        return 0, []

    port_keys = {str(p) for p in ports}
    target_rules: List[Dict[str, Any]] = []
    for p in ports:
        s_p = str(p).strip()
        if s_p.startswith("!="):
            ex_vals = sorted(_parse_port_tokens(s_p[2:], expand_limit=1000))
            if ex_vals:
                target_rules.append({"port": 1, "port_range": "1-65535", "excluded_ports": ex_vals})
        elif "-" in s_p:
            target_rules.append({"port_range": s_p})
        elif s_p.isdigit():
            target_rules.append({"port": int(s_p)})

    mock_rules: List[Dict[str, Any]] = []
    for lr in get_live_nftables_rules():
        spec = "!=" + ",".join(map(str, lr["excluded_ports"])) if lr.get("excluded_ports") else str(lr.get("port_range") or lr.get("port") or "")
        overlaps = any(rules_ports_overlap(lr, tr) for tr in target_rules)
        if spec in port_keys or lr.get("port") in ports or overlaps:
            mock_rules.append(lr)

    if not mock_rules:
        for p in ports:
            s_p = str(p).strip()
            if s_p.startswith("!="):
                continue
            if isinstance(p, int) or s_p.isdigit():
                mock_rules.append({"port": int(p), "_meta": {}})
            else:
                mock_rules.append({"port_range": s_p, "_meta": {}})

    return deactivate_legacy_rules(mock_rules)


def import_nftables_rules_into_config(
    config_path: str,
    deactivate_legacy: bool = True
) -> Tuple[int, List[Any], List[str]]:
    """
    Discovers unimported NFTables rules and atomically merges them into config_path.
    If deactivate_legacy is True, automatically backs up the old ruleset and deactivates
    the imported rules to prevent port collisions.
    Returns (imported_count, list_of_imported_ports_or_ranges, log_messages).
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
    importable = discover_importable_nftables_rules(rules, protected_ports=get_protected_ports(cfg))

    if not importable:
        return 0, [], ["No new unimported NFTables rules found"]

    # Optional legacy rule backup and deactivation
    if deactivate_legacy:
        backup_file = backup_legacy_nftables()
        if backup_file:
            logs.append(f"Created legacy ruleset backup at: {backup_file}")
        deact_count, deact_logs = deactivate_legacy_rules(importable)
        logs.extend(deact_logs)

    imported_ports: List[Any] = []
    for r in importable:
        # Clean private _meta before persisting to config.json
        clean_rule = {k: v for k, v in r.items() if not k.startswith("_")}
        rules.append(clean_rule)
        if clean_rule.get("excluded_ports"):
            imported_ports.append("!=" + ",".join(str(p) for p in clean_rule["excluded_ports"]))
        else:
            imported_ports.append(clean_rule.get("port_range") or clean_rule["port"])

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


def discover_all_relay_rules(
    existing_rules: Optional[List[Dict[str, Any]]] = None,
    protected_ports: Optional[Set[int]] = None
) -> Dict[str, Any]:
    """
    Unified discovery scanning both HAProxy configurations and active NFTables rules.
    Returns structured results with per-source metrics.
    """
    # 1. HAProxy rules
    from core.haproxy_parser import discover_importable_rules as discover_haproxy
    ha_rules = discover_haproxy(existing_rules)
    for r in ha_rules:
        r["_source"] = "haproxy"

    ha_ports = {r.get("port_range") or r["port"] for r in ha_rules if "port" in r or "port_range" in r}

    # 2. NFTables rules (exclude overlapping HAProxy ports to avoid double discovery)
    all_known = list(existing_rules or []) + ha_rules
    nft_rules = discover_importable_nftables_rules(all_known, protected_ports=protected_ports)
    for r in nft_rules:
        r["_source"] = "nftables"

    nft_ports = {
        ("!=" + ",".join(str(p) for p in r["excluded_ports"]))
        if r.get("excluded_ports") else (r.get("port_range") or r["port"])
        for r in nft_rules if "port" in r or "port_range" in r
    }

    combined = ha_rules + nft_rules
    combined_ports = sorted(
        list(ha_ports | nft_ports),
        key=lambda x: (0, str(x)) if str(x).startswith("!=") else (int(str(x).split("-")[0]), str(x))
    )

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

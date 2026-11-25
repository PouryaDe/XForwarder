#!/usr/bin/env python3
"""
XForwarder - Kernel Firewall & NFTables Orchestrator
Generates isolated NFTables rulesets for table ip/ip6 xfwd_orchestrator,
validates syntax dry-runs, and clears connection tracking states.
"""

import os
import sys
import json
import shutil
import socket
import subprocess
import re
import math
import ipaddress
from typing import Dict, Any, Tuple, Optional, List, Set

_IPV6_LITERAL_REGEX = re.compile(r"(?:\b[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}")


def is_ipv6_supported() -> bool:
    """Returns True if the host kernel has an active IPv6 networking stack."""
    if os.path.exists("/proc/net/if_inet6"):
        return True
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            return True
    except Exception:
        return False


def _find_system_bin(name: str, extra_dirs: Tuple[str, ...] = ("/usr/sbin", "/sbin", "/usr/bin", "/bin")) -> Optional[str]:
    """Locate a system binary even when systemd restricts PATH."""
    found = shutil.which(name)
    if found:
        return found
    for d in extra_dirs:
        candidate = f"{d}/{name}"
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _find_conntrack_bin() -> Optional[str]:
    """Locate the conntrack binary even when systemd restricts PATH."""
    return _find_system_bin("conntrack", ("/usr/sbin", "/sbin", "/usr/bin"))


def _find_tc_bin() -> Optional[str]:
    """Locate the tc binary even when systemd restricts PATH."""
    return _find_system_bin("tc", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))


def ensure_fq_qdisc(wan_iface: str, flow_limit: int = 1000) -> bool:
    """
    Re-applies `tc qdisc replace dev <wan> root fq flow_limit <N>` on Linux startup
    when `fq` is the active default qdisc (e.g. with BBR) so high-PPS tunnel flows
    avoid the kernel default 100p `flows_plimit` tail drops across reboots.
    """
    if sys.platform == "win32":
        return False
    clean_iface = str(wan_iface or "").strip()
    if not clean_iface or not IFACE_NAME_REGEX.match(clean_iface):
        return False
    safe_limit = max(100, min(int(flow_limit or 1000), 100000))
    try:
        if os.path.isfile("/proc/sys/net/core/default_qdisc"):
            with open("/proc/sys/net/core/default_qdisc", "r", encoding="utf-8") as f:
                if f.read().strip() != "fq":
                    return False
    except Exception:
        pass
    tc_bin = _find_tc_bin()
    if not tc_bin:
        return False
    try:
        res = subprocess.run(
            [tc_bin, "qdisc", "replace", "dev", clean_iface, "root", "fq", "flow_limit", str(safe_limit)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
            check=False,
        )
        if res.returncode == 0:
            return True
        res_fb = subprocess.run(
            [tc_bin, "qdisc", "replace", "dev", clean_iface, "root", "fq"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
            check=False,
        )
        return res_fb.returncode == 0
    except Exception:
        return False


def flush_conntrack(port: Any, proto: Optional[str] = None, reply_src: Optional[str] = None) -> None:
    """Flushes stale conntrack states for TCP and UDP on a validated port or tiny range (optionally scoped to a specific backend IP)."""
    ports_to_flush: List[int] = []
    s_port = str(port or "").strip()
    if "-" in s_port:
        parts = s_port.split("-", 1)
        try:
            sp, ep = int(parts[0].strip()), int(parts[1].strip())
            if 1 <= sp <= ep <= 65535 and (ep - sp) <= 32:
                ports_to_flush = list(range(sp, ep + 1))
        except (TypeError, ValueError):
            return
    else:
        try:
            port_int = int(port)
            if 1 <= port_int <= 65535:
                ports_to_flush = [port_int]
        except (TypeError, ValueError):
            return

    if not ports_to_flush:
        return
    conntrack_bin = _find_conntrack_bin()
    if not conntrack_bin:
        return

    clean_reply_src: Optional[str] = None
    reply_family: Optional[str] = None
    if reply_src is not None and str(reply_src).strip():
        cand = str(reply_src).strip().strip("[]")
        try:
            ip_obj = ipaddress.ip_address(cand)
            clean_reply_src = str(ip_obj)
            reply_family = "ipv6" if ip_obj.version == 6 else "ipv4"
        except ValueError:
            return

    protos = [proto] if proto in ("tcp", "udp") else ["tcp", "udp"]
    for port_int in ports_to_flush:
        for p in protos:
            try:
                if clean_reply_src and reply_family:
                    cmd = [
                        conntrack_bin, "-D", "-f", reply_family,
                        "-p", p, "--orig-port-dst", str(port_int),
                        "--reply-src", clean_reply_src
                    ]
                else:
                    cmd = [conntrack_bin, "-D", "-p", p, "--dport", str(port_int)]
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5.0,
                    check=False
                )
            except Exception:
                pass


def normalize_lb_weights(weights: List[int], max_slots: int = 100) -> List[int]:
    """Reduces integer weights via GCD and caps total slot count for compact discrete nftables maps."""
    if not weights:
        return []
    clean = [max(1, min(int(w or 1), 100)) for w in weights]
    g = clean[0]
    for w in clean[1:]:
        g = math.gcd(g, w)
    reduced = [max(1, w // g) for w in clean]
    total = sum(reduced)
    if total > max_slots:
        scale = 64.0 / float(total)
        reduced = [max(1, int(round(w * scale))) for w in reduced]
    return reduced


def build_nft_lb_dnat_entries(
    backends: List[Tuple[str, Optional[int], int]],
    lb_mode: str,
    ip_version: int,
    protos: Tuple[str, ...],
    dport_selectors: List[Any],
    iif_prefix: str,
    inbound_start_port: int,
    rule_idx: int,
    preserve_range: bool = False,
    is_inbound_range: bool = False
) -> Tuple[List[str], List[str]]:
    """
    Generates NFTables load-balancing DNAT rules (discrete anonymous maps for same-port/1:1
    and vmap helper chains for port translation) compatible with Linux kernels >= 4.9.
    Returns (dnat_rules: List[str], extra_chains: List[str]).
    """
    if not backends:
        return [], []

    valid_protos = [p for p in protos if p in ("tcp", "udp")]
    if not valid_protos:
        return [], []

    is_ipv6 = (ip_version == 6)
    ip_kw = "ip6" if is_ipv6 else "ip"
    sanitized_backends: List[Tuple[str, Optional[int], int]] = []
    for ip_str, b_port, b_weight in backends:
        clean_ip = str(ip_str or "").strip().strip("[]")
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
        except ValueError:
            continue
        if ip_obj.version != ip_version:
            continue
        eff_bp: Optional[int] = None
        if b_port is not None:
            try:
                p_int = int(b_port)
                if 1 <= p_int <= 65535:
                    eff_bp = p_int
            except (TypeError, ValueError):
                pass
        sanitized_backends.append((str(ip_obj), eff_bp, max(1, min(int(b_weight or 1), 100))))

    if not sanitized_backends:
        return [], []

    dnat_rules: List[str] = []
    extra_chains: List[str] = []

    if len(sanitized_backends) == 1:
        clean_ip, b_port, _ = sanitized_backends[0]
        if preserve_range or b_port is None:
            dnat_target = f"[{clean_ip}]" if is_ipv6 else clean_ip
        else:
            dnat_target = f"[{clean_ip}]:{b_port}" if is_ipv6 else f"{clean_ip}:{b_port}"
        for listen_spec in dport_selectors:
            for p_name in valid_protos:
                dnat_rules.append(
                    f'        {iif_prefix}{p_name} dport {listen_spec} dnat to {dnat_target}'
                )
        return dnat_rules, extra_chains

    weights = normalize_lb_weights([b[2] for b in sanitized_backends])
    total_slots = sum(weights)

    mode = str(lb_mode or "ip_hash").lower().strip()
    if mode == "round_robin":
        selector = f"numgen inc mod {total_slots}"
    elif mode == "random":
        selector = f"numgen random mod {total_slots}"
    else:
        selector = f"jhash {ip_kw} saddr mod {total_slots}"

    # An inbound range mapped to a single fixed port always requires explicit :port DNAT,
    # even when the fixed target port numerically equals inbound_start_port.
    needs_port_translation = bool(is_inbound_range and not preserve_range)
    if not preserve_range and not needs_port_translation:
        for _, b_port, _ in sanitized_backends:
            if b_port is not None and int(b_port) != int(inbound_start_port):
                needs_port_translation = True
                break

    if not needs_port_translation:
        slot_pairs: List[str] = []
        slot_idx = 0
        for (clean_ip, _, _), w in zip(sanitized_backends, weights):
            for _ in range(w):
                slot_pairs.append(f"{slot_idx} : {clean_ip}")
                slot_idx += 1
        map_body = ", ".join(slot_pairs)
        for listen_spec in dport_selectors:
            for p_name in valid_protos:
                dnat_rules.append(
                    f'        {iif_prefix}{p_name} dport {listen_spec} dnat to {selector} map {{ {map_body} }}'
                )
    else:
        slot_pairs = []
        slot_idx = 0
        for m_idx, ((clean_ip, b_port, _), w) in enumerate(zip(sanitized_backends, weights)):
            eff_port = int(b_port) if b_port is not None else int(inbound_start_port)
            dnat_target = f"[{clean_ip}]:{eff_port}" if is_ipv6 else f"{clean_ip}:{eff_port}"
            chain_name = f"xfwd_lb_r{int(rule_idx)}_m{m_idx}"
            chain_lines = [f"    chain {chain_name} {{"]
            for p_name in valid_protos:
                chain_lines.append(f"        meta l4proto {p_name} dnat to {dnat_target}")
            chain_lines.append("    }")
            extra_chains.append("\n".join(chain_lines))
            for _ in range(w):
                slot_pairs.append(f"{slot_idx} : jump {chain_name}")
                slot_idx += 1
        vmap_body = ", ".join(slot_pairs)
        for listen_spec in dport_selectors:
            for p_name in valid_protos:
                dnat_rules.append(
                    f'        {iif_prefix}{p_name} dport {listen_spec} {selector} vmap {{ {vmap_body} }}'
                )

    return dnat_rules, extra_chains


IFACE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.\-]{0,14}$")

DSR_DIRECT_TABLE_BASE = 42600
DSR_DIRECT_PRIO_BASE = 12600
DSR_DIRECT_MARK_BASE = 0x42600001
DSR_DIRECT_MAX_SLOTS = 64
DSR_DIRECT_STATE_PATH = "/run/xforwarder/dsr_direct_routes.json"
_DSR_DIRECT_POLICY_APPLIED = False


def _format_postrouting_masquerades(custom_oifs: Optional[Set[str]] = None) -> str:
    """Builds validated postrouting masquerade statements including custom tunnel interfaces."""
    lines = [
        "        ct status dnat masquerade",
        '        oifname "gre*" masquerade',
        '        oifname "ipip*" masquerade',
        '        oifname "ftcp*" masquerade',
        '        oifname "awg*" masquerade',
        '        oifname "gnv*" masquerade',
        '        oifname "vxlan*" masquerade',
        '        oifname "wg*" masquerade',
        '        oifname "tun*" masquerade',
        '        oifname "xfrm*" masquerade',
        '        oifname "esp*" masquerade',
        '        oifname "backhaul*" masquerade',
    ]
    for iface in sorted(custom_oifs or set()):
        clean_iface = str(iface or "").strip()
        if IFACE_NAME_REGEX.match(clean_iface):
            lines.append(f'        oifname "{clean_iface}" masquerade')
    return "\n".join(lines)


def _run_ip_cmd(ip_bin: str, args: List[str]) -> subprocess.CompletedProcess:
    """Executes an iproute2 command with bounded timeout."""
    return subprocess.run(
        [ip_bin] + args,
        capture_output=True,
        text=True,
        timeout=2.0,
        check=False,
    )


def _load_dsr_direct_state(state_path: str) -> Dict[int, Dict[str, Any]]:
    """Loads persisted XForwarder-owned DSR Direct policy routing slots."""
    if not state_path or not os.path.isfile(state_path):
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        slots = raw.get("slots", []) if isinstance(raw, dict) else []
        out: Dict[int, Dict[str, Any]] = {}
        for item in slots:
            if not isinstance(item, dict):
                continue
            tid = int(item.get("table_id", 0))
            if DSR_DIRECT_TABLE_BASE <= tid < DSR_DIRECT_TABLE_BASE + DSR_DIRECT_MAX_SLOTS:
                out[tid] = item
        return out
    except Exception:
        return {}


def _save_dsr_direct_state(state_path: str, slots: List[Dict[str, Any]]) -> None:
    """Atomically persists or removes XForwarder-owned DSR Direct policy routing state."""
    if not state_path:
        return
    try:
        if not slots:
            if os.path.isfile(state_path):
                os.remove(state_path)
            return
        parent = os.path.dirname(state_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = f"{state_path}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"slots": slots}, f, indent=2)
        os.replace(tmp_path, state_path)
    except Exception:
        pass


def _parse_ip_rule_entry(line: str) -> Tuple[Optional[int], Optional[Tuple[int, int]], Optional[int], bool]:
    """Parses `(priority, (fwmark_val, fwmark_mask), lookup_table, has_not)` from one `ip -4 rule show` line."""
    words = line.strip().split()
    if not words or not words[0].endswith(":"):
        return None, None, None, False
    try:
        prio = int(words[0][:-1])
    except ValueError:
        return None, None, None, False
    fwmark_pair: Optional[Tuple[int, int]] = None
    has_not = False
    if "fwmark" in words:
        idx = words.index("fwmark")
        has_not = "not" in words[:idx]
        if idx + 1 < len(words):
            parts = words[idx + 1].split("/", 1)
            try:
                val = int(parts[0], 0)
                mask = int(parts[1], 0) if len(parts) == 2 else 0xFFFFFFFF
                fwmark_pair = (val, mask)
            except ValueError:
                pass
    lookup_table: Optional[int] = None
    if "lookup" in words:
        idx = words.index("lookup")
        if idx + 1 < len(words):
            try:
                lookup_table = int(words[idx + 1])
            except ValueError:
                pass
    return prio, fwmark_pair, lookup_table, has_not


def _delete_dsr_direct_slot(ip_bin: str, slot: Dict[str, Any]) -> None:
    """Removes kernel ip rule and routes recorded for one XForwarder-owned DSR Direct slot."""
    try:
        prio = int(slot.get("priority", 0))
        tid = int(slot.get("table_id", 0))
        fwmark_hex = hex(int(str(slot.get("fwmark", "0")), 0))
        iface = str(slot.get("iface", "")).strip()
    except (TypeError, ValueError):
        return
    if prio > 0 and tid > 0 and fwmark_hex != "0x0":
        _run_ip_cmd(ip_bin, ["rule", "del", "priority", str(prio), "fwmark", f"{fwmark_hex}/0xffffffff", "lookup", str(tid)])
    if tid > 0 and iface and IFACE_NAME_REGEX.match(iface):
        _run_ip_cmd(ip_bin, ["route", "del", "default", "dev", iface, "table", str(tid)])
    for ip_str in (slot.get("throw_ips") or []):
        try:
            clean_ip = str(ipaddress.IPv4Address(str(ip_str).strip()))
            _run_ip_cmd(ip_bin, ["route", "del", "throw", f"{clean_ip}/32", "table", str(tid)])
        except ValueError:
            continue


def cleanup_dsr_direct_policy_routing(state_path: str = DSR_DIRECT_STATE_PATH) -> None:
    """Removes XForwarder-owned DSR Direct policy routing entries without touching unrelated rules."""
    global _DSR_DIRECT_POLICY_APPLIED
    _DSR_DIRECT_POLICY_APPLIED = False
    if sys.platform == "win32":
        return
    prev_by_table = _load_dsr_direct_state(state_path)
    if not prev_by_table:
        try:
            if state_path and os.path.isfile(state_path):
                os.remove(state_path)
        except Exception:
            pass
        return
    ip_bin = _find_system_bin("ip", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))
    if ip_bin:
        for slot in prev_by_table.values():
            _delete_dsr_direct_slot(ip_bin, slot)
    _save_dsr_direct_state(state_path, [])


def ensure_dsr_direct_policy_routing(
    routes_spec: Optional[List[Dict[str, Any]]],
    state_path: str = DSR_DIRECT_STATE_PATH
) -> Tuple[bool, Optional[str]]:
    """
    Reconciles dedicated policy routing tables/rules for `nftables_dsr_direct` SYN-ACK tunnel return.
    Validates ownership before modifying kernel tables and rolls back newly added items on failure.
    """
    global _DSR_DIRECT_POLICY_APPLIED
    if not routes_spec:
        cleanup_dsr_direct_policy_routing(state_path=state_path)
        return True, None
    if sys.platform == "win32":
        _DSR_DIRECT_POLICY_APPLIED = True
        return True, None

    ip_bin = _find_system_bin("ip", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))
    if not ip_bin:
        return False, "iproute2 'ip' binary not found for DSR Direct policy routing"

    desired_by_table: Dict[int, Dict[str, Any]] = {}
    for raw in routes_spec:
        if not isinstance(raw, dict):
            continue
        iface = str(raw.get("iface") or "").strip()
        if not iface or not IFACE_NAME_REGEX.match(iface):
            return False, f"Invalid DSR Direct tunnel interface '{iface}'"
        try:
            tid = int(raw.get("table_id"))
            prio = int(raw.get("priority"))
            mark_int = int(str(raw.get("fwmark")), 0)
        except (TypeError, ValueError):
            return False, "Invalid DSR Direct policy routing identifiers"
        if not (DSR_DIRECT_TABLE_BASE <= tid < DSR_DIRECT_TABLE_BASE + DSR_DIRECT_MAX_SLOTS):
            return False, f"DSR Direct route table {tid} out of reserved range"
        if not (DSR_DIRECT_PRIO_BASE <= prio < DSR_DIRECT_PRIO_BASE + DSR_DIRECT_MAX_SLOTS):
            return False, f"DSR Direct rule priority {prio} out of reserved range"
        if not (DSR_DIRECT_MARK_BASE <= mark_int < DSR_DIRECT_MARK_BASE + DSR_DIRECT_MAX_SLOTS):
            return False, f"DSR Direct fwmark {hex(mark_int)} out of reserved range"
        clean_throws: List[str] = []
        seen_throws: Set[str] = set()
        for t_ip in (raw.get("throw_ips") or []):
            try:
                ip_str = str(ipaddress.IPv4Address(str(t_ip).strip()))
            except ValueError:
                return False, f"Invalid DSR Direct throw IP '{t_ip}'"
            if ip_str not in seen_throws:
                seen_throws.add(ip_str)
                clean_throws.append(ip_str)
        desired_by_table[tid] = {
            "iface": iface,
            "table_id": tid,
            "priority": prio,
            "fwmark": f"0x{mark_int:08x}",
            "throw_ips": sorted(clean_throws),
        }

    if not desired_by_table:
        cleanup_dsr_direct_policy_routing(state_path=state_path)
        return True, None

    prev_by_table = _load_dsr_direct_state(state_path)
    rules_res = _run_ip_cmd(ip_bin, ["-4", "rule", "show"])
    if rules_res.returncode != 0:
        return False, f"Failed inspecting ip rules: {rules_res.stderr.strip()}"
    rule_lines = [ln for ln in rules_res.stdout.splitlines() if ln.strip()]

    existing_own_rule: Set[int] = set()
    for tid, slot in desired_by_table.items():
        prio = slot["priority"]
        mark_int = int(slot["fwmark"], 0)
        prio_matches = []
        for ln in rule_lines:
            l_prio, l_fw, l_tbl, l_not = _parse_ip_rule_entry(ln)
            if l_prio == prio:
                prio_matches.append((l_fw, l_tbl, l_not))
                continue
            if l_tbl == tid:
                return False, f"Policy route table {tid} is already referenced by foreign ip rule"
            if l_fw is not None:
                f_val, f_mask = l_fw
                matches = (mark_int & f_mask) == (f_val & f_mask)
                if l_not:
                    matches = not matches
                if matches:
                    return False, f"Policy fwmark {slot['fwmark']} collides with existing ip rule"
        if len(prio_matches) > 1:
            return False, f"Multiple ip rules exist at reserved priority {prio}"
        if len(prio_matches) == 1:
            l_fw, l_tbl, l_not = prio_matches[0]
            if l_not or l_tbl != tid or l_fw is None or l_fw[0] != mark_int or l_fw[1] != 0xFFFFFFFF:
                return False, f"Policy priority {prio} collides with unrelated ip rule"
            existing_own_rule.add(tid)

    existing_routes_by_table: Dict[int, List[Dict[str, Any]]] = {}
    for tid, slot in desired_by_table.items():
        rt_res = _run_ip_cmd(ip_bin, ["-j", "-4", "route", "show", "table", str(tid)])
        err_text = rt_res.stderr.strip()
        err_lower = err_text.lower()
        table_missing = "fib table does not exist" in err_lower or "does not exist" in err_lower
        if rt_res.returncode != 0 and err_text and not table_missing:
            return False, f"Failed inspecting route table {tid}: {err_text}"
        routes_list: List[Dict[str, Any]] = []
        raw_out = "" if table_missing else rt_res.stdout.strip()
        if raw_out:
            try:
                parsed_rt = json.loads(raw_out)
                if isinstance(parsed_rt, list):
                    routes_list = parsed_rt
            except ValueError:
                return False, f"Route table {tid} is non-empty or returned unparseable output"
        if routes_list and tid not in prev_by_table and tid not in existing_own_rule:
            return False, f"Reserved route table {tid} is not empty and not owned by XForwarder"
        prev_iface = str((prev_by_table.get(tid) or {}).get("iface") or "")
        for r in routes_list:
            if not isinstance(r, dict):
                continue
            rtype = str(r.get("type") or "")
            rdst = str(r.get("dst") or "default")
            if rtype == "throw":
                continue
            rdev = str(r.get("dev") or "")
            if rdst == "default" and rdev in (slot["iface"], prev_iface) and rdev and not r.get("gateway"):
                continue
            return False, f"Route table {tid} contains unrelated route entry"
        existing_routes_by_table[tid] = routes_list

    undo_cmds: List[List[str]] = []
    try:
        for tid, slot in desired_by_table.items():
            iface = slot["iface"]
            prio = slot["priority"]
            fwmark = slot["fwmark"]
            prev_throws = set((prev_by_table.get(tid) or {}).get("throw_ips") or [])
            cur_routes = existing_routes_by_table.get(tid, [])
            cur_throws = {
                str(r.get("dst", "")).split("/", 1)[0]
                for r in cur_routes
                if isinstance(r, dict) and r.get("type") == "throw"
            }
            cur_has_default = any(
                isinstance(r, dict) and str(r.get("dst", "default")) == "default" and str(r.get("dev", "")) == iface
                for r in cur_routes
            )
            desired_throws = set(slot["throw_ips"])
            for stale_ip in sorted((prev_throws | cur_throws) - desired_throws):
                _run_ip_cmd(ip_bin, ["route", "del", "throw", f"{stale_ip}/32", "table", str(tid)])

            for t_ip in slot["throw_ips"]:
                if t_ip not in cur_throws:
                    res = _run_ip_cmd(ip_bin, ["route", "replace", "throw", f"{t_ip}/32", "table", str(tid)])
                    if res.returncode != 0:
                        raise RuntimeError(res.stderr.strip() or f"Failed adding throw route for {t_ip}")
                    undo_cmds.append(["route", "del", "throw", f"{t_ip}/32", "table", str(tid)])

            if not cur_has_default:
                res = _run_ip_cmd(ip_bin, ["route", "replace", "default", "dev", iface, "table", str(tid)])
                if res.returncode != 0:
                    raise RuntimeError(res.stderr.strip() or f"Failed adding default route on {iface}")
                undo_cmds.append(["route", "del", "default", "dev", iface, "table", str(tid)])

            if tid not in existing_own_rule:
                res = _run_ip_cmd(ip_bin, ["rule", "add", "priority", str(prio), "fwmark", f"{fwmark}/0xffffffff", "lookup", str(tid)])
                if res.returncode != 0:
                    raise RuntimeError(res.stderr.strip() or f"Failed adding ip rule at priority {prio}")
                undo_cmds.append(["rule", "del", "priority", str(prio), "fwmark", f"{fwmark}/0xffffffff", "lookup", str(tid)])
    except Exception as exc:
        for cmd in reversed(undo_cmds):
            _run_ip_cmd(ip_bin, cmd)
        return False, f"DSR Direct policy routing error: {exc}"

    for stale_tid, stale_slot in prev_by_table.items():
        if stale_tid not in desired_by_table:
            _delete_dsr_direct_slot(ip_bin, stale_slot)

    _save_dsr_direct_state(state_path, [desired_by_table[k] for k in sorted(desired_by_table)])
    _DSR_DIRECT_POLICY_APPLIED = True
    return True, None


def reconcile_dsr_direct_kernel_routes(state_path: str = DSR_DIRECT_STATE_PATH) -> None:
    """
    Re-installs missing `default dev <iface>` entries in active DSR Direct routing
    tables when an underlying tunnel interface (e.g. esp*, tcptun*) flaps or rekeys.
    """
    ip_bin = shutil.which("ip")
    if not ip_bin or not os.path.isfile(state_path):
        return
    slots = _load_dsr_direct_state(state_path)
    if not slots:
        return
    for tid, slot in slots.items():
        iface = str(slot.get("iface") or "").strip()
        if not iface or not os.path.exists(f"/sys/class/net/{iface}"):
            continue
        rt_res = _run_ip_cmd(ip_bin, ["-4", "route", "show", "table", str(tid), "default"])
        err_l = rt_res.stderr.lower()
        has_default = (
            rt_res.returncode == 0
            and "fib table does not exist" not in err_l
            and f"dev {iface}" in rt_res.stdout
        )
        if not has_default:
            _run_ip_cmd(ip_bin, ["route", "replace", "default", "dev", iface, "table", str(tid)])


DSR_SYSCTL_CONF_PATH = "/etc/sysctl.d/99-xforwarder-dsr.conf"
_DSR_SYSCTL_APPLIED = False
_NFT_MAPS_SUPPORTED: Optional[bool] = None

_IIF_NEQ_PREFIX_RE = re.compile(r'^\s*iifname\s+!=\s+"([^"]+)"\s+')
_RAW_SINGLE_RE = re.compile(
    r"^\s*"
    r'(?:(iifname\s+(?:!=\s*)?"[^"]+")\s+)?'
    r"(?:(ip6?\s+daddr\s+\S+)\s+)?"
    r"(tcp|udp)\s+dport\s+(\d+)\s+"
    r"(notrack\s+)?"
    r"(ip6?)\s+daddr\s+set\s+(\S+)\s*$"
)
_DNAT_SINGLE_RE = re.compile(
    r"^\s*"
    r'(?:(iifname\s+(?:!=\s*)?"[^"]+")\s+)?'
    r"(?:(ip6?\s+daddr\s+\S+)\s+)?"
    r"(tcp|udp)\s+dport\s+(\d+)\s+"
    r"dnat\s+to\s+(?:\[([0-9a-fA-F:]+)\]|([0-9.]+)):(\d+)\s*$"
)
_EXCL_DPORT_RE = re.compile(r"\bdport\s+!=")


def cleanup_dsr_sysctl(sysctl_conf_path: str = DSR_SYSCTL_CONF_PATH) -> None:
    """Removes persistent DSR sysctl drop-in when no DSR rules remain active."""
    if sys.platform == "win32":
        return
    try:
        if os.path.isfile(sysctl_conf_path):
            os.remove(sysctl_conf_path)
    except Exception:
        pass


def ensure_dsr_sysctl(
    ifaces: Optional[Set[str]] = None,
    sysctl_conf_path: str = DSR_SYSCTL_CONF_PATH,
    proc_net_conf_dir: str = "/proc/sys/net/ipv4/conf"
) -> None:
    """
    Ensures Linux kernel IP forwarding and rp_filter=0 are configured and persisted for asymmetric DSR routing.
    Required so packets arriving on tunnel interfaces with un-NATted client IPs are not dropped on reboot or tune.
    """
    if sys.platform == "win32":
        return

    target_ifaces: Set[str] = set()
    for iface in (ifaces or set()):
        clean_if = str(iface or "").strip()
        if IFACE_NAME_REGEX.match(clean_if):
            target_ifaces.add(clean_if)

    # Also disable rp_filter on any active host/tunnel interfaces (critical when ingress_iface/tunnel_iface is Auto)
    try:
        if proc_net_conf_dir and os.path.isdir(proc_net_conf_dir):
            for name in os.listdir(proc_net_conf_dir):
                if name in ("all", "default", "lo"):
                    continue
                if IFACE_NAME_REGEX.match(name):
                    target_ifaces.add(name)
    except Exception:
        pass

    settings = [
        "net.ipv4.ip_forward=1",
        "net.ipv4.conf.all.rp_filter=0",
        "net.ipv4.conf.default.rp_filter=0",
    ]
    for clean_if in sorted(target_ifaces):
        settings.append(f"net.ipv4.conf.{clean_if}.rp_filter=0")

    # Atomically persist drop-in so sysctl --system or reboots never re-enable rp_filter=1
    try:
        conf_dir = os.path.dirname(sysctl_conf_path)
        if conf_dir and os.path.isdir(conf_dir):
            tmp_path = f"{sysctl_conf_path}.tmp.{os.getpid()}"
            content = "# Managed by XForwarder - Asymmetric DSR Tunnel Routing\n" + "\n".join(settings) + "\n"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, sysctl_conf_path)
    except Exception:
        pass

    sysctl_bin = _find_system_bin("sysctl", ("/sbin", "/usr/sbin", "/bin"))
    if not sysctl_bin:
        return

    for kv in settings:
        try:
            subprocess.run(
                [sysctl_bin, "-w", kv],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
                check=False
            )
        except Exception:
            pass


def _is_ipv6_nft_statement(stmt: str) -> bool:
    """Returns True if an NFTables rule or chain block targets IPv6 addresses or selectors."""
    return (
        "dnat to [" in stmt
        or "]:" in stmt
        or "ip6 daddr" in stmt
        or "ip6 saddr" in stmt
        or "dnat ip6 to" in stmt
        or "snat to [" in stmt
        or bool(_IPV6_LITERAL_REGEX.search(stmt))
    )


def _detect_early_wan_bypass(rules: List[str]) -> Optional[str]:
    """Returns WAN iface if every rule in the chain explicitly excludes it via `iifname != "<wan>"`."""
    if not rules:
        return None
    ifaces: Set[str] = set()
    for r in rules:
        m = _IIF_NEQ_PREFIX_RE.match(r)
        if not m:
            return None
        ifaces.add(m.group(1))
    return next(iter(ifaces)) if len(ifaces) == 1 else None


def _format_nft_map_block(name: str, key_type: str, val_type: str, elements: List[str], kind: str = "map") -> str:
    """Formats a named NFTables map or set declaration block."""
    if kind == "set":
        elems = ", ".join(elements)
        return (
            f"    set {name} {{\n"
            f"        type {key_type}\n"
            f"        elements = {{ {elems} }}\n"
            f"    }}"
        )
    elems = ", ".join(elements)
    return (
        f"    map {name} {{\n"
        f"        type {key_type} : {val_type}\n"
        f"        elements = {{ {elems} }}\n"
        f"    }}"
    )


def _optimize_raw_rules(raw_rules: List[str], ip_kw: str, optimize_maps: bool = True) -> Tuple[List[str], List[str]]:
    """
    Optimizes raw_prerouting rules with optional early WAN bypass and O(1) maps
    grouped strictly by (iif_clause, daddr_clause, has_notrack, ip_kw).
    """
    if not raw_rules:
        return [], []

    wan_bypass = _detect_early_wan_bypass(raw_rules)
    bypass_lines = [f'        iifname "{wan_bypass}" accept'] if wan_bypass else []

    if not optimize_maps:
        return [], bypass_lines + list(raw_rules)

    grouped: Dict[Tuple[str, str, bool, str], Dict[str, Dict[int, str]]] = {}
    group_order: List[Tuple[str, str, bool, str]] = []
    group_raw_lines: Dict[Tuple[str, str, bool, str, str], List[str]] = {}
    passthrough: List[str] = []

    for r in raw_rules:
        m = _RAW_SINGLE_RE.match(r)
        if not m:
            passthrough.append(r)
            continue
        iif_c, daddr_c, proto, port_s, nt_kw, r_ip_kw, target_ip = m.groups()
        port_i = int(port_s)
        try:
            ip_obj = ipaddress.ip_address(target_ip)
        except ValueError:
            passthrough.append(r)
            continue
        if not (1 <= port_i <= 65535) or (ip_obj.version == 6) != ((r_ip_kw or ip_kw) == "ip6"):
            passthrough.append(r)
            continue
        gkey = (iif_c or "", daddr_c or "", bool(nt_kw), r_ip_kw or ip_kw)
        if gkey not in grouped:
            grouped[gkey] = {"tcp": {}, "udp": {}}
            group_order.append(gkey)
        p_map = grouped[gkey][proto]
        if port_i not in p_map:
            p_map[port_i] = str(ip_obj)
            group_raw_lines.setdefault((*gkey, proto), []).append(r)
        else:
            passthrough.append(r)

    addr_type = "ipv6_addr" if ip_kw == "ip6" else "ipv4_addr"
    map_defs: List[str] = []
    opt_rules: List[str] = list(bypass_lines)
    map_idx = 0

    for gkey in group_order:
        iif_c, daddr_c, has_nt, r_ip_kw = gkey
        prefix = "".join(f"{c} " for c in (iif_c, daddr_c) if c)
        tcp_map = grouped[gkey]["tcp"]
        udp_map = grouped[gkey]["udp"]

        if len(tcp_map) >= 2 and tcp_map == udp_map:
            map_name = f"raw_dst_map_{map_idx}"
            elems = [f"{p} : {tcp_map[p]}" for p in sorted(tcp_map)]
            map_defs.append(_format_nft_map_block(map_name, "inet_service", addr_type, elems))
            if has_nt:
                set_name = f"raw_nt_set_{map_idx}"
                set_elems = [str(p) for p in sorted(tcp_map)]
                map_defs.append(_format_nft_map_block(set_name, "inet_service", "", set_elems, kind="set"))
                for p_name in ("tcp", "udp"):
                    opt_rules.append(f"        {prefix}{p_name} dport @{set_name} notrack")
                    opt_rules.append(f"        {prefix}{r_ip_kw} daddr set {p_name} dport map @{map_name}")
            else:
                for p_name in ("tcp", "udp"):
                    opt_rules.append(f"        {prefix}{r_ip_kw} daddr set {p_name} dport map @{map_name}")
            map_idx += 1
            continue

        for p_name in ("tcp", "udp"):
            p_map = grouped[gkey][p_name]
            if len(p_map) >= 2:
                map_name = f"raw_dst_map_{map_idx}"
                elems = [f"{p} : {p_map[p]}" for p in sorted(p_map)]
                map_defs.append(_format_nft_map_block(map_name, "inet_service", addr_type, elems))
                if has_nt:
                    set_name = f"raw_nt_set_{map_idx}"
                    set_elems = [str(p) for p in sorted(p_map)]
                    map_defs.append(_format_nft_map_block(set_name, "inet_service", "", set_elems, kind="set"))
                    opt_rules.append(f"        {prefix}{p_name} dport @{set_name} notrack")
                opt_rules.append(f"        {prefix}{r_ip_kw} daddr set {p_name} dport map @{map_name}")
                map_idx += 1
            elif len(p_map) == 1:
                opt_rules.extend(group_raw_lines.get((*gkey, p_name), []))

    opt_rules.extend(passthrough)
    return map_defs, opt_rules


def _optimize_dnat_rules(dnat_rules: List[str], ip_kw: str, optimize_maps: bool = True) -> Tuple[List[str], List[str]]:
    """
    Optimizes prerouting DNAT rules with optional early WAN bypass and O(1) maps
    for same-port 1:1 mappings grouped by (iif_clause, daddr_clause, ip_kw).
    """
    if not dnat_rules:
        return [], []

    wan_bypass = _detect_early_wan_bypass(dnat_rules)
    bypass_lines = [f'        iifname "{wan_bypass}" accept'] if wan_bypass else []

    if not optimize_maps:
        return [], bypass_lines + list(dnat_rules)

    grouped: Dict[Tuple[str, str, str], Dict[str, Dict[int, str]]] = {}
    group_order: List[Tuple[str, str, str]] = []
    group_raw_lines: Dict[Tuple[str, str, str, str], List[str]] = {}
    specific_passthrough: List[str] = []
    wildcard_passthrough: List[str] = []

    for r in dnat_rules:
        m = _DNAT_SINGLE_RE.match(r)
        if m:
            iif_c, daddr_c, proto, in_p_s, v6_t, v4_t, out_p_s = m.groups()
            in_p, out_p = int(in_p_s), int(out_p_s)
            if in_p == out_p and 1 <= in_p <= 65535:
                r_ip_kw = "ip6" if v6_t else "ip"
                try:
                    ip_obj = ipaddress.ip_address(v6_t or v4_t)
                except ValueError:
                    ip_obj = None
                if ip_obj is not None and (ip_obj.version == 6) == (r_ip_kw == "ip6"):
                    gkey = (iif_c or "", daddr_c or "", r_ip_kw)
                    if gkey not in grouped:
                        grouped[gkey] = {"tcp": {}, "udp": {}}
                        group_order.append(gkey)
                    p_map = grouped[gkey][proto]
                    if in_p not in p_map:
                        p_map[in_p] = str(ip_obj)
                        group_raw_lines.setdefault((*gkey, proto), []).append(r)
                        continue
        if _EXCL_DPORT_RE.search(r):
            wildcard_passthrough.append(r)
        else:
            specific_passthrough.append(r)

    addr_type = "ipv6_addr" if ip_kw == "ip6" else "ipv4_addr"
    map_defs: List[str] = []
    opt_rules: List[str] = list(bypass_lines)
    map_idx = 0

    for gkey in group_order:
        iif_c, daddr_c, _ = gkey
        prefix = "".join(f"{c} " for c in (iif_c, daddr_c) if c)
        tcp_map = grouped[gkey]["tcp"]
        udp_map = grouped[gkey]["udp"]

        if len(tcp_map) >= 2 and tcp_map == udp_map:
            map_name = f"dnat_map_{map_idx}"
            elems = [f"{p} : {tcp_map[p]}" for p in sorted(tcp_map)]
            map_defs.append(_format_nft_map_block(map_name, "inet_service", addr_type, elems))
            for p_name in ("tcp", "udp"):
                opt_rules.append(f"        {prefix}dnat to {p_name} dport map @{map_name}")
            map_idx += 1
            continue

        for p_name in ("tcp", "udp"):
            p_map = grouped[gkey][p_name]
            if len(p_map) >= 2:
                map_name = f"dnat_map_{map_idx}"
                elems = [f"{p} : {p_map[p]}" for p in sorted(p_map)]
                map_defs.append(_format_nft_map_block(map_name, "inet_service", addr_type, elems))
                opt_rules.append(f"        {prefix}dnat to {p_name} dport map @{map_name}")
                map_idx += 1
            elif len(p_map) == 1:
                opt_rules.extend(group_raw_lines.get((*gkey, p_name), []))

    opt_rules.extend(specific_passthrough)
    opt_rules.extend(wildcard_passthrough)
    return map_defs, opt_rules


def _build_forward_counter_vmaps(
    all_ports: Set[int],
    all_ranges: Set[str],
    excl_counters: List[Tuple[str, str]],
    has_untracked: bool,
    optimize_maps: bool = True
) -> Tuple[List[str], List[str], List[str]]:
    """
    Builds O(1) vmap counter chains & maps when >= 2 single ports exist,
    plus linear rules for port ranges and negated exclusion rules.
    Returns (vmap_defs, vmap_chains, forward_counter_lines).
    """
    vmap_defs: List[str] = []
    vmap_chains: List[str] = []
    forward_lines: List[str] = []
    sorted_ports = sorted(all_ports)

    if optimize_maps and len(sorted_ports) >= 2:
        in_elems: List[str] = []
        out_elems: List[str] = []
        for p in sorted_ports:
            vmap_chains.append(f"    chain c_in_{p} {{ counter name cnt_in_{p}; }}")
            vmap_chains.append(f"    chain c_out_{p} {{ counter name cnt_out_{p}; }}")
            in_elems.append(f"{p} : jump c_in_{p}")
            out_elems.append(f"{p} : jump c_out_{p}")
        vmap_defs.append(_format_nft_map_block("vmap_in", "inet_service", "verdict", in_elems))
        vmap_defs.append(_format_nft_map_block("vmap_out", "inet_service", "verdict", out_elems))
        forward_lines.extend([
            "        tcp dport vmap @vmap_in",
            "        udp dport vmap @vmap_in",
            "        tcp sport vmap @vmap_out",
            "        udp sport vmap @vmap_out",
        ])
    else:
        for p in sorted_ports:
            forward_lines.append(f"        tcp dport {p} counter name cnt_in_{p}")
            forward_lines.append(f"        tcp sport {p} counter name cnt_out_{p}")
            forward_lines.append(f"        udp dport {p} counter name cnt_in_{p}")
            forward_lines.append(f"        udp sport {p} counter name cnt_out_{p}")

    for pr in sorted(all_ranges):
        cname = pr.replace("-", "_")
        forward_lines.append(f"        tcp dport {pr} counter name cnt_in_{cname}")
        forward_lines.append(f"        tcp sport {pr} counter name cnt_out_{cname}")
        forward_lines.append(f"        udp dport {pr} counter name cnt_in_{cname}")
        forward_lines.append(f"        udp sport {pr} counter name cnt_out_{cname}")

    for proto_e, expr_e in excl_counters:
        forward_lines.append(f"        {proto_e} dport {expr_e} ct status dnat counter name cnt_in_1_excl")
        if has_untracked:
            forward_lines.append(f"        {proto_e} dport {expr_e} ct state untracked counter name cnt_in_1_excl")
        forward_lines.append(f"        {proto_e} sport {expr_e} counter name cnt_out_1_excl")

    return vmap_defs, vmap_chains, forward_lines


def _build_family_table(
    family: str,
    dnat_rules: List[str],
    raw_rules: List[str],
    snat_rules: List[str],
    mss_rules: List[str],
    extra_chains: List[str],
    counter_defs_str: str,
    all_ports: Set[int],
    all_ranges: Set[str],
    excl_counters: List[Tuple[str, str]],
    base_postrouting: str,
    has_untracked: bool,
    optimize_maps: bool,
    input_rules: Optional[List[str]] = None,
    raw_output_rules: Optional[List[str]] = None,
    route_output_rules: Optional[List[str]] = None,
    raw_postrouting_rules: Optional[List[str]] = None,
    extra_forward_rules: Optional[List[str]] = None
) -> str:
    """Renders an isolated table ip/ip6 xfwd_orchestrator block."""
    if family == "ip6" and not (
        dnat_rules or raw_rules or snat_rules or mss_rules or extra_chains
        or input_rules or raw_output_rules or route_output_rules or raw_postrouting_rules or extra_forward_rules
    ):
        # Emit counter declarations only (zero active Netfilter hooks when IPv6 is unused)
        body = counter_defs_str.rstrip()
        inner = f"\n{body}\n" if body else "\n"
        return (
            f"table ip6 xfwd_orchestrator\n"
            f"delete table ip6 xfwd_orchestrator\n\n"
            f"table ip6 xfwd_orchestrator {{{inner}}}"
        )

    raw_defs, opt_raw_rules = _optimize_raw_rules(raw_rules, family, optimize_maps=optimize_maps)
    dnat_defs, opt_dnat_rules = _optimize_dnat_rules(dnat_rules, family, optimize_maps=optimize_maps)
    vmap_defs, vmap_chains, forward_counter_lines = _build_forward_counter_vmaps(
        all_ports, all_ranges, excl_counters, has_untracked=has_untracked, optimize_maps=optimize_maps
    )

    decl_blocks: List[str] = []
    if counter_defs_str.strip():
        decl_blocks.append(counter_defs_str.strip("\n"))
    if raw_defs:
        decl_blocks.append("\n\n".join(raw_defs))
    if dnat_defs:
        decl_blocks.append("\n\n".join(dnat_defs))
    if vmap_defs:
        decl_blocks.append("\n\n".join(vmap_defs))
    if extra_chains:
        decl_blocks.append("\n\n".join(extra_chains))
    if vmap_chains:
        decl_blocks.append("\n".join(vmap_chains))

    syn_mss_chain = ""
    if mss_rules and optimize_maps:
        stripped_mss = [re.sub(r"^\s*tcp\s+flags\s+syn\s+", "        ", r) for r in mss_rules]
        syn_mss_chain = (
            "    chain syn_mss {\n"
            "        tcp option maxseg size set rt mtu\n"
            + "\n".join(stripped_mss)
            + "\n    }"
        )
        decl_blocks.append(syn_mss_chain)
        forward_mss_line = "        tcp flags & (syn|rst) == syn jump syn_mss"
    else:
        mss_lines = ["        tcp flags syn tcp option maxseg size set rt mtu"] + list(mss_rules)
        forward_mss_line = "\n".join(mss_lines)

    if opt_raw_rules:
        decl_blocks.append(
            "    chain raw_prerouting {\n"
            "        type filter hook prerouting priority raw; policy accept;\n"
            + "\n".join(opt_raw_rules)
            + "\n    }"
        )

    if input_rules:
        decl_blocks.append(
            "    chain dsr_input {\n"
            "        type filter hook input priority -20; policy accept;\n"
            + "\n".join(input_rules)
            + "\n    }"
        )

    if raw_output_rules:
        decl_blocks.append(
            "    chain raw_output {\n"
            "        type filter hook output priority raw; policy accept;\n"
            + "\n".join(raw_output_rules)
            + "\n    }"
        )

    if route_output_rules:
        decl_blocks.append(
            "    chain dsr_route_output {\n"
            "        type route hook output priority -149; policy accept;\n"
            + "\n".join(route_output_rules)
            + "\n    }"
        )

    if raw_postrouting_rules:
        decl_blocks.append(
            "    chain dsr_postrouting {\n"
            "        type filter hook postrouting priority 300; policy accept;\n"
            + "\n".join(raw_postrouting_rules)
            + "\n    }"
        )

    no_dnat_comment = f"        # No active NFTables {'IPv6' if family == 'ip6' else 'IPv4'} DNAT rules"
    dnat_block = "\n".join(opt_dnat_rules) if opt_dnat_rules else no_dnat_comment
    postrouting_block = ("\n".join(snat_rules) + "\n" + base_postrouting) if snat_rules else base_postrouting
    combined_forward_lines = list(forward_counter_lines) + list(extra_forward_rules or [])
    forward_counters_str = "\n".join(combined_forward_lines) + "\n" if combined_forward_lines else ""
    pmtu_line = (
        ("        icmpv6 type packet-too-big accept\n" if family == "ip6" else "        icmp type destination-unreachable accept\n")
        if has_untracked else ""
    )
    ct_accept_line = (
        "        ct state { established, related, untracked } accept"
        if has_untracked else "        ct state { established, related } accept"
    )

    decl_prefix = ("\n\n".join(decl_blocks) + "\n\n") if decl_blocks else ""
    return (
        f"table {family} xfwd_orchestrator\n"
        f"delete table {family} xfwd_orchestrator\n\n"
        f"table {family} xfwd_orchestrator {{\n"
        f"{decl_prefix}    chain prerouting {{\n"
        f"        type nat hook prerouting priority dstnat; policy accept;\n"
        f"{dnat_block}\n"
        f"    }}\n\n"
        f"    chain postrouting {{\n"
        f"        type nat hook postrouting priority srcnat; policy accept;\n"
        f"{postrouting_block}\n"
        f"    }}\n\n"
        f"    chain forward {{\n"
        f"        type filter hook forward priority filter; policy accept;\n"
        f"        # Automatically clamp TCP MSS to path MTU to prevent packet loss in GRE/IPIP tunnels\n"
        f"{forward_mss_line}\n"
        f"{forward_counters_str}{pmtu_line}        ct status dnat accept\n"
        f"{ct_accept_line}\n"
        f"    }}\n"
        f"}}"
    )


def _split_rules_by_family(rules: Optional[List[str]], v6_marker: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Splits NFTables statements into (ipv4_list, ipv6_list)."""
    v4: List[str] = []
    v6: List[str] = []
    for r in (rules or []):
        if (v6_marker and v6_marker in r) or _is_ipv6_nft_statement(r):
            v6.append(r)
        else:
            v4.append(r)
    return v4, v6


def generate_nftables_ruleset(
    dnat_rules: List[str],
    rule_ports: Optional[Set[int]] = None,
    enable_ipv6: Optional[bool] = None,
    rule_ranges: Optional[Set[str]] = None,
    custom_oifs: Optional[Set[str]] = None,
    raw_rules: Optional[List[str]] = None,
    snat_rules: Optional[List[str]] = None,
    dsr_mss_rules: Optional[List[str]] = None,
    has_untracked: bool = False,
    extra_chains: Optional[List[str]] = None,
    optimize_maps: bool = True,
    input_rules: Optional[List[str]] = None,
    raw_output_rules: Optional[List[str]] = None,
    route_output_rules: Optional[List[str]] = None,
    raw_postrouting_rules: Optional[List[str]] = None,
    extra_forward_rules: Optional[List[str]] = None
) -> str:
    """Generates a complete, isolated NFTables ruleset string (O(1) maps/vmaps, syn_mss, DSR stateless/relay/synack/direct, single ports & ranges)."""
    if enable_ipv6 is None:
        enable_ipv6 = is_ipv6_supported()

    ipv4_rules, ipv6_rules = _split_rules_by_family(dnat_rules)
    ipv4_extra_chains, ipv6_extra_chains = _split_rules_by_family(extra_chains)
    ipv4_raw_rules, ipv6_raw_rules = _split_rules_by_family(raw_rules, "ip6 daddr")
    ipv4_snat_rules, ipv6_snat_rules = _split_rules_by_family(snat_rules, "ip6 daddr")
    ipv4_input_rules, ipv6_input_rules = _split_rules_by_family(input_rules, "ip6 ")
    ipv4_raw_output_rules, ipv6_raw_output_rules = _split_rules_by_family(raw_output_rules, "ip6 ")
    ipv4_route_output_rules, ipv6_route_output_rules = _split_rules_by_family(route_output_rules, "ip6 ")
    ipv4_raw_postrouting_rules, ipv6_raw_postrouting_rules = _split_rules_by_family(raw_postrouting_rules, "ip6 ")
    ipv4_extra_forward_rules, ipv6_extra_forward_rules = _split_rules_by_family(extra_forward_rules, "ip6 ")

    all_ports = set(rule_ports or [])
    all_ranges = set(rule_ranges or [])
    excl_counters: List[Tuple[str, str]] = []
    seen_excl: Set[Tuple[str, str]] = set()
    for r in list(dnat_rules) + list(raw_rules or []):
        m_excl = re.search(r"\b(tcp|udp)\s+dport\s+(!=\s*(?:\{\s*[^}]+\s*\}|\d+))", r)
        if m_excl:
            proto_e, expr_e = m_excl.group(1), m_excl.group(2)
            if (proto_e, expr_e) not in seen_excl:
                seen_excl.add((proto_e, expr_e))
                excl_counters.append((proto_e, expr_e))
            continue
        m = re.search(r"dport\s+(\d+)(?:-(\d+))?", r)
        if m:
            try:
                sp = int(m.group(1))
                if m.group(2):
                    ep = int(m.group(2))
                    if 1 <= sp < ep <= 65535:
                        all_ranges.add(f"{sp}-{ep}")
                    elif 1 <= sp <= 65535:
                        all_ports.add(sp)
                elif 1 <= sp <= 65535:
                    all_ports.add(sp)
            except ValueError:
                pass

    counter_defs: List[str] = []
    for p in sorted(list(all_ports)):
        counter_defs.append(f"    counter cnt_in_{p} {{ }}")
        counter_defs.append(f"    counter cnt_out_{p} {{ }}")
    for pr in sorted(list(all_ranges)):
        cname = pr.replace("-", "_")
        counter_defs.append(f"    counter cnt_in_{cname} {{ }}")
        counter_defs.append(f"    counter cnt_out_{cname} {{ }}")
    if excl_counters:
        counter_defs.append("    counter cnt_in_1_excl { }")
        counter_defs.append("    counter cnt_out_1_excl { }")

    counter_defs_str = "\n".join(counter_defs) + "\n\n" if counter_defs else ""

    ipv4_mss_rules = [r for r in (dsr_mss_rules or []) if "ip6 daddr" not in r]
    ipv6_mss_rules = [r for r in (dsr_mss_rules or []) if "ip6 daddr" in r]
    base_postrouting = _format_postrouting_masquerades(custom_oifs)

    tables_content = [
        _build_family_table(
            family="ip",
            dnat_rules=ipv4_rules,
            raw_rules=ipv4_raw_rules,
            snat_rules=ipv4_snat_rules,
            mss_rules=ipv4_mss_rules,
            extra_chains=ipv4_extra_chains,
            counter_defs_str=counter_defs_str,
            all_ports=all_ports,
            all_ranges=all_ranges,
            excl_counters=excl_counters,
            base_postrouting=base_postrouting,
            has_untracked=has_untracked,
            optimize_maps=optimize_maps,
            input_rules=ipv4_input_rules,
            raw_output_rules=ipv4_raw_output_rules,
            route_output_rules=ipv4_route_output_rules,
            raw_postrouting_rules=ipv4_raw_postrouting_rules,
            extra_forward_rules=ipv4_extra_forward_rules,
        )
    ]

    if enable_ipv6:
        tables_content.append(
            _build_family_table(
                family="ip6",
                dnat_rules=ipv6_rules,
                raw_rules=ipv6_raw_rules,
                snat_rules=ipv6_snat_rules,
                mss_rules=ipv6_mss_rules,
                extra_chains=ipv6_extra_chains,
                counter_defs_str=counter_defs_str,
                all_ports=all_ports,
                all_ranges=all_ranges,
                excl_counters=excl_counters,
                base_postrouting=base_postrouting,
                has_untracked=has_untracked,
                optimize_maps=optimize_maps,
                input_rules=ipv6_input_rules,
                raw_output_rules=ipv6_raw_output_rules,
                route_output_rules=ipv6_route_output_rules,
                raw_postrouting_rules=ipv6_raw_postrouting_rules,
                extra_forward_rules=ipv6_extra_forward_rules,
            )
        )

    return "#!/usr/sbin/nft -f\n# Generated by XForwarder Core Engine\n" + "\n\n".join(tables_content) + "\n"


def apply_nftables(
    dnat_rules: List[str],
    rule_ports: Optional[Set[int]] = None,
    last_content: Optional[str] = None,
    rule_ranges: Optional[Set[str]] = None,
    custom_oifs: Optional[Set[str]] = None,
    raw_rules: Optional[List[str]] = None,
    snat_rules: Optional[List[str]] = None,
    dsr_mss_rules: Optional[List[str]] = None,
    has_untracked: bool = False,
    dsr_ifaces: Optional[Set[str]] = None,
    extra_chains: Optional[List[str]] = None,
    input_rules: Optional[List[str]] = None,
    raw_output_rules: Optional[List[str]] = None,
    route_output_rules: Optional[List[str]] = None,
    raw_postrouting_rules: Optional[List[str]] = None,
    extra_forward_rules: Optional[List[str]] = None,
    dsr_direct_routes: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates and atomically applies NFTables ruleset.
    Falls back automatically to linear ruleset generation if `nft -c -f` fails on legacy kernels.
    Returns (success: bool, error_msg: Optional[str], new_content: Optional[str]).
    """
    global _DSR_SYSCTL_APPLIED, _DSR_DIRECT_POLICY_APPLIED, _NFT_MAPS_SUPPORTED
    use_opt = (_NFT_MAPS_SUPPORTED is not False)
    has_any_dsr = bool(raw_rules or raw_output_rules or route_output_rules or raw_postrouting_rules)
    gen_kwargs: Dict[str, Any] = {
        "rule_ports": rule_ports,
        "rule_ranges": rule_ranges,
        "custom_oifs": custom_oifs,
        "raw_rules": raw_rules,
        "snat_rules": snat_rules,
        "dsr_mss_rules": dsr_mss_rules,
        "has_untracked": has_untracked,
        "extra_chains": extra_chains,
        "input_rules": input_rules,
        "raw_output_rules": raw_output_rules,
        "route_output_rules": route_output_rules,
        "raw_postrouting_rules": raw_postrouting_rules,
        "extra_forward_rules": extra_forward_rules,
    }
    nft_content = generate_nftables_ruleset(dnat_rules, optimize_maps=use_opt, **gen_kwargs)

    if not shutil.which("nft"):
        return True, None, nft_content

    if last_content and last_content == nft_content:
        if has_any_dsr and not _DSR_SYSCTL_APPLIED:
            ensure_dsr_sysctl(dsr_ifaces)
            _DSR_SYSCTL_APPLIED = True
        if dsr_direct_routes and not _DSR_DIRECT_POLICY_APPLIED:
            ok_pr, err_pr = ensure_dsr_direct_policy_routing(dsr_direct_routes)
            if not ok_pr:
                return False, err_pr, last_content
        elif dsr_direct_routes and _DSR_DIRECT_POLICY_APPLIED:
            reconcile_dsr_direct_kernel_routes()
        elif not dsr_direct_routes and (_DSR_DIRECT_POLICY_APPLIED or os.path.isfile(DSR_DIRECT_STATE_PATH)):
            cleanup_dsr_direct_policy_routing()
        return True, None, nft_content

    try:
        # Clean up legacy tables if exist
        subprocess.run(["nft", "delete", "table", "ip", "fwdman_orchestrator"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["nft", "delete", "table", "ip6", "fwdman_orchestrator"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        proc = subprocess.Popen(["nft", "-c", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(input=nft_content)
        if proc.returncode != 0 and use_opt:
            linear_content = generate_nftables_ruleset(dnat_rules, optimize_maps=False, **gen_kwargs)
            if linear_content != nft_content:
                lin_proc = subprocess.Popen(["nft", "-c", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                _, lin_err = lin_proc.communicate(input=linear_content)
                if lin_proc.returncode == 0:
                    _NFT_MAPS_SUPPORTED = False
                    nft_content = linear_content
                    proc = lin_proc
                    err = lin_err
        if proc.returncode == 0:
            if has_any_dsr:
                ensure_dsr_sysctl(dsr_ifaces)
                _DSR_SYSCTL_APPLIED = True
            elif _DSR_SYSCTL_APPLIED or os.path.isfile(DSR_SYSCTL_CONF_PATH):
                cleanup_dsr_sysctl()
                _DSR_SYSCTL_APPLIED = False
            if dsr_direct_routes:
                ok_pr, err_pr = ensure_dsr_direct_policy_routing(dsr_direct_routes)
                if not ok_pr:
                    print(f"[WARN] DSR Direct policy routing failed: {err_pr}", file=sys.stderr)
                    return False, err_pr, last_content
            apply_proc = subprocess.Popen(["nft", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, apply_err = apply_proc.communicate(input=nft_content)
            if apply_proc.returncode != 0:
                err_msg = apply_err.strip() if apply_err else "Failed applying nftables ruleset"
                print(f"[WARN] NFTables apply failed: {err_msg}", file=sys.stderr)
                return False, f"NFTables apply: {err_msg}", last_content
            if not dsr_direct_routes and (_DSR_DIRECT_POLICY_APPLIED or os.path.isfile(DSR_DIRECT_STATE_PATH)):
                cleanup_dsr_direct_policy_routing()
            return True, None, nft_content
        else:
            err_msg = err.strip() if err else "NFTables validation check failed"
            print(f"[WARN] NFTables check failed: {err_msg}", file=sys.stderr)
            return False, f"NFTables syntax: {err_msg}", last_content
    except Exception as ex:
        return False, f"NFTables error: {str(ex)}", last_content

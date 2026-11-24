#!/usr/bin/env python3
"""
XForwarder - Kernel Firewall & NFTables Orchestrator
Generates isolated NFTables rulesets for table ip/ip6 xfwd_orchestrator,
validates syntax dry-runs, and clears connection tracking states.
"""

import os
import sys
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


def _find_conntrack_bin() -> Optional[str]:
    """Locate the conntrack binary even when systemd restricts PATH."""
    found = shutil.which("conntrack")
    if found:
        return found
    for candidate in ("/usr/sbin/conntrack", "/sbin/conntrack", "/usr/bin/conntrack"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


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
        '        oifname "backhaul*" masquerade',
    ]
    for iface in sorted(custom_oifs or set()):
        clean_iface = str(iface or "").strip()
        if IFACE_NAME_REGEX.match(clean_iface):
            lines.append(f'        oifname "{clean_iface}" masquerade')
    return "\n".join(lines)


DSR_SYSCTL_CONF_PATH = "/etc/sysctl.d/99-xforwarder-dsr.conf"
_DSR_SYSCTL_APPLIED = False


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
    sysctl_conf_path: str = DSR_SYSCTL_CONF_PATH
) -> None:
    """
    Ensures Linux kernel IP forwarding and rp_filter=0 are configured and persisted for asymmetric DSR routing.
    Required so packets arriving on tunnel interfaces with un-NATted client IPs are not dropped on reboot or tune.
    """
    if sys.platform == "win32":
        return

    settings = [
        "net.ipv4.ip_forward=1",
        "net.ipv4.conf.all.rp_filter=0",
        "net.ipv4.conf.default.rp_filter=0",
    ]
    for iface in sorted(ifaces or set()):
        clean_if = str(iface or "").strip()
        if IFACE_NAME_REGEX.match(clean_if):
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

    sysctl_bin = shutil.which("sysctl")
    if not sysctl_bin:
        for candidate in ("/sbin/sysctl", "/usr/sbin/sysctl", "/bin/sysctl"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                sysctl_bin = candidate
                break
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
    extra_chains: Optional[List[str]] = None
) -> str:
    """Generates a complete, isolated NFTables ruleset string (DNAT, LB maps/vmaps, DSR stateless/relay, single ports & ranges)."""
    if enable_ipv6 is None:
        enable_ipv6 = is_ipv6_supported()

    ipv4_rules = []
    ipv6_rules = []
    for r in dnat_rules:
        if _is_ipv6_nft_statement(r):
            ipv6_rules.append(r)
        else:
            ipv4_rules.append(r)

    ipv4_extra_chains = []
    ipv6_extra_chains = []
    for ch in (extra_chains or []):
        if _is_ipv6_nft_statement(ch):
            ipv6_extra_chains.append(ch)
        else:
            ipv4_extra_chains.append(ch)

    ipv4_raw_rules = []
    ipv6_raw_rules = []
    for r in (raw_rules or []):
        if "ip6 daddr" in r:
            ipv6_raw_rules.append(r)
        else:
            ipv4_raw_rules.append(r)

    ipv4_snat_rules = []
    ipv6_snat_rules = []
    for r in (snat_rules or []):
        if "ip6 daddr" in r or "snat to [" in r:
            ipv6_snat_rules.append(r)
        else:
            ipv4_snat_rules.append(r)

    ipv4_block = "\n".join(ipv4_rules) if ipv4_rules else "        # No active NFTables IPv4 DNAT rules"

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
                    if sp < ep:
                        all_ranges.add(f"{sp}-{ep}")
                    else:
                        all_ports.add(sp)
                else:
                    all_ports.add(sp)
            except ValueError:
                pass

    counter_defs = []
    forward_counters = []
    for p in sorted(list(all_ports)):
        counter_defs.append(f"    counter cnt_in_{p} {{ }}")
        counter_defs.append(f"    counter cnt_out_{p} {{ }}")
        forward_counters.append(f"        tcp dport {p} counter name cnt_in_{p}")
        forward_counters.append(f"        tcp sport {p} counter name cnt_out_{p}")
        forward_counters.append(f"        udp dport {p} counter name cnt_in_{p}")
        forward_counters.append(f"        udp sport {p} counter name cnt_out_{p}")

    for pr in sorted(list(all_ranges)):
        cname = pr.replace("-", "_")
        counter_defs.append(f"    counter cnt_in_{cname} {{ }}")
        counter_defs.append(f"    counter cnt_out_{cname} {{ }}")
        forward_counters.append(f"        tcp dport {pr} counter name cnt_in_{cname}")
        forward_counters.append(f"        tcp sport {pr} counter name cnt_out_{cname}")
        forward_counters.append(f"        udp dport {pr} counter name cnt_in_{cname}")
        forward_counters.append(f"        udp sport {pr} counter name cnt_out_{cname}")

    if excl_counters:
        counter_defs.append("    counter cnt_in_1_excl { }")
        counter_defs.append("    counter cnt_out_1_excl { }")
        for proto_e, expr_e in excl_counters:
            forward_counters.append(f"        {proto_e} dport {expr_e} ct status dnat counter name cnt_in_1_excl")
            if has_untracked:
                forward_counters.append(f"        {proto_e} dport {expr_e} ct state untracked counter name cnt_in_1_excl")
            forward_counters.append(f"        {proto_e} sport {expr_e} counter name cnt_out_1_excl")

    counter_defs_str = "\n".join(counter_defs) + "\n\n" if counter_defs else ""
    forward_counters_str = "\n".join(forward_counters) + "\n" if forward_counters else ""

    ipv4_mss_rules = [r for r in (dsr_mss_rules or []) if "ip6 daddr" not in r]
    ipv6_mss_rules = [r for r in (dsr_mss_rules or []) if "ip6 daddr" in r]
    ipv4_mss_str = ("\n" + "\n".join(ipv4_mss_rules)) if ipv4_mss_rules else ""
    ipv6_mss_str = ("\n" + "\n".join(ipv6_mss_rules)) if ipv6_mss_rules else ""
    ct_accept_line = "        ct state { established, related, untracked } accept" if has_untracked else "        ct state { established, related } accept"
    ipv4_pmtu_line = "        icmp type destination-unreachable accept\n" if has_untracked else ""
    ipv6_pmtu_line = "        icmpv6 type packet-too-big accept\n" if has_untracked else ""

    base_postrouting = _format_postrouting_masquerades(custom_oifs)
    ipv4_postrouting = ("\n".join(ipv4_snat_rules) + "\n" + base_postrouting) if ipv4_snat_rules else base_postrouting
    ipv4_extra_block = ("\n\n".join(ipv4_extra_chains) + "\n\n") if ipv4_extra_chains else ""
    ipv4_raw_chain = (
        f"    chain raw_prerouting {{\n"
        f"        type filter hook prerouting priority raw; policy accept;\n"
        f"{chr(10).join(ipv4_raw_rules)}\n"
        f"    }}\n\n"
    ) if ipv4_raw_rules else ""

    tables_content = [
        f"""table ip xfwd_orchestrator
delete table ip xfwd_orchestrator

table ip xfwd_orchestrator {{
{counter_defs_str}{ipv4_extra_block}{ipv4_raw_chain}    chain prerouting {{
        type nat hook prerouting priority dstnat; policy accept;
{ipv4_block}
    }}

    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
{ipv4_postrouting}
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
        # Automatically clamp TCP MSS to path MTU to prevent packet loss in GRE/IPIP tunnels
        tcp flags syn tcp option maxseg size set rt mtu{ipv4_mss_str}
{forward_counters_str}{ipv4_pmtu_line}        ct status dnat accept
{ct_accept_line}
    }}
}}"""
    ]

    if enable_ipv6:
        ipv6_block = "\n".join(ipv6_rules) if ipv6_rules else "        # No active NFTables IPv6 DNAT rules"
        ipv6_postrouting = ("\n".join(ipv6_snat_rules) + "\n" + base_postrouting) if ipv6_snat_rules else base_postrouting
        ipv6_extra_block = ("\n\n".join(ipv6_extra_chains) + "\n\n") if ipv6_extra_chains else ""
        ipv6_raw_chain = (
            f"    chain raw_prerouting {{\n"
            f"        type filter hook prerouting priority raw; policy accept;\n"
            f"{chr(10).join(ipv6_raw_rules)}\n"
            f"    }}\n\n"
        ) if ipv6_raw_rules else ""
        tables_content.append(
            f"""table ip6 xfwd_orchestrator
delete table ip6 xfwd_orchestrator

table ip6 xfwd_orchestrator {{
{counter_defs_str}{ipv6_extra_block}{ipv6_raw_chain}    chain prerouting {{
        type nat hook prerouting priority dstnat; policy accept;
{ipv6_block}
    }}

    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
{ipv6_postrouting}
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
        # Automatically clamp TCP MSS to path MTU to prevent packet loss in GRE/IPIP tunnels
        tcp flags syn tcp option maxseg size set rt mtu{ipv6_mss_str}
{forward_counters_str}{ipv6_pmtu_line}        ct status dnat accept
{ct_accept_line}
    }}
}}"""
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
    extra_chains: Optional[List[str]] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates and atomically applies NFTables ruleset.
    Returns (success: bool, error_msg: Optional[str], new_content: Optional[str]).
    """
    nft_content = generate_nftables_ruleset(
        dnat_rules,
        rule_ports=rule_ports,
        rule_ranges=rule_ranges,
        custom_oifs=custom_oifs,
        raw_rules=raw_rules,
        snat_rules=snat_rules,
        dsr_mss_rules=dsr_mss_rules,
        has_untracked=has_untracked,
        extra_chains=extra_chains
    )

    global _DSR_SYSCTL_APPLIED
    if not shutil.which("nft"):
        return True, None, nft_content

    if last_content and last_content == nft_content:
        if raw_rules and not _DSR_SYSCTL_APPLIED:
            ensure_dsr_sysctl(dsr_ifaces)
            _DSR_SYSCTL_APPLIED = True
        return True, None, nft_content

    try:
        # Clean up legacy tables if exist
        subprocess.run(["nft", "delete", "table", "ip", "fwdman_orchestrator"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["nft", "delete", "table", "ip6", "fwdman_orchestrator"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        proc = subprocess.Popen(["nft", "-c", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(input=nft_content)
        if proc.returncode == 0:
            if raw_rules:
                ensure_dsr_sysctl(dsr_ifaces)
                _DSR_SYSCTL_APPLIED = True
            elif _DSR_SYSCTL_APPLIED or os.path.isfile(DSR_SYSCTL_CONF_PATH):
                cleanup_dsr_sysctl()
                _DSR_SYSCTL_APPLIED = False
            apply_proc = subprocess.Popen(["nft", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, apply_err = apply_proc.communicate(input=nft_content)
            if apply_proc.returncode != 0:
                err_msg = apply_err.strip() if apply_err else "Failed applying nftables ruleset"
                print(f"[WARN] NFTables apply failed: {err_msg}", file=sys.stderr)
                return False, f"NFTables apply: {err_msg}", last_content
            return True, None, nft_content
        else:
            err_msg = err.strip() if err else "NFTables validation check failed"
            print(f"[WARN] NFTables check failed: {err_msg}", file=sys.stderr)
            return False, f"NFTables syntax: {err_msg}", last_content
    except Exception as ex:
        return False, f"NFTables error: {str(ex)}", last_content

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
from typing import Dict, Any, Tuple, Optional, List, Set


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


def flush_conntrack(port: Any, proto: Optional[str] = None) -> None:
    """Flushes stale conntrack states for TCP and UDP on a validated port or tiny range."""
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
    protos = [proto] if proto in ("tcp", "udp") else ["tcp", "udp"]
    for port_int in ports_to_flush:
        for p in protos:
            try:
                subprocess.run(
                    [conntrack_bin, "-D", "-p", p, "--dport", str(port_int)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5.0,
                    check=False
                )
            except Exception:
                pass


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


def ensure_dsr_sysctl(ifaces: Optional[Set[str]] = None) -> None:
    """
    Ensures Linux kernel IP forwarding and rp_filter=0 are configured for asymmetric DSR routing.
    Required so packets arriving on tunnel interfaces with un-NATted client IPs are not dropped.
    """
    if sys.platform == "win32":
        return
    sysctl_bin = shutil.which("sysctl")
    if not sysctl_bin:
        for candidate in ("/sbin/sysctl", "/usr/sbin/sysctl", "/bin/sysctl"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                sysctl_bin = candidate
                break
    if not sysctl_bin:
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


def generate_nftables_ruleset(
    dnat_rules: List[str],
    rule_ports: Optional[Set[int]] = None,
    enable_ipv6: Optional[bool] = None,
    rule_ranges: Optional[Set[str]] = None,
    custom_oifs: Optional[Set[str]] = None,
    raw_rules: Optional[List[str]] = None,
    snat_rules: Optional[List[str]] = None,
    dsr_mss_rules: Optional[List[str]] = None,
    has_untracked: bool = False
) -> str:
    """Generates a complete, isolated NFTables ruleset string (DNAT, DSR stateless/relay, single ports & ranges)."""
    if enable_ipv6 is None:
        enable_ipv6 = is_ipv6_supported()

    ipv4_rules = []
    ipv6_rules = []
    for r in dnat_rules:
        if "dnat to [" in r or "]:" in r or "ip6 daddr" in r:
            ipv6_rules.append(r)
        else:
            ipv4_rules.append(r)

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

    base_postrouting = _format_postrouting_masquerades(custom_oifs)
    ipv4_postrouting = ("\n".join(ipv4_snat_rules) + "\n" + base_postrouting) if ipv4_snat_rules else base_postrouting
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
{counter_defs_str}{ipv4_raw_chain}    chain prerouting {{
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
{forward_counters_str}        ct status dnat accept
{ct_accept_line}
    }}
}}"""
    ]

    if enable_ipv6:
        ipv6_block = "\n".join(ipv6_rules) if ipv6_rules else "        # No active NFTables IPv6 DNAT rules"
        ipv6_postrouting = ("\n".join(ipv6_snat_rules) + "\n" + base_postrouting) if ipv6_snat_rules else base_postrouting
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
{counter_defs_str}{ipv6_raw_chain}    chain prerouting {{
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
{forward_counters_str}        ct status dnat accept
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
    dsr_ifaces: Optional[Set[str]] = None
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
        has_untracked=has_untracked
    )

    if not shutil.which("nft"):
        return True, None, nft_content

    if last_content and last_content == nft_content:
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

#!/usr/bin/env python3
"""
XForwarder - Kernel & Network Performance Optimizer
Adaptive BBR, fq qdisc, conntrack scaling, MTU probing, and ESP/DSR-safe rp_filter=0 tuning.
Supports both incremental optimization and clean backup-first reset of legacy/conflicting configs.
Native Python Standard Library only.
"""

import os
import sys
import re
import json
import time
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    from core.firewall import _find_system_bin, ensure_fq_qdisc, IFACE_NAME_REGEX, DSR_SYSCTL_CONF_PATH
except ImportError:
    from firewall import _find_system_bin, ensure_fq_qdisc, IFACE_NAME_REGEX, DSR_SYSCTL_CONF_PATH


XFW_SYSCTL_CONF_PATH = "/etc/sysctl.d/99-xforwarder.conf"
SYSCTL_CONF_PATH = "/etc/sysctl.conf"
SYSCTL_D_DIR = "/etc/sysctl.d"
ETC_MODULES_PATH = "/etc/modules"
MODULES_LOAD_DIR = "/etc/modules-load.d"
HAPROXY_OVERRIDE_PATH = "/etc/systemd/system/haproxy.service.d/override.conf"
DEFAULT_BACKUP_DIR = "/etc/xforwarder/backups"

# Distro-owned sysctl drop-ins that must never be deleted during reset
_DISTRO_SYSCTL_PREFIXES = ("10-", "30-", "50-", "99-cloudimg", "99-sysctl", "README")
_MANAGED_CONFLICT_KEYS = (
    "net.ipv4.conf.all.rp_filter",
    "net.ipv4.conf.default.rp_filter",
    "net.ipv4.tcp_congestion_control",
    "net.core.default_qdisc",
    "net.ipv4.ip_forward",
    "net.netfilter.nf_conntrack_max",
    "net.netfilter.nf_conntrack_buckets",
    "net.core.rmem_max",
    "net.core.wmem_max",
    "vm.min_free_kbytes",
)


def _atomic_write_text(path: str, content: str) -> None:
    """Writes text file atomically using temporary file + os.replace."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = f"{path}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp_path, path)


def _read_text_safe(path: str) -> Optional[str]:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def _read_sysctl_proc(key: str, proc_sys_root: str = "/proc/sys") -> Optional[str]:
    rel = key.replace(".", "/")
    return _read_text_safe(os.path.join(proc_sys_root, rel))


def _proc_sysctl_exists(key: str, proc_sys_root: str = "/proc/sys") -> bool:
    rel = key.replace(".", "/")
    return os.path.exists(os.path.join(proc_sys_root, rel))


def detect_system_capacity(meminfo_path: str = "/proc/meminfo") -> Tuple[int, int]:
    """Returns `(mem_mb, cpu_cores)` using /proc/meminfo with safe fallbacks."""
    mem_mb = 1024
    raw = _read_text_safe(meminfo_path)
    if raw:
        m = re.search(r"MemTotal:\s+(\d+)\s+kB", raw)
        if m:
            try:
                mem_mb = max(128, int(round(int(m.group(1)) / 1024.0)))
            except Exception:
                pass
    cores = max(1, int(os.cpu_count() or 1))
    return mem_mb, cores


def compute_tuning_profile(mem_mb: int, cpu_cores: int) -> Dict[str, Any]:
    """
    Computes adaptive kernel tuning parameters scaled by host RAM tier.
    Prevents 8GB defaults (32-64MB buffers, 1M conntrack, 128MB min_free_kbytes) from causing OOM on 1GB VPSes.
    """
    if mem_mb < 1000:
        tier = "tier1_low"
        tier_label = "Small VPS (<1 GB RAM)"
        maxconn = 15000
        rmem_def = 131072
        rmem_max = 16777216       # 16 MB
        conntrack_max = 131072
        somaxconn = 32768
        syn_backlog = 8192
        tw_buckets = 262144
        min_free_kbytes = 32768   # 32 MB
    elif mem_mb < 2500:
        tier = "tier2_medium"
        tier_label = "Medium VPS (1-2.5 GB RAM)"
        maxconn = 35000
        rmem_def = 262144
        rmem_max = 33554432       # 32 MB
        conntrack_max = 262144
        somaxconn = 65535
        syn_backlog = 16384
        tw_buckets = 524288
        min_free_kbytes = 65536   # 64 MB
    elif mem_mb < 4500:
        tier = "tier3_large"
        tier_label = "Large VPS (2.5-4.5 GB RAM)"
        maxconn = 75000
        rmem_def = 262144
        rmem_max = 67108864       # 64 MB
        conntrack_max = 524288
        somaxconn = 65535
        syn_backlog = 32768
        tw_buckets = 1000000
        min_free_kbytes = 65536   # 64 MB
    else:
        tier = "tier4_high"
        tier_label = "High-Spec VPS (>=4.5 GB RAM)"
        maxconn = 150000
        rmem_def = 262144
        rmem_max = 67108864       # 64 MB
        conntrack_max = 1048576
        somaxconn = 65535
        syn_backlog = 32768
        tw_buckets = 1000000
        min_free_kbytes = 131072  # 128 MB

    return {
        "mem_mb": mem_mb,
        "cpu_cores": cpu_cores,
        "tier": tier,
        "tier_label": tier_label,
        "haproxy_maxconn": maxconn,
        "rmem_def": rmem_def,
        "wmem_def": rmem_def,
        "rmem_max": rmem_max,
        "wmem_max": rmem_max,
        "conntrack_max": conntrack_max,
        "conntrack_buckets": conntrack_max // 4,
        "somaxconn": somaxconn,
        "syn_backlog": syn_backlog,
        "tw_buckets": tw_buckets,
        "min_free_kbytes": min_free_kbytes,
    }


def _parse_active_sysctl_directives(text: str) -> List[Tuple[str, str]]:
    """Extracts `(key, value)` pairs from non-comment lines of a sysctl config file."""
    pairs: List[Tuple[str, str]] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        clean_k = k.strip()
        clean_v = v.strip()
        if clean_k:
            pairs.append((clean_k, clean_v))
    return pairs


def _detect_wan_iface(run_fn: Optional[Callable] = None) -> str:
    ip_bin = _find_system_bin("ip", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))
    if not ip_bin or sys.platform == "win32":
        return ""
    runner = run_fn or subprocess.run
    try:
        res = runner(
            [ip_bin, "-o", "-4", "route", "show", "to", "default"],
            capture_output=True, text=True, timeout=2.0, check=False
        )
        m = re.search(r"\bdev\s+([^\s]+)", res.stdout or "")
        if m and IFACE_NAME_REGEX.match(m.group(1)):
            return m.group(1)
    except Exception:
        pass
    return ""


def get_kernel_tuning_status(
    *,
    meminfo_path: str = "/proc/meminfo",
    proc_sys_root: str = "/proc/sys",
    sysctl_conf_path: str = SYSCTL_CONF_PATH,
    sysctl_d_dir: str = SYSCTL_D_DIR,
    xfw_sysctl_path: str = XFW_SYSCTL_CONF_PATH,
    dsr_sysctl_path: str = DSR_SYSCTL_CONF_PATH,
    modules_path: str = ETC_MODULES_PATH,
) -> Dict[str, Any]:
    """
    Inspects live kernel tuning metrics and detects legacy/conflicting configurations
    (e.g. `rp_filter=2`, custom `/etc/sysctl.conf`, conflicting `/etc/sysctl.d/*.conf`, duplicate `/etc/modules`).
    """
    mem_mb, cpu_cores = detect_system_capacity(meminfo_path=meminfo_path)
    profile = compute_tuning_profile(mem_mb, cpu_cores)

    ip_forward = _read_sysctl_proc("net.ipv4.ip_forward", proc_sys_root)
    ipv6_forward = _read_sysctl_proc("net.ipv6.conf.all.forwarding", proc_sys_root)
    cc = _read_sysctl_proc("net.ipv4.tcp_congestion_control", proc_sys_root) or "unknown"
    avail_cc = (_read_sysctl_proc("net.ipv4.tcp_available_congestion_control", proc_sys_root) or "").split()
    qdisc = _read_sysctl_proc("net.core.default_qdisc", proc_sys_root) or "unknown"
    rp_all = _read_sysctl_proc("net.ipv4.conf.all.rp_filter", proc_sys_root)
    rp_def = _read_sysctl_proc("net.ipv4.conf.default.rp_filter", proc_sys_root)
    mtu_probing = _read_sysctl_proc("net.ipv4.tcp_mtu_probing", proc_sys_root)
    ct_max = _read_sysctl_proc("net.netfilter.nf_conntrack_max", proc_sys_root)
    rmem_max = _read_sysctl_proc("net.core.rmem_max", proc_sys_root)
    somaxconn = _read_sysctl_proc("net.core.somaxconn", proc_sys_root)
    file_max = _read_sysctl_proc("fs.file-max", proc_sys_root)

    conflicts: List[Dict[str, str]] = []
    conflicting_files: List[str] = []

    if rp_all is not None and rp_all != "0":
        conflicts.append({
            "code": "rp_filter_nonzero",
            "message": f"net.ipv4.conf.all.rp_filter is {rp_all}; ESP Spoof / DSR tunnels require 0.",
        })
    if rp_def is not None and rp_def != "0":
        conflicts.append({
            "code": "rp_filter_default_nonzero",
            "message": f"net.ipv4.conf.default.rp_filter is {rp_def}; DSR recommends 0.",
        })

    # Inspect /etc/sysctl.conf for custom tuning or rp_filter overrides
    sysctl_conf_text = _read_text_safe(sysctl_conf_path)
    sysctl_pairs = _parse_active_sysctl_directives(sysctl_conf_text or "")
    if sysctl_pairs:
        conflicting_files.append(sysctl_conf_path)
        has_rp2 = any(k.endswith(".rp_filter") and v != "0" for k, v in sysctl_pairs)
        conflicts.append({
            "code": "legacy_sysctl_conf",
            "message": (
                f"{sysctl_conf_path} contains {len(sysctl_pairs)} active directive(s)"
                + (" including non-zero rp_filter" if has_rp2 else "")
                + "."
            ),
        })

    # Inspect /etc/sysctl.d/*.conf for third-party overrides
    if os.path.isdir(sysctl_d_dir):
        xfw_base = os.path.basename(xfw_sysctl_path)
        dsr_base = os.path.basename(dsr_sysctl_path)
        for fname in sorted(os.listdir(sysctl_d_dir)):
            if not fname.endswith(".conf"):
                continue
            if fname in (xfw_base, dsr_base) or fname.startswith(_DISTRO_SYSCTL_PREFIXES):
                continue
            fpath = os.path.join(sysctl_d_dir, fname)
            if os.path.islink(fpath) or not os.path.isfile(fpath):
                continue
            f_text = _read_text_safe(fpath) or ""
            f_pairs = _parse_active_sysctl_directives(f_text)
            matched_keys = [k for k, _ in f_pairs if k in _MANAGED_CONFLICT_KEYS or k.endswith(".rp_filter")]
            if matched_keys:
                conflicting_files.append(fpath)
                conflicts.append({
                    "code": "conflicting_sysctl_dropin",
                    "message": f"Conflicting drop-in {fpath} overrides {', '.join(sorted(set(matched_keys))[:3])}.",
                })

    # Inspect /etc/modules for duplicate nf_conntrack lines
    mod_text = _read_text_safe(modules_path)
    duplicate_modules = False
    if mod_text is not None:
        non_comment = [ln.strip() for ln in mod_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if non_comment.count("nf_conntrack") > 1:
            duplicate_modules = True
            conflicts.append({
                "code": "duplicate_etc_modules",
                "message": f"{modules_path} has duplicate 'nf_conntrack' entries ({non_comment.count('nf_conntrack')}x).",
            })

    xfw_tuned = os.path.isfile(xfw_sysctl_path)
    has_conflict = len(conflicts) > 0
    is_optimal = (
        xfw_tuned
        and ip_forward == "1"
        and (rp_all in (None, "0"))
        and (rp_def in (None, "0"))
        and cc == "bbr"
        and qdisc == "fq"
        and not has_conflict
    )

    return {
        "supported": sys.platform != "win32" and os.path.isdir(proc_sys_root),
        "tuned": xfw_tuned,
        "optimal": is_optimal,
        "previous_tuning_detected": bool(conflicting_files or duplicate_modules),
        "conflicting_files": conflicting_files,
        "duplicate_modules": duplicate_modules,
        "conflicts": conflicts,
        "profile": profile,
        "live": {
            "ip_forward": ip_forward == "1" if ip_forward is not None else None,
            "ipv6_forward": ipv6_forward == "1" if ipv6_forward is not None else None,
            "congestion_control": cc,
            "bbr_available": "bbr" in avail_cc or cc == "bbr",
            "default_qdisc": qdisc,
            "rp_filter_all": int(rp_all) if (rp_all is not None and rp_all.lstrip("-").isdigit()) else None,
            "rp_filter_default": int(rp_def) if (rp_def is not None and rp_def.lstrip("-").isdigit()) else None,
            "mtu_probing": int(mtu_probing) if (mtu_probing is not None and mtu_probing.isdigit()) else None,
            "conntrack_loaded": ct_max is not None,
            "conntrack_max": int(ct_max) if (ct_max is not None and ct_max.isdigit()) else None,
            "rmem_max": int(rmem_max) if (rmem_max is not None and rmem_max.isdigit()) else None,
            "somaxconn": int(somaxconn) if (somaxconn is not None and somaxconn.isdigit()) else None,
            "file_max": int(file_max) if (file_max is not None and file_max.isdigit()) else None,
        },
    }


def _deduplicate_etc_modules(modules_path: str, backup_dir: Optional[str] = None) -> bool:
    """Ensures `nf_conntrack` appears cleanly once in /etc/modules without duplicates."""
    raw = _read_text_safe(modules_path)
    if raw is None:
        # On modern systemd-only hosts /etc/modules may not exist; /etc/modules-load.d handles persistence
        return False

    lines = raw.splitlines()
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        _atomic_write_text(os.path.join(backup_dir, os.path.basename(modules_path) + ".bak"), raw + "\n")

    seen_modules: Set[str] = set()
    cleaned: List[str] = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            cleaned.append(ln)
            continue
        mod_name = stripped.split()[0]
        if mod_name in seen_modules:
            continue
        seen_modules.add(mod_name)
        cleaned.append(stripped)

    if "nf_conntrack" not in seen_modules:
        cleaned.append("nf_conntrack")

    new_content = "\n".join(cleaned).rstrip() + "\n"
    changed = (new_content.strip() != raw.strip())
    if changed:
        _atomic_write_text(modules_path, new_content)
    return changed


def _cleanup_previous_sysctl(
    *,
    sysctl_conf_path: str,
    sysctl_d_dir: str,
    xfw_sysctl_path: str,
    dsr_sysctl_path: str,
    modules_path: str,
    backup_dir: str,
) -> Dict[str, Any]:
    """Backs up and cleans previous conflicting /etc/sysctl.conf, /etc/sysctl.d/*.conf, and duplicate /etc/modules."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    session_bak = os.path.join(backup_dir, f"sysctl_reset_{ts}_{os.getpid()}")
    backed_up: List[str] = []
    removed: List[str] = []

    raw_main = _read_text_safe(sysctl_conf_path)
    if raw_main is not None and _parse_active_sysctl_directives(raw_main):
        os.makedirs(session_bak, exist_ok=True)
        bak_main = os.path.join(session_bak, "sysctl.conf.bak")
        _atomic_write_text(bak_main, raw_main + "\n")
        backed_up.append(bak_main)
        _atomic_write_text(
            sysctl_conf_path,
            "# Reset by XForwarder Kernel Optimizer\n"
            "# Persistent kernel network tuning is managed in /etc/sysctl.d/99-xforwarder.conf\n",
        )
        removed.append(sysctl_conf_path)

    if os.path.isdir(sysctl_d_dir):
        xfw_base = os.path.basename(xfw_sysctl_path)
        dsr_base = os.path.basename(dsr_sysctl_path)
        d_bak_dir = os.path.join(session_bak, "sysctl.d")
        for fname in sorted(os.listdir(sysctl_d_dir)):
            if not fname.endswith(".conf"):
                continue
            if fname in (xfw_base, dsr_base) or fname.startswith(_DISTRO_SYSCTL_PREFIXES):
                continue
            fpath = os.path.join(sysctl_d_dir, fname)
            if os.path.islink(fpath) or not os.path.isfile(fpath):
                continue
            raw_d = _read_text_safe(fpath) or ""
            pairs = _parse_active_sysctl_directives(raw_d)
            if any(k in _MANAGED_CONFLICT_KEYS or k.endswith(".rp_filter") for k, _ in pairs):
                os.makedirs(d_bak_dir, exist_ok=True)
                bak_d = os.path.join(d_bak_dir, fname)
                _atomic_write_text(bak_d, raw_d + "\n")
                backed_up.append(bak_d)
                os.remove(fpath)
                removed.append(fpath)

    mod_deduped = _deduplicate_etc_modules(modules_path, backup_dir=session_bak)
    return {
        "backup_dir": session_bak if backed_up or mod_deduped else None,
        "backed_up_files": backed_up,
        "cleaned_files": removed,
        "modules_deduplicated": mod_deduped,
    }


def _render_xforwarder_sysctl(
    profile: Dict[str, Any],
    *,
    bbr_ok: bool,
    proc_sys_root: str = "/proc/sys",
    active_ifaces: Optional[List[str]] = None,
) -> str:
    """Builds the authoritative ESP/DSR-safe high-performance `/etc/sysctl.d/99-xforwarder.conf` text."""
    lines: List[str] = [
        "# Generated by XForwarder Kernel & Network Optimizer",
        f"# Host Profile: {profile['mem_mb']} MB RAM, {profile['cpu_cores']} vCPU ({profile['tier_label']})",
        "",
        "# --- Forwarding & RP Filter (MUST stay 0 for ESP Spoof / DSR tunnels) ---",
        "net.ipv4.ip_forward = 1",
        "net.ipv4.conf.all.rp_filter = 0",
        "net.ipv4.conf.default.rp_filter = 0",
    ]
    for iface in sorted(set(active_ifaces or [])):
        if IFACE_NAME_REGEX.match(iface):
            lines.append(f"net.ipv4.conf.{iface}.rp_filter = 0")

    if _proc_sysctl_exists("net.ipv6.conf.all.forwarding", proc_sys_root):
        lines.append("net.ipv6.conf.all.forwarding = 1")
    if _proc_sysctl_exists("net.ipv6.conf.default.forwarding", proc_sys_root):
        lines.append("net.ipv6.conf.default.forwarding = 1")

    lines += [
        "",
        "# --- Security & Redirect Hardening ---",
        "net.ipv4.conf.all.accept_source_route = 0",
        "net.ipv4.conf.default.accept_source_route = 0",
        "net.ipv4.conf.all.accept_redirects = 0",
        "net.ipv4.conf.default.accept_redirects = 0",
        "net.ipv4.conf.all.send_redirects = 0",
        "net.ipv4.conf.default.send_redirects = 0",
        "net.ipv4.icmp_echo_ignore_broadcasts = 1",
        "net.ipv4.icmp_ignore_bogus_error_responses = 1",
    ]
    if _proc_sysctl_exists("net.ipv6.conf.all.accept_source_route", proc_sys_root):
        lines += [
            "net.ipv6.conf.all.accept_source_route = 0",
            "net.ipv6.conf.default.accept_source_route = 0",
            "net.ipv6.conf.all.accept_redirects = 0",
            "net.ipv6.conf.default.accept_redirects = 0",
        ]

    if bbr_ok:
        lines += [
            "",
            "# --- TCP Congestion Control (BBR + fq) ---",
            "net.core.default_qdisc = fq",
            "net.ipv4.tcp_congestion_control = bbr",
        ]

    lines += [
        "",
        "# --- Socket Buffers & Queues ---",
        f"net.core.somaxconn = {profile['somaxconn']}",
        "net.core.netdev_max_backlog = 100000",
        f"net.ipv4.tcp_max_syn_backlog = {profile['syn_backlog']}",
        f"net.ipv4.tcp_max_tw_buckets = {profile['tw_buckets']}",
        f"net.core.rmem_default = {profile['rmem_def']}",
        f"net.core.wmem_default = {profile['wmem_def']}",
        f"net.core.rmem_max = {profile['rmem_max']}",
        f"net.core.wmem_max = {profile['wmem_max']}",
        f"net.ipv4.tcp_rmem = 4096 {profile['rmem_def']} {profile['rmem_max']}",
        f"net.ipv4.tcp_wmem = 4096 {profile['wmem_def']} {profile['wmem_max']}",
        "net.ipv4.udp_rmem_min = 16384",
        "net.ipv4.udp_wmem_min = 16384",
        "",
        "# --- TCP Optimization & PMTU Discovery ---",
        "net.ipv4.ip_local_port_range = 20000 65535",
        "net.ipv4.ip_local_reserved_ports = 80,443,2053,2083,2087,2096,8443,9000-9999",
        "net.ipv4.tcp_fastopen = 3",
        "net.ipv4.tcp_fin_timeout = 15",
        "net.ipv4.tcp_tw_reuse = 1",
        "net.ipv4.tcp_window_scaling = 1",
        "net.ipv4.tcp_timestamps = 1",
        "net.ipv4.tcp_sack = 1",
        "net.ipv4.tcp_dsack = 1",
        "net.ipv4.tcp_slow_start_after_idle = 0",
        "net.ipv4.tcp_no_metrics_save = 1",
        "net.ipv4.tcp_moderate_rcvbuf = 1",
        "net.ipv4.tcp_mtu_probing = 1",
        "net.ipv4.tcp_base_mss = 1024",
        "net.ipv4.tcp_keepalive_time = 300",
        "net.ipv4.tcp_keepalive_intvl = 15",
        "net.ipv4.tcp_keepalive_probes = 5",
    ]

    napi_lines = []
    for k, v in (
        ("net.core.netdev_budget", 1200),
        ("net.core.netdev_budget_usecs", 8000),
        ("net.core.dev_weight", 128),
    ):
        if _proc_sysctl_exists(k, proc_sys_root):
            napi_lines.append(f"{k} = {v}")
    if napi_lines:
        lines += ["", "# --- NAPI SoftIRQ Polling Budget ---"] + napi_lines

    jit_lines = []
    for k, v in (
        ("net.core.bpf_jit_enable", 1),
        ("net.core.bpf_jit_kallsyms", 1),
        ("net.core.bpf_jit_harden", 0),
    ):
        if _proc_sysctl_exists(k, proc_sys_root):
            jit_lines.append(f"{k} = {v}")
    if jit_lines:
        lines += ["", "# --- BPF JIT ---"] + jit_lines

    if _proc_sysctl_exists("net.netfilter.nf_conntrack_max", proc_sys_root):
        lines += [
            "",
            "# --- Conntrack Scaling (does not block DSR notrack rules) ---",
            f"net.netfilter.nf_conntrack_max = {profile['conntrack_max']}",
            "net.netfilter.nf_conntrack_tcp_timeout_established = 3600",
            "net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30",
            "net.netfilter.nf_conntrack_tcp_timeout_close_wait = 15",
            "net.netfilter.nf_conntrack_tcp_timeout_fin_wait = 30",
            "net.netfilter.nf_conntrack_udp_timeout = 30",
            "net.netfilter.nf_conntrack_udp_timeout_stream = 60",
        ]

    lines += [
        "",
        "# --- Virtual Memory & File Descriptors ---",
        "vm.swappiness = 10",
        "vm.dirty_ratio = 15",
        "vm.dirty_background_ratio = 5",
        "vm.vfs_cache_pressure = 50",
        f"vm.min_free_kbytes = {profile['min_free_kbytes']}",
        "vm.overcommit_memory = 0",
        "fs.file-max = 2097152",
    ]
    for k, v in (
        ("fs.nr_open", 2097152),
        ("fs.inotify.max_user_watches", 524288),
        ("fs.inotify.max_user_instances", 512),
    ):
        if _proc_sysctl_exists(k, proc_sys_root):
            lines.append(f"{k} = {v}")

    return "\n".join(lines) + "\n"


def apply_kernel_tuning(
    reset_existing: bool = False,
    *,
    meminfo_path: str = "/proc/meminfo",
    proc_sys_root: str = "/proc/sys",
    sysctl_conf_path: str = SYSCTL_CONF_PATH,
    sysctl_d_dir: str = SYSCTL_D_DIR,
    xfw_sysctl_path: str = XFW_SYSCTL_CONF_PATH,
    dsr_sysctl_path: str = DSR_SYSCTL_CONF_PATH,
    modules_path: str = ETC_MODULES_PATH,
    modules_load_dir: str = MODULES_LOAD_DIR,
    haproxy_override_path: str = HAPROXY_OVERRIDE_PATH,
    backup_dir: str = DEFAULT_BACKUP_DIR,
    hashsize_param_path: str = "/sys/module/nf_conntrack/parameters/hashsize",
    run_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Applies the XForwarder ESP/DSR-safe kernel & network optimization profile.
    When `reset_existing=True`, backs up and clears conflicting `/etc/sysctl.conf`,
    third-party `/etc/sysctl.d/*.conf`, and duplicate `/etc/modules` entries first.
    """
    if sys.platform == "win32" and proc_sys_root == "/proc/sys":
        return {"ok": False, "error": "Kernel sysctl optimization requires a Linux host."}

    runner = run_fn or subprocess.run
    warnings: List[str] = []
    reset_report: Dict[str, Any] = {
        "performed": bool(reset_existing),
        "backup_dir": None,
        "backed_up_files": [],
        "cleaned_files": [],
        "modules_deduplicated": False,
    }

    if reset_existing:
        reset_report = {
            "performed": True,
            **_cleanup_previous_sysctl(
                sysctl_conf_path=sysctl_conf_path,
                sysctl_d_dir=sysctl_d_dir,
                xfw_sysctl_path=xfw_sysctl_path,
                dsr_sysctl_path=dsr_sysctl_path,
                modules_path=modules_path,
                backup_dir=backup_dir,
            ),
        }

    # 1. Load nf_conntrack + tcp_bbr safely & deduplicate module persistence
    modprobe_bin = _find_system_bin("modprobe", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))
    if modprobe_bin:
        for mod_name in ("nf_conntrack", "tcp_bbr"):
            try:
                runner([modprobe_bin, mod_name], capture_output=True, text=True, timeout=3.0, check=False)
            except Exception:
                pass

    # Always deduplicate /etc/modules if nf_conntrack is duplicated, or ensure clean single entry
    if _deduplicate_etc_modules(modules_path):
        reset_report["modules_deduplicated"] = True

    avail_cc_raw = _read_sysctl_proc("net.ipv4.tcp_available_congestion_control", proc_sys_root) or ""
    bbr_ok = "bbr" in avail_cc_raw.split()

    try:
        os.makedirs(modules_load_dir, exist_ok=True)
        _atomic_write_text(os.path.join(modules_load_dir, "xforwarder-conntrack.conf"), "nf_conntrack\n")
        if bbr_ok:
            _atomic_write_text(os.path.join(modules_load_dir, "bbr.conf"), "tcp_bbr\n")
    except Exception as e:
        warnings.append(f"modules-load.d write warning: {e}")

    mem_mb, cpu_cores = detect_system_capacity(meminfo_path=meminfo_path)
    profile = compute_tuning_profile(mem_mb, cpu_cores)

    # Set conntrack hashsize safely via sysfs instead of read-only sysctl key
    if os.path.isfile(hashsize_param_path):
        try:
            with open(hashsize_param_path, "w", encoding="utf-8") as hf:
                hf.write(str(profile["conntrack_buckets"]))
        except Exception:
            pass

    active_ifaces: List[str] = []
    proc_net_conf = os.path.join(proc_sys_root, "net", "ipv4", "conf")
    if os.path.isdir(proc_net_conf):
        for name in os.listdir(proc_net_conf):
            if name not in ("all", "default", "lo") and IFACE_NAME_REGEX.match(name):
                active_ifaces.append(name)

    # 2. Write /etc/sysctl.d/99-xforwarder.conf atomically
    sysctl_content = _render_xforwarder_sysctl(
        profile,
        bbr_ok=bbr_ok,
        proc_sys_root=proc_sys_root,
        active_ifaces=active_ifaces,
    )
    try:
        _atomic_write_text(xfw_sysctl_path, sysctl_content)
    except Exception as e:
        return {"ok": False, "error": f"Failed to write {xfw_sysctl_path}: {e}"}

    # 3. Apply sysctl settings (use --system so DSR drop-in 99-xforwarder-dsr.conf is preserved too)
    sysctl_bin = _find_system_bin("sysctl", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))
    if sysctl_bin:
        try:
            runner([sysctl_bin, "-e", "--system"], capture_output=True, text=True, timeout=6.0, check=False)
            runner([sysctl_bin, "-e", "-p", xfw_sysctl_path], capture_output=True, text=True, timeout=4.0, check=False)
            if os.path.isfile(dsr_sysctl_path):
                runner([sysctl_bin, "-e", "-p", dsr_sysctl_path], capture_output=True, text=True, timeout=4.0, check=False)
        except Exception as e:
            warnings.append(f"sysctl apply warning: {e}")

    # 4. Systemd LimitNOFILE override for HAProxy
    try:
        _atomic_write_text(haproxy_override_path, "[Service]\nLimitNOFILE=1048576\n")
        systemctl_bin = _find_system_bin("systemctl", ("/bin", "/usr/bin", "/sbin"))
        if systemctl_bin:
            runner([systemctl_bin, "daemon-reload"], capture_output=True, text=True, timeout=4.0, check=False)
    except Exception as e:
        warnings.append(f"HAProxy LimitNOFILE warning: {e}")

    # 5. WAN NIC offload tuning + fq flow_limit 1000
    wan_iface = _detect_wan_iface(run_fn=runner)
    if wan_iface:
        ethtool_bin = _find_system_bin("ethtool", ("/sbin", "/usr/sbin", "/bin", "/usr/bin"))
        if ethtool_bin:
            for offload_args in (
                ["-K", wan_iface, "tso", "on", "gso", "on", "gro", "off"],
                ["-K", wan_iface, "tx-udp_tnl-segmentation", "off", "tx-udp_tnl-csum-segmentation", "off"],
            ):
                try:
                    runner([ethtool_bin] + offload_args, capture_output=True, text=True, timeout=2.0, check=False)
                except Exception:
                    pass
        if bbr_ok:
            try:
                ensure_fq_qdisc(wan_iface, flow_limit=1000)
            except Exception:
                pass

    status_after = get_kernel_tuning_status(
        meminfo_path=meminfo_path,
        proc_sys_root=proc_sys_root,
        sysctl_conf_path=sysctl_conf_path,
        sysctl_d_dir=sysctl_d_dir,
        xfw_sysctl_path=xfw_sysctl_path,
        dsr_sysctl_path=dsr_sysctl_path,
        modules_path=modules_path,
    )

    msg = f"Applied {profile['tier_label']} optimization ({'BBR + fq' if bbr_ok else 'no BBR'}, rp_filter=0)"
    if reset_report.get("cleaned_files"):
        msg += f" after backing up & cleaning {len(reset_report['cleaned_files'])} previous file(s)"

    return {
        "ok": True,
        "message": msg,
        "wan_interface": wan_iface or None,
        "bbr_enabled": bbr_ok,
        "sysctl_file": xfw_sysctl_path,
        "reset": reset_report,
        "warnings": warnings,
        "status": status_after,
    }


def _print_cli_status(status: Dict[str, Any]) -> None:
    prof = status.get("profile", {})
    live = status.get("live", {})
    print(f"  Host Capacity   : {prof.get('mem_mb', '?')} MB RAM, {prof.get('cpu_cores', '?')} vCPU ({prof.get('tier_label', '')})")
    print(f"  TCP / Qdisc     : {live.get('congestion_control')} / {live.get('default_qdisc')} (BBR available: {live.get('bbr_available')})")
    print(f"  IPv4/IPv6 Fwd   : {live.get('ip_forward')} / {live.get('ipv6_forward')}")
    print(f"  RP Filter       : all={live.get('rp_filter_all')}, default={live.get('rp_filter_default')} (ESP/DSR requires 0)")
    print(f"  Conntrack       : loaded={live.get('conntrack_loaded')}, max={live.get('conntrack_max')}")
    print(f"  Buffers / Queue : rmem_max={live.get('rmem_max')}, somaxconn={live.get('somaxconn')}")
    conflicts = status.get("conflicts") or []
    if conflicts:
        print("  [!] Conflicts / Legacy Tuning Detected:")
        for c in conflicts:
            print(f"      - {c.get('message')}")
    else:
        print("  [OK] No rp_filter or legacy sysctl conflicts detected.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--status" in args:
        st = get_kernel_tuning_status()
        if "--json" in args:
            print(json.dumps(st, indent=2, ensure_ascii=False))
        else:
            _print_cli_status(st)
    elif "--apply" in args:
        res = apply_kernel_tuning(reset_existing=("--reset" in args))
        if "--json" in args:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res.get("ok"):
                print(f"[OK] {res.get('message')}")
                if res.get("reset", {}).get("backup_dir"):
                    print(f"[INFO] Backups saved to: {res['reset']['backup_dir']}")
                _print_cli_status(res.get("status", {}))
            else:
                print(f"[ERR] {res.get('error')}", file=sys.stderr)
                sys.exit(1)

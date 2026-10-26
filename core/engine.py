#!/usr/bin/env python3
"""
XForwarder - Core Engine Daemon
Monitors uplink destinations (IPv6 HAProxy vs IPv4 NFTables tunnels),
manages automatic failover, and dynamically synchronizes kernel NAT and user-space daemons.
Refactored into clean modular architecture delegating to specialized core subsystems.
"""

import os
import sys
import time
import json
import socket
import subprocess
import threading
import signal
import ipaddress
import shutil
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from core.config_manager import (
    get_config_path, get_state_file_path, migrate_and_normalize_config,
    load_config as cm_load_config, save_config as cm_save_config,
    CONFIG_PATH as DEFAULT_CONFIG_PATH, LEGACY_CONFIG_PATH, LOCAL_CONFIG_PATH,
    STATE_FILE_PATH, LEGACY_STATE_FILE_PATH
)
from core.prober import (
    is_private_or_tunnel_target, validate_probe_route,
    probe_destination_icmp as prober_probe_destination_icmp,
    check_destination as prober_check_destination,
    fast_confirm_burst as prober_fast_confirm_burst,
    is_interface_up, get_route_interface
)
from core.firewall import is_ipv6_supported, apply_nftables, flush_conntrack
from core.proxy_gen import apply_haproxy, apply_nginx, HAPROXY_CONF_PATH, UDP_CONF_PATH, NGINX_CONF_PATH
from core.route_quality import (
    summarize_cycle, aggregate_window, compute_score, classify_status, decide_route, pick_best_now
)

try:
    from core.metrics import parse_ping_output, sanitize_target_host, LossMonitorScheduler
    from core.traffic import TrafficCollector
except ImportError:
    from metrics import parse_ping_output, sanitize_target_host, LossMonitorScheduler
    try:
        from traffic import TrafficCollector
    except ImportError:
        TrafficCollector = None

PID_FILE_CANDIDATES = [
    "/run/xforwarder/engine.pid",
    "/run/forward-manager/engine.pid",
    os.path.join(tempfile.gettempdir(), "xforwarder_engine.pid"),
]


class XForwarderEngine:
    migrate_and_normalize_config = staticmethod(migrate_and_normalize_config)
    _is_ipv6_supported = staticmethod(is_ipv6_supported)

    def __init__(self, config_path: Optional[str] = None, state_file_path: Optional[str] = None):
        self.config_path = self._resolve_config_path(config_path)
        self.state_file_path = state_file_path or STATE_FILE_PATH
        self.running = False
        self.lock = threading.Lock()
        self.config: Dict[str, Any] = {}
        self.runtime_state: Dict[str, Any] = {
            "uptime_started": time.time(),
            "last_check_timestamp": 0,
            "wan_interface": "unknown",
            "active_services": {
                "haproxy": False,
                "nginx": False,
                "udp_stream": False,
                "nftables": False
            },
            "rules_state": {}
        }
        self._load_initial_runtime_state()
        self._last_applied_rules: Optional[str] = None
        self._wake_event = threading.Event()
        self._last_nft_content: Optional[str] = None
        self._pid_path: Optional[str] = None
        self._loss_scheduler: Optional[Any] = None
        self._traffic_collector: Optional[Any] = None
        self._last_traffic_cycle: float = 0.0
        self._probe_executor: Optional[ThreadPoolExecutor] = None
        self._target_probe_cache: Dict[Any, Dict[str, Any]] = {}
        self._target_last_probe_time: Dict[str, float] = {}
        self._target_last_fast_check: Dict[str, float] = {}
        self._target_history: Dict[str, Dict[str, Any]] = {}
        self._target_lock = threading.Lock()
        self.load_config()

    @property
    def rules_state(self) -> Dict[str, Any]:
        return self.runtime_state.get("rules_state", {})

    def _load_initial_runtime_state(self) -> None:
        """Loads pre-existing runtime state from disk if available to prevent state erasure during dynamic sync."""
        paths = [self.state_file_path]
        if self.state_file_path == STATE_FILE_PATH:
            paths.append(LEGACY_STATE_FILE_PATH)
        for s_path in paths:
            if os.path.exists(s_path):
                try:
                    with open(s_path, "r", encoding="utf-8") as rf:
                        data = json.load(rf)
                        if isinstance(data, dict):
                            rt = data.get("runtime", {}) if isinstance(data.get("runtime"), dict) else data
                            if isinstance(rt, dict) and "rules_state" in rt:
                                self.runtime_state["rules_state"] = rt["rules_state"]
                            if isinstance(rt, dict) and "uptime_started" in rt:
                                self.runtime_state["uptime_started"] = rt["uptime_started"]
                            break
                except Exception:
                    pass

    def _resolve_config_path(self, override_path: Optional[str]) -> str:
        return get_config_path(override_path)

    def _save_config_unlocked(self) -> bool:
        """Atomically writes current configuration to disk."""
        return cm_save_config(self.config, self.config_path)

    def load_config(self) -> None:
        """Loads and normalizes configuration from disk using self-healing schema migration."""
        with self.lock:
            self.config = cm_load_config(self.config_path)
            self.runtime_state["wan_interface"] = self._detect_wan_interface()

    def save_config(self) -> bool:
        with self.lock:
            return self._save_config_unlocked()

    def _detect_wan_interface(self) -> str:
        cfg_iface = self.config.get("wan_interface", "auto")
        if cfg_iface and cfg_iface != "auto":
            return cfg_iface
        if sys.platform != "win32":
            try:
                out = subprocess.check_output(
                    ["ip", "-o", "route", "show", "default"],
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
                parts = out.split()
                if "dev" in parts:
                    idx = parts.index("dev")
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
            except Exception:
                pass
        return "eth0"

    def _is_interface_up(self, iface: str) -> bool:
        return is_interface_up(iface)

    def _get_route_interface(self, target: str) -> Optional[str]:
        return get_route_interface(target)

    def _validate_probe_route(self, dest: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        wan_iface = self._detect_wan_interface()
        return validate_probe_route(
            dest,
            wan_iface=wan_iface,
            is_interface_up_fn=self._is_interface_up,
            get_route_interface_fn=self._get_route_interface
        )

    def probe_destination_icmp(
        self,
        target: str,
        iface: Optional[str] = None,
        count: int = 10,
        interval_ms: int = 200
    ) -> Dict[str, Any]:
        return prober_probe_destination_icmp(target, iface=iface, count=count, interval_ms=interval_ms)

    def check_destination(
        self,
        dest: Dict[str, Any],
        rule_port: Optional[int] = None,
        protocol: Optional[str] = None,
        count: int = 1
    ) -> Dict[str, Any]:
        wan_iface = self._detect_wan_interface()
        return prober_check_destination(
            dest,
            rule_port=rule_port,
            protocol=protocol,
            count=count,
            wan_iface=wan_iface,
            validate_route_fn=self._validate_probe_route
        )

    def _send_haproxy_runtime_cmd(self, cmd: str) -> Tuple[bool, str]:
        sock_path = "/run/haproxy/admin.sock"
        if not os.path.exists(sock_path) or sys.platform == "win32":
            return False, "HAProxy stats socket not available"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.5)
                client.connect(sock_path)
                client.sendall((cmd.strip() + "\n").encode())
                response = b""
                while True:
                    data = client.recv(1024)
                    if not data:
                        break
                    response += data
                return True, response.decode().strip()
        except Exception as e:
            return False, str(e)

    def _fast_confirm_burst(
        self,
        dest: Dict[str, Any],
        rule_port: Optional[int] = None,
        protocol: Optional[str] = "both",
        count: int = 5
    ) -> Dict[str, Any]:
        return prober_fast_confirm_burst(dest, rule_port=rule_port, protocol=protocol, count=count)

    def _hot_toggle_rule_priority(self, rule: Dict[str, Any], old_prio: int, new_prio: int, is_critical: bool = False) -> None:
        """
        Performs runtime priority transition.
        In planned switches: preserves active client sockets and allows connection draining.
        In critical switches: flushes stale conntrack states for TCP and UDP.
        """
        port = rule.get("port")
        if not port:
            return
        if is_critical:
            flush_conntrack(port)

    def _probe_all_destinations(self, rules: List[Dict[str, Any]], now: Optional[float] = None) -> Dict[Any, Dict[str, Any]]:
        """
        Deduplicates unique destination IP endpoints across all rules, caches 10-ping probes in memory
        for target_probe_interval_seconds (default: 60s), and executes fast 2-ping liveness checks every
        fast_liveness_interval_seconds (default: 15s) to trigger immediate emergency failovers.
        Guarantees that an IP shared across 5 or 50 ports is probed exactly once per cycle,
        synchronizing latency, loss, and composite quality metrics across all matching rules.
        """
        curr_time = now if now is not None else time.time()
        probe_interval = float(self.config.get("target_probe_interval_seconds", 60.0))
        fast_interval = float(self.config.get("fast_liveness_interval_seconds", 15.0))
        count = int(self.config.get("probe_count", 10))
        interval_ms = int(self.config.get("probe_interval_ms", 200))
        window_sec = float(self.config.get("quality_window_seconds", 300))
        max_loss = float(self.config.get("max_acceptable_loss", 25))
        crit_loss = float(self.config.get("critical_loss_percent", 30))

        unique_targets: Dict[str, Dict[str, Any]] = {}
        invalid_results: Dict[str, Dict[str, Any]] = {}

        for rule in rules:
            for dest in rule.get("destinations", []):
                raw_target = str(dest.get("target", "")).strip().strip("[]")
                if not raw_target:
                    continue
                clean_target = (sanitize_target_host(raw_target) or raw_target).lower()
                is_valid, iface, reason = self._validate_probe_route(dest)
                if not is_valid:
                    invalid_results[clean_target] = {
                        "healthy": False,
                        "packets_sent": count,
                        "packets_received": 0,
                        "packet_loss": 100.0,
                        "latency_ms": None,
                        "jitter_ms": 0.0,
                        "reason": reason
                    }
                    # Immediately invalidate previous cached entries if route became invalid
                    with self._target_lock:
                        self._target_probe_cache.pop(clean_target, None)
                        self._target_last_probe_time.pop(clean_target, None)
                        self._target_last_fast_check.pop(clean_target, None)
                        self._target_history.pop(clean_target, None)
                else:
                    if clean_target not in unique_targets or (iface and not unique_targets[clean_target].get("iface")):
                        unique_targets[clean_target] = {
                            "target": clean_target,
                            "iface": iface,
                            "dest": dest
                        }

        # Evict stale target entries for rules that have been removed
        with self._target_lock:
            active_targets = set(unique_targets.keys()) | set(invalid_results.keys())
            stale_keys = [k for k in list(self._target_probe_cache.keys()) if k not in active_targets]
            for sk in stale_keys:
                self._target_probe_cache.pop(sk, None)
                self._target_last_probe_time.pop(sk, None)
                self._target_last_fast_check.pop(sk, None)
                self._target_history.pop(sk, None)

        # Separate targets into 60s full probe vs 15s fast liveness check
        targets_to_full_probe: Dict[str, Dict[str, Any]] = {}
        targets_to_fast_check: Dict[str, Dict[str, Any]] = {}
        with self._target_lock:
            for target, info in unique_targets.items():
                last_t = self._target_last_probe_time.get(target, 0.0)
                last_fast = self._target_last_fast_check.get(target, last_t)

                if (target not in self._target_probe_cache) or (curr_time - last_t >= probe_interval):
                    targets_to_full_probe[target] = info
                elif (curr_time - last_fast >= fast_interval):
                    targets_to_fast_check[target] = info

        # Execute parallel probes (full 10-ping bursts or fast 2-ping liveness checks)
        if targets_to_full_probe or targets_to_fast_check:
            if not self._probe_executor:
                self._probe_executor = ThreadPoolExecutor(max_workers=8)

            futures = {}
            for target, info in targets_to_full_probe.items():
                f = self._probe_executor.submit(
                    self.probe_destination_icmp,
                    target,
                    iface=info.get("iface"),
                    count=count,
                    interval_ms=interval_ms
                )
                futures[f] = (target, "full", info)

            for target, info in targets_to_fast_check.items():
                f = self._probe_executor.submit(
                    self.probe_destination_icmp,
                    target,
                    iface=info.get("iface"),
                    count=2,
                    interval_ms=100
                )
                futures[f] = (target, "fast", info)

            for f in as_completed(futures):
                tgt, probe_type, info = futures[f]
                try:
                    res = f.result()
                except Exception as e:
                    res = {
                        "healthy": False,
                        "packets_sent": count if probe_type == "full" else 2,
                        "packets_received": 0,
                        "packet_loss": 100.0,
                        "latency_ms": None,
                        "jitter_ms": 0.0,
                        "reason": str(e)
                    }

                with self._target_lock:
                    if probe_type == "full":
                        self._target_probe_cache[tgt] = res
                        self._target_last_probe_time[tgt] = curr_time
                        self._target_last_fast_check[tgt] = curr_time

                        # Update target-level sample history
                        if tgt not in self._target_history:
                            self._target_history[tgt] = {
                                "samples": [],
                                "consecutive_fails": 0,
                                "consecutive_success": 0
                            }
                        thist = self._target_history[tgt]
                        sample = summarize_cycle(res, curr_time)
                        thist["samples"].append(sample)
                        thist["samples"] = [s for s in thist["samples"] if (curr_time - float(s[0])) <= window_sec]
                    else:
                        # Fast liveness check (2-ping test every 15s)
                        self._target_last_fast_check[tgt] = curr_time
                        if res.get("packets_received", 0) == 0:
                            # Immediate Hard Outage: mark dead, invalidate cache, set 100% loss
                            fail_res = {
                                "healthy": False,
                                "packets_sent": res.get("packets_sent", 2),
                                "packets_received": 0,
                                "packet_loss": 100.0,
                                "latency_ms": None,
                                "jitter_ms": 0.0,
                                "reason": "Fast liveness check failed (unreachable)"
                            }
                            self._target_probe_cache[tgt] = fail_res
                            self._target_last_probe_time[tgt] = 0.0
                            if tgt not in self._target_history:
                                self._target_history[tgt] = {
                                    "samples": [],
                                    "consecutive_fails": 0,
                                    "consecutive_success": 0
                                }
                            thist = self._target_history[tgt]
                            thist["consecutive_fails"] = int(thist.get("consecutive_fails", 0)) + 1
                            thist["consecutive_success"] = 0
                            sample = summarize_cycle(fail_res, curr_time)
                            thist["samples"].append(sample)
                            thist["samples"] = [s for s in thist["samples"] if (curr_time - float(s[0])) <= window_sec]
                            thist["status"] = "failed"
                        else:
                            # Target is alive; if previously marked dead, immediately unmark dead state and trigger full probe
                            was_dead = not self._target_probe_cache.get(tgt, {}).get("healthy", True)
                            if was_dead:
                                self._target_probe_cache[tgt] = res
                                self._target_last_probe_time[tgt] = 0.0
                                if tgt in self._target_history:
                                    thist = self._target_history[tgt]
                                    thist["consecutive_fails"] = 0
                                    thist["consecutive_success"] = 1
                                    sample = summarize_cycle(res, curr_time)
                                    thist["samples"].append(sample)
                                    thist["samples"] = [s for s in thist["samples"] if (curr_time - float(s[0])) <= window_sec]

        # Compute rolling window aggregates for every valid target
        with self._target_lock:
            for target in unique_targets:
                if target in self._target_probe_cache and target in self._target_history:
                    thist = self._target_history[target]
                    samples = thist.get("samples", [])
                    short_samples = samples[-3:]
                    short_agg = aggregate_window(short_samples, window_seconds=40.0, now=curr_time)
                    long_agg = aggregate_window(samples, window_seconds=window_sec, now=curr_time)
                    last_loss = float(self._target_probe_cache[target].get("packet_loss", 0.0))
                    lossy_cycles = sum(1 for s in short_samples if isinstance(s, (list, tuple)) and len(s) >= 3 and int(s[2]) < int(s[1]))
                    burst_dead = (last_loss >= 100.0 and not self._target_probe_cache[target].get("healthy", True))
                    status = classify_status(
                        short_loss=short_agg["packet_loss"],
                        long_loss=long_agg["packet_loss"],
                        last_cycle_loss=last_loss,
                        burst_confirmed_dead=burst_dead,
                        route_invalid=False,
                        max_acceptable_loss=max_loss,
                        critical_loss=crit_loss,
                        lossy_cycles=lossy_cycles
                    )
                    thist["short_agg"] = short_agg
                    thist["long_agg"] = long_agg
                    thist["status"] = status
                    thist["last_cycle_loss"] = last_loss
                    thist["lossy_cycles"] = lossy_cycles

        # Build consolidated probe_cache indexed by target IP and (target, iface)
        results: Dict[Any, Dict[str, Any]] = {}
        for target, res in invalid_results.items():
            results[target] = res
            results[(target, None)] = res

        with self._target_lock:
            for target in unique_targets:
                if target in self._target_probe_cache:
                    c_res = dict(self._target_probe_cache[target])
                    results[target] = c_res
                    iface = unique_targets[target].get("iface")
                    results[(target, iface)] = c_res
                    results[(target, None)] = c_res

        return results

    def _persist_active_priorities(self, changed_rule_ids: Dict[str, int]) -> bool:
        if not changed_rule_ids:
            return True
        with self.lock:
            try:
                on_disk_cfg = {}
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        on_disk_cfg = json.load(f)
                if not isinstance(on_disk_cfg, dict):
                    on_disk_cfg = dict(self.config)

                rules = on_disk_cfg.get("rules", [])
                for r in rules:
                    r_id = r.get("id")
                    if r_id in changed_rule_ids:
                        r["active_priority"] = changed_rule_ids[r_id]

                self.config["rules"] = rules
                return self._save_config_unlocked()
            except Exception as e:
                print(f"[ERROR] Failed to persist active priorities: {e}", file=sys.stderr)
                return False

    def evaluate_rule(self, rule: Dict[str, Any], probe_cache: Optional[Dict[Tuple[str, Optional[str]], Dict[str, Any]]] = None) -> bool:
        rule_id = rule.get("id", f"rule-{rule.get('port')}")
        destinations = sorted(rule.get("destinations", []), key=lambda x: x.get("priority", 99))
        if not destinations:
            return False

        if rule_id not in self.runtime_state["rules_state"]:
            self.runtime_state["rules_state"][rule_id] = {
                "active_priority": rule.get("active_priority", 1),
                "dest_stats": {},
                "last_switch_time": 0,
                "switch_history": [],
                "is_flapping": False,
                "cooldown_remaining": 0,
                "hold_remaining": 0,
                "switch_pending_seconds": 0,
                "switch_candidate": None,
                "switch_streak_start": 0.0,
                "last_switch_reason": "init"
            }

        rule_state = self.runtime_state["rules_state"][rule_id]
        force_override = rule.get("force_override", 0)

        # Reconcile if web panel modified active_priority directly
        cfg_active = rule.get("active_priority")
        if cfg_active is not None and cfg_active != rule_state.get("active_priority"):
            rule_state["active_priority"] = cfg_active
            rule_state["last_switch_time"] = time.time()
            rule_state["switch_candidate"] = None
            rule_state["switch_streak_start"] = 0.0

        current_active = rule_state.get("active_priority", rule.get("active_priority", 1))

        # Reset hold/streak if admin changed the override mode
        prev_force_override = rule_state.get("last_force_override", force_override)
        override_mode_changed = (prev_force_override != force_override)
        if override_mode_changed:
            rule_state["last_switch_time"] = 0
            rule_state["cooldown_remaining"] = 0
            rule_state["hold_remaining"] = 0
            rule_state["switch_candidate"] = None
            rule_state["switch_streak_start"] = 0.0
        rule_state["last_force_override"] = force_override

        fast_failover = bool(self.config.get("fast_failover_enabled", True))
        max_loss = float(self.config.get("max_acceptable_loss", 25))
        crit_loss = float(self.config.get("critical_loss_percent", 30))
        fail_thresh = int(self.config.get("failure_threshold", 3))
        loss_weight = float(self.config.get("loss_penalty_weight", 20))
        jitter_weight = float(self.config.get("jitter_penalty_weight", 2))
        window_sec = float(self.config.get("quality_window_seconds", 300))
        min_hold = float(self.config.get("min_hold_seconds", 600))
        cooldown = float(self.config.get("cooldown_seconds", 60))
        priority_bias = float(self.config.get("priority_bias_ms", 0))

        now = time.time()
        last_switch = float(rule_state.get("last_switch_time", 0))
        time_since_switch = max(0.0, now - last_switch)

        # Prune old switch history (>30 minutes)
        switches = [t for t in rule_state.get("switch_history", []) if now - t < 1800]
        rule_state["switch_history"] = switches
        rule_state["is_flapping"] = (len(switches) >= 3)
        if rule_state["is_flapping"]:
            min_hold = min(3600.0, min_hold * 2.0)
            cooldown = min(600.0, cooldown * 2.0)

        rule_state["hold_remaining"] = max(0, round(min_hold - time_since_switch)) if (time_since_switch < min_hold) else 0
        is_post_crit = (rule_state.get("last_switch_reason") == "critical")
        rule_state["cooldown_remaining"] = max(0, round(cooldown - time_since_switch)) if (is_post_crit and time_since_switch < cooldown) else 0

        dest_metrics: Dict[int, Dict[str, Any]] = {}

        for dest in destinations:
            prio = dest.get("priority", 1)
            dest_key = f"prio_{prio}"
            if dest_key not in rule_state["dest_stats"]:
                rule_state["dest_stats"][dest_key] = {
                    "consecutive_fails": 0,
                    "consecutive_success": 0,
                    "status": "unknown",
                    "latency_ms": None,
                    "jitter_ms": 0.0,
                    "packet_loss": 0,
                    "short_loss": 0,
                    "composite_score": 999.0,
                    "fill_ratio": 0.0,
                    "fingerprint": "",
                    "samples": []
                }

            stat = rule_state["dest_stats"][dest_key]
            target = str(dest.get("target", "")).strip().strip("[]")
            clean_tgt = (sanitize_target_host(target) or target).lower()
            is_valid, iface, route_err = self._validate_probe_route(dest)

            # Check destination fingerprint: if target/iface changed, reset samples
            curr_fp = f"{dest.get('type')}:{clean_tgt}:{dest.get('port')}:{iface}"
            if stat.get("fingerprint") != curr_fp:
                stat["fingerprint"] = curr_fp
                stat["samples"] = []

            # Retrieve probe from cache or execute on demand
            probe_key = (clean_tgt, iface)
            if probe_cache is not None and probe_key in probe_cache:
                check_res = probe_cache[probe_key]
            elif probe_cache is not None and (target, iface) in probe_cache:
                check_res = probe_cache[(target, iface)]
            elif probe_cache is not None and clean_tgt in probe_cache:
                check_res = probe_cache[clean_tgt]
            elif probe_cache is not None and target in probe_cache:
                check_res = probe_cache[target]
            elif probe_cache is not None and (clean_tgt, None) in probe_cache:
                check_res = probe_cache[(clean_tgt, None)]
            elif probe_cache is not None and (target, None) in probe_cache:
                check_res = probe_cache[(target, None)]
            else:
                try:
                    check_res = self.check_destination(
                        dest,
                        rule_port=dest.get("port") or rule.get("port"),
                        protocol=dest.get("protocol") or rule.get("protocol"),
                        count=int(self.config.get("probe_count", 10))
                    )
                except TypeError:
                    check_res = self.check_destination(
                        dest,
                        rule_port=dest.get("port") or rule.get("port"),
                        protocol=dest.get("protocol") or rule.get("protocol")
                    )

            # If active priority destination suffered 100% loss in this cycle:
            # Run adaptive fast burst to confirm total outage in < 1s
            is_active_dest = (prio == current_active)
            burst_confirmed_dead = False
            last_cycle_loss = float(check_res.get("packet_loss", 0.0))

            if is_active_dest and last_cycle_loss >= 100.0 and fast_failover and is_valid:
                burst_dest = dict(dest, tunnel_iface=iface) if iface and not dest.get("tunnel_iface") else dest
                burst_res = self._fast_confirm_burst(burst_dest, rule_port=rule.get("port"), count=int(self.config.get("fast_probe_burst", 5)))
                if burst_res.get("all_failed"):
                    burst_confirmed_dead = True
                    stat["consecutive_fails"] = max(stat.get("consecutive_fails", 0), fail_thresh)

            if "reason" in check_res and check_res["reason"]:
                stat["reason"] = check_res["reason"]

            # Store compact sample [ts, sent, recv, avg, jit]
            # If target-level shared history exists, use target-level metrics
            has_target_history = False
            shared_status = None
            with self._target_lock:
                thist = self._target_history.get(clean_tgt)
                if thist and "short_agg" in thist:
                    has_target_history = True
                    short_agg = dict(thist["short_agg"])
                    long_agg = dict(thist["long_agg"])
                    stat["samples"] = list(thist.get("samples", []))
                    lossy_cycles = thist.get("lossy_cycles", 0)
                    shared_status = thist.get("status")

            if not has_target_history:
                sample = summarize_cycle(check_res, now)
                if "samples" not in stat or not isinstance(stat["samples"], list):
                    stat["samples"] = []
                stat["samples"].append(sample)

                # Prune samples older than quality_window_seconds
                stat["samples"] = [s for s in stat["samples"] if (now - float(s[0])) <= window_sec]

                # Aggregate short window (last 3 samples or ~30s) and long window (window_sec)
                short_samples = stat["samples"][-3:]
                short_agg = aggregate_window(short_samples, window_seconds=40.0, now=now)
                long_agg = aggregate_window(stat["samples"], window_seconds=window_sec, now=now)
                lossy_cycles = sum(1 for s in short_samples if isinstance(s, (list, tuple)) and len(s) >= 3 and int(s[2]) < int(s[1]))

            # Classify status
            is_route_invalid = (not is_valid and not check_res.get("healthy", False))
            if burst_confirmed_dead or is_route_invalid:
                status = classify_status(
                    short_loss=short_agg["packet_loss"],
                    long_loss=long_agg["packet_loss"],
                    last_cycle_loss=last_cycle_loss,
                    burst_confirmed_dead=burst_confirmed_dead,
                    route_invalid=is_route_invalid,
                    max_acceptable_loss=max_loss,
                    critical_loss=crit_loss,
                    lossy_cycles=lossy_cycles
                )
            elif has_target_history and shared_status:
                status = shared_status
            else:
                status = classify_status(
                    short_loss=short_agg["packet_loss"],
                    long_loss=long_agg["packet_loss"],
                    last_cycle_loss=last_cycle_loss,
                    burst_confirmed_dead=burst_confirmed_dead,
                    route_invalid=is_route_invalid,
                    max_acceptable_loss=max_loss,
                    critical_loss=crit_loss,
                    lossy_cycles=lossy_cycles
                )

            # Compute short and long composite scores
            bias = priority_bias if prio == 1 else 0.0
            short_score = compute_score(
                avg_lat=short_agg["avg_latency_ms"],
                jitter=short_agg["jitter_ms"],
                loss_pct=short_agg["packet_loss"],
                loss_weight=loss_weight,
                jitter_weight=jitter_weight,
                priority_bias=bias
            )
            long_score = compute_score(
                avg_lat=long_agg["avg_latency_ms"],
                jitter=long_agg["jitter_ms"],
                loss_pct=long_agg["packet_loss"],
                loss_weight=loss_weight,
                jitter_weight=jitter_weight,
                priority_bias=bias
            )

            stat["status"] = status
            stat["packet_loss"] = long_agg["packet_loss"]
            stat["short_loss"] = short_agg["packet_loss"]
            stat["latency_ms"] = long_agg["avg_latency_ms"] if long_agg["avg_latency_ms"] is not None else check_res.get("latency_ms")
            stat["jitter_ms"] = long_agg["jitter_ms"]
            stat["composite_score"] = long_score
            stat["fill_ratio"] = long_agg["fill_ratio"]

            if status == "healthy":
                stat["consecutive_fails"] = 0
                stat["consecutive_success"] = stat.get("consecutive_success", 0) + 1
            else:
                stat["consecutive_success"] = 0
                stat["consecutive_fails"] = stat.get("consecutive_fails", 0) + 1

            dest_metrics[prio] = {
                "status": status,
                "short_loss": short_agg["packet_loss"],
                "long_loss": long_agg["packet_loss"],
                "short_score": short_score,
                "long_score": long_score,
                "fill_ratio": long_agg["fill_ratio"]
            }

        # ── Decision Logic ──
        target_active = current_active
        force_reset_occurred = False
        decision_reason = "hold"
        pending_sec = 0

        if override_mode_changed:
            if force_override == 0 and prev_force_override > 0:
                target_active = pick_best_now(rule_state.get("dest_stats", {}), rule.get("destinations", []), current_active)
                decision_reason = "auto_reset"
                force_reset_occurred = True

        if force_override > 0:
            forced_stat = rule_state["dest_stats"].get(f"prio_{force_override}", {})
            is_forced_down = (forced_stat.get("status") in ("failed", "critical") or forced_stat.get("packet_loss", 0) >= 100)
            if is_forced_down:
                print(f"[WARN] Forced Priority #{force_override} for rule '{rule_id}' is down/critical. Falling back to Auto Failover.")
                rule["force_override"] = 0
                force_override = 0
                rule_state["last_force_override"] = 0
                rule_state["last_switch_time"] = 0
                rule_state["cooldown_remaining"] = 0
                rule_state["hold_remaining"] = 0
                target_active = pick_best_now(rule_state.get("dest_stats", {}), rule.get("destinations", []), current_active)
                decision_reason = "auto_fallback"
                force_reset_occurred = True
            else:
                target_active = force_override
                decision_reason = "override"
                rule_state["last_switch_time"] = 0
                rule_state["cooldown_remaining"] = 0
                rule_state["hold_remaining"] = 0
                rule_state["switch_candidate"] = None
                rule_state["switch_streak_start"] = 0.0

        if force_override == 0 and not force_reset_occurred:
            target_active, decision_reason, pending_sec = decide_route(
                rule_state=rule_state,
                dest_metrics=dest_metrics,
                current_active=current_active,
                config=self.config,
                now=now
            )

        rule_state["switch_pending_seconds"] = pending_sec
        rule_state["candidate_priority"] = rule_state.get("switch_candidate")

        # Flap detection: 3 or more switches in 10 minutes
        recent_switches = [t for t in rule_state.get("switch_history", []) if (now - t) <= 600.0]
        rule_state["switch_history"] = recent_switches
        rule_state["is_flapping"] = (len(recent_switches) >= 3)

        state_changed = (target_active != current_active) or force_reset_occurred

        if state_changed:
            rule_state["last_switch_time"] = now
            rule_state["last_switch_reason"] = decision_reason
            rule_state["switch_history"].append(now)
            rule_state["active_priority"] = target_active
            rule["active_priority"] = target_active
            is_crit = (decision_reason == "critical")
            self._hot_toggle_rule_priority(rule, old_prio=current_active, new_prio=target_active, is_critical=is_crit)

        # Calculate remaining hold and cooldown for UI display
        time_since_switch = max(0.0, now - float(rule_state.get("last_switch_time", 0.0)))
        min_hold = float(self.config.get("min_hold_seconds", 600))
        cooldown = float(self.config.get("cooldown_seconds", 60))
        if rule_state.get("is_flapping"):
            min_hold = min(3600.0, min_hold * 2.0)
            cooldown = min(600.0, cooldown * 2.0)

        if rule_state.get("last_switch_time", 0.0) > 0:
            rule_state["hold_remaining"] = max(0, round(min_hold - time_since_switch))
            rule_state["cooldown_remaining"] = max(0, round(cooldown - time_since_switch))
        else:
            rule_state["hold_remaining"] = 0
            rule_state["cooldown_remaining"] = 0

        return state_changed

    def _get_rules_fingerprint(self) -> str:
        rules = self.config.get("rules", [])
        return json.dumps([
            {
                "id": r.get("id"),
                "port": r.get("port"),
                "protocol": r.get("protocol"),
                "active_priority": r.get("active_priority"),
                "force_override": r.get("force_override", 0),
                "destinations": r.get("destinations")
            } for r in rules
        ], sort_keys=True)

    def sync_firewall_and_proxies(self) -> Tuple[bool, List[str]]:
        wan_iface = self._detect_wan_interface()
        haproxy_entries = []
        udp_entries = []
        nginx_entries = []
        nft_dnat_rules = []

        rules = self.config.get("rules", [])
        for rule in rules:
            port = rule.get("port")
            proto = str(rule.get("protocol", "both")).lower()
            active_prio = rule.get("active_priority", 1)

            dest = None
            for d in rule.get("destinations", []):
                if d.get("priority") == active_prio:
                    dest = d
                    break
            if not dest and rule.get("destinations"):
                dest = rule["destinations"][0]
            if not dest:
                continue

            target = str(dest.get("target", "")).strip().strip("[]")
            target_port = dest.get("port", port)
            dest_type = dest.get("type", "haproxy")
            target_str = f"[{target}]:{target_port}" if ":" in target else f"{target}:{target_port}"
            comment_clean = str(dest.get("comment") or rule.get("id") or f"Port {port}").replace("\n", " ").replace("\r", "")

            if dest_type == "haproxy":
                send_proxy = bool(dest.get("proxy_protocol", False) or dest.get("send_proxy", False))
                proxy_flag = " send-proxy-v2" if send_proxy else ""
                binds = [f"bind *:{port}"]
                if self._is_ipv6_supported():
                    binds.append(f"bind [::]:{port} v6only")
                bind_str = "\n    ".join(binds)

                if proto in ("tcp", "both"):
                    haproxy_entries.append(
                        f"listen fwd_{port}\n"
                        f"    {bind_str}\n"
                        f"    server srv_{port} {target_str}{proxy_flag}\n"
                    )
                if proto in ("udp", "both"):
                    pp_ngx = " proxy_protocol on;" if send_proxy else ""
                    udp_listens = [f"listen {port} udp reuseport;"]
                    if self._is_ipv6_supported():
                        udp_listens.append(f"listen [::]:{port} udp ipv6only=on reuseport;")
                    udp_listens_str = " ".join(udp_listens)
                    nginx_entries.append(
                        f"    # [UDP for HAProxy {comment_clean}]\n"
                        f"    server {{ {udp_listens_str} proxy_pass {target_str};{pp_ngx} proxy_timeout 60s; }}"
                    )
            elif dest_type == "nginx":
                send_proxy = bool(dest.get("proxy_protocol", False) or dest.get("send_proxy", False))
                pp_ngx = " proxy_protocol on;" if send_proxy else ""

                tcp_listens = [f"listen {port} reuseport so_keepalive=on;"]
                udp_listens = [f"listen {port} udp reuseport;"]
                if self._is_ipv6_supported():
                    tcp_listens.append(f"listen [::]:{port} ipv6only=on reuseport so_keepalive=on;")
                    udp_listens.append(f"listen [::]:{port} udp ipv6only=on reuseport;")

                if proto in ("both", ""):
                    listens_str = " ".join(tcp_listens + udp_listens)
                    nginx_entries.append(
                        f"    # [{comment_clean}]\n"
                        f"    server {{ {listens_str} proxy_pass {target_str};{pp_ngx} }}"
                    )
                elif proto == "tcp":
                    listens_str = " ".join(tcp_listens)
                    nginx_entries.append(
                        f"    # [{comment_clean}]\n"
                        f"    server {{ {listens_str} proxy_pass {target_str};{pp_ngx} }}"
                    )
                elif proto == "udp":
                    listens_str = " ".join(udp_listens)
                    nginx_entries.append(
                        f"    # [{comment_clean}]\n"
                        f"    server {{ {listens_str} proxy_pass {target_str};{pp_ngx} proxy_timeout 60s; }}"
                    )
            elif dest_type == "nftables":
                is_ipv6 = ":" in target
                dnat_target = f"[{target}]:{target_port}" if is_ipv6 else f"{target}:{target_port}"
                if proto in ("tcp", "both"):
                    nft_dnat_rules.append(
                        f'        iifname "{wan_iface}" tcp dport {port} dnat to {dnat_target}'
                    )
                if proto in ("udp", "both"):
                    nft_dnat_rules.append(
                        f'        iifname "{wan_iface}" udp dport {port} dnat to {dnat_target}'
                    )

        errors: List[str] = []
        ok_nft, err_nft = self._apply_nftables(nft_dnat_rules)
        if not ok_nft and err_nft:
            errors.append(err_nft)

        ok_ha, err_ha = self._apply_haproxy(haproxy_entries, udp_entries)
        if not ok_ha and err_ha:
            errors.append(err_ha)

        ok_ngx, err_ngx = self._apply_nginx(nginx_entries)
        if not ok_ngx and err_ngx:
            errors.append(err_ngx)

        self._save_state_file()
        self._last_applied_rules = self._get_rules_fingerprint()
        return len(errors) == 0, errors

    def _apply_nftables(self, dnat_rules: List[str]) -> Tuple[bool, Optional[str]]:
        rule_ports = set()
        for r in self.config.get("rules", []):
            try:
                p = int(r.get("port", 0))
                if p > 0:
                    rule_ports.add(p)
            except (ValueError, TypeError):
                pass
        ok, err, new_content = apply_nftables(dnat_rules, rule_ports=rule_ports, last_content=self._last_nft_content)
        if ok:
            self._last_nft_content = new_content
            self.runtime_state["active_services"]["nftables"] = bool(dnat_rules)
        return ok, err

    def _apply_haproxy(self, haproxy_entries: List[str], udp_entries: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        ok, err = apply_haproxy(haproxy_entries, conf_path=HAPROXY_CONF_PATH)
        if ok:
            self.runtime_state["active_services"]["haproxy"] = bool(haproxy_entries)
        return ok, err

    def _apply_nginx(self, nginx_entries: List[str]) -> Tuple[bool, Optional[str]]:
        ok, err = apply_nginx(nginx_entries, conf_path=NGINX_CONF_PATH)
        if ok:
            self.runtime_state["active_services"]["nginx"] = bool(nginx_entries)
        return ok, err

    def _save_state_file(self) -> None:
        try:
            rt_to_save = dict(self.runtime_state)
            paths = [self.state_file_path]
            if self.state_file_path == STATE_FILE_PATH:
                paths.append(LEGACY_STATE_FILE_PATH)

            if not rt_to_save.get("rules_state"):
                for s_path in paths:
                    if os.path.exists(s_path):
                        try:
                            with open(s_path, "r", encoding="utf-8") as rf:
                                existing_state = json.load(rf)
                                if isinstance(existing_state, dict):
                                    existing_rt = existing_state.get("runtime") if isinstance(existing_state.get("runtime"), dict) else existing_state
                                    live_rules = existing_rt.get("rules_state", {})
                                    if live_rules:
                                        rt_to_save["rules_state"] = live_rules
                                    if "uptime_started" in existing_rt:
                                        rt_to_save["uptime_started"] = existing_rt["uptime_started"]
                                    break
                        except Exception:
                            pass

            for s_path in paths:
                s_dir = os.path.dirname(s_path)
                if s_path == LEGACY_STATE_FILE_PATH and not os.path.exists(s_dir):
                    continue
                if s_dir:
                    os.makedirs(s_dir, exist_ok=True)
                tmp_path = f"{s_path}.tmp.{os.getpid()}"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "config": self.config,
                        "runtime": rt_to_save,
                        "updated_at": time.time()
                    }, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, s_path)
        except Exception:
            pass

    def _write_pid_file(self) -> None:
        for candidate in PID_FILE_CANDIDATES:
            try:
                os.makedirs(os.path.dirname(candidate), exist_ok=True)
                with open(candidate, "w", encoding="utf-8") as pf:
                    pf.write(str(os.getpid()))
                self._pid_path = candidate
                break
            except Exception:
                continue

    def _remove_pid_file(self) -> None:
        if self._pid_path:
            try:
                if os.path.exists(self._pid_path):
                    os.remove(self._pid_path)
            except Exception:
                pass
            self._pid_path = None

    def run_loop(self) -> None:
        self.running = True
        print("[INFO] XForwarder Core Engine started.")
        self._write_pid_file()

        if hasattr(signal, "SIGUSR1"):
            try:
                signal.signal(signal.SIGUSR1, lambda sig, frame: self._wake_event.set())
            except Exception:
                pass

        self.sync_firewall_and_proxies()

        if LossMonitorScheduler and not self._loss_scheduler:
            self._loss_scheduler = LossMonitorScheduler(config_loader_fn=self.load_config)
            self._loss_scheduler.start()

        if TrafficCollector and not self._traffic_collector:
            try:
                self._traffic_collector = TrafficCollector()
            except Exception:
                pass

        try:
            while self.running:
                try:
                    self.load_config()
                    rules = self.config.get("rules", [])

                    current_rule_ids = {r.get("id") for r in rules if r.get("id")}
                    stale_ids = [rid for rid in list(self.runtime_state["rules_state"].keys()) if rid not in current_rule_ids]
                    for rid in stale_ids:
                        del self.runtime_state["rules_state"][rid]

                    probe_cache = self._probe_all_destinations(rules)

                    changed_priorities: Dict[str, int] = {}
                    for rule in rules:
                        r_id = rule.get("id", f"rule-{rule.get('port')}")
                        if self.evaluate_rule(rule, probe_cache=probe_cache):
                            changed_priorities[r_id] = rule.get("active_priority", 1)

                    self.runtime_state["last_check_timestamp"] = time.time()

                    now_ts = time.time()
                    if self._traffic_collector and (now_ts - self._last_traffic_cycle >= 30.0):
                        try:
                            rule_ports_list = [int(r["port"]) for r in rules if r.get("port")]
                            self._traffic_collector.collect_cycle(ports=rule_ports_list)
                            self._last_traffic_cycle = now_ts
                        except Exception:
                            pass

                    config_changed = (self._get_rules_fingerprint() != self._last_applied_rules)

                    if changed_priorities or config_changed:
                        print("[INFO] Routing state or configuration change detected. Synchronizing routing layer...")
                        if changed_priorities:
                            self._persist_active_priorities(changed_priorities)
                        self.sync_firewall_and_proxies()
                        self._save_state_file()
                    else:
                        self._save_state_file()

                    interval = int(self.config.get("check_interval_seconds", 8))
                    self._wake_event.wait(timeout=max(3, interval))
                    self._wake_event.clear()
                except Exception as e:
                    print(f"[ERROR] Exception in xforwarder loop: {e}", file=sys.stderr)
                    self._wake_event.wait(timeout=5)
                    self._wake_event.clear()
        finally:
            if self._loss_scheduler:
                self._loss_scheduler.stop()
                self._loss_scheduler = None
            if self._probe_executor:
                try:
                    self._probe_executor.shutdown(wait=False)
                except Exception:
                    pass
                self._probe_executor = None
            self._remove_pid_file()

    def stop(self) -> None:
        self.running = False
        if self._loss_scheduler:
            self._loss_scheduler.stop()
            self._loss_scheduler = None
        if self._probe_executor:
            try:
                self._probe_executor.shutdown(wait=False)
            except Exception:
                pass
            self._probe_executor = None
        self._wake_event.set()
        self._remove_pid_file()


def sync_system_rules(max_retries: int = 2, delay_between_retries: float = 0.5, config_path: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Synchronizes firewall (NFTables) and proxy layers (HAProxy, Nginx) on demand.
    Automatically retries up to max_retries times if a transient service or syntax failure occurs.
    Returns (success: bool, errors: List[str]).
    """
    engine = XForwarderEngine(config_path=config_path)
    last_errors: List[str] = []
    for attempt in range(max_retries + 1):
        engine.load_config()
        ok, errors = engine.sync_firewall_and_proxies()
        if ok:
            return True, []
        last_errors = errors
        if attempt < max_retries:
            time.sleep(delay_between_retries)
    return False, last_errors


ForwardManagerEngine = XForwarderEngine

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--migrate", "-m"):
        cfg_override = sys.argv[2] if len(sys.argv) > 2 else None
        engine = XForwarderEngine(config_path=cfg_override)
        engine.save_config()
        rule_count = len(engine.config.get("rules", []))
        print(f"[OK] Configuration migrated and normalized successfully.")
        print(f"[OK] Target config: {engine.config_path}")
        print(f"[OK] Preserved {rule_count} port forwarding rule(s).")
        sys.exit(0)

    engine = XForwarderEngine()

    def handle_sig(sig, frame):
        print("\n[INFO] Terminating XForwarder Engine...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)
    engine.run_loop()

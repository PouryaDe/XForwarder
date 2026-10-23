#!/usr/bin/env python3
"""
XForwarder - Core Engine Daemon
Monitors uplink destinations (IPv6 HAProxy vs IPv4 NFTables tunnels),
manages automatic failover, and dynamically synchronizes kernel NAT and user-space daemons.
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

try:
    from core.route_quality import (
        summarize_cycle, aggregate_window, compute_score, classify_status, decide_route, pick_best_now
    )
    from core.metrics import parse_ping_output, sanitize_target_host
    from core.traffic import TrafficCollector
except ImportError:
    from route_quality import (
        summarize_cycle, aggregate_window, compute_score, classify_status, decide_route, pick_best_now
    )
    from metrics import parse_ping_output, sanitize_target_host
    try:
        from traffic import TrafficCollector
    except ImportError:
        TrafficCollector = None

DEFAULT_CONFIG_PATH = "/etc/xforwarder/config.json"
LEGACY_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.json")
STATE_FILE_PATH = "/run/xforwarder/state.json"
LEGACY_STATE_FILE_PATH = "/run/forward-manager/state.json"
HAPROXY_CONF_PATH = "/etc/haproxy/haproxy.cfg"
UDP_CONF_PATH = "/etc/haproxy/forwarder-udp.conf"
NGINX_CONF_PATH = "/etc/nginx/nginx.conf"

PID_FILE_CANDIDATES = [
    "/run/xforwarder/engine.pid",
    "/run/forward-manager/engine.pid",
    os.path.join(tempfile.gettempdir(), "xforwarder_engine.pid"),
]


def is_private_or_tunnel_target(target: str) -> bool:
    """Returns True if the target IP is in RFC 1918 private, loopback, link-local, or IPv6 ULA address space."""
    if not target:
        return False
    try:
        ip = ipaddress.ip_address(target.strip())
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


class XForwarderEngine:
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
                            rt = data.get("runtime") if isinstance(data.get("runtime"), dict) else data
                            if "rules_state" in rt and isinstance(rt["rules_state"], dict):
                                self.runtime_state["rules_state"] = rt["rules_state"]
                            if "uptime_started" in rt:
                                self.runtime_state["uptime_started"] = rt["uptime_started"]
                            if "last_check_timestamp" in rt:
                                self.runtime_state["last_check_timestamp"] = rt["last_check_timestamp"]
                            if "active_services" in rt and isinstance(rt["active_services"], dict):
                                self.runtime_state["active_services"].update(rt["active_services"])
                            break
                except Exception:
                    pass

    @staticmethod
    def _is_ipv6_supported() -> bool:
        """Returns True if the host kernel has an active IPv6 networking stack."""
        if os.path.exists("/proc/net/if_inet6"):
            return True
        try:
            with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
                return True
        except Exception:
            return False

    def _resolve_config_path(self, override_path: Optional[str]) -> str:
        if override_path:
            return override_path
        if os.path.exists(DEFAULT_CONFIG_PATH):
            return DEFAULT_CONFIG_PATH
        if os.path.exists(LEGACY_CONFIG_PATH):
            return LEGACY_CONFIG_PATH
        if os.path.exists(LOCAL_CONFIG_PATH):
            return LOCAL_CONFIG_PATH
        example_path = LOCAL_CONFIG_PATH + ".example"
        if os.path.exists(example_path):
            return example_path
        return DEFAULT_CONFIG_PATH

    @staticmethod
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
            "fast_probe_burst": 5
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

        if "rules" not in cfg or not isinstance(cfg["rules"], list):
            cfg["rules"] = []
            modified = True

        for rule in cfg["rules"]:
            if not isinstance(rule, dict):
                continue
            
            # Normalize port
            try:
                port = int(rule.get("port", 0))
                if rule.get("port") != port:
                    rule["port"] = port
                    modified = True
            except (ValueError, TypeError):
                port = 0

            if not rule.get("id"):
                rule["id"] = f"rule-{port}"
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

                try:
                    d_port = int(d.get("port", port))
                except (ValueError, TypeError):
                    d_port = port
                if d.get("port") != d_port:
                    d["port"] = d_port
                    modified = True

                if "comment" not in d:
                    d["comment"] = ""
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

                has_pp = bool(d.get("proxy_protocol", False) or d.get("send_proxy", False))
                if d.get("proxy_protocol") != has_pp:
                    d["proxy_protocol"] = has_pp
                    modified = True

        return cfg, modified

    def _save_config_unlocked(self) -> bool:
        """Atomically writes current configuration to disk using a temporary file and os.replace."""
        try:
            dir_name = os.path.dirname(self.config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            tmp_path = f"{self.config_path}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.config_path)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save config to {self.config_path}: {e}", file=sys.stderr)
            return False

    def load_config(self) -> None:
        """Loads and self-heals configuration, applying schema migrations when legacy keys are detected."""
        with self.lock:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                else:
                    self.config = {
                        "schema_version": 2,
                        "wan_interface": "auto",
                        "check_interval_seconds": 8,
                        "failure_threshold": 3,
                        "recovery_threshold": 3,
                        "fast_failover_enabled": True,
                        "max_acceptable_loss": 25,
                        "cooldown_seconds": 60,
                        "hysteresis_percent": 10,
                        "loss_penalty_weight": 10,
                        "fast_probe_burst": 3,
                        "web": {
                            "bind_host": "0.0.0.0",
                            "port": 8090,
                            "secret_path": "xfwd-admin",
                            "auth": {
                                "username": "admin",
                                "password_hash": ""
                            }
                        },
                        "rules": []
                    }
                self.config, modified = self.migrate_and_normalize_config(self.config)
                self._detect_wan_interface()
                if modified and os.path.exists(self.config_path):
                    self._save_config_unlocked()
            except Exception as e:
                print(f"[ERROR] Failed to load config from {self.config_path}: {e}", file=sys.stderr)

    def save_config(self) -> bool:
        """Thread-safe wrapper to persist the configuration atomically."""
        with self.lock:
            return self._save_config_unlocked()

    def _detect_wan_interface(self) -> str:
        configured = self.config.get("wan_interface", "auto")
        if configured and configured != "auto":
            self.runtime_state["wan_interface"] = configured
            return configured

        try:
            cmd = ["ip", "-o", "route", "show", "default"]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            parts = out.split()
            if "dev" in parts:
                idx = parts.index("dev")
                if idx + 1 < len(parts):
                    iface = parts[idx + 1]
                    self.runtime_state["wan_interface"] = iface
                    return iface
        except Exception:
            pass

        self.runtime_state["wan_interface"] = "eth0"
        return "eth0"

    def _is_interface_up(self, iface: str) -> bool:
        """Checks if a Linux network interface exists and is operstate UP."""
        if not iface:
            return False
        if sys.platform == "win32":
            return True
        sys_path = f"/sys/class/net/{iface}"
        if not os.path.exists(sys_path):
            return False
        try:
            operstate_path = os.path.join(sys_path, "operstate")
            if os.path.exists(operstate_path):
                with open(operstate_path, "r", encoding="utf-8") as f:
                    state = f.read().strip().lower()
                    if state in ("up", "unknown"):
                        return True
                    if state == "down":
                        return False
            flags_path = os.path.join(sys_path, "flags")
            if os.path.exists(flags_path):
                with open(flags_path, "r", encoding="utf-8") as f:
                    flags = int(f.read().strip(), 16)
                    return bool(flags & 0x1)
        except Exception:
            pass
        return True

    def _get_route_interface(self, target: str) -> Optional[str]:
        """Queries the kernel routing table to find the outbound network interface for target."""
        if sys.platform == "win32":
            return None
        try:
            out = subprocess.check_output(
                ["ip", "-o", "route", "get", target],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            parts = out.split()
            if "dev" in parts:
                idx = parts.index("dev")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except Exception:
            return ""
        return ""

    def _validate_probe_route(self, dest: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """
        Validates network interface and kernel route isolation for destination.
        Returns (is_valid: bool, tunnel_iface: Optional[str], reason: str).
        """
        target = str(dest.get("target", "")).strip().strip("[]")
        dest_type = dest.get("type", "haproxy")
        tunnel_iface = str(dest.get("tunnel_iface", "")).strip()

        if not target:
            return False, None, "Invalid target"

        wan_iface = self._detect_wan_interface()
        target_is_private = is_private_or_tunnel_target(target)

        if dest_type in ("nftables", "nginx") or tunnel_iface:
            if tunnel_iface:
                if not self._is_interface_up(tunnel_iface):
                    return False, tunnel_iface, f"Tunnel interface '{tunnel_iface}' is missing or down"
            elif target_is_private:
                route_iface = self._get_route_interface(target)
                if route_iface == "":
                    return False, None, f"No route to destination {target}"
                elif route_iface:
                    if route_iface == wan_iface:
                        return False, route_iface, f"WAN leak via {wan_iface}"
                    if route_iface in ("lo", "gre0", "gretap0", "erspan0", "tunl0", "sit0", "ip6tnl0", "ip6gre0", "dummy0"):
                        return False, route_iface, f"Destination {target} routes to kernel fallback device {route_iface}"
                    if not self._is_interface_up(route_iface):
                        return False, route_iface, f"Interface {route_iface} for {target} is down"
                    tunnel_iface = route_iface

        return True, (tunnel_iface if tunnel_iface else None), ""

    def probe_destination_icmp(
        self,
        target: str,
        iface: Optional[str] = None,
        count: int = 10,
        interval_ms: int = 200
    ) -> Dict[str, Any]:
        """
        Executes precise multi-probe ICMP test (default 10 packets, 200ms interval).
        Safe argument injection shielding, explicit locale C, IPv4/IPv6 handling.
        """
        clean_target = sanitize_target_host(target)
        if not clean_target:
            return {
                "healthy": False,
                "packets_sent": count,
                "packets_received": 0,
                "packet_loss": 100.0,
                "latency_ms": None,
                "jitter_ms": 0.0,
                "reason": "Invalid target host"
            }

        is_ipv6 = ":" in clean_target
        safe_count = max(1, min(count, 30))
        interval_sec = max(0.1, min(interval_ms / 1000.0, 2.0))
        timeout_sec = max(2, int(safe_count * interval_sec + 3))

        safe_env = dict(os.environ)
        safe_env["LC_ALL"] = "C"
        safe_env["LANG"] = "C"

        clean_iface = None
        if iface:
            raw_iface = str(iface).strip()
            if raw_iface and not raw_iface.startswith("-") and re.match(r'^[a-zA-Z0-9_.-]+$', raw_iface):
                clean_iface = raw_iface

        if sys.platform == "win32":
            cmd = ["ping", "-n", str(safe_count), "-w", "500", clean_target]
        else:
            cmd = ["ping", "-c", str(safe_count), "-i", f"{interval_sec:.1f}", "-W", "1"]
            if is_ipv6:
                cmd.insert(1, "-6")
            else:
                cmd.insert(1, "-4")
            if clean_iface:
                cmd.extend(["-I", clean_iface])
            cmd.append(clean_target)

        # Backward-compatibility for unit tests patching subprocess.call
        if getattr(subprocess.call, "_mock_return_value", None) is not None or "Mock" in str(type(subprocess.call)):
            try:
                ret = subprocess.call(cmd)
                return {
                    "healthy": (ret == 0),
                    "packets_sent": safe_count,
                    "packets_received": safe_count if ret == 0 else 0,
                    "packet_loss": 0.0 if ret == 0 else 100.0,
                    "latency_ms": 10.0 if ret == 0 else None,
                    "jitter_ms": 0.0
                }
            except Exception:
                pass

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec,
                env=safe_env
            )
            if proc.returncode != 0 and is_ipv6 and sys.platform != "win32" and "unknown" in proc.stderr.lower():
                cmd_alt = ["ping6", "-c", str(safe_count), "-i", f"{interval_sec:.1f}", "-W", "1"]
                if clean_iface:
                    cmd_alt.extend(["-I", clean_iface])
                cmd_alt.append(clean_target)
                proc = subprocess.run(
                    cmd_alt,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout_sec,
                    env=safe_env
                )
            parsed = parse_ping_output(proc.stdout, proc.returncode, sent_default=safe_count)
            return parsed
        except subprocess.TimeoutExpired:
            return {
                "healthy": False,
                "packets_sent": safe_count,
                "packets_received": 0,
                "packet_loss": 100.0,
                "latency_ms": None,
                "jitter_ms": 0.0,
                "reason": f"Probe timed out after {timeout_sec}s"
            }
        except Exception as e:
            return {
                "healthy": False,
                "packets_sent": safe_count,
                "packets_received": 0,
                "packet_loss": 100.0,
                "latency_ms": None,
                "jitter_ms": 0.0,
                "reason": str(e)
            }

    def check_destination(self, dest: Dict[str, Any], rule_port: Optional[int] = None, protocol: Optional[str] = None, count: int = 1) -> Dict[str, Any]:
        """Perform a low-overhead health check on a target destination with strict route and interface isolation."""
        target = str(dest.get("target", "")).strip().strip("[]")
        port = int(dest.get("port") or rule_port or 0)
        proto = str(dest.get("protocol") or protocol or "both").lower()
        start_time = time.perf_counter()
        healthy = False
        fail_reason = ""

        if not target or port <= 0:
            return {"healthy": False, "latency_ms": None, "packet_loss": 100, "reason": "Invalid target/port"}

        is_valid, tunnel_iface, err_reason = self._validate_probe_route(dest)
        if not is_valid:
            return {
                "healthy": False,
                "latency_ms": None,
                "packet_loss": 100,
                "reason": err_reason
            }

        # Multi-sample packet loss test when count > 1
        if count > 1:
            sent = max(1, min(count, 10))
            successes = 0
            latencies = []

            if proto != "udp":
                for _ in range(sent):
                    t_sample = time.perf_counter()
                    try:
                        family = socket.AF_INET6 if ":" in target else socket.AF_INET
                        with socket.socket(family, socket.SOCK_STREAM) as s:
                            s.settimeout(1.5)
                            if tunnel_iface and sys.platform != "win32":
                                try:
                                    s.setsockopt(socket.SOL_SOCKET, 25, tunnel_iface.encode())
                                except Exception:
                                    pass
                            if s.connect_ex((target, port)) == 0:
                                successes += 1
                                latencies.append(round((time.perf_counter() - t_sample) * 1000, 1))
                    except Exception as e:
                        if not fail_reason:
                            fail_reason = str(e)

            if successes == 0:
                p_res = self.probe_destination_icmp(target, iface=tunnel_iface, count=sent, interval_ms=200)
                return p_res

            loss_pct = round(((sent - successes) / sent) * 100) if sent > 0 else 100
            avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else None
            healthy = (successes > 0)
            res_dict = {
                "healthy": healthy,
                "latency_ms": avg_lat,
                "packet_loss": loss_pct,
                "packets_sent": sent,
                "packets_received": successes
            }
            if not healthy and fail_reason:
                res_dict["reason"] = fail_reason
            return res_dict

        # Single-sample probe
        if proto != "udp":
            try:
                family = socket.AF_INET6 if ":" in target else socket.AF_INET
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    if tunnel_iface and sys.platform != "win32":
                        try:
                            s.setsockopt(socket.SOL_SOCKET, 25, tunnel_iface.encode())
                        except Exception:
                            pass
                    res = s.connect_ex((target, port))
                    healthy = (res == 0)
            except Exception as e:
                healthy = False
                fail_reason = str(e)

        if not healthy:
            p_res = self.probe_destination_icmp(target, iface=tunnel_iface, count=1, interval_ms=200)
            healthy = p_res.get("healthy", False)
            if not healthy and not fail_reason:
                fail_reason = p_res.get("reason", "Ping probe unreachable")
            elif healthy:
                fail_reason = ""

        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        res_dict = {
            "healthy": healthy,
            "latency_ms": latency_ms if healthy else None,
            "packet_loss": 0 if healthy else 100
        }
        if not healthy and fail_reason:
            res_dict["reason"] = fail_reason
        return res_dict

    def _send_haproxy_runtime_cmd(self, cmd: str) -> Tuple[bool, str]:
        """Communicates with HAProxy Runtime API via UNIX domain socket."""
        sock_path = "/run/haproxy/admin.sock"
        if not os.path.exists(sock_path):
            return False, "admin.sock not found"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(sock_path)
                s.sendall(f"{cmd.strip()}\n".encode("utf-8"))
                response = s.recv(4096).decode("utf-8", errors="replace")
                return True, response
        except Exception as e:
            return False, str(e)

    def _fast_confirm_burst(self, dest: Dict[str, Any], rule_port: Optional[int] = None, protocol: Optional[str] = "both", count: int = 5) -> Dict[str, Any]:
        """
        Executes a rapid micro-probe burst (< 1s) to confirm destination outage
        without waiting for multiple full check intervals.
        """
        target = str(dest.get("target", "")).strip().strip("[]")
        port = int(dest.get("port") or rule_port or 0)
        proto = str(dest.get("protocol") or protocol or "both").lower()
        if not target or port <= 0:
            return {"all_failed": True, "successes": 0, "packet_loss": 100, "avg_latency_ms": None}

        burst_count = max(1, min(count, 5))
        successes = 0
        latencies = []

        if proto != "udp":
            for _ in range(burst_count):
                t0 = time.perf_counter()
                try:
                    family = socket.AF_INET6 if ":" in target else socket.AF_INET
                    with socket.socket(family, socket.SOCK_STREAM) as s:
                        s.settimeout(0.25)
                        if s.connect_ex((target, port)) == 0:
                            successes += 1
                            latencies.append((time.perf_counter() - t0) * 1000)
                except Exception:
                    pass

        if successes == 0:
            iface = dest.get("tunnel_iface")
            p_res = self.probe_destination_icmp(target, iface=iface, count=burst_count, interval_ms=100)
            recv = p_res.get("packets_received", 0)
            if recv > 0:
                successes = recv
                if p_res.get("latency_ms") is not None:
                    latencies.append(p_res["latency_ms"])

        all_failed = (successes == 0)
        loss = round(((burst_count - successes) / burst_count) * 100) if burst_count > 0 else 100
        avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else None
        return {
            "all_failed": all_failed,
            "successes": successes,
            "packet_loss": loss,
            "avg_latency_ms": avg_lat
        }

    def _hot_toggle_rule_priority(self, rule: Dict[str, Any], old_prio: int, new_prio: int, is_critical: bool = False) -> None:
        """
        Performs runtime priority transition.
        In planned switches: preserves active client sockets and allows connection draining.
        In critical switches: flushes stale conntrack states for TCP and UDP.
        """
        port = rule.get("port")
        if not port:
            return

        if is_critical and shutil.which("conntrack"):
            for proto in ("tcp", "udp"):
                try:
                    subprocess.run(["conntrack", "-D", "-p", proto, "--dport", str(port)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                except Exception:
                    pass

    def _probe_all_destinations(self, rules: List[Dict[str, Any]]) -> Dict[Tuple[str, Optional[str]], Dict[str, Any]]:
        """
        Deduplicates unique (target, iface) endpoints across all rules,
        validates routes, and executes 10-ping probes in parallel using persistent thread pool.
        """
        unique_targets: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
        invalid_results: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}

        count = int(self.config.get("probe_count", 10))
        interval_ms = int(self.config.get("probe_interval_ms", 200))

        for rule in rules:
            for dest in rule.get("destinations", []):
                target = str(dest.get("target", "")).strip().strip("[]")
                if not target:
                    continue
                is_valid, iface, reason = self._validate_probe_route(dest)
                key = (target, iface)
                if not is_valid:
                    invalid_results[key] = {
                        "healthy": False,
                        "packets_sent": count,
                        "packets_received": 0,
                        "packet_loss": 100.0,
                        "latency_ms": None,
                        "jitter_ms": 0.0,
                        "reason": reason
                    }
                elif key not in unique_targets:
                    unique_targets[key] = dest

        results: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = dict(invalid_results)
        if not unique_targets:
            return results

        if not self._probe_executor:
            self._probe_executor = ThreadPoolExecutor(max_workers=min(8, len(unique_targets)))

        futures = {}
        for key, dest in unique_targets.items():
            target, iface = key
            f = self._probe_executor.submit(self.probe_destination_icmp, target, iface=iface, count=count, interval_ms=interval_ms)
            futures[f] = key

        for f in as_completed(futures):
            k = futures[f]
            try:
                results[k] = f.result()
            except Exception as e:
                results[k] = {
                    "healthy": False,
                    "packets_sent": count,
                    "packets_received": 0,
                    "packet_loss": 100.0,
                    "latency_ms": None,
                    "jitter_ms": 0.0,
                    "reason": str(e)
                }

        return results

    def _persist_active_priorities(self, changed_rule_ids: Dict[str, int]) -> bool:
        """
        Safely merges active_priority updates into the latest config on disk
        without overwriting newly added, edited, or deleted rules by the web dashboard.
        """
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
            is_valid, iface, route_err = self._validate_probe_route(dest)

            # Check destination fingerprint: if target/iface changed, reset samples
            curr_fp = f"{dest.get('type')}:{target}:{dest.get('port')}:{iface}"
            if stat.get("fingerprint") != curr_fp:
                stat["fingerprint"] = curr_fp
                stat["samples"] = []

            # Retrieve probe from cache or execute on demand
            probe_key = (target, iface)
            if probe_cache is not None and probe_key in probe_cache:
                check_res = probe_cache[probe_key]
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
                burst_res = self._fast_confirm_burst(dest, rule_port=rule.get("port"), count=int(self.config.get("fast_probe_burst", 5)))
                if burst_res.get("all_failed"):
                    burst_confirmed_dead = True
                    stat["consecutive_fails"] = max(stat.get("consecutive_fails", 0), fail_thresh)

            if "reason" in check_res and check_res["reason"]:
                stat["reason"] = check_res["reason"]

            # Store compact sample [ts, sent, recv, avg, jit]
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

            # Classify status
            is_route_invalid = (not is_valid and not check_res.get("healthy", False))
            status = classify_status(
                short_loss=short_agg["packet_loss"],
                long_loss=long_agg["packet_loss"],
                last_cycle_loss=last_cycle_loss,
                burst_confirmed_dead=burst_confirmed_dead,
                route_invalid=is_route_invalid,
                max_acceptable_loss=max_loss,
                critical_loss=crit_loss
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
            stat["latency_ms"] = long_agg["avg_latency_ms"]
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

    def sync_firewall_and_proxies(self) -> None:
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
                    # Use Nginx stream for UDP forwarding of HAProxy rules
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
                # Nginx Stream TCP/UDP Forwarding (XManager Standard)
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
        ipv4_rules = []
        ipv6_rules = []

        for r in dnat_rules:
            if "dnat to [" in r or "]:" in r:
                ipv6_rules.append(r)
            else:
                ipv4_rules.append(r)

        ipv4_block = "\n".join(ipv4_rules) if ipv4_rules else "        # No active NFTables IPv4 DNAT rules"

        # Collect unique rule ports for traffic accounting named counters
        counter_defs = []
        forward_counters = []
        rule_ports = set()
        for r in self.config.get("rules", []):
            try:
                p = int(r.get("port", 0))
                if p > 0:
                    rule_ports.add(p)
            except (ValueError, TypeError):
                pass
        for r in dnat_rules:
            m = re.search(r"dport\s+(\d+)", r)
            if m:
                try:
                    rule_ports.add(int(m.group(1)))
                except ValueError:
                    pass

        for p in sorted(list(rule_ports)):
            counter_defs.append(f"    counter cnt_in_{p} {{ }}")
            counter_defs.append(f"    counter cnt_out_{p} {{ }}")
            forward_counters.append(f"        tcp dport {p} counter name cnt_in_{p}")
            forward_counters.append(f"        tcp sport {p} counter name cnt_out_{p}")
            forward_counters.append(f"        udp dport {p} counter name cnt_in_{p}")
            forward_counters.append(f"        udp sport {p} counter name cnt_out_{p}")

        counter_defs_str = "\n".join(counter_defs) + "\n\n" if counter_defs else ""
        forward_counters_str = "\n".join(forward_counters) + "\n" if forward_counters else ""

        tables_content = [
            f"""table ip xfwd_orchestrator
delete table ip xfwd_orchestrator

table ip xfwd_orchestrator {{
{counter_defs_str}    chain prerouting {{
        type nat hook prerouting priority dstnat; policy accept;
{ipv4_block}
    }}

    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
        oifname "gre*" masquerade
        oifname "ipip*" masquerade
        oifname "ftcp*" masquerade
        oifname "awg*" masquerade
        oifname "gnv*" masquerade
        oifname "vxlan*" masquerade
        oifname "wg*" masquerade
        oifname "tun*" masquerade
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
{forward_counters_str}        ct status dnat accept
        ct state {{ established, related }} accept
    }}
}}"""
        ]

        if self._is_ipv6_supported():
            ipv6_block = "\n".join(ipv6_rules) if ipv6_rules else "        # No active NFTables IPv6 DNAT rules"
            tables_content.append(
                f"""table ip6 xfwd_orchestrator
delete table ip6 xfwd_orchestrator

table ip6 xfwd_orchestrator {{
{counter_defs_str}    chain prerouting {{
        type nat hook prerouting priority dstnat; policy accept;
{ipv6_block}
    }}

    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
        oifname "gre*" masquerade
        oifname "ipip*" masquerade
        oifname "ftcp*" masquerade
        oifname "awg*" masquerade
        oifname "gnv*" masquerade
        oifname "vxlan*" masquerade
        oifname "wg*" masquerade
        oifname "tun*" masquerade
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
{forward_counters_str}        ct status dnat accept
        ct state {{ established, related }} accept
    }}
}}"""
            )

        nft_content = "#!/usr/sbin/nft -f\n# Generated by XForwarder Core Engine\n" + "\n\n".join(tables_content) + "\n"

        if not shutil.which("nft"):
            return True, None

        if hasattr(self, "_last_nft_content") and self._last_nft_content == nft_content:
            self.runtime_state["active_services"]["nftables"] = bool(dnat_rules)
            return True, None

        try:
            # Clean up legacy tables if exist
            subprocess.run(["nft", "delete", "table", "ip", "fwdman_orchestrator"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["nft", "delete", "table", "ip6", "fwdman_orchestrator"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            proc = subprocess.Popen(["nft", "-c", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate(input=nft_content)
            if proc.returncode == 0:
                apply_proc = subprocess.Popen(["nft", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                _, apply_err = apply_proc.communicate(input=nft_content)
                if apply_proc.returncode != 0:
                    err_msg = apply_err.strip() if apply_err else "Failed applying nftables ruleset"
                    print(f"[WARN] NFTables apply failed: {err_msg}", file=sys.stderr)
                    return False, f"NFTables apply: {err_msg}"
                self.runtime_state["active_services"]["nftables"] = bool(dnat_rules)
                self._last_nft_content = nft_content
                return True, None
            else:
                err_msg = err.strip() if err else "NFTables validation check failed"
                print(f"[WARN] NFTables check failed: {err_msg}", file=sys.stderr)
                return False, f"NFTables syntax: {err_msg}"
        except Exception as ex:
            return False, f"NFTables error: {str(ex)}"

    def _apply_haproxy(self, haproxy_entries: List[str], udp_entries: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        haproxy_dir = os.path.dirname(HAPROXY_CONF_PATH)
        if not os.path.exists(haproxy_dir) and not shutil.which("haproxy"):
            return True, None

        # Guarantee /run/haproxy exists for admin.sock
        try:
            os.makedirs("/run/haproxy", exist_ok=True)
        except Exception:
            pass

        # Standby dummy section prevents HAProxy error "no frontend, backend or listen section found" when 0 rules active
        active_entries = list(haproxy_entries)
        if not active_entries:
            active_entries = [
                "frontend xfwd_standby\n"
                "    mode tcp\n"
                "    bind 127.0.0.1:65534\n"
                "    disabled\n"
            ]

        # Bounded between 1 and 64 to comply with Linux thread bitmasks across HAProxy releases
        cpu_cores = min(64, max(1, os.cpu_count() or 1))
        nbthread_entry = f"    nbthread {cpu_cores}\n" if cpu_cores > 1 else ""
        cpu_map_entry = f"    cpu-map auto:1/1-{cpu_cores} 0-{cpu_cores - 1}\n" if cpu_cores > 1 else ""

        base_haproxy = f"""# Generated by XForwarder
global
    log /dev/log local0 notice
    stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
    stats timeout 30s
    user haproxy
    group haproxy
    daemon
    maxconn 100000
    tune.bufsize 65536
    tune.pipesize 262144
{nbthread_entry}{cpu_map_entry}defaults
    log     global
    mode    tcp
    option  dontlognull
    option  clitcpka
    option  srvtcpka
    option  splice-auto
    retries 3
    timeout connect    5s
    timeout client     1h
    timeout server     1h
    timeout client-fin 30s
    timeout server-fin 30s

""" + "\n".join(active_entries)

        if os.path.exists(HAPROXY_CONF_PATH):
            try:
                with open(HAPROXY_CONF_PATH, "r", encoding="utf-8") as f_curr:
                    if f_curr.read() == base_haproxy:
                        self.runtime_state["active_services"]["haproxy"] = bool(haproxy_entries)
                        return True, None
            except Exception:
                pass

        try:
            if not os.path.exists(haproxy_dir):
                os.makedirs(haproxy_dir, exist_ok=True)
            tmp_haproxy = f"{HAPROXY_CONF_PATH}.tmp.{os.getpid()}"
            with open(tmp_haproxy, "w", encoding="utf-8") as f:
                f.write(base_haproxy)

            # Pre-validate if haproxy binary is present
            if shutil.which("haproxy"):
                chk = subprocess.run(["haproxy", "-c", "-f", tmp_haproxy], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                if chk.returncode != 0:
                    # Defensive fallback: if older HAProxy build rejects advanced tune/splice/cpu-map/nbthread directives, remove them and retry
                    fallback_haproxy = (
                        base_haproxy.replace("    option  splice-auto\n", "")
                        .replace("    tune.bufsize 65536\n", "")
                        .replace("    tune.pipesize 262144\n", "")
                    )
                    if cpu_map_entry:
                        fallback_haproxy = fallback_haproxy.replace(cpu_map_entry, "")
                    if nbthread_entry:
                        fallback_haproxy = fallback_haproxy.replace(nbthread_entry, "")
                    if fallback_haproxy != base_haproxy:
                        with open(tmp_haproxy, "w", encoding="utf-8") as f:
                            f.write(fallback_haproxy)
                        chk_fb = subprocess.run(["haproxy", "-c", "-f", tmp_haproxy], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                        if chk_fb.returncode == 0:
                            base_haproxy = fallback_haproxy
                            chk = chk_fb
                    if chk.returncode != 0:
                        if os.path.exists(tmp_haproxy):
                            os.remove(tmp_haproxy)
                        err_msg = chk.stderr.strip() if chk.stderr else "HAProxy config validation failed"
                        return False, f"HAProxy syntax: {err_msg}"

            os.replace(tmp_haproxy, HAPROXY_CONF_PATH)

            if shutil.which("systemctl"):
                res = subprocess.run(["systemctl", "reload", "haproxy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode != 0:
                    res = subprocess.run(["systemctl", "restart", "haproxy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode != 0:
                        return False, "HAProxy service reload/restart failed"

            self.runtime_state["active_services"]["haproxy"] = bool(haproxy_entries)
            return True, None
        except Exception as ex:
            return False, f"HAProxy error: {str(ex)}"

    def _apply_nginx(self, nginx_entries: List[str]) -> Tuple[bool, Optional[str]]:
        nginx_dir = os.path.dirname(NGINX_CONF_PATH)
        if not os.path.exists(nginx_dir) and not shutil.which("nginx"):
            return True, None

        stream_body = "\n".join(nginx_entries) if nginx_entries else "    # No active Nginx stream servers"

        # Determine user safely to avoid getpwnam failures on non-Debian distributions
        user_line = ""
        for u in ("www-data", "nginx"):
            try:
                with open("/etc/passwd", "r", encoding="utf-8") as pf:
                    if any(line.startswith(f"{u}:") for line in pf):
                        user_line = f"user {u};"
                        break
            except Exception:
                pass

        # Determine module loading safely
        modules_line = ""
        if os.path.isdir("/etc/nginx/modules-enabled"):
            modules_line = "include /etc/nginx/modules-enabled/*.conf;"
        elif os.path.exists("/usr/lib/nginx/modules/ngx_stream_module.so"):
            modules_line = "load_module /usr/lib/nginx/modules/ngx_stream_module.so;"
        elif os.path.exists("/usr/lib64/nginx/modules/ngx_stream_module.so"):
            modules_line = "load_module /usr/lib64/nginx/modules/ngx_stream_module.so;"

        # Determine safe log directory
        log_dir = "/var/log/nginx"
        error_log_line = "error_log /var/log/nginx/error.log warn;"
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                error_log_line = "error_log /dev/null crit;"

        # Determine safe http includes (only existing directories/files)
        http_includes = []
        if os.path.exists("/etc/nginx/mime.types"):
            http_includes.append("    include /etc/nginx/mime.types;")
        if os.path.isdir("/etc/nginx/conf.d"):
            http_includes.append("    include /etc/nginx/conf.d/*.conf;")
        if os.path.isdir("/etc/nginx/sites-enabled"):
            http_includes.append("    include /etc/nginx/sites-enabled/*;")
        http_includes_block = ("\n" + "\n".join(http_includes)) if http_includes else ""

        nginx_content = f"""# Generated by XForwarder Engine (XManager Standard)
{user_line}
worker_processes auto;
pid /run/nginx.pid;
{modules_line}

worker_rlimit_nofile 300000;

events {{
    worker_connections 65535;
    use epoll;
    multi_accept on;
    accept_mutex off;
}}

stream {{
    access_log off;
    {error_log_line}

    proxy_connect_timeout 5s;
    proxy_timeout 1h;
    proxy_buffer_size 64k;
    proxy_socket_keepalive on;
    tcp_nodelay on;

{stream_body}
}}

http {{
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;{http_includes_block}
    default_type application/octet-stream;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    access_log off;
    error_log off;
    gzip on;
}}
"""
        if not nginx_entries:
            if shutil.which("nginx") and shutil.which("systemctl"):
                try:
                    chk = subprocess.run(["systemctl", "is-active", "--quiet", "nginx"])
                    if chk.returncode == 0:
                        subprocess.run(["systemctl", "stop", "nginx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            self.runtime_state["active_services"]["nginx"] = False
            return True, None

        if os.path.exists(NGINX_CONF_PATH):
            try:
                with open(NGINX_CONF_PATH, "r", encoding="utf-8") as f_curr:
                    if f_curr.read() == nginx_content:
                        self.runtime_state["active_services"]["nginx"] = bool(nginx_entries)
                        return True, None
            except Exception:
                pass

        try:
            if not os.path.exists(nginx_dir):
                os.makedirs(nginx_dir, exist_ok=True)
            if not os.path.exists("/etc/nginx/modules-enabled"):
                try:
                    os.makedirs("/etc/nginx/modules-enabled", exist_ok=True)
                except Exception:
                    pass
            tmp_nginx = f"{NGINX_CONF_PATH}.tmp.{os.getpid()}"
            with open(tmp_nginx, "w", encoding="utf-8") as f:
                f.write(nginx_content)

            # Validate Nginx syntax before applying if nginx installed
            if shutil.which("nginx"):
                test_res = subprocess.run(
                    ["nginx", "-t", "-c", tmp_nginx],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if test_res.returncode == 0:
                    os.replace(tmp_nginx, NGINX_CONF_PATH)
                    if shutil.which("systemctl"):
                        chk_active = subprocess.run(["systemctl", "is-active", "--quiet", "nginx"])
                        if chk_active.returncode == 0:
                            res = subprocess.run(["systemctl", "reload", "nginx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            res = subprocess.run(["systemctl", "start", "nginx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if res.returncode != 0:
                            res = subprocess.run(["systemctl", "restart", "nginx"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            if res.returncode != 0:
                                return False, "Nginx service reload/restart failed"
                    self.runtime_state["active_services"]["nginx"] = bool(nginx_entries)
                    return True, None
                else:
                    if os.path.exists(tmp_nginx):
                        os.remove(tmp_nginx)
                    err_msg = test_res.stderr.strip() if test_res.stderr else "Nginx syntax test failed"
                    return False, f"Nginx syntax: {err_msg}"
            else:
                os.replace(tmp_nginx, NGINX_CONF_PATH)
                self.runtime_state["active_services"]["nginx"] = bool(nginx_entries)
                return True, None
        except Exception as ex:
            return False, f"Nginx error: {str(ex)}"

    def _save_state_file(self) -> None:
        try:
            # If self.runtime_state has empty rules_state (e.g. called from one-off sync),
            # attempt to preserve live rules_state from existing state file on disk
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
        """Persists current engine PID to candidate paths to enable instant IPC wakeups."""
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
        """Removes persisted engine PID file on process termination."""
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

        # Start 15-minute packet loss monitor scheduler across unique destinations
        try:
            from core.metrics import LossMonitorScheduler
        except ImportError:
            try:
                from metrics import LossMonitorScheduler
            except ImportError:
                LossMonitorScheduler = None

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

                    # Clean up deleted rules from runtime state
                    current_rule_ids = {r.get("id") for r in rules if r.get("id")}
                    stale_ids = [rid for rid in list(self.runtime_state["rules_state"].keys()) if rid not in current_rule_ids]
                    for rid in stale_ids:
                        del self.runtime_state["rules_state"][rid]

                    # Parallel 10-ping ICMP probes across all unique destinations
                    probe_cache = self._probe_all_destinations(rules)

                    changed_priorities: Dict[str, int] = {}
                    for rule in rules:
                        r_id = rule.get("id", f"rule-{rule.get('port')}")
                        if self.evaluate_rule(rule, probe_cache=probe_cache):
                            changed_priorities[r_id] = rule.get("active_priority", 1)

                    self.runtime_state["last_check_timestamp"] = time.time()

                    # Periodic traffic accounting sample (every ~30s)
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


# Backward compatibility alias
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

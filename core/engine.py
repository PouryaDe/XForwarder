#!/usr/bin/env python3
"""
Forward Manager - Core Engine Daemon
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
from typing import Dict, List, Any, Optional

DEFAULT_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.json")
STATE_FILE_PATH = "/run/forward-manager/state.json"
HAPROXY_CONF_PATH = "/etc/haproxy/haproxy.cfg"
UDP_CONF_PATH = "/etc/haproxy/forwarder-udp.conf"


class ForwardManagerEngine:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = self._resolve_config_path(config_path)
        self.running = False
        self.lock = threading.Lock()
        self.config: Dict[str, Any] = {}
        self.runtime_state: Dict[str, Any] = {
            "uptime_started": time.time(),
            "last_check_timestamp": 0,
            "wan_interface": "unknown",
            "active_services": {
                "haproxy": False,
                "udp_stream": False,
                "nftables": False
            },
            "rules_state": {}
        }
        self.load_config()

    def _resolve_config_path(self, override_path: Optional[str]) -> str:
        if override_path and os.path.exists(override_path):
            return override_path
        if os.path.exists(DEFAULT_CONFIG_PATH):
            return DEFAULT_CONFIG_PATH
        if os.path.exists(LOCAL_CONFIG_PATH):
            return LOCAL_CONFIG_PATH
        example_path = LOCAL_CONFIG_PATH + ".example"
        if os.path.exists(example_path):
            return example_path
        return DEFAULT_CONFIG_PATH

    def load_config(self) -> None:
        with self.lock:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                else:
                    self.config = {
                        "wan_interface": "auto",
                        "check_interval_seconds": 8,
                        "failure_threshold": 3,
                        "recovery_threshold": 3,
                        "web": {
                            "bind_host": "0.0.0.0",
                            "port": 8090,
                            "secret_path": "fwd-admin",
                            "auth": {
                                "username": "admin",
                                "password_hash": ""
                            }
                        },
                        "rules": []
                    }
                self._detect_wan_interface()
            except Exception as e:
                print(f"[ERROR] Failed to load config from {self.config_path}: {e}", file=sys.stderr)

    def save_config(self) -> bool:
        with self.lock:
            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                tmp_path = f"{self.config_path}.tmp.{os.getpid()}"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self.config_path)
                return True
            except Exception as e:
                print(f"[ERROR] Failed to save config to {self.config_path}: {e}", file=sys.stderr)
                return False

    def _detect_wan_interface(self) -> str:
        configured = self.config.get("wan_interface", "auto")
        if configured and configured != "auto":
            self.runtime_state["wan_interface"] = configured
            return configured

        try:
            out = subprocess.check_output("ip -o route show default", shell=True, text=True).strip()
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

    def check_destination(self, dest: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a low-overhead health check on a target destination."""
        target = dest.get("target", "")
        port = int(dest.get("port", 0))
        dest_type = dest.get("type", "haproxy")
        start_time = time.time()
        healthy = False

        if not target or port <= 0:
            return {"healthy": False, "latency_ms": 0.0, "reason": "Invalid target/port"}

        try:
            family = socket.AF_INET6 if ":" in target else socket.AF_INET
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                res = s.connect_ex((target, port))
                healthy = (res == 0)
        except Exception:
            healthy = False

        if not healthy and dest_type == "nftables":
            try:
                ping_cmd = f"ping -c 1 -W 1 {target} >/dev/null 2>&1"
                healthy = (subprocess.call(ping_cmd, shell=True) == 0)
            except Exception:
                healthy = False

        latency_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "healthy": healthy,
            "latency_ms": latency_ms if healthy else 0.0
        }

    def evaluate_rule(self, rule: Dict[str, Any]) -> bool:
        rule_id = rule.get("id", f"rule-{rule.get('port')}")
        destinations = sorted(rule.get("destinations", []), key=lambda x: x.get("priority", 99))
        if not destinations:
            return False

        if rule_id not in self.runtime_state["rules_state"]:
            self.runtime_state["rules_state"][rule_id] = {
                "active_priority": rule.get("active_priority", 1),
                "dest_stats": {}
            }

        rule_state = self.runtime_state["rules_state"][rule_id]
        force_override = rule.get("force_override", 0)

        dest_results = {}
        for dest in destinations:
            prio = dest.get("priority", 1)
            dest_key = f"prio_{prio}"
            if dest_key not in rule_state["dest_stats"]:
                rule_state["dest_stats"][dest_key] = {
                    "consecutive_fails": 0,
                    "consecutive_success": 0,
                    "status": "unknown",
                    "latency_ms": 0.0
                }

            stat = rule_state["dest_stats"][dest_key]
            check_res = self.check_destination(dest)
            stat["latency_ms"] = check_res["latency_ms"]

            if check_res["healthy"]:
                stat["consecutive_fails"] = 0
                stat["consecutive_success"] += 1
                if stat["consecutive_success"] >= self.config.get("recovery_threshold", 3):
                    stat["status"] = "healthy"
            else:
                stat["consecutive_success"] = 0
                stat["consecutive_fails"] += 1
                if stat["consecutive_fails"] >= self.config.get("failure_threshold", 3):
                    stat["status"] = "failed"

            dest_results[prio] = (stat["status"] == "healthy")

        current_active = rule_state["active_priority"]
        target_active = current_active

        if force_override > 0:
            target_active = force_override
        else:
            chosen = None
            for dest in destinations:
                p = dest.get("priority", 1)
                if dest_results.get(p, False):
                    chosen = p
                    break

            if chosen is not None:
                target_active = chosen
            else:
                target_active = current_active

        state_changed = (target_active != current_active)
        rule_state["active_priority"] = target_active
        rule["active_priority"] = target_active
        return state_changed

    def sync_firewall_and_proxies(self) -> None:
        wan_iface = self._detect_wan_interface()
        haproxy_entries = []
        udp_entries = []
        nft_dnat_rules = []

        rules = self.config.get("rules", [])
        for rule in rules:
            port = rule.get("port")
            proto = rule.get("protocol", "both").lower()
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

            target = dest.get("target")
            target_port = dest.get("port", port)
            dest_type = dest.get("type", "haproxy")

            if dest_type == "haproxy":
                if proto in ("tcp", "both"):
                    haproxy_entries.append(
                        f"listen fwd_{port}\n"
                        f"    bind *:{port}\n"
                        f"    server srv_{port} [{target}]:{target_port} send-proxy-v2\n"
                    )
                if proto in ("udp", "both"):
                    udp_entries.append(
                        f"    server {{\n"
                        f"        listen {port} udp reuseport;\n"
                        f"        proxy_pass [{target}]:{target_port};\n"
                        f"    }}\n"
                    )
            elif dest_type == "nftables":
                if proto in ("tcp", "both"):
                    nft_dnat_rules.append(
                        f'        iifname "{wan_iface}" tcp dport {port} dnat to {target}:{target_port}'
                    )
                if proto in ("udp", "both"):
                    nft_dnat_rules.append(
                        f'        iifname "{wan_iface}" udp dport {port} dnat to {target}:{target_port}'
                    )

        self._apply_nftables(nft_dnat_rules)
        self._apply_haproxy(haproxy_entries, udp_entries)
        self._save_state_file()

    def _apply_nftables(self, dnat_rules: List[str]) -> None:
        dnat_block = "\n".join(dnat_rules) if dnat_rules else "        # No active NFTables DNAT rules"
        nft_content = f"""#!/usr/sbin/nft -f
# Generated by Forward-Manager Core Engine
table ip fwdman_orchestrator
delete table ip fwdman_orchestrator

table ip fwdman_orchestrator {{
    chain prerouting {{
        type nat hook prerouting priority dstnat; policy accept;
{dnat_block}
    }}

    chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
        oifname {{ "gre*", "ipip*", "ftcp*", "awg*", "gnv*", "vxlan*" }} masquerade
    }}

    chain forward {{
        type filter hook forward priority filter; policy accept;
        ct status dnat accept
        ct state {{ established, related }} accept
    }}
}}
"""
        try:
            proc = subprocess.Popen(["nft", "-c", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate(input=nft_content)
            if proc.returncode == 0:
                apply_proc = subprocess.Popen(["nft", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                apply_proc.communicate(input=nft_content)
                self.runtime_state["active_services"]["nftables"] = bool(dnat_rules)
            else:
                print(f"[WARN] NFTables check failed: {err}", file=sys.stderr)
        except Exception:
            pass

    def _apply_haproxy(self, haproxy_entries: List[str], udp_entries: List[str]) -> None:
        if not os.path.exists(os.path.dirname(HAPROXY_CONF_PATH)):
            return

        base_haproxy = """# Generated by Forward-Manager
global
    log /dev/log local0
    log /dev/log local1 notice
    stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
    stats timeout 30s
    user haproxy
    group haproxy
    daemon
    maxconn 100000

defaults
    log     global
    mode    tcp
    option  tcplog
    option  dontlognull
    retries 3
    timeout connect    5s
    timeout client     1h
    timeout server     1h
    timeout client-fin 30s
    timeout server-fin 30s

""" + "\n".join(haproxy_entries)

        try:
            with open(HAPROXY_CONF_PATH, "w", encoding="utf-8") as f:
                f.write(base_haproxy)

            subprocess.call("systemctl reload haproxy >/dev/null 2>&1 || systemctl restart haproxy >/dev/null 2>&1", shell=True)
            self.runtime_state["active_services"]["haproxy"] = bool(haproxy_entries)
        except Exception:
            pass

        if udp_entries and os.path.exists(os.path.dirname(UDP_CONF_PATH)):
            udp_content = f"""# Generated by Forward-Manager UDP Forwarder
user www-data;
worker_processes auto;
worker_rlimit_nofile 1048576;
pid /run/haproxy-forwarder-udp.pid;
daemon off;

events {{
    worker_connections 65535;
    multi_accept on;
    use epoll;
}}

stream {{
    proxy_timeout 60s;
    proxy_buffer_size 64k;
{"".join(udp_entries)}
}}
"""
            try:
                with open(UDP_CONF_PATH, "w", encoding="utf-8") as f:
                    f.write(udp_content)
                subprocess.call("systemctl reload haproxy-forwarder-udp >/dev/null 2>&1 || systemctl restart haproxy-forwarder-udp >/dev/null 2>&1", shell=True)
                self.runtime_state["active_services"]["udp_stream"] = True
            except Exception:
                pass

    def _save_state_file(self) -> None:
        try:
            os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
            with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "config": self.config,
                    "runtime": self.runtime_state,
                    "updated_at": time.time()
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def run_loop(self) -> None:
        self.running = True
        print("[INFO] Forward-Manager Core Engine started.")
        self.sync_firewall_and_proxies()

        while self.running:
            try:
                self.load_config()
                state_changed = False
                rules = self.config.get("rules", [])

                for rule in rules:
                    if self.evaluate_rule(rule):
                        state_changed = True

                self.runtime_state["last_check_timestamp"] = time.time()

                if state_changed:
                    print("[INFO] Failover state change detected. Synchronizing routing layer...")
                    self.save_config()
                    self.sync_firewall_and_proxies()
                else:
                    self._save_state_file()

                interval = int(self.config.get("check_interval_seconds", 8))
                time.sleep(max(3, interval))
            except Exception as e:
                print(f"[ERROR] Exception in forward-manager loop: {e}", file=sys.stderr)
                time.sleep(5)

    def stop(self) -> None:
        self.running = False


if __name__ == "__main__":
    engine = ForwardManagerEngine()

    def handle_sig(sig, frame):
        print("\n[INFO] Terminating Forward-Manager Engine...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)
    engine.run_loop()

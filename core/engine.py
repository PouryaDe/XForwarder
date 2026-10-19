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
from typing import Dict, List, Any, Optional, Tuple

DEFAULT_CONFIG_PATH = "/etc/xforwarder/config.json"
LEGACY_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.json")
STATE_FILE_PATH = "/run/xforwarder/state.json"
LEGACY_STATE_FILE_PATH = "/run/forward-manager/state.json"
HAPROXY_CONF_PATH = "/etc/haproxy/haproxy.cfg"
UDP_CONF_PATH = "/etc/haproxy/forwarder-udp.conf"
NGINX_CONF_PATH = "/etc/nginx/nginx.conf"


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
                "nginx": False,
                "udp_stream": False,
                "nftables": False
            },
            "rules_state": {}
        }
        self._last_applied_rules: Optional[str] = None
        self.load_config()

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

        if cfg.get("schema_version") != 2:
            cfg["schema_version"] = 2
            modified = True

        defaults = {
            "wan_interface": "auto",
            "check_interval_seconds": 8,
            "failure_threshold": 3,
            "recovery_threshold": 3
        }
        for k, v in defaults.items():
            if k not in cfg:
                cfg[k] = v
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
                    if target.startswith("10.") or target.startswith("192.168."):
                        dtype = "nftables"
                    else:
                        dtype = "haproxy"
                    d["type"] = dtype
                    modified = True
                elif d.get("type") != dtype:
                    d["type"] = dtype
                    modified = True

                if "target" in d:
                    clean_target = str(d["target"]).strip()
                    if d["target"] != clean_target:
                        d["target"] = clean_target
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

    def check_destination(self, dest: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a low-overhead health check on a target destination with strict route and interface isolation."""
        target = str(dest.get("target", "")).strip()
        port = int(dest.get("port", 0))
        dest_type = dest.get("type", "haproxy")
        tunnel_iface = str(dest.get("tunnel_iface", "")).strip()
        start_time = time.perf_counter()
        healthy = False
        fail_reason = ""

        if not target or port <= 0:
            return {"healthy": False, "latency_ms": 0.0, "reason": "Invalid target/port"}

        wan_iface = self._detect_wan_interface()
        target_is_private = is_private_or_tunnel_target(target)

        # 1. Interface & Route Validation for Tunnel/NFTables destinations
        if dest_type == "nftables" or tunnel_iface:
            if tunnel_iface:
                # Explicit tunnel interface specified - verify it exists and is UP
                if not self._is_interface_up(tunnel_iface):
                    return {
                        "healthy": False,
                        "latency_ms": 0.0,
                        "reason": f"Tunnel interface '{tunnel_iface}' is missing or down"
                    }
            elif target_is_private:
                # Private IP without explicit interface - verify route doesn't fall back to WAN default gateway
                route_iface = self._get_route_interface(target)
                if route_iface == "":
                    return {
                        "healthy": False,
                        "latency_ms": 0.0,
                        "reason": f"No route to destination {target}"
                    }
                elif route_iface:
                    if route_iface == wan_iface:
                        return {
                            "healthy": False,
                            "latency_ms": 0.0,
                            "reason": f"Tunnel destination {target} routes via WAN ({wan_iface}); tunnel interface is not defined"
                        }
                    if route_iface in ("lo", "gre0", "gretap0", "erspan0", "tunl0", "sit0", "ip6tnl0", "ip6gre0", "dummy0"):
                        return {
                            "healthy": False,
                            "latency_ms": 0.0,
                            "reason": f"Destination {target} routes to kernel fallback device {route_iface}"
                        }
                    if not self._is_interface_up(route_iface):
                        return {
                            "healthy": False,
                            "latency_ms": 0.0,
                            "reason": f"Interface {route_iface} for {target} is down"
                        }
                    tunnel_iface = route_iface

        # 2. Socket TCP probe (low-overhead connect)
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

        # 3. ICMP Ping fallback probe for NFTables destinations
        if not healthy and dest_type == "nftables":
            try:
                # Safe ping probe without shell injection
                if all(c in "0123456789abcdefABCDEF:.-" for c in target):
                    if sys.platform == "win32":
                        ping_cmd = ["ping", "-n", "1", "-w", "1000", target]
                    else:
                        ping_cmd = ["ping", "-c", "1", "-W", "1"]
                        if tunnel_iface:
                            ping_cmd.extend(["-I", tunnel_iface])
                        ping_cmd.append(target)
                    healthy = (subprocess.call(ping_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0)
                    if not healthy and not fail_reason:
                        fail_reason = "Ping probe unreachable"
            except Exception as e:
                healthy = False
                fail_reason = str(e)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        res_dict = {
            "healthy": healthy,
            "latency_ms": latency_ms if healthy else 0.0
        }
        if not healthy and fail_reason:
            res_dict["reason"] = fail_reason
        return res_dict

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
            if "reason" in check_res:
                stat["reason"] = check_res["reason"]

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

            target = str(dest.get("target", "")).strip()
            target_port = dest.get("port", port)
            dest_type = dest.get("type", "haproxy")
            target_str = f"[{target}]:{target_port}" if ":" in target else f"{target}:{target_port}"
            comment_clean = str(dest.get("comment") or rule.get("id") or f"Port {port}").replace("\n", " ").replace("\r", "")

            if dest_type == "haproxy":
                if proto in ("tcp", "both"):
                    haproxy_entries.append(
                        f"listen fwd_{port}\n"
                        f"    bind *:{port}\n"
                        f"    server srv_{port} {target_str} send-proxy-v2\n"
                    )
                if proto in ("udp", "both"):
                    udp_entries.append(
                        f"    server {{\n"
                        f"        listen {port} udp reuseport;\n"
                        f"        proxy_pass {target_str};\n"
                        f"    }}\n"
                    )
            elif dest_type == "nginx":
                # Nginx Stream TCP/UDP Forwarding (XManager Standard)
                if proto in ("both", ""):
                    nginx_entries.append(
                        f"    # [{comment_clean}]\n"
                        f"    server {{ listen {port} reuseport; listen {port} udp; proxy_pass {target_str}; }}"
                    )
                elif proto == "tcp":
                    nginx_entries.append(
                        f"    # [{comment_clean}]\n"
                        f"    server {{ listen {port} reuseport; proxy_pass {target_str}; }}"
                    )
                elif proto == "udp":
                    nginx_entries.append(
                        f"    # [{comment_clean}]\n"
                        f"    server {{ listen {port} udp reuseport; proxy_pass {target_str}; }}"
                    )
            elif dest_type == "nftables":
                # NFTables DNAT in IPv4 table expects valid IPv4 tunnel target
                if ":" not in target:
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
        self._apply_nginx(nginx_entries)
        self._save_state_file()
        self._last_applied_rules = self._get_rules_fingerprint()

    def _apply_nftables(self, dnat_rules: List[str]) -> None:
        dnat_block = "\n".join(dnat_rules) if dnat_rules else "        # No active NFTables DNAT rules"
        nft_content = f"""#!/usr/sbin/nft -f
# Generated by XForwarder Core Engine
table ip xfwd_orchestrator
delete table ip xfwd_orchestrator

table ip xfwd_orchestrator {{
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
            # Clean up legacy table if exists
            subprocess.run(["nft", "delete", "table", "ip", "fwdman_orchestrator"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
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
        haproxy_dir = os.path.dirname(HAPROXY_CONF_PATH)
        if not os.path.exists(haproxy_dir):
            return

        base_haproxy = """# Generated by XForwarder
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
            tmp_haproxy = f"{HAPROXY_CONF_PATH}.tmp.{os.getpid()}"
            with open(tmp_haproxy, "w", encoding="utf-8") as f:
                f.write(base_haproxy)
            os.replace(tmp_haproxy, HAPROXY_CONF_PATH)

            subprocess.call("systemctl reload haproxy >/dev/null 2>&1 || systemctl restart haproxy >/dev/null 2>&1", shell=True)
            self.runtime_state["active_services"]["haproxy"] = bool(haproxy_entries)
        except Exception:
            pass

        udp_dir = os.path.dirname(UDP_CONF_PATH)
        if udp_entries and os.path.exists(udp_dir):
            udp_content = f"""# Generated by XForwarder UDP Forwarder
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
                tmp_udp = f"{UDP_CONF_PATH}.tmp.{os.getpid()}"
                with open(tmp_udp, "w", encoding="utf-8") as f:
                    f.write(udp_content)
                os.replace(tmp_udp, UDP_CONF_PATH)
                subprocess.call("systemctl reload haproxy-forwarder-udp >/dev/null 2>&1 || systemctl restart haproxy-forwarder-udp >/dev/null 2>&1", shell=True)
                self.runtime_state["active_services"]["udp_stream"] = True
            except Exception:
                pass
        elif not udp_entries:
            self.runtime_state["active_services"]["udp_stream"] = False

    def _apply_nginx(self, nginx_entries: List[str]) -> None:
        nginx_dir = os.path.dirname(NGINX_CONF_PATH)
        if not os.path.exists(nginx_dir):
            return

        stream_body = "\n".join(nginx_entries) if nginx_entries else "    # No active Nginx stream servers"

        nginx_content = f"""# Generated by XForwarder Engine (XManager Standard)
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

worker_rlimit_nofile 300000;

events {{
    worker_connections 65535;
    use epoll;
    multi_accept on;
    accept_mutex off;
}}

stream {{
    access_log off;
    error_log /dev/null crit;

    proxy_connect_timeout 5s;
    proxy_timeout 10m;
    proxy_socket_keepalive on;
    tcp_nodelay on;

    proxy_responses 1;

{stream_body}
}}

http {{
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    access_log off;
    error_log off;
    gzip on;
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}}
"""
        try:
            tmp_nginx = f"{NGINX_CONF_PATH}.tmp.{os.getpid()}"
            with open(tmp_nginx, "w", encoding="utf-8") as f:
                f.write(nginx_content)

            # Validate Nginx syntax before applying
            test_res = subprocess.run(
                ["nginx", "-t", "-c", tmp_nginx],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            if test_res.returncode == 0:
                os.replace(tmp_nginx, NGINX_CONF_PATH)
                subprocess.call("systemctl reload nginx >/dev/null 2>&1 || systemctl restart nginx >/dev/null 2>&1", shell=True)
                self.runtime_state["active_services"]["nginx"] = bool(nginx_entries)
            else:
                if os.path.exists(tmp_nginx):
                    os.remove(tmp_nginx)
                # If nginx is installed but test with temp file has include issues, fallback to atomic replace
                if "open() \"/etc/nginx/modules-enabled/" not in test_res.stderr:
                    os.replace(tmp_nginx if os.path.exists(tmp_nginx) else NGINX_CONF_PATH, NGINX_CONF_PATH)
                    subprocess.call("systemctl reload nginx >/dev/null 2>&1 || systemctl restart nginx >/dev/null 2>&1", shell=True)
                    self.runtime_state["active_services"]["nginx"] = bool(nginx_entries)
                else:
                    print(f"[WARN] Nginx syntax check warning: {test_res.stderr}", file=sys.stderr)
        except Exception:
            pass

    def _save_state_file(self) -> None:
        try:
            for s_path in [STATE_FILE_PATH, LEGACY_STATE_FILE_PATH]:
                s_dir = os.path.dirname(s_path)
                if s_path == LEGACY_STATE_FILE_PATH and not os.path.exists(s_dir):
                    continue
                os.makedirs(s_dir, exist_ok=True)
                tmp_path = f"{s_path}.tmp.{os.getpid()}"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "config": self.config,
                        "runtime": self.runtime_state,
                        "updated_at": time.time()
                    }, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, s_path)
        except Exception:
            pass

    def run_loop(self) -> None:
        self.running = True
        print("[INFO] XForwarder Core Engine started.")
        self.sync_firewall_and_proxies()

        while self.running:
            try:
                self.load_config()
                rules = self.config.get("rules", [])

                # Clean up deleted rules from runtime state
                current_rule_ids = {r.get("id") for r in rules if r.get("id")}
                stale_ids = [rid for rid in self.runtime_state["rules_state"] if rid not in current_rule_ids]
                for rid in stale_ids:
                    del self.runtime_state["rules_state"][rid]

                state_changed = False
                for rule in rules:
                    if self.evaluate_rule(rule):
                        state_changed = True

                self.runtime_state["last_check_timestamp"] = time.time()

                config_changed = (self._get_rules_fingerprint() != self._last_applied_rules)

                if state_changed or config_changed:
                    print("[INFO] Routing state or configuration change detected. Synchronizing routing layer...")
                    if state_changed:
                        self.save_config()
                    self.sync_firewall_and_proxies()
                else:
                    self._save_state_file()

                interval = int(self.config.get("check_interval_seconds", 8))
                time.sleep(max(3, interval))
            except Exception as e:
                print(f"[ERROR] Exception in xforwarder loop: {e}", file=sys.stderr)
                time.sleep(5)

    def stop(self) -> None:
        self.running = False


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

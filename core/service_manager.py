#!/usr/bin/env python3
"""
XForwarder - Service Controller & System Update Manager
Provides granular service restart controls and decoupled update orchestration.
"""

import os
import sys
import glob
import json
import time
import shutil
import threading
import subprocess
import tempfile
import urllib.request
import urllib.parse
import http.client
import socket
import ssl
import ipaddress
import shlex
import re
from contextlib import contextmanager
from typing import Dict, Any, Tuple, Optional, List, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_VERSION = "1.10.0"

_GITHUB_REPO_URL = "https://github.com/PouryaDe/XForwarder.git"
_GITHUB_API_URL = "https://api.github.com/repos/PouryaDe/XForwarder/commits/main"
_GITHUB_HOSTS = ("github.com", "api.github.com", "codeload.github.com", "objects.githubusercontent.com", "raw.githubusercontent.com")
_COMMON_PROXY_PORTS = (10808, 10809, 1080, 10810, 2080, 2081, 7890, 7891, 8080, 8118, 8888, 3128, 9050, 10800)
_EXCLUDED_SYSTEM_PORTS = {22, 25, 53, 80, 443, 3306, 5432, 6379, 27017}

_REMOTE_VERSION_CACHE: Dict[str, Any] = {"data": None, "key": None, "expires": 0}
_REMOTE_VERSION_LOCK = threading.Lock()
_IFACE_ROUTE_LOCK = threading.Lock()


def invalidate_remote_version_cache() -> None:
    """Clears cached remote GitHub version check results."""
    with _REMOTE_VERSION_LOCK:
        _REMOTE_VERSION_CACHE["data"] = None
        _REMOTE_VERSION_CACHE["key"] = None
        _REMOTE_VERSION_CACHE["expires"] = 0

_UPDATE_STATE: Dict[str, Any] = {
    "status": "idle",
    "start_time": 0.0,
    "pid": None,
    "error": None
}
_UPDATE_LOCK = threading.Lock()


def get_update_state_file_path() -> str:
    """Returns persistent update state file path in /run/xforwarder or system temp."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "update_state.json")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/update_state.json"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_update_state.json")


def save_update_state(state: dict, path_override: Optional[str] = None) -> None:
    """Atomically persists update progress state to disk."""
    path = path_override or get_update_state_file_path()
    try:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except Exception:
        pass


def load_update_state(path_override: Optional[str] = None) -> None:
    """Loads update progress state across daemon reloads."""
    path = path_override or get_update_state_file_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                with _UPDATE_LOCK:
                    _UPDATE_STATE.update(data)
        except Exception:
            pass


load_update_state()


def get_installed_version() -> str:
    """Reads script version from xforwarder.sh or returns default APP_VERSION."""
    script_candidates = [
        "/opt/xforwarder/xforwarder.sh",
        os.path.join(BASE_DIR, "xforwarder.sh"),
        "/usr/local/bin/xforwarder"
    ]
    for s in script_candidates:
        if os.path.exists(s):
            try:
                with open(s, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("SCRIPT_VERSION="):
                            v = line.split("=")[1].strip().strip('"').strip("'")
                            if v:
                                return v
            except Exception:
                pass
    return APP_VERSION


def get_local_version_info() -> dict:
    """Inspects local git repository, .commit metadata files, or installed package version."""
    version = get_installed_version()
    info = {
        "version": version,
        "commit": None,
        "commit_date": None,
        "is_git": False
    }

    commit_file_candidates = [
        os.path.join(BASE_DIR, ".commit"),
        "/opt/xforwarder/.commit",
        "/etc/xforwarder/.commit",
    ]
    for c_path in commit_file_candidates:
        if os.path.isfile(c_path):
            try:
                with open(c_path, "r", encoding="utf-8", errors="replace") as f:
                    c_val = f.read().strip()
                if c_val:
                    info["commit"] = c_val[:7]
                    d_path = c_path.replace(".commit", ".commit_date")
                    if os.path.isfile(d_path):
                        with open(d_path, "r", encoding="utf-8", errors="replace") as df:
                            info["commit_date"] = df.read().strip()
                    break
            except Exception:
                pass

    git_dirs = [
        BASE_DIR,
        "/opt/xforwarder",
        os.path.join(os.path.dirname(BASE_DIR), "XForwarder"),
        os.path.join(os.path.dirname(BASE_DIR), "Forward-Manager"),
        "/root/XForwarder",
        "/root/Forward-Manager",
    ]
    for g_dir in git_dirs:
        if os.path.isdir(os.path.join(g_dir, ".git")):
            try:
                res = subprocess.run(
                    ["git", "-C", g_dir, "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=2.0
                )
                if res.returncode == 0 and res.stdout.strip():
                    info["commit"] = res.stdout.strip()
                    info["is_git"] = True
                    res_date = subprocess.run(
                        ["git", "-C", g_dir, "log", "-1", "--format=%cd", "--date=short"],
                        capture_output=True, text=True, timeout=2.0
                    )
                    if res_date.returncode == 0 and res_date.stdout.strip():
                        info["commit_date"] = res_date.stdout.strip()
                    break
            except Exception:
                pass

    return info


def build_mirror_git_url(mirror_url: str) -> str:
    """Normalizes a GitHub mirror prefix or direct git URL to a cloneable repository URL."""
    m = str(mirror_url or "").strip()
    if not m:
        return _GITHUB_REPO_URL
    lower = m.lower()
    if "pouryade/xforwarder" in lower or lower.endswith(".git"):
        return m
    return f"{m.rstrip('/')}/{_GITHUB_REPO_URL}"


def build_mirror_api_url(mirror_url: str) -> str:
    """Normalizes a GitHub mirror prefix to a GitHub commits API URL when prefix-based."""
    m = str(mirror_url or "").strip()
    if not m:
        return _GITHUB_API_URL
    if "pouryade/xforwarder" in m.lower() or m.lower().endswith(".git"):
        return _GITHUB_API_URL
    return f"{m.rstrip('/')}/{_GITHUB_API_URL}"


def _open_socks5_socket(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    timeout: float = 4.0,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> socket.socket:
    """Connects to `target_host:target_port` via an RFC 1928 SOCKS5 proxy using remote DNS (ATYP=0x03)."""
    sock = socket.create_connection((proxy_host, int(proxy_port)), timeout=timeout)
    try:
        sock.settimeout(timeout)
        if username is not None and password is not None:
            sock.sendall(b"\x05\x02\x00\x02")
        else:
            sock.sendall(b"\x05\x01\x00")
        greeting = sock.recv(2)
        if len(greeting) < 2 or greeting[0] != 5:
            raise OSError("Invalid SOCKS5 proxy greeting response")
        method = greeting[1]
        if method == 2:
            if username is None or password is None:
                raise OSError("SOCKS5 proxy requires authentication")
            u_b = username.encode("utf-8")[:255]
            p_b = password.encode("utf-8")[:255]
            sock.sendall(bytes([1, len(u_b)]) + u_b + bytes([len(p_b)]) + p_b)
            auth_resp = sock.recv(2)
            if len(auth_resp) < 2 or auth_resp[1] != 0:
                raise OSError("SOCKS5 username/password authentication failed")
        elif method != 0:
            raise OSError(f"SOCKS5 proxy selected unsupported auth method {method}")

        host_b = target_host.encode("idna")
        if len(host_b) > 255:
            raise ValueError("Target hostname exceeds SOCKS5 limit")
        req = b"\x05\x01\x00\x03" + bytes([len(host_b)]) + host_b + int(target_port).to_bytes(2, "big")
        sock.sendall(req)

        hdr = sock.recv(4)
        if len(hdr) < 4 or hdr[0] != 5 or hdr[1] != 0:
            code = hdr[1] if len(hdr) >= 2 else -1
            raise OSError(f"SOCKS5 CONNECT failed with status {code}")
        atyp = hdr[3]
        if atyp == 1:
            sock.recv(6)
        elif atyp == 3:
            alen_b = sock.recv(1)
            if alen_b:
                sock.recv(alen_b[0] + 2)
        elif atyp == 4:
            sock.recv(18)
        return sock
    except Exception:
        try:
            sock.close()
        except Exception:
            pass
        raise


class _HttpsViaSocks5Connection(http.client.HTTPSConnection):
    """Stdlib HTTPSConnection tunneling TLS cleanly through a SOCKS5/SOCKS5h proxy."""

    def __init__(self, host, proxy_host, proxy_port, proxy_user=None, proxy_pass=None, port=443, timeout=4.0, context=None):
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._proxy_user = proxy_user
        self._proxy_pass = proxy_pass

    def connect(self):
        raw_sock = _open_socks5_socket(
            self._proxy_host,
            self._proxy_port,
            self.host,
            self.port,
            timeout=float(self.timeout or 4.0),
            username=self._proxy_user,
            password=self._proxy_pass,
        )
        try:
            ctx = self._context or ssl.create_default_context()
            self.sock = ctx.wrap_socket(raw_sock, server_hostname=self.host)
        except Exception:
            try:
                raw_sock.close()
            except Exception:
                pass
            raise


def _probe_socks5_noauth(host: str, port: int, timeout: float = 0.25) -> Tuple[bool, bool]:
    """Tests if a local loopback TCP port speaks SOCKS5. Returns `(is_socks5, requires_auth)`."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(b"\x05\x01\x00")
            resp = sock.recv(2)
            if len(resp) >= 2 and resp[0] == 5:
                return True, (resp[1] == 2)
    except Exception:
        pass
    return False, False


def _parse_proc_net_tcp_listen(proc_path: str, is_v6: bool = False) -> List[Tuple[str, int]]:
    """Parses Linux `/proc/net/tcp` or `/proc/net/tcp6` and returns `(ip, port)` of LISTEN sockets."""
    results: List[Tuple[str, int]] = []
    if not os.path.isfile(proc_path):
        return results
    try:
        with open(proc_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 4 or parts[3] != "0A":
                continue
            local_addr = parts[1]
            if ":" not in local_addr:
                continue
            hex_ip, hex_port = local_addr.split(":", 1)
            port = int(hex_port, 16)
            if not (1 <= port <= 65535):
                continue
            if not is_v6 and len(hex_ip) == 8:
                raw_bytes = bytes.fromhex(hex_ip)[::-1]
                ip_str = str(ipaddress.IPv4Address(raw_bytes))
                results.append((ip_str, port))
            elif is_v6 and len(hex_ip) == 32:
                words = [bytes.fromhex(hex_ip[i:i + 8])[::-1] for i in range(0, 32, 8)]
                ip_str = str(ipaddress.IPv6Address(b"".join(words)))
                results.append((ip_str, port))
    except Exception:
        pass
    return results


def discover_local_proxies(
    config: Optional[dict] = None,
    proc_tcp_paths: Optional[Tuple[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Discovers local SOCKS5/HTTP proxy tunnels listening on the host (e.g. Xray, Sing-box, SSH -D)
    while strictly excluding XForwarder's own web port and managed forwarding ports.
    """
    if config is None:
        try:
            from core.config_manager import load_config
        except ImportError:
            from config_manager import load_config
        config = load_config()

    excluded = set(_EXCLUDED_SYSTEM_PORTS)
    try:
        excluded.add(int((config.get("web") or {}).get("port", 8090)))
    except (ValueError, TypeError):
        excluded.add(8090)

    for rule in config.get("rules", []) if isinstance(config, dict) else []:
        if not isinstance(rule, dict):
            continue
        try:
            p = int(rule.get("port", 0))
            if 1 <= p <= 65535:
                excluded.add(p)
        except (ValueError, TypeError):
            pass
        pr = str(rule.get("port_range") or "")
        if "-" in pr:
            try:
                sp, ep = map(int, pr.split("-", 1))
                if ep - sp <= 256:
                    excluded.update(range(sp, ep + 1))
            except (ValueError, TypeError):
                pass

    tcp4_path, tcp6_path = proc_tcp_paths or ("/proc/net/tcp", "/proc/net/tcp6")
    raw_listeners = _parse_proc_net_tcp_listen(tcp4_path, is_v6=False) + _parse_proc_net_tcp_listen(tcp6_path, is_v6=True)

    candidates_by_port: Dict[int, bool] = {}
    for ip_str, port in raw_listeners:
        if port in excluded:
            continue
        is_loopback = ip_str in ("127.0.0.1", "::1")
        is_wildcard = ip_str in ("0.0.0.0", "::")
        if is_loopback:
            candidates_by_port[port] = True
        elif is_wildcard and port in _COMMON_PROXY_PORTS:
            candidates_by_port.setdefault(port, False)

    # Sort known proxy ports first, then ascending port number; cap probing to 12 ports
    sorted_ports = sorted(
        candidates_by_port.keys(),
        key=lambda p: (0 if p in _COMMON_PROXY_PORTS else 1, p),
    )[:12]

    discovered: List[Dict[str, Any]] = []
    http_likely_ports = {3128, 7890, 7891, 8080, 8118, 8888, 10809, 10811, 2081}
    for port in sorted_ports:
        is_socks, req_auth = _probe_socks5_noauth("127.0.0.1", port, timeout=0.25)
        if is_socks and not req_auth:
            discovered.append({
                "url": f"socks5h://127.0.0.1:{port}",
                "host": "127.0.0.1",
                "port": port,
                "proto": "socks5h",
                "label": f"SOCKS5 Local (127.0.0.1:{port})",
                "verified": True,
            })
        elif port in http_likely_ports:
            discovered.append({
                "url": f"http://127.0.0.1:{port}",
                "host": "127.0.0.1",
                "port": port,
                "proto": "http",
                "label": f"HTTP Proxy (127.0.0.1:{port})",
                "verified": False,
            })

    return discovered


def _get_iface_ipv4_endpoints(iface: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolves `(local_ipv4, peer_ipv4)` for an active Linux tunnel interface."""
    if sys.platform == "win32" or not iface:
        return None, None
    local_ip: Optional[str] = None
    peer_ip: Optional[str] = None
    try:
        out = subprocess.check_output(
            ["ip", "-o", "-4", "addr", "show", "dev", iface],
            text=True, stderr=subprocess.DEVNULL, timeout=2.0
        )
        for line in out.splitlines():
            tokens = line.split()
            if "inet" in tokens:
                idx = tokens.index("inet")
                if idx + 1 < len(tokens):
                    local_ip = tokens[idx + 1].split("/")[0]
            if "peer" in tokens:
                p_idx = tokens.index("peer")
                if p_idx + 1 < len(tokens):
                    peer_ip = tokens[p_idx + 1].split("/")[0]
            if local_ip:
                break
    except Exception:
        pass
    return local_ip, peer_ip


def _resolve_public_ipv4s(hosts: Tuple[str, ...]) -> List[str]:
    """Resolves unique global public IPv4 addresses, filtering out poisoned/private/loopback IPs."""
    ips: List[str] = []
    for host in hosts:
        try:
            infos = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
            for item in infos:
                ip_str = item[4][0]
                try:
                    ip_obj = ipaddress.IPv4Address(ip_str)
                    if ip_obj.is_global and not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast):
                        if ip_str not in ips:
                            ips.append(ip_str)
                except ValueError:
                    pass
        except Exception:
            pass
    return ips


@contextmanager
def _transient_iface_routes(iface: str, hosts: Tuple[str, ...] = ("github.com", "api.github.com")):
    """
    Temporarily injects scoped /32 host routes exclusively for GitHub hosts via `iface`
    without modifying the default gateway or disrupting relay forwarding, then cleans them up.
    """
    if sys.platform == "win32" or not iface:
        yield False
        return
    try:
        from core.config_manager import IFACE_NAME_REGEX
    except ImportError:
        from config_manager import IFACE_NAME_REGEX
    if not IFACE_NAME_REGEX.fullmatch(iface):
        yield False
        return

    with _IFACE_ROUTE_LOCK:
        local_ip, peer_ip = _get_iface_ipv4_endpoints(iface)
        target_ips = _resolve_public_ipv4s(hosts)
        added_ips: List[str] = []
        try:
            for ip_str in target_ips:
                # Skip if kernel already routes this host IP out via the target interface
                already_via_iface = False
                try:
                    rt = subprocess.check_output(
                        ["ip", "-o", "route", "get", ip_str],
                        text=True, stderr=subprocess.DEVNULL, timeout=1.5
                    )
                    if f" dev {iface} " in f" {rt} ":
                        already_via_iface = True
                except Exception:
                    pass
                if already_via_iface:
                    continue

                cmd = ["ip", "route", "replace", f"{ip_str}/32"]
                if peer_ip:
                    cmd.extend(["via", peer_ip])
                cmd.extend(["dev", iface])
                if local_ip:
                    cmd.extend(["src", local_ip])
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
                if res.returncode != 0 and peer_ip:
                    # Fallback without `via` for L3 p2p devices like WireGuard/tun
                    cmd_p2p = ["ip", "route", "replace", f"{ip_str}/32", "dev", iface]
                    if local_ip:
                        cmd_p2p.extend(["src", local_ip])
                    res = subprocess.run(cmd_p2p, capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0:
                    added_ips.append(ip_str)
            yield True
        finally:
            for ip_str in added_ips:
                try:
                    subprocess.run(
                        ["ip", "route", "del", f"{ip_str}/32", "dev", iface],
                        capture_output=True, timeout=2.0
                    )
                except Exception:
                    pass


def discover_update_transports(config: Optional[dict] = None) -> Dict[str, Any]:
    """Discovers active server L3 tunnels and local proxies usable for GitHub system updates."""
    try:
        from core.config_manager import load_config, normalize_update_transport_config
    except ImportError:
        from config_manager import load_config, normalize_update_transport_config

    cfg = config if isinstance(config, dict) else load_config()
    norm_cfg = normalize_update_transport_config(cfg.get("system_update"))

    tunnels: List[Dict[str, Any]] = []
    try:
        try:
            from core.system_info import get_network_interfaces_info
        except ImportError:
            from system_info import get_network_interfaces_info
        net_info = get_network_interfaces_info(config_loader_fn=lambda: cfg)
        for t in net_info.get("tunnel_interfaces", []):
            state = str(t.get("state", "DOWN")).upper()
            ip = str(t.get("ip", "") or "")
            peer_ip = str(t.get("peer_ip", "") or "")
            usable = (state == "UP") and (bool(peer_ip) or (bool(ip) and ip != "No IP assigned"))
            tunnels.append({
                "name": t.get("name"),
                "type": t.get("type", "Tunnel"),
                "state": state,
                "ip": ip,
                "peer_ip": peer_ip,
                "reachable": bool(t.get("reachable", False)),
                "latency_ms": t.get("latency_ms"),
                "usable": usable,
            })
        tunnels.sort(key=lambda x: (0 if x["usable"] else 1, 0 if x["reachable"] else 1, x["latency_ms"] or 9999.0, str(x["name"])))
    except Exception:
        pass

    local_proxies = discover_local_proxies(config=cfg)
    return {
        "ok": True,
        "config": norm_cfg,
        "tunnels": tunnels,
        "local_proxies": local_proxies,
    }


def _fetch_github_commit_single(
    mode: str,
    tunnel_iface: str = "",
    proxy_url: str = "",
    mirror_url: str = "",
    timeout: float = 4.0,
) -> Tuple[bool, Dict[str, Optional[str]], Optional[str]]:
    """
    Attempts a single GitHub remote version check via the requested transport (`direct`, `iface`, `proxy`, or `mirror`).
    Uses pure Python stdlib (including RFC 1928 SOCKS5 CONNECT) with bounded git `ls-remote` fallback.
    """
    headers = {
        "User-Agent": "XForwarder-Updater/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token.strip()}"

    api_url = build_mirror_api_url(mirror_url) if mode == "mirror" else _GITHUB_API_URL
    git_url = build_mirror_git_url(mirror_url) if mode == "mirror" else _GITHUB_REPO_URL

    result = {
        "remote_commit": None,
        "remote_commit_msg": None,
        "remote_date": None,
        "repo_url": "https://github.com/PouryaDe/XForwarder",
    }
    last_err: Optional[str] = None

    def _parse_api_json(raw_text: str) -> bool:
        body = json.loads(raw_text)
        sha = body.get("sha", "")
        if not sha:
            return False
        result["remote_commit"] = sha[:7]
        commit_info = body.get("commit", {})
        result["remote_commit_msg"] = commit_info.get("message", "").strip().split("\n")[0]
        author_date = commit_info.get("author", {}).get("date") or commit_info.get("committer", {}).get("date", "")
        if author_date:
            result["remote_date"] = author_date[:10]
        return True

    def _run_http_and_git(active_proxy: str = "") -> bool:
        nonlocal last_err
        # 1. HTTP/HTTPS API check
        try:
            if active_proxy:
                parsed_p = urllib.parse.urlparse(active_proxy)
                scheme = parsed_p.scheme.lower()
                if scheme in ("socks5", "socks5h"):
                    parsed_api = urllib.parse.urlparse(api_url)
                    conn = _HttpsViaSocks5Connection(
                        parsed_api.hostname,
                        proxy_host=parsed_p.hostname,
                        proxy_port=parsed_p.port or 1080,
                        proxy_user=parsed_p.username,
                        proxy_pass=parsed_p.password,
                        port=parsed_api.port or 443,
                        timeout=timeout,
                    )
                    try:
                        path = parsed_api.path or "/"
                        if parsed_api.query:
                            path += f"?{parsed_api.query}"
                        conn.request("GET", path, headers=headers)
                        resp = conn.getresponse()
                        if resp.status == 200:
                            if _parse_api_json(resp.read().decode("utf-8")):
                                return True
                        else:
                            last_err = f"HTTP {resp.status}"
                    finally:
                        conn.close()
                else:
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler({"http": active_proxy, "https": active_proxy})
                    )
                    req = urllib.request.Request(api_url, headers=headers)
                    with opener.open(req, timeout=timeout) as resp:
                        if resp.status == 200 and _parse_api_json(resp.read().decode("utf-8")):
                            return True
            else:
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200 and _parse_api_json(resp.read().decode("utf-8")):
                        return True
        except Exception as e:
            last_err = str(e)

        # 2. Fallback: git ls-remote (works reliably even on API rate limits or Git mirrors)
        try:
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GIT_HTTP_LOW_SPEED_LIMIT"] = "1024"
            env["GIT_HTTP_LOW_SPEED_TIME"] = "5"
            git_cmd = ["git"]
            if active_proxy:
                git_cmd.extend(["-c", f"http.proxy={active_proxy}"])
            git_cmd.extend(["ls-remote", git_url, "refs/heads/main"])
            res = subprocess.run(git_cmd, capture_output=True, text=True, timeout=max(4.0, timeout + 1.0), env=env)
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split()
                if parts and len(parts[0]) >= 7:
                    result["remote_commit"] = parts[0][:7]
                    result["remote_commit_msg"] = "Latest release on main"
                    return True
            elif res.stderr.strip() and not last_err:
                last_err = res.stderr.strip().splitlines()[-1]
        except Exception as e:
            if not last_err:
                last_err = str(e)
        return False

    if mode == "iface" and tunnel_iface:
        with _transient_iface_routes(tunnel_iface):
            ok = _run_http_and_git("")
        return ok, result, (None if ok else (last_err or f"Tunnel {tunnel_iface} could not reach GitHub"))
    if mode == "proxy" and proxy_url:
        ok = _run_http_and_git(proxy_url)
        return ok, result, (None if ok else (last_err or f"Proxy {proxy_url} could not reach GitHub"))
    ok = _run_http_and_git("")
    return ok, result, (None if ok else (last_err or "Could not reach GitHub"))


def get_remote_version_info(force: bool = False, transport_override: Optional[dict] = None) -> dict:
    """Checks remote GitHub repository for latest commit using configured/auto-discovered tunnel or proxy."""
    try:
        from core.config_manager import load_config, normalize_update_transport_config
    except ImportError:
        from config_manager import load_config, normalize_update_transport_config

    cfg = load_config()
    saved_t = normalize_update_transport_config(cfg.get("system_update"))
    if isinstance(transport_override, dict):
        eff_t = normalize_update_transport_config({**saved_t, **transport_override})
    else:
        eff_t = saved_t

    cache_key = (eff_t["transport_mode"], eff_t["tunnel_iface"], eff_t["proxy_url"], eff_t["mirror_url"])
    now = time.time()
    with _REMOTE_VERSION_LOCK:
        if (
            not force
            and _REMOTE_VERSION_CACHE["data"]
            and _REMOTE_VERSION_CACHE.get("key") == cache_key
            and now < _REMOTE_VERSION_CACHE["expires"]
        ):
            return _REMOTE_VERSION_CACHE["data"]

    remote: Dict[str, Any] = {
        "remote_commit": None,
        "remote_commit_msg": None,
        "remote_date": None,
        "repo_url": "https://github.com/PouryaDe/XForwarder",
        "checked_at": int(now),
        "error": None,
        "used_transport": None,
    }

    mode = eff_t["transport_mode"]
    api_success = False
    first_error: Optional[str] = None

    attempts: List[Tuple[str, str, str, str, str]] = []
    if mode == "direct":
        attempts.append(("direct", "", "", "", "Direct Internet"))
    elif mode == "iface" and eff_t["tunnel_iface"]:
        attempts.append(("iface", eff_t["tunnel_iface"], "", "", f"Tunnel ({eff_t['tunnel_iface']})"))
    elif mode == "proxy" and eff_t["proxy_url"]:
        attempts.append(("proxy", "", eff_t["proxy_url"], "", f"Proxy ({eff_t['proxy_url']})"))
    elif mode == "mirror" and eff_t["mirror_url"]:
        attempts.append(("mirror", "", "", eff_t["mirror_url"], "GitHub Mirror"))
    else:
        # Auto mode: Direct -> saved proxy/mirror/iface -> discovered local proxies -> active UP L3 tunnels
        attempts.append(("direct", "", "", "", "Direct Internet"))
        if eff_t["proxy_url"]:
            attempts.append(("proxy", "", eff_t["proxy_url"], "", f"Proxy ({eff_t['proxy_url']})"))
        if eff_t["tunnel_iface"]:
            attempts.append(("iface", eff_t["tunnel_iface"], "", "", f"Tunnel ({eff_t['tunnel_iface']})"))
        if eff_t["mirror_url"]:
            attempts.append(("mirror", "", "", eff_t["mirror_url"], "GitHub Mirror"))

        disc = discover_update_transports(config=cfg)
        for p in disc.get("local_proxies", []):
            if p["url"] != eff_t["proxy_url"]:
                attempts.append(("proxy", "", p["url"], "", p.get("label") or p["url"]))
        for t_info in disc.get("tunnels", []):
            if t_info.get("usable") and t_info.get("name") and t_info["name"] != eff_t["tunnel_iface"]:
                attempts.append(("iface", t_info["name"], "", "", f"Tunnel ({t_info['name']})"))

    seen_attempts: Set[Tuple[str, str, str, str]] = set()
    for a_mode, a_iface, a_proxy, a_mirror, a_label in attempts:
        akey = (a_mode, a_iface, a_proxy, a_mirror)
        if akey in seen_attempts:
            continue
        seen_attempts.add(akey)
        ok, data, err = _fetch_github_commit_single(
            a_mode,
            tunnel_iface=a_iface,
            proxy_url=a_proxy,
            mirror_url=a_mirror,
            timeout=3.5 if mode == "auto" else 5.0,
        )
        if ok:
            remote.update(data)
            remote["error"] = None
            remote["used_transport"] = {
                "mode": a_mode,
                "target": a_iface or a_proxy or a_mirror or "direct",
                "label": a_label,
            }
            api_success = True
            break
        elif first_error is None:
            first_error = err

    if not api_success:
        remote["error"] = first_error or "Could not reach GitHub"

    with _REMOTE_VERSION_LOCK:
        _REMOTE_VERSION_CACHE["data"] = remote
        _REMOTE_VERSION_CACHE["key"] = cache_key
        _REMOTE_VERSION_CACHE["expires"] = now + (180.0 if api_success else 30.0)

    return remote


def get_full_version_status(
    force: bool = False,
    get_local_version_fn: Optional[Any] = None,
    get_remote_version_fn: Optional[Any] = None
) -> dict:
    """Returns composite version status comparing local and remote GitHub states."""
    local_fn = get_local_version_fn or get_local_version_info
    remote_fn = get_remote_version_fn or get_remote_version_info
    local_info = local_fn()
    remote_info = remote_fn(force=force)

    update_available = False
    local_commit = (local_info.get("commit") or "").lower()
    remote_commit = (remote_info.get("remote_commit") or "").lower()

    if remote_commit:
        if local_commit:
            if local_commit != remote_commit:
                update_available = True
        else:
            update_available = True

    return {
        "ok": True,
        "current_version": local_info["version"],
        "current_commit": local_info["commit"],
        "current_date": local_info["commit_date"],
        "is_git": local_info["is_git"],
        "remote_commit": remote_info.get("remote_commit"),
        "remote_commit_msg": remote_info.get("remote_commit_msg"),
        "remote_date": remote_info.get("remote_date"),
        "repo_url": remote_info.get("repo_url"),
        "checked_at": remote_info.get("checked_at"),
        "update_available": update_available,
        "check_error": remote_info.get("error"),
        "used_transport": remote_info.get("used_transport"),
    }


def get_update_log_path() -> str:
    """Resolves path to update log file in /run/xforwarder or system tempdir."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "update.log")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/update.log"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_update.log")


def get_script_path() -> Optional[str]:
    """Finds executable xforwarder.sh on host."""
    candidates = [
        "/opt/xforwarder/xforwarder.sh",
        os.path.join(BASE_DIR, "xforwarder.sh"),
        "/usr/local/bin/xforwarder",
        "/usr/local/bin/xfwd"
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def start_system_update(transport_override: Optional[dict] = None) -> Tuple[bool, str]:
    """Triggers an unattended background update via systemd-run or detached process using active transport settings."""
    try:
        from core.config_manager import load_config, normalize_update_transport_config, validate_update_transport_config
    except ImportError:
        from config_manager import load_config, normalize_update_transport_config, validate_update_transport_config

    if transport_override is not None:
        ok_v, err_v, eff_t = validate_update_transport_config(transport_override, require_target=True)
        if not ok_v:
            return False, err_v
    else:
        eff_t = normalize_update_transport_config(load_config().get("system_update"))

    with _UPDATE_LOCK:
        now = time.time()
        if _UPDATE_STATE["status"] == "running" and (now - _UPDATE_STATE["start_time"]) < 180:
            return False, "An update is already in progress"

        script = get_script_path()
        if not script:
            return False, "XForwarder update script (xforwarder.sh) not found on host"

        log_path = get_update_log_path()
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== XForwarder Update Initiated at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.flush()
        except Exception as e:
            return False, f"Failed to initialize update log: {e}"

        _UPDATE_STATE["status"] = "running"
        _UPDATE_STATE["start_time"] = now
        _UPDATE_STATE["error"] = None
        save_update_state(_UPDATE_STATE)

        has_systemd_run = bool(shutil.which("systemd-run"))
        ts = int(now)

        def _worker():
            try:
                env_prefix = " ".join([
                    "DEBIAN_FRONTEND=noninteractive",
                    "NONINTERACTIVE=1",
                    "YES=1",
                    "GIT_TERMINAL_PROMPT=0",
                    f"XFWD_UPDATE_MODE={shlex.quote(eff_t['transport_mode'])}",
                    f"XFWD_UPDATE_IFACE={shlex.quote(eff_t['tunnel_iface'])}",
                    f"XFWD_UPDATE_PROXY={shlex.quote(eff_t['proxy_url'])}",
                    f"XFWD_UPDATE_MIRROR={shlex.quote(eff_t['mirror_url'])}",
                ])
                cmd_str = f"{env_prefix} bash {shlex.quote(script)} update >> {shlex.quote(log_path)} 2>&1"
                if has_systemd_run:
                    unit_name = f"xfwd-updater-{ts}"
                    run_cmd = [
                        "systemd-run",
                        f"--unit={unit_name}",
                        "--description=XForwarder Web Update",
                        "bash", "-c", cmd_str
                    ]
                    res = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10.0)
                    if res.returncode != 0:
                        subprocess.Popen(["bash", "-c", cmd_str], start_new_session=True)
                else:
                    if sys.platform == "win32":
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write("[OK] XForwarder updated successfully! All services are active and running.\n")
                        with _UPDATE_LOCK:
                            _UPDATE_STATE["status"] = "completed"
                            save_update_state(_UPDATE_STATE)
                    else:
                        subprocess.Popen(["bash", "-c", cmd_str], start_new_session=True)
            except Exception as ex:
                with _UPDATE_LOCK:
                    _UPDATE_STATE["status"] = "failed"
                    _UPDATE_STATE["error"] = str(ex)
                    save_update_state(_UPDATE_STATE)
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n[ERROR] Update runner failure: {ex}\n")
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return True, "Update initiated"


def get_update_status(log_path_fn: Optional[Any] = None) -> dict:
    """Returns current update execution state and sanitized log output."""
    log_path = log_path_fn() if log_path_fn else get_update_log_path()
    raw_log = ""
    mtime = 0.0
    if os.path.exists(log_path):
        try:
            mtime = os.path.getmtime(log_path)
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                raw_log = f.read()
        except Exception:
            pass

    clean_log = re.sub(r'\x1b\[[0-9;]*m', '', raw_log)
    now = time.time()

    with _UPDATE_LOCK:
        mem_status = _UPDATE_STATE["status"]
        start_time = _UPDATE_STATE["start_time"]

    status = "idle"
    is_recent_success = "XForwarder updated successfully!" in clean_log and (
        (start_time > 0 and mtime >= start_time - 5) or (mtime > 0 and (now - mtime) < 180)
    )
    if is_recent_success:
        status = "completed"
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "completed"
            save_update_state(_UPDATE_STATE)
    elif mem_status == "running":
        if (now - start_time) > 300:
            status = "failed"
            with _UPDATE_LOCK:
                _UPDATE_STATE["status"] = "failed"
                save_update_state(_UPDATE_STATE)
        else:
            status = "running"
    elif mtime > 0 and (now - mtime) < 45 and (start_time == 0 or (now - start_time) < 300):
        status = "running"
    elif ("Could not pull updates" in clean_log or "Failed to install" in clean_log or "[ERROR]" in clean_log) and (
        (start_time > 0 and mtime >= start_time - 5) or (mtime > 0 and (now - mtime) < 180)
    ):
        status = "failed"
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "failed"
            save_update_state(_UPDATE_STATE)

    return {
        "ok": True,
        "status": status,
        "start_time": start_time,
        "log": clean_log[-12000:] if len(clean_log) > 12000 else clean_log
    }


def _strip_nginx_comments(text: str) -> str:
    """Strips `#` comments from Nginx configuration lines."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _parse_nginx_listen_directive(arg_str: str) -> Tuple[Optional[int], str]:
    """Parses `listen [addr:]port [udp|...]` into `(port, 'tcp'|'udp')`."""
    tokens = arg_str.strip().split()
    if not tokens:
        return None, "tcp"
    proto = "udp" if any(t.lower() == "udp" for t in tokens[1:]) else "tcp"
    addr_tok = tokens[0].strip()
    m = re.match(r"^(?:\[[^\]]+\]:|[^:\s]+:)?(\d{1,5})$", addr_tok)
    if not m:
        return None, proto
    p = int(m.group(1))
    return (p if 1 <= p <= 65535 else None), proto


def _parse_nginx_host_port(raw_addr: str) -> Tuple[str, Optional[int]]:
    """Extracts `(host, port)` from `host:port` or `[ipv6]:port`."""
    s = raw_addr.strip()
    m_v6 = re.match(r"^\[([0-9a-fA-F:]+)\]:(\d{1,5})$", s)
    if m_v6:
        p = int(m_v6.group(2))
        return m_v6.group(1), (p if 1 <= p <= 65535 else None)
    m_v4 = re.match(r"^([^:\s]+):(\d{1,5})$", s)
    if m_v4:
        p = int(m_v4.group(2))
        return m_v4.group(1), (p if 1 <= p <= 65535 else None)
    return "", None


def parse_nginx_stream_endpoints(
    nginx_paths: Optional[List[str]] = None
) -> Dict[int, List[Tuple[str, str, int]]]:
    """
    Parses active Nginx `stream { server { listen ...; proxy_pass ...; } }` blocks.
    Returns `{inbound_port: [(protocol, target_host, target_port), ...]}`.
    Returns `{}` when Nginx is uninstalled or has no stream forwarding entries.
    """
    if nginx_paths is None:
        paths: List[str] = []
        if os.path.isfile("/etc/nginx/nginx.conf"):
            paths.append("/etc/nginx/nginx.conf")
        for pat in (
            "/etc/nginx/conf.d/*.conf",
            "/etc/nginx/streams-enabled/*",
            "/etc/nginx/stream.d/*.conf",
        ):
            paths.extend(sorted(glob.glob(pat)))
    else:
        paths = [p for p in nginx_paths if os.path.isfile(p)]

    if not paths:
        return {}

    upstreams: Dict[str, List[Tuple[str, int]]] = {}
    raw_entries: Dict[Tuple[int, str, int], Set[str]] = {}

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                cleaned = _strip_nginx_comments(f.read())
        except Exception:
            continue

        # Treat standalone files in streams-enabled / stream.d as already inside stream context
        in_stream_file = ("streams-enabled" in path or "stream.d" in path)
        depth = 0
        stream_depth = 0 if in_stream_file else -1
        http_depth = -1
        upstream_name = ""
        upstream_depth = -1
        in_server = False
        server_depth = -1
        cur_listens: List[Tuple[int, str]] = []
        cur_proxy_raw = ""

        # Tokenize braces and semicolons to handle single-line and multi-line Nginx blocks uniformly
        tokens = re.findall(r"[{}]|\n|[^;{}\n]+;?", cleaned)
        for tok in tokens:
            s = tok.strip()
            if not s:
                continue
            if s == "{":
                depth += 1
                continue
            if s == "}":
                depth = max(0, depth - 1)
                if in_server and depth <= server_depth:
                    if cur_proxy_raw:
                        tgt_host, tgt_port = _parse_nginx_host_port(cur_proxy_raw)
                        if tgt_host and tgt_port:
                            for lp, lproto in cur_listens:
                                raw_entries.setdefault((lp, tgt_host, tgt_port), set()).add(lproto)
                        elif cur_proxy_raw in upstreams:
                            for uh, up in upstreams[cur_proxy_raw]:
                                for lp, lproto in cur_listens:
                                    raw_entries.setdefault((lp, uh, up), set()).add(lproto)
                    in_server = False
                    server_depth = -1
                    cur_listens = []
                    cur_proxy_raw = ""
                if upstream_name and depth <= upstream_depth:
                    upstream_name = ""
                    upstream_depth = -1
                if not in_stream_file and stream_depth >= 0 and depth <= stream_depth:
                    stream_depth = -1
                if http_depth >= 0 and depth <= http_depth:
                    http_depth = -1
                continue

            stmt = s.rstrip(";").strip()
            low = stmt.lower()
            if re.match(r"^stream\b", low):
                stream_depth = depth
                continue
            if re.match(r"^http\b", low):
                http_depth = depth
                continue
            if http_depth >= 0 and stream_depth < 0:
                continue

            m_up = re.match(r"^upstream\s+(\S+)$", stmt, re.IGNORECASE)
            if m_up and (stream_depth >= 0 or in_stream_file):
                upstream_name = m_up.group(1).strip()
                upstream_depth = depth
                continue

            if upstream_name:
                m_srv = re.match(r"^server\s+(\S+)", stmt, re.IGNORECASE)
                if m_srv:
                    uh, up = _parse_nginx_host_port(m_srv.group(1))
                    if uh and up:
                        upstreams.setdefault(upstream_name, []).append((uh, up))
                continue

            if low == "server" and (stream_depth >= 0 or in_stream_file):
                in_server = True
                server_depth = depth
                cur_listens = []
                cur_proxy_raw = ""
                continue

            if in_server:
                m_listen = re.match(r"^listen\s+(.+)$", stmt, re.IGNORECASE)
                if m_listen:
                    lp, lproto = _parse_nginx_listen_directive(m_listen.group(1))
                    if lp is not None:
                        cur_listens.append((lp, lproto))
                    continue
                m_pass = re.match(r"^proxy_pass\s+(\S+)", stmt, re.IGNORECASE)
                if m_pass:
                    cur_proxy_raw = m_pass.group(1).strip()

    grouped: Dict[int, List[Tuple[str, str, int]]] = {}
    for (lp, thost, tport), protos in sorted(raw_entries.items()):
        proto = "both" if protos == {"tcp", "udp"} else next(iter(protos))
        grouped.setdefault(lp, []).append((proto, thost, tport))
    return grouped


def sync_xforwarder_from_nginx(
    config_path: Optional[str] = None,
    nginx_paths: Optional[List[str]] = None,
    sync_rules_func=None,
    notify_func=None,
) -> Tuple[bool, str, bool]:
    """
    Reconciles XForwarder `config.json` from Nginx stream configs (Nginx -> XForwarder).
    Removes `nginx` destinations that no longer exist in Nginx (including all when Nginx is empty)
    and imports missing Nginx stream servers into `config.json` atomically.
    """
    try:
        from core.config_manager import get_config_path, load_config, save_config, validate_rule
    except ImportError:
        from config_manager import get_config_path, load_config, save_config, validate_rule

    path = get_config_path(config_path)
    cfg = load_config(path)
    nginx_map = parse_nginx_stream_endpoints(nginx_paths=nginx_paths)

    removed_dests = 0
    removed_rules = 0
    added_rules = 0
    updated_pools = 0
    new_rules: List[Dict[str, Any]] = []
    existing_nginx_keys: Set[Tuple[int, str, int]] = set()
    rules_by_port: Dict[int, Dict[str, Any]] = {}

    for rule in cfg.get("rules", []):
        if not isinstance(rule, dict):
            continue
        r_port = rule.get("port")
        is_range = bool(rule.get("port_range"))
        dests = rule.get("destinations", [])
        if is_range or not isinstance(dests, list):
            new_rules.append(rule)
            continue

        kept_dests: List[Dict[str, Any]] = []
        removed_prios: Set[int] = set()
        active_set = set()
        for proto, thost, tport in nginx_map.get(r_port, []):
            active_set.add((thost.strip("[]"), tport))

        for d in dests:
            if str(d.get("type", "")).lower() == "nginx":
                if d.get("lb_enabled") and isinstance(d.get("lb_targets"), list):
                    kept_members: List[Dict[str, Any]] = []
                    for m in d["lb_targets"]:
                        if not isinstance(m, dict):
                            continue
                        m_host = str(m.get("target", "")).strip().strip("[]")
                        try:
                            m_port = int(m.get("port") or d.get("port") or r_port)
                        except (ValueError, TypeError):
                            m_port = r_port
                        if (m_host, m_port) in active_set:
                            kept_members.append(m)
                            existing_nginx_keys.add((r_port, m_host, m_port))
                    if len(kept_members) >= 2:
                        if len(kept_members) != len(d["lb_targets"]):
                            updated_pools += 1
                        d["lb_targets"] = kept_members
                        first_m = next((x for x in kept_members if x.get("enabled", True)), kept_members[0])
                        d["target"] = first_m["target"]
                        d["port"] = first_m.get("port", r_port)
                        kept_dests.append(d)
                    elif len(kept_members) == 1:
                        updated_pools += 1
                        only_m = kept_members[0]
                        d.pop("lb_enabled", None)
                        d.pop("lb_mode", None)
                        d.pop("lb_targets", None)
                        d["target"] = only_m["target"]
                        d["port"] = only_m.get("port", r_port)
                        kept_dests.append(d)
                    else:
                        removed_dests += 1
                        try:
                            removed_prios.add(int(d.get("priority", 0)))
                        except (ValueError, TypeError):
                            pass
                    continue

                d_host = str(d.get("target", "")).strip().strip("[]")
                try:
                    d_port = int(d.get("port") or r_port)
                except (ValueError, TypeError):
                    d_port = r_port
                if (d_host, d_port) in active_set:
                    kept_dests.append(d)
                    existing_nginx_keys.add((r_port, d_host, d_port))
                else:
                    removed_dests += 1
                    try:
                        removed_prios.add(int(d.get("priority", 0)))
                    except (ValueError, TypeError):
                        pass
            else:
                kept_dests.append(d)

        if not kept_dests:
            removed_rules += 1
            continue

        if removed_prios:
            old_active = rule.get("active_priority", 1)
            old_force = rule.get("force_override", 0)
            new_active = None
            new_force = 0
            for idx, d in enumerate(kept_dests, start=1):
                old_p = d.get("priority", idx)
                d["priority"] = idx
                if old_p == old_active:
                    new_active = idx
                if old_p == old_force and old_force:
                    new_force = idx
            if new_active is None:
                enabled_p = [d["priority"] for d in kept_dests if d.get("enabled", True)]
                new_active = enabled_p[0] if enabled_p else 1
            rule["active_priority"] = new_active
            rule["force_override"] = new_force

        rule["destinations"] = kept_dests
        new_rules.append(rule)
        if isinstance(r_port, int):
            rules_by_port[r_port] = rule

    # Import any active Nginx stream servers missing from XForwarder
    for lp, entries in sorted(nginx_map.items()):
        missing_entries = [
            (proto, thost, tport)
            for proto, thost, tport in entries
            if (lp, thost.strip("[]"), tport) not in existing_nginx_keys
        ]
        if not missing_entries:
            continue
        existing_rule = rules_by_port.get(lp)
        if existing_rule is None and len(missing_entries) >= 2:
            merged_protos = {p for p, _, _ in missing_entries}
            rule_proto = "both" if ("both" in merged_protos or merged_protos == {"tcp", "udp"}) else next(iter(merged_protos))
            lb_targets = [
                {
                    "target": thost.strip("[]"),
                    "port": tport,
                    "weight": 1,
                    "enabled": True,
                    "comment": "Synced from Nginx upstream"
                }
                for _, thost, tport in missing_entries
            ]
            cand_rule: Dict[str, Any] = {
                "id": f"rule-{lp}",
                "port": lp,
                "protocol": rule_proto,
                "active_priority": 1,
                "force_override": 0,
                "destinations": [
                    {
                        "priority": 1,
                        "type": "nginx",
                        "target": lb_targets[0]["target"],
                        "port": lb_targets[0]["port"],
                        "proxy_protocol": False,
                        "enabled": True,
                        "is_relay": False,
                        "lb_enabled": True,
                        "lb_mode": "round_robin",
                        "lb_targets": lb_targets,
                        "comment": "Synced from Nginx upstream"
                    }
                ]
            }
            ok, _ = validate_rule(cand_rule)
            if ok:
                new_rules.append(cand_rule)
                rules_by_port[lp] = cand_rule
                added_rules += 1
                for _, thost, tport in missing_entries:
                    existing_nginx_keys.add((lp, thost.strip("[]"), tport))
                continue

        for proto, thost, tport in missing_entries:
            key = (lp, thost.strip("[]"), tport)
            if key in existing_nginx_keys:
                continue
            existing_rule = rules_by_port.get(lp)
            if existing_rule is not None:
                next_prio = len(existing_rule["destinations"]) + 1
                existing_rule["destinations"].append({
                    "priority": next_prio,
                    "type": "nginx",
                    "target": thost,
                    "port": tport,
                    "proxy_protocol": False,
                    "enabled": True,
                    "is_relay": False,
                    "comment": "Synced from Nginx stream"
                })
                added_rules += 1
            else:
                cand_rule = {
                    "id": f"rule-{lp}",
                    "port": lp,
                    "protocol": proto,
                    "active_priority": 1,
                    "force_override": 0,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nginx",
                            "target": thost,
                            "port": tport,
                            "proxy_protocol": False,
                            "enabled": True,
                            "is_relay": False,
                            "comment": "Synced from Nginx stream"
                        }
                    ]
                }
                ok, _ = validate_rule(cand_rule)
                if ok:
                    new_rules.append(cand_rule)
                    rules_by_port[lp] = cand_rule
                    added_rules += 1
            existing_nginx_keys.add(key)

    if removed_dests == 0 and removed_rules == 0 and added_rules == 0 and updated_pools == 0:
        return True, "XForwarder rules already match Nginx stream configuration", False

    if os.path.exists(path):
        try:
            shutil.copy2(path, f"{path}.bak.{int(time.time())}")
        except Exception:
            pass

    cfg["rules"] = new_rules
    if not save_config(cfg, config_path=path):
        return False, "Failed to save updated configuration after Nginx sync", False

    if sync_rules_func:
        sync_rules_func()
    if notify_func:
        notify_func()

    return (
        True,
        f"Synced XForwarder from Nginx: removed {removed_dests} Nginx destination(s), "
        f"{removed_rules} empty rule(s), added {added_rules} rule(s).",
        False,
    )


def _find_unmanaged_nginx_files() -> List[str]:
    """Returns existing Nginx config files that are NOT generated by XForwarder."""
    candidates: List[str] = []
    main_conf = "/etc/nginx/nginx.conf"
    if os.path.isfile(main_conf):
        try:
            with open(main_conf, "r", encoding="utf-8", errors="ignore") as f:
                if "# Generated by XForwarder" not in f.read(512):
                    candidates.append(main_conf)
        except Exception:
            pass
    for pat in (
        "/etc/nginx/streams-enabled/*",
        "/etc/nginx/stream.d/*.conf",
        "/etc/nginx/conf.d/*.conf",
    ):
        for p in sorted(glob.glob(pat)):
            if os.path.isfile(p) and p not in candidates:
                candidates.append(p)
    return candidates


def discover_importable_nginx_rules(
    existing_rules: Optional[List[Dict[str, Any]]] = None,
    protected_ports: Optional[Set[int]] = None
) -> List[Dict[str, Any]]:
    """
    Discovers unmanaged Nginx `stream { server { ... } }` forwarding rules not yet present
    in existing_rules (overlapping via rules_ports_overlap and respecting protected_ports).
    """
    nginx_paths = _find_unmanaged_nginx_files()
    if not nginx_paths:
        return []

    try:
        from core.config_manager import rules_ports_overlap, get_rule_port_bounds, validate_rule
    except ImportError:
        from config_manager import rules_ports_overlap, get_rule_port_bounds, validate_rule

    configured_rules: List[Dict[str, Any]] = [
        r for r in (existing_rules or [])
        if isinstance(r, dict) and get_rule_port_bounds(r)[0] is not None
    ]
    prot = set(protected_ports or {22})
    stream_map = parse_nginx_stream_endpoints(nginx_paths=nginx_paths)
    discovered: List[Dict[str, Any]] = []

    for lp, entries in sorted(stream_map.items()):
        if lp in prot or not entries:
            continue
        if len(entries) >= 2:
            merged_protos = {p for p, _, _ in entries}
            proto = "both" if ("both" in merged_protos or merged_protos == {"tcp", "udp"}) else next(iter(merged_protos))
            lb_targets = [
                {
                    "target": thost.strip("[]"),
                    "port": tport,
                    "weight": 1,
                    "enabled": True,
                    "comment": "Imported from Nginx upstream"
                }
                for _, thost, tport in entries
            ]
            dest_obj: Dict[str, Any] = {
                "priority": 1,
                "type": "nginx",
                "target": lb_targets[0]["target"],
                "port": lb_targets[0]["port"],
                "proxy_protocol": False,
                "enabled": True,
                "is_relay": False,
                "lb_enabled": True,
                "lb_mode": "round_robin",
                "lb_targets": lb_targets,
                "comment": "Imported from Nginx upstream"
            }
        else:
            proto, thost, tport = entries[0]
            dest_obj = {
                "priority": 1,
                "type": "nginx",
                "target": thost,
                "port": tport,
                "proxy_protocol": False,
                "enabled": True,
                "is_relay": False,
                "comment": "Imported from Nginx stream"
            }
        cand: Dict[str, Any] = {
            "id": f"rule-{lp}",
            "port": lp,
            "protocol": proto,
            "active_priority": 1,
            "force_override": 0,
            "destinations": [dest_obj],
            "_source": "nginx"
        }
        ok, _ = validate_rule(dict(cand))
        if not ok:
            continue
        if any(rules_ports_overlap(cand, ex) for ex in configured_rules):
            continue
        if any(rules_ports_overlap(cand, d) for d in discovered):
            continue
        discovered.append(cand)

    return discovered


def cleanup_legacy_nginx_files(backup_dir: str = "/etc/xforwarder/backups") -> List[str]:
    """
    Archives pre-existing Nginx backups (`nginx.conf.bak*`) and unmanaged stream drop-in files
    into /etc/xforwarder/backups/ so deleted rules cannot reappear.
    """
    logs: List[str] = []
    files_to_move: List[str] = []
    for pat in (
        "/etc/nginx/nginx.conf.bak*",
        "/etc/nginx/streams-enabled/*",
        "/etc/nginx/stream.d/*.conf",
    ):
        for p in sorted(glob.glob(pat)):
            if os.path.isfile(p) and p not in files_to_move:
                files_to_move.append(p)

    # Archive unmanaged nginx.conf copy (apply_nginx will rewrite it cleanly on sync)
    unmanaged_main = ""
    if os.path.isfile("/etc/nginx/nginx.conf"):
        try:
            with open("/etc/nginx/nginx.conf", "r", encoding="utf-8", errors="ignore") as f:
                if "# Generated by XForwarder" not in f.read(512):
                    unmanaged_main = "/etc/nginx/nginx.conf"
        except Exception:
            pass

    if not files_to_move and not unmanaged_main:
        return logs

    ts = time.strftime("%Y%m%d_%H%M%S")
    dest_dir = os.path.join(backup_dir, f"legacy_nginx_{ts}")
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except Exception as e:
        return [f"Warning: could not create Nginx backup dir: {e}"]

    if unmanaged_main:
        try:
            shutil.copy2(unmanaged_main, os.path.join(dest_dir, "nginx.conf.orig"))
            logs.append(f"Backed up legacy {unmanaged_main} -> {dest_dir}/nginx.conf.orig")
        except Exception as e:
            logs.append(f"Warning: failed backing up {unmanaged_main}: {e}")

    for src in files_to_move:
        try:
            dst = os.path.join(dest_dir, os.path.basename(src))
            shutil.move(src, dst)
            logs.append(f"Archived legacy Nginx file {src} -> {dst}")
        except Exception as e:
            logs.append(f"Warning: failed archiving {src}: {e}")
    return logs


def import_nginx_rules_into_config(
    config_path: str,
    cleanup_legacy: bool = True
) -> Tuple[int, List[int], List[str]]:
    """Discovers unmanaged Nginx stream rules and merges them into config_path atomically."""
    logs: List[str] = []
    if not os.path.exists(config_path):
        return 0, [], logs
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        return 0, [], [f"Error reading config: {e}"]

    try:
        from core.config_manager import get_protected_ports
    except ImportError:
        from config_manager import get_protected_ports

    rules = cfg.get("rules", [])
    importable = discover_importable_nginx_rules(rules, protected_ports=get_protected_ports(cfg))
    if not importable:
        return 0, [], logs

    imported_ports: List[int] = []
    for r in importable:
        clean_r = {k: v for k, v in r.items() if not k.startswith("_")}
        rules.append(clean_r)
        imported_ports.append(clean_r["port"])

    cfg["rules"] = rules
    tmp_path = f"{config_path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, config_path)
        logs.append(f"Imported {len(imported_ports)} Nginx stream rule(s): {imported_ports}")
        if cleanup_legacy:
            logs.extend(cleanup_legacy_nginx_files())
        return len(imported_ports), imported_ports, logs
    except Exception as e:
        return 0, [], [f"Failed to save Nginx imported rules: {e}"]


def restart_services_action(service: str, sync_rules_func=None, notify_func=None) -> Tuple[bool, str, bool]:
    """
    Executes controlled service restart or reload.
    Supports: 'all', 'engine', 'web', 'haproxy', 'haproxy_restart',
              'nginx', 'nginx_sync', 'nginx_pull', 'nginx_restart', 'nftables', 'nftables_restart'.
    Returns: (success: bool, message: str, is_reconnecting: bool)
    """
    valid_services = {
        "all", "engine", "web",
        "haproxy", "haproxy_restart",
        "nginx", "nginx_sync", "nginx_pull", "nginx_restart",
        "nftables", "nftables_restart"
    }
    svc = str(service or "all").lower().strip()
    if svc not in valid_services:
        return False, f"Invalid service identifier '{service}'. Allowed: {', '.join(sorted(valid_services))}", False

    if svc == "nginx_pull":
        return sync_xforwarder_from_nginx(sync_rules_func=sync_rules_func, notify_func=notify_func)

    has_systemctl = bool(shutil.which("systemctl"))
    if sys.platform == "win32" or not has_systemctl:
        if svc in ("all", "web"):
            return True, f"Service '{svc}' restarted (mock)", True
        elif svc in ("nftables", "nftables_restart"):
            if sync_rules_func:
                sync_rules_func()
            msg = "NFTables table restarted and synchronized (mock)" if svc == "nftables_restart" else "NFTables ruleset synchronized (mock)"
            return True, msg, False
        elif svc == "nginx_sync":
            if sync_rules_func:
                sync_rules_func()
            return True, "Nginx stream configuration synchronized (mock)", False
        elif svc in ("haproxy_restart", "nginx_restart", "engine"):
            return True, f"Service '{svc}' restarted successfully (mock)", False
        return True, f"Service '{svc}' reloaded successfully (mock)", False

    if svc == "nftables":
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "NFTables table 'xfwd_orchestrator' re-synchronized successfully", False
            return False, f"Failed to synchronize NFTables: {', '.join(errs)}", False
        return True, "NFTables reload requested", False

    if svc == "nftables_restart":
        if shutil.which("nft"):
            subprocess.run(["nft", "delete", "table", "ip", "xfwd_orchestrator"], capture_output=True, text=True, timeout=5.0)
            subprocess.run(["nft", "delete", "table", "ip6", "xfwd_orchestrator"], capture_output=True, text=True, timeout=5.0)
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "NFTables table 'xfwd_orchestrator' restarted and re-synchronized successfully", False
            return False, f"Failed to restart NFTables table: {', '.join(errs)}", False
        return True, "NFTables table 'xfwd_orchestrator' restarted successfully", False

    if svc == "haproxy":
        res = subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "HAProxy relay service reloaded successfully", False
        return False, f"HAProxy reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "haproxy_restart":
        if sync_rules_func:
            sync_rules_func()
        res = subprocess.run(["systemctl", "restart", "haproxy"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "HAProxy relay service restarted successfully", False
        return False, f"HAProxy restart failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "nginx_sync":
        if sync_rules_func:
            ok, errs = sync_rules_func()
            if ok:
                return True, "Nginx stream configuration synchronized successfully", False
            return False, f"Failed to synchronize Nginx: {', '.join(errs)}", False
        return True, "Nginx synchronization requested", False

    if svc == "nginx":
        res = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "Nginx stream proxy engine reloaded successfully", False
        return False, f"Nginx reload failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "nginx_restart":
        if sync_rules_func:
            sync_rules_func()
        res = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=8.0)
        if res.returncode == 0:
            return True, "Nginx stream proxy engine restarted successfully", False
        return False, f"Nginx restart failed: {res.stderr.strip() or res.stdout.strip()}", False

    if svc == "engine":
        svc_name = "xforwarder.service"
        res = subprocess.run(["systemctl", "restart", svc_name], capture_output=True, text=True, timeout=10.0)
        if res.returncode != 0:
            res = subprocess.run(["systemctl", "restart", "forward-manager.service"], capture_output=True, text=True, timeout=10.0)
        if res.returncode == 0:
            if notify_func:
                notify_func()
            return True, "XForwarder Core Failover Engine restarted successfully", False
        return False, f"Failed to restart core engine: {res.stderr.strip() or res.stdout.strip()}", False

    if svc in ("web", "all"):
        if svc == "all":
            subprocess.run(["systemctl", "restart", "xforwarder.service"], capture_output=True, timeout=5.0)
            subprocess.run(["systemctl", "reload", "haproxy"], capture_output=True, timeout=5.0)
            subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, timeout=5.0)

        def _delayed_web_restart():
            time.sleep(0.6)
            if shutil.which("systemd-run"):
                subprocess.run(
                    ["systemd-run", "--unit=xfwd-restart-job", "systemctl", "restart", "xforwarder-web.service"],
                    capture_output=True
                )
            else:
                subprocess.run(["systemctl", "restart", "xforwarder-web.service"], capture_output=True)

        threading.Thread(target=_delayed_web_restart, daemon=True).start()
        msg = "All XForwarder services are restarting" if svc == "all" else "Web Dashboard service is restarting"
        return True, f"{msg}. Reconnecting in ~2 seconds...", True

    return False, "Unknown action", False


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--discover-update-transports":
        print(json.dumps(discover_update_transports(), ensure_ascii=False))
    elif len(sys.argv) >= 2 and sys.argv[1] == "--resolve-github-ips":
        print("\n".join(_resolve_public_ipv4s(_GITHUB_HOSTS)))
    elif len(sys.argv) >= 2 and sys.argv[1] == "--build-mirror-url":
        raw_m = sys.argv[2] if len(sys.argv) >= 3 else ""
        print(build_mirror_git_url(raw_m))

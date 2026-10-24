#!/usr/bin/env python3
"""
XForwarder - 24/7 Always-Online Web Server
Provides a secure English dashboard with session authentication (Username & Password).
Modular architecture delegating to specialized subsystems (config, auth, system, service, traffic, metrics).
"""

import os
import sys
import time
import threading
import json
import secrets
import ssl
import gzip
import signal
import tempfile
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Tuple, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config_manager import (
    load_config, save_config, load_state, update_state_rules,
    get_config_path, get_state_file_path, validate_rule,
    export_config_data, import_config_data, is_valid_target,
    is_port_in_use_by_external_service, migrate_and_normalize_config,
    CONFIG_PATH, LEGACY_CONFIG_PATH, LOCAL_CONFIG_PATH,
    STATE_FILE_PATH, LEGACY_STATE_FILE_PATH
)
from core.auth import (
    hash_password, verify_password, check_rate_limit, record_failed_login,
    reset_rate_limit,
    load_sessions_from_disk as auth_load_sessions_from_disk,
    save_sessions_to_disk as auth_save_sessions_to_disk,
    get_sessions_file_path as auth_get_sessions_file_path,
    ACTIVE_SESSIONS, SESSION_LOCK,
    SESSION_TTL_HOURS, SESSION_IDLE_TIMEOUT_SECONDS, MAX_ACTIVE_SESSIONS,
    LOCKOUT_DURATION, MAX_FAILED_ATTEMPTS
)
from core.system_info import (
    get_system_stats, get_services_status,
    get_network_interfaces_info as sys_get_network_interfaces_info,
    is_ignored_interface, ping_target, DEFAULT_IGNORED_INTERFACES,
    _VERSION_CACHE, _SERVICES_CACHE, _SERVICES_LOCK, _NET_CACHE, _NET_LOCK
)
from core.service_manager import (
    restart_services_action, start_system_update,
    get_update_status as sm_get_update_status,
    get_installed_version, get_remote_version_info,
    get_full_version_status as sm_get_full_version_status,
    get_local_version_info,
    get_update_state_file_path as sm_get_update_state_file_path,
    get_update_log_path as sm_get_update_log_path,
    save_update_state as sm_save_update_state,
    load_update_state as sm_load_update_state,
    APP_VERSION, _UPDATE_STATE, _UPDATE_LOCK
)

def get_network_interfaces_info() -> Dict[str, Any]:
    return sys_get_network_interfaces_info(config_loader_fn=load_config)

def get_sessions_file_path() -> str:
    return auth_get_sessions_file_path()

def save_sessions_to_disk() -> None:
    auth_save_sessions_to_disk(path_override=get_sessions_file_path())

def load_sessions_from_disk() -> None:
    auth_load_sessions_from_disk(path_override=get_sessions_file_path())

def get_update_state_file_path() -> str:
    return sm_get_update_state_file_path()

def save_update_state(state: Optional[dict] = None) -> None:
    if state is None:
        with _UPDATE_LOCK:
            state = dict(_UPDATE_STATE)
    sm_save_update_state(state, path_override=get_update_state_file_path())

def load_update_state() -> None:
    sm_load_update_state(path_override=get_update_state_file_path())

def get_update_log_path() -> str:
    return sm_get_update_log_path()

def get_update_status() -> dict:
    return sm_get_update_status(log_path_fn=get_update_log_path)

def get_full_version_status(force: bool = False) -> dict:
    return sm_get_full_version_status(
        force=force,
        get_local_version_fn=get_local_version_info,
        get_remote_version_fn=get_remote_version_info
    )

try:
    from core.traffic import get_traffic_summary, get_traffic_timeseries, reset_traffic_counter
except ImportError:
    try:
        from traffic import get_traffic_summary, get_traffic_timeseries, reset_traffic_counter
    except ImportError:
        get_traffic_summary = None
        get_traffic_timeseries = None
        reset_traffic_counter = None

WEB_DIR = os.path.join(BASE_DIR, "web")
_STATIC_CACHE: Dict[str, dict] = {}
_STATIC_LOCK = threading.Lock()

PID_FILE_CANDIDATES = [
    "/run/xforwarder/engine.pid",
    "/run/forward-manager/engine.pid",
    os.path.join(tempfile.gettempdir(), "xforwarder_engine.pid"),
]


def notify_engine_wakeup():
    """Signals core engine to immediately evaluate routing changes without waiting for interval."""
    if hasattr(signal, "SIGUSR1"):
        for pid_file in PID_FILE_CANDIDATES:
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, "r", encoding="utf-8") as f:
                        pid = int(f.read().strip())
                    os.kill(pid, signal.SIGUSR1)
                    break
                except Exception:
                    pass


def sync_rules_and_notify(max_retries: int = 2) -> Tuple[bool, List[str]]:
    try:
        from engine import sync_system_rules
    except ImportError:
        from core.engine import sync_system_rules
    res = sync_system_rules(max_retries=max_retries)
    notify_engine_wakeup()
    return res


# Backward compatibility aliases for engine imports
try:
    from engine import XForwarderEngine
    migrate_config = XForwarderEngine.migrate_and_normalize_config
    from route_quality import pick_best_now
except ImportError:
    try:
        from core.engine import XForwarderEngine
        migrate_config = XForwarderEngine.migrate_and_normalize_config
        from core.route_quality import pick_best_now
    except ImportError:
        migrate_config = migrate_and_normalize_config
        pick_best_now = None


class XForwarderWebHandler(BaseHTTPRequestHandler):
    server_instance: 'XForwarderWebServer'
    server_version = "XForwarder-Shield/2.0"
    sys_version = ""

    def apply_security_headers(self, cookie_token: Optional[str] = None, include_cache_control: bool = True):
        """Applies comprehensive OWASP recommended security headers."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        )
        if include_cache_control:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")

        is_https = self.headers.get("X-Forwarded-Proto") == "https" or (
            hasattr(self, "server_instance") and getattr(self.server_instance, "is_ssl", False)
        )
        host = self.headers.get("Host", "").split(":")[0].lower()
        is_trustworthy = is_https or host in ("localhost", "127.0.0.1", "::1")
        if is_trustworthy:
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")

        secure_flag = "; Secure" if is_https else ""

        if is_https:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        if cookie_token:
            self.send_header("Set-Cookie", f"xfwd_session={cookie_token}; Path=/; HttpOnly; SameSite=Strict{secure_flag}")
        elif cookie_token == "":
            self.send_header("Set-Cookie", f"xfwd_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Strict{secure_flag}")
            self.send_header("Set-Cookie", f"fwdman_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Strict{secure_flag}")

    def send_json(self, data: dict, status: int = 200, cookie_token: Optional[str] = None):
        body = json.dumps(data).encode("utf-8")
        accept_encoding = self.headers.get("Accept-Encoding", "")
        use_gzip = "gzip" in accept_encoding and len(body) > 512
        if use_gzip:
            body = gzip.compress(body)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        if status == 429 and isinstance(data, dict) and "remaining_seconds" in data:
            self.send_header("Retry-After", str(data["remaining_seconds"]))
        self.apply_security_headers(cookie_token=cookie_token)
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path: str, content_type: str):
        if not os.path.exists(file_path):
            self.send_error(404, "File Not Found")
            return

        stat = os.stat(file_path)
        mtime = int(stat.st_mtime)
        size = stat.st_size
        etag = f'W/"{mtime}-{size}"'

        # Conditional request (ETag / 304 Not Modified)
        if_none_match = self.headers.get("If-None-Match", "").strip()
        if if_none_match and if_none_match == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.apply_security_headers(include_cache_control=False)
            self.end_headers()
            return

        # In-memory cached asset retrieval
        with _STATIC_LOCK:
            entry = _STATIC_CACHE.get(file_path)
            if not entry or entry["mtime"] != mtime:
                with open(file_path, "rb") as f:
                    raw_content = f.read()
                gz_content = gzip.compress(raw_content) if len(raw_content) > 512 else None
                entry = {
                    "mtime": mtime,
                    "etag": etag,
                    "content": raw_content,
                    "gz_content": gz_content
                }
                _STATIC_CACHE[file_path] = entry

        accept_encoding = self.headers.get("Accept-Encoding", "")
        can_gzip = "gzip" in accept_encoding and entry["gz_content"] is not None

        content = entry["gz_content"] if can_gzip else entry["content"]

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if can_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.apply_security_headers(include_cache_control=False)
        self.end_headers()
        self.wfile.write(content)

    def get_client_ip(self) -> str:
        """Extracts remote client IP with reverse-proxy support."""
        cf_ip = self.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()
        xfwd = self.headers.get("X-Forwarded-For")
        if xfwd:
            return xfwd.split(",")[0].strip()
        return self.client_address[0]

    def check_origin(self) -> bool:
        """Validates Origin/Referer headers against Host to prevent CSRF."""
        origin = self.headers.get("Origin") or self.headers.get("Referer")
        host = self.headers.get("Host")
        if origin and host:
            parsed = urlparse(origin)
            if parsed.netloc and parsed.netloc.lower() != host.lower():
                return False
        return True

    def get_session_token(self) -> Optional[str]:
        auth_header = self.headers.get("X-Session-Token")
        if auth_header:
            return auth_header

        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            item = item.strip()
            if item.startswith("xfwd_session="):
                return item.split("=")[1].strip()
            if item.startswith("fwdman_session="):
                return item.split("=")[1].strip()
        return None

    def is_authenticated(self) -> bool:
        token = self.get_session_token()
        if not token:
            return False
        now = time.time()
        with SESSION_LOCK:
            session = ACTIVE_SESSIONS.get(token)
            if not session:
                return False

            if now > session.get("expires_at", 0) or (now - session.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS:
                ACTIVE_SESSIONS.pop(token, None)
                return False

            session["last_active"] = now

            if len(ACTIVE_SESSIONS) > MAX_ACTIVE_SESSIONS:
                stale = [k for k, v in ACTIVE_SESSIONS.items() if now > v.get("expires_at", 0) or (now - v.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS]
                for k in stale:
                    ACTIVE_SESSIONS.pop(k, None)
        return True

    def resolve_path(self) -> Tuple[bool, str, Optional[str]]:
        parsed = urlparse(self.path)
        raw_path = parsed.path
        cfg = load_config()
        secret = cfg.get("web", {}).get("secret_path", "")
        secret = str(secret or "").strip().strip("/")

        if raw_path == "/favicon.ico":
            return True, "/favicon.ico", None

        if not secret:
            clean = raw_path.rstrip("/") or "/"
            return True, clean, None

        secret_prefix = f"/{secret}"

        if raw_path == secret_prefix:
            return True, "/", f"{secret_prefix}/"

        if raw_path.startswith(f"{secret_prefix}/"):
            subpath = raw_path[len(secret_prefix):]
            clean = subpath.rstrip("/") or "/"
            return True, clean, None

        if raw_path.startswith("/api/") and self.is_authenticated():
            clean = raw_path.rstrip("/") or "/"
            return True, clean, None

        return False, raw_path, None

    def do_GET(self):
        allowed, subpath, redirect_url = self.resolve_path()
        if redirect_url:
            self.send_response(302)
            self.send_header("Location", redirect_url)
            self.apply_security_headers()
            self.end_headers()
            return

        if not allowed:
            self.send_error(404, "Not Found")
            return

        if subpath == "/favicon.ico":
            self.send_response(204)
            self.apply_security_headers()
            self.end_headers()
            return

        # ── Generalized Static Asset Dispatcher with Security & MIME Resolution ──
        static_rel = subpath.lstrip("/")
        candidate_file = os.path.normpath(os.path.join(WEB_DIR, static_rel))
        if os.path.isfile(candidate_file) and not subpath.startswith("/api/"):
            try:
                if os.path.commonpath([WEB_DIR, candidate_file]) == WEB_DIR:
                    mime = "text/plain; charset=utf-8"
                    ext = os.path.splitext(candidate_file)[1].lower()
                    if ext == ".css":
                        mime = "text/css; charset=utf-8"
                    elif ext == ".js":
                        mime = "application/javascript; charset=utf-8"
                    elif ext in (".html", ".htm"):
                        mime = "text/html; charset=utf-8"
                    elif ext == ".json":
                        mime = "application/json; charset=utf-8"
                    elif ext == ".svg":
                        mime = "image/svg+xml"
                    elif ext == ".png":
                        mime = "image/png"
                    elif ext in (".jpg", ".jpeg"):
                        mime = "image/jpeg"
                    elif ext == ".ico":
                        mime = "image/x-icon"
                    elif ext == ".woff2":
                        mime = "font/woff2"
                    self.send_file(candidate_file, mime)
                    return
            except Exception:
                pass

        # Check authentication for API
        if subpath.startswith("/api/"):
            if subpath == "/api/me":
                auth_ok = self.is_authenticated()
                cfg = load_config()
                username = cfg.get("web", {}).get("auth", {}).get("username", "admin")
                self.send_json({"authenticated": auth_ok, "username": username if auth_ok else None})
                return

            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if subpath == "/api/status":
                cfg = load_config()
                state = load_state()
                runtime = state.get("runtime", {})
                if isinstance(runtime, dict) and "rules_state" in runtime and isinstance(runtime["rules_state"], dict):
                    cleaned_rules = {}
                    for p_key, r_st in runtime["rules_state"].items():
                        if not isinstance(r_st, dict):
                            cleaned_rules[p_key] = r_st
                            continue
                        r_copy = dict(r_st)
                        if "dest_stats" in r_copy and isinstance(r_copy["dest_stats"], dict):
                            cleaned_dest_stats = {}
                            for d_key, d_val in r_copy["dest_stats"].items():
                                if isinstance(d_val, dict):
                                    cleaned_dest_stats[d_key] = {k: v for k, v in d_val.items() if k != "samples"}
                                else:
                                    cleaned_dest_stats[d_key] = d_val
                            r_copy["dest_stats"] = cleaned_dest_stats
                        cleaned_rules[p_key] = r_copy
                    runtime = dict(runtime)
                traffic_data = None
                if get_traffic_summary:
                    try:
                        traffic_data = get_traffic_summary(period="24h")
                    except Exception:
                        pass
                self.send_json({
                    "version": get_installed_version(),
                    "config": cfg,
                    "runtime": runtime,
                    "system": get_system_stats(),
                    "services": get_services_status(),
                    "network": get_network_interfaces_info(),
                    "traffic": traffic_data,
                    "server_time": time.time()
                })
                return
            elif subpath == "/api/services/status":
                self.send_json(get_services_status())
                return
            elif subpath == "/api/network/interfaces":
                self.send_json(get_network_interfaces_info())
                return
            elif subpath == "/api/import/discover":
                cfg = load_config()
                existing_rules = cfg.get("rules", [])
                try:
                    from core.nftables_parser import discover_all_relay_rules
                except ImportError:
                    from nftables_parser import discover_all_relay_rules
                data = discover_all_relay_rules(existing_rules)
                self.send_json(data)
                return
            elif subpath == "/api/config/export":
                export_data = export_config_data()
                now_str = time.strftime("%Y%m%d-%H%M%S")
                body = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="xforwarder-backup-{now_str}.json"')
                self.send_header("Content-Length", str(len(body)))
                self.apply_security_headers()
                self.end_headers()
                self.wfile.write(body)
                return
            elif subpath == "/api/metrics/loss-history":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                target = params.get("target", ["all"])[0]
                range_str = params.get("range", ["24h"])[0]
                hours = 24
                if range_str == "7d":
                    hours = 168
                elif range_str == "30d":
                    hours = 720
                else:
                    try:
                        hours = int(range_str.replace("h", ""))
                    except Exception:
                        hours = 24

                try:
                    from core.metrics import get_metrics_history
                except ImportError:
                    try:
                        from metrics import get_metrics_history
                    except ImportError:
                        get_metrics_history = None

                if get_metrics_history:
                    history = get_metrics_history(target=target, time_range_hours=hours)
                    self.send_json({"ok": True, **history})
                else:
                    self.send_json({"ok": False, "error": "Metrics module unavailable"}, 500)
                return
            elif subpath == "/api/system/version":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                force_check = params.get("check", ["0"])[0] in ("1", "true")
                data = get_full_version_status(force=force_check)
                self.send_json(data)
                return
            elif subpath == "/api/system/update/status":
                data = get_update_status()
                self.send_json(data)
                return
            elif subpath == "/api/traffic/summary":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                period = params.get("period", ["24h"])[0]
                etype = params.get("entity_type", [None])[0]
                eid = params.get("entity_id", [None])[0]
                if get_traffic_summary:
                    data = get_traffic_summary(period=period, entity_type=etype, entity_id=eid)
                    self.send_json({"ok": True, "data": data})
                else:
                    self.send_json({"ok": False, "error": "Traffic module unavailable"}, 500)
                return
            elif subpath == "/api/traffic/timeseries":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                period = params.get("period", ["24h"])[0]
                etype = params.get("entity_type", [None])[0]
                eid = params.get("entity_id", [None])[0]
                if get_traffic_timeseries:
                    data = get_traffic_timeseries(period=period, entity_type=etype, entity_id=eid)
                    self.send_json({"ok": True, "data": data})
                else:
                    self.send_json({"ok": False, "error": "Traffic module unavailable"}, 500)
                return
            else:
                self.send_error(404, "API endpoint not found")
                return

        # Serve SPA index.html for all UI subpaths under secret_path
        self.send_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")

    def do_POST(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if not self.check_origin():
            try:
                drain_len = int(self.headers.get("Content-Length", 0))
                if 0 < drain_len <= 65536:
                    self.rfile.read(drain_len)
            except Exception:
                pass
            self.send_json({"ok": False, "error": "Cross-origin request rejected"}, 403)
            return

        body = {}
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > 0:
            if content_len > 65536:
                self.send_json({"error": "Payload too large"}, 413)
                return
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except Exception:
                body = {}

        client_ip = self.get_client_ip()

        # 1. Login endpoint
        if subpath == "/api/login":
            is_locked, remaining, _ = check_rate_limit(client_ip)
            if is_locked:
                self.send_json({
                    "ok": False,
                    "error": f"Too many failed login attempts. Temporary lockout active. Try again in {remaining} seconds.",
                    "lockout": True,
                    "remaining_seconds": remaining
                }, 429)
                return

            cfg = load_config()
            auth_cfg = cfg.get("web", {}).get("auth", {})
            expected_user = auth_cfg.get("username", "admin")
            expected_hash = auth_cfg.get("password_hash", "")

            user = body.get("username", "").strip()
            pwd = body.get("password", "")

            import hmac
            user_matches = hmac.compare_digest(user, expected_user)
            pwd_valid, needs_rehash = verify_password(pwd, expected_hash)

            if user_matches and pwd_valid:
                reset_rate_limit(client_ip)
                if needs_rehash:
                    cfg["web"]["auth"]["password_hash"] = hash_password(pwd)
                    save_config(cfg)

                token = secrets.token_hex(32)
                now = time.time()
                with SESSION_LOCK:
                    ACTIVE_SESSIONS[token] = {
                        "username": user,
                        "created_at": now,
                        "last_active": now,
                        "expires_at": now + (SESSION_TTL_HOURS * 3600),
                        "ip": client_ip
                    }
                save_sessions_to_disk()
                self.send_json({"ok": True, "token": token, "username": user}, 200, cookie_token=token)
            else:
                is_locked_now, lock_remaining, count = record_failed_login(client_ip)
                time.sleep(0.4 + (secrets.randbelow(300) / 1000.0))
                attempts_left = max(0, MAX_FAILED_ATTEMPTS - count)
                if is_locked_now:
                    self.send_json({
                        "ok": False,
                        "error": f"Maximum failed attempts exceeded. Access locked for {LOCKOUT_DURATION // 60} minutes.",
                        "lockout": True,
                        "remaining_seconds": lock_remaining
                    }, 429)
                else:
                    self.send_json({
                        "ok": False,
                        "error": f"Invalid username or password. {attempts_left} attempt(s) remaining before temporary lockout.",
                        "attempts_left": attempts_left
                    }, 401)
            return

        # 2. Logout endpoint
        if subpath == "/api/logout":
            token = self.get_session_token()
            if token:
                with SESSION_LOCK:
                    ACTIVE_SESSIONS.pop(token, None)
                save_sessions_to_disk()
            self.send_json({"ok": True}, 200, cookie_token="")
            return

        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        # 3. Security Credentials Management
        if subpath in ("/api/security", "/api/security/credentials"):
            current_pwd = body.get("current_password", "")
            new_user = body.get("new_username", "").strip()
            new_pwd = body.get("new_password", "")

            cfg = load_config()
            auth_cfg = cfg.get("web", {}).get("auth", {})
            expected_hash = auth_cfg.get("password_hash", "")

            pwd_valid, _ = verify_password(current_pwd, expected_hash)
            if not pwd_valid:
                self.send_json({"ok": False, "error": "Current password verification failed"}, 403)
                return

            if new_user:
                if len(new_user) < 3:
                    self.send_json({"ok": False, "error": "Username must be at least 3 characters"}, 400)
                    return
                auth_cfg["username"] = new_user
                token = self.get_session_token()
                if token:
                    with SESSION_LOCK:
                        if token in ACTIVE_SESSIONS:
                            ACTIVE_SESSIONS[token]["username"] = new_user
                    save_sessions_to_disk()

            if new_pwd:
                if len(new_pwd) < 8:
                    self.send_json({"ok": False, "error": "New password must be at least 8 characters"}, 400)
                    return
                auth_cfg["password_hash"] = hash_password(new_pwd)

            cfg["web"]["auth"] = auth_cfg
            if save_config(cfg):
                self.send_json({"ok": True, "username": auth_cfg["username"]})
            else:
                self.send_json({"ok": False, "error": "Failed to save configuration"}, 500)
            return

        elif subpath == "/api/rule":
            valid, err_msg = validate_rule(body)
            if not valid:
                self.send_json({"ok": False, "error": err_msg}, 400)
                return

            cfg = load_config()
            rules = cfg.get("rules", [])
            rule_id = str(body.get("id") or f"rule-{body['port']}")
            body["id"] = rule_id

            for r in rules:
                if r.get("id") != rule_id and r.get("port") == body["port"]:
                    self.send_json({"ok": False, "error": f"Port {body['port']} is already used by rule '{r.get('id')}'"}, 409)
                    return

            if is_port_in_use_by_external_service(body["port"], rule_id, rules):
                self.send_json({
                    "ok": False,
                    "error": f"Port {body['port']} is already bound by an external system service (e.g. web server, SSH, or proxy)!"
                }, 409)
                return

            now_ts = time.time()
            updated = False
            for i, r in enumerate(rules):
                if r.get("id") == rule_id:
                    orig_created_at = float(r.get("created_at", 0) or 0)
                    body_created_at = float(body.get("created_at", 0) or 0)
                    if orig_created_at > 0 and body_created_at <= 0:
                        body["created_at"] = orig_created_at
                    elif body_created_at <= 0:
                        body["created_at"] = now_ts
                    else:
                        body["created_at"] = body_created_at
                    rules[i] = body
                    updated = True
                    break
            if not updated:
                if float(body.get("created_at", 0) or 0) <= 0:
                    body["created_at"] = now_ts
                rules.append(body)

            cfg["rules"] = rules
            if save_config(cfg):
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "rule": body,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/override":
            rule_id = str(body.get("rule_id", ""))
            try:
                override_prio = int(body.get("force_override", 0))
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid force_override value"}, 400)
                return

            if override_prio < 0:
                self.send_json({"ok": False, "error": "force_override cannot be negative"}, 400)
                return

            cfg = load_config()
            found = False
            for r in cfg.get("rules", []):
                if r.get("id") == rule_id:
                    r["force_override"] = override_prio
                    if override_prio > 0:
                        r["active_priority"] = override_prio
                    else:
                        state = load_state()
                        r_state = state.get("runtime", {}).get("rules_state", {}).get(rule_id, {})
                        r_state["last_switch_time"] = 0
                        r_state["cooldown_remaining"] = 0
                        dest_stats = r_state.get("dest_stats", {})
                        dests = sorted(r.get("destinations", []), key=lambda d: d.get("priority", 99))
                        current_prio = r.get("active_priority", 1)
                        if callable(pick_best_now):
                            r["active_priority"] = pick_best_now(dest_stats, dests, current_prio)
                        else:
                            chosen = None
                            for d in dests:
                                p = d.get("priority", 1)
                                st = dest_stats.get(f"prio_{p}", {})
                                if st.get("status") == "healthy" and st.get("packet_loss", 0) <= 25:
                                    chosen = p
                                    break
                            r["active_priority"] = chosen if chosen is not None else (dests[0].get("priority", 1) if dests else 1)
                    found = True
                    break
            if not found:
                self.send_json({"ok": False, "error": "Rule not found"}, 404)
                return

            if save_config(cfg):
                update_state_rules({
                    rule_id: {
                        "active_priority": r["active_priority"],
                        "last_force_override": override_prio,
                        "last_switch_time": 0,
                        "cooldown_remaining": 0
                    }
                })
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)
            return

        elif subpath == "/api/override/batch":
            try:
                override_prio = int(body.get("force_override", 0))
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid force_override value"}, 400)
                return

            if override_prio < 0:
                self.send_json({"ok": False, "error": "force_override cannot be negative"}, 400)
                return

            cfg = load_config()
            rules = cfg.get("rules", [])
            state = load_state()
            rules_state = state.get("runtime", {}).get("rules_state", {})
            for r in rules:
                r["force_override"] = override_prio
                r_id = r.get("id")
                r_state = rules_state.get(r_id, {})
                r_state["last_switch_time"] = 0
                r_state["cooldown_remaining"] = 0
                if override_prio > 0:
                    r["active_priority"] = override_prio
                else:
                    dest_stats = r_state.get("dest_stats", {})
                    dests = sorted(r.get("destinations", []), key=lambda d: d.get("priority", 99))
                    current_prio = r.get("active_priority", 1)
                    if callable(pick_best_now):
                        r["active_priority"] = pick_best_now(dest_stats, dests, current_prio)
                    else:
                        chosen = None
                        for d in dests:
                            p = d.get("priority", 1)
                            st = dest_stats.get(f"prio_{p}", {})
                            if st.get("status") == "healthy" and st.get("packet_loss", 0) <= 25:
                                chosen = p
                                break
                        r["active_priority"] = chosen if chosen is not None else (dests[0].get("priority", 1) if dests else 1)

            if save_config(cfg):
                batch_updates = {
                    r.get("id"): {
                        "active_priority": r["active_priority"],
                        "last_force_override": override_prio,
                        "last_switch_time": 0,
                        "cooldown_remaining": 0
                    } for r in rules if r.get("id")
                }
                update_state_rules(batch_updates)
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "count": len(rules),
                    "force_override": override_prio,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/sync":
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": sync_ok,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            }, 200 if sync_ok else 500)

        elif subpath == "/api/import/haproxy":
            from core.haproxy_parser import import_haproxy_rules_into_config
            cfg_path = get_config_path()
            count, ports = import_haproxy_rules_into_config(cfg_path)
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })

        elif subpath == "/api/import/nftables":
            try:
                from core.nftables_parser import import_nftables_rules_into_config
            except ImportError:
                from nftables_parser import import_nftables_rules_into_config
            cfg_path = get_config_path()
            count, ports, logs = import_nftables_rules_into_config(cfg_path, deactivate_legacy=True)
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports,
                "logs": logs,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })

        elif subpath == "/api/import/all":
            try:
                from core.nftables_parser import import_all_relay_rules_into_config
            except ImportError:
                from nftables_parser import import_all_relay_rules_into_config
            cfg_path = get_config_path()
            count, ports, logs = import_all_relay_rules_into_config(cfg_path, deactivate_legacy=True)
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports,
                "logs": logs,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })

        elif subpath == "/api/config/import":
            if isinstance(body, dict) and "config" in body:
                imported_raw = body["config"]
            else:
                imported_raw = body
            mode = body.get("mode", "merge") if isinstance(body, dict) else "merge"
            ok, err, info = import_config_data(imported_raw, mode=mode)
            if ok:
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({"ok": True, "sync_ok": sync_ok, "sync_errors": sync_errors, **info})
            else:
                self.send_json({"ok": False, "error": err}, 400)

        elif subpath == "/api/test-target":
            target = str(body.get("target", "")).strip().strip("[]")
            try:
                port = int(body.get("port", 0))
            except (ValueError, TypeError):
                port = 0
            if not target or not is_valid_target(target) or port <= 0 or port > 65535:
                self.send_json({"ok": False, "healthy": False, "error": "Invalid target IP/host or port"}, 400)
                return

            dest_type = str(body.get("type", "")).lower().strip()
            if not dest_type:
                dest_type = "haproxy" if ":" in target else "nginx"
            if dest_type == "haproxy":
                clean_target = target.strip("[]")
                try:
                    import ipaddress
                    ip_obj = ipaddress.ip_address(clean_target)
                    if ip_obj.version != 6:
                        self.send_json({"ok": False, "healthy": False, "error": f"HAProxy destination target must be a valid IPv6 address (got IPv4 '{target}')"}, 400)
                        return
                except ValueError:
                    self.send_json({"ok": False, "healthy": False, "error": f"HAProxy destination target must be a valid IPv6 address (got '{target}')"}, 400)
                    return

            is_loss_test = (body.get("mode") == "loss_50" or body.get("test_loss") is True or str(body.get("packets", "")) == "50")
            if is_loss_test:
                try:
                    from core.metrics import measure_packet_loss_50
                except ImportError:
                    try:
                        from metrics import measure_packet_loss_50
                    except ImportError:
                        measure_packet_loss_50 = None

                if measure_packet_loss_50:
                    try:
                        res = measure_packet_loss_50(target, count=50, interval=0.2, save_to_db=True)
                        self.send_json({
                            "ok": True,
                            "healthy": res.get("healthy", False),
                            "latency_ms": res.get("latency_ms"),
                            "min_lat": res.get("min_lat"),
                            "max_lat": res.get("max_lat"),
                            "packet_loss": res.get("packet_loss", 0 if res.get("healthy") else 100),
                            "packets_sent": res.get("packets_sent", 50),
                            "packets_received": res.get("packets_received", 0),
                            "is_disrupted": res.get("is_disrupted", 0),
                            "reason": res.get("error", "")
                        })
                        return
                    except Exception as e:
                        self.send_json({"ok": False, "healthy": False, "error": str(e)}, 500)
                        return

            protocol = str(body.get("protocol", "both")).lower()
            try:
                packets = int(body.get("packets", 4))
            except (ValueError, TypeError):
                packets = 4
            packets = max(1, min(packets, 10))

            try:
                from core.prober import check_destination
                probe_res = check_destination(
                    {"target": target, "port": port, "type": dest_type},
                    rule_port=port,
                    protocol=protocol,
                    count=packets
                )
                self.send_json({
                    "ok": True,
                    "healthy": probe_res.get("healthy", False),
                    "latency_ms": probe_res.get("latency_ms"),
                    "packet_loss": probe_res.get("packet_loss", 0 if probe_res.get("healthy") else 100),
                    "packets_sent": probe_res.get("packets_sent", packets),
                    "packets_received": probe_res.get("packets_received", packets if probe_res.get("healthy") else 0),
                    "reason": probe_res.get("reason", "")
                })
            except Exception as e:
                self.send_json({"ok": False, "healthy": False, "error": str(e)}, 500)
            return

        elif subpath == "/api/test-loss":
            target = str(body.get("target", "")).strip().strip("[]")
            if not target or not is_valid_target(target):
                self.send_json({"ok": False, "healthy": False, "error": "Invalid target IP/host"}, 400)
                return

            try:
                from core.metrics import measure_packet_loss_50
            except ImportError:
                try:
                    from metrics import measure_packet_loss_50
                except ImportError:
                    measure_packet_loss_50 = None

            if not measure_packet_loss_50:
                self.send_json({"ok": False, "healthy": False, "error": "Loss measurement module unavailable"}, 500)
                return

            try:
                res = measure_packet_loss_50(target, count=50, interval=0.2, save_to_db=True)
                self.send_json({"ok": True, **res})
            except Exception as e:
                self.send_json({"ok": False, "healthy": False, "error": str(e)}, 500)
            return

        elif subpath == "/api/metrics/trigger-round":
            try:
                from core.metrics import run_scheduled_ping_round
            except ImportError:
                try:
                    from metrics import run_scheduled_ping_round
                except ImportError:
                    run_scheduled_ping_round = None

            if not run_scheduled_ping_round:
                self.send_json({"ok": False, "error": "Metrics module unavailable"}, 500)
                return

            try:
                cfg = load_config()
                results = run_scheduled_ping_round(cfg)
                self.send_json({"ok": True, "count": len(results), "results": results})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        elif subpath == "/api/system/update":
            ok, msg = start_system_update()
            if ok:
                self.send_json({"ok": True, "status": "started", "message": msg})
            else:
                self.send_json({"ok": False, "status": "error", "error": msg}, 409 if "already" in msg else 500)
            return

        elif subpath == "/api/services/restart":
            svc = body.get("service", "all")
            ok, msg, is_reconnecting = restart_services_action(svc, sync_rules_func=sync_rules_and_notify, notify_func=notify_engine_wakeup)
            if ok:
                self.send_json({"ok": True, "service": svc, "message": msg, "reconnecting": is_reconnecting})
            else:
                self.send_json({"ok": False, "service": svc, "error": msg}, 400 if "Invalid" in msg else 500)
            return

        elif subpath == "/api/traffic/reset":
            entity_type = str(body.get("entity_type", "all")).strip().lower()
            entity_id = str(body.get("entity_id", "all")).strip()
            wipe_history = bool(body.get("wipe_history", False))

            if entity_type not in ("all", "port", "tunnel", "method", "tunnel_type"):
                self.send_json({"ok": False, "error": f"Invalid entity_type '{entity_type}'. Must be 'all', 'port', 'tunnel', 'method', or 'tunnel_type'."}, 400)
                return

            if entity_type == "port" and entity_id.lower() != "all":
                try:
                    p_num = int(entity_id)
                    if not (1 <= p_num <= 65535):
                        raise ValueError()
                except ValueError:
                    self.send_json({"ok": False, "error": f"Invalid port number '{entity_id}'. Must be 1-65535 or 'all'."}, 400)
                    return

            if entity_type in ("tunnel", "method", "tunnel_type") and entity_id.lower() != "all":
                import re
                if not re.match(r"^[a-zA-Z0-9_.-]{1,32}$", entity_id):
                    self.send_json({"ok": False, "error": f"Invalid {entity_type} identifier '{entity_id}'."}, 400)
                    return

            if reset_traffic_counter:
                res = reset_traffic_counter(entity_type=entity_type, entity_id=entity_id, wipe_history=wipe_history)
                if res.get("success"):
                    self.send_json({"ok": True, **res})
                else:
                    self.send_json({"ok": False, **res}, 500)
            else:
                self.send_json({"ok": False, "error": "Traffic module unavailable"}, 500)
            return

        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if not self.check_origin():
            try:
                drain_len = int(self.headers.get("Content-Length", 0))
                if 0 < drain_len <= 65536:
                    self.rfile.read(drain_len)
            except Exception:
                pass
            self.send_json({"ok": False, "error": "Cross-origin request rejected"}, 403)
            return

        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        if subpath.startswith("/api/rule/"):
            rule_id = subpath.split("/api/rule/")[1].strip()
            cfg = load_config()
            cfg["rules"] = [r for r in cfg.get("rules", []) if r.get("id") != rule_id]
            if save_config(cfg):
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "deleted": rule_id,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)
        else:
            self.send_error(404, "Not Found")


class XForwarderWebServer:
    def __init__(self, bind_host: Optional[str] = None, port: Optional[int] = None):
        cfg = load_config()
        web_cfg = cfg.get("web", {})
        self.bind_host = bind_host or web_cfg.get("bind_host", "0.0.0.0")
        self.port = port or int(web_cfg.get("port", 8090))
        self.ssl_cert = web_cfg.get("ssl_cert", "")
        self.ssl_key = web_cfg.get("ssl_key", "")
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.is_ssl = False

    def start(self):
        XForwarderWebHandler.server_instance = self
        server_address = (self.bind_host, self.port)
        self.httpd = ThreadingHTTPServer(server_address, XForwarderWebHandler)

        # SSL Configuration if cert and key provided
        if self.ssl_cert and self.ssl_key and os.path.exists(self.ssl_cert) and os.path.exists(self.ssl_key):
            try:
                ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ctx.load_cert_chain(certfile=self.ssl_cert, keyfile=self.ssl_key)
                self.httpd.socket = ctx.wrap_socket(self.httpd.socket, server_side=True)
                self.is_ssl = True
                print(f"[OK] HTTPS/TLS enabled on https://{self.bind_host}:{self.port}/")
            except Exception as e:
                print(f"[WARN] Failed to configure SSL: {e}. Falling back to plain HTTP.", file=sys.stderr)
                self.is_ssl = False

        scheme = "https" if self.is_ssl else "http"
        print(f"[INFO] XForwarder Web Server listening at {scheme}://{self.bind_host}:{self.port}/")
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.httpd.server_close()
            print("[INFO] Web server stopped.")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


ForwardManagerWebHandler = XForwarderWebHandler
ForwardManagerWebServer = XForwarderWebServer

if __name__ == "__main__":
    server = XForwarderWebServer()
    server.start()

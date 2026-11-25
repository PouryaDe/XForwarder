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
import socket
import re
import tempfile
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional, Dict, Tuple, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config_manager import (
    load_config, save_config, load_state, update_state_rules, remove_state_rules,
    get_config_path, get_state_file_path, validate_rule,
    get_rule_port_bounds, ports_overlap, rules_ports_overlap,
    find_dsr_backend_conflict,
    export_config_data, import_config_data, is_valid_target,
    is_port_in_use_by_external_service, migrate_and_normalize_config,
    validate_update_transport_config, sanitize_config_for_api,
    CONFIG_PATH, LEGACY_CONFIG_PATH, LOCAL_CONFIG_PATH,
    STATE_FILE_PATH, LEGACY_STATE_FILE_PATH
)
from core.auth import (
    hash_password, verify_password, check_rate_limit, record_failed_login,
    reset_rate_limit,
    load_sessions_from_disk as auth_load_sessions_from_disk,
    save_sessions_to_disk as auth_save_sessions_to_disk,
    get_sessions_file_path as auth_get_sessions_file_path,
    generate_api_key, sanitize_api_key_record, scope_allows, authenticate_api_key,
    VALID_API_SCOPES,
    ACTIVE_SESSIONS, SESSION_LOCK,
    SESSION_TTL_HOURS, SESSION_IDLE_TIMEOUT_SECONDS, MAX_ACTIVE_SESSIONS,
    LOCKOUT_DURATION, MAX_FAILED_ATTEMPTS
)
from core.openapi_spec import build_openapi_spec
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
    discover_update_transports, invalidate_remote_version_cache,
    get_update_state_file_path as sm_get_update_state_file_path,
    get_update_log_path as sm_get_update_log_path,
    save_update_state as sm_save_update_state,
    load_update_state as sm_load_update_state,
    APP_VERSION, _UPDATE_STATE, _UPDATE_LOCK
)

try:
    from core.firewall import flush_conntrack
except ImportError:
    try:
        from firewall import flush_conntrack
    except ImportError:
        flush_conntrack = lambda port, proto=None: None

try:
    from core.kernel_tuner import (
        get_kernel_tuning_status, apply_kernel_tuning,
        get_spoof_test_status, start_spoof_test_listener,
        stop_spoof_test_listener, run_spoof_egress_test,
    )
except ImportError:
    from kernel_tuner import (
        get_kernel_tuning_status, apply_kernel_tuning,
        get_spoof_test_status, start_spoof_test_listener,
        stop_spoof_test_listener, run_spoof_egress_test,
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

try:
    from core.metrics import get_latest_metrics_per_target, sanitize_target_host
except ImportError:
    try:
        from metrics import get_latest_metrics_per_target, sanitize_target_host
    except ImportError:
        get_latest_metrics_per_target = None
        sanitize_target_host = lambda t: str(t).strip().strip("[]")

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


def _safe_flush_port_conntrack(port: Any) -> None:
    """Safely purges stale conntrack states for a rule port after firewall/proxy synchronization."""
    try:
        p_num = int(port or 0)
        if 0 < p_num <= 65535:
            flush_conntrack(p_num)
    except Exception:
        pass


def _get_rule_effective_id(rule: Dict[str, Any]) -> str:
    """Returns canonical rule ID, deriving a deterministic fallback for range/exclusion/port rules."""
    raw_id = str(rule.get("id") or "").strip()
    if raw_id:
        return raw_id
    excl = rule.get("excluded_ports")
    if isinstance(excl, list) and excl:
        return f"rule-excl-{'-'.join(str(p) for p in excl[:5])}"
    label = str(rule.get("port_range") or rule.get("port") or "").strip()
    return f"rule-{label}" if label else ""


def _get_rule_all_ids(rule: Dict[str, Any]) -> List[str]:
    """Collects explicit and derived rule IDs for matching and runtime state cleanup."""
    ids: List[str] = []
    raw_id = str(rule.get("id") or "").strip()
    if raw_id:
        ids.append(raw_id)
    excl = rule.get("excluded_ports")
    prange = str(rule.get("port_range") or "").strip()
    port = rule.get("port")
    if isinstance(excl, list) and excl:
        ids.append(f"rule-excl-{'-'.join(str(p) for p in excl[:5])}")
        ids.append(f"rule-!={','.join(str(p) for p in excl[:4])}")
    if prange:
        ids.append(f"rule-{prange}")
    if port is not None and str(port).strip():
        ids.append(f"rule-{port}")
    return [i for i in dict.fromkeys(ids) if i]


def _rule_matches_target_id(rule: Dict[str, Any], target_id: str) -> bool:
    """Matches a rule by explicit ID or, when explicit ID is missing/empty, by fallback IDs."""
    target = unquote(str(target_id or "")).strip()
    if not target:
        return False
    raw_id = str(rule.get("id") or "").strip()
    if raw_id:
        return raw_id == target
    candidates = set(_get_rule_all_ids(rule))
    prange = str(rule.get("port_range") or "").strip()
    port = rule.get("port")
    if prange:
        candidates.add(prange)
    if port is not None and str(port).strip():
        candidates.add(str(port).strip())
    return target in candidates


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


GLOBAL_SETTINGS_KEYS = (
    "wan_interface",
    "check_interval_seconds",
    "probe_count",
    "probe_interval_ms",
    "quality_window_seconds",
    "failure_threshold",
    "recovery_threshold",
    "fast_failover_enabled",
    "max_acceptable_loss",
    "critical_loss_percent",
    "cooldown_seconds",
    "min_hold_seconds",
    "switch_confirm_seconds",
    "hysteresis_percent",
    "loss_penalty_weight",
    "jitter_penalty_weight",
    "priority_bias_ms",
    "fast_probe_burst",
    "target_probe_interval_seconds",
    "fast_liveness_interval_seconds",
    "max_primary_latency_ms",
)


def _normalize_api_subpath(subpath: str) -> str:
    """Normalizes versioned `/api/v1/*` paths to canonical `/api/*` paths."""
    if subpath == "/api/v1":
        return "/api"
    if subpath.startswith("/api/v1/"):
        return "/api/" + subpath[len("/api/v1/"):]
    return subpath


def _extract_api_key_from_headers(headers: Any) -> Optional[str]:
    """Extracts an API key from `Authorization: Bearer <key>` or `X-API-Key` headers."""
    if not headers:
        return None
    api_key_hdr = headers.get("X-API-Key")
    if isinstance(api_key_hdr, str) and api_key_hdr.strip():
        return api_key_hdr.strip()
    auth_hdr = headers.get("Authorization", "")
    if isinstance(auth_hdr, str) and auth_hdr.lower().startswith("bearer "):
        tok = auth_hdr[7:].strip()
        if tok:
            return tok
    return None


def _require_scope(handler: Any, required_scope: str = "read") -> bool:
    """Enforces authentication and scoped API key authorization (401/403), compatible with mocked handlers."""
    ctx = None
    if hasattr(handler, "get_auth_context"):
        cand = handler.get_auth_context()
        if isinstance(cand, dict):
            ctx = cand
    if ctx is None:
        if handler.is_authenticated():
            ctx = {
                "authenticated": True,
                "auth_type": "session",
                "username": "admin",
                "scope": "admin",
                "key_id": None,
                "key_name": None,
            }
        else:
            handler.send_json({"ok": False, "error": "Unauthorized"}, 401)
            return False
    if not scope_allows(ctx.get("scope", ""), required_scope):
        handler.send_json({
            "ok": False,
            "error": f"Insufficient API key scope (requires '{required_scope}', key has '{ctx.get('scope')}')",
            "required_scope": required_scope,
            "current_scope": ctx.get("scope"),
        }, 403)
        return False
    return True


def _parse_json_body(handler: Any) -> Tuple[bool, Any]:
    """Reads and parses up to 64KB JSON request payload."""
    headers = getattr(handler, "headers", None)
    content_len = int((headers.get("Content-Length", 0) if headers else 0) or 0)
    if content_len <= 0:
        return True, {}
    if content_len > 65536:
        handler.send_json({"ok": False, "error": "Payload too large"}, 413)
        return False, None
    raw_body = handler.rfile.read(content_len).decode("utf-8", errors="replace")
    try:
        return True, json.loads(raw_body)
    except Exception:
        return True, {}


def _reject_disallowed_origin(handler: Any) -> bool:
    """Validates CSRF Origin/Referer for cookie-backed browser requests; returns True if rejected."""
    headers = getattr(handler, "headers", None)
    has_api_key = bool(_extract_api_key_from_headers(headers))
    has_cookie = bool(headers.get("Cookie")) if headers else False
    if has_api_key and not has_cookie:
        return False
    if not handler.check_origin():
        try:
            drain_len = int((headers.get("Content-Length", 0) if headers else 0) or 0)
            if 0 < drain_len <= 65536:
                handler.rfile.read(drain_len)
        except Exception:
            pass
        handler.send_json({"ok": False, "error": "Cross-origin request rejected"}, 403)
        return True
    return False


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
                return item.split("=", 1)[1].strip()
            if item.startswith("fwdman_session="):
                return item.split("=", 1)[1].strip()
        return None

    def get_api_key_from_headers(self) -> Optional[str]:
        """Extracts an API key from `Authorization: Bearer <key>` or `X-API-Key` headers."""
        return _extract_api_key_from_headers(getattr(self, "headers", None))

    def is_stateless_api_key_request(self) -> bool:
        """Returns True when request authenticates solely via explicit API key header without cookies."""
        return bool(self.get_api_key_from_headers()) and not bool(self.headers.get("Cookie"))

    def get_auth_context(self) -> Optional[Dict[str, Any]]:
        """Resolves session or API key authentication context, or None if unauthenticated."""
        token = self.get_session_token()
        if token:
            now = time.time()
            with SESSION_LOCK:
                session = ACTIVE_SESSIONS.get(token)
                if session:
                    if now > session.get("expires_at", 0) or (now - session.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS:
                        ACTIVE_SESSIONS.pop(token, None)
                    else:
                        session["last_active"] = now
                        if len(ACTIVE_SESSIONS) > MAX_ACTIVE_SESSIONS:
                            stale = [
                                k for k, v in ACTIVE_SESSIONS.items()
                                if now > v.get("expires_at", 0) or (now - v.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS
                            ]
                            for k in stale:
                                ACTIVE_SESSIONS.pop(k, None)
                        return {
                            "authenticated": True,
                            "auth_type": "session",
                            "username": session.get("username", "admin"),
                            "scope": "admin",
                            "key_id": None,
                            "key_name": None,
                        }

        raw_key = self.get_api_key_from_headers()
        if raw_key:
            cfg = load_config()
            api_keys = cfg.get("web", {}).get("api_keys", [])
            key_meta = authenticate_api_key(raw_key, api_keys)
            if key_meta:
                return {
                    "authenticated": True,
                    "auth_type": "api_key",
                    "username": cfg.get("web", {}).get("auth", {}).get("username", "admin"),
                    "scope": key_meta.get("scope", "admin"),
                    "key_id": key_meta.get("id"),
                    "key_name": key_meta.get("name"),
                }
        return None

    def is_authenticated(self) -> bool:
        return self.get_auth_context() is not None

    def require_scope(self, required_scope: str = "read") -> bool:
        """Enforces authentication and scoped API key authorization (401/403)."""
        return _require_scope(self, required_scope)

    def _parse_json_body(self) -> Tuple[bool, Any]:
        """Reads and parses up to 64KB JSON request payload."""
        return _parse_json_body(self)

    def _reject_disallowed_origin(self) -> bool:
        """Validates CSRF Origin/Referer for cookie-backed browser requests; returns True if rejected."""
        return _reject_disallowed_origin(self)

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
        if not os.path.isfile(candidate_file) and "/" in static_rel and not subpath.startswith("/api/"):
            first_seg, rest_rel = static_rel.split("/", 1)
            if first_seg.lower() in ("rules", "overview", "traffic", "services", "updates", "security", "logs") and rest_rel:
                candidate_file = os.path.normpath(os.path.join(WEB_DIR, rest_rel))
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
            subpath = _normalize_api_subpath(subpath)

            if subpath == "/api/me":
                raw_ctx = self.get_auth_context() if hasattr(self, "get_auth_context") else None
                ctx = raw_ctx if isinstance(raw_ctx, dict) else None
                auth_ok = ctx is not None or bool(self.is_authenticated())
                cfg = load_config()
                username = (ctx or {}).get("username") or cfg.get("web", {}).get("auth", {}).get("username", "admin")
                self.send_json({
                    "authenticated": auth_ok,
                    "username": username if auth_ok else None,
                    "auth_type": (ctx or {}).get("auth_type") if auth_ok else None,
                    "scope": (ctx or {}).get("scope") if auth_ok else None,
                    "key_id": (ctx or {}).get("key_id") if auth_ok else None,
                    "key_name": (ctx or {}).get("key_name") if auth_ok else None,
                })
                return

            if subpath in ("/api/api-keys", "/api/security/api-keys"):
                if not _require_scope(self, "admin"):
                    return
                cfg = load_config()
                keys = [sanitize_api_key_record(k) for k in cfg.get("web", {}).get("api_keys", []) if isinstance(k, dict)]
                self.send_json({"ok": True, "count": len(keys), "api_keys": keys})
                return

            if subpath.startswith("/api/api-keys/") or subpath.startswith("/api/security/api-keys/"):
                if not _require_scope(self, "admin"):
                    return
                prefix = "/api/api-keys/" if subpath.startswith("/api/api-keys/") else "/api/security/api-keys/"
                key_id = unquote(subpath[len(prefix):]).strip().strip("/")
                if not key_id or "/" in key_id:
                    self.send_json({"ok": False, "error": "API key ID required"}, 400)
                    return
                cfg = load_config()
                match = next((k for k in cfg.get("web", {}).get("api_keys", []) if isinstance(k, dict) and k.get("id") == key_id), None)
                if not match:
                    self.send_json({"ok": False, "error": "API key not found"}, 404)
                    return
                self.send_json({"ok": True, "key": sanitize_api_key_record(match)})
                return

            if not _require_scope(self, "read"):
                return

            if subpath == "/api/health":
                self.send_json({
                    "ok": True,
                    "status": "healthy",
                    "version": get_installed_version(),
                    "server_time": time.time(),
                })
                return
            elif subpath == "/api/openapi.json":
                host_hdr = self.headers.get("Host", "").strip()
                scheme = "https" if (
                    self.headers.get("X-Forwarded-Proto") == "https"
                    or (hasattr(self, "server_instance") and getattr(self.server_instance, "is_ssl", False))
                ) else "http"
                cfg = load_config()
                secret = str(cfg.get("web", {}).get("secret_path", "") or "").strip().strip("/")
                base_url = f"{scheme}://{host_hdr}/{secret}" if (host_hdr and secret) else (f"{scheme}://{host_hdr}" if host_hdr else "/")
                spec = build_openapi_spec(version=get_installed_version(), server_url=base_url)
                self.send_json(spec)
                return
            elif subpath == "/api/rules":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                cat_filter = params.get("category", [None])[0]
                proto_filter = params.get("protocol", [None])[0]
                type_filter = params.get("type", [None])[0]
                port_filter = params.get("port", [None])[0]
                include_rt = params.get("include_runtime", ["true"])[0].lower() not in ("0", "false", "no")

                cfg = load_config()
                rules = cfg.get("rules", []) if isinstance(cfg, dict) else []
                rules_state = load_state().get("runtime", {}).get("rules_state", {}) if include_rt else {}

                p_filter_num = None
                if port_filter is not None and str(port_filter).strip():
                    try:
                        p_filter_num = int(port_filter)
                    except (ValueError, TypeError):
                        self.send_json({"ok": False, "error": "Invalid port query filter"}, 400)
                        return

                items = []
                for r in rules:
                    if not isinstance(r, dict):
                        continue
                    if cat_filter is not None:
                        r_cat = str(r.get("category") or "")
                        if cat_filter == "__uncategorized__":
                            if r_cat != "":
                                continue
                        elif r_cat.lower() != cat_filter.strip().lower():
                            continue
                    if proto_filter is not None:
                        if str(r.get("protocol", "both")).lower() != proto_filter.strip().lower():
                            continue
                    if type_filter is not None:
                        t_low = type_filter.strip().lower()
                        if not any(str(d.get("type", "")).lower() == t_low for d in r.get("destinations", []) if isinstance(d, dict)):
                            continue
                    if p_filter_num is not None:
                        sp, ep, _ = get_rule_port_bounds(r)
                        excl = set(r.get("excluded_ports") or [])
                        if sp is None or ep is None or not (sp <= p_filter_num <= ep) or p_filter_num in excl:
                            continue
                    r_out = dict(r)
                    if include_rt:
                        rid = _get_rule_effective_id(r)
                        r_st = rules_state.get(rid) or rules_state.get(str(r.get("port", ""))) or {}
                        r_out["runtime"] = r_st
                    items.append(r_out)
                self.send_json({"ok": True, "count": len(items), "rules": items})
                return
            elif subpath.startswith("/api/rules/") or subpath.startswith("/api/rule/"):
                prefix = "/api/rules/" if subpath.startswith("/api/rules/") else "/api/rule/"
                rule_id = unquote(subpath[len(prefix):]).strip().strip("/")
                if not rule_id or "/" in rule_id:
                    self.send_json({"ok": False, "error": "API endpoint not found"}, 404)
                    return
                cfg = load_config()
                rules = cfg.get("rules", []) if isinstance(cfg, dict) else []
                idx = XForwarderWebHandler._find_rule_index(self, rules, rule_id)
                if idx is None:
                    self.send_json({"ok": False, "error": "Rule not found"}, 404)
                    return
                rule_obj = rules[idx]
                rid = _get_rule_effective_id(rule_obj)
                rules_state = load_state().get("runtime", {}).get("rules_state", {})
                r_st = rules_state.get(rid) or rules_state.get(str(rule_obj.get("port", ""))) or {}
                self.send_json({"ok": True, "rule": rule_obj, "runtime": r_st})
                return
            elif subpath == "/api/settings":
                cfg = load_config()
                settings_data = {k: cfg.get(k) for k in GLOBAL_SETTINGS_KEYS}
                self.send_json({"ok": True, "settings": settings_data})
                return
            elif subpath == "/api/logs/switches":
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                rule_filter = params.get("rule_id", [None])[0]
                try:
                    limit = max(1, min(int(params.get("limit", [50])[0]), 200))
                except (ValueError, TypeError):
                    limit = 50
                runtime = load_state().get("runtime", {})
                if rule_filter:
                    r_state = runtime.get("rules_state", {}).get(rule_filter, {})
                    events = list(r_state.get("switch_events", []))
                else:
                    events = list(runtime.get("recent_switches", []))
                events = list(reversed(events))[:limit]
                self.send_json({"ok": True, "count": len(events), "events": events})
                return
            elif subpath == "/api/status":
                cfg = load_config()
                state = load_state()
                runtime = state.get("runtime", {})
                latest_loss = {}
                if get_latest_metrics_per_target:
                    try:
                        latest_loss = get_latest_metrics_per_target()
                    except Exception:
                        pass

                # Build rule destination map to correlate target IPs with prio stats
                rules_list = cfg.get("rules", []) if isinstance(cfg, dict) else []
                rule_dest_targets: Dict[str, Dict[str, str]] = {}
                for r in rules_list:
                    rid = _get_rule_effective_id(r)
                    r_port = str(r.get("port", ""))
                    d_map = {}
                    for d in r.get("destinations", []):
                        p = d.get("priority", 1)
                        raw_tgt = str(d.get("target", "")).strip().strip("[]")
                        clean_tgt = (sanitize_target_host(raw_tgt) or raw_tgt).lower()
                        d_map[f"prio_{p}"] = clean_tgt
                    rule_dest_targets[rid] = d_map
                    if r_port:
                        rule_dest_targets[r_port] = d_map

                if isinstance(runtime, dict) and "rules_state" in runtime and isinstance(runtime["rules_state"], dict):
                    cleaned_rules = {}
                    for p_key, r_st in runtime["rules_state"].items():
                        if not isinstance(r_st, dict):
                            cleaned_rules[p_key] = r_st
                            continue
                        r_copy = dict(r_st)
                        target_map = rule_dest_targets.get(str(p_key), {})
                        if "dest_stats" in r_copy and isinstance(r_copy["dest_stats"], dict):
                            cleaned_dest_stats = {}
                            for d_key, d_val in r_copy["dest_stats"].items():
                                if isinstance(d_val, dict):
                                    ds = {k: v for k, v in d_val.items() if k != "samples"}
                                    tgt_ip = target_map.get(d_key)
                                    if tgt_ip and tgt_ip in latest_loss:
                                        ds["loss_50"] = latest_loss[tgt_ip]
                                    if isinstance(ds.get("lb_members"), list):
                                        enriched_members = []
                                        for m in ds["lb_members"]:
                                            if isinstance(m, dict):
                                                m_copy = dict(m)
                                                raw_m_t = str(m_copy.get("target", "")).strip().strip("[]")
                                                clean_m_t = (sanitize_target_host(raw_m_t) or raw_m_t).lower()
                                                if clean_m_t and clean_m_t in latest_loss:
                                                    m_copy["loss_50"] = latest_loss[clean_m_t]
                                                enriched_members.append(m_copy)
                                            else:
                                                enriched_members.append(m)
                                        ds["lb_members"] = enriched_members
                                    cleaned_dest_stats[d_key] = ds
                                else:
                                    cleaned_dest_stats[d_key] = d_val
                            r_copy["dest_stats"] = cleaned_dest_stats
                        cleaned_rules[p_key] = r_copy
                    runtime = dict(runtime)
                    runtime["rules_state"] = cleaned_rules
                traffic_data = None
                if get_traffic_summary:
                    try:
                        traffic_data = get_traffic_summary(period="24h")
                    except Exception:
                        pass
                self.send_json({
                    "version": get_installed_version(),
                    "config": sanitize_config_for_api(cfg),
                    "runtime": runtime,
                    "latest_loss": latest_loss,
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
                    from core.config_manager import get_protected_ports
                    from core.nftables_parser import discover_all_relay_rules
                except ImportError:
                    from config_manager import get_protected_ports
                    from nftables_parser import discover_all_relay_rules
                data = discover_all_relay_rules(existing_rules, protected_ports=get_protected_ports(cfg))
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
                data["transport_config"] = load_config().get("system_update", {})
                self.send_json(data)
                return
            elif subpath == "/api/system/update/transports":
                cfg = load_config()
                data = discover_update_transports(config=cfg)
                self.send_json(data)
                return
            elif subpath == "/api/system/update/status":
                data = get_update_status()
                self.send_json(data)
                return
            elif subpath == "/api/system/optimize":
                self.send_json({"ok": True, **get_kernel_tuning_status()})
                return
            elif subpath == "/api/system/spoof-test/status":
                self.send_json({"ok": True, **get_spoof_test_status()})
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

    def _find_rule_index(self, rules: List[Dict[str, Any]], target_id: str) -> Optional[int]:
        """Finds a rule index by exact ID first, then derived ID, then port/range fallback."""
        target = unquote(str(target_id or "")).strip()
        if not target:
            return None
        for idx, r in enumerate(rules):
            if isinstance(r, dict) and str(r.get("id") or "").strip() == target:
                return idx
        for idx, r in enumerate(rules):
            if isinstance(r, dict) and _rule_matches_target_id(r, target):
                return idx
        for idx, r in enumerate(rules):
            if not isinstance(r, dict):
                continue
            if str(r.get("port") or "").strip() == target or str(r.get("port_range") or "").strip() == target:
                return idx
        return None

    def _save_rule_payload(
        self,
        body: Any,
        create_only: bool = False,
        target_rule_id: Optional[str] = None,
        partial: bool = False,
    ) -> None:
        """Shared DRY handler for rule creation, upsert, full replacement (PUT), and partial update (PATCH)."""
        if not isinstance(body, dict):
            self.send_json({"ok": False, "error": "Invalid JSON body"}, 400)
            return

        cfg = load_config()
        rules = cfg.get("rules", [])
        existing_idx: Optional[int] = None
        existing_rule: Optional[Dict[str, Any]] = None

        if target_rule_id is not None:
            existing_idx = XForwarderWebHandler._find_rule_index(self, rules, target_rule_id)
            if existing_idx is None:
                self.send_json({"ok": False, "error": "Rule not found"}, 404)
                return
            existing_rule = dict(rules[existing_idx])

        if partial and existing_rule is not None:
            merged = json.loads(json.dumps(existing_rule))
            for k, v in body.items():
                if k == "id":
                    continue
                if k == "port" and "port_range" not in body:
                    merged.pop("port_range", None)
                if k == "excluded_ports" and (v is None or v == [] or v == ""):
                    merged.pop("excluded_ports", None)
                    continue
                merged[k] = v
            payload = merged
        else:
            payload = json.loads(json.dumps(body))
            if existing_rule is not None:
                payload["id"] = existing_rule.get("id") or _get_rule_effective_id(existing_rule)

        valid, err_msg = validate_rule(payload)
        if not valid:
            self.send_json({"ok": False, "error": err_msg}, 400)
            return

        rule_label = (
            f"!={','.join(str(p) for p in payload['excluded_ports'])}"
            if payload.get("excluded_ports") else (payload.get("port_range") or payload["port"])
        )
        rule_id = str(
            payload.get("id")
            or (f"rule-excl-{'-'.join(str(p) for p in payload['excluded_ports'][:5])}" if payload.get("excluded_ports") else f"rule-{rule_label}")
        )
        payload["id"] = rule_id

        if create_only and any(r.get("id") == rule_id for r in rules if isinstance(r, dict)):
            self.send_json({"ok": False, "error": f"Rule '{rule_id}' already exists"}, 409)
            return

        new_start, new_end, _ = get_rule_port_bounds(payload)
        web_port = int(cfg.get("web", {}).get("port", 8090) or 8090)
        if not payload.get("excluded_ports") and new_start is not None and new_end is not None and new_start <= web_port <= new_end:
            self.send_json({
                "ok": False,
                "error": f"Port / range {rule_label} overlaps the XForwarder Web Dashboard port ({web_port})"
            }, 409)
            return

        other_rules = []
        for idx, r in enumerate(rules):
            if existing_idx is not None and idx == existing_idx:
                continue
            if existing_idx is None and r.get("id") == rule_id:
                continue
            other_rules.append(r)
            if rules_ports_overlap(payload, r):
                ex_label = r.get("port_range") or r.get("port")
                self.send_json({"ok": False, "error": f"Port / range {rule_label} overlaps with existing rule '{r.get('id')}' ({ex_label})"}, 409)
                return

        dsr_conflict_err = find_dsr_backend_conflict(payload, other_rules)
        if dsr_conflict_err:
            self.send_json({"ok": False, "error": dsr_conflict_err}, 409)
            return

        if not payload.get("port_range") and is_port_in_use_by_external_service(payload["port"], rule_id, rules):
            self.send_json({
                "ok": False,
                "error": f"Port {payload['port']} is already bound by an external system service (e.g. web server, SSH, or proxy)!"
            }, 409)
            return

        now_ts = time.time()
        if existing_idx is not None and existing_rule is not None:
            orig_created_at = float(existing_rule.get("created_at", 0) or 0)
            body_created_at = float(payload.get("created_at", 0) or 0)
            if orig_created_at > 0 and body_created_at <= 0:
                payload["created_at"] = orig_created_at
            elif body_created_at <= 0:
                payload["created_at"] = now_ts
            rules[existing_idx] = payload
            status_code = 200
        else:
            updated = False
            for i, r in enumerate(rules):
                if r.get("id") == rule_id:
                    orig_created_at = float(r.get("created_at", 0) or 0)
                    body_created_at = float(payload.get("created_at", 0) or 0)
                    if orig_created_at > 0 and body_created_at <= 0:
                        payload["created_at"] = orig_created_at
                    elif body_created_at <= 0:
                        payload["created_at"] = now_ts
                    rules[i] = payload
                    updated = True
                    break
            if not updated:
                if float(payload.get("created_at", 0) or 0) <= 0:
                    payload["created_at"] = now_ts
                rules.append(payload)
            status_code = 201 if create_only else 200

        cfg["rules"] = rules
        if save_config(cfg):
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "rule": payload,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors,
            }, status_code)
        else:
            self.send_json({"ok": False, "error": "Save failed"}, 500)

    def _handle_override_request(self, rule_id: str, body: dict) -> None:
        """Applies or clears priority override on a rule and flushes targeted conntrack."""
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
        idx = XForwarderWebHandler._find_rule_index(self, rules, rule_id)
        matched_rule = rules[idx] if idx is not None else None
        matched_rule_id = (_get_rule_effective_id(matched_rule) or rule_id) if matched_rule else rule_id
        if matched_rule is not None:
            r = matched_rule
            r["force_override"] = override_prio
            if override_prio > 0:
                r["active_priority"] = override_prio
            else:
                state = load_state()
                r_state = state.get("runtime", {}).get("rules_state", {}).get(matched_rule_id, {})
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
        if not matched_rule:
            self.send_json({"ok": False, "error": "Rule not found"}, 404)
            return

        if save_config(cfg):
            update_state_rules({
                matched_rule_id: {
                    "active_priority": matched_rule["active_priority"],
                    "last_force_override": override_prio,
                    "last_switch_time": 0,
                    "cooldown_remaining": 0
                }
            })
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            _safe_flush_port_conntrack(matched_rule.get("port", 0))
            self.send_json({
                "ok": True,
                "rule_id": matched_rule_id,
                "force_override": override_prio,
                "active_priority": matched_rule["active_priority"],
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })
        else:
            self.send_json({"ok": False, "error": "Save failed"}, 500)

    def _handle_toggle_destination_request(self, rule_id: str, target_prio: int, explicit_enabled: Optional[bool]) -> None:
        """Toggles or explicitly sets enabled state on a destination priority."""
        cfg = load_config()
        rules = cfg.get("rules", [])
        idx = XForwarderWebHandler._find_rule_index(self, rules, rule_id)
        found_rule = rules[idx] if idx is not None else None
        found_dest = None
        matched_rule_id = (_get_rule_effective_id(found_rule) or rule_id) if found_rule else rule_id

        if found_rule is not None:
            for d in found_rule.get("destinations", []):
                if int(d.get("priority", 1)) == target_prio:
                    found_dest = d
                    break

        if not found_rule or not found_dest:
            self.send_json({"ok": False, "error": "Rule or destination priority not found"}, 404)
            return

        curr_en = bool(found_dest.get("enabled", True))
        new_enabled = (not curr_en) if explicit_enabled is None else explicit_enabled
        found_dest["enabled"] = new_enabled

        active_prio_changed = False
        if not new_enabled:
            if found_rule.get("force_override") == target_prio:
                found_rule["force_override"] = 0
            if found_rule.get("active_priority") == target_prio:
                enabled_dests = [d for d in found_rule.get("destinations", []) if d.get("enabled", True)]
                if enabled_dests:
                    found_rule["active_priority"] = enabled_dests[0].get("priority", 1)
                    active_prio_changed = True

        if save_config(cfg):
            update_state_rules({
                matched_rule_id: {
                    "active_priority": found_rule.get("active_priority", 1),
                    "force_override": found_rule.get("force_override", 0)
                }
            })
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            if active_prio_changed:
                _safe_flush_port_conntrack(found_rule.get("port", 0))
            self.send_json({
                "ok": True,
                "rule_id": matched_rule_id,
                "priority": target_prio,
                "enabled": new_enabled,
                "rule": found_rule,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })
        else:
            self.send_json({"ok": False, "error": "Save failed"}, 500)

    def _handle_delete_rule_request(self, rule_id: str) -> None:
        """Deletes a forwarding rule by ID or port and cleans up runtime state."""
        if not rule_id:
            self.send_json({"ok": False, "error": "Rule ID required"}, 400)
            return
        cfg = load_config()
        orig_rules = cfg.get("rules", [])
        idx = XForwarderWebHandler._find_rule_index(self, orig_rules, rule_id)
        if idx is None:
            self.send_json({"ok": False, "error": "Rule not found"}, 404)
            return
        removed_rule = orig_rules[idx]
        cfg["rules"] = [r for i, r in enumerate(orig_rules) if i != idx]
        if save_config(cfg):
            cleanup_ids = [rule_id, *_get_rule_all_ids(removed_rule)]
            remove_state_rules(list(dict.fromkeys(cleanup_ids)))
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": True,
                "deleted": rule_id,
                "deleted_count": 1,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            })
        else:
            self.send_json({"ok": False, "error": "Save failed"}, 500)

    def _handle_settings_update(self, body: Any) -> None:
        """Validates and updates global failover/probing engine settings."""
        if not isinstance(body, dict) or len(body) == 0:
            self.send_json({"ok": False, "error": "JSON object with settings fields required"}, 400)
            return
        unknown = [k for k in body.keys() if k not in GLOBAL_SETTINGS_KEYS]
        if unknown:
            self.send_json({"ok": False, "error": f"Unknown settings key(s): {', '.join(unknown)}"}, 400)
            return
        cfg = load_config()
        for k, v in body.items():
            if k == "wan_interface":
                iface_val = str(v or "auto").strip()
                if iface_val != "auto" and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.\-]{0,14}", iface_val):
                    self.send_json({"ok": False, "error": f"Invalid wan_interface '{iface_val}'"}, 400)
                    return
                cfg[k] = iface_val or "auto"
            elif k == "fast_failover_enabled":
                cfg[k] = bool(v)
            else:
                if isinstance(v, bool):
                    self.send_json({"ok": False, "error": f"Setting '{k}' must be numeric"}, 400)
                    return
                try:
                    cfg[k] = float(v) if k == "hysteresis_percent" else int(v)
                except (ValueError, TypeError):
                    self.send_json({"ok": False, "error": f"Setting '{k}' must be numeric"}, 400)
                    return
        cfg, _ = migrate_and_normalize_config(cfg)
        if save_config(cfg):
            notify_engine_wakeup()
            self.send_json({"ok": True, "settings": {k: cfg.get(k) for k in GLOBAL_SETTINGS_KEYS}})
        else:
            self.send_json({"ok": False, "error": "Failed to save settings"}, 500)

    def _handle_api_keys_create(self, body: Any) -> None:
        """Creates a new scoped API key and returns the secret once."""
        if not isinstance(body, dict):
            self.send_json({"ok": False, "error": "Invalid JSON body"}, 400)
            return
        raw_name = str(body.get("name") or "").strip()
        clean_name = "".join(c for c in raw_name[:64] if ord(c) >= 32 and c not in "<>\";`$\\{}")
        if not clean_name:
            self.send_json({"ok": False, "error": "API key 'name' must contain valid characters"}, 400)
            return
        name = clean_name
        scope = str(body.get("scope") or "admin").strip().lower()
        if scope not in VALID_API_SCOPES:
            self.send_json({"ok": False, "error": f"Invalid scope '{scope}'. Allowed: {', '.join(VALID_API_SCOPES)}"}, 400)
            return
        expires_days = body.get("expires_in_days")
        if expires_days is not None and expires_days != "":
            if isinstance(expires_days, bool):
                self.send_json({"ok": False, "error": "expires_in_days must be a non-negative integer"}, 400)
                return
            try:
                expires_days = int(expires_days)
                if expires_days < 0 or expires_days > 3650:
                    raise ValueError()
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "expires_in_days must be between 0 and 3650"}, 400)
                return
        else:
            expires_days = None

        raw_key, record = generate_api_key(name=name, scope=scope, expires_in_days=expires_days)
        cfg = load_config()
        api_keys = cfg.setdefault("web", {}).setdefault("api_keys", [])
        if len(api_keys) >= 50:
            self.send_json({"ok": False, "error": "Maximum of 50 API keys reached"}, 409)
            return
        api_keys.append(record)
        if save_config(cfg):
            self.send_json({
                "ok": True,
                "api_key": raw_key,
                "key": sanitize_api_key_record(record),
            }, 201)
        else:
            self.send_json({"ok": False, "error": "Failed to save API key"}, 500)

    def _handle_api_keys_update(self, key_id: str, body: Any) -> None:
        """Updates an existing API key's name, scope, or enabled state."""
        if not isinstance(body, dict):
            self.send_json({"ok": False, "error": "Invalid JSON body"}, 400)
            return
        cfg = load_config()
        api_keys = cfg.get("web", {}).get("api_keys", [])
        target_rec = next((k for k in api_keys if isinstance(k, dict) and k.get("id") == key_id), None)
        if not target_rec:
            self.send_json({"ok": False, "error": "API key not found"}, 404)
            return
        if "name" in body:
            clean_name = "".join(c for c in str(body.get("name") or "").strip()[:64] if ord(c) >= 32 and c not in "<>\";`$\\{}")
            if not clean_name:
                self.send_json({"ok": False, "error": "API key name cannot be empty"}, 400)
                return
            target_rec["name"] = clean_name
        if "scope" in body:
            sc = str(body.get("scope") or "").strip().lower()
            if sc not in VALID_API_SCOPES:
                self.send_json({"ok": False, "error": f"Invalid scope '{sc}'. Allowed: {', '.join(VALID_API_SCOPES)}"}, 400)
                return
            target_rec["scope"] = sc
        if "enabled" in body:
            target_rec["enabled"] = bool(body["enabled"])
        if save_config(cfg):
            self.send_json({"ok": True, "key": sanitize_api_key_record(target_rec)})
        else:
            self.send_json({"ok": False, "error": "Failed to save API key"}, 500)

    def _handle_api_keys_delete(self, key_id: str) -> None:
        """Revokes and removes an API key."""
        cfg = load_config()
        api_keys = cfg.get("web", {}).get("api_keys", [])
        remaining = [k for k in api_keys if not (isinstance(k, dict) and k.get("id") == key_id)]
        if len(remaining) == len(api_keys):
            self.send_json({"ok": False, "error": "API key not found"}, 404)
            return
        cfg["web"]["api_keys"] = remaining
        if save_config(cfg):
            self.send_json({"ok": True, "deleted": key_id})
        else:
            self.send_json({"ok": False, "error": "Failed to delete API key"}, 500)

    def do_OPTIONS(self):
        allowed, _, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return
        self.send_response(204)
        self.send_header("Allow", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.apply_security_headers()
        self.end_headers()

    def do_POST(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if _reject_disallowed_origin(self):
            return

        ok_body, body = _parse_json_body(self)
        if not ok_body:
            return

        if subpath.startswith("/api/"):
            subpath = _normalize_api_subpath(subpath)

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

        # 3. Security Credentials & API Keys Management
        if subpath in ("/api/api-keys", "/api/security/api-keys"):
            if not _require_scope(self, "admin"):
                return
            XForwarderWebHandler._handle_api_keys_create(self, body)
            return

        if subpath in ("/api/security", "/api/security/credentials"):
            if not _require_scope(self, "admin"):
                return
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

        elif subpath == "/api/security/panel":
            if not _require_scope(self, "admin"):
                return
            cfg = load_config()
            web_cfg = cfg.setdefault("web", {})
            old_port = int(web_cfg.get("port", 8090) or 8090)
            old_secret = str(web_cfg.get("secret_path", "xfwd-admin") or "").strip().strip("/")

            raw_port = body.get("port", old_port)
            if isinstance(raw_port, bool):
                self.send_json({"ok": False, "error": "Panel port must be a valid integer between 1 and 65535"}, 400)
                return
            try:
                new_port = int(raw_port)
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Panel port must be a valid integer between 1 and 65535"}, 400)
                return
            if new_port < 1 or new_port > 65535:
                self.send_json({"ok": False, "error": "Panel port must be between 1 and 65535"}, 400)
                return

            if "secret_path" in body:
                new_secret = str(body.get("secret_path") or "").strip().strip("/")
            else:
                new_secret = old_secret

            if new_secret:
                if len(new_secret) > 64 or not re.fullmatch(r"[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", new_secret):
                    self.send_json({"ok": False, "error": "Panel path must contain only letters, numbers, '-', '_', or '/' (max 64 chars)"}, 400)
                    return
                first_seg = new_secret.split("/", 1)[0].lower()
                if first_seg in ("api", "css", "js", "rules", "overview", "traffic", "services", "updates", "security", "logs", "favicon.ico"):
                    self.send_json({"ok": False, "error": f"Panel path '/{new_secret}' conflicts with reserved dashboard routes"}, 400)
                    return

            if new_port != old_port:
                for r in cfg.get("rules", []):
                    if not isinstance(r, dict) or r.get("excluded_ports"):
                        continue
                    sp, ep, _ = get_rule_port_bounds(r)
                    if sp is not None and ep is not None and sp <= new_port <= ep:
                        r_label = r.get("port_range") or r.get("port")
                        self.send_json({"ok": False, "error": f"Port {new_port} overlaps with existing forwarding rule ({r_label})"}, 409)
                        return

                bind_host = str(web_cfg.get("bind_host", "0.0.0.0") or "0.0.0.0")
                sock_family = socket.AF_INET6 if ":" in bind_host else socket.AF_INET
                test_sock = socket.socket(sock_family, socket.SOCK_STREAM)
                try:
                    test_sock.bind((bind_host, new_port))
                except OSError:
                    self.send_json({"ok": False, "error": f"Port {new_port} is already in use by another service"}, 409)
                    return
                finally:
                    try:
                        test_sock.close()
                    except Exception:
                        pass

            if new_port == old_port and new_secret == old_secret:
                self.send_json({
                    "ok": True,
                    "changed": False,
                    "restarting": False,
                    "port": new_port,
                    "secret_path": new_secret,
                    "message": "Panel access settings are already up to date"
                })
                return

            web_cfg["port"] = new_port
            web_cfg["secret_path"] = new_secret
            if not save_config(cfg):
                self.send_json({"ok": False, "error": "Failed to save configuration"}, 500)
                return

            if new_port != old_port:
                sync_rules_and_notify(max_retries=2)

            ok, msg, is_reconnecting = restart_services_action("web", sync_rules_func=sync_rules_and_notify, notify_func=notify_engine_wakeup)
            with _SERVICES_LOCK:
                _SERVICES_CACHE["expires"] = 0.0
            if ok:
                self.send_json({
                    "ok": True,
                    "changed": True,
                    "restarting": is_reconnecting,
                    "port": new_port,
                    "secret_path": new_secret,
                    "message": msg
                })
            else:
                self.send_json({"ok": False, "error": msg}, 500)
            return

        elif subpath == "/api/rule":
            if not _require_scope(self, "write"):
                return
            XForwarderWebHandler._save_rule_payload(self, body, create_only=False)

        elif subpath == "/api/rules":
            if not _require_scope(self, "write"):
                return
            XForwarderWebHandler._save_rule_payload(self, body, create_only=True)

        elif subpath == "/api/override" or ((subpath.startswith("/api/rule/") or subpath.startswith("/api/rules/")) and subpath.endswith("/override")):
            if not _require_scope(self, "write"):
                return
            if subpath.startswith("/api/rule/") or subpath.startswith("/api/rules/"):
                parts = subpath.split("/")
                url_rule_id = unquote(parts[3]) if len(parts) >= 4 else ""
                rule_id = str(body.get("rule_id", url_rule_id) or url_rule_id)
            else:
                rule_id = str(body.get("rule_id", ""))
            XForwarderWebHandler._handle_override_request(self, rule_id, body)
            return

        elif subpath == "/api/override/batch":
            if not _require_scope(self, "write"):
                return
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
                for r in rules:
                    _safe_flush_port_conntrack(r.get("port", 0))
                self.send_json({
                    "ok": True,
                    "count": len(rules),
                    "force_override": override_prio,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath in ("/api/rule/toggle-destination", "/api/destination/toggle") or (
            (subpath.startswith("/api/rules/") or subpath.startswith("/api/rule/"))
            and "/destinations/" in subpath
            and subpath.endswith("/toggle")
        ):
            if not _require_scope(self, "write"):
                return
            if "/destinations/" in subpath:
                parts = subpath.split("/")
                # /api/rules/<rule_id>/destinations/<priority>/toggle
                rule_id = unquote(parts[3]) if len(parts) >= 7 else ""
                raw_prio = parts[5] if len(parts) >= 7 else "1"
            else:
                rule_id = str(body.get("rule_id", "")).strip()
                raw_prio = body.get("priority", 1)
            try:
                target_prio = int(raw_prio)
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid priority"}, 400)
                return

            explicit_enabled = body.get("enabled") if isinstance(body, dict) else None
            if explicit_enabled is not None:
                explicit_enabled = bool(explicit_enabled)
            XForwarderWebHandler._handle_toggle_destination_request(self, rule_id, target_prio, explicit_enabled)
            return

        elif subpath == "/api/sync":
            if not _require_scope(self, "write"):
                return
            sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
            self.send_json({
                "ok": sync_ok,
                "sync_ok": sync_ok,
                "sync_errors": sync_errors
            }, 200 if sync_ok else 500)

        elif subpath == "/api/import/haproxy":
            if not _require_scope(self, "write"):
                return
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
            if not _require_scope(self, "write"):
                return
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
            if not _require_scope(self, "write"):
                return
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

        elif subpath == "/api/rules/bulk-delete":
            if not _require_scope(self, "write"):
                return
            raw_ids = body.get("rule_ids") if isinstance(body, dict) else None
            if not isinstance(raw_ids, list) or len(raw_ids) == 0:
                self.send_json({"ok": False, "error": "rule_ids list required"}, 400)
                return
            del_ids = {unquote(str(rid)).strip() for rid in raw_ids if str(rid).strip()}
            if not del_ids:
                self.send_json({"ok": False, "error": "No valid rule IDs"}, 400)
                return
            cfg = load_config()
            orig_rules = cfg.get("rules", [])
            removed_rules = [r for r in orig_rules if any(_rule_matches_target_id(r, did) for did in del_ids)]
            remaining = [r for r in orig_rules if not any(_rule_matches_target_id(r, did) for did in del_ids)]
            removed_count = len(orig_rules) - len(remaining)
            cfg["rules"] = remaining
            if save_config(cfg):
                cleanup_ids = list(del_ids)
                for rr in removed_rules:
                    cleanup_ids.extend(_get_rule_all_ids(rr))
                remove_state_rules(list(dict.fromkeys(cleanup_ids)))
                sync_ok, sync_errors = sync_rules_and_notify(max_retries=2)
                self.send_json({
                    "ok": True,
                    "deleted_count": removed_count,
                    "sync_ok": sync_ok,
                    "sync_errors": sync_errors
                })
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/config/import":
            if not _require_scope(self, "write"):
                return
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
            if not _require_scope(self, "write"):
                return
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
            packets = max(1, min(packets, 50))

            try:
                from core.prober import check_destination
                from core.config_manager import IFACE_NAME_REGEX
                test_dest = {"target": target, "port": port, "type": dest_type}
                tunnel_iface = str(body.get("tunnel_iface") or "").strip()
                if tunnel_iface and dest_type in ("nftables", "nftables_dsr", "nftables_dsr_synack") and IFACE_NAME_REGEX.match(tunnel_iface):
                    test_dest["tunnel_iface"] = tunnel_iface
                ingress_iface = str(body.get("ingress_iface") or "").strip()
                if ingress_iface and dest_type in ("nftables_dsr_relay", "nftables_dsr_direct") and IFACE_NAME_REGEX.match(ingress_iface):
                    test_dest["ingress_iface"] = ingress_iface
                probe_res = check_destination(
                    test_dest,
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
            if not _require_scope(self, "write"):
                return
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
            if not _require_scope(self, "write"):
                return
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

        elif subpath == "/api/system/update/transports":
            if not _require_scope(self, "admin"):
                return
            if not isinstance(body, dict):
                self.send_json({"ok": False, "error": "Invalid JSON body"}, 400)
                return
            ok_v, err_v, clean_t = validate_update_transport_config(body, require_target=True)
            if not ok_v:
                self.send_json({"ok": False, "error": err_v}, 400)
                return
            cfg = load_config()
            cfg["system_update"] = clean_t
            if not save_config(cfg):
                self.send_json({"ok": False, "error": "Failed to save update transport configuration"}, 500)
                return
            invalidate_remote_version_cache()
            resp_payload: Dict[str, Any] = {"ok": True, "system_update": clean_t}
            if bool(body.get("test", False)):
                resp_payload["version_status"] = get_full_version_status(force=True)
            self.send_json(resp_payload)
            return

        elif subpath == "/api/system/update":
            if not _require_scope(self, "admin"):
                return
            transport_override = None
            if isinstance(body, dict) and any(
                k in body for k in ("transport_mode", "tunnel_iface", "proxy_url", "mirror_url")
            ):
                ok_v, err_v, clean_t = validate_update_transport_config(body, require_target=True)
                if not ok_v:
                    self.send_json({"ok": False, "status": "error", "error": err_v}, 400)
                    return
                cfg = load_config()
                cfg["system_update"] = clean_t
                save_config(cfg)
                invalidate_remote_version_cache()
                transport_override = clean_t

            ok, msg = start_system_update(transport_override=transport_override)
            if ok:
                self.send_json({"ok": True, "status": "started", "message": msg})
            else:
                code = 409 if "already" in msg else (400 if "Invalid" in msg or "required" in msg else 500)
                self.send_json({"ok": False, "status": "error", "error": msg}, code)
            return

        elif subpath == "/api/services/restart":
            if not _require_scope(self, "admin"):
                return
            svc = body.get("service", "all")
            ok, msg, is_reconnecting = restart_services_action(svc, sync_rules_func=sync_rules_and_notify, notify_func=notify_engine_wakeup)
            with _SERVICES_LOCK:
                _SERVICES_CACHE["expires"] = 0.0
            if ok:
                self.send_json({"ok": True, "service": svc, "message": msg, "reconnecting": is_reconnecting})
            else:
                self.send_json({"ok": False, "service": svc, "error": msg}, 400 if "Invalid" in msg else 500)
            return

        elif subpath == "/api/system/optimize":
            if not _require_scope(self, "admin"):
                return
            if not isinstance(body, dict):
                body = {}
            reset_existing = bool(body.get("reset_existing", False))
            res = apply_kernel_tuning(reset_existing=reset_existing)
            with _SERVICES_LOCK:
                _SERVICES_CACHE["expires"] = 0.0
            self.send_json(res, 200 if res.get("ok") else 500)
            return

        elif subpath == "/api/system/spoof-test/listen":
            if not _require_scope(self, "admin"):
                return
            if not isinstance(body, dict):
                body = {}
            action = str(body.get("action", "start")).strip().lower()
            if action == "stop":
                st = stop_spoof_test_listener()
                self.send_json({"ok": True, "message": "UDP spoof test listener stopped.", "listener": st})
                return
            try:
                p_num = int(body.get("port", 55199) or 55199)
                t_sec = int(body.get("timeout", 180) or 180)
            except (TypeError, ValueError):
                self.send_json({"ok": False, "error": "Invalid port or timeout value."}, 400)
                return
            ok_l, msg_l, st_l = start_spoof_test_listener(port=p_num, timeout_sec=t_sec)
            self.send_json({"ok": ok_l, "message": msg_l, "error": None if ok_l else msg_l, "listener": st_l}, 200 if ok_l else 400)
            return

        elif subpath == "/api/system/spoof-test/run":
            if not _require_scope(self, "admin"):
                return
            if not isinstance(body, dict):
                self.send_json({"ok": False, "error": "Invalid JSON body"}, 400)
                return
            peer_ip = str(body.get("peer_ip", "")).strip()
            spoof_ip = str(body.get("spoof_ip", "")).strip()
            try:
                p_num = int(body.get("port", 55199) or 55199)
                cnt = int(body.get("count", 5) or 5)
            except (TypeError, ValueError):
                self.send_json({"ok": False, "error": "Invalid port or count value."}, 400)
                return
            res = run_spoof_egress_test(peer_ip=peer_ip, spoof_ip=spoof_ip, port=p_num, count=cnt)
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        elif subpath == "/api/traffic/reset":
            if not _require_scope(self, "write"):
                return
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

    def _dispatch_put_or_patch(self, is_patch: bool) -> None:
        """Shared dispatcher for PUT (replace) and PATCH (partial update) requests."""
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if _reject_disallowed_origin(self):
            return

        ok_body, body = _parse_json_body(self)
        if not ok_body:
            return

        if subpath.startswith("/api/"):
            subpath = _normalize_api_subpath(subpath)

        if subpath.startswith("/api/rules/") or subpath.startswith("/api/rule/"):
            if not _require_scope(self, "write"):
                return
            prefix = "/api/rules/" if subpath.startswith("/api/rules/") else "/api/rule/"
            rule_id = unquote(subpath[len(prefix):]).strip().strip("/")
            if not rule_id or "/" in rule_id:
                self.send_json({"ok": False, "error": "Rule ID required"}, 400)
                return
            XForwarderWebHandler._save_rule_payload(self, body, target_rule_id=rule_id, partial=is_patch)
            return

        if subpath == "/api/settings":
            if not _require_scope(self, "admin"):
                return
            XForwarderWebHandler._handle_settings_update(self, body)
            return

        if is_patch and (subpath.startswith("/api/api-keys/") or subpath.startswith("/api/security/api-keys/")):
            if not _require_scope(self, "admin"):
                return
            prefix = "/api/api-keys/" if subpath.startswith("/api/api-keys/") else "/api/security/api-keys/"
            key_id = unquote(subpath[len(prefix):]).strip().strip("/")
            if not key_id or "/" in key_id:
                self.send_json({"ok": False, "error": "API key ID required"}, 400)
                return
            XForwarderWebHandler._handle_api_keys_update(self, key_id, body)
            return

        if not _require_scope(self, "read"):
            return
        self.send_error(404, "Not Found")

    def do_PUT(self):
        self._dispatch_put_or_patch(is_patch=False)

    def do_PATCH(self):
        self._dispatch_put_or_patch(is_patch=True)

    def do_DELETE(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if _reject_disallowed_origin(self):
            return

        if subpath.startswith("/api/"):
            subpath = _normalize_api_subpath(subpath)

        if subpath.startswith("/api/api-keys/") or subpath.startswith("/api/security/api-keys/"):
            if not _require_scope(self, "admin"):
                return
            prefix = "/api/api-keys/" if subpath.startswith("/api/api-keys/") else "/api/security/api-keys/"
            key_id = unquote(subpath[len(prefix):]).strip().strip("/")
            if not key_id or "/" in key_id:
                self.send_json({"ok": False, "error": "API key ID required"}, 400)
                return
            XForwarderWebHandler._handle_api_keys_delete(self, key_id)
            return

        if subpath.startswith("/api/rules/") or subpath.startswith("/api/rule/"):
            if not _require_scope(self, "write"):
                return
            prefix = "/api/rules/" if subpath.startswith("/api/rules/") else "/api/rule/"
            rule_id = unquote(subpath[len(prefix):]).strip().strip("/")
            XForwarderWebHandler._handle_delete_rule_request(self, rule_id)
            return

        if not _require_scope(self, "read"):
            return
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

#!/usr/bin/env python3
"""
XForwarder - 24/7 Always-Online Web Server
Provides a secure English dashboard with session authentication (Username & Password).
"""

import os
import sys
import time
import json
import hashlib
import hmac
import secrets
import socket
import subprocess
import threading
import ipaddress
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Optional, Dict, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

WEB_DIR = os.path.join(BASE_DIR, "web")
CONFIG_PATH = "/etc/xforwarder/config.json"
LEGACY_CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
STATE_FILE_PATH = "/run/xforwarder/state.json"
LEGACY_STATE_FILE_PATH = "/run/forward-manager/state.json"

ACTIVE_SESSIONS: Dict[str, dict] = {}
SESSION_LOCK = threading.Lock()
SESSION_TTL_HOURS = 24
SESSION_IDLE_TIMEOUT_SECONDS = 14400  # 4 hours idle limit
MAX_ACTIVE_SESSIONS = 50

# Rate Limiting & Brute-Force Shield State
FAILED_LOGIN_ATTEMPTS: Dict[str, dict] = {}
RATE_LIMIT_LOCK = threading.Lock()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes lockout
WINDOW_DURATION = 300   # 5 minutes failure evaluation window

try:
    from engine import XForwarderEngine
    migrate_config = XForwarderEngine.migrate_and_normalize_config
except ImportError:
    try:
        from core.engine import XForwarderEngine
        migrate_config = XForwarderEngine.migrate_and_normalize_config
    except ImportError:
        migrate_config = None


def get_config_path() -> str:
    if os.path.exists(CONFIG_PATH):
        return CONFIG_PATH
    if os.path.exists(LEGACY_CONFIG_PATH):
        return LEGACY_CONFIG_PATH
    if os.path.exists(LOCAL_CONFIG_PATH):
        return LOCAL_CONFIG_PATH
    return CONFIG_PATH


def load_config() -> dict:
    path = get_config_path()
    cfg = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    if not isinstance(cfg, dict):
        cfg = {
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
                    "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918" # admin
                }
            },
            "rules": []
        }
    if migrate_config:
        cfg, modified = migrate_config(cfg)
        if modified and os.path.exists(path):
            save_config(cfg)
    return cfg


def save_config(cfg: dict) -> bool:
    path = get_config_path()
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}", file=sys.stderr)
        return False


def load_state() -> dict:
    for path in [STATE_FILE_PATH, LEGACY_STATE_FILE_PATH]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def get_system_stats() -> dict:
    stats = {
        "ram_used_mb": 0,
        "ram_total_mb": 0,
        "ram_percent": 0,
        "cpu_percent": 0
    }
    if os.path.exists("/proc/meminfo"):
        try:
            mem = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        mem[parts[0].strip()] = parts[1].strip().split()[0]
            total_kb = float(mem.get("MemTotal", 0))
            avail_kb = float(mem.get("MemAvailable", mem.get("MemFree", 0)))
            used_kb = max(0.0, total_kb - avail_kb)
            if total_kb > 0:
                stats["ram_total_mb"] = int(round(total_kb / 1024))
                stats["ram_used_mb"] = int(round(used_kb / 1024))
                stats["ram_percent"] = round((used_kb / total_kb) * 100, 1)
        except Exception:
            pass
    if os.path.exists("/proc/loadavg"):
        try:
            with open("/proc/loadavg", "r", encoding="utf-8") as f:
                load = float(f.read().split()[0])
                cpu_count = os.cpu_count() or 1
                stats["cpu_percent"] = min(100.0, round((load / cpu_count) * 100, 1))
        except Exception:
            pass
    return stats


PBKDF2_ITERATIONS = 100000


def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    """Generates a secure PBKDF2-HMAC-SHA256 salted password hash."""
    if not salt_hex:
        salt_hex = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt_hex}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> Tuple[bool, bool]:
    """
    Verifies password against stored hash using constant-time comparison.
    Returns: (is_valid, needs_rehash)
    Backward compatible with legacy SHA-256 with automatic seamless upgrade to PBKDF2.
    """
    if not stored_hash or not password or not isinstance(password, str):
        return False, False

    # Modern salted PBKDF2-HMAC-SHA256 format
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) == 3:
                header, salt_hex, expected_hex = parts
                iters = int(header.split(":")[-1])
                salt_bytes = bytes.fromhex(salt_hex)
                derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iters)
                return hmac.compare_digest(derived.hex(), expected_hex), False
        except Exception:
            return False, False

    # Legacy plain SHA-256 hash (64 hex characters)
    legacy_test = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hmac.compare_digest(legacy_test, stored_hash):
        return True, True  # Valid, but triggers self-healing upgrade to salted PBKDF2!

    return False, False


def check_rate_limit(client_ip: str) -> Tuple[bool, int, int]:
    """Checks if client IP is currently rate-limited. Returns (is_locked, remaining_seconds, fail_count)."""
    now = time.time()
    with RATE_LIMIT_LOCK:
        record = FAILED_LOGIN_ATTEMPTS.get(client_ip)
        if not record:
            return False, 0, 0

        lockout_until = record.get("lockout_until", 0)
        if now < lockout_until:
            remaining = int(lockout_until - now)
            return True, remaining, record.get("count", 0)

        # If evaluation window expired and not locked out, clear record
        if now > record.get("first_attempt", 0) + WINDOW_DURATION:
            FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)
            return False, 0, 0

        return False, 0, record.get("count", 0)


def record_failed_login(client_ip: str) -> Tuple[bool, int, int]:
    """Records a failed login attempt and calculates lockout status."""
    now = time.time()
    with RATE_LIMIT_LOCK:
        record = FAILED_LOGIN_ATTEMPTS.get(client_ip)
        if not record or now > record.get("first_attempt", 0) + WINDOW_DURATION:
            record = {"count": 1, "first_attempt": now, "lockout_until": 0}
        else:
            record["count"] += 1

        is_locked = False
        remaining = 0
        if record["count"] >= MAX_FAILED_ATTEMPTS:
            record["lockout_until"] = now + LOCKOUT_DURATION
            is_locked = True
            remaining = LOCKOUT_DURATION

        FAILED_LOGIN_ATTEMPTS[client_ip] = record

        # Prune expired entries if dict is growing
        if len(FAILED_LOGIN_ATTEMPTS) > 100:
            stale = [k for k, v in FAILED_LOGIN_ATTEMPTS.items() if now > v.get("lockout_until", 0) and now > v.get("first_attempt", 0) + WINDOW_DURATION]
            for k in stale:
                FAILED_LOGIN_ATTEMPTS.pop(k, None)

        return is_locked, remaining, record["count"]


def reset_rate_limit(client_ip: str):
    """Clears failed login counter on successful authentication."""
    with RATE_LIMIT_LOCK:
        FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)


HOSTNAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def is_valid_target(target: str) -> bool:
    """Strictly validates if a destination target is a valid IPv4, IPv6, or RFC hostname."""
    clean = target.strip().strip("[]")
    if not clean:
        return False
    # Check IPv4 or IPv6
    try:
        ipaddress.ip_address(clean)
        return True
    except ValueError:
        pass

    # If it is an all-numeric dotted quad that failed IP validation, it is invalid
    parts = clean.split(".")
    if all(p.isdigit() for p in parts):
        return False

    # Check RFC hostname (TLD cannot be purely numeric per RFC 3696)
    if HOSTNAME_REGEX.match(clean):
        if len(parts) > 1 and parts[-1].isdigit():
            return False
        return True
    return False


def validate_rule(body: dict) -> Tuple[bool, str]:
    if not isinstance(body, dict):
        return False, "Invalid JSON body"

    port = body.get("port")
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return False, "Port must be between 1 and 65535"
        body["port"] = port
    except (ValueError, TypeError):
        return False, "Port must be a valid integer"

    proto = str(body.get("protocol", "both")).lower()
    if proto not in ("tcp", "udp", "both"):
        return False, "Protocol must be 'tcp', 'udp', or 'both'"
    body["protocol"] = proto

    dests = body.get("destinations", [])
    if not isinstance(dests, list) or len(dests) == 0:
        return False, "At least one destination is required"

    for d in dests:
        if not isinstance(d, dict):
            return False, "Invalid destination item"
        target = str(d.get("target", "")).strip()
        if not target:
            return False, "Destination target cannot be empty"

        # Disallow control characters or shell injection hazards
        if any(c in target for c in ";&|`$ \t\n\r<>\"'"):
            return False, "Destination target contains invalid characters"

        if not is_valid_target(target):
            return False, f"Invalid destination target '{target}'. Must be a valid IPv4, IPv6, or hostname"

        d_type = str(d.get("type", "haproxy")).lower()
        if d_type not in ("haproxy", "nftables", "nginx"):
            return False, "Destination type must be 'haproxy', 'nftables', or 'nginx'"
        d["type"] = d_type

        d_port = d.get("port", port)
        try:
            d_port = int(d_port)
            if d_port < 1 or d_port > 65535:
                return False, "Destination port must be between 1 and 65535"
            d["port"] = d_port
        except (ValueError, TypeError):
            return False, "Destination port must be a valid integer"

    return True, ""


def is_haproxy_listening(port: int) -> bool:
    """Returns True if the process currently listening on port is HAProxy (which XForwarder manages)."""
    try:
        res = subprocess.run(["ss", "-tlpn", f"sport = :{port}"], capture_output=True, text=True, timeout=1.0)
        if "haproxy" in res.stdout.lower():
            return True
    except Exception:
        pass
    return False


def is_port_in_use_by_external_service(port: int, current_rule_id: str, existing_rules: list) -> bool:
    """Checks if a port is actively bound by an external non-HAProxy process not managed by this rule."""
    for r in existing_rules:
        if r.get("id") == current_rule_id and r.get("port") == port:
            return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                # If connected, check if it's HAProxy (which XForwarder will orchestrate and reload)
                if is_haproxy_listening(port):
                    return False
                return True
    except Exception:
        pass
    return False


class XForwarderWebHandler(BaseHTTPRequestHandler):
    server_instance: 'XForwarderWebServer'
    server_version = "XForwarder-Shield/2.0"
    sys_version = ""

    def apply_security_headers(self, cookie_token: Optional[str] = None):
        """Applies comprehensive OWASP recommended security headers."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        )
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")

        is_https = self.headers.get("X-Forwarded-Proto") == "https"
        secure_flag = "; Secure" if is_https else ""

        if cookie_token:
            self.send_header("Set-Cookie", f"xfwd_session={cookie_token}; Path=/; HttpOnly; SameSite=Strict{secure_flag}")
        elif cookie_token == "":
            self.send_header("Set-Cookie", f"xfwd_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Strict{secure_flag}")
            self.send_header("Set-Cookie", f"fwdman_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Strict{secure_flag}")

    def send_json(self, data: dict, status: int = 200, cookie_token: Optional[str] = None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.apply_security_headers()
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
        # Check custom header first
        auth_header = self.headers.get("X-Session-Token")
        if auth_header:
            return auth_header

        # Check cookies
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

            # Check absolute expiry or idle timeout
            if now > session.get("expires_at", 0) or (now - session.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS:
                ACTIVE_SESSIONS.pop(token, None)
                return False

            # Slide activity window
            session["last_active"] = now

            # Bound session table size
            if len(ACTIVE_SESSIONS) > MAX_ACTIVE_SESSIONS:
                stale = [k for k, v in ACTIVE_SESSIONS.items() if now > v.get("expires_at", 0) or (now - v.get("last_active", 0)) > SESSION_IDLE_TIMEOUT_SECONDS]
                for k in stale:
                    ACTIVE_SESSIONS.pop(k, None)
        return True

    def resolve_path(self) -> Tuple[bool, str, Optional[str]]:
        """
        Resolves the requested path against configured secret_path.
        Returns: (is_allowed, normalized_subpath, redirect_url)
        """
        parsed = urlparse(self.path)
        raw_path = parsed.path
        cfg = load_config()
        secret = cfg.get("web", {}).get("secret_path", "")
        secret = str(secret or "").strip().strip("/")

        # Favicon optimization
        if raw_path == "/favicon.ico":
            return True, "/favicon.ico", None

        # Case 1: No secret path configured -> direct root access allowed
        if not secret:
            clean = raw_path.rstrip("/") or "/"
            return True, clean, None

        secret_prefix = f"/{secret}"

        # Exact match without trailing slash -> redirect to /{secret}/
        if raw_path == secret_prefix:
            return True, "/", f"{secret_prefix}/"

        # Request under /{secret}/
        if raw_path.startswith(f"{secret_prefix}/"):
            subpath = raw_path[len(secret_prefix):]
            clean = subpath.rstrip("/") or "/"
            return True, clean, None

        # Allow authenticated requests to /api/ if user already has a valid session token
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

        # Favicon optimization
        if subpath == "/favicon.ico":
            self.send_response(204)
            self.apply_security_headers()
            self.end_headers()
            return

        # Static assets
        if subpath == "/style.css":
            self.send_file(os.path.join(WEB_DIR, "style.css"), "text/css; charset=utf-8")
            return
        elif subpath == "/app.js":
            self.send_file(os.path.join(WEB_DIR, "app.js"), "application/javascript; charset=utf-8")
            return

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
                self.send_json({
                    "config": cfg,
                    "runtime": state.get("runtime", {}),
                    "system": get_system_stats(),
                    "server_time": time.time()
                })
                return
            elif subpath == "/api/import/discover":
                cfg = load_config()
                existing_rules = cfg.get("rules", [])
                from core.haproxy_parser import discover_importable_rules
                importable = discover_importable_rules(existing_rules)
                self.send_json({
                    "available": bool(importable),
                    "count": len(importable),
                    "ports": [r["port"] for r in importable],
                    "rules": importable
                })
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

        # CSRF Protection: Verify Origin matches Host
        if not self.check_origin():
            self.send_json({"ok": False, "error": "Cross-origin request rejected"}, 403)
            return

        # DoS Protection: Limit payload size to 64KB
        MAX_PAYLOAD = 65536
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_PAYLOAD:
            self.send_json({"ok": False, "error": "Payload exceeds 64KB limit"}, 413)
            return

        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}

        # 1. Login endpoint (Protected with Adaptive Rate Limiting & PBKDF2)
        if subpath == "/api/login":
            client_ip = self.get_client_ip()

            # Check rate limiting / lockout
            is_locked, remaining, fail_count = check_rate_limit(client_ip)
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

            user_matches = hmac.compare_digest(user, expected_user)
            pwd_valid, needs_rehash = verify_password(pwd, expected_hash)

            if user_matches and pwd_valid:
                reset_rate_limit(client_ip)

                # Automatic self-healing upgrade of legacy SHA-256 hashes to salted PBKDF2
                if needs_rehash:
                    new_salted_hash = hash_password(pwd)
                    cfg["web"]["auth"]["password_hash"] = new_salted_hash
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
                self.send_json({"ok": True, "token": token, "username": user}, 200, cookie_token=token)
            else:
                is_locked_now, lock_remaining, count = record_failed_login(client_ip)
                # Intentional timing jitter delay to defeat automated credential stuffing
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
            self.send_json({"ok": True}, 200, cookie_token="")
            return

        # All other POST endpoints require authentication
        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        # 3. Security Credentials Management (Change Username / Password)
        if subpath == "/api/security/credentials":
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

            # Zero-Collision Check: Ensure no other rule is already using this listening port
            for r in rules:
                if r.get("id") != rule_id and r.get("port") == body["port"]:
                    self.send_json({"ok": False, "error": f"Port {body['port']} is already used by rule '{r.get('id')}'"}, 409)
                    return

            # External Conflict Check: Ensure no external service is listening on this port
            if is_port_in_use_by_external_service(body["port"], rule_id, rules):
                self.send_json({
                    "ok": False,
                    "error": f"Port {body['port']} is already bound by an external system service (e.g. web server, SSH, or proxy)!"
                }, 409)
                return

            updated = False
            for i, r in enumerate(rules):
                if r.get("id") == rule_id:
                    rules[i] = body
                    updated = True
                    break
            if not updated:
                rules.append(body)

            cfg["rules"] = rules
            if save_config(cfg):
                self.send_json({"ok": True, "rule": body})
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/override":
            rule_id = str(body.get("rule_id", ""))
            try:
                override_prio = int(body.get("force_override", 0))
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid force_override value"}, 400)
                return

            if override_prio not in (0, 1, 2):
                self.send_json({"ok": False, "error": "force_override must be 0, 1, or 2"}, 400)
                return

            cfg = load_config()
            found = False
            for r in cfg.get("rules", []):
                if r.get("id") == rule_id:
                    r["force_override"] = override_prio
                    if override_prio > 0:
                        r["active_priority"] = override_prio
                    found = True
                    break
            if not found:
                self.send_json({"ok": False, "error": "Rule not found"}, 404)
                return

            if save_config(cfg):
                self.send_json({"ok": True})
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/override/batch":
            try:
                override_prio = int(body.get("force_override", 0))
            except (ValueError, TypeError):
                self.send_json({"ok": False, "error": "Invalid force_override value"}, 400)
                return

            if override_prio not in (0, 1, 2):
                self.send_json({"ok": False, "error": "force_override must be 0, 1, or 2"}, 400)
                return

            cfg = load_config()
            rules = cfg.get("rules", [])
            for r in rules:
                r["force_override"] = override_prio
                if override_prio > 0:
                    r["active_priority"] = override_prio

            if save_config(cfg):
                self.send_json({"ok": True, "count": len(rules), "force_override": override_prio})
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        elif subpath == "/api/import/haproxy":
            from core.haproxy_parser import import_haproxy_rules_into_config
            cfg_path = get_config_path()
            count, ports = import_haproxy_rules_into_config(cfg_path)
            self.send_json({
                "ok": True,
                "imported_count": count,
                "imported_ports": ports
            })

        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
            return

        if not self.check_origin():
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
                self.send_json({"ok": True, "deleted": rule_id})
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)
        else:
            self.send_error(404, "Not Found")


class XForwarderWebServer:
    def __init__(self, port: Optional[int] = None, bind_host: Optional[str] = None):
        cfg = load_config()
        web_cfg = cfg.get("web", {})
        self.port = port or int(web_cfg.get("port", 8090))
        self.bind_host = bind_host or web_cfg.get("bind_host", "0.0.0.0")
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.is_running = False

    def start(self):
        handler_class = XForwarderWebHandler
        handler_class.server_instance = self

        self.httpd = ThreadingHTTPServer((self.bind_host, self.port), handler_class)
        self.is_running = True

        print(f"\n=======================================================")
        print(f"  XForwarder Web Panel Started (Always-Online)")
        print(f"  Access URL: http://{self.bind_host}:{self.port}/")
        print(f"=======================================================\n")

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        if self.is_running and self.httpd:
            self.is_running = False
            self.httpd.shutdown()
            print("[INFO] Web server stopped successfully.")


# Backward compatibility aliases
ForwardManagerWebHandler = XForwarderWebHandler
ForwardManagerWebServer = XForwarderWebServer

if __name__ == "__main__":
    server = XForwarderWebServer()
    server.start()

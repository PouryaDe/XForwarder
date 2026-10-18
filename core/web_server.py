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
import threading
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

ACTIVE_SESSIONS: Dict[str, float] = {}
SESSION_LOCK = threading.Lock()
SESSION_TTL_HOURS = 24

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


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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


def is_port_in_use_by_external_service(port: int, current_rule_id: str, existing_rules: list) -> bool:
    """Checks if a port is actively bound by an external process not managed by this rule."""
    for r in existing_rules:
        if r.get("id") == current_rule_id and r.get("port") == port:
            return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
    except Exception:
        pass
    return False


class XForwarderWebHandler(BaseHTTPRequestHandler):
    server_instance: 'XForwarderWebServer'

    def send_json(self, data: dict, status: int = 200, cookie_token: Optional[str] = None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        if cookie_token:
            self.send_header("Set-Cookie", f"xfwd_session={cookie_token}; Path=/; HttpOnly; SameSite=Lax")
        elif cookie_token == "":
            self.send_header("Set-Cookie", "xfwd_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT")
            self.send_header("Set-Cookie", "fwdman_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT")
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
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(content)

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
            expiry = ACTIVE_SESSIONS.get(token)
            if not expiry or now > expiry:
                ACTIVE_SESSIONS.pop(token, None)
                return False
            # Bound session table size
            if len(ACTIVE_SESSIONS) > 50:
                stale = [k for k, v in ACTIVE_SESSIONS.items() if now > v]
                for k in stale:
                    del ACTIVE_SESSIONS[k]
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
            self.end_headers()
            return

        if not allowed:
            self.send_error(404, "Not Found")
            return

        # Favicon optimization
        if subpath == "/favicon.ico":
            self.send_response(204)
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
                    "server_time": time.time()
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

        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}

        # 1. Login endpoint
        if subpath == "/api/login":
            cfg = load_config()
            auth_cfg = cfg.get("web", {}).get("auth", {})
            expected_user = auth_cfg.get("username", "admin")
            expected_hash = auth_cfg.get("password_hash", "")

            user = body.get("username", "").strip()
            pwd = body.get("password", "")

            if user == expected_user and hmac.compare_digest(hash_password(pwd), expected_hash):
                token = secrets.token_hex(24)
                with SESSION_LOCK:
                    ACTIVE_SESSIONS[token] = time.time() + (SESSION_TTL_HOURS * 3600)
                self.send_json({"ok": True, "token": token, "username": user}, 200, cookie_token=token)
            else:
                self.send_json({"ok": False, "error": "Invalid username or password"}, 401)
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

        if subpath == "/api/rule":
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

        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        allowed, subpath, _ = self.resolve_path()
        if not allowed:
            self.send_error(404, "Not Found")
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

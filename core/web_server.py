#!/usr/bin/env python3
"""
Forward Manager - 24/7 Always-Online Web Server
Provides a secure English dashboard with session authentication (Username & Password).
"""

import os
import sys
import time
import json
import hashlib
import secrets
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Optional, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
CONFIG_PATH = "/etc/forward-manager/config.json"
LOCAL_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
STATE_FILE_PATH = "/run/forward-manager/state.json"

ACTIVE_SESSIONS: Dict[str, float] = {}
SESSION_TTL_HOURS = 24


def get_config_path() -> str:
    if os.path.exists(CONFIG_PATH):
        return CONFIG_PATH
    if os.path.exists(LOCAL_CONFIG_PATH):
        return LOCAL_CONFIG_PATH
    return CONFIG_PATH


def load_config() -> dict:
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "web": {
            "port": 8090,
            "secret_path": "fwd-admin",
            "auth": {
                "username": "admin",
                "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918" # admin
            }
        },
        "rules": []
    }


def save_config(cfg: dict) -> bool:
    path = get_config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}", file=sys.stderr)
        return False


def load_state() -> dict:
    if os.path.exists(STATE_FILE_PATH):
        try:
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class ForwardManagerWebHandler(BaseHTTPRequestHandler):
    server_instance: 'ForwardManagerWebServer'

    def send_json(self, data: dict, status: int = 200, cookie_token: Optional[str] = None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        if cookie_token:
            self.send_header("Set-Cookie", f"fwdman_session={cookie_token}; Path=/; HttpOnly; SameSite=Lax")
        elif cookie_token == "":
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
            if item.startswith("fwdman_session="):
                return item.split("=")[1].strip()
        return None

    def is_authenticated(self) -> bool:
        token = self.get_session_token()
        if not token:
            return False
        expiry = ACTIVE_SESSIONS.get(token)
        if not expiry or time.time() > expiry:
            ACTIVE_SESSIONS.pop(token, None)
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Static assets
        if path == "/style.css":
            self.send_file(os.path.join(WEB_DIR, "style.css"), "text/css; charset=utf-8")
            return
        elif path == "/app.js":
            self.send_file(os.path.join(WEB_DIR, "app.js"), "application/javascript; charset=utf-8")
            return

        # Check authentication for API
        if path.startswith("/api/"):
            if path == "/api/me":
                auth_ok = self.is_authenticated()
                cfg = load_config()
                username = cfg.get("web", {}).get("auth", {}).get("username", "admin")
                self.send_json({"authenticated": auth_ok, "username": username if auth_ok else None})
                return

            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return

            if path == "/api/status":
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

        # Serve SPA index.html for all other routes
        self.send_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}

        # 1. Login endpoint
        if path == "/api/login":
            cfg = load_config()
            auth_cfg = cfg.get("web", {}).get("auth", {})
            expected_user = auth_cfg.get("username", "admin")
            expected_hash = auth_cfg.get("password_hash", "")

            user = body.get("username", "").strip()
            pwd = body.get("password", "")

            if user == expected_user and hash_password(pwd) == expected_hash:
                token = secrets.token_hex(24)
                ACTIVE_SESSIONS[token] = time.time() + (SESSION_TTL_HOURS * 3600)
                self.send_json({"ok": True, "token": token, "username": user}, 200, cookie_token=token)
            else:
                self.send_json({"ok": False, "error": "Invalid username or password"}, 401)
            return

        # 2. Logout endpoint
        if path == "/api/logout":
            token = self.get_session_token()
            if token:
                ACTIVE_SESSIONS.pop(token, None)
            self.send_json({"ok": True}, 200, cookie_token="")
            return

        # All other POST endpoints require authentication
        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        if path == "/api/rule":
            cfg = load_config()
            rules = cfg.get("rules", [])
            rule_id = body.get("id") or f"rule-{body.get('port')}"
            body["id"] = rule_id

            updated = False
            for i, r in enumerate(rules):
                if r.get("id") == rule_id or r.get("port") == body.get("port"):
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

        elif path == "/api/override":
            rule_id = body.get("rule_id")
            override_prio = int(body.get("force_override", 0))
            cfg = load_config()
            for r in cfg.get("rules", []):
                if r.get("id") == rule_id:
                    r["force_override"] = override_prio
                    if override_prio > 0:
                        r["active_priority"] = override_prio
                    break
            if save_config(cfg):
                self.send_json({"ok": True})
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)

        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if not self.is_authenticated():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        if path.startswith("/api/rule/"):
            rule_id = path.split("/api/rule/")[1].strip()
            cfg = load_config()
            cfg["rules"] = [r for r in cfg.get("rules", []) if r.get("id") != rule_id]
            if save_config(cfg):
                self.send_json({"ok": True, "deleted": rule_id})
            else:
                self.send_json({"ok": False, "error": "Save failed"}, 500)
        else:
            self.send_error(404, "Not Found")


class ForwardManagerWebServer:
    def __init__(self, port: Optional[int] = None):
        cfg = load_config()
        web_cfg = cfg.get("web", {})
        self.port = port or int(web_cfg.get("port", 8090))
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.is_running = False

    def start(self):
        handler_class = ForwardManagerWebHandler
        handler_class.server_instance = self

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler_class)
        self.is_running = True

        print(f"\n=======================================================")
        print(f"  Forward-Manager Web Panel Started (Always-Online)")
        print(f"  Access URL: http://<SERVER-IP>:{self.port}/")
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


if __name__ == "__main__":
    server = ForwardManagerWebServer()
    server.start()

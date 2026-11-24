#!/usr/bin/env python3
import os
import sys
import json
import socket
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.config_manager import (
    validate_update_transport_config,
    normalize_update_transport_config,
    migrate_and_normalize_config,
    load_config,
    save_config,
)
from core.service_manager import (
    build_mirror_git_url,
    build_mirror_api_url,
    discover_local_proxies,
    discover_update_transports,
    get_remote_version_info,
    invalidate_remote_version_cache,
    _open_socks5_socket,
    start_system_update,
)
from core.web_server import XForwarderWebHandler, ACTIVE_SESSIONS, SESSION_LOCK, _UPDATE_LOCK, _UPDATE_STATE


class TestSystemUpdateTransports(unittest.TestCase):
    def test_validate_and_normalize_update_transport_config(self):
        ok, err, clean = validate_update_transport_config({
            "transport_mode": "proxy",
            "proxy_url": "socks5h://127.0.0.1:10808",
            "tunnel_iface": "wg0",
            "mirror_url": "https://ghproxy.net/",
        })
        self.assertTrue(ok, err)
        self.assertEqual(clean["transport_mode"], "proxy")
        self.assertEqual(clean["proxy_url"], "socks5h://127.0.0.1:10808")

        # Reject invalid mode, missing required targets, unsafe chars, bad schemes
        for bad_payload in [
            {"transport_mode": "bgp"},
            {"transport_mode": "iface", "tunnel_iface": ""},
            {"transport_mode": "iface", "tunnel_iface": "wg0;rm -rf /"},
            {"transport_mode": "proxy", "proxy_url": ""},
            {"transport_mode": "proxy", "proxy_url": "ftp://127.0.0.1:21"},
            {"transport_mode": "proxy", "proxy_url": "socks5h://127.0.0.1:10808;id"},
            {"transport_mode": "mirror", "mirror_url": "javascript:alert(1)"},
            {"transport_mode": "mirror", "mirror_url": "https://ghproxy.net/$(id)"},
        ]:
            ok_bad, _, _ = validate_update_transport_config(bad_payload, require_target=True)
            self.assertFalse(ok_bad, f"Expected validation failure for {bad_payload}")

        # Schema migration normalizes missing or corrupted system_update safely
        cfg = {"schema_version": 3, "system_update": {"transport_mode": "invalid", "proxy_url": "socks5h://127.0.0.1:10808;bad"}, "rules": []}
        norm_cfg, modified = migrate_and_normalize_config(cfg)
        self.assertTrue(modified)
        self.assertEqual(norm_cfg["system_update"]["transport_mode"], "auto")
        self.assertEqual(norm_cfg["system_update"]["proxy_url"], "")

        # Mirror URL helpers
        self.assertEqual(
            build_mirror_git_url("https://ghproxy.net/"),
            "https://ghproxy.net/https://github.com/PouryaDe/XForwarder.git",
        )
        self.assertEqual(
            build_mirror_api_url("https://ghproxy.net"),
            "https://ghproxy.net/https://api.github.com/repos/PouryaDe/XForwarder/commits/main",
        )

    def test_discover_local_proxies_and_exclude_relay_ports(self):
        # Start a local mock SOCKS5 server on an ephemeral port
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        proxy_port = srv.getsockname()[1]

        # Also start a second listener representing a relay port (to verify exclusion)
        relay_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        relay_srv.bind(("127.0.0.1", 0))
        relay_srv.listen(5)
        relay_port = relay_srv.getsockname()[1]

        stop_flag = threading.Event()

        def _serve_socks():
            srv.settimeout(0.2)
            while not stop_flag.is_set():
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    greet = conn.recv(16)
                    if greet.startswith(b"\x05"):
                        conn.sendall(b"\x05\x00")
                        req = conn.recv(256)
                        if len(req) >= 4 and req[0] == 5 and req[1] == 1:
                            conn.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x01\xbb")

        th = threading.Thread(target=_serve_socks, daemon=True)
        th.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tcp4 = os.path.join(tmpdir, "tcp")
                tcp6 = os.path.join(tmpdir, "tcp6")
                with open(tcp4, "w", encoding="utf-8") as f:
                    f.write("  sl  local_address rem_address   st\n")
                    f.write(f"   0: 0100007F:{proxy_port:04X} 00000000:0000 0A\n")
                    f.write(f"   1: 0100007F:{relay_port:04X} 00000000:0000 0A\n")
                    f.write("   2: 0100007F:1F9A 00000000:0000 0A\n")  # 8090 web port
                with open(tcp6, "w", encoding="utf-8") as f:
                    f.write("  sl  local_address rem_address   st\n")

                fake_cfg = {
                    "web": {"port": 8090},
                    "rules": [{"id": "rule-relay", "port": relay_port, "destinations": []}],
                }
                found = discover_local_proxies(config=fake_cfg, proc_tcp_paths=(tcp4, tcp6))
                urls = [p["url"] for p in found]
                self.assertIn(f"socks5h://127.0.0.1:{proxy_port}", urls)
                self.assertNotIn(f"socks5h://127.0.0.1:{relay_port}", urls)
                self.assertNotIn("http://127.0.0.1:8090", urls)

                # Verify RFC 1928 SOCKS5 CONNECT handshake helper end-to-end
                s = _open_socks5_socket("127.0.0.1", proxy_port, "api.github.com", 443, timeout=2.0)
                s.close()
        finally:
            stop_flag.set()
            srv.close()
            relay_srv.close()

    def test_auto_mode_remote_version_fallback_to_tunnel_or_proxy(self):
        invalidate_remote_version_cache()
        fake_cfg = {
            "schema_version": 3,
            "web": {"port": 8090},
            "system_update": {"transport_mode": "auto", "tunnel_iface": "", "proxy_url": "", "mirror_url": ""},
            "rules": [],
        }
        fake_disc = {
            "ok": True,
            "config": fake_cfg["system_update"],
            "tunnels": [{"name": "wg0", "type": "WireGuard Tunnel", "state": "UP", "ip": "10.0.0.1", "peer_ip": "10.0.0.2", "usable": True, "reachable": True, "latency_ms": 40.0}],
            "local_proxies": [{"url": "socks5h://127.0.0.1:10808", "port": 10808, "proto": "socks5h", "label": "SOCKS5 Local (127.0.0.1:10808)", "verified": True}],
        }
        calls = []

        def _fake_fetch(mode, tunnel_iface="", proxy_url="", mirror_url="", timeout=4.0):
            calls.append((mode, tunnel_iface, proxy_url, mirror_url))
            if mode == "direct":
                return False, {}, "Timed out"
            if mode == "proxy" and proxy_url == "socks5h://127.0.0.1:10808":
                return False, {}, "Proxy offline"
            if mode == "iface" and tunnel_iface == "wg0":
                return True, {
                    "remote_commit": "abc9876",
                    "remote_commit_msg": "Via tunnel",
                    "remote_date": "2026-11-24",
                    "repo_url": "https://github.com/PouryaDe/XForwarder",
                }, None
            return False, {}, "Unsupported"

        with patch("core.config_manager.load_config", return_value=fake_cfg), \
             patch("core.service_manager.discover_update_transports", return_value=fake_disc), \
             patch("core.service_manager._fetch_github_commit_single", side_effect=_fake_fetch):
            res = get_remote_version_info(force=True)

        self.assertEqual(res["remote_commit"], "abc9876")
        self.assertIsNone(res["error"])
        self.assertEqual(res["used_transport"]["mode"], "iface")
        self.assertEqual(res["used_transport"]["target"], "wg0")
        self.assertEqual([c[0] for c in calls], ["direct", "proxy", "iface"])

    def test_update_transports_endpoints_and_security(self):
        cfg_orig = load_config()
        orig_su = dict(cfg_orig.get("system_update") or {})
        secret = str(cfg_orig.get("web", {}).get("secret_path", "")).strip().strip("/")
        secret_prefix = f"/{secret}" if secret else ""
        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        threading.Thread(target=server.serve_forever, daemon=True).start()

        token = "test_update_transports_tok"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[token] = {
                "username": "admin",
                "created_at": 9999999999.0,
                "last_active": 9999999999.0,
                "expires_at": 9999999999.0,
            }

        try:
            # Unauth GET -> 401
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{secret_prefix}/api/system/update/transports", timeout=3.0)
            self.assertEqual(ctx.exception.code, 401)

            # Auth GET -> 200
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update/transports",
                headers={"Cookie": f"xfwd_session={token}"}
            )
            with patch("core.web_server.discover_update_transports", return_value={
                "ok": True,
                "config": {"transport_mode": "auto", "tunnel_iface": "", "proxy_url": "", "mirror_url": ""},
                "tunnels": [{"name": "awg0", "type": "AmneziaWG Tunnel", "state": "UP", "usable": True}],
                "local_proxies": [],
            }):
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    self.assertEqual(resp.status, 200)
                    body = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(body["ok"])
                    self.assertEqual(body["tunnels"][0]["name"], "awg0")

            # Invalid Origin POST -> 403
            bad_csrf = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update/transports",
                data=json.dumps({"transport_mode": "iface", "tunnel_iface": "awg0"}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": "https://evil.example",
                }
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx_csrf:
                urllib.request.urlopen(bad_csrf, timeout=3.0)
            self.assertEqual(ctx_csrf.exception.code, 403)

            # Malicious iface POST -> 400
            bad_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update/transports",
                data=json.dumps({"transport_mode": "iface", "tunnel_iface": "wg0;id"}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}",
                }
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx_400:
                urllib.request.urlopen(bad_req, timeout=3.0)
            self.assertEqual(ctx_400.exception.code, 400)

            # Valid POST saves transport safely
            good_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update/transports",
                data=json.dumps({"transport_mode": "iface", "tunnel_iface": "awg0", "test": False}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}",
                }
            )
            with urllib.request.urlopen(good_req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body["system_update"]["tunnel_iface"], "awg0")
        finally:
            cfg_restore = load_config()
            cfg_restore["system_update"] = orig_su or {"transport_mode": "auto", "tunnel_iface": "", "proxy_url": "", "mirror_url": ""}
            save_config(cfg_restore)
            invalidate_remote_version_cache()
            with SESSION_LOCK:
                ACTIVE_SESSIONS.pop(token, None)
            with _UPDATE_LOCK:
                _UPDATE_STATE["status"] = "idle"
                _UPDATE_STATE["start_time"] = 0.0
            server.shutdown()
            server.server_close()

    def test_xforwarder_sh_tty_guard_and_update_helpers(self):
        sh_path = os.path.join(BASE_DIR, "xforwarder.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh = f.read()
        self.assertIn('(exec < /dev/tty) 2>/dev/null', sh)
        self.assertNotIn('exec < /dev/tty 2>/dev/null || true', sh)
        self.assertIn("xfwd_fetch_repo_with_fallback", sh)
        self.assertIn("GIT_HTTP_LOW_SPEED_TIME=12", sh)
        self.assertIn("_xfwd_cleanup_temp_routes", sh)
        with open(os.path.join(BASE_DIR, "core", "service_manager.py"), "r", encoding="utf-8") as smf:
            self.assertIn("NONINTERACTIVE=1", smf.read())


if __name__ == "__main__":
    unittest.main()

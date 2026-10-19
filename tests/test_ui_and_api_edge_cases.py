#!/usr/bin/env python3
"""
Unit tests for XForwarder UI, API Edge Cases, and Multi-Priority Validation.
Covers rule destination cascades, SSL fallback, boundary sanitization, and static asset integrity.
Standard Library unittest only.
"""

import os
import sys
import unittest
import tempfile
import json
import re
import time
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.web_server import (
    validate_rule,
    is_valid_target,
    XForwarderWebServer,
    load_config,
    get_services_status,
    XForwarderWebHandler,
    ACTIVE_SESSIONS,
    SESSION_LOCK
)
from core.engine import XForwarderEngine


class TestUIAndAPIEdgeCases(unittest.TestCase):

    def test_validate_rule_arbitrary_priorities(self):
        """Verifies that validate_rule accepts arbitrary cascading priorities (P1..PN)."""
        rule = {
            "port": 9000,
            "protocol": "both",
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 9000},
                {"priority": 2, "type": "nftables", "target": "10.0.0.2", "port": 9000},
                {"priority": 3, "type": "nginx", "target": "10.0.0.3", "port": 9000},
                {"priority": 4, "type": "haproxy", "target": "2001:db8::4", "port": 9000}
            ]
        }
        valid, msg = validate_rule(rule)
        self.assertTrue(valid, f"Expected valid rule, got: {msg}")
        self.assertEqual(len(rule["destinations"]), 4)

    def test_validate_rule_empty_destinations_rejected(self):
        """Verifies that a rule without destinations is rejected."""
        rule = {"port": 8080, "protocol": "tcp", "destinations": []}
        valid, msg = validate_rule(rule)
        self.assertFalse(valid)
        self.assertIn("destination", msg.lower())

    def test_validate_rule_port_boundary_conditions(self):
        """Tests port bounds (1 to 65535)."""
        # Port 0
        valid, _ = validate_rule({"port": 0, "protocol": "tcp", "destinations": [{"target": "1.1.1.1"}]})
        self.assertFalse(valid)

        # Port 65536
        valid, _ = validate_rule({"port": 65536, "protocol": "tcp", "destinations": [{"target": "1.1.1.1"}]})
        self.assertFalse(valid)

        # Negative port
        valid, _ = validate_rule({"port": -1, "protocol": "tcp", "destinations": [{"target": "1.1.1.1"}]})
        self.assertFalse(valid)

        # Valid boundary min
        valid, _ = validate_rule({"port": 1, "protocol": "tcp", "destinations": [{"target": "1.1.1.1"}]})
        self.assertTrue(valid)

        # Valid boundary max
        valid, _ = validate_rule({"port": 65535, "protocol": "tcp", "destinations": [{"target": "1.1.1.1"}]})
        self.assertTrue(valid)

    def test_validate_rule_destination_defaults_port_if_missing(self):
        """Verifies destination inherits rule listening port when omitted."""
        rule = {
            "port": 4444,
            "protocol": "udp",
            "destinations": [{"priority": 1, "type": "haproxy", "target": "192.168.1.50"}]
        }
        valid, _ = validate_rule(rule)
        self.assertTrue(valid)
        self.assertEqual(rule["destinations"][0]["port"], 4444)

    def test_validate_rule_invalid_characters_rejected(self):
        """Prevents shell command injection characters in destination target."""
        hazards = [
            "1.2.3.4; rm -rf /",
            "1.2.3.4 && cat /etc/passwd",
            "1.2.3.4 | nc evil 1337",
            "1.2.3.4`reboot`",
            "1.2.3.4$(whoami)"
        ]
        for hazard in hazards:
            rule = {"port": 1234, "protocol": "tcp", "destinations": [{"target": hazard}]}
            valid, msg = validate_rule(rule)
            self.assertFalse(valid, f"Should reject hazard: {hazard}")

    def test_ssl_web_server_graceful_fallback(self):
        """Verifies that XForwarderWebServer handles missing SSL certs without crashing."""
        server = XForwarderWebServer(port=18090, bind_host="127.0.0.1")
        # Explicitly set invalid certificate path
        server.ssl_cert = "/tmp/nonexistent_cert_123.crt"
        server.ssl_key = "/tmp/nonexistent_key_123.key"

        # Web server start logic should catch the FileNotFoundError and stay running as HTTP
        self.assertFalse(server.is_ssl)

    def test_static_assets_integrity(self):
        """Verifies that index.html, style.css, and app.js exist and meet architectural standards."""
        web_dir = os.path.join(REPO_ROOT, "web")
        index_path = os.path.join(web_dir, "index.html")
        style_path = os.path.join(web_dir, "style.css")
        app_path = os.path.join(web_dir, "app.js")

        self.assertTrue(os.path.exists(index_path), "index.html must exist")
        self.assertTrue(os.path.exists(style_path), "style.css must exist")
        self.assertTrue(os.path.exists(app_path), "app.js must exist")

        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        with open(style_path, "r", encoding="utf-8") as f:
            style_content = f.read()

        with open(app_path, "r", encoding="utf-8") as f:
            app_content = f.read()

        # 1. Check data-theme pre-hydration script in <head>
        self.assertIn('localStorage.getItem("xfwd_theme")', index_content)
        self.assertIn('data-theme', index_content)

        # 2. Check Light & Dark theme definitions in style.css
        self.assertIn('[data-theme="light"]', style_content)
        self.assertIn('[data-theme="dark"]', style_content)

        # 3. Check hidden scrollbar on modal card
        self.assertIn('scrollbar-width: none', style_content)
        self.assertIn('.modal-card::-webkit-scrollbar', style_content)

        # 4. Check select arrow spacing styling
        self.assertIn('select.form-control', style_content)
        self.assertIn('padding-right: 40px', style_content)

        # 5. Verify quick presets was removed from index.html
        self.assertNotIn('presetHaproxyGre', index_content)
        self.assertNotIn('presetNginxTunnel', index_content)

        # 6. Verify critical DOM element IDs exist in index.html
        critical_ids = [
            "rulesContainer",
            "ruleModal",
            "securityModal",
            "confirmModal",
            "statTotalRules",
            "statActiveHaproxy",
            "statActiveNftables",
            "engineStatusBadge",
            "btnOpenAddModal",
            "searchInput",
            "batchOverrideSelect",
            "btnThemeToggle",
            "btnLoginThemeToggle",
            "loginThemeName",
            "loginScreen",
            "logConsole"
        ]
        for cid in critical_ids:
            self.assertIn(f'id="{cid}"', index_content, f"Missing critical DOM ID: {cid}")

        # 7. Verify unified login screen styling and light theme card shadow in style.css
        self.assertIn('.login-top-bar', style_content)
        self.assertIn('.login-logo', style_content)
        self.assertIn('[data-theme="light"] .login-card', style_content)

        # 8. Verify 2-column rules layout and vertical paths stacking
        self.assertIn('grid-template-columns: repeat(2', style_content)
        self.assertIn('.paths-grid', style_content)
        self.assertIn('flex-direction: column', style_content)
        self.assertIn('.rule-test-bar', style_content)
        self.assertIn('.btn-mode-pill', style_content)
        self.assertIn('.btn-path-test', style_content)

        # 9. Verify testing controls and mode switcher in app.js
        with open(os.path.join(REPO_ROOT, "web", "app.js"), "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertIn('Auto Failover', app_content)
        self.assertIn('Force P', app_content)
        self.assertIn('btn-mode-pill', app_content)
        self.assertIn('btn-path-test', app_content)

    def test_services_status_api_and_dom(self):
        """Verifies get_services_status API structure and DOM presence for NFTables, HAProxy, and Nginx."""
        services = get_services_status()
        self.assertIsInstance(services, dict)
        for svc in ("nftables", "haproxy", "nginx"):
            self.assertIn(svc, services)
            item = services[svc]
            self.assertIn("installed", item)
            self.assertIn("active", item)
            self.assertIn("version", item)
            self.assertIn("details", item)
            self.assertIsInstance(item["installed"], bool)
            self.assertIsInstance(item["active"], bool)

        web_dir = os.path.join(REPO_ROOT, "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            index_content = f.read()
        with open(os.path.join(web_dir, "app.js"), "r", encoding="utf-8") as f:
            app_content = f.read()
        with open(os.path.join(web_dir, "style.css"), "r", encoding="utf-8") as f:
            style_content = f.read()

        # Check DOM element IDs
        for expected_id in (
            "servicesStatusBar",
            "svcPillNft", "svcValNft", "svcDotNft",
            "svcPillHaproxy", "svcValHaproxy", "svcDotHaproxy",
            "svcPillNginx", "svcValNginx", "svcDotNginx",
            "servicesWarningBanner",
            "badgeHaproxyStatus", "badgeNftablesStatus", "badgeNginxStatus"
        ):
            self.assertIn(f'id="{expected_id}"', index_content, f"Missing services DOM ID: {expected_id}")

        # Check app.js function and services rendering
        self.assertIn("renderServicesStatus", app_content)
        self.assertIn("svcDotNft", app_content)
        self.assertIn("svcDotHaproxy", app_content)
        self.assertIn("svcDotNginx", app_content)

        # Check style.css classes
        self.assertIn(".services-status-bar", style_content)
        self.assertIn(".services-warning-banner", style_content)
        self.assertIn(".svc-pill-dot", style_content)

    def test_ui_proxy_protocol_and_test_target_dom(self):
        """Verifies UI elements for PROXY Protocol toggle and Test Target button exist."""
        web_dir = os.path.join(REPO_ROOT, "web")
        with open(os.path.join(web_dir, "app.js"), "r", encoding="utf-8") as f:
            app_content = f.read()
        with open(os.path.join(web_dir, "style.css"), "r", encoding="utf-8") as f:
            style_content = f.read()

        self.assertIn("dest-proxy-proto", app_content)
        self.assertIn("proxy_protocol", app_content)
        self.assertIn("testModalDestination", app_content)
        self.assertIn("/test-target", app_content)

        self.assertIn(".dest-proxy-proto", style_content)
        self.assertIn(".btn-test-dest", style_content)
        self.assertIn(".test-dest-result", style_content)

    def test_api_test_target_http_endpoint(self):
        """Tests POST /api/test-target endpoint auth, input validation, and successful probing."""
        cfg = load_config()
        secret = str(cfg.get("web", {}).get("secret_path", "")).strip().strip("/")
        secret_prefix = f"/{secret}" if secret else ""

        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        token = "test_target_session_token"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[token] = {
                "username": "admin",
                "created_at": time.time(),
                "last_active": time.time(),
                "expires_at": time.time() + 3600
            }

        try:
            # 1. Unauthenticated request under secret prefix must return 401
            req_unauth = urllib.request.Request(
                f"http://127.0.0.1:{port}{secret_prefix}/api/test-target",
                data=json.dumps({"target": "127.0.0.1", "port": 80}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req_unauth, timeout=3.0)
                self.fail("Expected 401 HTTPError")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 401)

            # 2. Authenticated request with invalid target syntax must return 400
            req_bad = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/test-target",
                data=json.dumps({"target": "127.0.0.1; rm -rf /", "port": 80}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}"
                }
            )
            try:
                urllib.request.urlopen(req_bad, timeout=3.0)
                self.fail("Expected 400 HTTPError")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 400)

            # 3. Authenticated valid request returns JSON with ok: true
            req_valid = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/test-target",
                data=json.dumps({"target": "127.0.0.1", "port": port}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}"
                }
            )
            with urllib.request.urlopen(req_valid, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(body.get("ok"))
                self.assertTrue(body.get("healthy"))
                self.assertIsNotNone(body.get("latency_ms"))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()

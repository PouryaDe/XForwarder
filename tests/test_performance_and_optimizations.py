#!/usr/bin/env python3
"""
Unit tests for XForwarder Performance Optimizations.
Tests Gzip compression, ETag conditional 304 responses, in-memory static caching,
selective service reloading (HAProxy, NFTables, Nginx), and fast IPC engine wake-up.
Standard Library unittest only.
"""

import os
import sys
import json
import gzip
import time
import io
import tempfile
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.engine import (
    XForwarderEngine,
    PID_FILE_CANDIDATES
)
from core.web_server import (
    XForwarderWebHandler,
    _STATIC_CACHE,
    _STATIC_LOCK,
    _VERSION_CACHE,
    _SERVICES_CACHE,
    _SERVICES_LOCK,
    notify_engine_wakeup,
    get_services_status
)


class DummyHandler(XForwarderWebHandler):
    """Subclass of XForwarderWebHandler with mocked network I/O for unit testing."""

    def __init__(self, headers=None):
        self.headers = headers or {}
        self.wfile = io.BytesIO()
        self.client_address = ("127.0.0.1", 54321)
        self.status_code = None
        self.response_headers = {}
        self.headers_ended = False

    def send_response(self, code, message=None):
        self.status_code = code

    def send_header(self, keyword, value):
        self.response_headers[keyword] = value

    def end_headers(self):
        self.headers_ended = True

    def send_error(self, code, message=None, explain=None):
        self.status_code = code


class TestPerformanceAndOptimizations(unittest.TestCase):

    def setUp(self):
        with _STATIC_LOCK:
            _STATIC_CACHE.clear()
        with _SERVICES_LOCK:
            _SERVICES_CACHE["data"] = None
            _SERVICES_CACHE["expires"] = 0
        _VERSION_CACHE.clear()

    def tearDown(self):
        with _STATIC_LOCK:
            _STATIC_CACHE.clear()
        with _SERVICES_LOCK:
            _SERVICES_CACHE["data"] = None
            _SERVICES_CACHE["expires"] = 0
        _VERSION_CACHE.clear()

    def test_send_json_gzip_compression_for_large_payload(self):
        """Verifies large JSON responses are gzipped when Accept-Encoding contains gzip."""
        handler = DummyHandler(headers={"Accept-Encoding": "gzip, deflate, br"})
        large_data = {"rules": [{"id": f"rule-{i}", "port": 1000 + i, "target": "10.0.0.1"} for i in range(50)]}

        handler.send_json(large_data)

        self.assertEqual(handler.status_code, 200)
        self.assertEqual(handler.response_headers.get("Content-Type"), "application/json; charset=utf-8")
        self.assertEqual(handler.response_headers.get("Content-Encoding"), "gzip")

        raw_output = handler.wfile.getvalue()
        self.assertEqual(len(raw_output), int(handler.response_headers.get("Content-Length")))

        decompressed = gzip.decompress(raw_output)
        decoded = json.loads(decompressed.decode("utf-8"))
        self.assertEqual(len(decoded["rules"]), 50)
        self.assertEqual(decoded["rules"][0]["id"], "rule-0")

    def test_send_json_no_gzip_for_small_payload(self):
        """Verifies small JSON payloads (<512 bytes) skip gzip overhead even if requested."""
        handler = DummyHandler(headers={"Accept-Encoding": "gzip, deflate"})
        small_data = {"ok": True, "message": "all good"}

        handler.send_json(small_data)

        self.assertEqual(handler.status_code, 200)
        self.assertNotIn("Content-Encoding", handler.response_headers)

        raw_output = handler.wfile.getvalue()
        decoded = json.loads(raw_output.decode("utf-8"))
        self.assertTrue(decoded["ok"])

    def test_send_json_no_gzip_when_unsupported_by_client(self):
        """Verifies gzip is not used if client does not send Accept-Encoding: gzip."""
        handler = DummyHandler(headers={"Accept-Encoding": "deflate"})
        large_data = {"data": "X" * 2000}

        handler.send_json(large_data)

        self.assertEqual(handler.status_code, 200)
        self.assertNotIn("Content-Encoding", handler.response_headers)
        raw_output = handler.wfile.getvalue()
        decoded = json.loads(raw_output.decode("utf-8"))
        self.assertEqual(len(decoded["data"]), 2000)

    def test_send_file_with_etag_and_gzip(self):
        """Verifies static file delivery includes ETag and gzipped content for large assets."""
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            tf.write("/* CSS Mock file */\n" + (".rule-card { color: red; }\n" * 50))
            tf_path = tf.name

        try:
            handler = DummyHandler(headers={"Accept-Encoding": "gzip"})
            handler.send_file(tf_path, "text/css")

            self.assertEqual(handler.status_code, 200)
            self.assertEqual(handler.response_headers.get("Content-Type"), "text/css")
            self.assertEqual(handler.response_headers.get("Content-Encoding"), "gzip")
            self.assertIn("ETag", handler.response_headers)
            self.assertIn("Cache-Control", handler.response_headers)

            # Decompressed body matches file
            raw_output = handler.wfile.getvalue()
            decompressed = gzip.decompress(raw_output).decode("utf-8")
            self.assertIn(".rule-card", decompressed)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_send_file_conditional_304_not_modified(self):
        """Verifies HTTP 304 Not Modified is returned with 0-byte body when If-None-Match matches."""
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            tf.write("console.log('XForwarder JS test');")
            tf_path = tf.name

        try:
            stat = os.stat(tf_path)
            expected_etag = f'W/"{int(stat.st_mtime)}-{stat.st_size}"'

            handler = DummyHandler(headers={"If-None-Match": expected_etag})
            handler.send_file(tf_path, "application/javascript")

            self.assertEqual(handler.status_code, 304)
            self.assertEqual(handler.response_headers.get("ETag"), expected_etag)
            # Body must be 0 bytes for 304 Not Modified
            self.assertEqual(len(handler.wfile.getvalue()), 0)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_send_file_mismatched_etag_returns_200(self):
        """Verifies HTTP 200 OK is returned when If-None-Match does not match."""
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            tf.write("console.log('updated content');")
            tf_path = tf.name

        try:
            handler = DummyHandler(headers={"If-None-Match": 'W/"123-456"'})
            handler.send_file(tf_path, "application/javascript")

            self.assertEqual(handler.status_code, 200)
            self.assertGreater(len(handler.wfile.getvalue()), 0)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_static_cache_invalidation_on_mtime_change(self):
        """Verifies _STATIC_CACHE caches assets and invalidates when file mtime changes."""
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            tf.write("initial content")
            tf_path = tf.name

        try:
            # First request caches content
            h1 = DummyHandler()
            h1.send_file(tf_path, "text/plain")
            self.assertEqual(h1.wfile.getvalue().decode("utf-8"), "initial content")

            with _STATIC_LOCK:
                self.assertIn(tf_path, _STATIC_CACHE)

            # Second request uses cache
            h2 = DummyHandler()
            h2.send_file(tf_path, "text/plain")
            self.assertEqual(h2.wfile.getvalue().decode("utf-8"), "initial content")

            # Modify file content and advance mtime
            time.sleep(1.05)
            with open(tf_path, "w", encoding="utf-8") as f:
                f.write("modified new content")

            h3 = DummyHandler()
            h3.send_file(tf_path, "text/plain")
            self.assertEqual(h3.wfile.getvalue().decode("utf-8"), "modified new content")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_binary_version_cache(self):
        """Verifies get_services_status caches parsed versions in _VERSION_CACHE to avoid subprocess calls."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.side_effect = lambda cmd: "/usr/sbin/haproxy" if cmd == "haproxy" else None
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "HAProxy version 2.8.3 2023/09/08"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            s1 = get_services_status()
            self.assertIn("haproxy", _VERSION_CACHE)

            # Invalidate services cache data so function runs logic, but _VERSION_CACHE remains
            with _SERVICES_LOCK:
                _SERVICES_CACHE["data"] = None
                _SERVICES_CACHE["expires"] = 0

            mock_run.reset_mock()
            s2 = get_services_status()
            # On second run, _VERSION_CACHE is used, so version check subprocess for haproxy (-v) is skipped
            version_calls = [call for call in mock_run.call_args_list if "-v" in call[0][0] or "--version" in call[0][0]]
            self.assertEqual(len(version_calls), 0)

    def test_engine_pid_file_lifecycle(self):
        """Verifies engine writes PID file on startup and cleans it up on stop."""
        engine = XForwarderEngine()
        engine._write_pid_file()

        self.assertIsNotNone(engine._pid_path)
        self.assertTrue(os.path.exists(engine._pid_path))

        with open(engine._pid_path, "r", encoding="utf-8") as pf:
            saved_pid = int(pf.read().strip())
        self.assertEqual(saved_pid, os.getpid())

        engine._remove_pid_file()
        self.assertIsNone(engine._pid_path)

    def test_notify_engine_wakeup_graceful_handling(self):
        """Verifies notify_engine_wakeup handles missing PID files or OS signals gracefully."""
        # When no pid file exists
        notify_engine_wakeup()

        # When pid file exists with dummy pid
        test_pid_file = os.path.join(tempfile.gettempdir(), "xforwarder_engine.pid")
        try:
            with open(test_pid_file, "w", encoding="utf-8") as f:
                f.write("999999")  # Unlikely PID
            with patch("os.kill") as mock_kill:
                notify_engine_wakeup()
                if hasattr(os, "kill"):
                    # On POSIX it attempts to send signal; on Windows it handles cleanly
                    pass
        finally:
            if os.path.exists(test_pid_file):
                os.remove(test_pid_file)

    def test_selective_service_reload_haproxy(self):
        """Verifies _apply_haproxy skips systemctl reload when configuration on disk is identical."""
        engine = XForwarderEngine()

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_haproxy_conf = tf.name

        try:
            with patch("core.engine.HAPROXY_CONF_PATH", test_haproxy_conf), \
                 patch("shutil.which", return_value="/usr/sbin/haproxy"), \
                 patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(return_value=0, returncode=0)

                # First apply writes file and reloads
                ok1, err1 = engine._apply_haproxy(["listen test_p1\n    bind *:8080\n    server s1 10.0.0.1:8080"])
                self.assertTrue(ok1)
                first_run_calls = mock_run.call_count

                # Second apply with identical entries skips write and reload
                ok2, err2 = engine._apply_haproxy(["listen test_p1\n    bind *:8080\n    server s1 10.0.0.1:8080"])
                self.assertTrue(ok2)
                second_run_calls = mock_run.call_count

                self.assertEqual(first_run_calls, second_run_calls)
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_selective_service_reload_nftables(self):
        """Verifies _apply_nftables skips execution when ruleset content is unchanged."""
        engine = XForwarderEngine()

        with patch("shutil.which", return_value="/usr/sbin/nft"), \
             patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen:
            mock_run.return_value = MagicMock(returncode=0)
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            dnat_rules = ['        iifname "eth0" tcp dport 443 dnat to 10.0.0.2:443']

            # First apply validates and executes
            ok1, err1 = engine._apply_nftables(dnat_rules)
            self.assertTrue(ok1)
            first_popen_calls = mock_popen.call_count

            # Second apply with exact same content skips execution
            ok2, err2 = engine._apply_nftables(dnat_rules)
            self.assertTrue(ok2)
            second_popen_calls = mock_popen.call_count

            self.assertEqual(first_popen_calls, second_popen_calls)

    def test_selective_service_reload_nginx(self):
        """Verifies _apply_nginx skips reload when configuration on disk is identical."""
        engine = XForwarderEngine()

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_nginx_conf = tf.name

        try:
            with patch("core.engine.NGINX_CONF_PATH", test_nginx_conf), \
                 patch("shutil.which", return_value="/usr/sbin/nginx"), \
                 patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(return_value=0, returncode=0)

                nginx_entries = ["    server { listen 9090; proxy_pass 10.0.0.1:9090; }"]

                # First apply writes and reloads
                ok1, err1 = engine._apply_nginx(nginx_entries)
                self.assertTrue(ok1)
                first_calls = mock_run.call_count

                # Second apply with identical configuration skips reload
                ok2, err2 = engine._apply_nginx(nginx_entries)
                self.assertTrue(ok2)
                second_calls = mock_run.call_count

                self.assertEqual(first_calls, second_calls)
        finally:
            if os.path.exists(test_nginx_conf):
                os.remove(test_nginx_conf)

    def test_engine_wake_event_sets_and_clears(self):
        """Verifies that _wake_event allows instant unblocking of the engine loop."""
        engine = XForwarderEngine()
        self.assertFalse(engine._wake_event.is_set())

        # Trigger wakeup
        engine._wake_event.set()
        self.assertTrue(engine._wake_event.is_set())

        # Wait with timeout returns immediately because event is set
        t0 = time.perf_counter()
        woken = engine._wake_event.wait(timeout=2.0)
        dt = time.perf_counter() - t0

        self.assertTrue(woken)
        self.assertLess(dt, 0.5)

        engine._wake_event.clear()
        self.assertFalse(engine._wake_event.is_set())


    def test_haproxy_performance_options_rendered(self):
        """Verifies option splice-auto, tune.pipesize, clitcpka, and quiet logging are generated."""
        engine = XForwarderEngine()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_haproxy_conf = tf.name

        try:
            with patch("core.engine.HAPROXY_CONF_PATH", test_haproxy_conf), \
                 patch("shutil.which", return_value=None):
                ok, err = engine._apply_haproxy(["listen test_p1\n    bind *:8080\n    server s1 10.0.0.1:8080"])
                self.assertTrue(ok)
                with open(test_haproxy_conf, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertIn("option  splice-auto", content)
                self.assertIn("tune.bufsize 65536", content)
                self.assertIn("tune.pipesize 262144", content)
                self.assertIn("option  clitcpka", content)
                self.assertIn("option  srvtcpka", content)
                self.assertIn("log /dev/log local0 notice", content)
                # Ensure verbose tcplog is NOT in defaults
                self.assertNotIn("option  tcplog", content)
                if os.cpu_count() and os.cpu_count() > 1:
                    self.assertIn("nbthread ", content)
                    self.assertIn("cpu-map auto:1/1-", content)
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_haproxy_performance_fallback_on_old_binary(self):
        """Verifies fallback removes splice-auto, pipesize, and multi-thread directives if validation fails."""
        engine = XForwarderEngine()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_haproxy_conf = tf.name

        try:
            # First call fails (e.g. unknown keyword 'splice-auto'), second call (fallback) succeeds
            call_count = [0]
            def mock_run_validator(cmd, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return MagicMock(returncode=1, stderr="parsing [/tmp/test]: unknown keyword 'splice-auto'")
                return MagicMock(returncode=0, stderr="")

            with patch("core.engine.HAPROXY_CONF_PATH", test_haproxy_conf), \
                 patch("shutil.which", return_value="/usr/sbin/haproxy"), \
                 patch("subprocess.run", side_effect=mock_run_validator):
                ok, err = engine._apply_haproxy(["listen test_p1\n    bind *:8080\n    server s1 10.0.0.1:8080"])
                self.assertTrue(ok)
                with open(test_haproxy_conf, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertNotIn("option  splice-auto", content)
                self.assertNotIn("tune.pipesize", content)
                self.assertNotIn("nbthread", content)
                self.assertNotIn("cpu-map", content)
                self.assertIn("listen test_p1", content)
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_haproxy_single_core_omits_nbthread_and_cpumap(self):
        """Edge Case: On 1-core VPS or when os.cpu_count() returns None, nbthread and cpu-map are cleanly omitted."""
        engine = XForwarderEngine()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_haproxy_conf = tf.name

        try:
            with patch("core.engine.HAPROXY_CONF_PATH", test_haproxy_conf), \
                 patch("shutil.which", return_value=None), \
                 patch("os.cpu_count", return_value=1):
                ok, err = engine._apply_haproxy(["listen test_p1\n    bind *:8080\n    server s1 10.0.0.1:8080"])
                self.assertTrue(ok)
                with open(test_haproxy_conf, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertNotIn("nbthread", content)
                self.assertNotIn("cpu-map", content)
                self.assertIn("listen test_p1", content)
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_haproxy_multicore_renders_both_nbthread_and_cpumap(self):
        """Edge Case: On multi-core host (4 cores), both nbthread 4 and cpu-map auto:1/1-4 0-3 are generated."""
        engine = XForwarderEngine()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_haproxy_conf = tf.name

        try:
            with patch("core.engine.HAPROXY_CONF_PATH", test_haproxy_conf), \
                 patch("shutil.which", return_value=None), \
                 patch("os.cpu_count", return_value=4):
                ok, err = engine._apply_haproxy(["listen test_p1\n    bind *:8080\n    server s1 10.0.0.1:8080"])
                self.assertTrue(ok)
                with open(test_haproxy_conf, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertIn("    nbthread 4\n", content)
                self.assertIn("    cpu-map auto:1/1-4 0-3\n", content)
                self.assertIn("listen test_p1", content)
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_nginx_udp_proxy_timeout_rendered(self):
        """Verifies that UDP rules and HAProxy UDP helper set proxy_timeout 60s and 64k buffer."""
        engine = XForwarderEngine()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_nginx_conf = tf.name

        try:
            with patch("core.engine.NGINX_CONF_PATH", test_nginx_conf), \
                 patch("shutil.which", return_value=None):
                entries = [
                    "    # [UDP for HAProxy Port 443]\n    server { listen 443 udp reuseport; proxy_pass [2001:db8::1]:443; proxy_timeout 60s; }"
                ]
                ok, err = engine._apply_nginx(entries)
                self.assertTrue(ok)
                with open(test_nginx_conf, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertIn("proxy_timeout 60s;", content)
                self.assertIn("proxy_buffer_size 64k;", content)
        finally:
            if os.path.exists(test_nginx_conf):
                os.remove(test_nginx_conf)


    def test_haproxy_syntax_validation_real_error_fails(self):
        """Verifies that legitimate syntax errors in HAProxy config fail gracefully without looping."""
        engine = XForwarderEngine()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
            test_haproxy_conf = tf.name

        try:
            with patch("core.engine.HAPROXY_CONF_PATH", test_haproxy_conf), \
                 patch("shutil.which", return_value="/usr/sbin/haproxy"), \
                 patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="parsing [/tmp/test]: bind: invalid port range")):
                ok, err = engine._apply_haproxy(["listen test_p1\n    bind *:999999\n    server s1 10.0.0.1:8080"])
                self.assertFalse(ok)
                self.assertIn("HAProxy syntax:", err)
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_nginx_stream_sync_firewall_udp_and_proxy_protocol(self):
        """Verifies sync_firewall_and_proxies generates proxy_timeout 60s and proxy_protocol for pure UDP rules."""
        engine = XForwarderEngine()
        engine.config = {
            "schema_version": 2,
            "wan_interface": "eth0",
            "rules": [
                {
                    "id": "rule-udp-edge",
                    "port": 50053,
                    "protocol": "udp",
                    "active_priority": 1,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nginx",
                            "target": "10.10.10.10",
                            "port": 50053,
                            "proxy_protocol": True,
                            "comment": "Edge UDP Tunnel"
                        }
                    ]
                }
            ]
        }
        with patch.object(engine, "_is_ipv6_supported", return_value=False), \
             patch.object(engine, "_apply_nftables", return_value=(True, None)), \
             patch.object(engine, "_apply_haproxy", return_value=(True, None)), \
             patch.object(engine, "_apply_nginx") as mock_apply_ngx:
            mock_apply_ngx.return_value = (True, None)
            ok, errors = engine.sync_firewall_and_proxies()
            self.assertTrue(ok)
            self.assertEqual(len(errors), 0)
            mock_apply_ngx.assert_called_once()
            entries = mock_apply_ngx.call_args[0][0]
            self.assertEqual(len(entries), 1)
            self.assertIn("listen 50053 udp reuseport;", entries[0])
            self.assertIn("proxy_timeout 60s;", entries[0])
            self.assertIn("proxy_protocol on;", entries[0])

    def test_nftables_o1_maps_vmaps_syn_mss_and_grouping(self):
        """Verifies O(1) map/vmap generation without `th`/`dnat ip to`, strict raw_prerouting grouping, and syn_mss."""
        from core.firewall import generate_nftables_ruleset

        dnat_rules = [
            '        tcp dport 1000 dnat to 5.199.136.72:1000',
            '        udp dport 1000 dnat to 5.199.136.72:1000',
            '        tcp dport 9102 dnat to 5.199.130.135:9102',
            '        udp dport 9102 dnat to 5.199.130.135:9102',
            # Port-translated rule must remain linear (cannot go into 1:1 map)
            '        tcp dport 443 dnat to 10.88.1.2:8443',
            # Range and exclusion rules must remain linear
            '        tcp dport 20000-20010 dnat to 10.88.1.2',
            '        iifname "eth0" tcp dport != { 22, 443, 1000, 9102, 8090 } dnat to 10.10.1.2',
        ]
        raw_rules = [
            # Stateful DSR relay rules (no notrack, iifname != "eth0")
            '        iifname != "eth0" tcp dport 3001 ip daddr set 185.215.229.193',
            '        iifname != "eth0" tcp dport 3002 ip daddr set 185.215.229.194',
            # Stateless DSR rules (with notrack, iifname "eth0")
            '        iifname "eth0" tcp dport 4001 notrack ip daddr set 10.10.10.2',
            '        iifname "eth0" tcp dport 4002 notrack ip daddr set 10.10.10.3',
        ]
        dsr_mss_rules = [
            '        tcp flags syn ip daddr 5.199.136.72 tcp option maxseg size > 1340 tcp option maxseg size set 1340',
            '        tcp flags syn ip saddr 5.199.136.72 tcp option maxseg size > 1340 tcp option maxseg size set 1340',
        ]
        rs = generate_nftables_ruleset(
            dnat_rules,
            rule_ports={1000, 9102, 443, 3001, 3002, 4001, 4002},
            rule_ranges={"20000-20010"},
            raw_rules=raw_rules,
            dsr_mss_rules=dsr_mss_rules,
            has_untracked=True,
            enable_ipv6=True,
        )

        # Compatibility guard: zero `th` or `dnat ip to` syntax (must work on nftables 0.9.3 / Ubuntu 20.04)
        self.assertNotIn("th dport", rs)
        self.assertNotIn("th sport", rs)
        self.assertNotIn("dnat ip to", rs)

        # Shared O(1) DNAT map for 1000 and 9102 (separate tcp/udp dport lookups)
        self.assertIn("map dnat_map_0", rs)
        self.assertIn("1000 : 5.199.136.72, 9102 : 5.199.130.135", rs)
        self.assertIn("dnat to tcp dport map @dnat_map_0", rs)
        self.assertIn("dnat to udp dport map @dnat_map_0", rs)
        # Port-translated, range, and excluded rules remain linear and excluded comes after specific maps
        self.assertIn("tcp dport 443 dnat to 10.88.1.2:8443", rs)
        self.assertIn("tcp dport 20000-20010 dnat to 10.88.1.2", rs)
        self.assertLess(rs.index("dnat to tcp dport map @dnat_map_0"), rs.index("tcp dport != { 22, 443, 1000, 9102, 8090 }"))

        # Mixed raw_rules: MUST NOT prepend `iifname "eth0" accept` because stateless DSR uses `iifname "eth0"`
        raw_section = rs.split("chain raw_prerouting {", 1)[1].split("}", 1)[0]
        self.assertNotIn('iifname "eth0" accept', raw_section)
        # Separate maps for stateful vs notrack raw rules, and safe @raw_nt_set for notrack
        self.assertIn("map raw_dst_map_0", rs)
        self.assertIn("map raw_dst_map_1", rs)
        self.assertIn("set raw_nt_set_1", rs)
        self.assertIn('iifname "eth0" tcp dport @raw_nt_set_1 notrack', raw_section)
        self.assertIn('iifname "eth0" ip daddr set tcp dport map @raw_dst_map_1', raw_section)
        self.assertIn('iifname != "eth0" ip daddr set tcp dport map @raw_dst_map_0', raw_section)

        # syn_mss subchain & O(1) vmap counters preserving cnt_in_* / cnt_out_*
        self.assertIn("chain syn_mss {", rs)
        self.assertIn("tcp flags & (syn|rst) == syn jump syn_mss", rs)
        self.assertIn("map vmap_in {", rs)
        self.assertIn("map vmap_out {", rs)
        self.assertIn("chain c_in_1000 { counter name cnt_in_1000; }", rs)
        self.assertIn("chain c_out_9102 { counter name cnt_out_9102; }", rs)
        self.assertIn("tcp dport vmap @vmap_in", rs)
        self.assertIn("udp dport vmap @vmap_in", rs)
        self.assertIn("tcp sport vmap @vmap_out", rs)
        self.assertIn("udp sport vmap @vmap_out", rs)
        self.assertIn("tcp dport 20000-20010 counter name cnt_in_20000_20010", rs)

        # Change B: IPv6 table must have ZERO hook chains when no IPv6 rules exist, keeping only counters
        ip6_section = rs.split("table ip6 xfwd_orchestrator {", 1)[1]
        self.assertIn("counter cnt_in_1000 { }", ip6_section)
        self.assertNotIn("chain prerouting", ip6_section)
        self.assertNotIn("chain postrouting", ip6_section)
        self.assertNotIn("chain forward", ip6_section)

    def test_nftables_early_wan_bypass_and_linear_fallback(self):
        """Verifies early WAN accept when all raw/dnat rules use `iifname !=` and linear fallback on nft -c -f failure."""
        import core.firewall as fw

        # 1. Early WAN accept when ALL raw & dnat rules exclude WAN
        rs_bypass = fw.generate_nftables_ruleset(
            ['        iifname != "eth0" tcp dport 1001 dnat to 5.199.136.72:1001'],
            raw_rules=['        iifname != "eth0" tcp dport 1001 ip daddr set 185.215.229.193'],
            rule_ports={1001},
            enable_ipv6=False,
        )
        raw_sec = rs_bypass.split("chain raw_prerouting {", 1)[1].split("}", 1)[0]
        pre_sec = rs_bypass.split("chain prerouting {", 1)[1].split("}", 1)[0]
        self.assertTrue(raw_sec.strip().splitlines()[1].strip() == 'iifname "eth0" accept')
        self.assertTrue(pre_sec.strip().splitlines()[1].strip() == 'iifname "eth0" accept')

        # 2. Linear fallback when `nft -c -f` rejects map/vmap on legacy kernels
        dnat_multi = [
            '        tcp dport 1001 dnat to 10.88.1.2:1001',
            '        tcp dport 1002 dnat to 10.88.1.3:1002',
        ]
        called_inputs = []

        def fake_popen(*args, **kwargs):
            proc = MagicMock()
            def fake_comm(input=None):
                called_inputs.append(input)
                if input and "vmap" in input:
                    proc.returncode = 1
                    return ("", "syntax error, unexpected vmap")
                proc.returncode = 0
                return ("", "")
            proc.communicate.side_effect = fake_comm
            return proc

        orig_flag = fw._NFT_MAPS_SUPPORTED
        try:
            fw._NFT_MAPS_SUPPORTED = None
            with patch("shutil.which", return_value="/usr/sbin/nft"), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)), \
                 patch("subprocess.Popen", side_effect=fake_popen):
                ok, err, new_content = fw.apply_nftables(dnat_multi, rule_ports={1001, 1002})
            self.assertTrue(ok, err)
            self.assertIsNone(err)
            self.assertFalse(fw._NFT_MAPS_SUPPORTED)
            self.assertNotIn("vmap", new_content)
            self.assertIn("tcp dport 1001 dnat to 10.88.1.2:1001", new_content)
            self.assertGreaterEqual(len(called_inputs), 3)
        finally:
            fw._NFT_MAPS_SUPPORTED = orig_flag

    def test_qdisc_fq_flow_limit_and_xforwarder_tuning_flags(self):
        """Verifies startup `ensure_fq_qdisc` helper and xforwarder.sh Change D tuning invariants."""
        from core.firewall import ensure_fq_qdisc

        with patch("core.firewall.sys.platform", "linux"), \
             patch("core.firewall.os.path.isfile", return_value=True), \
             patch("builtins.open", unittest.mock.mock_open(read_data="fq\n")), \
             patch("core.firewall._find_tc_bin", return_value="/sbin/tc"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_tc:
            self.assertTrue(ensure_fq_qdisc("eth0", flow_limit=1000))
            mock_tc.assert_called_once_with(
                ["/sbin/tc", "qdisc", "replace", "dev", "eth0", "root", "fq", "flow_limit", "1000"],
                stdout=-3,
                stderr=-3,
                timeout=2.0,
                check=False,
            )

        # Invalid interface name is rejected cleanly
        self.assertFalse(ensure_fq_qdisc("eth0; rm -rf /", flow_limit=1000))

        # Verify xforwarder.sh enforces gro off + udp tnl off + fq flow_limit 1000 + NAPI/conntrack values
        sh_path = os.path.join(REPO_ROOT, "xforwarder.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_text = f.read()
        self.assertIn("ethtool -K \"$def_iface\" tso on gso on gro off", sh_text)
        self.assertIn("tx-udp_tnl-segmentation off tx-udp_tnl-csum-segmentation off", sh_text)
        self.assertIn("tc qdisc replace dev \"$def_iface\" root fq flow_limit 1000", sh_text)
        self.assertIn("net.core.netdev_max_backlog = 100000", sh_text)
        self.assertIn("net.core.netdev_budget=1200", sh_text)
        self.assertIn("net.core.netdev_budget_usecs=8000", sh_text)
        self.assertIn("net.core.dev_weight=128", sh_text)
        self.assertIn("net.netfilter.nf_conntrack_tcp_timeout_established = 3600", sh_text)
        self.assertIn("net.netfilter.nf_conntrack_udp_timeout = 30", sh_text)
        self.assertIn("net.netfilter.nf_conntrack_udp_timeout_stream = 60", sh_text)

    def test_nftables_optimization_edge_cases_and_ipv6_multiport(self):
        """Verifies IPv6 multi-port O(1) maps, invalid-port/IP passthrough guards, and ensure_fq_qdisc fallbacks."""
        import core.firewall as fw

        # 1. IPv6 multi-port rules produce IPv6 map (without brackets inside map) + vmap + syn_mss
        rs_v6 = fw.generate_nftables_ruleset(
            [
                '        tcp dport 8443 dnat to [2001:db8::1]:8443',
                '        tcp dport 9443 dnat to [2001:db8::2]:9443',
                # Out-of-range port must never enter map
                '        tcp dport 99999 dnat to [2001:db8::3]:99999',
            ],
            rule_ports={8443, 9443},
            dsr_mss_rules=['        tcp flags syn ip6 daddr 2001:db8::1 tcp option maxseg size > 1340 tcp option maxseg size set 1340'],
            enable_ipv6=True,
        )
        ip6_part = rs_v6.split("table ip6 xfwd_orchestrator {", 1)[1]
        self.assertIn("type inet_service : ipv6_addr", ip6_part)
        self.assertIn("8443 : 2001:db8::1, 9443 : 2001:db8::2", ip6_part)
        self.assertNotIn("99999 :", ip6_part)
        self.assertIn("tcp dport 99999 dnat to [2001:db8::3]:99999", ip6_part)
        self.assertIn("chain syn_mss {", ip6_part)
        self.assertIn("tcp dport vmap @vmap_in", ip6_part)

        # 2. ensure_fq_qdisc skips when default_qdisc is not fq, and falls back to plain `root fq` if flow_limit fails
        with patch("core.firewall.sys.platform", "linux"), \
             patch("core.firewall.os.path.isfile", return_value=True), \
             patch("builtins.open", unittest.mock.mock_open(read_data="fq_codel\n")), \
             patch("core.firewall._find_tc_bin", return_value="/sbin/tc"), \
             patch("subprocess.run") as mock_tc_skip:
            self.assertFalse(fw.ensure_fq_qdisc("eth0", flow_limit=1000))
            mock_tc_skip.assert_not_called()

        with patch("core.firewall.sys.platform", "linux"), \
             patch("core.firewall.os.path.isfile", return_value=True), \
             patch("builtins.open", unittest.mock.mock_open(read_data="fq\n")), \
             patch("core.firewall._find_tc_bin", return_value="/sbin/tc"), \
             patch("subprocess.run", side_effect=[MagicMock(returncode=1), MagicMock(returncode=0)]) as mock_tc_fb:
            self.assertTrue(fw.ensure_fq_qdisc("eth0", flow_limit=1000))
            self.assertEqual(mock_tc_fb.call_count, 2)
            self.assertEqual(
                mock_tc_fb.call_args_list[1][0][0],
                ["/sbin/tc", "qdisc", "replace", "dev", "eth0", "root", "fq"],
            )


if __name__ == "__main__":
    unittest.main()

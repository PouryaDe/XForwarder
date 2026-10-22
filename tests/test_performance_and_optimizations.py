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
        finally:
            if os.path.exists(test_haproxy_conf):
                os.remove(test_haproxy_conf)

    def test_haproxy_performance_fallback_on_old_binary(self):
        """Verifies fallback removes splice-auto and pipesize if validation fails."""
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


if __name__ == "__main__":
    unittest.main()

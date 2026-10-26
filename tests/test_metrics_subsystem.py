#!/usr/bin/env python3
"""
Unit tests for XForwarder Network Quality & Packet Loss Monitoring Subsystem.
Covers 50-probe measurement, deduplicated target discovery across ports,
SQLite persistence, 30-day retention pruning, and Web API endpoints.
Standard Library unittest only.
"""

import os
import sys
import unittest
import tempfile
import time
import json
import sqlite3
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.metrics import (
    sanitize_target_host,
    parse_ping_output,
    get_unique_targets_from_config,
    init_metrics_db,
    record_ping_result,
    prune_old_metrics,
    get_metrics_history,
    measure_packet_loss_50,
    run_scheduled_ping_round,
    LossMonitorScheduler
)
from core.web_server import (
    XForwarderWebHandler,
    ACTIVE_SESSIONS,
    SESSION_LOCK,
    load_config
)


class TestMetricsSubsystem(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_metrics.db")

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            for f in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, f))
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_sanitize_target_host(self):
        """Tests that hostnames and IPv4/IPv6 IPs are sanitized safely."""
        self.assertEqual(sanitize_target_host("  1.1.1.1  "), "1.1.1.1")
        self.assertEqual(sanitize_target_host("[2001:db8::1]"), "2001:db8::1")
        self.assertEqual(sanitize_target_host("relay.example.com"), "relay.example.com")
        self.assertEqual(sanitize_target_host("1.1.1.1; rm -rf /"), "")
        self.assertEqual(sanitize_target_host(""), "")
        # Injection attempts with flags or invalid prefixes
        self.assertEqual(sanitize_target_host("-c 50"), "")
        self.assertEqual(sanitize_target_host("--help"), "")
        self.assertEqual(sanitize_target_host("-I eth0"), "")
        self.assertEqual(sanitize_target_host(".leadingdot.com"), "")
        self.assertEqual(sanitize_target_host("999.999.999.999"), "")

    def test_unique_targets_deduplication_across_ports(self):
        """
        Guarantees that an IP referenced across multiple rules/ports
        is deduplicated so only ONE probe is taken.
        """
        cfg = {
            "rules": [
                {"port": 80, "destinations": [{"target": "10.0.0.1", "port": 80}, {"target": "[2001:db8::1]", "port": 80}]},
                {"port": 443, "destinations": [{"target": "10.0.0.1", "port": 443}, {"target": "[2001:db8::1]", "port": 443}]},
                {"port": 8080, "destinations": [{"target": "10.0.0.1", "port": 8080}, {"target": "192.168.1.1", "port": 8080}]},
                {"port": 8443, "destinations": [{"target": "192.168.1.1", "port": 8443}]}
            ]
        }
        targets = get_unique_targets_from_config(cfg)
        self.assertEqual(targets, ["10.0.0.1", "192.168.1.1", "2001:db8::1"])
        self.assertEqual(len(targets), 3)

    def test_parse_ping_output_linux_format(self):
        """Tests regex parsing of standard Linux iputils ping output."""
        linux_clean = """
PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
--- 1.1.1.1 ping statistics ---
50 packets transmitted, 50 received, 0% packet loss, time 9812ms
rtt min/avg/max/mdev = 12.110/14.520/18.300/0.850 ms
"""
        res = parse_ping_output(linux_clean, returncode=0, sent_default=50)
        self.assertTrue(res["healthy"])
        self.assertEqual(res["packet_loss"], 0.0)
        self.assertEqual(res["packets_sent"], 50)
        self.assertEqual(res["packets_received"], 50)
        self.assertEqual(res["latency_ms"], 14.5)
        self.assertEqual(res["min_lat"], 12.1)
        self.assertEqual(res["max_lat"], 18.3)
        self.assertEqual(res["is_disrupted"], 0)

        # Degraded with partial loss
        linux_degraded = """
--- 1.1.1.1 ping statistics ---
50 packets transmitted, 45 received, 10% packet loss, time 9890ms
rtt min/avg/max/mdev = 20.000/25.400/35.200/2.100 ms
"""
        res_deg = parse_ping_output(linux_degraded, returncode=0, sent_default=50)
        self.assertTrue(res_deg["healthy"])
        self.assertEqual(res_deg["packet_loss"], 10.0)
        self.assertEqual(res_deg["packets_received"], 45)
        self.assertEqual(res_deg["latency_ms"], 25.4)
        self.assertEqual(res_deg["is_disrupted"], 1)

        # 100% loss / unreachable
        linux_down = """
--- 1.1.1.1 ping statistics ---
50 packets transmitted, 0 received, 100% packet loss, time 10020ms
"""
        res_down = parse_ping_output(linux_down, returncode=1, sent_default=50)
        self.assertFalse(res_down["healthy"])
        self.assertEqual(res_down["packet_loss"], 100.0)
        self.assertEqual(res_down["packets_received"], 0)
        self.assertIsNone(res_down["latency_ms"])
        self.assertEqual(res_down["is_disrupted"], 1)

    def test_sqlite_metrics_persistence_and_querying(self):
        """Tests SQLite database initialization, record insertion, and history querying."""
        init_metrics_db(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

        now = time.time()
        # Insert 3 sample probes: 2 clean, 1 disrupted
        record_ping_result("1.1.1.1", {
            "timestamp": now - 3600,
            "latency_ms": 15.0,
            "min_lat": 14.0,
            "max_lat": 16.0,
            "packet_loss": 0.0,
            "packets_sent": 50,
            "packets_received": 50,
            "is_disrupted": 0
        }, db_path=self.db_path)

        record_ping_result("1.1.1.1", {
            "timestamp": now - 1800,
            "latency_ms": 35.0,
            "min_lat": 25.0,
            "max_lat": 50.0,
            "packet_loss": 12.0,
            "packets_sent": 50,
            "packets_received": 44,
            "is_disrupted": 1,
            "error": "Packet loss detected"
        }, db_path=self.db_path)

        record_ping_result("2001:db8::1", {
            "timestamp": now - 600,
            "latency_ms": 22.0,
            "min_lat": 20.0,
            "max_lat": 24.0,
            "packet_loss": 0.0,
            "packets_sent": 50,
            "packets_received": 50,
            "is_disrupted": 0
        }, db_path=self.db_path)

        # Query all targets
        hist = get_metrics_history(target="all", time_range_hours=24, db_path=self.db_path)
        self.assertEqual(len(hist["targets"]), 2)
        self.assertIn("1.1.1.1", hist["targets"])
        self.assertIn("2001:db8::1", hist["targets"])
        self.assertEqual(hist["summary"]["total_probes"], 3)
        self.assertEqual(hist["summary"]["disrupted_probes"], 1)
        self.assertEqual(len(hist["recent_disruptions"]), 1)
        self.assertEqual(hist["recent_disruptions"][0]["target"], "1.1.1.1")
        self.assertEqual(hist["recent_disruptions"][0]["packet_loss"], 12.0)

        # Query single target filter
        hist_single = get_metrics_history(target="2001:db8::1", time_range_hours=24, db_path=self.db_path)
        self.assertEqual(hist_single["summary"]["total_probes"], 1)
        self.assertEqual(hist_single["summary"]["disrupted_probes"], 0)
        self.assertEqual(len(hist_single["recent_disruptions"]), 0)

    def test_30_day_retention_pruning(self):
        """Tests that records older than 30 days are automatically deleted."""
        init_metrics_db(self.db_path)
        now = time.time()
        old_ts = now - (32 * 86400)  # 32 days ago
        recent_ts = now - (2 * 86400) # 2 days ago

        record_ping_result("1.1.1.1", {
            "timestamp": old_ts,
            "latency_ms": 10.0,
            "packet_loss": 0.0,
            "packets_sent": 50,
            "packets_received": 50,
            "is_disrupted": 0
        }, db_path=self.db_path)

        record_ping_result("1.1.1.1", {
            "timestamp": recent_ts,
            "latency_ms": 11.0,
            "packet_loss": 0.0,
            "packets_sent": 50,
            "packets_received": 50,
            "is_disrupted": 0
        }, db_path=self.db_path)

        # Prune with 30-day cutoff
        pruned_count = prune_old_metrics(retention_days=30, db_path=self.db_path)
        self.assertEqual(pruned_count, 1)

        # Verify only recent remains
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM ping_history;").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_measure_packet_loss_50_mocked(self):
        """Tests measure_packet_loss_50 execution and output structure."""
        fake_output = """
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
--- 8.8.8.8 ping statistics ---
50 packets transmitted, 50 received, 0% packet loss, time 9800ms
rtt min/avg/max/mdev = 15.1/16.2/19.4/0.6 ms
"""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout=fake_output, stderr="")
            res = measure_packet_loss_50("8.8.8.8", count=50, interval=0.2, save_to_db=True, db_path=self.db_path)

            self.assertTrue(res["healthy"])
            self.assertEqual(res["packet_loss"], 0.0)
            self.assertEqual(res["latency_ms"], 16.2)
            self.assertEqual(res["packets_sent"], 50)
            self.assertEqual(res["packets_received"], 50)
            self.assertEqual(res["is_disrupted"], 0)

            # Check that command sent -c 50 and -i 0.2
            called_cmd = mock_sub.call_args[0][0]
            if sys.platform != "win32":
                self.assertIn("-c", called_cmd)
                self.assertIn("50", called_cmd)
                self.assertIn("-i", called_cmd)
                self.assertIn("0.2", called_cmd)

    def test_measure_packet_loss_iface_sanitization_and_bounds(self):
        """Tests that dangerous interface flags are rejected and bounds enforced."""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="50 packets transmitted, 50 received, 0% packet loss\nrtt min/avg/max = 10/12/15 ms", stderr="")

            # Dangerous iface starting with dash
            measure_packet_loss_50("1.1.1.1", iface="-c 100", count=500, save_to_db=False)
            called_cmd = mock_sub.call_args[0][0]
            # Must NOT contain -I
            self.assertNotIn("-I", called_cmd)
            # Count must be capped at 200
            if sys.platform != "win32":
                idx = called_cmd.index("-c")
                self.assertEqual(called_cmd[idx + 1], "200")
            else:
                idx = called_cmd.index("-n")
                self.assertEqual(called_cmd[idx + 1], "200")

            # Safe iface on non-windows
            if sys.platform != "win32":
                measure_packet_loss_50("1.1.1.1", iface="gre1", count=10, save_to_db=False)
                called_cmd2 = mock_sub.call_args[0][0]
                self.assertIn("-I", called_cmd2)
                self.assertIn("gre1", called_cmd2)

    def test_scheduler_lifecycle_and_trigger_now(self):
        """Verifies LossMonitorScheduler runs, trigger_now wakes it without terminating, and stop cleans up."""
        def dummy_loader():
            return {"rules": []}

        scheduler = LossMonitorScheduler(config_loader_fn=dummy_loader, interval_seconds=3600, db_path=self.db_path)
        with patch("core.metrics.run_scheduled_ping_round") as mock_round:
            mock_round.return_value = []
            scheduler.start()
            self.assertIsNotNone(scheduler._thread)
            self.assertTrue(scheduler._thread.is_alive())

            # Trigger an immediate round out of schedule
            scheduler.trigger_now()
            time.sleep(0.1)

            # Thread MUST remain alive (trigger_now must NOT kill the thread)
            self.assertTrue(scheduler._thread.is_alive())

            # Clean shutdown
            scheduler.stop()
            self.assertIsNone(scheduler._thread)

    def test_web_api_test_loss_and_history_endpoints(self):
        """Tests POST /api/test-loss and GET /api/metrics/loss-history over real HTTP."""
        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        token = "test_metrics_session_token"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[token] = {
                "username": "admin",
                "created_at": time.time(),
                "last_active": time.time(),
                "expires_at": time.time() + 3600
            }

        headers = {
            "Content-Type": "application/json",
            "Cookie": f"xfwd_session={token}",
            "Origin": f"http://127.0.0.1:{port}"
        }

        cfg = load_config()
        secret = str(cfg.get("web", {}).get("secret_path", "")).strip().strip("/")
        secret_prefix = f"/{secret}" if secret else ""

        try:
            # 1. Unauthenticated request to /api/test-loss returns 401 under secret prefix
            req_unauth = urllib.request.Request(
                f"http://127.0.0.1:{port}{secret_prefix}/api/test-loss",
                data=json.dumps({"target": "127.0.0.1"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_unauth, timeout=3.0)
            self.assertEqual(ctx.exception.code, 401)

            # 2. Authenticated request with invalid target returns 400
            req_bad = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/test-loss",
                data=json.dumps({"target": "1.1.1.1; rm -rf /"}).encode("utf-8"),
                headers=headers
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_bad, timeout=3.0)
            self.assertEqual(ctx.exception.code, 400)

            # 3. GET /api/metrics/loss-history returns valid JSON structure
            req_hist = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/metrics/loss-history?range=24h",
                headers={"Cookie": f"xfwd_session={token}"}
            )
            with urllib.request.urlopen(req_hist, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(data.get("ok"))
                self.assertIn("summary", data)
                self.assertIn("timeline", data)
                self.assertIn("recent_disruptions", data)

        finally:
            server.shutdown()
            server.server_close()

    def test_scheduler_resilient_to_none_returning_loader_and_bound_self_fallback(self):
        """Verifies LossMonitorScheduler runs even if config_loader_fn returns None initially."""
        class MockEngine:
            def __init__(self):
                self.config = {"rules": [{"port": 80, "destinations": [{"target": "1.1.1.1"}]}]}
            def load_config(self):
                # Returns None like the original engine bug
                return None

        mock_engine = MockEngine()
        scheduler = LossMonitorScheduler(
            config_loader_fn=mock_engine.load_config,
            interval_seconds=3600,
            db_path=self.db_path
        )
        with patch("core.metrics.run_scheduled_ping_round") as mock_round:
            mock_round.return_value = []
            scheduler.start()
            scheduler.trigger_now()
            time.sleep(0.15)
            # Must have called run_scheduled_ping_round via defensive fallback to mock_engine.config
            self.assertTrue(mock_round.called)
            scheduler.stop()

    def test_engine_load_config_returns_dict(self):
        """Verifies that XForwarderEngine.load_config returns the configuration dictionary."""
        from core.engine import XForwarderEngine
        engine = XForwarderEngine()
        loaded = engine.load_config()
        self.assertIsInstance(loaded, dict)
        self.assertIs(loaded, engine.config)

    def test_run_scheduled_ping_round_with_tunnel_iface(self):
        """Verifies run_scheduled_ping_round binds to destination's tunnel_iface if specified."""
        cfg = {
            "rules": [
                {
                    "port": 443,
                    "destinations": [
                        {"priority": 1, "target": "2001:db8::1", "port": 443},
                        {"priority": 2, "target": "10.88.1.2", "tunnel_iface": "gre1", "port": 443}
                    ]
                }
            ]
        }
        with patch("core.metrics.measure_packet_loss_50") as mock_measure, \
             patch("core.metrics.prune_old_metrics"):
            mock_measure.return_value = {"target": "mock", "packet_loss": 0.0}
            run_scheduled_ping_round(cfg, db_path=self.db_path)

            calls = mock_measure.call_args_list
            target_to_iface = {call.kwargs.get("target") or call.args[0]: call.kwargs.get("iface") for call in calls}
            self.assertIn("10.88.1.2", target_to_iface)
            self.assertEqual(target_to_iface["10.88.1.2"], "gre1")
            self.assertIn("2001:db8::1", target_to_iface)
            self.assertIsNone(target_to_iface["2001:db8::1"])


if __name__ == "__main__":
    unittest.main()

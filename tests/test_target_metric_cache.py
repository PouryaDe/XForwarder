#!/usr/bin/env python3
"""
Unit tests for per-IP probe deduplication, 10-ping burst averaging,
and 60-second in-memory target metric caching in XForwarder.

Verifies:
1. When multiple rules (e.g. 5 ports) share the same tunnel IP (e.g. 10.81.8.2),
   the IP is probed only ONCE.
2. The probe uses a 10-ping burst (count=10).
3. Results are cached in memory for 60 seconds, preventing redundant probes.
4. All rules sharing that target receive identical latency, jitter, loss, and composite score.
5. Cache invalidation / re-probing occurs after 60 seconds.
6. NFTables / ICMP destinations probe ICMP directly with 10 packets without TCP port connecting.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.engine import XForwarderEngine
from core.prober import check_destination


class TestTargetMetricCache(unittest.TestCase):
    def setUp(self):
        self.engine = XForwarderEngine(config_path=None)
        self.engine.config = {
            "wan_interface": "eth0",
            "probe_count": 10,
            "target_probe_interval_seconds": 60,
            "quality_window_seconds": 300,
            "rules": []
        }
        self.engine.runtime_state["wan_interface"] = "eth0"

        # Create 5 rules all forwarding over Priority 2 tunnel IP 10.81.8.2
        self.ports = [80, 443, 8080, 8443, 9000]
        self.rules = []
        for p in self.ports:
            self.rules.append({
                "id": f"rule-{p}",
                "port": p,
                "protocol": "tcp",
                "active_priority": 2,
                "destinations": [
                    {
                        "priority": 1,
                        "type": "haproxy",
                        "target": "2001:db8::1",
                        "port": p
                    },
                    {
                        "priority": 2,
                        "type": "nftables",
                        "target": "10.81.8.2",
                        "port": p,
                        "tunnel_iface": "tun_gre0"
                    }
                ]
            })

    @patch("core.engine.prober_probe_destination_icmp")
    @patch("core.engine.XForwarderEngine._validate_probe_route")
    def test_deduplicated_probe_across_multiple_ports(self, mock_validate, mock_probe_icmp):
        # Mock route validation to pass
        mock_validate.return_value = (True, "tun_gre0", None)

        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 82.5,
            "jitter_ms": 1.4,
            "reason": ""
        }

        # Probe all destinations for all 5 rules (10 total destinations across 2 unique IPs)
        cache = self.engine._probe_all_destinations(self.rules)

        # mock_probe_icmp should have been called ONCE per unique IP (2 total), NOT 10 times!
        self.assertEqual(mock_probe_icmp.call_count, 2)
        probed_ips = {call[0][0] for call in mock_probe_icmp.call_args_list}
        self.assertEqual(probed_ips, {"10.81.8.2", "2001:db8::1"})

        # Check cache lookup has identical results
        res1 = cache.get("10.81.8.2")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["latency_ms"], 82.5)

        # Evaluate all 5 rules
        for rule in self.rules:
            self.engine.evaluate_rule(rule, probe_cache=cache)

        # Inspect rules_state in runtime_state
        rules_state = self.engine.runtime_state["rules_state"]
        latencies = []
        scores = []
        losses = []
        for p in self.ports:
            rid = f"rule-{p}"
            self.assertIn(rid, rules_state)
            p2_stat = rules_state[rid]["dest_stats"]["prio_2"]
            latencies.append(p2_stat["latency_ms"])
            scores.append(p2_stat["composite_score"])
            losses.append(p2_stat["packet_loss"])

        # Every single port must have EXACTLY the same latency, score, and loss!
        self.assertEqual(len(set(latencies)), 1, f"Latencies diverged across ports: {latencies}")
        self.assertEqual(len(set(scores)), 1, f"Scores diverged across ports: {scores}")
        self.assertEqual(len(set(losses)), 1, f"Losses diverged across ports: {losses}")
        self.assertEqual(latencies[0], 82.5)

    @patch("core.engine.prober_probe_destination_icmp")
    @patch("core.engine.XForwarderEngine._validate_probe_route")
    def test_60_second_cache_prevents_reprobing(self, mock_validate, mock_probe_icmp):
        mock_validate.return_value = (True, "tun_gre0", None)
        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 80.0,
            "jitter_ms": 1.0,
            "reason": ""
        }

        # First cycle at t = 1000.0 (probes 2 unique IPs)
        with patch("time.time", return_value=1000.0):
            self.engine._probe_all_destinations(self.rules)
        self.assertEqual(mock_probe_icmp.call_count, 2)

        # Second cycle at t = 1030.0 (30 seconds later, < 60s cache interval)
        with patch("time.time", return_value=1030.0):
            cached = self.engine._probe_all_destinations(self.rules)
        # Call count must still be 2! No new ping executed!
        self.assertEqual(mock_probe_icmp.call_count, 2)
        self.assertEqual(cached["10.81.8.2"]["latency_ms"], 80.0)

        # Third cycle at t = 1065.0 (> 60 seconds later, cache expired)
        with patch("time.time", return_value=1065.0):
            self.engine._probe_all_destinations(self.rules)
        # Call count should now be 4 (2 fresh probes)!
        self.assertEqual(mock_probe_icmp.call_count, 4)

    @patch("core.engine.prober_probe_destination_icmp")
    @patch("core.engine.XForwarderEngine._validate_probe_route")
    def test_distinct_ips_probed_once_each(self, mock_validate, mock_probe_icmp):
        mock_validate.return_value = (True, "tun_gre0", None)
        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 75.0,
            "jitter_ms": 1.0,
            "reason": ""
        }

        rules = [
            {"id": "r1", "port": 80, "destinations": [{"priority": 1, "type": "nftables", "target": "10.81.8.2"}]},
            {"id": "r2", "port": 443, "destinations": [{"priority": 1, "type": "nftables", "target": "10.81.8.2"}]},
            {"id": "r3", "port": 8080, "destinations": [{"priority": 1, "type": "nftables", "target": "10.81.8.3"}]},
            {"id": "r4", "port": 8443, "destinations": [{"priority": 1, "type": "nftables", "target": "10.81.8.3"}]},
            {"id": "r5", "port": 9000, "destinations": [{"priority": 1, "type": "nftables", "target": "10.81.8.4"}]},
        ]

        with patch("time.time", return_value=5000.0):
            self.engine._probe_all_destinations(rules)

        # 3 unique IPs -> exactly 3 calls
        self.assertEqual(mock_probe_icmp.call_count, 3)
        probed_ips = {call[0][0] for call in mock_probe_icmp.call_args_list}
        self.assertEqual(probed_ips, {"10.81.8.2", "10.81.8.3", "10.81.8.4"})

    @patch("core.prober.probe_destination_icmp")
    def test_check_destination_routes_nftables_to_icmp_with_10_count(self, mock_probe_icmp):
        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 80.0,
            "jitter_ms": 1.1,
            "reason": ""
        }

        dest = {
            "type": "nftables",
            "target": "10.81.8.2",
            "port": 443,
            "tunnel_iface": "tun0"
        }

        res = check_destination(dest, rule_port=443, count=10)
        self.assertTrue(res["healthy"])
        self.assertEqual(res["latency_ms"], 80.0)
        mock_probe_icmp.assert_called_once_with("10.81.8.2", iface="tun0", count=10, interval_ms=200)

    @patch("core.engine.prober_probe_destination_icmp")
    def test_route_invalidation_immediately_clears_cache(self, mock_probe_icmp):
        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 70.0,
            "jitter_ms": 1.0,
            "reason": ""
        }

        # Step 1: Initial probe when route is valid
        with patch.object(self.engine, "_validate_probe_route", return_value=(True, "tun_gre0", None)):
            res1 = self.engine._probe_all_destinations(self.rules, now=1000.0)
            self.assertTrue(res1["10.81.8.2"]["healthy"])
            self.assertIn("10.81.8.2", self.engine._target_probe_cache)

        # Step 2: Route becomes invalid at t = 1010.0 (e.g. tunnel interface dropped)
        with patch.object(self.engine, "_validate_probe_route", return_value=(False, "tun_gre0", "Interface tun_gre0 is down")):
            res2 = self.engine._probe_all_destinations(self.rules, now=1010.0)
            # Must immediately report failed without returning stale healthy cached ping!
            self.assertFalse(res2["10.81.8.2"]["healthy"])
            self.assertEqual(res2["10.81.8.2"]["packet_loss"], 100.0)
            self.assertNotIn("10.81.8.2", self.engine._target_probe_cache)

    @patch("core.engine.prober_probe_destination_icmp")
    def test_stale_target_eviction_on_rule_removal(self, mock_probe_icmp):
        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 65.0,
            "jitter_ms": 0.8,
            "reason": ""
        }

        rules_with_old_target = [
            {"id": "r1", "port": 80, "destinations": [{"priority": 1, "type": "nftables", "target": "10.99.99.1"}]}
        ]

        with patch.object(self.engine, "_validate_probe_route", return_value=(True, "tun0", None)):
            self.engine._probe_all_destinations(rules_with_old_target, now=1000.0)
            self.assertIn("10.99.99.1", self.engine._target_probe_cache)

            # Now rule is changed/removed and points to a new target
            rules_new = [
                {"id": "r1", "port": 80, "destinations": [{"priority": 1, "type": "nftables", "target": "10.99.99.2"}]}
            ]
            self.engine._probe_all_destinations(rules_new, now=1010.0)

            # Old target must be evicted to prevent memory accumulation in 24/7 daemon
            self.assertNotIn("10.99.99.1", self.engine._target_probe_cache)
            self.assertIn("10.99.99.2", self.engine._target_probe_cache)

    @patch("core.engine.prober_probe_destination_icmp")
    def test_target_casing_normalization(self, mock_probe_icmp):
        mock_probe_icmp.return_value = {
            "healthy": True,
            "packets_sent": 10,
            "packets_received": 10,
            "packet_loss": 0.0,
            "latency_ms": 50.0,
            "jitter_ms": 0.5,
            "reason": ""
        }

        # Rule has uppercase IPv6 target
        rule_upper = {
            "id": "r_upper",
            "port": 443,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:DB8::ABCD", "port": 443}
            ]
        }

        with patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)):
            cache = self.engine._probe_all_destinations([rule_upper], now=2000.0)
            self.engine.evaluate_rule(rule_upper, probe_cache=cache)

            # Must evaluate successfully and find shared history
            rule_stat = self.engine.runtime_state["rules_state"]["r_upper"]["dest_stats"]["prio_1"]
            self.assertEqual(rule_stat["latency_ms"], 50.0)
            self.assertEqual(rule_stat["status"], "healthy")


if __name__ == "__main__":
    unittest.main()

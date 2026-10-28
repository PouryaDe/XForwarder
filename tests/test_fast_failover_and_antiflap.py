#!/usr/bin/env python3
"""
Unit tests for XForwarder Fast Failover, Multi-Metric Scoring, and Anti-Flapping Engine.
Verifies:
1. Adaptive Fast Burst Confirmation (<1s failure detection)
2. Multi-metric sliding-window packet loss and composite scoring
3. Anti-flapping hold-down cooldown and hard failure bypass
4. 10% hysteresis margin preventing marginal jitter switching
5. Flap damping with exponential cooldown extension
6. Asymmetric failback requiring sustained clean health
7. Zero-Collision port isolation across HAProxy, NFTables, and Nginx
8. Nginx dynamic service lifecycle management (stop when 0 rules active)

Standard library unittest only.
"""

import os
import sys
import time
import json
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.engine import XForwarderEngine


class TestFastFailoverAndAntiFlap(unittest.TestCase):
    def setUp(self):
        self.engine = XForwarderEngine(config_path=None)
        self.engine.config = {
            "wan_interface": "eth0",
            "check_interval_seconds": 8,
            "failure_threshold": 3,
            "recovery_threshold": 3,
            "fast_failover_enabled": True,
            "max_acceptable_loss": 25,
            "cooldown_seconds": 60,
            "hysteresis_percent": 10,
            "loss_penalty_weight": 10,
            "fast_probe_burst": 3,
            "rules": []
        }
        self.engine.runtime_state["wan_interface"] = "eth0"
        self.engine.runtime_state["rules_state"] = {}

    def test_config_defaults_and_normalization(self):
        """Verifies that migrate_and_normalize_config sets and clamps all new parameters."""
        raw_cfg = {
            "schema_version": 1,
            "rules": []
        }
        migrated, modified = XForwarderEngine.migrate_and_normalize_config(raw_cfg)
        self.assertTrue(modified)
        self.assertEqual(migrated["schema_version"], 3)
        self.assertTrue(migrated["fast_failover_enabled"])
        self.assertEqual(migrated["max_acceptable_loss"], 25)
        self.assertEqual(migrated["cooldown_seconds"], 60)
        self.assertEqual(migrated["hysteresis_percent"], 20)
        self.assertEqual(migrated["loss_penalty_weight"], 20)
        self.assertEqual(migrated["fast_probe_burst"], 5)

        # Clamping check: out of bound values should clamp cleanly
        bad_cfg = {
            "cooldown_seconds": 9999,
            "hysteresis_percent": -5,
            "max_acceptable_loss": 100
        }
        migrated_clamped, _ = XForwarderEngine.migrate_and_normalize_config(bad_cfg)
        self.assertEqual(migrated_clamped["cooldown_seconds"], 600)  # clamped to max 600
        self.assertEqual(migrated_clamped["hysteresis_percent"], 0)  # clamped to min 0
        self.assertEqual(migrated_clamped["max_acceptable_loss"], 90)  # clamped to max 90

    def test_adaptive_fast_burst_detection(self):
        """Verifies that an active destination outage triggers fast burst confirmation in < 1 second."""
        rule = {
            "id": "rule-443",
            "port": 443,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 443},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 443}
            ]
        }
        self.engine.config["rules"] = [rule]

        # Destination 1 fails regular probe and fails all fast burst probes
        # Destination 2 is healthy
        def mock_check(dest, rule_port=None, protocol=None):
            if dest["priority"] == 1:
                return {"healthy": False, "latency_ms": None, "packet_loss": 100, "reason": "Connection refused"}
            return {"healthy": True, "latency_ms": 35.0, "packet_loss": 0}

        def mock_burst(dest, rule_port=None, protocol=None, count=3):
            return {"all_failed": True, "successes": 0, "packet_loss": 100, "avg_latency_ms": None}

        with patch.object(self.engine, "check_destination", side_effect=mock_check), \
             patch.object(self.engine, "_fast_confirm_burst", side_effect=mock_burst) as burst_mock:

            changed = self.engine.evaluate_rule(rule)
            self.assertTrue(changed)
            burst_mock.assert_called_once()

            # Rule should have failed over immediately to Priority 2
            self.assertEqual(rule["active_priority"], 2)
            rule_st = self.engine.runtime_state["rules_state"]["rule-443"]
            self.assertEqual(rule_st["active_priority"], 2)
            self.assertEqual(rule_st["dest_stats"]["prio_1"]["status"], "failed")
            self.assertEqual(rule_st["dest_stats"]["prio_1"]["packet_loss"], 100)

    def test_multi_metric_composite_scoring_and_loss_penalization(self):
        """Verifies that high packet loss degrades the route and penalizes composite score."""
        rule = {
            "id": "rule-8080",
            "port": 8080,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 8080},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 8080}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.config["cooldown_seconds"] = 0  # no cooldown for this test

        # Simulate 4 checks for Priority 1: 2 drops and 2 successes (50% loss, 40ms latency)
        # Priority 2: 100% success (0% loss, 60ms latency)
        p1_samples = [
            {"healthy": False, "latency_ms": None, "packet_loss": 100},
            {"healthy": True, "latency_ms": 40.0, "packet_loss": 0},
            {"healthy": False, "latency_ms": None, "packet_loss": 100},
            {"healthy": True, "latency_ms": 40.0, "packet_loss": 0}
        ]

        with patch.object(self.engine, "_fast_confirm_burst", return_value={"all_failed": False, "successes": 1}):
            for sample in p1_samples:
                def mock_check(dest, rule_port=None, protocol=None):
                    if dest["priority"] == 1:
                        return dict(sample)
                    return {"healthy": True, "latency_ms": 60.0, "packet_loss": 0}

                with patch.object(self.engine, "check_destination", side_effect=mock_check):
                    self.engine.evaluate_rule(rule)

        rule_st = self.engine.runtime_state["rules_state"]["rule-8080"]
        p1_stat = rule_st["dest_stats"]["prio_1"]
        p2_stat = rule_st["dest_stats"]["prio_2"]

        # P1 has 50% packet loss (2 out of 4 failed)
        self.assertEqual(p1_stat["packet_loss"], 50)
        self.assertIn(p1_stat["status"], ("degraded", "critical"))  # > max_acceptable_loss (25%) / >= 30%
        # Score = 40ms + (50 * 10) = 540.0
        self.assertEqual(p1_stat["composite_score"], 540.0)

        # P2 has 0% loss and 60ms latency -> Score = 60 + 0 = 60.0
        self.assertEqual(p2_stat["packet_loss"], 0)
        self.assertEqual(p2_stat["composite_score"], 60.0)

        # P2 is vastly superior due to 0% loss; rule should switch to P2
        self.assertEqual(rule["active_priority"], 2)

    def test_anti_flapping_cooldown_hold_and_hard_outage_bypass(self):
        """Verifies cooldown prevents route flapping on minor fluctuations, but hard failure bypasses it."""
        rule = {
            "id": "rule-9000",
            "port": 9000,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 9000},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 9000}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.config["cooldown_seconds"] = 60

        # Initial state: rule just switched to P2 10 seconds ago (50s cooldown remaining)
        now = time.time()
        self.engine.runtime_state["rules_state"]["rule-9000"] = {
            "active_priority": 2,
            "last_switch_time": now - 10,
            "dest_stats": {
                "prio_1": {"status": "healthy", "latency_ms": 30.0, "packet_loss": 0, "composite_score": 30.0, "consecutive_success": 5},
                "prio_2": {"status": "healthy", "latency_ms": 40.0, "packet_loss": 0, "composite_score": 40.0, "consecutive_success": 5}
            }
        }
        rule["active_priority"] = 2

        # 1. During cooldown, even if P1 has slightly better ping, hold P2 to prevent flapping!
        def mock_check_both_healthy(dest, rule_port=None, protocol=None):
            if dest["priority"] == 1:
                return {"healthy": True, "latency_ms": 30.0, "packet_loss": 0}
            return {"healthy": True, "latency_ms": 40.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check_both_healthy):
            changed = self.engine.evaluate_rule(rule)
            self.assertFalse(changed)
            # Route must remain on Priority 2 because of active cooldown
            self.assertEqual(rule["active_priority"], 2)
            rule_st = self.engine.runtime_state["rules_state"]["rule-9000"]
            self.assertGreater(rule_st["cooldown_remaining"], 0)

        # 2. Hard Failure Scenario: Priority 2 completely dies (100% loss / failed)
        # Emergency failover must bypass cooldown immediately!
        def mock_check_p2_dead(dest, rule_port=None, protocol=None):
            if dest["priority"] == 1:
                return {"healthy": True, "latency_ms": 30.0, "packet_loss": 0}
            return {"healthy": False, "latency_ms": None, "packet_loss": 100, "reason": "Connection refused"}

        with patch.object(self.engine, "check_destination", side_effect=mock_check_p2_dead), \
             patch.object(self.engine, "_fast_confirm_burst", return_value={"all_failed": True, "successes": 0}):
            changed = self.engine.evaluate_rule(rule)
            self.assertTrue(changed)
            # Must immediately fail over to Priority 1 despite cooldown
            self.assertEqual(rule["active_priority"], 1)

    def test_hysteresis_percent_10_margin(self):
        """Verifies that an alternative route must be at least 10% better to justify switching."""
        rule = {
            "id": "rule-3000",
            "port": 3000,
            "protocol": "tcp",
            "active_priority": 2,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 3000},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 3000}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.config["cooldown_seconds"] = 0  # cooldown expired
        self.engine.config["min_hold_seconds"] = 0
        self.engine.config["switch_confirm_seconds"] = 0
        self.engine.config["hysteresis_percent"] = 10  # 10% threshold

        # Current active is Priority 2 with score = 100.0 (100ms, 0% loss)
        # Priority 1 has score = 96.0 (only 4% better, within jitter range)
        # 10% hysteresis requirement: cand_score must be <= 100 * 0.90 - 10 = 80.0
        self.engine.runtime_state["rules_state"]["rule-3000"] = {
            "active_priority": 2,
            "last_switch_time": 0,
            "dest_stats": {
                "prio_1": {"status": "healthy", "latency_ms": 96.0, "packet_loss": 0, "composite_score": 96.0, "consecutive_success": 1},
                "prio_2": {"status": "healthy", "latency_ms": 100.0, "packet_loss": 0, "composite_score": 100.0, "consecutive_success": 5}
            }
        }
        rule["active_priority"] = 2

        def mock_check_marginal(dest, rule_port=None, protocol=None):
            if dest["priority"] == 1:
                return {"healthy": True, "latency_ms": 96.0, "packet_loss": 0}
            return {"healthy": True, "latency_ms": 100.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check_marginal):
            changed = self.engine.evaluate_rule(rule)
            # Marginal 4% difference must NOT switch!
            self.assertFalse(changed)
            self.assertEqual(rule["active_priority"], 2)

        # Now Priority 1 has score = 75.0 (25% better, passes 10% hysteresis)
        rule_st = self.engine.runtime_state["rules_state"]["rule-3000"]
        rule_st["dest_stats"]["prio_1"]["samples"] = []
        rule_st["dest_stats"]["prio_2"]["samples"] = []

        def mock_check_significant(dest, rule_port=None, protocol=None):
            if dest["priority"] == 1:
                return {"healthy": True, "latency_ms": 75.0, "packet_loss": 0}
            return {"healthy": True, "latency_ms": 100.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check_significant):
            changed = self.engine.evaluate_rule(rule)
            # Substantial advantage (>10%) switches cleanly!
            self.assertTrue(changed)
            self.assertEqual(rule["active_priority"], 1)

    def test_flap_damping_exponential_cooldown(self):
        """Verifies repeated switches within 10 minutes trigger flap damping and double cooldown."""
        rule = {
            "id": "rule-flap",
            "port": 5000,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 5000},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 5000}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.config["cooldown_seconds"] = 30

        now = time.time()
        # Seed 3 switches in the last 5 minutes
        self.engine.runtime_state["rules_state"]["rule-flap"] = {
            "active_priority": 1,
            "last_switch_time": now - 35,
            "switch_history": [now - 200, now - 120, now - 40],
            "is_flapping": False,
            "dest_stats": {
                "prio_1": {"status": "healthy", "latency_ms": 50.0, "packet_loss": 0},
                "prio_2": {"status": "healthy", "latency_ms": 50.0, "packet_loss": 0}
            }
        }

        def mock_check(dest, rule_port=None, protocol=None):
            return {"healthy": True, "latency_ms": 50.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check):
            self.engine.evaluate_rule(rule)

        rule_st = self.engine.runtime_state["rules_state"]["rule-flap"]
        self.assertTrue(rule_st["is_flapping"])
        # Cooldown should be doubled to 60s
        self.assertGreaterEqual(rule_st["cooldown_remaining"], 20)

    def test_nginx_service_lifecycle_management(self):
        """Verifies that Nginx is stopped when 0 rules use it, and started when needed."""
        # Scenario 1: 0 rules use Nginx -> systemctl stop nginx
        with patch("shutil.which", return_value="/bin/systemctl"), \
             patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            ok, err = self.engine._apply_nginx([])
            self.assertTrue(ok)
            self.assertFalse(self.engine.runtime_state["active_services"]["nginx"])
            # Verify systemctl stop nginx was called
            calls = [c[0][0] for c in mock_sub.call_args_list]
            self.assertTrue(any("stop" in str(c) for c in calls))

        # Scenario 2: 1 rule uses Nginx -> systemctl start/reload nginx
        with patch("shutil.which", return_value="/bin/systemctl"), \
             patch("subprocess.run") as mock_sub, \
             patch("builtins.open", unittest.mock.mock_open()), \
             patch("os.path.exists", return_value=True), \
             patch("os.replace"):
            mock_sub.return_value = MagicMock(returncode=0)
            ok, err = self.engine._apply_nginx(["    server { listen 8000; proxy_pass 1.2.3.4:8000; }"])
            self.assertTrue(ok)
            self.assertTrue(self.engine.runtime_state["active_services"]["nginx"])

    def test_zero_collision_mutual_exclusivity(self):
        """Verifies a port is never bound by HAProxy, NFTables, and Nginx simultaneously."""
        self.engine.config["rules"] = [
            {
                "id": "rule-exclusive",
                "port": 7000,
                "protocol": "both",
                "active_priority": 1,
                "destinations": [
                    {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 7000},
                    {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 7000}
                ]
            }
        ]

        captured_haproxy = []
        captured_nft = []
        captured_nginx = []

        def mock_ha(entries, udp=None):
            captured_haproxy.extend(entries)
            return True, None

        def mock_nft(rules):
            captured_nft.extend(rules)
            return True, None

        def mock_ngx(entries):
            captured_nginx.extend(entries)
            return True, None

        with patch.object(self.engine, "_detect_wan_interface", return_value="eth0"), \
             patch.object(self.engine, "_apply_haproxy", side_effect=mock_ha), \
             patch.object(self.engine, "_apply_nftables", side_effect=mock_nft), \
             patch.object(self.engine, "_apply_nginx", side_effect=mock_ngx), \
             patch.object(self.engine, "_save_state_file"):

            # 1. When Priority 1 is active: only HAProxy has port 7000
            self.engine.sync_firewall_and_proxies()
            self.assertTrue(any("fwd_7000" in e for e in captured_haproxy))
            self.assertFalse(any("dport 7000" in r for r in captured_nft))

            # 2. Switch to Priority 2: only NFTables has port 7000
            captured_haproxy.clear()
            captured_nft.clear()
            self.engine.config["rules"][0]["active_priority"] = 2
            self.engine.sync_firewall_and_proxies()

            self.assertFalse(any("fwd_7000" in e for e in captured_haproxy))
            self.assertTrue(any("dport 7000" in r for r in captured_nft))

    def test_override_mode_change_resets_cooldown(self):
        """Verifies that changing force_override (e.g. restoring to Auto) clears active hold-down cooldown."""
        rule = {
            "id": "rule-override-reset",
            "port": 4040,
            "protocol": "tcp",
            "active_priority": 2,
            "force_override": 2,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 4040},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 4040}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.config["cooldown_seconds"] = 60
        now = time.time()
        self.engine.runtime_state["rules_state"]["rule-override-reset"] = {
            "active_priority": 2,
            "last_switch_time": now - 10,
            "cooldown_remaining": 50,
            "last_force_override": 2,
            "dest_stats": {
                "prio_1": {"status": "healthy", "latency_ms": 20.0, "packet_loss": 0, "composite_score": 20.0},
                "prio_2": {"status": "healthy", "latency_ms": 50.0, "packet_loss": 0, "composite_score": 50.0}
            }
        }

        # User changes force_override from 2 to 0 (Auto Failover)
        rule["force_override"] = 0

        def mock_check(dest, rule_port=None, protocol=None):
            if dest["priority"] == 1:
                return {"healthy": True, "latency_ms": 20.0, "packet_loss": 0}
            return {"healthy": True, "latency_ms": 50.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check):
            changed = self.engine.evaluate_rule(rule)
            self.assertTrue(changed)
            # Rule switches to P1 because cooldown was reset and P1 has better score
            self.assertEqual(rule["active_priority"], 1)
            rule_st = self.engine.runtime_state["rules_state"]["rule-override-reset"]
            self.assertEqual(rule_st["last_force_override"], 0)

    def test_burst_probe_fqdn_and_boundary_parameters(self):
        """Verifies burst probe supports domain names, respects count boundaries, and handles invalid inputs."""
        # 1. Invalid port or empty target returns safe failure
        invalid_dest = {"target": "", "port": 0}
        res_inv = self.engine._fast_confirm_burst(invalid_dest, rule_port=0)
        self.assertTrue(res_inv["all_failed"])
        self.assertEqual(res_inv["packet_loss"], 100)

        # 2. Count boundary clamping (count < 1 or count > 5)
        fqdn_dest = {"target": "relay.example.com", "port": 443}
        with patch("socket.socket") as mock_sock:
            mock_inst = MagicMock()
            mock_inst.connect_ex.return_value = 0
            mock_sock.return_value.__enter__.return_value = mock_inst

            # Test count = 99 is clamped to 5
            res_clamped = self.engine._fast_confirm_burst(fqdn_dest, rule_port=443, count=99)
            self.assertFalse(res_clamped["all_failed"])
            self.assertEqual(res_clamped["successes"], 5)
            self.assertEqual(res_clamped["packet_loss"], 0)

    def test_single_destination_rule_stability(self):
        """Verifies a rule with a single destination does not crash or loop when destination fails."""
        rule = {
            "id": "rule-single",
            "port": 9090,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 9090}
            ]
        }
        self.engine.config["rules"] = [rule]

        def mock_check(dest, rule_port=None, protocol=None):
            return {"healthy": False, "latency_ms": None, "packet_loss": 100, "reason": "Connection refused"}

        with patch.object(self.engine, "check_destination", side_effect=mock_check), \
             patch.object(self.engine, "_fast_confirm_burst", return_value={"all_failed": True, "successes": 0}):
            changed = self.engine.evaluate_rule(rule)
            # Cannot switch because no alternative destination exists
            self.assertFalse(changed)
            self.assertEqual(rule["active_priority"], 1)

    def test_all_destinations_failed_behavior(self):
        """Verifies that when all destinations suffer total failure, engine gracefully retains active priority."""
        rule = {
            "id": "rule-all-failed",
            "port": 8443,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 8443},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 8443}
            ]
        }
        self.engine.config["rules"] = [rule]

        def mock_check(dest, rule_port=None, protocol=None):
            return {"healthy": False, "latency_ms": None, "packet_loss": 100, "reason": "Down"}

        with patch.object(self.engine, "check_destination", side_effect=mock_check), \
             patch.object(self.engine, "_fast_confirm_burst", return_value={"all_failed": True, "successes": 0}):
            changed = self.engine.evaluate_rule(rule)
            # Neither candidate is healthy; priority stays without oscillating
            self.assertFalse(changed)
            self.assertEqual(rule["active_priority"], 1)

    def test_forced_priority_down_falls_back_to_auto_mode(self):
        """Verifies that if a rule has a manual force_override, and that destination goes down, it automatically falls back to Auto Failover."""
        rule = {
            "id": "rule-forced-fallback",
            "port": 5050,
            "protocol": "tcp",
            "active_priority": 2,
            "force_override": 2,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 5050},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 5050}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.runtime_state["rules_state"]["rule-forced-fallback"] = {
            "active_priority": 2,
            "last_force_override": 2,
            "dest_stats": {}
        }

        # Destination 2 (forced) fails; Destination 1 is healthy
        def mock_check(dest, rule_port=None, protocol=None):
            if dest["priority"] == 2:
                return {"healthy": False, "latency_ms": None, "packet_loss": 100, "reason": "Connection timed out"}
            return {"healthy": True, "latency_ms": 25.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check), \
             patch.object(self.engine, "_fast_confirm_burst", return_value={"all_failed": True, "successes": 0}):
            changed = self.engine.evaluate_rule(rule)
            self.assertTrue(changed)
            # Must fall back to Auto Failover (force_override -> 0)
            self.assertEqual(rule["force_override"], 0)
            # Must fail over to the healthy candidate (Priority 1)
            self.assertEqual(rule["active_priority"], 1)

    def test_forced_priority_stays_when_healthy(self):
        """Verifies that a manual force_override is respected when the destination remains healthy."""
        rule = {
            "id": "rule-forced-healthy",
            "port": 6060,
            "protocol": "tcp",
            "active_priority": 2,
            "force_override": 2,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "1.1.1.1", "port": 6060},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 6060}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.runtime_state["rules_state"]["rule-forced-healthy"] = {
            "active_priority": 2,
            "last_force_override": 2,
            "dest_stats": {}
        }

        def mock_check(dest, rule_port=None, protocol=None):
            # Both destinations healthy; forced priority 2 must remain
            return {"healthy": True, "latency_ms": 40.0, "packet_loss": 0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check):
            changed = self.engine.evaluate_rule(rule)
            self.assertFalse(changed)
            self.assertEqual(rule["force_override"], 2)
            self.assertEqual(rule["active_priority"], 2)

    def test_evaluate_rule_failback_from_degraded_backup_clears_hold_remaining(self):
        """
        Tests that when an active backup route (Priority 2) experiences packet loss (4%),
        and Priority 1 is healthy (110.6ms, 0% loss), evaluate_rule immediately switches
        back to Priority 1 and does NOT leave hold_remaining set to 1200s even if is_flapping is True.
        """
        now = time.time()
        rule = {
            "id": "rule-9224",
            "port": 9224,
            "protocol": "tcp",
            "active_priority": 2,
            "force_override": 0,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe:bd5::1", "port": 9224, "enabled": True},
                {"priority": 2, "type": "nftables", "target": "10.81.8.2", "port": 9224, "enabled": True}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.config["min_hold_seconds"] = 600
        self.engine.config["max_primary_latency_ms"] = 150.0

        rule_state = {
            "active_priority": 2,
            "last_force_override": 0,
            "last_switch_time": now - 15.0,  # Switched 15s ago
            "last_switch_reason": "critical",
            "is_flapping": True,
            "switch_history": [now - 300, now - 150, now - 15],
            "dest_stats": {
                "prio_1": {"samples": [[now - 20, 10, 10, 110.6, 0.0, 0.0]], "status": "healthy"},
                "prio_2": {"samples": [[now - 20, 10, 9, 123.3, 10.0, 4.0]], "status": "degraded"}
            }
        }
        self.engine.runtime_state["rules_state"]["rule-9224"] = rule_state

        def mock_check(dest, rule_port=None, protocol=None):
            prio = dest.get("priority")
            if prio == 1:
                return {"healthy": True, "latency_ms": 110.6, "packet_loss": 0, "packets_sent": 50, "packets_received": 50, "jitter_ms": 2.0}
            else:
                return {"healthy": True, "latency_ms": 123.3, "packet_loss": 4.0, "packets_sent": 50, "packets_received": 48, "jitter_ms": 3.0}

        with patch.object(self.engine, "check_destination", side_effect=mock_check), \
             patch.object(self.engine, "_hot_toggle_rule_priority") as mock_toggle, \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, "eth0", None)):
            changed = self.engine.evaluate_rule(rule)
            self.assertTrue(changed)
            self.assertEqual(rule["active_priority"], 1)
            self.assertEqual(rule_state["active_priority"], 1)
            # Failback to primary must NOT be critical (is_critical=False) to avoid flushing conntrack!
            mock_toggle.assert_called_once_with(rule, old_prio=2, new_prio=1, is_critical=False)
            # Must NOT be locked in 1200s hold!
            self.assertEqual(rule_state["hold_remaining"], 0)
            # Must record switch event and explanation
            self.assertTrue(len(rule_state.get("switch_events", [])) > 0)
            last_ev = rule_state["switch_events"][-1]
            self.assertEqual(last_ev["from_priority"], 2)
            self.assertEqual(last_ev["to_priority"], 1)
            self.assertEqual(last_ev["reason"], "failback_degraded")
            self.assertIn("Immediate failback to Primary Route", rule_state.get("last_switch_explanation", ""))
            self.assertTrue(len(self.engine.runtime_state.get("recent_switches", [])) > 0)

    def test_switch_events_ring_buffer_capped_at_max(self):
        """Verifies switch_events per rule is bounded at 20 and recent_switches is bounded at 50."""
        rule = {
            "id": "rule-ring-buffer",
            "port": 9300,
            "protocol": "both",
            "active_priority": 1,
            "force_override": 0,
            "destinations": [
                {"priority": 1, "target": "10.0.1.1", "enabled": True},
                {"priority": 2, "target": "10.0.1.2", "enabled": True}
            ]
        }
        # Simulate 25 switches back and forth
        with patch.object(self.engine, "_hot_toggle_rule_priority"), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, "eth0", None)):
            for i in range(25):
                curr = 1 if (i % 2 == 0) else 2
                nxt = 2 if curr == 1 else 1
                mock_cache = {
                    ("10.0.1.1", "eth0"): {"healthy": (nxt == 1), "latency_ms": 50, "packet_loss": 0 if nxt == 1 else 100},
                    ("10.0.1.2", "eth0"): {"healthy": (nxt == 2), "latency_ms": 60, "packet_loss": 0 if nxt == 2 else 100}
                }
                rule["active_priority"] = curr
                if "rule-ring-buffer" in self.engine.runtime_state["rules_state"]:
                    self.engine.runtime_state["rules_state"]["rule-ring-buffer"]["active_priority"] = curr
                self.engine.evaluate_rule(rule, probe_cache=mock_cache)

        rule_state = self.engine.runtime_state["rules_state"]["rule-ring-buffer"]
        self.assertLessEqual(len(rule_state["switch_events"]), 20)
        self.assertLessEqual(len(self.engine.runtime_state["recent_switches"]), 50)

    def test_short_window_aggregates_sample_at_50_seconds(self):
        """Verifies that 50s into a 60s probe interval, short_agg retains healthy metrics without false 100% loss."""
        now = 1050.0
        rule = {
            "id": "rule-window-test",
            "port": 9350,
            "protocol": "both",
            "active_priority": 1,
            "force_override": 0,
            "destinations": [
                {"priority": 1, "target": "10.0.2.1", "enabled": True},
                {"priority": 2, "target": "10.0.2.2", "enabled": True}
            ]
        }
        self.engine.config["target_probe_interval_seconds"] = 60.0
        # Sample recorded at 1000.0s (50 seconds ago)
        cache = {
            ("10.0.2.1", "eth0"): {"healthy": True, "latency_ms": 75.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10},
            ("10.0.2.2", "eth0"): {"healthy": True, "latency_ms": 45.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10}
        }
        with patch("time.time", return_value=now), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, "eth0", None)):
            self.engine.evaluate_rule(rule, probe_cache=cache)
            dest_stats = self.engine.runtime_state["rules_state"]["rule-window-test"]["dest_stats"]
            # Must remain healthy and NOT become degraded with phantom 100% loss
            self.assertEqual(dest_stats["prio_1"]["status"], "healthy")
            self.assertEqual(dest_stats["prio_1"]["short_loss"], 0.0)


if __name__ == "__main__":
    unittest.main()



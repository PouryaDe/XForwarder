#!/usr/bin/env python3
"""
Unit tests for Dual-Feedback Failover Engine:
1. L4 Protocol-Aware Health Probing (eliminating ICMP mask on blocked TCP ports)
2. In-Band Traffic Blackhole / Asymmetric Flow Detection (RX > 20KB, TX == 0)
3. HAProxy C-Native Backend Health Check Status Integration (status == DOWN)
4. Cold-Start / Zero-Traffic False Positive Protection
5. Automatic Failback Recovery when Primary TCP Port Reopens
6. Pure UDP Protocol Isolation (no TCP sockets on UDP destinations)

Standard library unittest only.
"""

import os
import sys
import time
import json
import socket
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.engine import XForwarderEngine
from core.prober import probe_destination_l4_tcp, check_destination, fast_confirm_burst
from core.traffic import TrafficCollector, parse_haproxy_backend_csv


class TestTrafficAwareFailover(unittest.TestCase):
    def setUp(self):
        self.engine = XForwarderEngine(config_path=None)
        self.engine.config = {
            "wan_interface": "eth0",
            "check_interval_seconds": 10,
            "failure_threshold": 3,
            "recovery_threshold": 3,
            "fast_failover_enabled": True,
            "target_probe_interval_seconds": 60,
            "quality_window_seconds": 300,
            "rules": []
        }
        self.engine.runtime_state["wan_interface"] = "eth0"
        self.engine.runtime_state["rules_state"] = {}

    # =========================================================================
    # Scenario 1: The User's Exact Case (ICMP Ping Alive, but TCP Port Blocked)
    # =========================================================================
    def test_scenario_ipv6_ping_alive_but_tcp_port_blocked(self):
        """
        Tests the user's exact issue:
        IPv6 host answers ICMP echo requests (86.9ms, 0% loss), but TCP port 9101
        is blocked by ISP/GFW firewall.
        Verify that check_destination returns healthy: False, packet_loss: 100%,
        and never falls back to ICMP ping.
        """
        dest = {
            "priority": 2,
            "type": "haproxy",
            "target": "2001:4ba0:cafe:3cf::1",
            "port": 9101,
            "protocol": "both"
        }

        # Mock socket to fail with ETIMEDOUT (110)
        with patch("socket.socket") as mock_sock, \
             patch("core.prober.probe_destination_icmp") as mock_icmp:
            mock_s = MagicMock()
            mock_s.connect_ex.return_value = 110  # Connection timed out
            mock_sock.return_value.__enter__.return_value = mock_s

            # Mock ICMP to return healthy 0% loss (the trap!)
            mock_icmp.return_value = {
                "healthy": True,
                "latency_ms": 86.9,
                "packet_loss": 0.0,
                "packets_sent": 10,
                "packets_received": 10
            }

            res = check_destination(dest, rule_port=9101, wan_iface="eth0")

            # Must NOT be healthy!
            self.assertFalse(res["healthy"])
            self.assertEqual(res["packet_loss"], 100.0)
            self.assertIsNone(res["latency_ms"])
            self.assertIn("TCP port 9101 connection", res["reason"])
            # ICMP ping must NOT have been called to override the failure
            mock_icmp.assert_not_called()

    # =========================================================================
    # Scenario 2: Candidate Route Port Block Prevents Unwanted Switch
    # =========================================================================
    def test_scenario_candidate_route_port_block_prevents_switching(self):
        """
        Port 9101 rule:
        Priority 1: Relay via NFTables (10.81.1.2:9101) - Healthy, currently active.
        Priority 2: Direct IPv6 via HAProxy ([2001:4ba0:cafe:3cf::1]:9101) - Candidate.
        IPv6 host answers ICMP, but port 9101 is closed/blocked.
        Verify: Auto Failover remains locked onto Priority 1 and does NOT switch to 2.
        """
        rule = {
            "id": "rule-9101",
            "port": 9101,
            "protocol": "both",
            "active_priority": 1,
            "destinations": [
                {
                    "priority": 1,
                    "type": "nftables",
                    "target": "10.81.1.2",
                    "port": 9101,
                    "tunnel_iface": "tun_gre0"
                },
                {
                    "priority": 2,
                    "type": "haproxy",
                    "target": "2001:4ba0:cafe:3cf::1",
                    "port": 9101
                }
            ]
        }
        self.engine.config["rules"] = [rule]

        now = 10000.0
        # Probe cache where both IPs have good ICMP ping
        probe_cache = {
            "10.81.1.2": {
                "healthy": True,
                "latency_ms": 73.7,
                "packet_loss": 0.0,
                "packets_sent": 10,
                "packets_received": 10
            },
            "2001:4ba0:cafe:3cf::1": {
                "healthy": True,
                "latency_ms": 86.9,
                "packet_loss": 0.0,
                "packets_sent": 10,
                "packets_received": 10
            }
        }

        # Mock L4 check: Priority 1 tunnel is open, Priority 2 IPv6 port 9101 is blocked
        def mock_l4(target, port, iface=None, count=1, timeout=1.5):
            if "2001:4ba0" in target:
                return {
                    "healthy": False,
                    "packets_sent": 1,
                    "packets_received": 0,
                    "packet_loss": 100.0,
                    "latency_ms": None,
                    "reason": "Connection timed out"
                }
            return {
                "healthy": True,
                "packets_sent": 1,
                "packets_received": 1,
                "packet_loss": 0.0,
                "latency_ms": 73.7,
                "reason": ""
            }

        with patch("core.engine.prober_probe_destination_l4_tcp", side_effect=mock_l4), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)), \
             patch.object(self.engine, "_hot_toggle_rule_priority") as mock_toggle:

            changed = self.engine.evaluate_rule(rule, probe_cache=probe_cache, now=now)

            # System must NOT switch to Priority 2!
            self.assertFalse(changed)
            self.assertEqual(rule["active_priority"], 1)
            mock_toggle.assert_not_called()

            # Priority 2 must be classified as failed
            rule_state = self.engine.runtime_state["rules_state"]["rule-9101"]
            p2_stat = rule_state["dest_stats"]["prio_2"]
            self.assertEqual(p2_stat["status"], "failed")
            self.assertEqual(p2_stat["packet_loss"], 100.0)

    # =========================================================================
    # Scenario 3: Active Route Asymmetric Traffic Blackhole Detection
    # =========================================================================
    def test_scenario_active_route_traffic_blackhole_detection(self):
        """
        Active port 9101 on HAProxy has clients uploading data (RX = 45KB),
        but 0 bytes are returned from backend (TX = 0) across 2 consecutive cycles.
        Verify that TrafficCollector flags a traffic blackhole and triggers immediate failover.
        """
        tc = TrafficCollector(db_path=":memory:")
        port = 9101

        # Cycle 1: 30KB RX, 0 TX
        tc._port_recent_deltas[port] = {"rx": 30000, "tx": 0}
        is_bh1, _ = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
        # 1 cycle is not enough (anti-flapping guard requires 2 cycles)
        self.assertFalse(is_bh1)

        # Cycle 2: 45KB RX, 0 TX
        tc._port_recent_deltas[port] = {"rx": 45000, "tx": 0}
        is_bh2, reason2 = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
        # 2nd consecutive cycle confirms the blackhole!
        self.assertTrue(is_bh2)
        self.assertIn("Traffic blackhole on port 9101", reason2)

    # =========================================================================
    # Scenario 4: Cold-Start / Zero-Traffic Hours Safety (No False Positives)
    # =========================================================================
    def test_scenario_cold_start_zero_traffic_safe(self):
        """
        At 4:00 AM with zero active users (RX = 0, TX = 0) or tiny heartbeat (RX = 500B):
        Verify that check_traffic_blackhole never triggers a false-positive failover.
        """
        tc = TrafficCollector(db_path=":memory:")
        port = 9101

        # Idle: 0 RX, 0 TX
        tc._port_recent_deltas[port] = {"rx": 0, "tx": 0}
        for _ in range(5):
            is_bh, _ = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
            self.assertFalse(is_bh)

        # Minor heartbeat: 1KB RX, 0 TX (below 20KB guard)
        tc._port_recent_deltas[port] = {"rx": 1024, "tx": 0}
        is_bh, _ = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
        self.assertFalse(is_bh)

    # =========================================================================
    # Scenario 5: Healthy Traffic Flow (High Download / Normal Browsing)
    # =========================================================================
    def test_scenario_healthy_traffic_flow_resets_blackhole_streak(self):
        """
        When traffic is flowing normally (e.g. 100KB RX, 2MB TX):
        Verify blackhole check returns False and any previous streak is reset.
        """
        tc = TrafficCollector(db_path=":memory:")
        port = 9101

        # Cycle 1: Anomaly
        tc._port_recent_deltas[port] = {"rx": 35000, "tx": 0}
        tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
        self.assertEqual(tc._port_blackhole_streaks[port], 1)

        # Cycle 2: Traffic recovered! 20KB RX, 500KB TX
        tc._port_recent_deltas[port] = {"rx": 20480, "tx": 500000}
        is_bh, _ = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
        self.assertFalse(is_bh)
        # Streak must be reset to 0
        self.assertEqual(tc._port_blackhole_streaks[port], 0)

    # =========================================================================
    # Scenario 6: HAProxy C-Native Backend Health Check Status (DOWN)
    # =========================================================================
    def test_scenario_haproxy_native_backend_down_triggers_emergency_failover(self):
        """
        HAProxy reports srv_9101 has status: DOWN with check_status: L4TOUT.
        Verify that parse_haproxy_backend_csv accurately parses the row,
        and evaluate_rule triggers Tier 1 emergency failover to Priority 2.
        """
        csv_sample = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration
fwd_9101,FRONTEND,,,0,1,100000,5,1024,2048,0,0,0,,,0,0,OPEN,,,,,,,,,1,2,0,,,,0,0,0,,,,
fwd_9101,srv_9101,0,0,0,0,100000,5,0,0,,0,,5,0,0,0,DOWN,1,1,0,3,1,12,30,,1,2,1,,5,,2,0,,0,L4TOUT,,2000
"""
        parsed = parse_haproxy_backend_csv(csv_sample)
        self.assertIn(9101, parsed)
        self.assertEqual(parsed[9101]["status"], "DOWN")
        self.assertEqual(parsed[9101]["check_status"], "L4TOUT")
        self.assertEqual(parsed[9101]["econ"], 5)

        # Now test that evaluate_rule on active HAProxy route triggers emergency switch
        rule = {
            "id": "rule-ha-fail",
            "port": 9101,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe:3cf::1", "port": 9101},
                {"priority": 2, "type": "nftables", "target": "10.81.1.2", "port": 9101, "tunnel_iface": "tun_gre0"}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.runtime_state["rules_state"]["rule-ha-fail"] = {
            "active_priority": 1,
            "dest_stats": {
                "prio_1": {"samples": [], "status": "healthy"},
                "prio_2": {"samples": [[time.time(), 10, 10, 70.0, 1.0]], "status": "healthy"}
            }
        }

        probe_cache = {
            "10.81.1.2": {"healthy": True, "latency_ms": 70.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10}
        }

        with patch.object(self.engine, "_get_cached_haproxy_backend_health", return_value=parsed), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)), \
             patch.object(self.engine, "_hot_toggle_rule_priority") as mock_toggle:

            changed = self.engine.evaluate_rule(rule, probe_cache=probe_cache)
            self.assertTrue(changed)
            self.assertEqual(rule["active_priority"], 2)
            mock_toggle.assert_called_once_with(rule, old_prio=1, new_prio=2, is_critical=True)

    # =========================================================================
    # Scenario 7: Automatic Failback Recovery When Primary Port Reopens
    # =========================================================================
    def test_scenario_failback_recovery_when_primary_port_reopens(self):
        """
        Rule currently running on backup Priority 2.
        Primary Priority 1 (HAProxy port 9101) was down, but now its TCP port reopens.
        Verify that the engine detects the recovery and automatically fails back to Priority 1.
        """
        now = time.time()
        rule = {
            "id": "rule-failback",
            "port": 9101,
            "protocol": "tcp",
            "active_priority": 2,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "198.51.100.1", "port": 9101},
                {"priority": 2, "type": "nftables", "target": "10.81.1.2", "port": 9101, "tunnel_iface": "tun_gre0"}
            ]
        }
        self.engine.config["rules"] = [rule]
        self.engine.runtime_state["rules_state"]["rule-failback"] = {
            "active_priority": 2,
            "last_switch_time": now - 300,
            "dest_stats": {
                "prio_1": {"samples": [[now - 10, 10, 10, 80.0, 1.0]], "status": "healthy"},
                "prio_2": {"samples": [[now - 10, 10, 8, 120.0, 2.0]], "status": "degraded"}
            }
        }

        probe_cache = {
            "198.51.100.1": {"healthy": True, "latency_ms": 80.0, "packet_loss": 0.0},
            "10.81.1.2": {"healthy": True, "latency_ms": 120.0, "packet_loss": 20.0}
        }

        def mock_l4(target, port, iface=None, count=1, timeout=1.5):
            return {"healthy": True, "packets_sent": 1, "packets_received": 1, "packet_loss": 0.0, "latency_ms": 80.0}

        with patch("core.engine.prober_probe_destination_l4_tcp", side_effect=mock_l4), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)), \
             patch.object(self.engine, "_hot_toggle_rule_priority") as mock_toggle:

            changed = self.engine.evaluate_rule(rule, probe_cache=probe_cache, now=now)
            self.assertTrue(changed)
            self.assertEqual(rule["active_priority"], 1)
            # Failback preserves active sockets (is_critical=False)
            mock_toggle.assert_called_once_with(rule, old_prio=2, new_prio=1, is_critical=False)

    # =========================================================================
    # Scenario 8: Pure UDP Destinations (No TCP Sockets Opened)
    # =========================================================================
    def test_scenario_pure_udp_destinations_use_icmp_cleanly(self):
        """
        Destinations configured with protocol: "udp" (e.g. WireGuard, TUIC):
        Verify that check_destination uses ICMP and does NOT attempt to create TCP stream sockets.
        """
        dest_udp = {
            "priority": 1,
            "type": "haproxy",
            "target": "198.51.100.2",
            "port": 51820,
            "protocol": "udp"
        }

        with patch("core.prober.probe_destination_icmp") as mock_icmp, \
             patch("socket.socket") as mock_sock:

            mock_icmp.return_value = {
                "healthy": True,
                "latency_ms": 45.0,
                "packet_loss": 0.0,
                "packets_sent": 1,
                "packets_received": 1
            }

            res = check_destination(dest_udp, rule_port=51820, wan_iface="eth0")

            self.assertTrue(res["healthy"])
            self.assertEqual(res["latency_ms"], 45.0)
            mock_icmp.assert_called_once()
            # TCP socket must NOT have been opened for UDP rule
            mock_sock.assert_not_called()

    # =========================================================================
    # Scenario 9: Custom Port Mapping Keying (rule.port != dest.port)
    # =========================================================================
    def test_scenario_custom_port_mapping_uses_rule_port_for_telemetry_and_dest_port_for_l4(self):
        """
        Rule listens locally on port 443 (fwd_443 / cnt_in_443) and translates to remote port 8443.
        Verify HAProxy backend DOWN status & traffic blackhole key off rule_port (443),
        while L4 TCP handshake checks remote target_port (8443).
        """
        rule = {
            "id": "rule-mapped",
            "port": 443,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe::1", "port": 8443},
                {"priority": 2, "type": "nftables", "target": "10.81.1.2", "port": 8443, "tunnel_iface": "tun_gre0"}
            ]
        }
        self.engine.config["rules"] = [rule]
        probe_cache = {
            "2001:4ba0:cafe::1": {"healthy": True, "latency_ms": 60.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10},
            "10.81.1.2": {"healthy": True, "latency_ms": 75.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10},
        }

        # HAProxy stats CSV keys by listener port 443 (fwd_443), NOT dest port 8443
        ha_health = {443: {"status": "DOWN", "check_status": "L4TOUT", "econ": 2, "stot": 1, "chkfail": 2}}
        checked_l4_ports = []

        def mock_l4(target, port, iface=None, count=1, timeout=1.5):
            checked_l4_ports.append((target, port))
            return {"healthy": True, "packets_sent": 1, "packets_received": 1, "packet_loss": 0.0, "latency_ms": 60.0}

        with patch.object(self.engine, "_get_cached_haproxy_backend_health", return_value=ha_health), \
             patch("core.engine.prober_probe_destination_l4_tcp", side_effect=mock_l4), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)), \
             patch.object(self.engine, "_hot_toggle_rule_priority") as mock_toggle:

            changed = self.engine.evaluate_rule(rule, probe_cache=probe_cache, now=time.time())
            self.assertTrue(changed)
            self.assertEqual(rule["active_priority"], 2)
            mock_toggle.assert_called_once_with(rule, old_prio=1, new_prio=2, is_critical=True)

            # Reset to test L4 check on target_port 8443 when HAProxy socket is healthy
            rule["active_priority"] = 1
            self.engine.runtime_state["rules_state"].pop("rule-mapped", None)
            self.engine._l4_port_cache.clear()
            checked_l4_ports.clear()

        with patch.object(self.engine, "_get_cached_haproxy_backend_health", return_value={}), \
             patch("core.engine.prober_probe_destination_l4_tcp", side_effect=mock_l4), \
             patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)):
            self.engine.evaluate_rule(rule, probe_cache=probe_cache, now=time.time())
            self.assertIn(("2001:4ba0:cafe::1", 8443), checked_l4_ports)

    # =========================================================================
    # Scenario 10: Blackhole Sequence Deduplication, Silent Reset & Failover Clear
    # =========================================================================
    def test_scenario_blackhole_seq_dedup_silent_reset_and_post_switch_clear(self):
        """
        Verifies:
        1. Calling check_traffic_blackhole multiple times during a single collect_cycle seq
           only increments streak once (prevents premature single-cycle trip).
        2. A silent collection cycle (rx=0, tx=0) clears stale delta & streak.
        3. Rule priority transition calls reset_port_blackhole so the new active priority
           does not inherit the previous priority's blackhole state.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "traffic_test.db")
            tc = TrafficCollector(db_path=db_file)
            port = 9101

            # Simulate collect_cycle baseline -> cycle 1 (30KB RX, 0 TX) -> cycle 2 (silent)
            with patch("core.traffic.read_haproxy_port_stats", side_effect=[
                {port: {"rx_bytes": 0, "tx_bytes": 0}},
                {port: {"rx_bytes": 30000, "tx_bytes": 0}},
                {port: {"rx_bytes": 30000, "tx_bytes": 0}},  # Silent cycle
            ]), patch("core.traffic.read_nftables_port_stats", return_value={}), \
                 patch("core.traffic.read_proc_net_dev", return_value={}):
                tc.collect_cycle(ports=[port])  # baseline
                tc.collect_cycle(ports=[port])  # seq 2: 30KB RX, 0 TX

                # Evaluate 5 times within the same collect_cycle seq: MUST remain False (streak == 1)
                for _ in range(5):
                    is_bh, _ = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
                    self.assertFalse(is_bh)
                self.assertEqual(tc._port_blackhole_streaks[port], 1)

                # Silent cycle (seq 3: rx=0, tx=0) must explicitly zero delta and clear streak
                tc.collect_cycle(ports=[port])
                is_bh, _ = tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
                self.assertFalse(is_bh)
                self.assertEqual(tc._port_blackhole_streaks[port], 0)
                self.assertEqual(tc._port_recent_deltas[port]["rx"], 0)

        # Verify engine clears collector blackhole state when switching priority
        tc._port_recent_deltas[port] = {"rx": 40000, "tx": 0}
        tc.check_traffic_blackhole(port, min_rx_bytes=20480, min_consecutive_cycles=2)
        tc._port_recent_deltas[port] = {"rx": 45000, "tx": 0}
        self.engine._traffic_collector = tc

        rule = {
            "id": "rule-bh-switch",
            "port": port,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe::1", "port": port},
                {"priority": 2, "type": "nftables", "target": "10.81.1.2", "port": port, "tunnel_iface": "tun0"}
            ]
        }
        probe_cache = {
            "2001:4ba0:cafe::1": {"healthy": True, "latency_ms": 50.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10},
            "10.81.1.2": {"healthy": True, "latency_ms": 70.0, "packet_loss": 0.0, "packets_sent": 10, "packets_received": 10},
        }
        with patch.object(self.engine, "_validate_probe_route", return_value=(True, None, None)), \
             patch("core.engine.prober_probe_destination_l4_tcp", return_value={"healthy": True, "latency_ms": 50.0, "packet_loss": 0.0, "packets_sent": 1, "packets_received": 1}), \
             patch.object(self.engine, "_hot_toggle_rule_priority"):
            changed = self.engine.evaluate_rule(rule, probe_cache=probe_cache, now=time.time())
            self.assertTrue(changed)
            self.assertEqual(rule["active_priority"], 2)
            # Blackhole state for port MUST be cleared for newly active Priority 2
            self.assertNotIn(port, tc._port_recent_deltas)
            self.assertNotIn(port, tc._port_blackhole_streaks)

    # =========================================================================
    # Scenario 11: Burst Confirmation Protocol & Type Isolation
    # =========================================================================
    def test_scenario_fast_confirm_burst_isolates_haproxy_from_icmp_mask(self):
        """
        fast_confirm_burst on HAProxy TCP must NOT fall back to ICMP on failure,
        while NFTables tunnel routes preserve ICMP burst confirmation fallback.
        """
        ha_dest = {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe::1", "port": 9101, "protocol": "tcp"}
        nft_dest = {"priority": 2, "type": "nftables", "target": "10.81.1.2", "port": 9101, "tunnel_iface": "tun0", "protocol": "tcp"}

        with patch("socket.socket") as mock_sock, \
             patch("core.prober.probe_destination_icmp") as mock_icmp:
            mock_s = MagicMock()
            mock_s.connect_ex.return_value = 111  # ECONNREFUSED
            mock_sock.return_value.__enter__.return_value = mock_s
            mock_icmp.return_value = {"healthy": True, "packets_received": 5, "latency_ms": 40.0}

            ha_burst = fast_confirm_burst(ha_dest, rule_port=9101, count=3)
            self.assertTrue(ha_burst["all_failed"])
            mock_icmp.assert_not_called()

            nft_burst = fast_confirm_burst(nft_dest, rule_port=9101, count=3)
            self.assertFalse(nft_burst["all_failed"])
            self.assertEqual(nft_burst["successes"], 5)
            mock_icmp.assert_called_once()

    # =========================================================================
    # Scenario 12: Security Sanitization in probe_destination_l4_tcp
    # =========================================================================
    def test_scenario_l4_tcp_rejects_malformed_and_injected_hosts(self):
        """Verify probe_destination_l4_tcp strictly rejects malformed targets and out-of-range ports."""
        with patch("socket.socket") as mock_sock:
            for bad_host in ("", "-oProxyCommand=id", "1.2.3.4;rm -rf /", "invalid host"):
                res = probe_destination_l4_tcp(bad_host, 443)
                self.assertFalse(res["healthy"])
                self.assertEqual(res["packet_loss"], 100.0)
                self.assertEqual(res["reason"], "Invalid target host or port")
            for bad_port in (0, -1, 70000, "abc"):
                res = probe_destination_l4_tcp("198.51.100.1", bad_port)
                self.assertFalse(res["healthy"])
                self.assertEqual(res["reason"], "Invalid target host or port")
            mock_sock.assert_not_called()


if __name__ == "__main__":
    unittest.main()

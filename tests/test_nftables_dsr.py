#!/usr/bin/env python3
"""
Unit tests for NFTables DSR (Direct Server Return) forwarding methods:
- nftables_dsr (Iran Ingress: stateless raw prerouting `notrack ip daddr set`)
- nftables_dsr_relay (Spoof-Capable Relay: raw daddr restore + DNAT + SNAT + MSS 1380)
Standard Library unittest only.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.config_manager import validate_rule, migrate_and_normalize_config, is_nftables_type
from core.firewall import generate_nftables_ruleset
from core.engine import XForwarderEngine
from core.prober import validate_probe_route, check_destination
from core.traffic import TrafficCollector, get_traffic_summary


class TestNFTablesDSRMethods(unittest.TestCase):

    def test_is_nftables_type_helper(self):
        for t in ("nftables", "nftables_dsr", "nftables_dsr_relay", "NFTABLES_DSR"):
            self.assertTrue(is_nftables_type(t))
        for t in ("haproxy", "nginx", "", None):
            self.assertFalse(is_nftables_type(t))

    def test_validate_and_migrate_dsr_iran(self):
        rule = {
            "port": 1001,
            "protocol": "tcp",
            "destinations": [
                {
                    "priority": 1,
                    "type": "nftables_dsr",
                    "target": "10.10.10.2",
                    "tunnel_iface": "tun1",
                    "spoof_ip": "185.215.229.193",
                    "comment": "FOU Upload-Only to NL"
                }
            ]
        }
        ok, err = validate_rule(rule)
        self.assertTrue(ok, f"Expected valid nftables_dsr rule, got: {err}")
        self.assertEqual(rule["destinations"][0]["type"], "nftables_dsr")
        self.assertEqual(rule["destinations"][0]["tunnel_iface"], "tun1")
        self.assertEqual(rule["destinations"][0]["spoof_ip"], "185.215.229.193")

        # Port range and excluded_ports are allowed on nftables_dsr
        range_rule = {
            "port": "2000-2010",
            "protocol": "both",
            "destinations": [{"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2"}]
        }
        ok_r, err_r = validate_rule(range_rule)
        self.assertTrue(ok_r, f"Expected valid DSR range rule, got: {err_r}")

        # Stateless nftables_dsr must reject port translation (mismatched single port or range->single port)
        bad_port_trans = {
            "port": 1001,
            "protocol": "tcp",
            "destinations": [{"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2", "port": 2001}]
        }
        ok_bad, err_bad = validate_rule(bad_port_trans)
        self.assertFalse(ok_bad)
        self.assertIn("match inbound port", err_bad.lower())

        bad_range_trans = {
            "port": "2000-2010",
            "protocol": "tcp",
            "destinations": [{"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2", "port": 443}]
        }
        ok_br, _ = validate_rule(bad_range_trans)
        self.assertFalse(ok_br)

        # Normalization idempotence
        cfg = {"schema_version": 3, "rules": [rule]}
        norm1, _ = migrate_and_normalize_config(cfg)
        norm2, modified2 = migrate_and_normalize_config(norm1)
        self.assertFalse(modified2, "Second normalization pass must be idempotent")
        self.assertEqual(norm2["rules"][0]["destinations"][0]["type"], "nftables_dsr")

    def test_validate_dsr_relay_constraints(self):
        # Missing spoof_ip must fail
        missing_spoof = {
            "port": 1001,
            "protocol": "tcp",
            "destinations": [
                {"priority": 1, "type": "nftables_dsr_relay", "target": "5.199.136.72"}
            ]
        }
        ok, err = validate_rule(missing_spoof)
        self.assertFalse(ok)
        self.assertIn("spoof_ip", err.lower())

        # IPv4/IPv6 mismatch between target and spoof_ip must fail
        mismatch = {
            "port": 1001,
            "protocol": "tcp",
            "destinations": [
                {
                    "priority": 1,
                    "type": "nftables_dsr_relay",
                    "target": "5.199.136.72",
                    "spoof_ip": "2001:db8::1"
                }
            ]
        }
        ok, err = validate_rule(mismatch)
        self.assertFalse(ok)
        self.assertIn("version", err.lower())

        # Valid DSR relay rule
        valid_relay = {
            "port": 1001,
            "protocol": "tcp",
            "destinations": [
                {
                    "priority": 1,
                    "type": "nftables_dsr_relay",
                    "target": "5.199.136.72",
                    "port": 1001,
                    "spoof_ip": "185.215.229.193",
                    "ingress_iface": "tun1",
                    "snat_ip": "81.180.93.42"
                }
            ]
        }
        ok, err = validate_rule(valid_relay)
        self.assertTrue(ok, f"Expected valid nftables_dsr_relay rule, got: {err}")
        self.assertEqual(valid_relay["destinations"][0]["ingress_iface"], "tun1")
        self.assertEqual(valid_relay["destinations"][0]["snat_ip"], "81.180.93.42")

    def test_engine_generates_dsr_iran_ruleset(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            cfg = {
                "schema_version": 3,
                "wan_interface": "eth0",
                "rules": [
                    {
                        "id": "rule-1001",
                        "port": 1001,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {
                                "priority": 1,
                                "type": "nftables_dsr",
                                "target": "10.10.10.2",
                                "port": 1001,
                                "spoof_ip": "185.215.229.193",
                                "tunnel_iface": "tun1"
                            }
                        ]
                    }
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            captured = {}
            def fake_apply_nft(dnat_rules, **kwargs):
                captured["dnat"] = dnat_rules
                captured["kwargs"] = kwargs
                captured["ruleset"] = generate_nftables_ruleset(
                    dnat_rules,
                    rule_ports=kwargs.get("rule_ports"),
                    enable_ipv6=True,
                    rule_ranges=kwargs.get("rule_ranges"),
                    custom_oifs=kwargs.get("custom_oifs"),
                    raw_rules=kwargs.get("raw_rules"),
                    snat_rules=kwargs.get("snat_rules"),
                    dsr_mss_rules=kwargs.get("dsr_mss_rules"),
                    has_untracked=kwargs.get("has_untracked", False),
                )
                return True, None, captured["ruleset"]

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            with patch("core.engine.apply_nftables", side_effect=fake_apply_nft), \
                 patch("core.engine.apply_haproxy", return_value=(True, None)), \
                 patch("core.engine.apply_nginx", return_value=(True, None)):
                ok, errs = eng.sync_firewall_and_proxies()

            self.assertTrue(ok, f"Sync failed: {errs}")
            self.assertEqual(captured["dnat"], [])
            rs = captured["ruleset"]
            self.assertIn("chain raw_prerouting", rs)
            self.assertIn("type filter hook prerouting priority raw; policy accept;", rs)
            self.assertIn('iifname "eth0" ip daddr 185.215.229.193 tcp dport 1001 notrack ip daddr set 10.10.10.2', rs)
            self.assertIn("ct state { established, related, untracked } accept", rs)
            self.assertIn("counter cnt_in_1001", rs)
            self.assertTrue(eng.runtime_state["active_services"]["nftables"])

    def test_engine_generates_dsr_relay_ruleset(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            cfg = {
                "schema_version": 3,
                "wan_interface": "eth0",
                "rules": [
                    {
                        "id": "rule-1001",
                        "port": 1001,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {
                                "priority": 1,
                                "type": "nftables_dsr_relay",
                                "target": "5.199.136.72",
                                "port": 1001,
                                "spoof_ip": "185.215.229.193",
                                "ingress_iface": "tun1",
                                "snat_ip": "81.180.93.42"
                            }
                        ]
                    }
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            captured = {}
            def fake_apply_nft(dnat_rules, **kwargs):
                captured["ruleset"] = generate_nftables_ruleset(
                    dnat_rules,
                    rule_ports=kwargs.get("rule_ports"),
                    enable_ipv6=False,
                    rule_ranges=kwargs.get("rule_ranges"),
                    custom_oifs=kwargs.get("custom_oifs"),
                    raw_rules=kwargs.get("raw_rules"),
                    snat_rules=kwargs.get("snat_rules"),
                    dsr_mss_rules=kwargs.get("dsr_mss_rules"),
                    has_untracked=kwargs.get("has_untracked", False),
                )
                return True, None, captured["ruleset"]

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            with patch("core.engine.apply_nftables", side_effect=fake_apply_nft), \
                 patch("core.engine.apply_haproxy", return_value=(True, None)), \
                 patch("core.engine.apply_nginx", return_value=(True, None)):
                ok, errs = eng.sync_firewall_and_proxies()

            self.assertTrue(ok, f"Sync failed: {errs}")
            rs = captured["ruleset"]
            self.assertIn("chain raw_prerouting", rs)
            self.assertIn('iifname "tun1" tcp dport 1001 ip daddr set 185.215.229.193', rs)
            self.assertNotIn("notrack", rs)
            self.assertIn('iifname "tun1" ip daddr 185.215.229.193 tcp dport 1001 dnat to 5.199.136.72:1001', rs)
            self.assertIn('oifname "eth0" ip daddr 5.199.136.72 snat to 81.180.93.42', rs)
            self.assertIn("tcp flags syn tcp option maxseg size set rt mtu", rs)
            self.assertIn("tcp flags syn ip daddr 5.199.136.72 tcp option maxseg size set 1380", rs)

    def test_coexistence_standard_nftables_with_dsr_and_dsr_relay(self):
        """Standard nftables DNAT, nftables_dsr, and nftables_dsr_relay coexist in table xfwd_orchestrator without collision."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            cfg = {
                "schema_version": 3,
                "wan_interface": "eth0",
                "rules": [
                    {
                        "id": "rule-443",
                        "port": 443,
                        "protocol": "both",
                        "active_priority": 1,
                        "destinations": [
                            {"priority": 1, "type": "nftables", "target": "10.88.1.2", "port": 443, "tunnel_iface": "gre1"}
                        ]
                    },
                    {
                        "id": "rule-1001",
                        "port": 1001,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2", "port": 1001, "tunnel_iface": "fou0"}
                        ]
                    },
                    {
                        "id": "rule-1002",
                        "port": 1002,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {
                                "priority": 1,
                                "type": "nftables_dsr_relay",
                                "target": "5.199.136.72",
                                "port": 1002,
                                "spoof_ip": "185.215.229.193",
                                "ingress_iface": "tun1",
                                "snat_ip": "81.180.93.42"
                            }
                        ]
                    },
                    {
                        "id": "rule-excl",
                        "port": 1,
                        "port_range": "1-65535",
                        "excluded_ports": [22, 443, 1001, 1002],
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2"}
                        ]
                    }
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            captured = {}
            def fake_apply_nft(dnat_rules, **kwargs):
                captured["kwargs"] = kwargs
                captured["ruleset"] = generate_nftables_ruleset(
                    dnat_rules,
                    rule_ports=kwargs.get("rule_ports"),
                    enable_ipv6=False,
                    rule_ranges=kwargs.get("rule_ranges"),
                    custom_oifs=kwargs.get("custom_oifs"),
                    raw_rules=kwargs.get("raw_rules"),
                    snat_rules=kwargs.get("snat_rules"),
                    dsr_mss_rules=kwargs.get("dsr_mss_rules"),
                    has_untracked=kwargs.get("has_untracked", False),
                )
                return True, None, captured["ruleset"]

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            with patch("core.engine.apply_nftables", side_effect=fake_apply_nft), \
                 patch("core.engine.apply_haproxy", return_value=(True, None)), \
                 patch("core.engine.apply_nginx", return_value=(True, None)):
                ok, errs = eng.sync_firewall_and_proxies()

            self.assertTrue(ok, f"Sync failed: {errs}")
            rs = captured["ruleset"]
            # Standard nftables rule keeps normal DNAT + gre1 masquerade + rt mtu
            self.assertIn('iifname "eth0" tcp dport 443 dnat to 10.88.1.2:443', rs)
            self.assertIn('oifname "gre1" masquerade', rs)
            self.assertNotIn('oifname "fou0" masquerade', rs)
            self.assertIn("tcp flags syn tcp option maxseg size set rt mtu", rs)
            # Stateless DSR rule uses raw notrack + untracked counter for excluded_ports
            self.assertIn('iifname "eth0" tcp dport 1001 notrack ip daddr set 10.10.10.2', rs)
            self.assertIn("ct state untracked counter name cnt_in_1_excl", rs)
            # DSR Relay keeps its own raw/dnat/snat/scoped MSS without overriding standard rt mtu
            self.assertIn('iifname "tun1" tcp dport 1002 ip daddr set 185.215.229.193', rs)
            self.assertIn('iifname "tun1" ip daddr 185.215.229.193 tcp dport 1002 dnat to 5.199.136.72:1002', rs)
            self.assertIn('oifname "eth0" ip daddr 5.199.136.72 snat to 81.180.93.42', rs)
            self.assertIn("tcp flags syn ip daddr 5.199.136.72 tcp option maxseg size set 1380", rs)

    def test_ipv6_and_malformed_config_defense_in_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            cfg = {
                "schema_version": 3,
                "wan_interface": "eth0",
                "rules": [
                    {
                        "id": "rule-2001",
                        "port": 2001,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {"priority": 1, "type": "nftables_dsr", "target": "2001:db8::2", "port": 2001}
                        ]
                    },
                    {
                        "id": "rule-2002",
                        "port": 2002,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {
                                "priority": 1,
                                "type": "nftables_dsr_relay",
                                "target": "5.199.136.72",
                                "port": 2002,
                                "spoof_ip": "1.2.3.4; drop table ip filter",
                                "ingress_iface": "tun1"
                            }
                        ]
                    }
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            captured = {}
            def fake_apply_nft(dnat_rules, **kwargs):
                captured["ruleset"] = generate_nftables_ruleset(
                    dnat_rules,
                    rule_ports=kwargs.get("rule_ports"),
                    enable_ipv6=True,
                    rule_ranges=kwargs.get("rule_ranges"),
                    custom_oifs=kwargs.get("custom_oifs"),
                    raw_rules=kwargs.get("raw_rules"),
                    snat_rules=kwargs.get("snat_rules"),
                    dsr_mss_rules=kwargs.get("dsr_mss_rules"),
                    has_untracked=kwargs.get("has_untracked", False),
                )
                return True, None, captured["ruleset"]

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            with patch("core.engine.apply_nftables", side_effect=fake_apply_nft), \
                 patch("core.engine.apply_haproxy", return_value=(True, None)), \
                 patch("core.engine.apply_nginx", return_value=(True, None)):
                ok, _ = eng.sync_firewall_and_proxies()

            self.assertTrue(ok)
            rs = captured["ruleset"]
            # Valid IPv6 DSR emitted cleanly without brackets around ip6 daddr set
            self.assertIn('iifname "eth0" tcp dport 2001 notrack ip6 daddr set 2001:db8::2', rs)
            # Malformed spoof_ip injected into config.json must be dropped cleanly
            self.assertNotIn("drop table", rs)

    def test_hot_toggle_between_dsr_and_dnat_queues_conntrack_flush(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            rule = {
                "id": "rule-1001",
                "port": 1001,
                "protocol": "both",
                "active_priority": 1,
                "destinations": [
                    {"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2"},
                    {"priority": 2, "type": "nftables", "target": "10.10.10.2"}
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 3, "rules": [rule]}, f)

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            eng._hot_toggle_rule_priority(rule, old_prio=1, new_prio=2, is_critical=False)
            self.assertIn((1001, None), eng._pending_conntrack_flushes)

    def test_dsr_iran_skips_blackhole_false_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            cfg = {
                "schema_version": 3,
                "wan_interface": "eth0",
                "rules": [
                    {
                        "id": "rule-1001",
                        "port": 1001,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {"priority": 1, "type": "nftables_dsr", "target": "10.10.10.2", "port": 1001, "tunnel_iface": "tun1"},
                            {"priority": 2, "type": "nftables", "target": "10.10.10.2", "port": 1001, "tunnel_iface": "tun1"}
                        ]
                    }
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            mock_tc = MagicMock()
            mock_tc.check_traffic_blackhole.return_value = (True, "Traffic blackhole on port 1001")
            eng._traffic_collector = mock_tc

            probe_cache = {
                "10.10.10.2": {"healthy": True, "packets_sent": 10, "packets_received": 10, "packet_loss": 0.0, "latency_ms": 20.0, "jitter_ms": 1.0}
            }
            with patch.object(eng, "_validate_probe_route", return_value=(True, "tun1", "")):
                changed = eng.evaluate_rule(eng.config["rules"][0], probe_cache=probe_cache)

            self.assertFalse(changed, "Upload-only DSR must not trigger blackhole failover when TX is 0")
            mock_tc.check_traffic_blackhole.assert_not_called()

    def test_prober_route_isolation_for_dsr_types(self):
        # Private DSR target routing via WAN must fail with WAN leak
        valid, iface, reason = validate_probe_route(
            {"type": "nftables_dsr", "target": "10.10.10.2"},
            wan_iface="eth0",
            is_interface_up_fn=lambda i: True,
            get_route_interface_fn=lambda t: "eth0"
        )
        self.assertFalse(valid)
        self.assertIn("WAN leak", reason)

        # DSR relay targets public exit IP via WAN; must not require tunnel_iface
        valid_relay, iface_relay, _ = validate_probe_route(
            {"type": "nftables_dsr_relay", "target": "5.199.136.72", "ingress_iface": "tun1"},
            wan_iface="eth0",
            is_interface_up_fn=lambda i: True,
            get_route_interface_fn=lambda t: "eth0"
        )
        self.assertTrue(valid_relay)
        self.assertIsNone(iface_relay)

        # check_destination uses ICMP for both DSR modes
        with patch("core.prober.probe_destination_icmp", return_value={"healthy": True, "latency_ms": 15.0, "packet_loss": 0.0}) as mock_icmp:
            res = check_destination(
                {"type": "nftables_dsr", "target": "10.10.10.2", "port": 1001, "tunnel_iface": "tun1"},
                validate_route_fn=lambda d: (True, "tun1", "")
            )
            self.assertTrue(res["healthy"])
            mock_icmp.assert_called_once()

    def test_traffic_collector_records_dsr_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "metrics.db")
            tc = TrafficCollector(db_path=db_path)

            nft_samples = [
                {1001: {"rx_bytes": 1000, "tx_bytes": 0}, 1002: {"rx_bytes": 2000, "tx_bytes": 5000}},
                {1001: {"rx_bytes": 6000, "tx_bytes": 0}, 1002: {"rx_bytes": 7000, "tx_bytes": 15000}},
            ]
            idx = {"i": 0}
            def fake_nft():
                val = nft_samples[idx["i"]]
                idx["i"] = min(idx["i"] + 1, len(nft_samples) - 1)
                return val

            method_map = {1001: "nftables_dsr", 1002: "nftables_dsr_relay"}
            with patch("core.traffic.read_haproxy_port_stats", return_value={}), \
                 patch("core.traffic.read_nftables_port_stats", side_effect=fake_nft), \
                 patch("core.traffic.read_proc_net_dev", return_value={}):
                tc.collect_cycle(ports=[1001, 1002], port_method_map=method_map)
                tc.collect_cycle(ports=[1001, 1002], port_method_map=method_map)

            summary = get_traffic_summary(period="24h", db_path=db_path)
            keys = {item["key"]: item for item in summary.get("type_breakdown", [])}
            self.assertIn("method:nftables_dsr", keys)
            self.assertIn("method:nftables_dsr_relay", keys)
            self.assertEqual(keys["method:nftables_dsr"]["total_bytes"], 5000)
            self.assertEqual(keys["method:nftables_dsr_relay"]["total_bytes"], 15000)


if __name__ == "__main__":
    unittest.main()

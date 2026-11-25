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

from core.config_manager import (
    validate_rule, migrate_and_normalize_config, is_nftables_type,
    find_dsr_backend_conflict, suggest_free_dsr_port, import_config_data
)
from core.firewall import generate_nftables_ruleset
from core.engine import XForwarderEngine
from core.prober import validate_probe_route, check_destination
from core.traffic import TrafficCollector, get_traffic_summary


class TestNFTablesDSRMethods(unittest.TestCase):

    def test_is_nftables_type_helper(self):
        for t in (
            "nftables", "nftables_dsr", "nftables_dsr_relay",
            "nftables_dsr_synack", "nftables_dsr_direct", "NFTABLES_DSR", "NFTABLES_DSR_SYNACK"
        ):
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
            self.assertIn("chain syn_mss", rs)
            self.assertIn("tcp flags & (syn|rst) == syn jump syn_mss", rs)
            self.assertIn("tcp option maxseg size set rt mtu", rs)
            self.assertIn("ip daddr 5.199.136.72 tcp option maxseg size > 1340 tcp option maxseg size set 1340", rs)
            self.assertIn("ip saddr 5.199.136.72 tcp option maxseg size > 1340 tcp option maxseg size set 1340", rs)

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
            # Standard nftables rule keeps normal DNAT + gre1 masquerade + rt mtu (omitting iifname for tunnel multi-hop)
            self.assertIn('tcp dport 443 dnat to 10.88.1.2:443', rs)
            self.assertNotIn('iifname "eth0" tcp dport 443 dnat to 10.88.1.2:443', rs)
            self.assertIn('oifname "gre1" masquerade', rs)
            self.assertNotIn('oifname "fou0" masquerade', rs)
            self.assertIn("chain syn_mss", rs)
            self.assertIn("tcp flags & (syn|rst) == syn jump syn_mss", rs)
            self.assertIn("tcp option maxseg size set rt mtu", rs)
            # Stateless DSR rule uses raw notrack + untracked counter for excluded_ports
            self.assertIn('iifname "eth0" tcp dport 1001 notrack ip daddr set 10.10.10.2', rs)
            self.assertIn("ct state untracked counter name cnt_in_1_excl", rs)
            # DSR Relay keeps its own raw/dnat/snat/scoped MSS without overriding standard rt mtu
            self.assertIn('iifname "tun1" tcp dport 1002 ip daddr set 185.215.229.193', rs)
            self.assertIn('iifname "tun1" ip daddr 185.215.229.193 tcp dport 1002 dnat to 5.199.136.72:1002', rs)
            self.assertIn('oifname "eth0" ip daddr 5.199.136.72 snat to 81.180.93.42', rs)
            self.assertIn("ip daddr 5.199.136.72 tcp option maxseg size > 1340 tcp option maxseg size set 1340", rs)
            self.assertIn("ip saddr 5.199.136.72 tcp option maxseg size > 1340 tcp option maxseg size set 1340", rs)

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

    def test_dsr_sysctl_persistence_pmtu_icmp_and_symmetric_mss(self):
        """Verifies persistent 99-xforwarder-dsr.conf drop-in, ICMP PMTU allowance on untracked DSR,
        and symmetric 1380 MSS clamping for nftables_dsr targets."""
        from core.firewall import ensure_dsr_sysctl, cleanup_dsr_sysctl, generate_nftables_ruleset

        # 1. ICMP PMTU rules appear only when has_untracked=True (and IPv6 chains only when IPv6 rules exist)
        rs_untracked = generate_nftables_ruleset(
            [
                '        tcp dport 443 dnat to 10.10.10.2:443',
                '        tcp dport 8443 dnat to [2001:db8::2]:8443',
            ],
            rule_ports={443, 8443},
            enable_ipv6=True,
            has_untracked=True
        )
        self.assertIn("icmp type destination-unreachable accept", rs_untracked)
        self.assertIn("icmpv6 type packet-too-big accept", rs_untracked)

        rs_normal = generate_nftables_ruleset(
            [
                '        tcp dport 443 dnat to 10.10.10.2:443',
                '        tcp dport 8443 dnat to [2001:db8::2]:8443',
            ],
            rule_ports={443, 8443},
            enable_ipv6=True,
            has_untracked=False
        )
        self.assertNotIn("icmp type destination-unreachable accept", rs_normal)
        self.assertNotIn("icmpv6 type packet-too-big accept", rs_normal)

        # 2. Persistent sysctl drop-in write & cleanup (cross-platform mocked linux)
        with tempfile.TemporaryDirectory() as tmp:
            conf_file = os.path.join(tmp, "99-xforwarder-dsr.conf")
            proc_conf_dir = os.path.join(tmp, "proc_conf")
            os.makedirs(os.path.join(proc_conf_dir, "tun99"), exist_ok=True)
            os.makedirs(os.path.join(proc_conf_dir, "all"), exist_ok=True)
            os.makedirs(os.path.join(proc_conf_dir, "lo"), exist_ok=True)
            with patch("core.firewall.sys.platform", "linux"), \
                 patch("core.firewall.shutil.which", return_value=None):
                ensure_dsr_sysctl({"eth0", "gre15"}, sysctl_conf_path=conf_file, proc_net_conf_dir=proc_conf_dir)
                self.assertTrue(os.path.isfile(conf_file))
                with open(conf_file, "r", encoding="utf-8") as f:
                    body = f.read()
                self.assertIn("net.ipv4.ip_forward=1", body)
                self.assertIn("net.ipv4.conf.all.rp_filter=0", body)
                self.assertIn("net.ipv4.conf.default.rp_filter=0", body)
                self.assertIn("net.ipv4.conf.eth0.rp_filter=0", body)
                self.assertIn("net.ipv4.conf.gre15.rp_filter=0", body)
                self.assertIn("net.ipv4.conf.tun99.rp_filter=0", body)
                self.assertNotIn("net.ipv4.conf.lo.rp_filter=0", body)

                cleanup_dsr_sysctl(sysctl_conf_path=conf_file)
                self.assertFalse(os.path.isfile(conf_file))

    def test_detect_dsr_mss_uses_iface_hint_and_ip_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            net_dir = os.path.join(tmp, "net")
            os.makedirs(os.path.join(net_dir, "tun1"), exist_ok=True)
            with open(os.path.join(net_dir, "tun1", "mtu"), "w", encoding="utf-8") as f:
                f.write("1320\n")

            eng = XForwarderEngine(config_path=os.path.join(tmp, "c.json"), state_file_path=os.path.join(tmp, "s.json"))
            orig_isdir = os.path.isdir
            orig_open = open
            with patch("core.engine.os.path.isdir", side_effect=lambda p: True if p == "/sys/class/net" else orig_isdir(p)), \
                 patch("builtins.open", side_effect=lambda p, *a, **kw: orig_open(os.path.join(net_dir, "tun1", "mtu"), *a, **kw) if str(p).replace("\\", "/") == "/sys/class/net/tun1/mtu" else orig_open(p, *a, **kw)):
                self.assertEqual(eng._detect_dsr_mss("eth0", "tun1", "ip"), 1280)
                self.assertEqual(eng._detect_dsr_mss("eth0", "tun1", "ip6"), 1260)

    def test_validate_and_migrate_dsr_synack_and_direct(self):
        # Valid nftables_dsr_synack with port translation (443 -> 24443)
        synack_rule = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [
                {
                    "priority": 1,
                    "type": "nftables_dsr_synack",
                    "target": "10.250.50.1",
                    "port": 24443,
                    "tunnel_iface": "esp-link",
                    "spoof_ip": "198.51.100.25",
                    "comment": "ESP SYN-ACK Return"
                }
            ]
        }
        ok, err = validate_rule(synack_rule)
        self.assertTrue(ok, f"Expected valid nftables_dsr_synack rule, got: {err}")
        self.assertEqual(synack_rule["destinations"][0]["port"], 24443)
        self.assertEqual(synack_rule["destinations"][0]["tunnel_iface"], "esp-link")

        # Valid nftables_dsr_direct (Outside server)
        direct_rule = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [
                {
                    "priority": 1,
                    "type": "nftables_dsr_direct",
                    "target": "10.250.50.1",
                    "port": 24443,
                    "spoof_ip": "198.51.100.25",
                    "ingress_iface": "esp-link"
                }
            ]
        }
        ok_d, err_d = validate_rule(direct_rule)
        self.assertTrue(ok_d, f"Expected valid nftables_dsr_direct rule, got: {err_d}")

        # Normalization idempotence
        cfg = {"schema_version": 3, "rules": [synack_rule, direct_rule]}
        norm1, _ = migrate_and_normalize_config(cfg)
        norm2, mod2 = migrate_and_normalize_config(norm1)
        self.assertFalse(mod2, "Second normalization pass for SYN-ACK/Direct must be idempotent")

        # Reject UDP / both, IPv6, ranges, excluded_ports, missing spoof_ip / ingress_iface
        for bad_rule in (
            {
                "port": 443,
                "protocol": "both",
                "destinations": [{"priority": 1, "type": "nftables_dsr_synack", "target": "10.250.50.1", "port": 24443}]
            },
            {
                "port": 443,
                "protocol": "udp",
                "destinations": [{"priority": 1, "type": "nftables_dsr_direct", "target": "10.250.50.1", "port": 24443, "spoof_ip": "198.51.100.25", "ingress_iface": "esp-link"}]
            },
            {
                "port": "2000-2010",
                "protocol": "tcp",
                "destinations": [{"priority": 1, "type": "nftables_dsr_synack", "target": "10.250.50.1"}]
            },
            {
                "port": 443,
                "protocol": "tcp",
                "destinations": [{"priority": 1, "type": "nftables_dsr_synack", "target": "2001:db8::1"}]
            },
            {
                "port": 443,
                "protocol": "tcp",
                "destinations": [{"priority": 1, "type": "nftables_dsr_direct", "target": "10.250.50.1", "port": 24443, "ingress_iface": "esp-link"}]
            },
            {
                "port": 443,
                "protocol": "tcp",
                "destinations": [{"priority": 1, "type": "nftables_dsr_direct", "target": "10.250.50.1", "port": 24443, "spoof_ip": "198.51.100.25"}]
            },
        ):
            ok_b, _ = validate_rule(bad_rule)
            self.assertFalse(ok_b, f"Expected validation failure for {bad_rule}")

    def test_engine_generates_dsr_synack_iran_ruleset(self):
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
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {
                                "priority": 1,
                                "type": "nftables_dsr_synack",
                                "target": "10.250.50.1",
                                "port": 24443,
                                "tunnel_iface": "esp-link",
                                "spoof_ip": "198.51.100.25"
                            }
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
                    input_rules=kwargs.get("input_rules"),
                    raw_output_rules=kwargs.get("raw_output_rules"),
                    route_output_rules=kwargs.get("route_output_rules"),
                    raw_postrouting_rules=kwargs.get("raw_postrouting_rules"),
                    extra_forward_rules=kwargs.get("extra_forward_rules"),
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
            self.assertIn('iifname "eth0" ip daddr 198.51.100.25 tcp dport 443 notrack ip daddr set 10.250.50.1 tcp dport set 24443', rs)
            self.assertIn('iifname "esp-link" ip saddr 10.250.50.1 tcp sport 24443 notrack', rs)
            self.assertIn("chain dsr_postrouting", rs)
            self.assertIn("type filter hook postrouting priority 300; policy accept;", rs)
            self.assertIn('iifname "esp-link" oifname "eth0" ip saddr 10.250.50.1 tcp sport 24443 tcp flags & (syn | ack) == (syn | ack) ip saddr set 198.51.100.25 tcp sport set 443', rs)
            self.assertIn('iifname "eth0" ip daddr 10.250.50.1 tcp dport 24443 counter name cnt_in_443', rs)
            self.assertIn('iifname "esp-link" ip saddr 10.250.50.1 tcp sport 24443 tcp flags & (syn | ack) == (syn | ack) counter name cnt_out_443', rs)
            self.assertIn("chain syn_mss", rs)
            self.assertNotIn("chain dsr_input", rs)
            self.assertNotIn("chain raw_output", rs)
            self.assertNotIn("chain dsr_route_output", rs)

    def test_engine_generates_dsr_direct_outside_ruleset(self):
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
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [
                            {
                                "priority": 1,
                                "type": "nftables_dsr_direct",
                                "target": "10.250.50.1",
                                "port": 24443,
                                "spoof_ip": "198.51.100.25",
                                "ingress_iface": "esp-link"
                            }
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
                    input_rules=kwargs.get("input_rules"),
                    raw_output_rules=kwargs.get("raw_output_rules"),
                    route_output_rules=kwargs.get("route_output_rules"),
                    raw_postrouting_rules=kwargs.get("raw_postrouting_rules"),
                    extra_forward_rules=kwargs.get("extra_forward_rules"),
                )
                return True, None, captured["ruleset"]

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            with patch("core.engine.apply_nftables", side_effect=fake_apply_nft), \
                 patch("core.engine.apply_haproxy", return_value=(True, None)), \
                 patch("core.engine.apply_nginx", return_value=(True, None)):
                ok, errs = eng.sync_firewall_and_proxies()

            self.assertTrue(ok, f"Sync failed: {errs}")
            rs = captured["ruleset"]
            self.assertIn('iifname "esp-link" ip daddr 10.250.50.1 tcp dport 24443 notrack', rs)
            self.assertIn("chain dsr_input", rs)
            self.assertIn("type filter hook input priority -20; policy accept;", rs)
            self.assertIn('ip daddr 10.250.50.1 tcp dport 24443 iifname != "esp-link" drop', rs)
            self.assertIn('iifname "esp-link" ip daddr 10.250.50.1 tcp dport 24443 counter name cnt_in_443', rs)
            self.assertIn("chain raw_output", rs)
            self.assertIn("type filter hook output priority raw; policy accept;", rs)
            self.assertIn("ip saddr 10.250.50.1 tcp sport 24443 notrack", rs)
            self.assertIn("chain dsr_route_output", rs)
            self.assertIn("type route hook output priority -149; policy accept;", rs)
            self.assertIn("ip saddr 10.250.50.1 tcp sport 24443 tcp flags & (syn | ack) == (syn | ack) meta mark set 0x42600001", rs)
            self.assertIn("chain dsr_postrouting", rs)
            self.assertIn('oifname "eth0" ip saddr 10.250.50.1 tcp sport 24443 tcp flags & (syn | ack) != (syn | ack) counter name cnt_out_443 ip saddr set 198.51.100.25 tcp sport set 443', rs)
            routes = captured["kwargs"].get("dsr_direct_routes", [])
            self.assertEqual(len(routes), 1)
            self.assertEqual(routes[0]["iface"], "esp-link")
            self.assertEqual(routes[0]["table_id"], 42600)
            self.assertEqual(routes[0]["priority"], 12600)
            self.assertEqual(routes[0]["fwmark"], "0x42600001")
            self.assertEqual(routes[0]["throw_ips"], ["198.51.100.25"])
            self.assertTrue(eng.runtime_state["active_services"]["nftables"])

    def test_dsr_direct_policy_routing_helpers_collision_and_cleanup(self):
        from core.firewall import ensure_dsr_direct_policy_routing, cleanup_dsr_direct_policy_routing

        with tempfile.TemporaryDirectory() as tmp:
            st_file = os.path.join(tmp, "dsr_direct_routes.json")
            cmds_seen = []

            def fake_run(cmd, **kwargs):
                cmds_seen.append(cmd[1:])
                res = MagicMock()
                res.returncode = 0
                res.stderr = ""
                if cmd[1:4] == ["-4", "rule", "show"]:
                    res.stdout = "0:\tfrom all lookup local\n32766:\tfrom all lookup main\n"
                elif cmd[1:5] == ["-j", "-4", "route", "show"]:
                    res.returncode = 2
                    res.stdout = ""
                    res.stderr = "Error: ipv4: FIB table does not exist.\nDump terminated"
                else:
                    res.stdout = ""
                return res

            slot = [{
                "iface": "esp-link",
                "table_id": 42600,
                "priority": 12600,
                "fwmark": "0x42600001",
                "throw_ips": ["198.51.100.25"]
            }]
            with patch("core.firewall.sys.platform", "linux"), \
                 patch("core.firewall._find_system_bin", return_value="/sbin/ip"), \
                 patch("core.firewall.subprocess.run", side_effect=fake_run):
                ok, err = ensure_dsr_direct_policy_routing(slot, state_path=st_file)
                self.assertTrue(ok, err)
                self.assertTrue(os.path.isfile(st_file))
                self.assertIn(["route", "replace", "throw", "198.51.100.25/32", "table", "42600"], cmds_seen)
                self.assertIn(["route", "replace", "default", "dev", "esp-link", "table", "42600"], cmds_seen)
                self.assertIn(["rule", "add", "priority", "12600", "fwmark", "0x42600001/0xffffffff", "lookup", "42600"], cmds_seen)

                cmds_seen.clear()
                cleanup_dsr_direct_policy_routing(state_path=st_file)
                self.assertFalse(os.path.isfile(st_file))
                self.assertIn(["rule", "del", "priority", "12600", "fwmark", "0x42600001/0xffffffff", "lookup", "42600"], cmds_seen)
                self.assertIn(["route", "del", "default", "dev", "esp-link", "table", "42600"], cmds_seen)
                self.assertIn(["route", "del", "throw", "198.51.100.25/32", "table", "42600"], cmds_seen)

                # Collision with foreign priority rule must fail cleanly without mutating
                def fake_run_collision(cmd, **kwargs):
                    res = MagicMock()
                    res.returncode = 0
                    res.stderr = ""
                    if cmd[1:4] == ["-4", "rule", "show"]:
                        res.stdout = "12600:\tfrom all fwmark 0x999 lookup 99\n"
                    else:
                        res.stdout = ""
                    return res

                with patch("core.firewall.subprocess.run", side_effect=fake_run_collision):
                    ok_col, err_col = ensure_dsr_direct_policy_routing(slot, state_path=st_file)
                    self.assertFalse(ok_col)
                    self.assertIn("12600", err_col)

    def test_dsr_synack_direct_prober_blackhole_hot_toggle_and_traffic(self):
        from core.traffic import classify_tunnel_type

        # 1. Prober route validation for nftables_dsr_direct allows local tunnel IP without WAN leak failure
        ok_p, iface_p, _ = validate_probe_route(
            {"type": "nftables_dsr_direct", "target": "10.250.50.1", "ingress_iface": "esp-link"},
            wan_iface="eth0",
            is_interface_up_fn=lambda i: i == "esp-link",
            get_route_interface_fn=lambda t: "lo"
        )
        self.assertTrue(ok_p)
        self.assertIsNone(iface_p)

        ok_down, _, reason_down = validate_probe_route(
            {"type": "nftables_dsr_direct", "target": "10.250.50.1", "ingress_iface": "esp-link"},
            wan_iface="eth0",
            is_interface_up_fn=lambda i: False,
            get_route_interface_fn=lambda t: "lo"
        )
        self.assertFalse(ok_down)
        self.assertIn("esp-link", reason_down)

        # 2. Hot-toggle between nftables_dsr_synack and haproxy on TCP-only rule still queues full conntrack flush
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            rule = {
                "id": "rule-443",
                "port": 443,
                "protocol": "tcp",
                "active_priority": 1,
                "destinations": [
                    {"priority": 1, "type": "nftables_dsr_synack", "target": "10.250.50.1", "port": 24443, "tunnel_iface": "esp-link"},
                    {"priority": 2, "type": "haproxy", "target": "2001:db8::1", "port": 443}
                ]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 3, "rules": [rule]}, f)

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            eng._hot_toggle_rule_priority(rule, old_prio=1, new_prio=2, is_critical=False)
            self.assertIn((443, None), eng._pending_conntrack_flushes)

            # 3. nftables_dsr_synack skips traffic blackhole check (download bypasses Iran)
            mock_tc = MagicMock()
            eng._traffic_collector = mock_tc
            probe_cache = {
                "10.250.50.1": {"healthy": True, "packets_sent": 10, "packets_received": 10, "packet_loss": 0.0, "latency_ms": 20.0, "jitter_ms": 1.0}
            }
            with patch.object(eng, "_validate_probe_route", return_value=(True, "esp-link", "")):
                changed = eng.evaluate_rule(eng.config["rules"][0], probe_cache=probe_cache)
            self.assertFalse(changed)
            mock_tc.check_traffic_blackhole.assert_not_called()

        # 4. Traffic accounting & IPsec ESP tunnel classification
        self.assertEqual(classify_tunnel_type("esp-link"), "ipsec_esp")
        self.assertEqual(classify_tunnel_type("xfrm0"), "ipsec_esp")
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "metrics.db")
            tc = TrafficCollector(db_path=db_path)
            samples = [
                {443: {"rx_bytes": 1000, "tx_bytes": 200}, 8443: {"rx_bytes": 1000, "tx_bytes": 5000}},
                {443: {"rx_bytes": 3500, "tx_bytes": 400}, 8443: {"rx_bytes": 2500, "tx_bytes": 25000}},
            ]
            idx = {"i": 0}
            def fake_nft():
                val = samples[idx["i"]]
                idx["i"] = min(idx["i"] + 1, len(samples) - 1)
                return val

            method_map = {443: "nftables_dsr_synack", 8443: "nftables_dsr_direct"}
            with patch("core.traffic.read_haproxy_port_stats", return_value={}), \
                 patch("core.traffic.read_nftables_port_stats", side_effect=fake_nft), \
                 patch("core.traffic.read_proc_net_dev", return_value={}):
                tc.collect_cycle(ports=[443, 8443], port_method_map=method_map)
                tc.collect_cycle(ports=[443, 8443], port_method_map=method_map)

            summary = get_traffic_summary(period="24h", db_path=db_path)
            keys = {item["key"]: item for item in summary.get("type_breakdown", [])}
            self.assertIn("method:nftables_dsr_synack", keys)
            self.assertIn("method:nftables_dsr_direct", keys)
            self.assertEqual(keys["method:nftables_dsr_synack"]["total_bytes"], 2700)
            self.assertEqual(keys["method:nftables_dsr_direct"]["total_bytes"], 21500)

    def test_dsr_direct_third_hop_exit_relay_validation_haproxy_and_probe(self):
        from core.config_manager import validate_rule
        from core.engine import XForwarderEngine

        ok_r, err_r = validate_rule({
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "exit_target": "203.0.113.50",
                "exit_port": 1036,
            }]
        })
        self.assertTrue(ok_r, f"Expected valid 3rd-hop DSR Direct rule, got: {err_r}")

        ok_bad, err_bad = validate_rule({
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "exit_target": "not-an-ip",
            }]
        })
        self.assertFalse(ok_bad)
        self.assertIn("Exit", err_bad)

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 3,
                    "wan_interface": "eth0",
                    "rules": [{
                        "id": "rule-1036",
                        "port": 1036,
                        "protocol": "tcp",
                        "active_priority": 1,
                        "destinations": [{
                            "priority": 1,
                            "type": "nftables_dsr_direct",
                            "target": "10.250.51.2",
                            "port": 24443,
                            "spoof_ip": "198.51.100.99",
                            "ingress_iface": "esp1",
                            "exit_target": "203.0.113.50",
                            "exit_port": 1036,
                            "enabled": True,
                        }]
                    }]
                }, f)

            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            ha_captured = {}
            def fake_ha(haproxy_entries, udp_entries):
                ha_captured["haproxy"] = list(haproxy_entries)
                return True, None

            with patch.object(eng, "_detect_wan_interface", return_value="eth0"), \
                 patch.object(eng, "_detect_dsr_mss", return_value=1340), \
                 patch.object(eng, "_apply_nftables", return_value=(True, None)), \
                 patch.object(eng, "_apply_haproxy", side_effect=fake_ha), \
                 patch.object(eng, "_apply_nginx", return_value=(True, None)):
                ok_sync, errs = eng.sync_firewall_and_proxies()

            self.assertTrue(ok_sync, f"Sync failed: {errs}")
            joined_ha = "\n".join(ha_captured.get("haproxy", []))
            self.assertIn("listen dsr_exit_1036_24443", joined_ha)
            self.assertIn("bind 10.250.51.2:24443", joined_ha)
            self.assertIn("server srv_exit_1036_24443 203.0.113.50:1036 check inter 3s fall 2 rise 2", joined_ha)

    def test_dsr_direct_third_hop_edge_cases_and_fib_error_guard(self):
        from core.config_manager import validate_rule
        from core.engine import XForwarderEngine
        from core.firewall import ensure_dsr_direct_policy_routing

        # 1. Self-loop exit_target == target on same port must be rejected
        ok_loop, err_loop = validate_rule({
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "exit_target": "10.250.51.2",
                "exit_port": 24443,
            }]
        })
        self.assertFalse(ok_loop)
        self.assertIn("self-loop", err_loop.lower())

        # 2. Invalid exit_port (range / out of bounds) rejected; empty exit_port defaults to rule port
        ok_bad_ep, _ = validate_rule({
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "exit_target": "203.0.113.50",
                "exit_port": "1000-2000",
            }]
        })
        self.assertFalse(ok_bad_ep)

        def_rule = {
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "exit_target": "203.0.113.50",
            }]
        }
        ok_def, err_def = validate_rule(def_rule)
        self.assertTrue(ok_def, err_def)
        self.assertEqual(def_rule["destinations"][0]["exit_port"], 1036)

        # 3. Stale exit_target/exit_port stripped when destination type is not nftables_dsr_direct
        syn_rule = {
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_synack",
                "target": "10.250.51.2",
                "port": 24443,
                "tunnel_iface": "esp1",
                "exit_target": "203.0.113.50",
                "exit_port": 1036,
            }]
        }
        self.assertTrue(validate_rule(syn_rule)[0])
        self.assertNotIn("exit_target", syn_rule["destinations"][0])
        self.assertNotIn("exit_port", syn_rule["destinations"][0])

        # 4. Genuine kernel route inspection failure (other than missing FIB table) still aborts cleanly
        with tempfile.TemporaryDirectory() as tmp:
            st_file = os.path.join(tmp, "dsr_direct_routes.json")
            def fake_run_perm_err(cmd, **kwargs):
                res = MagicMock()
                res.returncode = 0
                res.stderr = ""
                if cmd[1:4] == ["-4", "rule", "show"]:
                    res.stdout = "0:\tfrom all lookup local\n"
                elif cmd[1:5] == ["-j", "-4", "route", "show"]:
                    res.returncode = 1
                    res.stdout = ""
                    res.stderr = "RTNETLINK answers: Operation not permitted"
                else:
                    res.stdout = ""
                return res

            with patch("core.firewall.sys.platform", "linux"), \
                 patch("core.firewall._find_system_bin", return_value="/sbin/ip"), \
                 patch("core.firewall.subprocess.run", side_effect=fake_run_perm_err):
                ok_perm, err_perm = ensure_dsr_direct_policy_routing([{
                    "iface": "esp1", "table_id": 42600, "priority": 12600, "fwmark": "0x42600001", "throw_ips": ["198.51.100.99"]
                }], state_path=st_file)
                self.assertFalse(ok_perm)
                self.assertIn("Operation not permitted", err_perm)

        # 5. Bind guard prevents HAProxy port conflict with wildcard rule or web dashboard port (8090),
        #    and L4 TCP failure on 3rd-hop exit_target marks DSR Direct unhealthy
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            state_path = os.path.join(tmp, "state.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 3,
                    "wan_interface": "eth0",
                    "web": {"port": 8090},
                    "rules": [
                        {
                            "id": "rule-1036",
                            "port": 1036,
                            "protocol": "tcp",
                            "active_priority": 1,
                            "destinations": [{
                                "priority": 1,
                                "type": "nftables_dsr_direct",
                                "target": "10.250.51.2",
                                "port": 8090,
                                "spoof_ip": "198.51.100.99",
                                "ingress_iface": "esp1",
                                "exit_target": "203.0.113.50",
                                "exit_port": 1036,
                                "enabled": True,
                            }]
                        }
                    ]
                }, f)
            eng = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            ha_cap = {}
            with patch.object(eng, "_detect_wan_interface", return_value="eth0"), \
                 patch.object(eng, "_detect_dsr_mss", return_value=1340), \
                 patch.object(eng, "_apply_nftables", return_value=(True, None)), \
                 patch.object(eng, "_apply_haproxy", side_effect=lambda ha, udp: ha_cap.update({"ha": list(ha)}) or (True, None)), \
                 patch.object(eng, "_apply_nginx", return_value=(True, None)):
                eng.sync_firewall_and_proxies()
            self.assertEqual(ha_cap.get("ha"), [])

            # L4 check failing on 203.0.113.50:1036 marks dest failed despite healthy ICMP ping
            eng.config["rules"][0]["destinations"][0]["port"] = 24443
            probe_cache = {"203.0.113.50": {"healthy": True, "packets_sent": 10, "packets_received": 10, "packet_loss": 0.0, "latency_ms": 12.0, "jitter_ms": 0.5}}
            with patch.object(eng, "_validate_probe_route", return_value=(True, None, "")), \
                 patch.object(eng, "_check_l4_port_cached", return_value={"healthy": False, "reason": "Connection refused"}) as mock_l4:
                eng.evaluate_rule(eng.config["rules"][0], probe_cache=probe_cache)
            mock_l4.assert_called_once_with("203.0.113.50", 1036, iface=None)
            stat = eng.runtime_state["rules_state"]["rule-1036"]["dest_stats"]["prio_1"]
            self.assertEqual(stat["status"], "failed")
            self.assertEqual(stat["packet_loss"], 100.0)

        # 6. UI Regression: openEditRuleModal preserves exit_target/exit_port and CSS row aligns from top & wraps on mobile
        modal_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "rule_modal.js")
        modals_css_path = os.path.join(REPO_ROOT, "web", "css", "modals.css")
        with open(modal_js_path, "r", encoding="utf-8") as mf:
            modal_js = mf.read()
        with open(modals_css_path, "r", encoding="utf-8") as cf:
            modals_css = cf.read()
        self.assertIn("exit_target: d.exit_target", modal_js)
        self.assertIn("exit_port:", modal_js)
        self.assertIn("align-items: start;", modals_css)
        self.assertIn(".dest-exit-port-group", modals_css)

    def test_dsr_backend_port_conflict_detection_import_and_api(self):
        """Ensure stateless DSR rules cannot silently share (type, target, backend_port) across rules."""
        rule_1036_synack = {
            "id": "rule-1036",
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_synack",
                "target": "10.250.51.2",
                "port": 24443,
                "tunnel_iface": "esp1",
                "enabled": True,
            }],
        }
        rule_2036_conflict = {
            "id": "rule-2036",
            "port": 2036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_synack",
                "target": "10.250.51.2",
                "port": 24443,
                "tunnel_iface": "esp1",
                "enabled": True,
            }],
        }
        err = find_dsr_backend_conflict(rule_2036_conflict, [rule_1036_synack])
        self.assertIsNotNone(err)
        self.assertIn("24443", err)
        self.assertIn("24444", err)
        self.assertEqual(suggest_free_dsr_port("nftables_dsr_synack", "10.250.51.2", [rule_1036_synack]), 24444)

        # Updating the same rule on 24443 is allowed
        self.assertIsNone(find_dsr_backend_conflict(rule_1036_synack, [rule_1036_synack]))

        # Distinct backend port 24444, distinct tunnel IP, or disabled destination are allowed
        rule_2036_ok = {
            **rule_2036_conflict,
            "destinations": [{**rule_2036_conflict["destinations"][0], "port": 24444}],
        }
        self.assertIsNone(find_dsr_backend_conflict(rule_2036_ok, [rule_1036_synack]))

        rule_2036_other_ip = {
            **rule_2036_conflict,
            "destinations": [{**rule_2036_conflict["destinations"][0], "target": "10.250.52.2"}],
        }
        self.assertIsNone(find_dsr_backend_conflict(rule_2036_other_ip, [rule_1036_synack]))

        rule_2036_disabled = {
            **rule_2036_conflict,
            "destinations": [{**rule_2036_conflict["destinations"][0], "enabled": False}],
        }
        self.assertIsNone(find_dsr_backend_conflict(rule_2036_disabled, [rule_1036_synack]))

        # nftables_dsr_direct collision check (including omitted port -> defaults to inbound rule port)
        rule_direct_a = {
            "id": "rule-1036",
            "port": 1036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "enabled": True,
            }],
        }
        rule_direct_b = {
            "id": "rule-2036",
            "port": 2036,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables_dsr_direct",
                "target": "10.250.51.2",
                "port": 24443,
                "spoof_ip": "198.51.100.99",
                "ingress_iface": "esp1",
                "enabled": True,
            }],
        }
        self.assertIsNotNone(find_dsr_backend_conflict(rule_direct_b, [rule_direct_a]))

        # import_config_data rejects conflicting DSR rules and accepts unique backend ports
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 3, "wan_interface": "eth0", "rules": []}, f)
            with patch("core.config_manager.get_config_path", return_value=cfg_path):
                ok_bad, msg_bad, _ = import_config_data(json.dumps([rule_direct_a, rule_direct_b]), mode="replace")
                self.assertFalse(ok_bad)
                self.assertIn("24443", msg_bad)

                rule_direct_b_ok = {
                    **rule_direct_b,
                    "destinations": [{**rule_direct_b["destinations"][0], "port": 24444}],
                }
                ok_good, msg_good, info = import_config_data(json.dumps([rule_direct_a, rule_direct_b_ok]), mode="replace")
                self.assertTrue(ok_good, msg_good)
                self.assertEqual(info["count"], 2)

            # _save_rule_payload API enforces 409 on backend DSR collision
            from core import web_server
            sent = []
            handler = web_server.XForwarderWebHandler.__new__(web_server.XForwarderWebHandler)
            handler.send_json = lambda obj, status=200: sent.append((status, obj))

            def _load_tmp_cfg():
                with open(cfg_path, encoding="utf-8") as fp:
                    return json.load(fp)

            def _save_tmp_cfg(cfg):
                with open(cfg_path, "w", encoding="utf-8") as fp:
                    json.dump(cfg, fp)
                return True

            with patch.object(web_server, "load_config", side_effect=_load_tmp_cfg), \
                 patch.object(web_server, "save_config", side_effect=_save_tmp_cfg), \
                 patch.object(web_server, "is_port_in_use_by_external_service", return_value=False), \
                 patch.object(web_server, "sync_rules_and_notify", return_value=(True, [])):
                # Attempt conflicting port 24443 on new rule 3036
                handler._save_rule_payload({
                    "id": "rule-3036",
                    "port": 3036,
                    "protocol": "tcp",
                    "destinations": [{
                        "priority": 1,
                        "type": "nftables_dsr_direct",
                        "target": "10.250.51.2",
                        "port": 24443,
                        "spoof_ip": "198.51.100.99",
                        "ingress_iface": "esp1",
                        "enabled": True,
                    }],
                })
                self.assertEqual(sent[-1][0], 409)
                self.assertIn("24445", sent[-1][1]["error"])

                # Unique port 24445 succeeds with 200
                handler._save_rule_payload({
                    "id": "rule-3036",
                    "port": 3036,
                    "protocol": "tcp",
                    "destinations": [{
                        "priority": 1,
                        "type": "nftables_dsr_direct",
                        "target": "10.250.51.2",
                        "port": 24445,
                        "spoof_ip": "198.51.100.99",
                        "ingress_iface": "esp1",
                        "enabled": True,
                    }],
                })
                self.assertEqual(sent[-1][0], 200)

        # UI includes conflict guard and quick-apply action
        modal_js_path = os.path.join(REPO_ROOT, "web", "js", "modules", "rule_modal.js")
        with open(modal_js_path, "r", encoding="utf-8") as mf:
            modal_js = mf.read()
        self.assertIn("findConflictingDsrRule", modal_js)
        self.assertIn("applySuggestedDsrPort", modal_js)
        self.assertIn("exitPortVal", modal_js)
        self.assertIn("suggestFreeDsrPort(type, target, inboundStart", modal_js)


if __name__ == "__main__":
    unittest.main()

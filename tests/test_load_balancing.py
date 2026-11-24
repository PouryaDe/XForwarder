#!/usr/bin/env python3
"""
Unit & Integration Tests for Health-Aware Load Balancing on NFTables and Nginx.
Covers schema validation, backward compatibility, IPv4/IPv6 nftables map/vmap generation,
Nginx stream upstreams, targeted conntrack flushing, health-aware pool pruning, failover,
metrics deduplication, and Nginx bidirectional sync.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config_manager import (
    validate_rule,
    migrate_and_normalize_config,
    get_destination_backends,
)
from core.firewall import (
    build_nft_lb_dnat_entries,
    generate_nftables_ruleset,
    flush_conntrack,
    normalize_lb_weights,
)
from core.proxy_gen import (
    build_nginx_lb_upstream,
    apply_nginx,
)
from core.engine import XForwarderEngine
from core.metrics import get_unique_targets_from_config
from core.service_manager import (
    parse_nginx_stream_endpoints,
    sync_xforwarder_from_nginx,
    discover_importable_nginx_rules,
)


class TestLoadBalancing(unittest.TestCase):
    def test_config_validation_and_normalization(self):
        # 1. Valid NFTables IPv4 LB pool
        rule_nft = {
            "port": 443,
            "protocol": "both",
            "destinations": [{
                "priority": 1,
                "type": "nftables",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "10.88.1.2", "port": 443, "weight": 2, "tunnel_iface": "gre1", "comment": "DE{1};bad"},
                    {"target": "10.88.2.2", "port": 8443, "weight": 1, "tunnel_iface": "gre2", "comment": "NL-1"},
                ]
            }]
        }
        ok, err = validate_rule(rule_nft)
        self.assertTrue(ok, err)
        d0 = rule_nft["destinations"][0]
        self.assertEqual(d0["target"], "10.88.1.2")
        self.assertEqual(d0["port"], 443)
        self.assertEqual(d0["lb_targets"][0]["comment"], "DE1bad")

        # 2. Reject mixed IPv4 + IPv6 in NFTables LB pool
        bad_mixed = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "10.88.1.2", "port": 443, "weight": 1},
                    {"target": "2001:db8::2", "port": 443, "weight": 1},
                ]
            }]
        }
        ok_mix, err_mix = validate_rule(bad_mixed)
        self.assertFalse(ok_mix)
        self.assertIn("same IP version", err_mix)

        # 3. Allow mixed IPv4 + IPv6 + hostname in Nginx LB pool
        good_nginx = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nginx",
                "lb_enabled": True,
                "lb_mode": "least_conn",
                "lb_targets": [
                    {"target": "192.0.2.10", "port": 443, "weight": 3},
                    {"target": "2001:db8::10", "port": 8443, "weight": 1},
                    {"target": "edge.example.com", "port": 443, "weight": 2},
                ]
            }]
        }
        self.assertTrue(validate_rule(good_nginx)[0])

        # 4. Reject LB on haproxy and DSR modes
        for bad_type in ("haproxy", "nftables_dsr", "nftables_dsr_relay"):
            bad_rule = {
                "port": 443,
                "protocol": "tcp",
                "destinations": [{
                    "priority": 1,
                    "type": bad_type,
                    "spoof_ip": "198.51.100.1" if bad_type == "nftables_dsr_relay" else "",
                    "lb_enabled": True,
                    "lb_mode": "ip_hash",
                    "lb_targets": [
                        {"target": "2001:db8::1", "port": 443},
                        {"target": "2001:db8::2", "port": 443},
                    ]
                }]
            }
            ok_t, _ = validate_rule(bad_rule)
            self.assertFalse(ok_t, f"LB should be rejected for {bad_type}")

        # 5. Reject least_conn on nftables, duplicate endpoints, weight out of range, <2 targets
        bad_mode = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables",
                "lb_enabled": True,
                "lb_mode": "least_conn",
                "lb_targets": [
                    {"target": "10.0.0.1", "port": 443},
                    {"target": "10.0.0.2", "port": 443},
                ]
            }]
        }
        self.assertFalse(validate_rule(bad_mode)[0])

        bad_dup = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nginx",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "1.1.1.1", "port": 443},
                    {"target": "1.1.1.1", "port": 443},
                ]
            }]
        }
        self.assertFalse(validate_rule(bad_dup)[0])

        # 6. Range pool rejects mixed 1:1 range vs fixed port
        bad_range_mix = {
            "port_range": "10000-20000",
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "10.0.0.1", "port_range": "10000-20000"},
                    {"target": "10.0.0.2", "port": 443},
                ]
            }]
        }
        self.assertFalse(validate_rule(bad_range_mix)[0])

        # 7. Reject >16 targets, 0 enabled targets, out-of-range weight, and port_range on nginx LB
        too_many = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nginx",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [{"target": f"10.0.0.{i}", "port": 443} for i in range(1, 18)]
            }]
        }
        self.assertFalse(validate_rule(too_many)[0])

        zero_enabled = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nginx",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "10.0.0.1", "port": 443, "enabled": False},
                    {"target": "10.0.0.2", "port": 443, "enabled": False},
                ]
            }]
        }
        self.assertFalse(validate_rule(zero_enabled)[0])

        bad_weight = {
            "port": 443,
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nftables",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "10.0.0.1", "port": 443, "weight": 0},
                    {"target": "10.0.0.2", "port": 443, "weight": 101},
                ]
            }]
        }
        self.assertFalse(validate_rule(bad_weight)[0])

        nginx_range = {
            "port_range": "10000-20000",
            "protocol": "tcp",
            "destinations": [{
                "priority": 1,
                "type": "nginx",
                "lb_enabled": True,
                "lb_mode": "ip_hash",
                "lb_targets": [
                    {"target": "1.1.1.1", "port": 443},
                    {"target": "2.2.2.2", "port": 443},
                ]
            }]
        }
        self.assertFalse(validate_rule(nginx_range)[0])

        # 8. Migration preserves non-LB rules without adding LB keys
        legacy_cfg = {
            "schema_version": 3,
            "rules": [{
                "port": 8443,
                "protocol": "tcp",
                "destinations": [{"priority": 1, "type": "nginx", "target": "1.2.3.4", "port": 8443}]
            }]
        }
        norm_cfg, _ = migrate_and_normalize_config(legacy_cfg)
        self.assertNotIn("lb_enabled", norm_cfg["rules"][0]["destinations"][0])
        self.assertEqual(len(get_destination_backends(norm_cfg["rules"][0]["destinations"][0])), 1)

    def test_nftables_lb_ruleset_generation_ipv4_ipv6_and_vmap(self):
        self.assertEqual(normalize_lb_weights([70, 30]), [7, 3])

        # 1. IPv4 same-port discrete map (ip_hash)
        dnat_v4, chains_v4 = build_nft_lb_dnat_entries(
            backends=[("10.88.1.2", 443, 20), ("10.88.2.2", 443, 10)],
            lb_mode="ip_hash",
            ip_version=4,
            protos=("tcp",),
            dport_selectors=[443],
            iif_prefix="",
            inbound_start_port=443,
            rule_idx=0,
            preserve_range=False
        )
        self.assertEqual(chains_v4, [])
        self.assertIn("dnat to jhash ip saddr mod 3 map { 0 : 10.88.1.2, 1 : 10.88.1.2, 2 : 10.88.2.2 }", dnat_v4[0])

        # 2. IPv6 same-port discrete map placed strictly into table ip6
        dnat_v6, chains_v6 = build_nft_lb_dnat_entries(
            backends=[("2001:db8::1", 443, 1), ("2001:db8::2", 443, 1)],
            lb_mode="round_robin",
            ip_version=6,
            protos=("tcp",),
            dport_selectors=[443],
            iif_prefix="",
            inbound_start_port=443,
            rule_idx=1,
            preserve_range=False
        )
        ruleset = generate_nftables_ruleset(
            dnat_v4 + dnat_v6,
            rule_ports={443},
            enable_ipv6=True,
            extra_chains=chains_v4 + chains_v6
        )
        ip4_section, ip6_section = ruleset.split("table ip6 xfwd_orchestrator", 1)
        self.assertIn("10.88.1.2", ip4_section)
        self.assertNotIn("2001:db8::1", ip4_section)
        self.assertIn("numgen inc mod 2 map { 0 : 2001:db8::1, 1 : 2001:db8::2 }", ip6_section)

        # 3. Port translation uses vmap + isolated helper chains with explicit meta l4proto
        dnat_pt, chains_pt = build_nft_lb_dnat_entries(
            backends=[("10.88.1.2", 8443, 1), ("10.88.2.2", 9443, 1)],
            lb_mode="random",
            ip_version=4,
            protos=("tcp", "udp"),
            dport_selectors=[443],
            iif_prefix="",
            inbound_start_port=443,
            rule_idx=2,
            preserve_range=False
        )
        self.assertEqual(len(chains_pt), 2)
        self.assertIn("numgen random mod 2 vmap { 0 : jump xfwd_lb_r2_m0, 1 : jump xfwd_lb_r2_m1 }", dnat_pt[0])
        self.assertIn("meta l4proto tcp dnat to 10.88.1.2:8443", chains_pt[0])
        self.assertIn("meta l4proto udp dnat to 10.88.2.2:9443", chains_pt[1])

        # 4. Single surviving backend collapses cleanly to direct dnat
        dnat_single, chains_single = build_nft_lb_dnat_entries(
            backends=[("10.88.1.2", 8443, 1)],
            lb_mode="ip_hash",
            ip_version=4,
            protos=("tcp",),
            dport_selectors=[443],
            iif_prefix="",
            inbound_start_port=443,
            rule_idx=3,
            preserve_range=False
        )
        self.assertEqual(chains_single, [])
        self.assertEqual(dnat_single, ["        tcp dport 443 dnat to 10.88.1.2:8443"])

        # 5. Inbound range (10000-20000) -> 1:1 map vs fixed port equal to start port (10000)
        dnat_r11, chains_r11 = build_nft_lb_dnat_entries(
            backends=[("10.88.1.2", None, 1), ("10.88.2.2", None, 1)],
            lb_mode="ip_hash",
            ip_version=4,
            protos=("tcp",),
            dport_selectors=["10000-20000"],
            iif_prefix="",
            inbound_start_port=10000,
            rule_idx=4,
            preserve_range=True,
            is_inbound_range=True
        )
        self.assertEqual(chains_r11, [])
        self.assertIn("tcp dport 10000-20000 dnat to jhash ip saddr mod 2 map { 0 : 10.88.1.2, 1 : 10.88.2.2 }", dnat_r11[0])

        dnat_rfixed, chains_rfixed = build_nft_lb_dnat_entries(
            backends=[("10.88.1.2", 10000, 1), ("10.88.2.2", 10000, 1)],
            lb_mode="ip_hash",
            ip_version=4,
            protos=("tcp",),
            dport_selectors=["10000-20000"],
            iif_prefix="",
            inbound_start_port=10000,
            rule_idx=5,
            preserve_range=False,
            is_inbound_range=True
        )
        self.assertEqual(len(chains_rfixed), 2)
        self.assertIn("vmap", dnat_rfixed[0])
        self.assertIn("dnat to 10.88.1.2:10000", chains_rfixed[0])

        # 6. Security: reject injected/invalid target IPs in nftables and nginx upstream builders
        dnat_inj, chains_inj = build_nft_lb_dnat_entries(
            backends=[("10.88.1.2; flush ruleset", 443, 1)],
            lb_mode="ip_hash",
            ip_version=4,
            protos=("tcp",),
            dport_selectors=[443],
            iif_prefix="",
            inbound_start_port=443,
            rule_idx=6
        )
        self.assertEqual(dnat_inj, [])
        self.assertEqual(chains_inj, [])

        self.assertEqual(build_nginx_lb_upstream("bad name;", [("1.1.1.1", 443, 1)]), "")
        self.assertEqual(build_nginx_lb_upstream("xfwd_lb_443", [("1.1.1.1; evil", 443, 1)]), "")

    def test_nginx_lb_upstream_and_random_fallback(self):
        up_hash = build_nginx_lb_upstream("xfwd_lb_443", [("192.0.2.1", 443, 2), ("2001:db8::2", 8443, 1)], "ip_hash")
        self.assertIn("hash $remote_addr consistent;", up_hash)
        self.assertIn("server 192.0.2.1:443 weight=2 max_fails=2 fail_timeout=15s;", up_hash)
        self.assertIn("server [2001:db8::2]:8443 weight=1 max_fails=2 fail_timeout=15s;", up_hash)

        up_lc = build_nginx_lb_upstream("xfwd_lb_443", [("1.1.1.1", 443, 1)], "least_conn")
        self.assertIn("least_conn;", up_lc)

        up_rand = build_nginx_lb_upstream("xfwd_lb_443", [("1.1.1.1", 443, 1), ("2.2.2.2", 443, 1)], "random")
        self.assertIn("random two least_conn;", up_rand)

        # Fallback when nginx -t rejects 'random two least_conn;'
        with tempfile.TemporaryDirectory() as tmpdir:
            ngx_conf = os.path.join(tmpdir, "nginx.conf")
            call_count = {"n": 0}

            def fake_run(cmd, **kwargs):
                if cmd[:2] == ["nginx", "-t"]:
                    call_count["n"] += 1
                    if call_count["n"] == 1:
                        return MagicMock(returncode=1, stderr='nginx: [emerg] unknown directive "random"')
                    return MagicMock(returncode=0, stderr="")
                return MagicMock(returncode=0, stderr="")

            with patch("shutil.which", side_effect=lambda x: "/usr/sbin/nginx" if x == "nginx" else None), \
                 patch("subprocess.run", side_effect=fake_run):
                ok, err = apply_nginx([up_rand, "    server { listen 443 reuseport; proxy_pass xfwd_lb_443; }"], conf_path=ngx_conf)
            self.assertTrue(ok, err)
            self.assertEqual(call_count["n"], 2)
            with open(ngx_conf, "r", encoding="utf-8") as f:
                saved = f.read()
            self.assertNotIn("random two least_conn;", saved)
            self.assertIn("upstream xfwd_lb_443", saved)

    def test_flush_conntrack_targeted_reply_src(self):
        with patch("core.firewall._find_conntrack_bin", return_value="/usr/sbin/conntrack"), \
             patch("subprocess.run") as mock_run:
            flush_conntrack(443, proto="tcp", reply_src="10.88.1.2")
            mock_run.assert_called_once_with(
                ["/usr/sbin/conntrack", "-D", "-f", "ipv4", "-p", "tcp", "--orig-port-dst", "443", "--reply-src", "10.88.1.2"],
                stdout=unittest.mock.ANY, stderr=unittest.mock.ANY, timeout=5.0, check=False
            )
            mock_run.reset_mock()
            flush_conntrack(443, proto="udp", reply_src="2001:db8::2")
            mock_run.assert_called_once_with(
                ["/usr/sbin/conntrack", "-D", "-f", "ipv6", "-p", "udp", "--orig-port-dst", "443", "--reply-src", "2001:db8::2"],
                stdout=unittest.mock.ANY, stderr=unittest.mock.ANY, timeout=5.0, check=False
            )
            mock_run.reset_mock()
            # Reject invalid injection string
            flush_conntrack(443, proto="tcp", reply_src="10.0.0.1 --bad")
            mock_run.assert_not_called()

    def test_engine_health_aware_pruning_recovery_and_failover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            state_path = os.path.join(tmpdir, "state.json")
            cfg = {
                "schema_version": 3,
                "check_interval_seconds": 8,
                "min_hold_seconds": 60,
                "switch_confirm_seconds": 30,
                "rules": [{
                    "id": "rule-443",
                    "port": 443,
                    "protocol": "both",
                    "active_priority": 1,
                    "force_override": 0,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nftables",
                            "enabled": True,
                            "lb_enabled": True,
                            "lb_mode": "ip_hash",
                            "lb_targets": [
                                {"target": "10.88.1.2", "port": 443, "weight": 2, "tunnel_iface": "gre1", "enabled": True},
                                {"target": "10.88.2.2", "port": 443, "weight": 1, "tunnel_iface": "gre2", "enabled": True},
                                {"target": "10.88.3.2", "port": 443, "weight": 1, "tunnel_iface": "gre3", "enabled": True},
                            ]
                        },
                        {
                            "priority": 2,
                            "type": "haproxy",
                            "target": "2001:db8::99",
                            "port": 443,
                            "enabled": True
                        }
                    ]
                }]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            engine = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            engine._validate_probe_route = MagicMock(return_value=(True, "gre1", ""))
            engine._is_ipv6_supported = MagicMock(return_value=True)
            engine._check_l4_port_cached = MagicMock(return_value={"healthy": True, "latency_ms": 20.0, "jitter_ms": 1.0, "packet_loss": 0.0, "reason": ""})

            healthy_p = {"healthy": True, "packets_sent": 10, "packets_received": 10, "packet_loss": 0.0, "latency_ms": 40.0, "jitter_ms": 1.0}
            dead_p = {"healthy": False, "packets_sent": 10, "packets_received": 0, "packet_loss": 100.0, "latency_ms": None, "jitter_ms": 0.0, "reason": "Timeout"}

            # Cycle 1: All 3 healthy -> Priority 1 stays active, all 3 in pool
            probe_all_up = {
                "10.88.1.2": healthy_p,
                "10.88.2.2": healthy_p,
                "10.88.3.2": healthy_p,
                "2001:db8::99": healthy_p,
            }
            with patch("core.engine.apply_nftables", return_value=(True, None, "nft")) as mock_nft, \
                 patch("core.engine.apply_haproxy", return_value=(True, None)), \
                 patch("core.engine.apply_nginx", return_value=(True, None)), \
                 patch("core.engine.flush_conntrack"):
                changed = engine.evaluate_rule(engine.config["rules"][0], probe_cache=probe_all_up, now=1000.0)
                self.assertFalse(changed)
                stat1 = engine.runtime_state["rules_state"]["rule-443"]["dest_stats"]["prio_1"]
                self.assertEqual(stat1["lb_healthy_count"], 3)
                self.assertEqual(len(stat1["lb_active_keys"]), 3)
                fp_all_up = engine._get_rules_fingerprint()

                # Cycle 2: 10.88.2.2 goes DOWN -> auto-pruned from pool, targeted conntrack queued, NO failover to P2
                probe_one_down = dict(probe_all_up, **{"10.88.2.2": dead_p})
                changed2 = engine.evaluate_rule(engine.config["rules"][0], probe_cache=probe_one_down, now=1010.0)
                self.assertFalse(changed2)
                self.assertEqual(stat1["lb_healthy_count"], 2)
                self.assertEqual(stat1["lb_active_keys"], ["10.88.1.2:443", "10.88.3.2:443"])
                self.assertIn((443, None, "10.88.2.2"), engine._pending_targeted_conntrack_flushes)
                self.assertNotEqual(engine._get_rules_fingerprint(), fp_all_up)

                # Sync reflects only the 2 healthy IPs and collects gre1/gre2/gre3 in custom_oifs
                engine.sync_firewall_and_proxies()
                nft_dnat_arg = mock_nft.call_args[0][0]
                nft_kwargs = mock_nft.call_args[1]
                self.assertIn("gre1", nft_kwargs["custom_oifs"])
                self.assertIn("gre2", nft_kwargs["custom_oifs"])
                self.assertIn("gre3", nft_kwargs["custom_oifs"])
                joined_dnat = "\n".join(nft_dnat_arg)
                self.assertIn("10.88.1.2", joined_dnat)
                self.assertIn("10.88.3.2", joined_dnat)
                self.assertNotIn("10.88.2.2", joined_dnat)

                # Cycle 3: 10.88.2.2 recovers -> re-admitted automatically
                changed3 = engine.evaluate_rule(engine.config["rules"][0], probe_cache=probe_all_up, now=1020.0)
                self.assertFalse(changed3)
                self.assertEqual(stat1["lb_healthy_count"], 3)
                self.assertEqual(len(stat1["lb_active_keys"]), 3)

                # Cycle 4: ALL 3 LB nodes go DOWN -> immediate Tier 1 emergency failover to Priority #2
                probe_all_down = {
                    "10.88.1.2": dead_p,
                    "10.88.2.2": dead_p,
                    "10.88.3.2": dead_p,
                    "2001:db8::99": healthy_p,
                }
                changed4 = engine.evaluate_rule(engine.config["rules"][0], probe_cache=probe_all_down, now=1030.0)
                self.assertTrue(changed4)
                self.assertEqual(engine.config["rules"][0]["active_priority"], 2)
                self.assertEqual(stat1["status"], "failed")
                self.assertEqual(stat1["lb_healthy_count"], 0)

    def test_nginx_lb_icmp_blocked_stays_healthy_via_l4_tcp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            state_path = os.path.join(tmpdir, "state.json")
            cfg = {
                "schema_version": 3,
                "rules": [{
                    "id": "rule-8443",
                    "port": 8443,
                    "protocol": "tcp",
                    "active_priority": 1,
                    "destinations": [{
                        "priority": 1,
                        "type": "nginx",
                        "enabled": True,
                        "lb_enabled": True,
                        "lb_mode": "least_conn",
                        "lb_targets": [
                            {"target": "198.51.100.1", "port": 8443, "weight": 1, "enabled": True},
                            {"target": "198.51.100.2", "port": 8443, "weight": 1, "enabled": True},
                        ]
                    }]
                }]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            engine = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            engine._validate_probe_route = MagicMock(return_value=(True, None, ""))
            icmp_dead = {"healthy": False, "packets_sent": 10, "packets_received": 0, "packet_loss": 100.0, "latency_ms": None, "jitter_ms": 0.0}
            icmp_ok = {"healthy": True, "packets_sent": 10, "packets_received": 10, "packet_loss": 0.0, "latency_ms": 20.0, "jitter_ms": 1.0}

            def fake_l4(tgt, port, iface=None, timeout=1.5):
                # Node 1 blocks ICMP but TCP 8443 is UP; Node 2 TCP 8443 is DOWN
                if tgt == "198.51.100.1":
                    return {"healthy": True, "latency_ms": 25.0, "jitter_ms": 1.0, "packet_loss": 0.0, "reason": ""}
                return {"healthy": False, "latency_ms": None, "jitter_ms": 0.0, "packet_loss": 100.0, "reason": "Connection refused"}

            engine._check_l4_port_cached = fake_l4
            engine.evaluate_rule(
                engine.config["rules"][0],
                probe_cache={"198.51.100.1": icmp_dead, "198.51.100.2": icmp_ok},
                now=2000.0
            )
            stat = engine.runtime_state["rules_state"]["rule-8443"]["dest_stats"]["prio_1"]
            self.assertEqual(stat["lb_active_keys"], ["198.51.100.1:8443"])
            self.assertEqual(stat["lb_healthy_count"], 1)

    def test_metrics_and_nginx_sync_with_lb_pools(self):
        cfg = {
            "rules": [{
                "port": 443,
                "protocol": "both",
                "destinations": [{
                    "priority": 1,
                    "type": "nftables",
                    "target": "10.88.1.2",
                    "lb_enabled": True,
                    "lb_mode": "ip_hash",
                    "lb_targets": [
                        {"target": "10.88.1.2", "port": 443, "weight": 2},
                        {"target": "10.88.2.2", "port": 443, "weight": 1},
                        {"target": "10.88.1.2", "port": 8443, "weight": 1},
                    ]
                }]
            }]
        }
        unique = get_unique_targets_from_config(cfg)
        self.assertEqual(unique, ["10.88.1.2", "10.88.2.2"])

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            ngx_conf = os.path.join(tmpdir, "nginx.conf")
            with open(ngx_conf, "w", encoding="utf-8") as f:
                f.write("""
stream {
    upstream xfwd_lb_443 {
        hash $remote_addr consistent;
        server 192.0.2.1:443 weight=2 max_fails=2 fail_timeout=15s;
        server 192.0.2.2:443 weight=1 max_fails=2 fail_timeout=15s;
    }
    server {
        listen 443 reuseport;
        proxy_pass xfwd_lb_443;
    }
}
""")
            parsed = parse_nginx_stream_endpoints([ngx_conf])
            self.assertEqual(parsed, {443: [("tcp", "192.0.2.1", 443), ("tcp", "192.0.2.2", 443)]})

            with patch("core.service_manager._find_unmanaged_nginx_files", return_value=[ngx_conf]):
                disc = discover_importable_nginx_rules(existing_rules=[], protected_ports={22, 8090})
            self.assertEqual(len(disc), 1)
            self.assertTrue(disc[0]["destinations"][0]["lb_enabled"])
            self.assertEqual(len(disc[0]["destinations"][0]["lb_targets"]), 2)

            # Pull-sync retains LB pool when members still exist in Nginx
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 3, "rules": [disc[0]]}, f)
            ok, msg, _ = sync_xforwarder_from_nginx(config_path=cfg_path, nginx_paths=[ngx_conf])
            self.assertTrue(ok, msg)
            self.assertIn("already match", msg)

            # Pull-sync collapses 2-node LB pool to single-target when 1 server is removed from Nginx
            with open(ngx_conf, "w", encoding="utf-8") as f:
                f.write("""
stream {
    server {
        listen 443 reuseport;
        proxy_pass 192.0.2.1:443;
    }
}
""")
            ok_col, _, _ = sync_xforwarder_from_nginx(config_path=cfg_path, nginx_paths=[ngx_conf])
            self.assertTrue(ok_col)
            with open(cfg_path, "r", encoding="utf-8") as f:
                collapsed_cfg = json.load(f)
            d_col = collapsed_cfg["rules"][0]["destinations"][0]
            self.assertNotIn("lb_enabled", d_col)
            self.assertEqual(d_col["target"], "192.0.2.1")

    def test_lb_readmission_hysteresis_and_blackhole_failover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            state_path = os.path.join(tmpdir, "state.json")
            cfg = {
                "schema_version": 3,
                "rules": [{
                    "id": "rule-443",
                    "port": 443,
                    "protocol": "tcp",
                    "active_priority": 1,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nftables",
                            "enabled": True,
                            "lb_enabled": True,
                            "lb_mode": "ip_hash",
                            "lb_targets": [
                                {"target": "10.88.1.2", "port": 443, "weight": 1, "enabled": True},
                                {"target": "10.88.2.2", "port": 443, "weight": 1, "enabled": True},
                            ]
                        },
                        {
                            "priority": 2,
                            "type": "nginx",
                            "target": "198.51.100.5",
                            "port": 443,
                            "enabled": True
                        }
                    ]
                }]
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)

            engine = XForwarderEngine(config_path=cfg_path, state_file_path=state_path)
            engine._validate_probe_route = MagicMock(return_value=(True, "gre1", ""))
            healthy_p = {"healthy": True, "packets_sent": 10, "packets_received": 10, "packet_loss": 0.0, "latency_ms": 30.0, "jitter_ms": 1.0}
            degraded_p = {"healthy": True, "packets_sent": 10, "packets_received": 8, "packet_loss": 20.0, "latency_ms": 90.0, "jitter_ms": 5.0}
            dead_p = {"healthy": False, "packets_sent": 10, "packets_received": 0, "packet_loss": 100.0, "latency_ms": None, "jitter_ms": 0.0}

            # Cycle 1: both healthy; Cycle 2: node 2 dies -> pruned
            engine.evaluate_rule(engine.config["rules"][0], probe_cache={"10.88.1.2": healthy_p, "10.88.2.2": healthy_p, "198.51.100.5": healthy_p}, now=100.0)
            engine.evaluate_rule(engine.config["rules"][0], probe_cache={"10.88.1.2": healthy_p, "10.88.2.2": dead_p, "198.51.100.5": healthy_p}, now=110.0)
            stat = engine.runtime_state["rules_state"]["rule-443"]["dest_stats"]["prio_1"]
            self.assertEqual(stat["lb_active_keys"], ["10.88.1.2:443"])

            # Cycle 3: node 2 returns only as 'degraded' (20% loss) -> stays excluded while node 1 is healthy
            engine.evaluate_rule(engine.config["rules"][0], probe_cache={"10.88.1.2": healthy_p, "10.88.2.2": degraded_p, "198.51.100.5": healthy_p}, now=120.0)
            self.assertEqual(stat["lb_active_keys"], ["10.88.1.2:443"])

            # Cycle 4: active LB pool experiences traffic blackhole -> immediate Tier 1 failover to Priority 2
            mock_tc = MagicMock()
            mock_tc.check_traffic_blackhole.return_value = (True, "Asymmetric blackhole")
            engine._traffic_collector = mock_tc
            with patch("core.engine.flush_conntrack"):
                changed = engine.evaluate_rule(engine.config["rules"][0], probe_cache={"10.88.1.2": healthy_p, "10.88.2.2": healthy_p, "198.51.100.5": healthy_p}, now=130.0)
            self.assertTrue(changed)
            self.assertEqual(engine.config["rules"][0]["active_priority"], 2)
            self.assertEqual(stat["status"], "failed")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit tests for XForwarder Modular Subsystems (core/*.py).
Tests modularized components in isolation: config_manager, auth, firewall, proxy_gen,
prober, system_info, and service_manager.
Standard Library unittest only.
"""

import os
import sys
import json
import time
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.config_manager import (
    is_valid_target,
    validate_rule,
    migrate_and_normalize_config,
    export_config_data,
    import_config_data,
    get_config_path,
    get_state_file_path,
    load_config,
    save_config
)
from core.auth import (
    hash_password,
    verify_password,
    check_rate_limit,
    record_failed_login,
    reset_rate_limit,
    save_sessions_to_disk,
    load_sessions_from_disk,
    ACTIVE_SESSIONS,
    SESSION_LOCK,
    MAX_FAILED_ATTEMPTS
)
from core.firewall import generate_nftables_ruleset
from core.proxy_gen import generate_haproxy_cfg, generate_nginx_cfg
from core.prober import check_destination
from core.system_info import get_network_interfaces_info, get_system_stats
from core.service_manager import get_installed_version, get_local_version_info


class TestModularSubsystems(unittest.TestCase):

    # =========================================================================
    # 1. Config Manager Tests
    # =========================================================================
    def test_target_validation_edge_cases(self):
        """Tests is_valid_target against valid, empty, non-string, and malicious inputs."""
        valid_targets = [
            "1.1.1.1",
            "192.168.1.1",
            "10.0.0.1",
            "::1",
            "2001:db8::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "example.com",
            "relay-01.tunnel.internal",
            "sub.domain.co.uk",
            "localhost"
        ]
        for t in valid_targets:
            self.assertTrue(is_valid_target(t), f"Target should be valid: {t}")

        invalid_targets = [
            "",
            "   ",
            None,
            12345,
            "1.2.3.256",            # Out of IPv4 range
            "256.1.2.3",
            "1.2.3.4.5",
            "example.com; rm -rf /", # Command injection
            "example..com",          # Double dot
            "-example.com",          # Leading hyphen
            "example.com-",          # Trailing hyphen
            "http://example.com",    # URI scheme
            "1.2.3.4:80",            # Target includes port
            "foo$bar.com",           # Invalid shell character
            "2001:xyz::1",           # Invalid IPv6 hex
        ]
        for t in invalid_targets:
            self.assertFalse(is_valid_target(t), f"Target should be invalid: {t}")

    def test_rule_validation_edge_cases(self):
        """Tests validate_rule against schema violations, out-of-range ports, and destination formats."""
        # Valid rule
        valid_rule = {
            "id": "rule-443",
            "port": 443,
            "protocol": "both",
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 443},
                {"priority": 2, "type": "nftables", "target": "10.0.0.2", "port": 443}
            ]
        }
        ok, err = validate_rule(valid_rule)
        self.assertTrue(ok, f"Expected valid rule but got error: {err}")

        # Invalid port: negative, 0, > 65535, non-integer
        for bad_port in [-1, 0, 65536, 100000, "abc", None]:
            bad_rule = dict(valid_rule, port=bad_port)
            ok, err = validate_rule(bad_rule)
            self.assertFalse(ok, f"Port {bad_port} should be invalid")

        # Missing destinations
        ok, err = validate_rule({"port": 443, "destinations": []})
        self.assertFalse(ok)

        # Invalid destination type
        bad_dest_type = {
            "port": 443,
            "destinations": [{"priority": 1, "type": "invalid_engine", "target": "1.2.3.4"}]
        }
        ok, err = validate_rule(bad_dest_type)
        self.assertFalse(ok)

        # Invalid destination target
        bad_dest_target = {
            "port": 443,
            "destinations": [{"priority": 1, "type": "haproxy", "target": "bad;ip;address"}]
        }
        ok, err = validate_rule(bad_dest_target)
        self.assertFalse(ok)

        # HAProxy with IPv4 target must be rejected (HAProxy requires IPv6 target)
        haproxy_ipv4 = {
            "port": 443,
            "destinations": [{"priority": 1, "type": "haproxy", "target": "1.2.3.4"}]
        }
        ok, err = validate_rule(haproxy_ipv4)
        self.assertFalse(ok)

    def test_config_migration_normalization(self):
        """Tests automatic schema migration, default injection, and value clamping."""
        legacy_v1 = {
            "wan_interface": "eth0",
            "rules": [
                {
                    "port": "8080",
                    "protocol": "TCP",
                    "destinations": [
                        {"priority": "1", "target": "2001:db8::1", "comment": "IPv6 Node"},
                        {"priority": "2", "target": "10.0.0.2", "comment": "Internal Tunnel"}
                    ]
                }
            ]
        }
        migrated, modified = migrate_and_normalize_config(legacy_v1)
        self.assertTrue(modified)
        self.assertEqual(migrated["schema_version"], 3)
        self.assertEqual(migrated["check_interval_seconds"], 8)
        self.assertEqual(migrated["min_hold_seconds"], 600)
        self.assertEqual(migrated["hysteresis_percent"], 20)

        # Legacy rule structure normalized
        rule = migrated["rules"][0]
        self.assertEqual(rule["port"], 8080)
        self.assertEqual(rule["protocol"], "tcp")
        self.assertEqual(len(rule["destinations"]), 2)
        self.assertEqual(rule["destinations"][0]["target"], "2001:db8::1")
        self.assertEqual(rule["destinations"][0]["type"], "haproxy")
        self.assertEqual(rule["destinations"][0]["port"], 8080)
        self.assertEqual(rule["destinations"][1]["target"], "10.0.0.2")
        self.assertEqual(rule["destinations"][1]["type"], "nftables")
        self.assertEqual(rule["destinations"][1]["port"], 8080)

        # Out-of-bounds parameter clamping
        out_of_bounds = {
            "schema_version": 3,
            "check_interval_seconds": 9999,
            "probe_count": -5,
            "quality_window_seconds": 10
        }
        clamped, _ = migrate_and_normalize_config(out_of_bounds)
        self.assertEqual(clamped["check_interval_seconds"], 120)  # max 120
        self.assertEqual(clamped["probe_count"], 5)               # min 5
        self.assertEqual(clamped["quality_window_seconds"], 60)   # min 60

    def test_export_and_import_config_data(self):
        """Tests that configuration export sanitizes sensitive data and import validates properly."""
        raw_config = {
            "schema_version": 3,
            "web": {
                "auth": {
                    "username": "admin",
                    "password_hash": "pbkdf2:sha256:100000$abcdef$123456"
                },
                "secret_path": "topsecret"
            },
            "rules": [
                {
                    "id": "rule-1080",
                    "port": 1080,
                    "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::1"}]
                }
            ]
        }
        # Export
        exported = export_config_data(raw_config)
        self.assertNotIn("password_hash", json.dumps(exported))
        self.assertIn("rules", exported)
        self.assertEqual(len(exported["rules"]), 1)

        # Import format 1: Full dict
        import_json_str = json.dumps({"rules": [{"port": 8443, "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::2"}]}]})
        ok, err, res = import_config_data(import_json_str, mode="merge")
        self.assertTrue(ok, f"Import failed: {err}")
        self.assertIn("imported_count", res)
        self.assertEqual(res["imported_count"], 1)

        # Import format 2: Direct rules array
        rules_array_json = json.dumps([{"port": 9090, "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::3"}]}])
        ok, err, res = import_config_data(rules_array_json, mode="merge")
        self.assertTrue(ok, f"Import failed: {err}")
        self.assertEqual(res["imported_count"], 1)

        # Import format 3: Single rule object
        single_rule_json = json.dumps({"port": 9091, "destinations": [{"priority": 1, "type": "haproxy", "target": "2001:db8::4"}]})
        ok, err, res = import_config_data(single_rule_json, mode="merge")
        self.assertTrue(ok, f"Import failed: {err}")
        self.assertEqual(res["imported_count"], 1)

        # Import format 4: Invalid JSON string
        ok, err, res = import_config_data("{invalid_json:}", mode="merge")
        self.assertFalse(ok)

    # =========================================================================
    # 2. Auth Subsystem Tests
    # =========================================================================
    def test_auth_password_and_sessions(self):
        """Tests password hashing, verification, rate limiting, and session persistence."""
        pwd = "TestSecretPassword#2026"
        p_hash = hash_password(pwd)
        self.assertTrue(p_hash.startswith("pbkdf2:sha256:100000$"))

        valid, needs_rehash = verify_password(pwd, p_hash)
        self.assertTrue(valid)
        self.assertFalse(needs_rehash)

        # Wrong password
        invalid, _ = verify_password("WrongPassword!", p_hash)
        self.assertFalse(invalid)

        # Rate limiter
        test_ip = "198.51.100.42"
        reset_rate_limit(test_ip)
        for i in range(MAX_FAILED_ATTEMPTS - 1):
            is_locked, rem, cnt = record_failed_login(test_ip)
            self.assertFalse(is_locked)

        # 5th failed attempt triggers lockout
        is_locked, rem, cnt = record_failed_login(test_ip)
        self.assertTrue(is_locked)
        self.assertGreater(rem, 0)
        self.assertEqual(cnt, MAX_FAILED_ATTEMPTS)

        # Reset rate limit
        reset_rate_limit(test_ip)
        locked, rem, cnt = check_rate_limit(test_ip)
        self.assertFalse(locked)

        # Session persistence
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tf:
            temp_session_path = tf.name
        try:
            with SESSION_LOCK:
                ACTIVE_SESSIONS.clear()
                ACTIVE_SESSIONS["test_token_123"] = {
                    "username": "admin",
                    "expires_at": time.time() + 3600,
                    "last_active": time.time()
                }
            save_sessions_to_disk(temp_session_path)

            with SESSION_LOCK:
                ACTIVE_SESSIONS.clear()
            load_sessions_from_disk(temp_session_path)

            with SESSION_LOCK:
                self.assertIn("test_token_123", ACTIVE_SESSIONS)
                self.assertEqual(ACTIVE_SESSIONS["test_token_123"]["username"], "admin")
        finally:
            if os.path.exists(temp_session_path):
                os.unlink(temp_session_path)

    # =========================================================================
    # 3. Firewall (NFTables) Subsystem Tests
    # =========================================================================
    def test_firewall_ruleset_generation(self):
        """Tests that NFTables ruleset generator produces isolated table ip xfwd_orchestrator."""
        dnat_rules = [
            '        iifname "eth0" tcp dport 443 dnat to 10.0.0.2:443',
            '        iifname "eth0" udp dport 443 dnat to 10.0.0.2:443'
        ]
        nft_content = generate_nftables_ruleset(dnat_rules, rule_ports={443})
        self.assertIn("table ip xfwd_orchestrator", nft_content)
        self.assertIn("chain prerouting", nft_content)
        self.assertIn("chain postrouting", nft_content)
        self.assertIn("chain forward", nft_content)
        self.assertIn("tcp flags syn tcp option maxseg size set rt mtu", nft_content)
        self.assertIn("dport 443", nft_content)
        self.assertIn("dnat to 10.0.0.2:443", nft_content)
        self.assertIn("masquerade", nft_content)

        # Check named counters
        self.assertIn("counter cnt_in_443", nft_content)
        self.assertIn("counter cnt_out_443", nft_content)

        # Edge case: Test with IPv6 enabled produces MSS clamping in table ip6
        nft_ipv6_content = generate_nftables_ruleset(dnat_rules, rule_ports={443}, enable_ipv6=True)
        self.assertIn("table ip6 xfwd_orchestrator", nft_ipv6_content)
        self.assertIn("tcp flags syn tcp option maxseg size set rt mtu", nft_ipv6_content)

    # =========================================================================
    # 4. Proxy Generation Subsystem Tests
    # =========================================================================
    def test_haproxy_and_nginx_generators(self):
        """Tests HAProxy and Nginx configuration generators."""
        haproxy_entries = [
            "listen port_8443\n"
            "    bind :::8443 v4v6\n"
            "    server srv_1 [2001:db8::1]:8443 send-proxy-v2\n"
        ]
        base_ha, fallback_ha = generate_haproxy_cfg(haproxy_entries)
        self.assertIn("global", base_ha)
        self.assertIn("defaults", base_ha)
        self.assertIn("hard-stop-after 2m", base_ha)
        self.assertIn("retries 3", base_ha)
        self.assertIn("timeout connect    5s", base_ha)
        self.assertIn("timeout client     1h", base_ha)
        self.assertIn("listen port_8443", base_ha)
        self.assertIn("server srv_1 [2001:db8::1]:8443 send-proxy-v2", base_ha)
        # Zero-copy splicing in base
        self.assertIn("option  splice-auto", base_ha)

        # Nginx stream proxy config
        nginx_entries = [
            "    server { listen 9000; proxy_pass 10.0.0.5:9000; }"
        ]
        nginx_cfg = generate_nginx_cfg(nginx_entries)
        self.assertIn("stream {", nginx_cfg)
        self.assertIn("listen 9000;", nginx_cfg)
        self.assertIn("proxy_pass 10.0.0.5:9000;", nginx_cfg)

    # =========================================================================
    # 5. Prober Subsystem Tests
    # =========================================================================
    def test_check_destination_nonblocking_socket(self):
        """Tests destination socket health checking handles unreachable target cleanly."""
        dest = {
            "priority": 1,
            "type": "haproxy",
            "target": "192.0.2.1",
            "port": 54321
        }
        with patch("socket.socket") as mock_sock, \
             patch("core.prober.probe_destination_icmp", return_value={"healthy": False, "reason": "Connection refused"}):
            mock_inst = mock_sock.return_value.__enter__.return_value
            mock_inst.connect_ex.return_value = 111  # Connection refused
            res = check_destination(dest, rule_port=54321, wan_iface="eth0")
            self.assertIsInstance(res, dict)
            self.assertFalse(res["healthy"])
            self.assertIn("reason", res)

    # =========================================================================
    # 6. System Info Subsystem Tests
    # =========================================================================
    def test_system_stats_and_network_info(self):
        """Tests that system telemetry returns non-empty structured data."""
        stats = get_system_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("cpu_percent", stats)
        self.assertIn("ram_used_mb", stats)
        self.assertIn("ram_percent", stats)

        net_info = get_network_interfaces_info()
        self.assertIsInstance(net_info, dict)
        self.assertIn("server_ips", net_info)
        self.assertIn("tunnel_interfaces", net_info)

    # =========================================================================
    # 7. Service Manager Tests
    # =========================================================================
    def test_version_retrieval(self):
        """Tests that version detection returns valid string."""
        ver = get_installed_version()
        self.assertIsInstance(ver, str)
        self.assertTrue(len(ver) > 0)


if __name__ == "__main__":
    unittest.main()

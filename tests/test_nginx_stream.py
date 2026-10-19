#!/usr/bin/env python3
"""
Unit tests for XForwarder Nginx Stream Proxy Engine, Configuration Generation,
Zero-Collision Coordination, and Resilient Destination Health Probing.
Standard Library unittest only.
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Ensure repo root and core are in python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.engine import XForwarderEngine, NGINX_CONF_PATH


class TestNginxStreamEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.json")
        self.state_path = os.path.join(self.temp_dir.name, "state.json")
        self.engine = XForwarderEngine(config_path=self.config_path, state_file_path=self.state_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_nginx_entries_tcp(self):
        """Verifies that an Nginx TCP rule generates reuseport and so_keepalive=on."""
        self.engine.config = {
            "schema_version": 2,
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
                            "type": "nginx",
                            "target": "1.2.3.4",
                            "port": 8443,
                            "proxy_protocol": False,
                            "comment": "Foreign Node"
                        }
                    ]
                }
            ]
        }
        with patch.object(self.engine, "_is_ipv6_supported", return_value=False), \
             patch.object(self.engine, "_apply_nftables", return_value=(True, None)), \
             patch.object(self.engine, "_apply_haproxy", return_value=(True, None)), \
             patch.object(self.engine, "_apply_nginx") as mock_apply_ngx:
            mock_apply_ngx.return_value = (True, None)
            ok, errors = self.engine.sync_firewall_and_proxies()
            self.assertTrue(ok)
            self.assertEqual(len(errors), 0)
            mock_apply_ngx.assert_called_once()
            entries = mock_apply_ngx.call_args[0][0]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertIn("listen 443 reuseport so_keepalive=on;", entry)
            self.assertNotIn("udp", entry)
            self.assertIn("proxy_pass 1.2.3.4:8443;", entry)
            self.assertNotIn("proxy_protocol on;", entry)

    def test_nginx_entries_udp(self):
        """Verifies that an Nginx UDP rule generates udp reuseport."""
        self.engine.config = {
            "schema_version": 2,
            "wan_interface": "eth0",
            "rules": [
                {
                    "id": "rule-53",
                    "port": 53,
                    "protocol": "udp",
                    "active_priority": 1,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nginx",
                            "target": "10.0.0.2",
                            "port": 53,
                            "comment": "DNS Tunnel"
                        }
                    ]
                }
            ]
        }
        with patch.object(self.engine, "_is_ipv6_supported", return_value=False), \
             patch.object(self.engine, "_apply_nftables", return_value=(True, None)), \
             patch.object(self.engine, "_apply_haproxy", return_value=(True, None)), \
             patch.object(self.engine, "_apply_nginx") as mock_apply_ngx:
            mock_apply_ngx.return_value = (True, None)
            ok, errors = self.engine.sync_firewall_and_proxies()
            self.assertTrue(ok)
            mock_apply_ngx.assert_called_once()
            entries = mock_apply_ngx.call_args[0][0]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertIn("listen 53 udp reuseport;", entry)
            self.assertNotIn("so_keepalive=on", entry)
            self.assertIn("proxy_pass 10.0.0.2:53;", entry)

    def test_nginx_entries_both_with_ipv6_and_proxy_protocol(self):
        """Verifies both TCP+UDP on IPv4 and IPv6 dual-stack with PROXY protocol v2."""
        self.engine.config = {
            "schema_version": 2,
            "wan_interface": "eth0",
            "rules": [
                {
                    "id": "rule-8443",
                    "port": 8443,
                    "protocol": "both",
                    "active_priority": 1,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nginx",
                            "target": "2001:4ba0:cafe::1",
                            "port": 8443,
                            "proxy_protocol": True,
                            "comment": "Dual Stack Node"
                        }
                    ]
                }
            ]
        }
        with patch.object(self.engine, "_is_ipv6_supported", return_value=True), \
             patch.object(self.engine, "_apply_nftables", return_value=(True, None)), \
             patch.object(self.engine, "_apply_haproxy", return_value=(True, None)), \
             patch.object(self.engine, "_apply_nginx") as mock_apply_ngx:
            mock_apply_ngx.return_value = (True, None)
            ok, errors = self.engine.sync_firewall_and_proxies()
            self.assertTrue(ok)
            mock_apply_ngx.assert_called_once()
            entries = mock_apply_ngx.call_args[0][0]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            # IPv4 listeners
            self.assertIn("listen 8443 reuseport so_keepalive=on;", entry)
            self.assertIn("listen 8443 udp reuseport;", entry)
            # IPv6 listeners
            self.assertIn("listen [::]:8443 ipv6only=on reuseport so_keepalive=on;", entry)
            self.assertIn("listen [::]:8443 udp ipv6only=on reuseport;", entry)
            # Upstream format & proxy_protocol
            self.assertIn("proxy_pass [2001:4ba0:cafe::1]:8443;", entry)
            self.assertIn("proxy_protocol on;", entry)

    def test_nginx_haproxy_udp_helper_with_proxy_protocol(self):
        """Verifies that the HAProxy UDP helper inherits proxy_protocol on and IPv6 listeners."""
        self.engine.config = {
            "schema_version": 2,
            "wan_interface": "eth0",
            "rules": [
                {
                    "id": "rule-443",
                    "port": 443,
                    "protocol": "both",
                    "active_priority": 1,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "haproxy",
                            "target": "1.2.3.4",
                            "port": 443,
                            "proxy_protocol": True,
                            "comment": "Primary HAProxy"
                        }
                    ]
                }
            ]
        }
        with patch.object(self.engine, "_is_ipv6_supported", return_value=True), \
             patch.object(self.engine, "_apply_nftables", return_value=(True, None)), \
             patch.object(self.engine, "_apply_haproxy", return_value=(True, None)), \
             patch.object(self.engine, "_apply_nginx") as mock_apply_ngx:
            mock_apply_ngx.return_value = (True, None)
            ok, errors = self.engine.sync_firewall_and_proxies()
            self.assertTrue(ok)
            entries = mock_apply_ngx.call_args[0][0]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertIn("listen 443 udp reuseport;", entry)
            self.assertIn("listen [::]:443 udp ipv6only=on reuseport;", entry)
            self.assertIn("proxy_protocol on;", entry)

    def test_apply_nginx_config_content(self):
        """Verifies that _apply_nginx generates valid nginx.conf with 1h proxy_timeout and no proxy_responses."""
        test_entries = [
            "    # [Test Server]\n    server { listen 443 reuseport so_keepalive=on; proxy_pass 1.2.3.4:443; }"
        ]
        test_conf_path = os.path.join(self.temp_dir.name, "nginx.conf")

        with patch("core.engine.NGINX_CONF_PATH", test_conf_path), \
             patch("shutil.which", return_value=None):
            ok, err = self.engine._apply_nginx(test_entries)
            self.assertTrue(ok)
            self.assertIsNone(err)
            self.assertTrue(os.path.exists(test_conf_path))

            with open(test_conf_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Ensure proxy_responses 1 is NOT present (which breaks UDP tunnels)
            self.assertNotIn("proxy_responses", content)
            # Ensure long 1h timeout is set
            self.assertIn("proxy_timeout 1h;", content)
            self.assertIn("proxy_connect_timeout 5s;", content)
            self.assertIn("proxy_socket_keepalive on;", content)
            # Ensure test server entry is rendered
            self.assertIn("proxy_pass 1.2.3.4:443;", content)

    def test_check_destination_udp_skips_tcp_probe(self):
        """Verifies that check_destination with protocol='udp' does not attempt TCP connect."""
        dest = {
            "type": "nginx",
            "target": "127.0.0.1",
            "port": 53
        }
        with patch("socket.socket") as mock_sock, \
             patch("subprocess.call", return_value=0):
            res = self.engine.check_destination(dest, rule_port=53, protocol="udp")
            # TCP connect_ex should not be called
            mock_sock.assert_not_called()
            # Ping fallback succeeds
            self.assertTrue(res["healthy"])
            self.assertIsNotNone(res["latency_ms"])

    def test_check_destination_tcp_fail_ping_fallback(self):
        """Verifies that if TCP connect fails, ICMP ping fallback succeeds for Nginx destination."""
        dest = {
            "type": "nginx",
            "target": "10.88.1.2",
            "port": 443
        }
        # Mock route interface so it doesn't fail WAN leak
        with patch.object(self.engine, "_get_route_interface", return_value="gre1"), \
             patch.object(self.engine, "_is_interface_up", return_value=True), \
             patch("socket.socket") as mock_sock, \
             patch("subprocess.call", return_value=0):
            mock_s_inst = MagicMock()
            mock_s_inst.connect_ex.return_value = 111  # Connection refused
            mock_sock.return_value.__enter__.return_value = mock_s_inst

            res = self.engine.check_destination(dest, rule_port=443, protocol="tcp")
            # Despite TCP refused, ICMP ping fallback marked it healthy
            self.assertTrue(res["healthy"])
    def test_nftables_masquerade_rules_syntax(self):
        """Verifies that _apply_nftables generates individual masquerade lines without wildcard set byteorder mismatch."""
        with patch("shutil.which", return_value="nft"), \
             patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            ok, err = self.engine._apply_nftables(["        iifname \"eth0\" tcp dport 443 dnat to 10.88.1.2:443"])
            self.assertTrue(ok)
            self.assertIsNone(err)

            # Retrieve the input passed to communicate()
            sent_input = mock_proc.communicate.call_args_list[0][1]["input"]
            self.assertNotIn('oifname { "gre*"', sent_input)
            self.assertIn('oifname "gre*" masquerade', sent_input)
            self.assertIn('oifname "ipip*" masquerade', sent_input)
            self.assertIn('oifname "awg*" masquerade', sent_input)


if __name__ == "__main__":
    unittest.main()

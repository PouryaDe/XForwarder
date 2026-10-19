import json
import tempfile
import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import XForwarderEngine, is_private_or_tunnel_target


class TestEngineProbes(unittest.TestCase):
    def setUp(self):
        self.engine = XForwarderEngine(config_path=None)
        self.engine.config = {
            "wan_interface": "eth0",
            "failure_threshold": 3,
            "recovery_threshold": 3,
            "rules": []
        }
        self.engine.runtime_state["wan_interface"] = "eth0"

    def test_is_private_or_tunnel_target(self):
        # RFC 1918 IPv4
        self.assertTrue(is_private_or_tunnel_target("10.88.1.2"))
        self.assertTrue(is_private_or_tunnel_target("10.0.0.1"))
        self.assertTrue(is_private_or_tunnel_target("172.16.0.1"))
        self.assertTrue(is_private_or_tunnel_target("172.31.255.254"))
        self.assertTrue(is_private_or_tunnel_target("192.168.1.1"))

        # Loopback and Link-local
        self.assertTrue(is_private_or_tunnel_target("127.0.0.1"))
        self.assertTrue(is_private_or_tunnel_target("169.254.1.1"))
        self.assertTrue(is_private_or_tunnel_target("::1"))
        self.assertTrue(is_private_or_tunnel_target("fe80::1"))

        # IPv6 ULA (Unique Local Address)
        self.assertTrue(is_private_or_tunnel_target("fd00::1"))
        self.assertTrue(is_private_or_tunnel_target("fc00:1234::1"))

        # Public IPv4 and IPv6 must return False
        self.assertFalse(is_private_or_tunnel_target("1.1.1.1"))
        self.assertFalse(is_private_or_tunnel_target("8.8.8.8"))
        self.assertFalse(is_private_or_tunnel_target("2001:4ba0:cafe:84e::1"))
        self.assertFalse(is_private_or_tunnel_target("2606:4700:4700::1111"))

        # Invalid strings
        self.assertFalse(is_private_or_tunnel_target(""))
        self.assertFalse(is_private_or_tunnel_target("not-an-ip"))
        self.assertFalse(is_private_or_tunnel_target("example.com"))

    def test_check_destination_missing_explicit_tunnel_interface(self):
        dest = {
            "priority": 2,
            "type": "nftables",
            "target": "10.88.1.2",
            "port": 2023,
            "tunnel_iface": "nonexistent_gre99"
        }
        with patch.object(self.engine, "_is_interface_up", return_value=False):
            res = self.engine.check_destination(dest)
            self.assertFalse(res["healthy"])
            self.assertIsNone(res["latency_ms"])
            self.assertIn("missing or down", res.get("reason", ""))

    def test_check_destination_private_target_routed_via_wan(self):
        # When 10.88.1.2 routes via primary WAN (eth0), it means no tunnel is defined!
        dest = {
            "priority": 2,
            "type": "nftables",
            "target": "10.88.1.2",
            "port": 2023
        }
        with patch.object(self.engine, "_detect_wan_interface", return_value="eth0"), \
             patch.object(self.engine, "_get_route_interface", return_value="eth0"):
            res = self.engine.check_destination(dest)
            self.assertFalse(res["healthy"])
            self.assertIsNone(res["latency_ms"])
            self.assertIn("WAN leak via eth0", res.get("reason", ""))

    def test_check_destination_private_target_no_route(self):
        dest = {
            "priority": 2,
            "type": "nftables",
            "target": "10.88.1.2",
            "port": 2023
        }
        with patch.object(self.engine, "_detect_wan_interface", return_value="eth0"), \
             patch.object(self.engine, "_get_route_interface", return_value=""):
            res = self.engine.check_destination(dest)
            self.assertFalse(res["healthy"])
            self.assertIsNone(res["latency_ms"])
            self.assertIn("No route to destination", res.get("reason", ""))

    def test_check_destination_fallback_device_rejected(self):
        dest = {
            "priority": 2,
            "type": "nftables",
            "target": "10.88.1.2",
            "port": 2023
        }
        with patch.object(self.engine, "_detect_wan_interface", return_value="eth0"), \
             patch.object(self.engine, "_get_route_interface", return_value="gre0"):
            res = self.engine.check_destination(dest)
            self.assertFalse(res["healthy"])
            self.assertIsNone(res["latency_ms"])
            self.assertIn("fallback device", res.get("reason", ""))

    def test_check_destination_valid_tunnel_probe(self):
        dest = {
            "priority": 2,
            "type": "nftables",
            "target": "10.88.1.2",
            "port": 2023
        }
        with patch.object(self.engine, "_detect_wan_interface", return_value="eth0"), \
             patch.object(self.engine, "_get_route_interface", return_value="gre1"), \
             patch.object(self.engine, "_is_interface_up", return_value=True), \
             patch("subprocess.call", return_value=0):
            res = self.engine.check_destination(dest)
            self.assertTrue(res["healthy"])
            self.assertGreaterEqual(res["latency_ms"], 0.0)

    def test_invalid_target_or_port(self):
        self.assertFalse(self.engine.check_destination({"target": "", "port": 80})["healthy"])
        self.assertFalse(self.engine.check_destination({"target": "10.0.0.1", "port": 0})["healthy"])
        self.assertFalse(self.engine.check_destination({"target": "10.0.0.1", "port": -5})["healthy"])

    def test_destination_port_fallback(self):
        # When dest has no port, falls back to rule_port
        dest = {"priority": 1, "type": "haproxy", "target": "127.0.0.1"}
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.__exit__.return_value = False
        with patch("socket.socket", return_value=mock_sock):
            res = self.engine.check_destination(dest, rule_port=9999)
            self.assertTrue(res["healthy"])
            mock_sock.connect_ex.assert_called_once_with(("127.0.0.1", 9999))

    def test_state_preservation_on_init_and_save(self):
        # Verifies that initializing engine or saving state does NOT wipe existing rules_state
        temp_dir = tempfile.mkdtemp()
        try:
            state_file = os.path.join(temp_dir, "state.json")
            initial_state = {
                "active_services": {"haproxy": True},
                "wan_interface": "eth0",
                "rules_state": {
                    "rule-80": {
                        "active_priority": 1,
                        "destinations": {
                            "1": {"status": "healthy", "latency_ms": 14.5}
                        }
                    }
                }
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(initial_state, f)

            engine = XForwarderEngine(config_path=None, state_file_path=state_file)
            self.assertIn("rule-80", engine.rules_state)
            self.assertEqual(engine.rules_state["rule-80"]["destinations"]["1"]["latency_ms"], 14.5)

            # Save state
            engine._save_state_file()

            with open(state_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertIn("rule-80", saved.get("runtime", {}).get("rules_state", {}))
            self.assertEqual(saved["runtime"]["rules_state"]["rule-80"]["destinations"]["1"]["latency_ms"], 14.5)
        finally:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for f in files:
                    try:
                        os.remove(os.path.join(root, f))
                    except Exception:
                        pass
                try:
                    os.rmdir(root)
                except Exception:
                    pass

    def test_haproxy_generation_proxy_protocol_and_brackets(self):
        # Test sync_firewall_and_proxies generating haproxy entries
        self.engine.config["rules"] = [
            {
                "id": "rule-no-proxy",
                "port": 443,
                "protocol": "tcp",
                "active_priority": 1,
                "destinations": [
                    {"priority": 1, "type": "haproxy", "target": "[2a01:4f8::1]", "port": 443, "proxy_protocol": False}
                ]
            },
            {
                "id": "rule-with-proxy",
                "port": 8443,
                "protocol": "tcp",
                "active_priority": 1,
                "destinations": [
                    {"priority": 1, "type": "haproxy", "target": "1.2.3.4", "port": 8443, "proxy_protocol": True}
                ]
            }
        ]

        captured_haproxy = []
        def mock_apply_haproxy(haproxy_entries, udp_entries=None):
            captured_haproxy.extend(haproxy_entries)
            return True, None

        with patch.object(self.engine, "_detect_wan_interface", return_value="eth0"), \
             patch.object(self.engine, "_apply_nftables", return_value=(True, None)), \
             patch.object(self.engine, "_apply_haproxy", side_effect=mock_apply_haproxy), \
             patch.object(self.engine, "_apply_nginx", return_value=(True, None)), \
             patch.object(self.engine, "_save_state_file"):
            ok, errors = self.engine.sync_firewall_and_proxies()
            self.assertTrue(ok)
            self.assertEqual(len(errors), 0)

        self.assertEqual(len(captured_haproxy), 2)
        # 1. rule-no-proxy: no send-proxy-v2 and brackets stripped properly
        fwd_443 = next(e for e in captured_haproxy if "fwd_443" in e)
        self.assertNotIn("send-proxy-v2", fwd_443)
        self.assertIn("[2a01:4f8::1]:443", fwd_443)
        self.assertNotIn("[[", fwd_443)

        # 2. rule-with-proxy: has send-proxy-v2
        fwd_8443 = next(e for e in captured_haproxy if "fwd_8443" in e)
        self.assertIn("send-proxy-v2", fwd_8443)
        self.assertIn("1.2.3.4:8443", fwd_8443)


if __name__ == "__main__":
    unittest.main()

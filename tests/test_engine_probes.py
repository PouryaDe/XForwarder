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
            self.assertEqual(res["latency_ms"], 0.0)
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
            self.assertEqual(res["latency_ms"], 0.0)
            self.assertIn("routes via WAN (eth0)", res.get("reason", ""))
            self.assertIn("tunnel interface is not defined", res.get("reason", ""))

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
            self.assertEqual(res["latency_ms"], 0.0)
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
            self.assertEqual(res["latency_ms"], 0.0)
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


if __name__ == "__main__":
    unittest.main()

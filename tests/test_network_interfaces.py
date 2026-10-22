import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.web_server import (
    get_network_interfaces_info,
    ping_target,
    is_ignored_interface,
    DEFAULT_IGNORED_INTERFACES,
)


class TestNetworkInterfaces(unittest.TestCase):
    def test_ping_target_safety(self):
        # Disallowed characters / injection vectors must return False, None immediately
        self.assertEqual(ping_target("127.0.0.1; rm -rf /"), (False, None))
        self.assertEqual(ping_target("10.0.0.1 && cat /etc/passwd"), (False, None))
        self.assertEqual(ping_target("$(whoami)"), (False, None))
        self.assertEqual(ping_target(""), (False, None))

    def test_ignored_interfaces_filter(self):
        # Default Linux kernel fallback devices must be ignored
        kernel_fallbacks = [
            "lo",
            "gre0",
            "gretap0",
            "erspan0",
            "tunl0",
            "sit0",
            "ip6tnl0",
            "ip6gre0",
            "ip6erspan0",
            "dummy0",
            "teql0",
        ]
        for dev in kernel_fallbacks:
            self.assertTrue(
                is_ignored_interface(dev),
                f"Kernel fallback device {dev} should be ignored"
            )
            self.assertIn(dev, DEFAULT_IGNORED_INTERFACES)

        # Container and hypervisor bridge devices must be ignored
        container_bridges = ["docker0", "docker_gwbridge", "veth89a12b", "virbr0", "virbr0-nic", "br-1234567890ab"]
        for dev in container_bridges:
            self.assertTrue(
                is_ignored_interface(dev),
                f"Container/hypervisor bridge {dev} should be ignored"
            )

        # Empty / whitespace must be ignored
        self.assertTrue(is_ignored_interface(""))
        self.assertTrue(is_ignored_interface("   "))

        # Actual legitimate user tunnel interfaces and WAN NICs must NOT be ignored
        valid_interfaces = [
            "gre1",
            "gre2",
            "gretap1",
            "ipip1",
            "tunl1",
            "ftcp0",
            "ftcp1",
            "awg0",
            "awg1",
            "wg0",
            "eth0",
            "ens18",
            "enp3s0",
        ]
        for dev in valid_interfaces:
            self.assertFalse(
                is_ignored_interface(dev),
                f"Legitimate interface {dev} should NOT be ignored"
            )

    def test_get_network_interfaces_structure(self):
        res = get_network_interfaces_info()
        self.assertIsInstance(res, dict)
        self.assertIn("primary_interface", res)
        self.assertIn("server_ips", res)
        self.assertIn("tunnel_interfaces", res)
        self.assertIn("updated_at", res)

        self.assertIsInstance(res["server_ips"], list)
        self.assertIsInstance(res["tunnel_interfaces"], list)

        # Server IPs should have expected structure
        for s_ip in res["server_ips"]:
            self.assertIn("ip", s_ip)
            self.assertIn("version", s_ip)
            self.assertIn(s_ip["version"], (4, 6))
            self.assertIn("interface", s_ip)
            self.assertTrue(s_ip.get("is_primary"))

        # Tunnel interfaces (if any) should have expected structure
        for t_if in res["tunnel_interfaces"]:
            self.assertIn("name", t_if)
            self.assertIn("ip", t_if)
            self.assertIn("state", t_if)
            self.assertIn("type", t_if)
            self.assertIn("reachable", t_if)
            # Primary WAN interface must never be inside tunnel_interfaces!
            self.assertNotEqual(t_if["name"], res["primary_interface"])
            # Fallback devices and loopback must never be in tunnel_interfaces
            self.assertFalse(
                is_ignored_interface(t_if["name"]),
                f"Ignored interface {t_if['name']} found in tunnel_interfaces!"
            )

    def test_bilateral_peer_resolution(self):
        import json
        from unittest.mock import patch

        # 1. Iran VPS local IP .1 -> resolves foreign peer .2
        mock_if_iran = [{
            "ifname": "gre1",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "gre",
            "mtu": 1476,
            "addr_info": [{
                "family": "inet",
                "local": "10.81.15.1",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_iran)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            gre1 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "gre1"), None)
            self.assertIsNotNone(gre1)
            self.assertEqual(gre1["ip"], "10.81.15.1")
            self.assertEqual(gre1["peer_ip"], "10.81.15.2")
            self.assertEqual(gre1["target_to_ping"], "10.81.15.2")

        # 2. Foreign VPS local IP .2 -> resolves Iran peer .1
        mock_if_foreign = [{
            "ifname": "gre1",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "gre",
            "mtu": 1476,
            "addr_info": [{
                "family": "inet",
                "local": "10.81.15.2",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_foreign)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            gre1 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "gre1"), None)
            self.assertIsNotNone(gre1)
            self.assertEqual(gre1["ip"], "10.81.15.2")
            self.assertEqual(gre1["peer_ip"], "10.81.15.1")
            self.assertEqual(gre1["target_to_ping"], "10.81.15.1")

        # 3. Subnet /30 pairs (.5 <-> .6)
        mock_if_sub30 = [{
            "ifname": "gre2",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "gre",
            "mtu": 1476,
            "addr_info": [{
                "family": "inet",
                "local": "10.81.15.6",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_sub30)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            gre2 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "gre2"), None)
            self.assertIsNotNone(gre2)
            self.assertEqual(gre2["peer_ip"], "10.81.15.5")
            self.assertEqual(gre2["target_to_ping"], "10.81.15.5")

        # 4. Explicit peer configured in kernel overrides calculation
        mock_if_explicit = [{
            "ifname": "tun1",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "tun",
            "mtu": 1420,
            "addr_info": [{
                "family": "inet",
                "local": "10.81.15.1",
                "address": "10.81.15.99",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_explicit)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            tun1 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "tun1"), None)
            self.assertIsNotNone(tun1)
            self.assertEqual(tun1["peer_ip"], "10.81.15.99")
            self.assertEqual(tun1["target_to_ping"], "10.81.15.99")

        # 5. Configured rule target matching /24 takes precedence over default bilateral calculation
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_iran)), \
             patch("core.web_server.load_config", return_value={
                 "wan_interface": "eth0",
                 "rules": [{"destinations": [{"target": "10.81.15.88"}]}]
             }), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            gre1 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "gre1"), None)
            self.assertIsNotNone(gre1)
            self.assertEqual(gre1["peer_ip"], "10.81.15.88")
            self.assertEqual(gre1["target_to_ping"], "10.81.15.88")

        # 6. Non point-to-point host (e.g. .100) without known target remains unpeered
        mock_if_other = [{
            "ifname": "gre3",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "gre",
            "mtu": 1476,
            "addr_info": [{
                "family": "inet",
                "local": "10.81.15.100",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_other)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            gre3 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "gre3"), None)
            self.assertIsNotNone(gre3)
            self.assertEqual(gre3["peer_ip"], "")
            self.assertEqual(gre3["target_to_ping"], "")

        # 7. IPv6 bilateral pairs (::1 <-> ::2)
        mock_if_ipv6 = [{
            "ifname": "gre6",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "gre",
            "mtu": 1476,
            "addr_info": [{
                "family": "inet6",
                "local": "fd00:81:15::1",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_ipv6)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            gre6 = next((t for t in info.get("tunnel_interfaces", []) if t["name"] == "gre6"), None)
            self.assertIsNotNone(gre6)
            self.assertEqual(gre6["peer_ip"], "fd00:81:15::2")
            self.assertEqual(gre6["target_to_ping"], "fd00:81:15::2")


if __name__ == "__main__":
    unittest.main()

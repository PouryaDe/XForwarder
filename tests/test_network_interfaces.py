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

    def test_no_synthetic_peer_guessing(self):
        import json
        from unittest.mock import patch
        mock_if_data = [{
            "ifname": "gre1",
            "flags": ["UP"],
            "operstate": "UP",
            "link_type": "gre",
            "mtu": 1476,
            "addr_info": [{
                "family": "inet",
                "local": "10.88.1.1",
                "scope": "global"
            }]
        }]
        with patch("sys.platform", "linux"), \
             patch("subprocess.check_output", return_value=json.dumps(mock_if_data)), \
             patch("core.web_server.load_config", return_value={"wan_interface": "eth0", "rules": []}), \
             patch.dict("core.web_server._NET_CACHE", {"data": None, "expires": 0}):
            info = get_network_interfaces_info()
            tunnels = info.get("tunnel_interfaces", [])
            gre1 = next((t for t in tunnels if t["name"] == "gre1"), None)
            self.assertIsNotNone(gre1)
            self.assertEqual(gre1["ip"], "10.88.1.1")
            self.assertEqual(gre1["peer_ip"], "")
            # target_to_ping must be empty, NOT guessed 10.88.1.2!
            self.assertEqual(gre1["target_to_ping"], "")


if __name__ == "__main__":
    unittest.main()

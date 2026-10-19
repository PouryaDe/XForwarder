import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.web_server import get_network_interfaces_info, ping_target


class TestNetworkInterfaces(unittest.TestCase):
    def test_ping_target_safety(self):
        # Disallowed characters / injection vectors must return False, None immediately
        self.assertEqual(ping_target("127.0.0.1; rm -rf /"), (False, None))
        self.assertEqual(ping_target("10.0.0.1 && cat /etc/passwd"), (False, None))
        self.assertEqual(ping_target("$(whoami)"), (False, None))
        self.assertEqual(ping_target(""), (False, None))

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
            self.assertNotEqual(t_if["name"], "lo")


if __name__ == "__main__":
    unittest.main()

import unittest
import sys
import os
import json
import tempfile
import time

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.web_server import load_config, save_config, get_config_path, export_config_data, import_config_data


class TestExportImport(unittest.TestCase):
    def setUp(self):
        # Create a temporary config file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.orig_config_path = os.environ.get("XFWD_CONFIG_PATH")
        self.test_cfg_path = os.path.join(self.temp_dir, "config.json")
        os.environ["XFWD_CONFIG_PATH"] = self.test_cfg_path

        self.initial_data = {
            "schema_version": 2,
            "wan_interface": "eth0",
            "check_interval_seconds": 8,
            "web": {
                "port": 8090,
                "secret_path": "xfwd-admin",
                "auth": {
                    "username": "admin",
                    "password_hash": "dummy_pbkdf2_hash_to_preserve"
                }
            },
            "rules": [
                {
                    "id": "rule-1080",
                    "port": 1080,
                    "protocol": "both",
                    "active_priority": 1,
                    "destinations": [
                        {"priority": 1, "type": "haproxy", "target": "2001:cafe::1", "port": 1080}
                    ]
                }
            ]
        }
        with open(self.test_cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f)

    def tearDown(self):
        if self.orig_config_path:
            os.environ["XFWD_CONFIG_PATH"] = self.orig_config_path
        elif "XFWD_CONFIG_PATH" in os.environ:
            del os.environ["XFWD_CONFIG_PATH"]

        # Clean up temp files
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass
        try:
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_export_sanitization(self):
        export_data = export_config_data()
        # Credentials must NEVER be exported in backup
        self.assertNotIn("web", export_data)
        self.assertNotIn("auth", export_data)
        self.assertEqual(len(export_data["rules"]), 1)
        self.assertEqual(export_data["rules"][0]["port"], 1080)
        self.assertEqual(export_data["wan_interface"], "eth0")

    def test_import_merge_mode(self):
        import_payload = {
            "rules": [
                {
                    "id": "rule-2083",
                    "port": 2083,
                    "protocol": "tcp",
                    "active_priority": 1,
                    "destinations": [
                        {"priority": 1, "type": "haproxy", "target": "2001:cafe::2", "port": 2083}
                    ]
                }
            ]
        }

        ok, err, info = import_config_data(import_payload, mode="merge")
        self.assertTrue(ok)
        self.assertEqual(err, "")
        self.assertEqual(info["imported_count"], 1)
        self.assertEqual(info["count"], 2)
        self.assertTrue(info["backup"].startswith("config.json.bak."))

        reloaded = load_config()
        ports = [r["port"] for r in reloaded["rules"]]
        self.assertIn(1080, ports)
        self.assertIn(2083, ports)
        self.assertEqual(len(ports), 2)
        # Verify credentials preserved!
        self.assertEqual(reloaded["web"]["auth"]["password_hash"], "dummy_pbkdf2_hash_to_preserve")
        self.assertEqual(reloaded["web"]["port"], 8090)

    def test_import_replace_mode(self):
        import_payload = {
            "wan_interface": "eth1",
            "check_interval_seconds": 10,
            "rules": [
                {
                    "id": "rule-443",
                    "port": 443,
                    "protocol": "both",
                    "active_priority": 1,
                    "destinations": [
                        {"priority": 1, "type": "haproxy", "target": "2001:cafe::443", "port": 443}
                    ]
                }
            ]
        }

        ok, err, info = import_config_data(import_payload, mode="replace")
        self.assertTrue(ok)
        self.assertEqual(info["count"], 1)

        reloaded = load_config()
        ports = [r["port"] for r in reloaded["rules"]]
        self.assertEqual(ports, [443])
        self.assertEqual(reloaded["wan_interface"], "eth1")
        self.assertEqual(reloaded["check_interval_seconds"], 10)
        # Verify admin credentials & panel port preserved even after replace!
        self.assertEqual(reloaded["web"]["auth"]["password_hash"], "dummy_pbkdf2_hash_to_preserve")
        self.assertEqual(reloaded["web"]["port"], 8090)

    def test_import_validation_edge_cases(self):
        # Invalid payload type
        ok, err, _ = import_config_data("not a dict")
        self.assertFalse(ok)
        self.assertIn("JSON object", err)

        # Invalid port number
        invalid_port_payload = {
            "rules": [{"port": 999999, "destinations": [{"priority": 1, "target": "1.1.1.1", "port": 80}]}]
        }
        ok, err, _ = import_config_data(invalid_port_payload)
        self.assertFalse(ok)
        self.assertIn("Invalid port", err)

        # Duplicate ports in payload
        dup_payload = {
            "rules": [
                {"port": 80, "destinations": [{"priority": 1, "target": "1.1.1.1", "port": 80}]},
                {"port": 80, "destinations": [{"priority": 1, "target": "2.2.2.2", "port": 80}]}
            ]
        }
        ok, err, _ = import_config_data(dup_payload)
        self.assertFalse(ok)
        self.assertIn("Duplicate port", err)


if __name__ == "__main__":
    unittest.main()


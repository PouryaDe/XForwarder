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

    def test_import_reserved_web_port_rejected(self):
        # Attempting to import rule on web dashboard port (8090) must be rejected
        payload = {
            "rules": [
                {"port": 8090, "destinations": [{"priority": 1, "target": "1.1.1.1", "port": 8090}]}
            ]
        }
        ok, err, _ = import_config_data(payload)
        self.assertFalse(ok)
        self.assertIn("reserved for the XForwarder Web Dashboard", err)

    def test_import_raw_rules_list(self):
        # Top-level array of rules should be accepted seamlessly
        raw_list = [
            {
                "port": 3000,
                "protocol": "tcp",
                "destinations": [{"priority": 1, "target": "1.2.3.4", "port": 3000}]
            }
        ]
        ok, err, info = import_config_data(raw_list, mode="merge")
        self.assertTrue(ok)
        self.assertEqual(info["imported_count"], 1)

        reloaded = load_config()
        ports = [r["port"] for r in reloaded["rules"]]
        self.assertIn(3000, ports)

    def test_missing_id_and_priority_auto_assigned(self):
        # Rules missing 'id' or 'active_priority' should be normalized
        payload = {
            "rules": [
                {
                    "port": 9090,
                    "destinations": [{"priority": 1, "target": "1.2.3.4", "port": 9090}]
                }
            ]
        }
        ok, err, info = import_config_data(payload, mode="merge")
        self.assertTrue(ok)

        reloaded = load_config()
        rule = next(r for r in reloaded["rules"] if r["port"] == 9090)
        self.assertEqual(rule["id"], "rule-9090")
        self.assertEqual(rule["active_priority"], 1)

    def test_atomic_backup_integrity(self):
        # Verify pre-import backup file is created atomically and is valid JSON
        payload = {
            "rules": [
                {"port": 5000, "destinations": [{"priority": 1, "target": "1.2.3.4", "port": 5000}]}
            ]
        }
        ok, _, info = import_config_data(payload, mode="merge")
        self.assertTrue(ok)

        backup_filename = info["backup"]
        backup_path = os.path.join(self.temp_dir, backup_filename)
        self.assertTrue(os.path.exists(backup_path))

        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        self.assertIn("rules", backup_data)
        # Pre-import state only had port 1080
        self.assertEqual([r["port"] for r in backup_data["rules"]], [1080])

    def test_http_export_endpoint(self):
        # End-to-end HTTP test ensuring do_GET /api/config/export applies headers and returns valid JSON
        import threading
        import urllib.request
        from http.server import HTTPServer
        from core.web_server import XForwarderWebHandler, ACTIVE_SESSIONS, SESSION_LOCK

        server = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        port = server.server_port
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        token = "test_e2e_export_token"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[token] = {
                "username": "admin",
                "created_at": time.time(),
                "last_active": time.time(),
                "expires_at": time.time() + 3600
            }

        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/config/export")
            req.add_header("Cookie", f"xfwd_session={token}")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                disp = resp.headers.get("Content-Disposition", "")
                self.assertTrue("attachment;" in disp and "xforwarder-backup-" in disp)
                # Verify OWASP headers applied cleanly
                self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")
                self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body["wan_interface"], "eth0")
                self.assertEqual(body["rules"][0]["port"], 1080)
                self.assertNotIn("web", body)
        finally:
            server.server_close()


    def test_import_single_rule_dict(self):
        # A single rule dictionary (without "rules" array wrapper) should be accepted seamlessly
        single_rule = {
            "name": "Single Port Service",
            "port": 4040,
            "protocol": "both",
            "category": "Custom",
            "destinations": [{"priority": 1, "target": "2001:cafe::4040", "port": 4040}]
        }
        ok, err, info = import_config_data(single_rule, mode="merge")
        self.assertTrue(ok)
        self.assertEqual(info["imported_count"], 1)

        reloaded = load_config()
        ports = [r["port"] for r in reloaded["rules"]]
        self.assertIn(4040, ports)
        rule_4040 = next(r for r in reloaded["rules"] if r["port"] == 4040)
        self.assertEqual(rule_4040["category"], "Custom")


if __name__ == "__main__":
    unittest.main()



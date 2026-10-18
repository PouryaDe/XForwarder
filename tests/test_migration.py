#!/usr/bin/env python3
"""
Unit tests for XForwarder Configuration Migration & Backward Compatibility.
Standard Library unittest only.
"""

import os
import sys
import json
import unittest
import tempfile
import subprocess

# Ensure repo root and core are in python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.engine import XForwarderEngine
from core.web_server import load_config, save_config, get_config_path


class TestXForwarderMigration(unittest.TestCase):

    def test_migrate_v1_legacy_config(self):
        """Verifies that an unversioned legacy v1 configuration is safely migrated to v2."""
        legacy_cfg = {
            "wan_interface": "eth0",
            "web": {
                "port": "8090",
                "secret_path": "xfwd-admin",
                "auth": {
                    "username": "custom_admin",
                    "password_hash": "existing_hash_123"
                }
            },
            "rules": [
                {
                    "port": "2083",
                    "protocol": "TCP",
                    "destinations": [
                        {
                            "priority": "1",
                            "target": "2a01:4f8:cafe::1",
                            "comment": "IPv6 Node"
                        },
                        {
                            "priority": "2",
                            "target": "10.88.0.2",
                            "comment": "Internal Tunnel"
                        }
                    ]
                }
            ]
        }

        migrated, modified = XForwarderEngine.migrate_and_normalize_config(legacy_cfg)

        self.assertTrue(modified)
        self.assertEqual(migrated.get("schema_version"), 2)
        self.assertEqual(migrated["wan_interface"], "eth0")
        self.assertEqual(migrated["check_interval_seconds"], 8)
        self.assertEqual(migrated["web"]["bind_host"], "0.0.0.0")
        self.assertEqual(migrated["web"]["port"], 8090)
        self.assertEqual(migrated["web"]["auth"]["username"], "custom_admin")
        self.assertEqual(migrated["web"]["auth"]["password_hash"], "existing_hash_123")

        # Rules verification
        rules = migrated.get("rules", [])
        self.assertEqual(len(rules), 1)
        r0 = rules[0]
        self.assertEqual(r0["port"], 2083)
        self.assertEqual(r0["id"], "rule-2083")
        self.assertEqual(r0["protocol"], "tcp")
        self.assertEqual(r0["active_priority"], 1)
        self.assertEqual(r0["force_override"], 0)

        # Destinations verification
        dests = r0["destinations"]
        self.assertEqual(len(dests), 2)
        self.assertEqual(dests[0]["type"], "haproxy")
        self.assertEqual(dests[0]["port"], 2083)
        self.assertEqual(dests[0]["priority"], 1)
        self.assertEqual(dests[1]["type"], "nftables")
        self.assertEqual(dests[1]["port"], 2083)
        self.assertEqual(dests[1]["priority"], 2)

    def test_migration_nginx_type_preserved(self):
        """Verifies that modern destination types like Nginx are fully preserved."""
        cfg = {
            "schema_version": 2,
            "rules": [
                {
                    "port": 443,
                    "destinations": [
                        {
                            "priority": 1,
                            "type": "nginx",
                            "target": "2a01:cafe::2",
                            "port": 443
                        }
                    ]
                }
            ]
        }
        migrated, modified = XForwarderEngine.migrate_and_normalize_config(cfg)
        self.assertEqual(migrated["rules"][0]["destinations"][0]["type"], "nginx")

    def test_migration_idempotence(self):
        """Verifies that running migration repeatedly produces zero further modifications."""
        raw_cfg = {
            "rules": [
                {
                    "port": "80",
                    "destinations": [
                        {"target": "1.1.1.1"}
                    ]
                }
            ]
        }
        pass1, mod1 = XForwarderEngine.migrate_and_normalize_config(raw_cfg)
        self.assertTrue(mod1)

        pass2, mod2 = XForwarderEngine.migrate_and_normalize_config(pass1)
        self.assertFalse(mod2)
        self.assertEqual(pass1, pass2)

    def test_corrupted_and_empty_inputs(self):
        """Verifies graceful self-healing when encountering malformed or empty config dictionaries."""
        migrated, modified = XForwarderEngine.migrate_and_normalize_config({})
        self.assertTrue(modified)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertIn("web", migrated)
        self.assertIn("rules", migrated)
        self.assertEqual(migrated["web"]["port"], 8090)

    def test_engine_save_and_relative_path(self):
        """Verifies that atomic file persistence handles relative paths and new directories safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_cfg = os.path.join(tmpdir, "nested", "config.json")
            engine = XForwarderEngine(config_path=target_cfg)
            self.assertTrue(engine.save_config())
            self.assertTrue(os.path.exists(target_cfg))

            # Verify persisted data
            with open(target_cfg, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded.get("schema_version"), 2)

    def test_cli_migrate_flag(self):
        """Verifies the --migrate CLI entry point in core/engine.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_legacy.json")
            legacy_data = {
                "rules": [
                    {"port": "5000", "destinations": [{"target": "2a01::5"}]}
                ]
            }
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            engine_py = os.path.join(REPO_ROOT, "core", "engine.py")
            res = subprocess.run([sys.executable, engine_py, "--migrate", test_file],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.assertEqual(res.returncode, 0)
            self.assertIn("[OK] Configuration migrated and normalized successfully", res.stdout)
            self.assertIn("Preserved 1 port forwarding rule(s)", res.stdout)

            with open(test_file, "r", encoding="utf-8") as f:
                upgraded = json.load(f)
            self.assertEqual(upgraded["schema_version"], 2)
            self.assertEqual(upgraded["rules"][0]["port"], 5000)


if __name__ == "__main__":
    unittest.main()

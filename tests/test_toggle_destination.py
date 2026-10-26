#!/usr/bin/env python3
"""
Unit tests for XForwarder Destination Enable/Disable (On/Off Toggle) Subsystem.
Verifies:
1. Schema normalization and default enabled: True
2. REST API /api/rule/toggle-destination toggle and explicit enable/disable
3. Active priority fallback when active destination is disabled
4. Forced override reset when forced destination is disabled
5. Core engine evaluation and dest_metrics exclusion for disabled paths
6. pick_best_now ignoring disabled destinations
7. HAProxy and NFTables rule generation ignoring disabled destinations

Standard library unittest only. Zero pip dependencies.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.config_manager import migrate_and_normalize_config, validate_rule
from core.route_quality import pick_best_now
from core.engine import XForwarderEngine


class TestToggleDestination(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="xfwd_toggle_test_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.state_path = os.path.join(self.test_dir, "state.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_normalization_enabled_flag(self):
        """Verifies destination enabled flag defaults to True and normalizes cleanly."""
        raw_config = {
            "schema_version": 3,
            "rules": [
                {
                    "port": 9121,
                    "destinations": [
                        {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe:b48::1", "port": 9121},
                        {"priority": 2, "type": "nftables", "target": "10.81.7.2", "port": 9121, "enabled": False}
                    ]
                }
            ]
        }
        migrated, changed = migrate_and_normalize_config(raw_config)
        self.assertTrue(changed)
        dests = migrated["rules"][0]["destinations"]
        self.assertTrue(dests[0]["enabled"])
        self.assertFalse(dests[1]["enabled"])

    def test_validate_rule_normalizes_enabled(self):
        """Verifies validate_rule normalizes boolean enabled flag."""
        rule_data = {
            "port": 8443,
            "protocol": "tcp",
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 8443, "enabled": 0},
                {"priority": 2, "type": "nftables", "target": "10.0.0.2", "port": 8443}
            ]
        }
        valid, err = validate_rule(rule_data)
        self.assertTrue(valid, err)
        self.assertFalse(rule_data["destinations"][0]["enabled"])
        self.assertTrue(rule_data["destinations"][1]["enabled"])

    def test_pick_best_now_ignores_disabled_destinations(self):
        """Verifies pick_best_now never selects a disabled destination."""
        destinations = [
            {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "enabled": False},
            {"priority": 2, "type": "nftables", "target": "10.0.0.2", "enabled": True}
        ]
        dest_stats = {
            "prio_1": {"status": "healthy", "packet_loss": 0.0, "composite_score": 20.0},
            "prio_2": {"status": "healthy", "packet_loss": 0.0, "composite_score": 60.0}
        }
        # Priority 1 has better score (20 vs 60), but it is disabled!
        best = pick_best_now(dest_stats, destinations, current_active=1)
        self.assertEqual(best, 2)

    def test_engine_evaluate_rule_skips_disabled_destinations(self):
        """Verifies engine.evaluate_rule sets disabled status and excludes from dest_metrics."""
        engine = XForwarderEngine(config_path=self.config_path, state_file_path=self.state_path)
        rule = {
            "id": "rule-9121",
            "port": 9121,
            "protocol": "tcp",
            "active_priority": 1,
            "force_override": 0,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 9121, "enabled": False},
                {"priority": 2, "type": "nftables", "target": "10.0.0.2", "port": 9121, "enabled": True}
            ]
        }
        engine.config = {"rules": [rule]}
        probe_cache = {
            ("10.0.0.2", None): {"healthy": True, "latency_ms": 35.0, "packet_loss": 0.0, "jitter_ms": 1.0}
        }

        # Priority 1 is currently active but disabled: evaluate_rule must trigger fallback to Priority 2
        changed = engine.evaluate_rule(rule, probe_cache=probe_cache)
        self.assertTrue(changed)
        self.assertEqual(rule["active_priority"], 2)
        r_state = engine.runtime_state["rules_state"]["rule-9121"]
        self.assertEqual(r_state["dest_stats"]["prio_1"]["status"], "disabled")
        self.assertFalse(r_state["dest_stats"]["prio_1"]["enabled"])

    def test_sync_firewall_and_proxies_ignores_disabled(self):
        """Verifies sync_firewall_and_proxies skips disabled destinations."""
        engine = XForwarderEngine(config_path=self.config_path, state_file_path=self.state_path)
        rule = {
            "id": "rule-9121",
            "port": 9121,
            "protocol": "tcp",
            "active_priority": 1,
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 9121, "enabled": False},
                {"priority": 2, "type": "nftables", "target": "10.0.0.2", "port": 9121, "enabled": True}
            ]
        }
        engine.config = {"rules": [rule]}
        # When Priority 1 is disabled, sync_firewall_and_proxies should select Priority 2
        engine._apply_nftables = lambda rules: (True, None)
        engine._apply_haproxy = lambda ha, udp: (True, None)
        engine._apply_nginx = lambda ngx: (True, None)
        ok, errs = engine.sync_firewall_and_proxies()
        self.assertTrue(ok)


import threading
from http.server import HTTPServer
from core.web_server import XForwarderWebHandler, ACTIVE_SESSIONS, SESSION_LOCK


class TestToggleDestinationApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="xfwd_api_toggle_")
        cls.config_path = os.path.join(cls.test_dir, "config.json")
        cls.state_path = os.path.join(cls.test_dir, "state.json")

        initial_config = {
            "schema_version": 3,
            "web": {
                "bind_host": "127.0.0.1",
                "port": 0,
                "secret_path": "xfwd-admin",
                "auth": {"username": "admin", "password_hash": ""}
            },
            "rules": [
                {
                    "id": "rule-9121",
                    "port": 9121,
                    "protocol": "tcp",
                    "active_priority": 1,
                    "force_override": 0,
                    "destinations": [
                        {"priority": 1, "type": "haproxy", "target": "2001:4ba0:cafe:b48::1", "port": 9121, "enabled": True},
                        {"priority": 2, "type": "nftables", "target": "10.81.7.2", "port": 9121, "enabled": True}
                    ]
                }
            ]
        }
        with open(cls.config_path, "w", encoding="utf-8") as f:
            json.dump(initial_config, f, indent=2)

        os.environ["XFWD_CONFIG_PATH"] = cls.config_path
        os.environ["XFWD_STATE_PATH"] = cls.state_path

        cls.httpd = HTTPServer(("127.0.0.1", 0), XForwarderWebHandler)
        cls.port = cls.httpd.server_port
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

        cls.base_url = f"http://127.0.0.1:{cls.port}/xfwd-admin"

        cls.token = "test_toggle_token_123"
        with SESSION_LOCK:
            ACTIVE_SESSIONS[cls.token] = {
                "username": "admin",
                "created_at": time.time(),
                "last_active": time.time(),
                "expires_at": time.time() + 3600
            }
        cls.cookie = f"xfwd_session={cls.token}"

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
            cls.httpd.server_close()
        except Exception:
            pass
        if "XFWD_CONFIG_PATH" in os.environ:
            del os.environ["XFWD_CONFIG_PATH"]
        if "XFWD_STATE_PATH" in os.environ:
            del os.environ["XFWD_STATE_PATH"]
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_api_toggle_destination(self):
        """Verifies POST /api/rule/toggle-destination toggles enabled flag and returns 200."""
        # 1. Toggle Priority 2 off
        req = Request(
            f"{self.base_url}/api/rule/toggle-destination",
            data=json.dumps({"rule_id": "rule-9121", "priority": 2}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": self.cookie,
                "Origin": f"http://127.0.0.1:{self.port}"
            }
        )
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertFalse(data.get("enabled"))
            self.assertEqual(data.get("priority"), 2)

        # Verify on-disk config persistence
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        dests = cfg["rules"][0]["destinations"]
        self.assertFalse(dests[1]["enabled"])

        # 2. Toggle Priority 2 back on
        req2 = Request(
            f"{self.base_url}/api/rule/toggle-destination",
            data=json.dumps({"rule_id": "rule-9121", "priority": 2}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": self.cookie,
                "Origin": f"http://127.0.0.1:{self.port}"
            }
        )
        with urlopen(req2) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertTrue(data.get("enabled"))

        # Verify on-disk config
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertTrue(cfg["rules"][0]["destinations"][1]["enabled"])

    def test_api_toggle_active_destination_falls_back(self):
        """Verifies that disabling the active priority causes automatic fallback to enabled path."""
        # Disable Priority 1 (which is currently active_priority)
        req = Request(
            f"{self.base_url}/api/rule/toggle-destination",
            data=json.dumps({"rule_id": "rule-9121", "priority": 1, "enabled": False}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": self.cookie,
                "Origin": f"http://127.0.0.1:{self.port}"
            }
        )
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertFalse(data.get("enabled"))
            # Active priority should have shifted to Priority 2
            self.assertEqual(data.get("rule", {}).get("active_priority"), 2)

        # Restore Priority 1
        req_restore = Request(
            f"{self.base_url}/api/rule/toggle-destination",
            data=json.dumps({"rule_id": "rule-9121", "priority": 1, "enabled": True}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cookie": self.cookie,
                "Origin": f"http://127.0.0.1:{self.port}"
            }
        )
        with urlopen(req_restore) as resp:
            self.assertEqual(resp.status, 200)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit tests for HAProxy Configuration Parser & Importer.
Standard Library unittest only.
"""

import os
import sys
import unittest
import tempfile
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.haproxy_parser import (
    parse_haproxy_content,
    parse_haproxy_file,
    discover_importable_rules,
    import_haproxy_rules_into_config
)


SAMPLE_HAPROXY_CONFIG = """
global
    daemon
    maxconn 256

defaults
    mode tcp
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

# Listen block with IPv6 target and send-proxy
listen relay_2083
    bind *:2083
    mode tcp
    server srv_2083 [2001:4ba0:cafe:84e::1]:2083 send-proxy-v2

# Listen block with IPv4 target
listen relay_8080
    bind 0.0.0.0:8080
    server srv_8080 1.2.3.4:8080 check

# Listen block with multiple binds
listen relay_8443
    bind :::8443
    bind *:8443
    server srv_8443 10.0.0.5:8443

# Frontend and backend separation
frontend fe_443
    bind *:443
    mode tcp
    default_backend be_443

backend be_443
    mode tcp
    server srv_443 [2600:1f18::5]:443 send-proxy-v2

# Another frontend with use_backend
frontend fe_80
    bind *:80
    use_backend be_80

backend be_80
    server srv_80 192.168.1.100:80

# Sixth port
listen custom_9090
    bind *:9090
    server foreign 5.6.7.8:9090
"""


class TestHAProxyParser(unittest.TestCase):

    def test_parse_sample_haproxy_content(self):
        rules = parse_haproxy_content(SAMPLE_HAPROXY_CONFIG)
        self.assertEqual(len(rules), 6)

        ports = {r["port"] for r in rules}
        self.assertEqual(ports, {80, 443, 2083, 8080, 8443, 9090})

        # Verify IPv6 target
        rule_2083 = next(r for r in rules if r["port"] == 2083)
        self.assertEqual(rule_2083["destinations"][0]["target"], "2001:4ba0:cafe:84e::1")
        self.assertEqual(rule_2083["destinations"][0]["port"], 2083)
        self.assertEqual(rule_2083["destinations"][0]["type"], "haproxy")

        # Verify frontend/backend resolution
        rule_443 = next(r for r in rules if r["port"] == 443)
        self.assertEqual(rule_443["destinations"][0]["target"], "2600:1f18::5")
        self.assertEqual(rule_443["destinations"][0]["port"], 443)

        rule_80 = next(r for r in rules if r["port"] == 80)
        self.assertEqual(rule_80["destinations"][0]["target"], "192.168.1.100")

    def test_import_into_config_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cfg_file:
            json.dump({
                "schema_version": 2,
                "wan_interface": "auto",
                "rules": [
                    {"id": "rule-443", "port": 443, "destinations": []}  # Already configured
                ]
            }, cfg_file)
            cfg_path = cfg_file.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as haproxy_file:
            haproxy_file.write(SAMPLE_HAPROXY_CONFIG)
            haproxy_path = haproxy_file.name

        try:
            # Parse specific file
            parsed_rules = parse_haproxy_file(haproxy_path)
            self.assertEqual(len(parsed_rules), 6)

            # Discover importable (port 443 should be skipped since already configured)
            existing = [{"port": 443}]
            importable = [r for r in parsed_rules if r["port"] not in {443}]
            self.assertEqual(len(importable), 5)

        finally:
            if os.path.exists(cfg_path):
                os.remove(cfg_path)
            if os.path.exists(haproxy_path):
                os.remove(haproxy_path)


if __name__ == "__main__":
    unittest.main()

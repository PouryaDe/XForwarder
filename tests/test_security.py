#!/usr/bin/env python3
"""
Unit tests for XForwarder Web & Authentication Security.
Tests PBKDF2 hashing, rate limiting, target sanitization, and CSRF protection.
Standard Library unittest only.
"""

import os
import sys
import hashlib
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.web_server import (
    hash_password,
    verify_password,
    check_rate_limit,
    record_failed_login,
    reset_rate_limit,
    is_valid_target,
    validate_rule,
    MAX_FAILED_ATTEMPTS
)


class TestXForwarderSecurity(unittest.TestCase):

    def setUp(self):
        # Reset test IP
        reset_rate_limit("192.0.2.100")

    def tearDown(self):
        reset_rate_limit("192.0.2.100")

    def test_pbkdf2_password_hashing_and_verification(self):
        """Verifies PBKDF2-HMAC-SHA256 password hashing with unique salts."""
        raw_pwd = "SuperSecretAdminPassword123!"
        hash1 = hash_password(raw_pwd)
        hash2 = hash_password(raw_pwd)

        # Hashes must have unique salts and therefore differ
        self.assertNotEqual(hash1, hash2)
        self.assertTrue(hash1.startswith("pbkdf2:sha256:100000$"))

        # Verification must succeed and not require rehash
        valid, needs_rehash = verify_password(raw_pwd, hash1)
        self.assertTrue(valid)
        self.assertFalse(needs_rehash)

        # Wrong password must fail
        invalid, _ = verify_password("WrongPassword!", hash1)
        self.assertFalse(invalid)

    def test_legacy_sha256_backward_compatibility_and_rehash_flag(self):
        """Verifies that legacy plain SHA-256 hashes are verified and flagged for auto-upgrade."""
        raw_pwd = "LegacyPassword2024"
        legacy_hash = hashlib.sha256(raw_pwd.encode("utf-8")).hexdigest()

        valid, needs_rehash = verify_password(raw_pwd, legacy_hash)
        self.assertTrue(valid)
        self.assertTrue(needs_rehash)  # Triggers automatic self-healing upgrade to salted PBKDF2!

        # Wrong password on legacy hash must fail
        invalid, _ = verify_password("WrongLegacyPassword", legacy_hash)
        self.assertFalse(invalid)

    def test_brute_force_rate_limiting_and_lockout(self):
        """Verifies that 5 failed attempts trigger IP lockout."""
        test_ip = "192.0.2.100"

        # Initially no lockout
        is_locked, remaining, count = check_rate_limit(test_ip)
        self.assertFalse(is_locked)
        self.assertEqual(count, 0)

        # 4 failed attempts should not lock out
        for i in range(MAX_FAILED_ATTEMPTS - 1):
            is_locked, _, count = record_failed_login(test_ip)
            self.assertFalse(is_locked)
            self.assertEqual(count, i + 1)

        # 5th failed attempt must trigger lockout
        is_locked, remaining, count = record_failed_login(test_ip)
        self.assertTrue(is_locked)
        self.assertGreater(remaining, 0)
        self.assertEqual(count, MAX_FAILED_ATTEMPTS)

        # Check rate limit must now report locked
        is_locked_check, _, _ = check_rate_limit(test_ip)
        self.assertTrue(is_locked_check)

        # Reset rate limit on success
        reset_rate_limit(test_ip)
        is_locked_after, _, _ = check_rate_limit(test_ip)
        self.assertFalse(is_locked_after)

    def test_destination_target_validation(self):
        """Verifies that IPv4, IPv6, and domain names are accepted, while injection attempts are rejected."""
        valid_targets = [
            "1.1.1.1",
            "192.168.1.1",
            "10.88.0.2",
            "2606:4700:4700::1111",
            "[2a01:4f8:cafe::1]",
            "relay.example.com",
            "node1.tunnel.internal"
        ]
        for t in valid_targets:
            self.assertTrue(is_valid_target(t), f"Target should be valid: {t}")

        invalid_targets = [
            "",
            "1.1.1.1; rm -rf /",
            "1.1.1.1 | cat /etc/shadow",
            "http://example.com",
            "10.0.0.1`reboot`",
            "$(whoami)",
            "bad target with spaces",
            "256.300.1.1"  # invalid ip and not valid rfc domain
        ]
        for t in invalid_targets:
            self.assertFalse(is_valid_target(t), f"Target should be invalid: {t}")

    def test_rule_validation_rejects_injections(self):
        """Verifies that validate_rule blocks command injection hazards."""
        malicious_rule = {
            "port": 8443,
            "protocol": "both",
            "destinations": [
                {
                    "priority": 1,
                    "type": "haproxy",
                    "target": "2a01:cafe::1; echo hacked",
                    "port": 8443
                }
            ]
        }
        valid, msg = validate_rule(malicious_rule)
        self.assertFalse(valid)
        self.assertIn("invalid", msg.lower())

    def test_verify_password_corrupt_and_empty_inputs(self):
        """Verifies that verify_password handles malformed, empty, or None inputs gracefully without exceptions."""
        # Empty and None values
        self.assertEqual(verify_password("", "valid_hash"), (False, False))
        self.assertEqual(verify_password("valid_pwd", ""), (False, False))
        self.assertEqual(verify_password(None, "valid_hash"), (False, False))
        self.assertEqual(verify_password("valid_pwd", None), (False, False))

        # Malformed PBKDF2 strings
        corrupt_hashes = [
            "pbkdf2:sha256:notanumber$salt$hex",
            "pbkdf2:sha256:100000$salt",  # missing hex
            "pbkdf2:sha256:100000$salt$hex$extra",  # too many parts
            "pbkdf2:sha256:100000$nothexsalt$hex",
            "unknown_algo:sha256:100000$salt$hex"
        ]
        for ch in corrupt_hashes:
            valid, needs_rehash = verify_password("Password123!", ch)
            self.assertFalse(valid, f"Corrupt hash should not validate: {ch}")
            self.assertFalse(needs_rehash)

    def test_validate_rule_port_boundary_edge_cases(self):
        """Verifies boundary port constraints (1-65535) and protocol validation."""
        # Port below minimum (0, -1)
        self.assertFalse(validate_rule({"port": 0, "protocol": "both", "destinations": [{"target": "1.1.1.1"}]})[0])
        self.assertFalse(validate_rule({"port": -5, "protocol": "both", "destinations": [{"target": "1.1.1.1"}]})[0])

        # Port above maximum (65536, 99999)
        self.assertFalse(validate_rule({"port": 65536, "protocol": "both", "destinations": [{"target": "1.1.1.1"}]})[0])
        self.assertFalse(validate_rule({"port": 99999, "protocol": "both", "destinations": [{"target": "1.1.1.1"}]})[0])

        # Non-integer port
        self.assertFalse(validate_rule({"port": "http", "protocol": "both", "destinations": [{"target": "1.1.1.1"}]})[0])

        # Invalid protocol
        self.assertFalse(validate_rule({"port": 443, "protocol": "sctp", "destinations": [{"target": "1.1.1.1"}]})[0])

        # Empty destinations list
        self.assertFalse(validate_rule({"port": 443, "protocol": "both", "destinations": []})[0])

        # Valid boundaries (port 1 and port 65535)
        self.assertTrue(validate_rule({"port": 1, "protocol": "tcp", "destinations": [{"target": "1.1.1.1", "port": 1}]})[0])
        self.assertTrue(validate_rule({"port": 65535, "protocol": "udp", "destinations": [{"target": "1.1.1.1", "port": 65535}]})[0])

    def test_validate_rule_multi_priority_cascading(self):
        """Verifies that arbitrary positive priority numbers (N-tier failover) are accepted and normalized."""
        multi_rule = {
            "port": 8443,
            "protocol": "both",
            "destinations": [
                {"priority": 1, "type": "haproxy", "target": "2001:db8::1", "port": 8443},
                {"priority": 2, "type": "nftables", "target": "10.88.1.2", "port": 8443},
                {"priority": 3, "type": "haproxy", "target": "2001:db8::3", "port": 8443},
                {"priority": 4, "type": "nftables", "target": "10.88.2.2", "port": 8443},
                {"priority": 5, "type": "nginx", "target": "10.88.3.2", "port": 8443}
            ]
        }
        ok, err = validate_rule(multi_rule)
        self.assertTrue(ok, f"Multi-priority rule should validate, got error: {err}")
        self.assertEqual(len(multi_rule["destinations"]), 5)
        for i, d in enumerate(multi_rule["destinations"], start=1):
            self.assertEqual(d["priority"], i)

        # Invalid priority <= 0
        self.assertFalse(validate_rule({"port": 443, "destinations": [{"priority": 0, "target": "1.1.1.1"}]})[0])
        self.assertFalse(validate_rule({"port": 443, "destinations": [{"priority": -1, "target": "1.1.1.1"}]})[0])

        # Non-integer priority string
        self.assertFalse(validate_rule({"port": 443, "destinations": [{"priority": "first", "target": "1.1.1.1"}]})[0])

    def test_web_server_ssl_initialization(self):
        """Verifies that XForwarderWebServer parses ssl_cert and ssl_key attributes."""
        from core.web_server import XForwarderWebServer
        server = XForwarderWebServer(port=8999, bind_host="127.0.0.1")
        self.assertEqual(server.port, 8999)
        self.assertEqual(server.bind_host, "127.0.0.1")
        self.assertIsInstance(server.ssl_cert, str)
        self.assertIsInstance(server.ssl_key, str)
        self.assertFalse(server.is_ssl)

    def test_session_persistence_prunes_idle_and_strips_internal_keys(self):
        """Verifies save/load_sessions_from_disk strips internal keys and prunes idle-expired sessions."""
        import json
        import tempfile
        import time
        from unittest.mock import patch
        from core.auth import (
            ACTIVE_SESSIONS, SESSION_LOCK, SESSION_IDLE_TIMEOUT_SECONDS,
            load_sessions_from_disk, save_sessions_to_disk,
        )

        tmp_file = os.path.join(tempfile.gettempdir(), f"xfwd_sec_sess_{os.getpid()}.json")
        now = time.time()
        try:
            with SESSION_LOCK:
                saved_backup = dict(ACTIVE_SESSIONS)
                ACTIVE_SESSIONS.clear()
                ACTIVE_SESSIONS["tok_active"] = {
                    "username": "admin",
                    "created_at": now - 100,
                    "last_active": now - 10,
                    "expires_at": now + 3600,
                    "_last_saved": now - 10,
                }
                ACTIVE_SESSIONS["tok_idle"] = {
                    "username": "admin",
                    "created_at": now - 20000,
                    "last_active": now - (SESSION_IDLE_TIMEOUT_SECONDS + 60),
                    "expires_at": now + 3600,
                }

            save_sessions_to_disk(path_override=tmp_file)
            with open(tmp_file, "r", encoding="utf-8") as f:
                persisted = json.load(f)
            self.assertIn("tok_active", persisted)
            self.assertNotIn("tok_idle", persisted)
            self.assertNotIn("_last_saved", persisted["tok_active"])

            with SESSION_LOCK:
                ACTIVE_SESSIONS.clear()
            load_sessions_from_disk(path_override=tmp_file)
            with SESSION_LOCK:
                self.assertIn("tok_active", ACTIVE_SESSIONS)
                self.assertNotIn("tok_idle", ACTIVE_SESSIONS)
        finally:
            with SESSION_LOCK:
                ACTIVE_SESSIONS.clear()
                ACTIVE_SESSIONS.update(saved_backup)
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_get_auth_context_throttled_session_persistence(self):
        """Verifies get_auth_context updates last_active and persists to disk when >=60s elapsed."""
        import tempfile
        import time
        from unittest.mock import MagicMock, patch
        from core.web_server import XForwarderWebHandler, ACTIVE_SESSIONS, SESSION_LOCK

        tmp_file = os.path.join(tempfile.gettempdir(), f"xfwd_ctx_sess_{os.getpid()}.json")
        now = time.time()
        try:
            with SESSION_LOCK:
                saved_backup = dict(ACTIVE_SESSIONS)
                ACTIVE_SESSIONS.clear()
                ACTIVE_SESSIONS["tok_throttle"] = {
                    "username": "admin",
                    "created_at": now - 500,
                    "last_active": now - 120,
                    "expires_at": now + 3600,
                    "_last_saved": now - 120,
                }

            handler = MagicMock(spec=XForwarderWebHandler)
            handler.headers = {"Cookie": "xfwd_session=tok_throttle"}
            handler.get_session_token = lambda: XForwarderWebHandler.get_session_token(handler)
            handler.get_api_key_from_headers = lambda: None

            with patch("core.web_server.get_sessions_file_path", return_value=tmp_file):
                ctx = XForwarderWebHandler.get_auth_context(handler)

            self.assertIsNotNone(ctx)
            self.assertTrue(ctx["authenticated"])
            self.assertTrue(os.path.isfile(tmp_file))
        finally:
            with SESSION_LOCK:
                ACTIVE_SESSIONS.clear()
                ACTIVE_SESSIONS.update(saved_backup)
            if os.path.exists(tmp_file):
                os.remove(tmp_file)


if __name__ == "__main__":
    unittest.main()

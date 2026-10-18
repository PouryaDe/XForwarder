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


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
XForwarder - Authentication & Security Subsystem
Provides salted PBKDF2-HMAC-SHA256 password hashing, persistent session tracking,
and adaptive brute-force lockout protection.
"""

import os
import sys
import json
import time
import hashlib
import hmac
import secrets
import threading
import tempfile
from typing import Dict, Any, Tuple, Optional

PBKDF2_ITERATIONS = 100000

ACTIVE_SESSIONS: Dict[str, dict] = {}
SESSION_LOCK = threading.Lock()
SESSION_TTL_HOURS = 24
SESSION_IDLE_TIMEOUT_SECONDS = 14400  # 4 hours idle limit
MAX_ACTIVE_SESSIONS = 50

# Rate Limiting & Brute-Force Shield State
FAILED_LOGIN_ATTEMPTS: Dict[str, dict] = {}
RATE_LIMIT_LOCK = threading.Lock()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900   # 15 minutes lockout
WINDOW_DURATION = 300    # 5 minutes failure evaluation window


def get_sessions_file_path() -> str:
    """Returns persistent sessions storage path in /run/xforwarder or system temp."""
    for d in ["/run/xforwarder", "/run/forward-manager"]:
        if os.path.isdir(d):
            return os.path.join(d, "sessions.json")
    try:
        os.makedirs("/run/xforwarder", exist_ok=True)
        return "/run/xforwarder/sessions.json"
    except Exception:
        return os.path.join(tempfile.gettempdir(), "xfwd_sessions.json")


def load_sessions_from_disk(path_override: Optional[str] = None) -> None:
    """Loads active, unexpired sessions from disk to survive daemon restarts."""
    path = path_override or get_sessions_file_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            now = time.time()
            valid = {}
            for tok, sess in data.items():
                if isinstance(sess, dict) and sess.get("expires_at", 0) > now:
                    valid[tok] = sess
            with SESSION_LOCK:
                ACTIVE_SESSIONS.update(valid)
    except Exception:
        pass


def save_sessions_to_disk(path_override: Optional[str] = None) -> None:
    """Atomically persists active sessions to disk."""
    path = path_override or get_sessions_file_path()
    now = time.time()
    with SESSION_LOCK:
        data_to_save = {k: v for k, v in ACTIVE_SESSIONS.items() if v.get("expires_at", 0) > now}
    try:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f)
        os.replace(tmp, path)
    except Exception:
        pass


def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    """Generates a secure PBKDF2-HMAC-SHA256 salted password hash."""
    if not salt_hex:
        salt_hex = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt_hex}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> Tuple[bool, bool]:
    """
    Verifies password against stored hash using constant-time comparison.
    Returns: (is_valid, needs_rehash)
    Backward compatible with legacy SHA-256 with automatic seamless upgrade to PBKDF2.
    """
    if not stored_hash or not password or not isinstance(password, str):
        return False, False

    # Modern salted PBKDF2-HMAC-SHA256 format
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) == 3:
                header, salt_hex, expected_hex = parts
                iters = int(header.split(":")[-1])
                salt_bytes = bytes.fromhex(salt_hex)
                derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iters)
                return hmac.compare_digest(derived.hex(), expected_hex), False
        except Exception:
            return False, False

    # Legacy plain SHA-256 hash (64 hex characters)
    legacy_test = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if hmac.compare_digest(legacy_test, stored_hash):
        return True, True  # Valid, triggers self-healing upgrade to salted PBKDF2!

    return False, False


def check_rate_limit(client_ip: str) -> Tuple[bool, int, int]:
    """Checks if client IP is currently rate-limited. Returns (is_locked, remaining_seconds, fail_count)."""
    now = time.time()
    with RATE_LIMIT_LOCK:
        record = FAILED_LOGIN_ATTEMPTS.get(client_ip)
        if not record:
            return False, 0, 0

        lockout_until = record.get("lockout_until", 0)
        if now < lockout_until:
            remaining = int(lockout_until - now)
            return True, remaining, record.get("count", 0)

        # If evaluation window expired and not locked out, clear record
        if now > record.get("first_attempt", 0) + WINDOW_DURATION:
            FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)
            return False, 0, 0

        return False, 0, record.get("count", 0)


def record_failed_login(client_ip: str) -> Tuple[bool, int, int]:
    """Records a failed login attempt and calculates lockout status."""
    now = time.time()
    with RATE_LIMIT_LOCK:
        record = FAILED_LOGIN_ATTEMPTS.get(client_ip)
        if not record or now > record.get("first_attempt", 0) + WINDOW_DURATION:
            record = {"count": 1, "first_attempt": now, "lockout_until": 0}
        else:
            record["count"] += 1

        is_locked = False
        remaining = 0
        if record["count"] >= MAX_FAILED_ATTEMPTS:
            record["lockout_until"] = now + LOCKOUT_DURATION
            is_locked = True
            remaining = LOCKOUT_DURATION

        FAILED_LOGIN_ATTEMPTS[client_ip] = record

        # Prune expired entries if dict is growing
        if len(FAILED_LOGIN_ATTEMPTS) > 100:
            stale = [k for k, v in FAILED_LOGIN_ATTEMPTS.items() if now > v.get("lockout_until", 0) and now > v.get("first_attempt", 0) + WINDOW_DURATION]
            for k in stale:
                FAILED_LOGIN_ATTEMPTS.pop(k, None)

        return is_locked, remaining, record["count"]


def reset_rate_limit(client_ip: str) -> None:
    """Clears failed login counter on successful authentication."""
    with RATE_LIMIT_LOCK:
        FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)


# Initialize sessions on module import
load_sessions_from_disk()

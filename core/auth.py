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
from typing import Dict, Any, Tuple, Optional, List

PBKDF2_ITERATIONS = 100000
VALID_API_SCOPES = ("read", "write", "admin")
API_KEY_PREFIX = "xfwd_"
_SCOPE_LEVEL = {"read": 1, "write": 2, "admin": 3}

API_KEY_USAGE: Dict[str, float] = {}
_API_USAGE_LOCK = threading.Lock()

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


def hash_api_key(raw_key: str, salt_hex: Optional[str] = None) -> str:
    """Hashes a high-entropy API key with a random 16-byte salt using SHA-256."""
    if not salt_hex:
        salt_hex = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt_hex}:{raw_key}".encode("utf-8")).hexdigest()
    return f"sha256${salt_hex}${digest}"


def verify_api_key_hash(raw_key: str, stored_hash: str) -> bool:
    """Verifies an API key against its stored salted hash using constant-time comparison."""
    if not raw_key or not stored_hash or not isinstance(raw_key, str) or not isinstance(stored_hash, str):
        return False
    if stored_hash.startswith("sha256$"):
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False
        _, salt_hex, expected_hex = parts
        digest = hashlib.sha256(f"{salt_hex}:{raw_key}".encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, expected_hex)
    if stored_hash.startswith("pbkdf2:sha256:"):
        ok, _ = verify_password(raw_key, stored_hash)
        return ok
    return False


def generate_api_key(
    name: str,
    scope: str = "admin",
    expires_in_days: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generates a cryptographically random API key and its non-secret config record.
    Returns (plaintext_api_key, key_record).
    """
    clean_scope = str(scope or "admin").strip().lower()
    if clean_scope not in VALID_API_SCOPES:
        clean_scope = "admin"
    clean_name = "".join(c for c in str(name or "API Key").strip()[:64] if ord(c) >= 32 and c not in "<>\";`$\\{}")
    if not clean_name:
        clean_name = "API Key"

    key_id = f"key_{secrets.token_hex(4)}"
    secret_hex = secrets.token_hex(24)
    raw_key = f"{API_KEY_PREFIX}{key_id}_{secret_hex}"
    prefix = f"{API_KEY_PREFIX}{key_id}_{secret_hex[:4]}..."
    now = time.time()

    expires_at = 0.0
    if expires_in_days is not None:
        try:
            days = int(expires_in_days)
            if days > 0:
                expires_at = now + (days * 86400)
        except (ValueError, TypeError):
            expires_at = 0.0

    record = {
        "id": key_id,
        "name": clean_name,
        "prefix": prefix,
        "key_hash": hash_api_key(raw_key),
        "scope": clean_scope,
        "enabled": True,
        "created_at": round(now, 3),
        "expires_at": round(expires_at, 3) if expires_at > 0 else 0.0,
        "last_used_at": 0.0,
    }
    return raw_key, record


def record_api_key_usage(key_id: str, ts: Optional[float] = None) -> None:
    """Tracks the latest usage timestamp for an API key in memory without disk churn."""
    if not key_id:
        return
    with _API_USAGE_LOCK:
        API_KEY_USAGE[key_id] = float(ts if ts is not None else time.time())


def get_api_key_last_used(key_id: str, fallback: float = 0.0) -> float:
    """Returns the most recent usage timestamp for an API key."""
    with _API_USAGE_LOCK:
        mem_ts = API_KEY_USAGE.get(key_id, 0.0)
    try:
        fb = float(fallback or 0.0)
    except (ValueError, TypeError):
        fb = 0.0
    return max(mem_ts, fb)


def sanitize_api_key_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Returns public-safe API key metadata without exposing key_hash or plaintext secret."""
    key_id = str(rec.get("id") or "")
    expires_at = float(rec.get("expires_at") or 0.0)
    now = time.time()
    is_expired = bool(expires_at > 0 and now > expires_at)
    return {
        "id": key_id,
        "name": str(rec.get("name") or "API Key"),
        "prefix": str(rec.get("prefix") or "xfwd_..."),
        "scope": str(rec.get("scope") or "admin"),
        "enabled": bool(rec.get("enabled", True)),
        "expired": is_expired,
        "created_at": float(rec.get("created_at") or 0.0),
        "expires_at": expires_at,
        "last_used_at": get_api_key_last_used(key_id, rec.get("last_used_at", 0.0)),
    }


def scope_allows(key_scope: str, required_scope: str) -> bool:
    """Checks whether `key_scope` satisfies `required_scope` under read < write < admin."""
    cur_lvl = _SCOPE_LEVEL.get(str(key_scope or "").strip().lower(), 0)
    req_lvl = _SCOPE_LEVEL.get(str(required_scope or "admin").strip().lower(), 3)
    return cur_lvl >= req_lvl


def authenticate_api_key(raw_key: str, api_keys: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Validates a presented API key against configured `web.api_keys` records.
    Returns sanitized key metadata on success, or None if invalid, disabled, or expired.
    """
    if not raw_key or not isinstance(raw_key, str) or not isinstance(api_keys, list):
        return None
    token = raw_key.strip()
    if not token.startswith(API_KEY_PREFIX) or len(token) < 20:
        return None

    now = time.time()
    for rec in api_keys:
        if not isinstance(rec, dict):
            continue
        if not rec.get("enabled", True):
            continue
        expires_at = float(rec.get("expires_at") or 0.0)
        if expires_at > 0 and now > expires_at:
            continue
        stored_hash = str(rec.get("key_hash") or "")
        if verify_api_key_hash(token, stored_hash):
            key_id = str(rec.get("id") or "")
            record_api_key_usage(key_id, now)
            return sanitize_api_key_record(rec)
    return None


# Initialize sessions on module import
load_sessions_from_disk()

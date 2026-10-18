# Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

**Date:** 2026-10-18  
**Category:** security  
**Status:** Active  

---

## 1. Context & Motivation
XForwarder runs 24/7 on public Linux intermediate relay servers (e.g. Iran VPS) with exposed web management ports. Simple unsalted SHA-256 password hashing and unbounded login endpoints create severe exposure to GPU rainbow tables, dictionary attacks, and high-frequency automated brute-force attempts.

## 2. Root Cause / Core Dynamics
1. **Unsalted Hash Vulnerability:** Single-iteration SHA-256 without salt allows precomputed rainbow tables to reverse passwords instantly.
2. **Brute-Force Flooding:** Without IP-based rate limiting, attackers can send thousands of POST requests per second to `/api/login`, consuming server CPU and risking credential discovery.
3. **MIME and Clickjacking Risks:** Missing modern browser security headers allows iframe embedding and MIME confusion.

## 3. Architecture & Solution Implemented
1. **PBKDF2-HMAC-SHA256 with 16-byte Cryptographic Salt:**
   - 100,000 iterations using native `hashlib.pbkdf2_hmac` (`pbkdf2:sha256:100000$<salt>$<hash>`).
   - Self-healing backward compatibility: legacy 64-hex SHA-256 hashes are verified via constant-time `hmac.compare_digest` and seamlessly auto-upgraded to PBKDF2 on first login without user intervention.
2. **Adaptive IP-Based Rate Limiting:**
   - In-memory thread-safe tracker (`FAILED_LOGIN_ATTEMPTS`).
   - 5 failed attempts in 5 minutes triggers an immediate 15-minute lockout returning HTTP 429 (`Retry-After: <seconds>`).
   - Timing jitter delay (400-700ms) on failed attempts defeats fast automated credential stuffing.
3. **OWASP Top 10 Defense in Depth:**
   - Enforce `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.
   - Cookies set with `HttpOnly; SameSite=Strict` and 4-hour idle timeout.
   - Origin/Referer verification on state-changing requests to block CSRF.
   - Max body size capped at 64KB (`MAX_PAYLOAD = 65536`) to prevent memory DoS.

## 4. Invariants & Rules for AI Agents
- **Rule 1:** Never store plaintext passwords or plain unsalted hashes. Always use `hash_password()` with PBKDF2.
- **Rule 2:** Never remove rate-limiting guards on `/api/login`.
- **Rule 3:** All state-changing endpoints (POST, DELETE) must verify Origin/Referer against Host.
- **Rule 4:** Keep RAM usage bounded by pruning expired sessions and lockout records.

## 5. Verification & Testing
- Run `python -m unittest tests/test_security.py` to verify PBKDF2 hashing, legacy migration, lockout thresholds, and input sanitization.
- Run `python .agents/scripts/verify-all.py` for full pre-commit compliance.

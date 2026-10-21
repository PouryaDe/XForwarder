---
trigger: always_on
description: Web dashboard UI aesthetics, Vanilla stack constraints, session authentication, and API security guidelines.
---

# Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

## 1. Frontend Technology Stack
- **Pure Vanilla Stack**: HTML5, CSS3, and modern Vanilla ES6+ JavaScript.
- **No Node.js / NPM Build Step**: The web dashboard is served directly from `web/` as static assets without any Webpack/Vite/Babel compilation step on the target Linux server.
- **Typography**: Google Fonts Inter (interface) and JetBrains Mono (monospaced IPs, ports, and latency readouts).

## 2. Aesthetics & Design Guidelines
- **Theme**: Modern Obsidian dark aesthetic (`#090A0F`) with sleek glassmorphism panels, subtle borders (`rgba(255, 255, 255, 0.07)`), and restrained highlights (red/rose strictly for outages, amber for degradation/flapping/manual testing overrides, and calm neutral surfaces for healthy states).
- **Responsiveness**: Fully usable on mobile viewports as well as ultra-wide monitors.
- **Language**: English interface for universal usability.

## 3. Authentication & Security Model
- **Password Protection**: Admin password is encrypted via PBKDF2-HMAC-SHA256 (100,000 iterations + 16-byte cryptographic salt) with backward-compatible auto-upgrade for legacy SHA-256 hashes.
- **Session Tokens & Timeouts**:
  - Secure 256-bit random tokens generated via `secrets.token_hex(32)`.
  - Stored in memory with 24-hour absolute TTL and 4-hour inactivity timeout (`SESSION_IDLE_TIMEOUT_SECONDS = 14400`).
  - Delivered via `Set-Cookie: xfwd_session=<token>; Path=/; HttpOnly; SameSite=Strict` (with `; Secure` when over HTTPS).
- **Brute-Force & Rate Limiting**:
  - 5 failed login attempts in 5 minutes triggers a 15-minute client IP lockout (HTTP 429 Too Many Requests with `Retry-After` header).
  - Failed logins incur an intentional 400-700ms timing jitter delay to defeat automated credential stuffing.
- **OWASP Defense in Depth**:
  - Enforce `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: strict-origin-when-cross-origin`.
  - Mask server identity header (`Server: XForwarder-Shield/2.0`).
  - Strict payload size limit of 64KB (`MAX_PAYLOAD = 65536`).
  - CSRF protection via `Origin`/`Referer` header verification on mutating endpoints (POST, DELETE).
- **API Guard**: Every endpoint under `/api/*` (except `/api/login`) must verify session validity using `check_auth(handler)` and return `401 Unauthorized` if unauthenticated.
- **Cache Control**: All JSON API responses must specify `Cache-Control: no-store, no-cache, must-revalidate`.

---
trigger: model_decision
always_on: false
description: Web dashboard UI aesthetics, Vanilla JS/CSS stack constraints, PBKDF2 session auth, and API security guidelines. Load when modifying web/ or core/web_server.py or core/auth.py.
---

# Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

## 1. Frontend Technology Stack
- **Pure Vanilla Stack**: HTML5, CSS3, and modern Vanilla ES6+ JavaScript.
- **No Node.js / NPM Build Step**: The web dashboard is served directly from `web/` as static assets without any Webpack/Vite/Babel compilation step on the target Linux server.
- **Typography**: Google Fonts Bricolage Grotesque (display/headings), Hanken Grotesk (interface body), JetBrains Mono (monospaced IPs, ports, and latency readouts), and Vazirmatn (Persian RTL typography).

## 2. Aesthetics & Design Guidelines
- **Theme**: Ovira Mint aesthetic with deep obsidian-teal dark base (`#05090a`), warm-stone light base (`#e8e7de`), cursor-lit dot matrix + drifting radial blobs (`.ambient.aurora`), split-screen login with animated SVG Bore Tunnel illustration, floating rounded glass sidebar with spring navigation indicator, per-card radial spotlight hover, Mint accent (`#34e0a1` dark / `#2fd896` light / `#006b4a` accessible text), Cyan secondary (`#46d6e6` dark / `#0b8c9b` light), and semantic alerts (`#ff6b57` / `#c43a28` for outages, `#ffb648` / `#a35b00` for warnings, `#3ee8a6` / `#0f7f58` for healthy states).
- **Rules Organization**: Default card view with optional compact list view toggle; multi-metric sorting (port, registration date, health, category); optional custom port categories with illuminated divider lines and autocomplete datalist suggestions.
- **Responsiveness**: Fully usable on mobile viewports as well as ultra-wide monitors.
- **Bilingual & RTL Architecture**: Comprehensive English (`en`) and Persian (`fa`) dual-language support with instant toggle. Persian mode activates `[dir="rtl"]`, right-to-left layout alignment, Vazirmatn font, and zero-flicker pre-hydration script in `<head>`. Latin numerals, IP addresses (`.dest-ip`, `.font-mono`), port badges, latency/packet-loss pills, and traffic values strictly enforce `direction: ltr !important` and `unicode-bidi: embed !important` to prevent text reversal.

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
- **System Updates & Service Control Endpoints**: `/api/system/version` (GET), `/api/system/update` (POST), `/api/system/update/status` (GET), and `/api/services/restart` (POST) are strictly authenticated, origin-checked, and execute asynchronously to prevent HTTP socket cutoff or systemd cgroup termination.

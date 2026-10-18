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
- **Theme**: Premium dark aesthetic with sleek glassmorphism panels, subtle borders (`rgba(255, 255, 255, 0.08)`), and soft neon accent indicators (green for healthy, amber for checking, red for failed).
- **Responsiveness**: Fully usable on mobile viewports as well as ultra-wide monitors.
- **Language**: English interface for universal usability.

## 3. Authentication & Security Model
- **Password Protection**: Admin password is stored as a SHA-256 hash (`password_hash`) in `config.json`.
- **Session Tokens**:
  - Secure random tokens generated via `secrets.token_hex(24)`.
  - Stored in memory with 24-hour TTL (`SESSION_TTL_HOURS = 24`).
  - Delivered via `Set-Cookie: xfwd_session=<token>; Path=/; HttpOnly; SameSite=Lax` (with backward compatibility for `fwdman_session`).
- **API Guard**: Every endpoint under `/api/*` (except `/api/login`) must verify session validity using `check_auth(handler)` and return `401 Unauthorized` if unauthenticated.
- **Cache Control**: All JSON API responses must specify `Cache-Control: no-store, no-cache, must-revalidate`.

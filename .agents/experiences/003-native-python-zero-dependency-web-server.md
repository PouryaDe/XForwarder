# Experience 003: Native Python Zero-Dependency Web Server

**Date:** 2026-10-18  
**Category:** Architecture & Footprint  
**Status:** Active  

---

## 1. Context & Motivation
XForwarder runs on low-cost intermediate relay VPS servers where RAM is severely constrained (often 512MB to 1GB total RAM shared with VPN tunnels, HAProxy, and kernel packet buffers). Heavy frameworks like Node.js, Flask, FastAPI, Uvicorn, or Docker can easily consume 100MB-300MB of RAM.

## 2. Root Cause / Core Dynamics
- Third-party pip packages introduce external C extensions, package version drift, and dependency resolution issues across Debian and Ubuntu LTS releases.
- Package managers (`pip`, `npm`) fail during offline installation or when Iranian network restrictions block PyPI/NPM registries.

## 3. Architecture & Solution Implemented
1. **Standard Library Only:** The web server is implemented using `http.server.ThreadingHTTPServer` and `http.server.BaseHTTPRequestHandler` from the Python 3 standard library.
2. **Session Security Without Frameworks:**
   - Cryptographically random session tokens via `secrets.token_hex(24)`.
   - In-memory session tracking with 24-hour expiration (`SESSION_TTL_HOURS = 24`).
   - Delivered via `Set-Cookie: xfwd_session=<token>; Path=/; HttpOnly; SameSite=Lax`.
   - Admin credentials secured via SHA-256 password hashing (`hashlib.sha256`).
3. **Static Vanilla Frontend:**
   - Web assets in `web/` (`index.html`, `style.css`, `app.js`) are pure HTML5/CSS3/Vanilla ES6.
   - Zero compilation, bundling, or transpilation required.

## 4. Invariants & Rules for AI Agents
- Never introduce third-party Python pip packages (no Flask, FastAPI, Requests).
- Never introduce Node.js, npm, or build tools into `web/`.
- Total idle memory consumption of both daemons must stay strictly below 15MB.

## 5. Verification & Testing
```bash
# Verify idle resident set size (RSS)
ps aux | grep -E "engine.py|web_server.py" | awk '{print $11, $6/1024 " MB"}'
```
Confirm RSS remains under 15MB.

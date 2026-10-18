---
name: code-review-audit
description: "8-point security, architecture, and code quality audit checklist covering zero-collision, native standard library, and socket safety."
---

# Code Review & Quality Audit Skill (XForwarder)

Use this skill when auditing existing code, reviewing pull requests, or conducting quality and security checks on XForwarder features.

---

## The 8-Point Audit Checklist

### 1. Zero-Collision Forwarding Invariant (CRITICAL)
- **Forbidden:** Binding a port in HAProxy while simultaneously forwarding it via NFTables DNAT.
- **Check:** When `active_priority` is 1 (HAProxy), only HAProxy binds `*:<port>`, and NFTables rules are deleted.
- **Check:** When `active_priority` is 2 (NFTables), HAProxy deactivates that listener, and DNAT takes over in `table ip xfwd_orchestrator`.

### 2. Native Standard Library Only (CRITICAL)
- **Forbidden:** Introducing third-party pip dependencies (`requests`, `flask`, `fastapi`, `uvicorn`, `pydantic`).
- **Check:** Code exclusively uses native Python 3 standard library modules.
- **Check:** Resident Set Size (RAM) stays strictly below 15MB.

### 3. Atomic File Persistence (CRITICAL)
- **Forbidden:** Direct `open(path, "w")` on `config.json` or `state.json`.
- **Check:** All writes dump to a temporary file (`.tmp.<pid>`) and commit atomically via `os.replace`.

### 4. Non-Blocking Probing & Socket Safety (CRITICAL)
- **Forbidden:** Unbounded or blocking socket calls without explicit timeouts.
- **Check:** Health checks use `socket.create_connection(..., timeout=2.0)`.
- **Check:** Sockets are reliably closed in `finally` blocks or context managers.

### 5. NFTables Table Isolation (CRITICAL)
- **Forbidden:** Executing `nft flush ruleset` or touching other system tables.
- **Check:** DNAT routing strictly resides inside `table ip xfwd_orchestrator`.
- **Check:** Generated rules are pre-validated via `nft -c -f -` before applying.

### 6. HAProxy Graceful Reloading
- **Forbidden:** Hard restarts of HAProxy during runtime failover cycles.
- **Check:** Updates use `systemctl reload haproxy` to preserve existing active client connections.

### 7. Authentication & API Security
- **Forbidden:** Unauthenticated endpoints under `/api/*` (except `/api/login`).
- **Forbidden:** Plaintext password storage. Must use SHA-256 hashes.
- **Check:** Session cookies enforce `HttpOnly` and `SameSite=Lax` with 24-hour TTL.
- **Check:** API responses include `Cache-Control: no-store, no-cache`.

### 8. Pure Vanilla Frontend
- **Forbidden:** Introducing npm, Webpack, Vite, or Node.js build steps into `web/`.
- **Check:** UI assets remain pure static HTML5, CSS3, and modern Vanilla ES6+.

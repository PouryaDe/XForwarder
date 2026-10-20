# Experience 008: Full-Stack Performance Optimization & Fast IPC

## Context & Motivation
As the number of forwarded ports and uplinks grew, the web dashboard and daemon interactions required optimization:
1. In the web dashboard, continuous 8-second polling caused full DOM re-renders of all rule cards, resulting in micro-flickering and layout reflow.
2. Static assets (`index.html`, `style.css`, `app.js`) were read from disk on every single HTTP request.
3. Service updates (`systemctl reload haproxy/nginx`) and `nft` rebuilds executed even when configuration had not changed.
4. Changes made in the web UI had to wait up to the full engine poll interval (8s) before the core engine evaluated routing changes.

## Architectural Solutions Implemented

### 1. Server-Side HTTP Performance
- **Native Gzip Compression**: Transparent compression added to `send_json()` and `send_file()` in `core/web_server.py` for payloads >512 bytes with accurate `Content-Length` framing when client sends `Accept-Encoding: gzip`.
- **ETag & Conditional 304 Responses**: Weak ETags (`W/"<mtime>-<size>"`) implemented. Requests with matching `If-None-Match` receive `304 Not Modified` with 0-byte wire transfer.
- **In-Memory Static Asset Caching**: `_STATIC_CACHE` stores raw and pre-compressed static assets in RAM, invalidating automatically upon file `mtime` modification.
- **Subprocess Version Caching**: `_VERSION_CACHE` prevents repeated execution of `haproxy -v`, `nft --version`, and `nginx -v` during system status inspections.

### 2. Selective Service Reloading
- `_apply_haproxy()` and `_apply_nginx()` compare generated configuration against disk contents before invoking `systemctl reload`.
- `_apply_nftables()` compares generated ruleset against `self._last_nft_content` before executing `nft -f -`.
- Unnecessary process signals and subshell spawns are eliminated when rules remain unchanged.

### 3. Fast IPC Engine Wake-Up
- Core engine daemon writes its PID to `/run/xforwarder/engine.pid` (with fallbacks to `/run/forward-manager/` and temp directory).
- Uses `threading.Event()` for responsive sleeping (`_wake_event.wait(timeout=interval)`).
- Installs `SIGUSR1` signal handler. Web server calls `notify_engine_wakeup()` on any mutating API operation (`POST /api/rule`, `DELETE /api/rule`, etc.), triggering instant routing evaluation.

### 4. Client-Side Smoothness
- **Smart DOM Fingerprinting**: `computeRulesFingerprint()` calculates an atomic string of rule IDs, active priorities, destination statuses, latencies, and comments. `renderRules()` skips complete DOM reconstruction when data is unchanged.
- **Optimistic UI with Rollback**: Deletions immediately apply an exit transition (`.is-deleting`), remove DOM elements smoothly, and roll back state and stats cards if the server request fails.
- **Debounced Search**: 120ms debounce on the search input prevents lag during rapid typing.
- **Page Visibility Throttling**: Reduces poll frequency from 8s to 15s when browser tab is inactive.

## Key Invariants & Lessons
- Ensure `apply_security_headers(include_cache_control=False)` is used when custom `Cache-Control` or 304 responses are sent to prevent duplicate HTTP headers.
- Always include comments in rule/destination fingerprints to avoid suppressing updates when user only modifies descriptive text.
- Sockets and subprocesses in unit tests must be thoroughly mocked to guarantee sub-second execution on both Linux and Windows development environments.

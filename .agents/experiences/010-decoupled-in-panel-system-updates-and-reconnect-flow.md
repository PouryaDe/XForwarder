# Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

**Date:** 2026-10-22  
**Category:** Architecture  
**Status:** Active  

---

## 1. Context & Motivation
Administrators requested the ability to trigger XForwarder software updates directly from the authenticated web dashboard without logging into the server CLI via SSH.

## 2. Root Cause / Core Dynamics
1. **Self-Termination Hazard in Systemd**: In production, `xforwarder.sh update` executes `systemctl restart xforwarder.service xforwarder-web.service`. If the web server initiates this update as a direct child subprocess, systemd terminates the entire cgroup (`KillMode=control-group`) during service restart. The update script would be killed mid-execution, potentially leaving core binaries half-copied.
2. **HTTP Stream Dropping**: As soon as the web service restarts, any active HTTP connections are severed before the client receives the final status response.
3. **GitHub API Rate Limits**: Probing GitHub on every page load would exhaust the unauthenticated rate limit (60 requests/hour).

## 3. Architecture & Solution Implemented
1. **Decoupled Transient Unit Execution (`systemd-run`)**:
   - `start_system_update()` in `core/web_server.py` delegates execution to `systemd-run --unit=xfwd-updater-<timestamp> --description="XForwarder Web Update" bash -c "DEBIAN_FRONTEND=noninteractive bash xforwarder.sh update >> /run/xforwarder/update.log 2>&1"`.
   - Because `systemd-run` creates a standalone transient service outside the `xforwarder-web.service` cgroup, restarting `xforwarder-web` does not disrupt or kill the updater.
2. **Persistent On-Disk State Across Restarts**:
   - Update logs stream continuously to `/run/xforwarder/update.log`.
   - `get_update_status()` parses this log and sanitizes ANSI escape codes (`re.sub(r'\x1b\[[0-9;]*m', '', raw_log)`).
   - Even after `web_server.py` restarts with a fresh memory footprint, reading `/run/xforwarder/update.log` reliably reports `"status": "completed"` when `[OK] XForwarder updated successfully!` is present.
3. **Client-Side Reconnection Recovery**:
   - `web/app.js` runs `pollUpdateProgress()` every 1200ms.
   - When the web daemon restarts and connection drops, the frontend catches the network exception, increments `updateReconnectTries`, displays a violet reconnecting banner, and maintains retry polling.
   - Upon reconnection, it detects `data.status === 'completed'`, confirms success, and reloads the browser seamlessly (`window.location.reload()`).
4. **Rate-Limit Shielding & 60-Second Cache**:
   - `GET /api/system/version` caches remote GitHub API queries for 60 seconds unless explicitly overridden with `?check=1`.
5. **Controlled Service Restart & Delayed Self-Restart (`POST /api/services/restart`)**:
   - Synchronously executing `systemctl restart xforwarder-web.service` drops the client socket before the HTTP 200 response reaches the browser.
   - `restart_services_action()` delivers an immediate `{ok: true, reconnecting: true}` response, followed by a 600ms delayed background daemon restart via `systemd-run`.
   - The UI displays an overlay reconnection banner and polls until the web daemon responds, then automatically refreshes the state.

## 4. Invariants & Rules for AI Agents
- **Decoupled Lifecycle Invariant**: Never execute commands that restart `xforwarder-web.service` directly inside the synchronous request thread. Always decouple via `systemd-run` or detached processes with redirected log output.
- **ANSI Code Stripping**: Log responses from `/api/system/update/status` must always be stripped of ANSI terminal escape codes before transmission.
- **CSRF & Origin Verification**: `POST /api/system/update` must enforce `check_origin()` and session authentication (`is_authenticated()`).
- **Concurrent Execution Lock**: Simultaneous update requests must be rejected with HTTP 409 Conflict.

## 5. Verification & Testing
1. Run automated unit test suite:
   ```bash
   python -m unittest tests/test_ui_and_api_edge_cases.py
   ```
2. Verify full verification pipeline passes:
   ```bash
   python .agents/scripts/verify-all.py
   ```


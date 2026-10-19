# Experience 007: Fix HAProxy Silent Drop and State Wipeout

**Date:** 2026-10-19  
**Category:** Networking  
**Status:** Active  

---

## 1. Context & Motivation
Users observed that configuring HAProxy forwarding rules resulted in 0 forwarded traffic despite the Web UI reporting destinations as healthy and green. Additionally, the Web UI felt disconnected or lost state intermittently, and changing security settings failed with 404 Not Found.

## 2. Root Cause / Core Dynamics
1. **Hardcoded `send-proxy-v2` in HAProxy Configuration:** `core/engine.py` was appending `send-proxy-v2` unconditionally to every HAProxy backend line. When forwarding to standard upstream services (Xray/V2Ray, Trojan, Nginx, or shadowsocks) not configured with `acceptProxyProtocol`, the upstream server immediately closed the TCP connection upon receiving the unexpected binary PROXY header. Basic TCP health probes succeeded because they only performed SYN-ACK handshakes, causing silent traffic failure with green UI status.
2. **Ephemeral Engine State Wipeout:** Whenever a rule was added, edited, or overridden, `core/web_server.py` instantiated a new `XForwarderEngine()` to invoke `sync_system_rules()`. That new instance started with empty `rules_state: {}` and immediately wrote it to `/run/xforwarder/state.json`, wiping all live health probe results and latencies until the next background daemon tick.
3. **Ghost UDP Forwarder Service:** `core/engine.py` was attempting to reload non-existent `haproxy-forwarder-udp.service` for UDP traffic. HAProxy TCP mode does not forward generic UDP, so UDP traffic stalled silently.
4. **Missing Dual-Stack IPv6 Bind:** HAProxy was only binding `*:<port>`, which on certain Linux sysctl configurations (`net.ipv6.bindv6only = 1`) failed to accept IPv6 inbound traffic.
5. **Settings Route Mismatch:** Web UI settings form submitted POST requests to `/api/security/credentials` and `/api/security`, where `/api/security` was returning 404.

## 3. Architecture & Solution Implemented
1. **Explicit PROXY Protocol Toggle:**
   - Modified `core/engine.py` to only append `send-proxy-v2` if `dest.get("proxy_protocol")` or `dest.get("send_proxy")` is explicitly enabled. Standard raw TCP forwarding is now the default.
   - Updated `web/app.js` and `web/style.css` to add a UI toggle for "Send PROXY Protocol v2 (Advanced)".
   - Added regex support in `core/haproxy_parser.py` to auto-detect `send-proxy` when importing rules.
2. **State Preservation Across Sync Calls:**
   - Added `_load_initial_runtime_state()` and updated `_save_state_file()` in `core/engine.py` to preserve existing live `rules_state` when saving state during on-demand Web UI actions.
3. **UDP Forwarding via Nginx Stream:**
   - Routed HAProxy UDP port rules into Nginx `stream { server { listen <port> udp reuseport; ... } }` and eliminated references to `haproxy-forwarder-udp`.
4. **Dual-Stack Inbound Bind & Bracket Sanitization:**
   - Added dual-stack binding (`bind *:<port>` and `bind ::::<port> v6only` when IPv6 supported).
   - Sanitized IPv6 bracket notation (`target.strip().strip("[]")`) to prevent invalid HAProxy addresses like `[[2a01::1]]:443`.
   - Added `frontend xfwd_standby` dummy section to prevent HAProxy config validation errors when 0 HAProxy rules are active.
5. **Real-time Target Testing Endpoint:**
   - Implemented `POST /api/test-target` endpoint in `core/web_server.py` and added an interactive "Test Target" probe button inside the rule modal with live millisecond latency readout and explicit failure reasons.
6. **Settings Endpoint Alias & External Conflict Check:**
   - Added `/api/security` alongside `/api/security/credentials` in `core/web_server.py`.
   - Added `is_nginx_listening()` alongside `is_haproxy_listening()` in `is_port_in_use_by_external_service` so XForwarder does not falsely detect its own Nginx stream ports as external conflicts.

## 4. Invariants & Rules for AI Agents
- **Rule 1:** Never hardcode `send-proxy-v2` in HAProxy backend definitions. Always respect `dest.get("proxy_protocol", False)`.
- **Rule 2:** `_save_state_file()` must always preserve existing `rules_state` when called from ad-hoc sync instances.
- **Rule 3:** Never assume HAProxy forwards UDP natively. Use Nginx stream or NFTables for UDP payloads.
- **Rule 4:** All target IP inputs must be validated with `is_valid_target()` before executing socket checks.

## 5. Verification & Testing
- Run test suite: `python -m unittest discover -s tests` (all 52 tests covering HAProxy entry generation, PROXY protocol toggle, state preservation, and `/api/test-target` must pass).
- Run full pre-commit pipeline: `python .agents/scripts/verify-all.py`.

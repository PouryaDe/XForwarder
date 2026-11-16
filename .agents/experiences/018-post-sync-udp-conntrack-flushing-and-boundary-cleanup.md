# Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup

**Date:** 2026-11-16  
**Category:** Networking & Reliability  
**Status:** Active  

---

## 1. Context & Motivation
When switching a live UDP/WireGuard port (e.g. `:1000`) from Priority 1 (`nftables` kernel DNAT) to Priority 2 (`nginx` user-space IPv6 UDP proxy), clients continued hitting the old `nftables` DNAT target instead of reaching `nginx`.

## 2. Root Cause / Core Dynamics
1. **`conntrack` CLI missing:** `xforwarder.sh` did not install the `conntrack` package, so `flush_conntrack(port)` silently returned early on `shutil.which("conntrack")`, leaving `[ASSURED]` UDP NAT entries active indefinitely while WireGuard keepalives/handshakes refreshed the 60s `nf_conntrack_udp_timeout_stream` timer.
2. **Pre-sync flush race condition:** Both `core/engine.py` (`_hot_toggle_rule_priority`) and `core/web_server.py` (`/api/override`, `/api/override/batch`, `/api/rule/toggle-destination`) invoked `flush_conntrack` *before* `sync_firewall_and_proxies()` / `sync_rules_and_notify()`. On active UDP ports receiving packets every few milliseconds, the kernel immediately recreated the old DNAT conntrack entry before `nft` and `nginx` reloaded.
3. **Planned boundary switches:** Planned switches between `nftables` (kernel PREROUTING DNAT) and `nginx`/`haproxy` (user-space sockets) skipped conntrack flushing entirely, trapping continuous UDP flows in stale kernel NAT.

## 3. Architecture & Solution Implemented
- Added `conntrack` to `ensure_dependencies()` in `xforwarder.sh`.
- Added `_find_conntrack_bin()` fallback (`/usr/sbin/conntrack`, `/sbin/conntrack`, `/usr/bin/conntrack`), strict `1..65535` port validation, and `timeout=5.0` to `flush_conntrack()` in `core/firewall.py`.
- Updated `core/engine.py` (`_queue_post_sync_conntrack_flush`, `_flush_pending_conntrack`) to run deferred flushes strictly after `sync_firewall_and_proxies()`, and to queue a UDP-only (`proto="udp"`) flush on planned switches crossing between `nftables` and `nginx`/`haproxy` without disrupting TCP sockets.
- Updated `core/web_server.py` (`_safe_flush_port_conntrack`) to run `flush_conntrack` strictly after `sync_rules_and_notify()` in override and toggle-destination endpoints.

## 4. Invariants & Rules for AI Agents
- **Rule 1:** Always synchronize NFTables/HAProxy/Nginx rules *before* calling `flush_conntrack(port)`.
- **Rule 2:** Never flush TCP conntrack on planned switches; only flush `proto="udp"` when crossing `nftables <-> proxy` boundaries on `udp`/`both` rules.
- **Rule 3:** Always validate `1 <= port <= 65535` and bound `conntrack` subprocess calls with a timeout.

## 5. Verification & Testing
- Unit tests in `tests/test_fast_failover_and_antiflap.py` and `tests/test_ui_and_api_edge_cases.py` verify port bounds, `/usr/sbin/conntrack` fallback, UDP-only boundary flushes, TCP socket preservation, and `sync -> flush` ordering.
- Run `python .agents/scripts/verify-all.py` before committing.

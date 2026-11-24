# XForwarder Master Architecture Constitution

Authoritative architectural invariants and navigation index for **XForwarder** (Python 3 Native Multi-Path Relay & Failover Engine).

---

## 1. System Model
- **Intermediate Relay Server:** Linux VPS bridging local clients to foreign exit nodes.
- **Priority 1 (Primary):** User-space TCP/UDP relay via HAProxy (`/etc/haproxy/haproxy.cfg`) or Nginx stream.
- **Priority 2 (Backup):** Kernel Layer-3 tunnel DNAT via NFTables (`table ip xfwd_orchestrator` / `ip6`) over GRE, IPIP, FakeTCP, or AmneziaWG.
- **Core Daemons:** `core/engine.py` (`xforwarder.service`) and `core/web_server.py` (`xforwarder-web.service`), supported by modular subsystems in `core/` and Vanilla ES6+ UI in `web/`.
- **CLI & Tests:** `xforwarder.sh` (`xforwarder` / `xfwd`) and native `unittest` suite in `tests/`.

---

## 2. Non-Negotiable Architectural Invariants
1. **Zero-Collision Forwarding:** A port must never be bound by HAProxy/Nginx and forwarded by NFTables DNAT simultaneously.
2. **Native Python 3 Stdlib Only:** Zero third-party pip dependencies in `core/` or runtime. Combined idle RAM must stay strictly under **15MB**.
3. **Atomic File Persistence:** Always write `config.json` and `state.json` via `.tmp.<pid>` + `os.replace`, preserving live `rules_state` on ad-hoc syncs.
4. **NFTables Isolation, O(1) Maps/VMaps & Clamping:** All DNAT, DSR (`nftables_dsr` / `nftables_dsr_relay`), O(1) `tcp`/`udp` `map`/`vmap` lookups (compatible with `nftables >= 0.9.3` with linear fallback), `syn_mss` subchain, and kernel LB `map`/`vmap` chains (`chain xfwd_lb_*`) reside exclusively inside `table ip xfwd_orchestrator` (and `ip6`, omitting empty IPv6 hook chains when unused). Never run `nft flush ruleset` or `iptables -F`; validate with `nft -c -f -`; enforce TCP MSS clamping (`rt mtu` for standard DNAT, scoped `1380` for DSR relay); preserve `fq flow_limit 1000` at startup via `ensure_fq_qdisc`.
5. **Bounded Non-Blocking Probes & Socket Safety:** Enforce explicit timeouts (`2.0s` / `1.5s` L4 TCP / `0.5s` burst), close sockets immediately, never fall back to ICMP when HAProxy L4 TCP fails, and isolate tunnel probes from WAN leakage.
6. **Graceful Proxy Reloads:** Use non-disruptive `systemctl reload haproxy` (never destructive restarts during failover) with `option splice-auto`, `hard-stop-after 2m`, multi-core `nbthread`, and bounded Nginx UDP `proxy_timeout 60s`.
7. **Clean TCP by Default:** Never hardcode `send-proxy-v2`; PROXY protocol v2 is opt-in per destination.
8. **Two-Tier Failover, Load-Balanced Pools, L4/Blackhole Feedback & Conntrack:** Tier 1 handles outages/critical loss (`>=30%` across `>=2` cycles), HAProxy `DOWN`, and asymmetric traffic blackholes; Tier 2 enforces 5m sliding window, 10m hold (waived on loss), 20%/15pt hysteresis, 120s streak, Priority 1 stickiness (`<=150ms`), and `is_relay` primary-anchor rules. Standard `nftables` and `nginx` destinations also support health-aware load-balanced pools (`lb_enabled`, `ip_hash`/`round_robin`/`random`/`least_conn`) that dynamically prune dead backends with targeted `reply_src` conntrack flushes and only trigger priority failover upon full pool exhaustion. Flush targeted port conntrack **after** sync on critical/override/disabled fallback (and UDP-only when crossing kernel DNAT ↔ user-space proxy).
9. **Backward Compatibility & Migrations:** All updates must preserve rules, custom ports, and admin auth via pre-update atomic backups and idempotent `migrate_and_normalize_config()`.
10. **Web Security & Performance:** Salted PBKDF2-HMAC-SHA256 auth, `/api/*` session guards, adaptive login rate limiting, CSRF `Origin` checks, OWASP headers, Gzip (>512B), ETag/304, and `SIGUSR1` IPC wakeup.
11. **Pure Vanilla Frontend & i18n/RTL:** Pure HTML5, CSS3, and ES6+ modules in `web/` (no Node/npm/build step), dual EN/FA localization with `direction: ltr !important` on technical readouts.
12. **Knowledge Graph First & Zero Polling:** Check `graphify-out/` (`query_graph` / `graphify query`) before reading large files; run `graphify update .` after code edits. Never use `schedule` timers or `manage_task(status)` polling.

---

## 3. On-Demand Rules, Skills & Tooling
Load detailed domain rules on demand (progressive disclosure via `trigger: model_decision`):
- **Architecture & Failover:** [`rules/01-architecture-and-failover.md`](rules/01-architecture-and-failover.md)
- **Python & Relay Constraints:** [`rules/02-python-core-standards.md`](rules/02-python-core-standards.md) | [`rules/relay-vps-constraints.md`](rules/relay-vps-constraints.md)
- **Networking & Kernel:** [`rules/03-networking-and-kernel.md`](rules/03-networking-and-kernel.md)
- **Web Dashboard, Security & UI:** [`rules/04-web-dashboard-and-security.md`](rules/04-web-dashboard-and-security.md) | [`rules/ui-design-consistency.md`](rules/ui-design-consistency.md)
- **Bash & Migrations:** [`rules/05-bash-and-deployment.md`](rules/05-bash-and-deployment.md) | [`rules/backward-compatibility-and-migrations.md`](rules/backward-compatibility-and-migrations.md)
- **Agent Hygiene & Verification:** [`rules/mandatory-checklist.md`](rules/mandatory-checklist.md) | [`rules/blast-radius-analysis.md`](rules/blast-radius-analysis.md) | [`rules/large-files-handling.md`](rules/large-files-handling.md) | [`rules/clean-code-dry.md`](rules/clean-code-dry.md) | [`rules/reverse-prompting.md`](rules/reverse-prompting.md) | [`rules/session-handoff.md`](rules/session-handoff.md) | [`rules/experience-logging.md`](rules/experience-logging.md)
- **Skills & Workflows:** [`skills/xfwd-ops/SKILL.md`](skills/xfwd-ops/SKILL.md) | [`skills/code-review-audit/SKILL.md`](skills/code-review-audit/SKILL.md) | [`skills/systematic-debugging/SKILL.md`](skills/systematic-debugging/SKILL.md) | [`workflows/`](workflows/) | [`experiences/README.md`](experiences/README.md)
- **Verification Pipeline:** `python .agents/scripts/verify-all.py` (runs syntax check, anti-pattern scan, ES import validation, `unittest`, and JSON checks).

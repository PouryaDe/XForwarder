# XForwarder Master Architecture Constitution

Authoritative architectural rules and standard operating procedures for AI agents in **XForwarder** (Python 3 Native Multi-Path Relay & Failover Engine).

---

## 1. Project Overview & Terminology
- **Intermediate Relay Server:** Linux VPS (e.g. Iran) bridging local clients to foreign exit nodes.
- **Priority 1 (Primary Relay):** Direct user-space TCP/UDP IPv6 relay via HAProxy (`/etc/haproxy/haproxy.cfg`).
- **Priority 2 (Backup Tunnel):** Kernel Layer-3 tunnel forwarding via NFTables DNAT (`table ip xfwd_orchestrator`) over GRE, IPIP, FakeTCP, or AmneziaWG.
- **Core Engine Daemon:** `core/engine.py` (running 24/7 as `xforwarder.service`).
- **Modular Core Subsystems:** `core/config_manager.py`, `core/auth.py`, `core/firewall.py`, `core/proxy_gen.py`, `core/prober.py`, `core/system_info.py`, `core/service_manager.py`.
- **Web UI Dashboard:** `core/web_server.py` + `web/` (modular CSS in `web/css/`, native ES modules in `web/js/modules/`, running 24/7 as `xforwarder-web.service`).
- **CLI Controller:** `xforwarder.sh` (aliased to `xforwarder` and `xfwd`).
- **Test Suite:** `tests/` (Native Python unittest covering migrations, security, PBKDF2 auth, modular subsystems, HAProxy parser, UI, and edge cases).

---

## 2. Non-Negotiable Architectural Constraints
1. **Zero-Collision Forwarding (HIGHEST PRIORITY):** A port must **NEVER** be bound by HAProxy and forwarded by NFTables DNAT simultaneously. When Priority 1 is active, only HAProxy listens on `*:<port>`, and NFTables rules are deleted. When Priority 2 is active, HAProxy listener is removed and kernel DNAT in `table ip xfwd_orchestrator` takes over.
2. **Native Python Standard Library Only:** **ZERO third-party pip dependencies.** No Flask, FastAPI, Requests, Uvicorn, or Pydantic. Use only system Python 3 standard library modules. Combined idle RAM must remain strictly **under 15MB**.
3. **Atomic File Persistence:** Never write directly to `/etc/xforwarder/config.json` or `/run/xforwarder/state.json`. Always write to `.tmp.<pid>` and execute atomic replacement via `os.replace`.
4. **Table Isolation in NFTables:** All DNAT routing strictly resides inside `table ip xfwd_orchestrator`. **Never execute `nft flush ruleset`** or touch global firewall tables. Always pre-validate syntax with `nft -c -f -`.
5. **Non-Blocking Probes & Socket Safety:** Destination health checks must always enforce explicit bounded timeouts (`socket.create_connection(..., timeout=2.0)`). Sockets must be closed immediately after testing.
6. **Graceful HAProxy Reloading:** Use non-disruptive `systemctl reload haproxy` to preserve existing active client connections during priority switching.
7. **Pure Vanilla Frontend:** The web dashboard in `web/` must remain pure Vanilla HTML5, CSS3, and ES6+ JavaScript. No Node.js, Webpack, Vite, or npm build tooling.
8. **Knowledge Graph First (Graphify):** Before modifying shared components, query Graphify (`graphify query "<component>"`) to trace callers and pinpoint exact line numbers (`loc=Lxx`).
9. **Zero Polling & Reactive Execution:** Never use `schedule` timers or poll `manage_task(status)`. Await reactive wakeup automatically.
10. **Clean Code & DRY:** Extract repeated socket, formatting, or parsing logic into centralized, single-responsibility methods.
11. **Backward Compatibility & Automated Migrations (Mandatory):** All software updates and schema changes must remain 100% backward compatible. Never drop or overwrite existing rules, custom ports, or admin credentials. Always perform atomic pre-update backup and automatic self-healing schema normalization via `migrate_and_normalize_config()`.
12. **Multi-Layer Web Security & PBKDF2 Auth (Mandatory):** Admin credentials must use salted PBKDF2-HMAC-SHA256 (100,000 iterations + 16-byte random salt). All mutating endpoints verify origin. Login endpoints enforce adaptive rate limiting (5 attempts in 5 minutes triggers 15-minute lockout). All responses enforce OWASP security headers (CSP, X-Frame-Options DENY, SameSite=Strict cookies).
13. **Clean TCP Stream by Default & Live State Preservation:** HAProxy rules stream clean raw TCP by default without hardcoding `send-proxy-v2`. PROXY protocol v2 is strictly opt-in per destination. Ad-hoc synchronizations from the web server must merge and preserve live `rules_state` metrics without resetting `state.json`.
14. **High-Performance HTTP, Asset Caching & Fast IPC:** Web server provides native Gzip compression on JSON/static assets (>512B), ETag conditional 304 handling, and in-memory caching with mtime invalidation. Daemons perform content-diffing to skip redundant service reloads, and use SIGUSR1 IPC to wake the engine loop immediately upon changes.
15. **Two-Tier Intelligent Failover, Quality Scoring & Anti-Flapping:** Outages trigger micro-probe bursts (`_fast_confirm_burst`, `BURST_TCP_TIMEOUT = 0.5s`) confirming hard failure. Probing uses 2-packet tail padding (`ICMP_TAIL_PADDING = 2`) and sequence-aware parsing (`parse_ping_replies`) to prevent tail-truncation false drops on high-RTT links. Probes are strictly deduplicated by destination IP across all rules and ports, averaging 10 consecutive pings and caching in memory for 60 seconds (`target_probe_interval_seconds = 60s`) with immediate invalidation upon route failure. Every 15 seconds (`fast_liveness_interval_seconds = 15s`), a fast liveness check verifies reachability; if unresponsive, cache is cleared and Tier 1 emergency failover triggers immediately. Route quality evaluates rolling metrics over 5-minute sliding windows via `Score = Latency + 2*Jitter + 20*Loss% + Priority Bias`. Tier 1 immediately fails over on critical outage (hard down, route invalid, or sustained loss >= 30% across >= 2 cycles) with conntrack flush. Tier 2 conservative planned switching requires 10-minute hold (`min_hold_seconds = 600s`), 20% & 15-point advantage margin (`hysteresis_percent = 20%`), and 120s sustained streak confirmation (`switch_confirm_seconds = 120s`) while preserving active client connections without conntrack flush. Exponential flap damping doubles hold time on frequent oscillations. Nginx is stopped when 0 rules use Nginx. Priority 1 Stickiness & 150ms Latency Ceiling: When Priority 1 is active, the engine never switches away to backup priorities merely for 10-30ms lower ping; it strictly stays on Priority 1 unless Priority 1 packet loss is worse than candidate (`curr_loss > cand_loss + 0.5`), or latency exceeds 150ms (`max_primary_latency_ms = 150`), or on critical outage.
16. **Long-Term Packet Loss Monitoring & Deduplicated Probing:** 50-probe packet loss measurement (`ping [ip] -c 50 -i 0.2 -W 1`) runs every 15 minutes across all unique targets (`get_unique_targets_from_config`). Persisted in SQLite (`/etc/xforwarder/metrics.db`) with 30-day auto-pruning. Probing deduplication ensures an IP shared across N ports is only tested once per round. Web UI strictly isolates latency from packet loss: ping pill displays solely round-trip latency (`.latency-pill`, e.g. `100.1 ms`), reserving amber for elevated latency/jitter and red for severe delays or hard outages (>250ms or Down). Packet loss is rendered exclusively in its dedicated `.loss50-pill` badge with test age tooltip (e.g. `Tested 4m ago`), with automatic fallback to continuous probe loss when initial SQLite metrics are warming up. Manual 'Test Loss' button is retired.
17. **In-Panel System Updates & Service Control:** Web dashboard provides native update checking against the remote GitHub repository (`/api/system/version`) and decoupled execution via `systemd-run` (`/api/system/update`, `/api/system/update/status`). Service restart and reload controls (`POST /api/services/restart`) support granular targets (`engine`, `haproxy`, `nginx`, `nftables`) and delayed self-restarting for `web` and `all` with client reconnection polling to prevent socket dropouts.
18. **Active Rules Auto-Discovery, Import & Deconfliction (Mandatory):** Pre-existing relay rules on the server (HAProxy listen blocks or active NFTables/iptables DNAT rules in kernel tables or `/etc/nftables.conf`) must be automatically detectable via unified discovery (`discover_all_relay_rules`). When imported, an atomic ruleset snapshot must be created at `/etc/xforwarder/backups/legacy_nftables_<timestamp>.nft`. Conflicting unmanaged legacy DNAT rules must be safely deactivated using exact rule handles (`nft delete rule <family> <table> <chain> handle <id>`) to eliminate kernel PREROUTING hook collision and guarantee zero-collision forwarding.
19. **Kernel Zero-Copy Splicing, BBR Tuning & Bounded UDP Timeouts (Mandatory):** HAProxy forwarding must enforce zero-copy kernel splicing (`option splice-auto`, `tune.pipesize 262144`, `tune.bufsize 65536`) and multi-core CPU thread affinity (`nbthread {cpu_cores}`, `cpu-map`) with defensive fallback to minimize CPU usage and prevent single-core bottlenecks. Per-connection TCP logging (`option tcplog`) is forbidden on forwarding relays. Client and server TCP keepalives (`option clitcpka`, `option srvtcpka`) are mandatory. UDP stream proxying must strictly enforce bounded timeouts (`proxy_timeout 60s`) and large buffers (`proxy_buffer_size 64k`). Dynamic host network profiling (`tune_network` in `xforwarder.sh`) configures BBR, scales `somaxconn` to 65,535, sets `LimitNOFILE=1048576` for HAProxy, and scales conntrack tables.
20. **Granular Port & Category JSON Export/Import (Mandatory):** Web dashboard provides 1-click single-port rule JSON copy (`copyRuleJson`) and entire category JSON batch copy (`copyCategoryJson`) formatted for immediate import into external panels. Import engine (`import_config_data`) and modal paste textarea support full configurations (`{"rules": [...]}`), raw rules arrays (`[...]`), and single-rule dictionaries (`{"port": 443, ...}`) with pre-import atomic backups. Inline event parameters enforce safe quote-escaping (`safeInlineArg`) preventing attribute breakout or syntax errors on custom categories.
21. **Per-Port & Per-Tunnel Traffic Accounting & Delta Engine (Mandatory):** Zero-overhead kernel and proxy metrics across NFTables named counters (`cnt_in_<port>`, `cnt_out_<port>`), HAProxy runtime stats socket (`bin`, `bout`), and tunnel interface counters (`/proc/net/dev`). Delta Engine computes non-negative monotonic deltas (~30s cycles) resilient against service reloads, system reboots, and counter rollovers. Pre-aggregated hourly rollups persist in SQLite (`metrics.db` in WAL mode) with 90-day retention and multi-period analytics (24h hourly, 7d/30d daily, 12m monthly). Baseline offset reset model persists historical time-series analytics while resetting current billing cycle counters to 0, with granular reset endpoints (`POST /api/traffic/reset`).

---

## 3. Specialized Skills Index (Progressive Disclosure)
- [`xfwd-ops`](skills/xfwd-ops/SKILL.md): Master operational runbook, configuration schema, and test simulations.
- [`code-review-audit`](skills/code-review-audit/SKILL.md): 8-point security, architecture, and code quality audit checklist.
- [`systematic-debugging`](skills/systematic-debugging/SKILL.md): 4-phase systematic debugging procedure for forwarding anomalies.
- [`graphify`](skills/graphify/SKILL.md): Knowledge graph query and update workflows.
- [`fwdman-ops`](skills/fwdman-ops/SKILL.md): Backward compatibility legacy alias.

---

## 4. Active Workspace Rules (Conditional Disclosure)
- [`mandatory-checklist.md`](rules/mandatory-checklist.md): Universal task completion and pre-commit verification protocol.
- [`blast-radius-analysis.md`](rules/blast-radius-analysis.md): Pre-execution blast radius analysis across engine, firewall, and web server.
- [`backward-compatibility-and-migrations.md`](rules/backward-compatibility-and-migrations.md): Mandatory backward compatibility, atomic backup, and schema migration standards.
- [`reverse-prompting.md`](rules/reverse-prompting.md): Interactive single-question clarification protocol.
- [`session-handoff.md`](rules/session-handoff.md): Tracking task context and milestones via `session-state.json`.
- [`clean-code-dry.md`](rules/clean-code-dry.md): DRY zero-duplication rules.
- [`large-files-handling.md`](rules/large-files-handling.md): Surgical chunk editing and Graphify line referencing.
- [`relay-vps-constraints.md`](rules/relay-vps-constraints.md): Linux intermediate relay server memory, CPU, and socket constraints.
- [`ui-design-consistency.md`](rules/ui-design-consistency.md): Vanilla dark-mode glassmorphism and typography standards.
- [`experience-logging.md`](rules/experience-logging.md): Guidelines for recording lessons in `.agents/experiences/`.
- [`01-architecture-and-failover.md`](rules/01-architecture-and-failover.md): Core relay architecture and failover state machine.
- [`02-python-core-standards.md`](rules/02-python-core-standards.md): Python coding and thread-safety standards.
- [`03-networking-and-kernel.md`](rules/03-networking-and-kernel.md): NFTables, HAProxy, and kernel forwarding rules.
- [`04-web-dashboard-and-security.md`](rules/04-web-dashboard-and-security.md): Web authentication and API security.
- [`05-bash-and-deployment.md`](rules/05-bash-and-deployment.md): Bash CLI standards and service units.
- [`graphify.md`](rules/graphify.md): Codebase knowledge graph rules.

---

## 5. Workflows & Automation Scripts
- **Workflows:** [`add-port-rule.md`](workflows/add-port-rule.md) | [`diagnose-failover.md`](workflows/diagnose-failover.md) | [`deploy-update.md`](workflows/deploy-update.md) | [`graphify.md`](workflows/graphify.md)
- **Automation Scripts:**
  - `python .agents/scripts/syntax-check.py`: Automatic Python syntax verification.
  - `python -m unittest discover -s tests`: Run native unit test suite (schema migrations, regression).
  - `python .agents/scripts/session-state.py --show`: Inspect active task state and milestones.
  - `python .agents/scripts/verify-all.py`: Full pre-commit test & verification pipeline.
  - `python .agents/scripts/check-anti-patterns.py`: Scan for forbidden imports and unsafe operations.
  - `python .agents/scripts/log-experience.py`: Scaffold a new architectural experience entry.

---

## 6. Experiences Catalog
- Documented architectural decisions and lessons learned in [`.agents/experiences/README.md`](experiences/README.md).

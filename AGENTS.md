# XForwarder - Agent Development Guide

Welcome to the **XForwarder** codebase. This repository follows the advanced Antigravity Agent Engineering Architecture inspired by the [XPanel .agents Standard](file:///.agents/AGENTS.md).

## 🧭 Project Architecture
XForwarder is an ultra-lightweight, 24/7 intelligent multi-path priority failover engine and authenticated web dashboard running on Linux intermediate relay servers (e.g. Iran VPS).

```text
XForwarder/
├── core/
│   ├── engine.py          # Core failover engine daemon (<15MB RAM, main loop & IPC router)
│   ├── web_server.py      # Native Python 3 HTTP server (session auth, JSON REST API, static asset server)
│   ├── config_manager.py  # Centralized schema migrations, atomic persistence, validation, import/export
│   ├── auth.py            # Salted PBKDF2-HMAC-SHA256, persistent sessions, adaptive brute-force lockout
│   ├── firewall.py        # Isolated table ip xfwd_orchestrator NFTables ruleset generator & conntrack flusher
│   ├── proxy_gen.py       # Multi-core HAProxy (zero-copy splice-auto) & Nginx stream proxy config generators
│   ├── prober.py          # 10-probe ICMP bursts, socket health checks, route/interface isolation
│   ├── system_info.py     # System telemetry, service status cache, network topology discovery
│   ├── service_manager.py # Controlled service restarts, async updates, version detection
│   ├── metrics.py         # 50-probe packet loss engine, 15m SQLite scheduler, target deduplicator & 30d retention
│   ├── route_quality.py   # Two-tier quality scoring, sliding window, hysteresis, streak confirmation
│   ├── traffic.py         # Kernel & proxy byte accounting, hourly rollups, SQLite persistence
│   ├── haproxy_parser.py  # HAProxy configuration parser, backup locator, and rule importer
│   └── nftables_parser.py # Active kernel NFTables & iptables DNAT parser, backup creator & handle-based deconfliction
├── web/
│   ├── index.html         # Modern panel dashboard with sidebar navigation, modular sections, and light/dark theme
│   ├── style.css          # Glassmorphism aesthetic, light & dark theme design system, and responsive layout
│   ├── app.js             # Vanilla JS state manager & orchestrator (Native ES module entry point)
│   ├── css/               # Modular CSS stylesheets (tokens, base, layout, components, modals, style)
│   └── js/modules/        # Clean Vanilla ES modules (api, state, theme, navigation, auth, stats, rules, etc.)
├── config/
│   └── config.json.example# Reference configuration schema
├── systemd/
│   ├── xforwarder.service     # Systemd unit for core daemon
│   └── xforwarder-web.service # Systemd unit for web server
├── xforwarder.sh          # Root installer and interactive CLI controller (xforwarder / xfwd)
├── forward-manager.sh     # Backward compatibility wrapper for xforwarder.sh
├── tests/
│   ├── test_migration.py  # Native Python unittest suite (schema migrations & edge cases)
│   ├── test_security.py   # Native Python unittest suite (PBKDF2 auth, rate limiting & input sanitization)
│   ├── test_modular_subsystems.py # Native Python unittest suite (modular core subsystems & edge cases)
│   ├── test_haproxy_parser.py # Native Python unittest suite (HAProxy config parser & importer)
│   ├── test_nftables_parser.py# Native Python unittest suite (NFTables/iptables parser, backup & deconfliction)
│   ├── test_export_import.py  # Native Python unittest suite (sanitized config export & merge/replace restore)
│   ├── test_metrics_subsystem.py # Native Python unittest suite (50-probe ping, deduplication & SQLite retention)
│   └── test_ui_and_api_edge_cases.py # Native Python unittest suite (UI, API edge cases & static asset integrity)
├── .agents/               # Antigravity agent configuration (constitution, rules, workflows, skills, scripts)
│   ├── AGENTS.md          # Master architecture constitution
│   ├── hooks.json         # Antigravity lifecycle hooks (pre-invocation and stop syntax checks)
│   ├── mcp_config.json    # Graphify MCP server configuration
│   ├── session-state.json # Active task context and milestone tracker
│   ├── experiences/       # Architectural memory & lessons learned (001+, README.md)
│   ├── rules/             # Mandatory rules (checklist, blast radius, reverse prompting, relay constraints)
│   ├── workflows/         # Interactive runbooks (add-port-rule, diagnose-failover, deploy-update, graphify)
│   ├── skills/            # Specialized operational procedures (xfwd-ops, code-review-audit, systematic-debugging)
│   └── scripts/           # Native Python tools (verify-all, syntax-check, session-state, check-anti-patterns, log-experience)
└── graphify-out/          # Persistent code knowledge graph (graph.json, graph.html, GRAPH_REPORT.md)
```

---

## ⚡ Core Rules & Constraints

1. **Zero-Collision Forwarding (Mandatory)**:
   - A port must **never** be handled by both HAProxy and NFTables DNAT simultaneously.
   - When **Priority 1 (HAProxy)** is active, only HAProxy binds `*:<port>`, and NFTables DNAT rules for that port are removed.
   - When **Priority 2 (NFTables)** is active, HAProxy does not bind that port, and kernel DNAT in `table ip xfwd_orchestrator` takes over.

2. **Native Python Standard Library Only**:
   - Do NOT add external pip dependencies (like Flask, FastAPI, Requests, Uvicorn).
   - Use only native Python 3 modules (`http.server`, `socket`, `threading`, `subprocess`, `json`, `hashlib`, `time`, `signal`).
   - Combined idle RAM usage must remain under **15MB**.

3. **Atomic File Persistence**:
   - State (`/run/xforwarder/state.json`) and config (`/etc/xforwarder/config.json`) must be written via temporary files and `os.replace` to prevent corruption.

4. **Table Isolation in NFTables**:
   - Never execute `nft flush ruleset`. Only isolate and manage `table ip xfwd_orchestrator`.

5. **Vanilla Frontend**:
   - The web dashboard in `web/` must remain pure Vanilla HTML5/CSS3/JavaScript without Node.js, Webpack, or NPM build tooling.

6. **Backward Compatibility & Automated Schema Migrations (Mandatory)**:
   - Any update (`xforwarder update` or CLI upgrade) must guarantee 100% backward compatibility with prior versions.
   - Updates must NEVER drop, overwrite, or corrupt existing port forwarding rules, user credentials, or custom ports.
   - All migrations must be automated, self-healing (`migrate_and_normalize_config`), idempotent, and preceded by an atomic configuration backup (`config.json.bak.<timestamp>`).
   - Detailed rule: `.agents/rules/backward-compatibility-and-migrations.md`.

7. **Multi-Layer Web Security & PBKDF2 Auth (Mandatory)**:
   - Admin credentials must use salted PBKDF2-HMAC-SHA256 (100,000 iterations + 16-byte random salt) with self-healing legacy SHA-256 upgrade.
   - Adaptive brute-force protection: 5 failed attempts in 5 minutes triggers a 15-minute IP lockout (HTTP 429).
   - OWASP defense in depth: enforce CSP, X-Frame-Options DENY, SameSite=Strict HttpOnly cookies, and CSRF origin validation.

8. **Clean TCP Stream by Default & Runtime State Preservation (Mandatory)**:
   - HAProxy forwarding must stream clean raw TCP by default. Never unconditionally append `send-proxy-v2` because upstream proxies (Xray, Trojan, Nginx) drop unexpected PROXY protocol headers. Only send PROXY protocol v2 when `proxy_protocol` is explicitly enabled.
   - Live health checks must strictly test the specific destination and port (falling back to rule port if omitted) and provide real-time diagnostic reporting via `POST /api/test-target`.
   - Ad-hoc sync calls (`sync_system_rules()`) from the web server must never erase live `rules_state` metrics in `/run/xforwarder/state.json`.

9. **High-Performance HTTP, In-Memory Asset Caching & Fast IPC (Mandatory)**:
   - Web server provides native Gzip compression on JSON responses and static assets (>512B) with correct Content-Length framing.
   - Enforce ETag conditional requests (`304 Not Modified`) and in-memory static caching (`_STATIC_CACHE`) with mtime invalidation for instant panel responsiveness.
   - Selective service reloads: HAProxy, Nginx, and NFTables rules are compared before issuing reloads, preventing redundant service signals.
   - Fast IPC: Core engine uses `SIGUSR1` signal wake-up via candidate PID files for instant evaluation when the web dashboard commits changes.

10. **Two-Tier Intelligent Failover, Quality Scoring & Anti-Flapping (Mandatory)**:
    - 10-Probe ICMP Precision & Jitter: Probes execute 10-ping bursts (`ping -c 10 -i 0.2 -W 1`) with 2-packet tail padding (`ICMP_TAIL_PADDING = 2`) and sequence-aware evaluation (`parse_ping_replies`) to eliminate tail-truncation false drops on long RTTs. Extracts average latency, packet loss, and within-cycle jitter (`mdev`). Parallel probing deduplicates endpoints across rules with persistent worker pool.
    - Strict Per-IP Probing, 60-Second In-Memory Cache & 15-Second Fast Liveness: Probes are strictly deduplicated by destination IP across all rules and ports. An IP configured on multiple ports (e.g. 5 or 50 ports) is probed exactly once with 10 consecutive pings and cached in memory for 60 seconds (`target_probe_interval_seconds = 60s`). Every 15 seconds (`fast_liveness_interval_seconds = 15s`), a fast liveness check validates reachability; if unresponsive (100% loss), cache is invalidated and Tier 1 emergency failover triggers immediately. When reachable, the 60s 10-ping average latency and composite score remain active and stable. Target routes that become invalid or dropped are evicted immediately from cache.
    - Composite Quality Scoring: Evaluates routes over a 5-minute sliding window via `Score = Latency + 2*Jitter + 20*Loss% + Priority Bias`.
    - Tier 1 Emergency Outage Failover: Total failure (100% loss), route invalidation, or sustained critical degradation (>=30% loss across >=2 cycles in the short window) triggers micro-probe confirmation (`BURST_TCP_TIMEOUT = 0.5s`) and immediate failover bypassing hold times, with conntrack flushed. Transient single-cycle loss blips degrade quality without triggering disruptive emergency failovers.
    - Tier 2 Conservative Planned Switching: Prevents disruptive route flapping on live client sessions via 10-minute hold guard (`min_hold_seconds = 600s`), 60% window warm-up, packet loss protection (never switch to higher loss), 20% & 15-point score margin, and 120s sustained streak confirmation. Planned switches reload HAProxy seamlessly without flushing conntrack, preserving existing client connections. Nginx is stopped when 0 rules use Nginx.
    - Priority 1 Stickiness & 150ms Latency Ceiling: When Priority 1 is currently active, the engine never switches away to backup priorities merely because a backup has lower ping (10-30ms lower). It strictly remains on Priority 1 unless Priority 1 suffers higher packet loss than the candidate (`curr_loss > cand_loss + 0.5`), or its latency exceeds 150ms (`max_primary_latency_ms = 150`), or upon critical failure.

11. **Long-Term Packet Loss Monitoring & Deduplicated Probing (Mandatory)**:
    - 50-Probe Precision: Detailed packet loss measurement uses `ping [ip] -c 50 -i 0.2 -W 1` (<10s).
    - 15-Minute Background Daemon: `LossMonitorScheduler` runs periodic rounds every 900 seconds.
    - Zero-Redundancy Target Deduplication: Targets across all rules and ports are deduplicated (`get_unique_targets_from_config`); testing is performed strictly once per IP regardless of port count.
    - 30-Day SQLite Time-Series Retention: Metrics are persisted in `/etc/xforwarder/metrics.db` (WAL mode) and automatically pruned after 30 days to protect disk storage.
    - In-Panel Path Metrics & Strict Badge Isolation: Web UI strictly isolates latency from packet loss. The ping badge displays solely the round-trip latency (`.latency-pill`, e.g. `100.1 ms`), reserving amber for elevated latency/jitter and red for severe delays or hard outages (>250ms or Down). Packet loss is rendered exclusively in its dedicated `.loss50-pill` badge with test age tooltip (e.g. `Tested 4m ago`), with automatic fallback to continuous probe loss when initial SQLite metrics are warming up. Manual 'Test Loss' button is retired.

12. **In-Panel System Updates & Service Control (Mandatory)**:
    - Remote Release & Update Engine: Web dashboard compares local git commit/version against remote GitHub repository (`/api/system/version`) and initiates decoupled update executions via `systemd-run` (`/api/system/update`, `/api/system/update/status`).
    - Controlled Service Lifecycle: Dashboard provides controlled service restart/reload capabilities (`POST /api/services/restart`) supporting individual targets (`engine`, `haproxy`, `nginx`, `nftables`) and graceful delayed self-restarts for `web` and `all` with UI reconnection polling.

13. **Active Rules Auto-Discovery, Import & Deconfliction (Mandatory)**:
    - Pre-existing relay rules on the server (HAProxy listen blocks or active NFTables/iptables DNAT rules in kernel tables or `/etc/nftables.conf`) must be automatically detectable via unified discovery (`discover_all_relay_rules`).
    - When imported, an atomic ruleset snapshot must be created at `/etc/xforwarder/backups/legacy_nftables_<timestamp>.nft`.
    - Conflicting unmanaged legacy DNAT rules must be safely deactivated using exact rule handles (`nft delete rule <family> <table> <chain> handle <id>`) to eliminate kernel PREROUTING hook collision and guarantee zero-collision forwarding.

14. **Kernel Zero-Copy Splicing, BBR Tuning & Bounded UDP Timeouts (Mandatory)**:
    - HAProxy forwarding must enforce zero-copy kernel splicing (`option splice-auto`, `tune.pipesize 262144`, `tune.bufsize 65536`) and multi-core CPU thread affinity (`nbthread {cpu_cores}`, `cpu-map`) with defensive fallback to minimize CPU usage, prevent single-core bottlenecks, and avoid user-space buffer copies.
    - Per-connection TCP logging (`option tcplog`) is forbidden on forwarding relays; logging is restricted to `notice` level and error states.
    - Client and server TCP keepalives (`option clitcpka`, `option srvtcpka`) are mandatory to sweep zombie connections.
    - UDP stream proxying must strictly enforce bounded timeouts (`proxy_timeout 60s`) and large buffers (`proxy_buffer_size 64k`) to eliminate UDP socket and memory accumulation.
    - Dynamic host network profiling (`tune_network` in `xforwarder.sh`) automatically configures BBR congestion control, scales `somaxconn` to 65,535, expands socket buffers, sets `LimitNOFILE=1048576` for HAProxy, and scales conntrack tables.

15. **Granular Port & Category JSON Export/Import (Mandatory)**:
    - Web dashboard provides 1-click single-port rule JSON copy (`copyRuleJson`) and entire category JSON batch copy (`copyCategoryJson`) formatted for immediate import into external panels.
    - Import engine (`import_config_data`) and modal paste textarea support full configurations (`{"rules": [...]}`), raw rules arrays (`[...]`), and single-rule dictionaries (`{"port": 443, ...}`) with pre-import atomic backups.
    - Inline event parameters enforce safe quote-escaping (`safeInlineArg`) preventing attribute breakout or syntax errors on custom categories.

16. **Per-Port & Per-Tunnel Traffic Accounting & Delta Engine (Mandatory)**:
    - Zero-Overhead Kernel & Proxy Metrics: NFTables forwarding tracks established TCP/UDP streams via kernel named counters (`cnt_in_<port>`, `cnt_out_<port>`). HAProxy runtime stats socket streams client upload/download bytes (`bin`, `bout`). Tunnel interfaces track wire traffic directly via `/proc/net/dev`.
    - Delta Engine: Raw kernel and proxy counters are sampled periodically (~30s), computing non-negative monotonic deltas immune to service reloads, system reboots, and counter roll-overs.
    - Pre-Aggregated Hourly Rollups: Hourly traffic records (`traffic_hourly`) persist in SQLite (`metrics.db` in WAL mode) with 90-day retention and auto-pruning. Multi-granularity queries provide 24h (hourly), 7d/30d (daily), and 12m (monthly) analytical breakdowns with upload (RX), download (TX), and total usage.
    - Baseline Offset Reset Model: Billing cycle resets persist current totals in `traffic_resets` as baseline offsets. The current billing cycle counter resets instantly to 0 while historical analytical time-series charts remain intact. Granular reset endpoints (`/api/traffic/reset`) support all entities, single ports (1-65535), and tunnel interfaces with optional permanent history wipe (`wipe_history=true`).

17. **Destination Enable/Disable (On/Off Toggle) Subsystem (Mandatory)**:
    - Each priority path in a rule supports interactive enable/disable toggling (`enabled: true/false`).
    - When disabled, the destination is retained in configuration and UI for effortless reactivation, but is completely excluded from probing, route quality evaluation, active priority switching, and proxy/firewall generation.
    - Disabling the currently active priority or a manually forced priority automatically triggers immediate fallback to the next best enabled priority.

18. **Intermediate Relay (`is_relay`) & Primary Anchor Subsystem (Mandatory)**:
    - Intermediate relay nodes (where ICMP ping measures only hop 1 to an intermediate relay or tunnel node) can be explicitly marked (`is_relay: true`).
    - The engine enforces the Primary Anchor pattern: Priority 1 is protected as the authoritative destination as long as it has no packet loss and latency <= 150ms.
    - Low hop ping on an intermediate relay never supersedes healthy Priority 1.
    - When active on an intermediate relay, the engine triggers failback to Priority 1 as soon as Priority 1 recovers.




---

## 🔍 Codebase Knowledge Graph (graphify)
This repository has an active graphify knowledge graph at `graphify-out/`:
- **CLI Query**: Run `graphify query "<question>"` to query symbols, calls, and relationships.
- **Paths**: Run `graphify path "<SymbolA>" "<SymbolB>"` to trace paths between components.
- **Update**: Run `graphify update .` after modifying code files (AST-based, instant, zero API cost).
- **Interactive Visualizer**: Open `graphify-out/graph.html` in a browser.
- **Audit Report**: Review `graphify-out/GRAPH_REPORT.md`.

---

## 🛠 Workflows, Skills & Verification Pipeline
- Full Pre-Commit Verification: `python .agents/scripts/verify-all.py`
- Session State Tracker: `python .agents/scripts/session-state.py --show`
- Rule Creation: `.agents/workflows/add-port-rule.md`
- Diagnostic Workflow: `.agents/workflows/diagnose-failover.md`
- Deployment Workflow: `.agents/workflows/deploy-update.md`
- Master Operations Skill: `.agents/skills/xfwd-ops/SKILL.md`
- Code Review & Audit: `.agents/skills/code-review-audit/SKILL.md`
- Systematic Debugging: `.agents/skills/systematic-debugging/SKILL.md`
- Experiences Catalog: `.agents/experiences/README.md`

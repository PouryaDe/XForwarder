# XForwarder Master Architecture Constitution

Authoritative architectural rules and standard operating procedures for AI agents in **XForwarder** (Python 3 Native Multi-Path Relay & Failover Engine).

---

## 1. Project Overview & Terminology
- **Intermediate Relay Server:** Linux VPS (e.g. Iran) bridging local clients to foreign exit nodes.
- **Priority 1 (Primary Relay):** Direct user-space TCP/UDP IPv6 relay via HAProxy (`/etc/haproxy/haproxy.cfg`).
- **Priority 2 (Backup Tunnel):** Kernel Layer-3 tunnel forwarding via NFTables DNAT (`table ip xfwd_orchestrator`) over GRE, IPIP, FakeTCP, or AmneziaWG.
- **Core Engine Daemon:** `core/engine.py` (running 24/7 as `xforwarder.service`).
- **Web UI Dashboard:** `core/web_server.py` + `web/` (running 24/7 as `xforwarder-web.service`).
- **CLI Controller:** `xforwarder.sh` (aliased to `xforwarder` and `xfwd`).
- **Test Suite:** `tests/` (Native Python unittest covering migrations, security, PBKDF2 auth, HAProxy parser, UI, and edge cases).

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

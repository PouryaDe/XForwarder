# XForwarder - Agent Development Guide

Welcome to the **XForwarder** codebase. This repository follows the advanced Antigravity Agent Engineering Architecture inspired by the [XPanel .agents Standard](file:///.agents/AGENTS.md).

## 🧭 Project Architecture
XForwarder is an ultra-lightweight, 24/7 intelligent multi-path priority failover engine and authenticated web dashboard running on Linux intermediate relay servers (e.g. Iran VPS).

```text
XForwarder/
├── core/
│   ├── engine.py          # Core failover engine daemon (<15MB RAM, socket health prober, firewall/proxy syncer)
│   └── web_server.py      # Native Python 3 HTTP server (session auth, JSON REST API, static asset server)
├── web/
│   ├── index.html         # Modern panel dashboard with sidebar navigation, modular sections, and light/dark theme
│   ├── style.css          # Glassmorphism aesthetic, light & dark theme design system, and responsive layout
│   └── app.js             # Vanilla JS state manager, auto-polling, section switcher, and real-time UI renderer
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
│   ├── test_haproxy_parser.py # Native Python unittest suite (HAProxy config parser & importer)
│   ├── test_export_import.py  # Native Python unittest suite (sanitized config export & merge/replace restore)
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

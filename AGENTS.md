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
│   ├── index.html         # Modern dark-mode dashboard with login card and rule management modals
│   ├── style.css          # Glassmorphism aesthetic and responsive layouts
│   └── app.js             # Vanilla JS state manager, auto-polling, and real-time UI renderer
├── config/
│   └── config.json.example# Reference configuration schema
├── systemd/
│   ├── xforwarder.service     # Systemd unit for core daemon
│   └── xforwarder-web.service # Systemd unit for web server
├── xforwarder.sh          # Root installer and interactive CLI controller (xforwarder / xfwd)
├── forward-manager.sh     # Backward compatibility wrapper for xforwarder.sh
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

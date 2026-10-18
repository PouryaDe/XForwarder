---
name: blast-radius-analysis
description: "Pre-execution blast radius analysis across engine daemons, firewall tables, HAProxy configs, and Web UI before modifying shared code."
always_on: false
trigger: model_decision
---

# Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder)

In real-time network forwarding, modifying a single method in the failover engine or firewall syncer can cause traffic blackholes or port binding collisions.

Before editing any shared or core component, AI agents MUST assess the **Blast Radius**.

---

## 1. High-Risk Core Components

Any modification to the following components requires a mandatory blast radius check:

1. **Routing & Firewall Syncer (`core/engine.py`):**
   - `sync_firewall_and_proxies()`: Synchronizes HAProxy listeners and NFTables DNAT. Regressions here cause port collisions or traffic drop.
   - `_apply_nftables()`: Generates `table ip xfwd_orchestrator`. Regressions can break kernel DNAT or masquerading across tunnel interfaces.
   - `_apply_haproxy()`: Writes `/etc/haproxy/haproxy.cfg`. Regressions can crash HAProxy or disrupt active established client connections.
   - `evaluate_rule()`: Determines healthy/failed state and triggers failover. Bugs here cause rapid switching flaps.
2. **Web API & Authentication (`core/web_server.py`):**
   - `get_session_token()` & `is_authenticated()`: Regressions could lock out the admin or expose `/api/*` endpoints unauthenticated.
   - `save_config()` & `load_config()`: Regressions can corrupt `/etc/xforwarder/config.json`.
3. **Installer & Service Lifecycle (`xforwarder.sh`):**
   - `install_xforwarder()`: Configures systemd units, symlinks, and kernel `net.ipv4.ip_forward`. Regressions can leave servers in an unbootable forwarding state.

---

## 2. Constitution Check Gate

Before modifying files, verify that the proposed change does not breach any core constraint:

1. **Zero-Collision Rule:** A port must NEVER be bound by HAProxy and DNAT'd by NFTables simultaneously.
2. **Native Standard Library Only:** Never import external pip dependencies (`requests`, `flask`, `fastapi`).
3. **Table Isolation in NFTables:** Never execute `nft flush ruleset`. Only isolate and delete `table ip xfwd_orchestrator`.
4. **Atomic File Persistence:** Always write temporary files (`.tmp.<pid>`) and use `os.replace`.
5. **Pure Vanilla Web:** Never introduce Node.js, Webpack, or NPM dependencies into `web/`.
6. **Codebase Knowledge Graph Discovery:** Use Graphify (`graphify query "<component>"`) to trace callers before changing function signatures.

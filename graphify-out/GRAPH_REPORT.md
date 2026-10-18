# Graph Report - Forward-Manager  (2026-10-19)

## Corpus Check
- 47 files · ~27,451 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .service 4, (none) 2, .example 1)

## Summary
- 474 nodes · 790 edges · 27 communities (26 shown, 1 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 19 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d980f94f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- os
- app.js
- XForwarderEngine
- fetchStatus
- web_server.py
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- .migrate_and_normalize_config
- experiences/README.md
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- Architecture & Failover Rules (XForwarder)
- The 8-Point Audit Checklist
- Networking & Kernel Standards (XForwarder)
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- showToast
- .do_POST
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Session State & Task Handoff Rule (XForwarder)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 22 edges
2. `xforwarder.sh script` - 15 edges
3. `XForwarderWebHandler` - 13 edges
4. `check_root()` - 12 edges
5. `modify_web_settings_menu()` - 12 edges
6. `show_web_access_info()` - 12 edges
7. `msg_ok()` - 11 edges
8. `resolve_active_config()` - 11 edges
9. `load_config()` - 10 edges
10. `TestXForwarderSecurity` - 10 edges

## Surprising Connections (you probably didn't know these)
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/web_server.py
- `2. Mandatory Helper Centralization` --references--> `hash_password()`  [INFERRED]
  .agents/rules/clean-code-dry.md → core/web_server.py
- `TestXForwarderMigration` --uses--> `XForwarderEngine`  [INFERRED]
  tests/test_migration.py → core/engine.py

## Import Cycles
- None detected.

## Communities (27 total, 1 thin omitted)

### Community 0 - "os"
Cohesion: 0.09
Nodes (18): check_file(), main(), get_next_number(), main(), slugify(), load_state(), main(), save_state() (+10 more)

### Community 1 - "app.js"
Cohesion: 0.03
Nodes (60): basePath, batchSelect, btnCancelModal, btnCancelSecurity, btnClearSearch, btnCloseModal, btnCloseSecurityModal, btnDismissImportBanner (+52 more)

### Community 2 - "XForwarderEngine"
Cohesion: 0.08
Nodes (17): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`), 1. High-Risk Core Components, 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder) (+9 more)

### Community 3 - "fetchStatus"
Cohesion: 0.22
Nodes (10): checkAuth(), checkImportableRules(), escapeHtml(), fetchStatus(), formatLatencyBadge(), renderRules(), renderStats(), renderSystemStats() (+2 more)

### Community 4 - "web_server.py"
Cohesion: 0.05
Nodes (18): check_syntax(), get_modified_py_files(), main(), main(), run_step(), show_git_status(), validate_json_files(), handle_sig() (+10 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.36
Nodes (24): change_all_web_settings(), change_password(), change_web_password(), change_web_port(), change_web_secret_path(), change_web_username(), check_root(), detect_wan_iface() (+16 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

### Community 8 - ".migrate_and_normalize_config"
Cohesion: 0.05
Nodes (25): 1. Project Overview & Terminology, 2. Non-Negotiable Architectural Constraints, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution, 🔍 Codebase Knowledge Graph (graphify) (+17 more)

### Community 9 - "experiences/README.md"
Cohesion: 0.06
Nodes (28): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+20 more)

### Community 10 - "Mandatory Task Completion & Verification Workflow (XForwarder)"
Cohesion: 0.18
Nodes (10): 0. Requirements Clarification & Blast Radius, 1. Code Verification & Syntax, 2. Automated Verification Pipeline, 3. Requirement Convergence, 4. Documentation Synchronization, 5. UI Consistency (If Web Modified), 6. Experience Logging, 7. Safe Git Operations & Token Efficiency (+2 more)

### Community 11 - "Workflow: Add Port Rule"
Cohesion: 0.33
Nodes (5): Step 1: Gather Rule Parameters, Step 2: Validate Target Reachability, Step 3: Register Rule in Configuration, Step 4: Verify Synchronization, Workflow: Add Port Rule

### Community 12 - "Workflow: Diagnose Failover & Forwarding"
Cohesion: 0.33
Nodes (5): Step 1: Check Runtime Daemon State, Step 2: Check Systemd Logs, Step 3: Verify Zero-Collision Rule Enforcement, Step 4: Test Manual Override, Workflow: Diagnose Failover & Forwarding

### Community 13 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 3. Failover & Recovery Dynamics, 4. State & Configuration Persistence, Architecture & Failover Rules (XForwarder)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, Networking & Kernel Standards (XForwarder)

### Community 16 - "Large Files Inspection & Surgical Editing Rule"
Cohesion: 0.40
Nodes (4): 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite), 3. Immediate Syntax Verification, Large Files Inspection & Surgical Editing Rule

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Consistency Standards (`web/`)"
Cohesion: 0.40
Nodes (4): 1. Visual Aesthetics & Theme Guidelines, 2. Typography Standard, 3. Technology Stack & Runtime, UI Design & Consistency Standards (`web/`)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 22 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 23 - "showToast"
Cohesion: 0.33
Nodes (7): askConfirm(), copyText(), deleteRule(), fallbackCopy(), handleOverrideChange(), showToast(), startLockoutTimer()

### Community 24 - ".do_POST"
Cohesion: 0.18
Nodes (5): get_config_path(), load_config(), save_config(), XForwarderWebHandler, XForwarderWebServer

### Community 25 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 26 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

## Knowledge Gaps
- **175 isolated node(s):** `basePath`, `currentRules`, `lastRuntime`, `loginScreen`, `dashboardScreen` (+170 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 236 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `.migrate_and_normalize_config`, `web_server.py`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **What connects `basePath`, `currentRules`, `lastRuntime` to the rest of the system?**
  _175 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `os` be split into smaller, more focused modules?**
  _Cohesion score 0.09059233449477352 - nodes in this community are weakly interconnected._
- **Why does `XForwarder Master Architecture Constitution` connect `.migrate_and_normalize_config` to `.agents/AGENTS.md`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.029850746268656716 - nodes in this community are weakly interconnected._
- **Why does `hash_password()` connect `web_server.py` to `.do_POST`, `experiences/README.md`, `XForwarderEngine`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Should `XForwarderEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.07682926829268293 - nodes in this community are weakly interconnected._
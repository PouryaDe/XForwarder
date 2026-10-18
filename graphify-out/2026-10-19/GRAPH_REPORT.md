# Graph Report - Forward-Manager  (2026-10-18)

## Corpus Check
- 44 files · ~18,481 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .service 4, (none) 2, .example 1)

## Summary
- 337 nodes · 515 edges · 27 communities (25 shown, 2 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `43f945e6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- web_server.py
- app.js
- XForwarderEngine
- forward-manager.sh
- engine.py
- 🌐 XForwarder (مدیر هوشمند اولویت‌بندی، رله و فورواردینگ تونل‌ها)
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
- XForwarder Operations Runbook
- 2. Mandatory Helper Centralization
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Session State & Task Handoff Rule (XForwarder)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 22 edges
2. `install_xforwarder()` - 10 edges
3. `update_xforwarder()` - 10 edges
4. `Mandatory Task Completion & Verification Workflow (XForwarder)` - 10 edges
5. `load_config()` - 9 edges
6. `XForwarderWebHandler` - 9 edges
7. `show_menu()` - 9 edges
8. `The 8-Point Audit Checklist` - 9 edges
9. `save_config()` - 8 edges
10. `TestXForwarderMigration` - 8 edges

## Surprising Connections (you probably didn't know these)
- `2. Mandatory Helper Centralization` --references--> `hash_password()`  [INFERRED]
  .agents/rules/clean-code-dry.md → core/web_server.py
- `TestXForwarderMigration` --uses--> `XForwarderEngine`  [INFERRED]
  tests/test_migration.py → core/engine.py

## Import Cycles
- None detected.

## Communities (27 total, 2 thin omitted)

### Community 0 - "web_server.py"
Cohesion: 0.11
Nodes (9): get_config_path(), hash_password(), is_port_in_use_by_external_service(), load_config(), load_state(), save_config(), validate_rule(), XForwarderWebHandler (+1 more)

### Community 1 - "app.js"
Cohesion: 0.09
Nodes (28): btnCancelModal, btnCloseModal, btnLogout, btnOpenAddModal, checkAuth(), currentRules, currentUsernameEl, dashboardScreen (+20 more)

### Community 2 - "XForwarderEngine"
Cohesion: 0.11
Nodes (9): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`), 1. High-Risk Core Components, 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder) (+1 more)

### Community 4 - "engine.py"
Cohesion: 0.11
Nodes (17): check_file(), main(), get_next_number(), main(), slugify(), load_state(), main(), save_state() (+9 more)

### Community 5 - "🌐 XForwarder (مدیر هوشمند اولویت‌بندی، رله و فورواردینگ تونل‌ها)"
Cohesion: 0.25
Nodes (7): 🌐 XForwarder (مدیر هوشمند اولویت‌بندی، رله و فورواردینگ تونل‌ها), اجرای اسکریپت نصب:, ⚡ ۱. معماری و نحوه عملکرد سیستم, 🚀 ۲. ویژگی‌های کلیدی, 📦 ۳. راهنمای نصب و راه‌اندازی, 🛠 ۴. دستورات خط فرمان (CLI Commands), 🖥 ۵. راهنمای استفاده از پنل وب (Web Dashboard)

### Community 6 - "xforwarder.sh"
Cohesion: 0.40
Nodes (16): change_password(), check_root(), detect_wan_iface(), detect_wan_ip(), ensure_dependencies(), install_xforwarder(), msg_err(), msg_info() (+8 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

### Community 8 - ".migrate_and_normalize_config"
Cohesion: 0.05
Nodes (25): 1. Project Overview & Terminology, 2. Non-Negotiable Architectural Constraints, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution, 🔍 Codebase Knowledge Graph (graphify) (+17 more)

### Community 9 - "experiences/README.md"
Cohesion: 0.07
Nodes (22): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+14 more)

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

### Community 23 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 24 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 25 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 26 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

## Knowledge Gaps
- **125 isolated node(s):** `forward-manager.sh script`, `currentRules`, `loginScreen`, `dashboardScreen`, `loginForm` (+120 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 159 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `.migrate_and_normalize_config`, `web_server.py`, `engine.py`?**
  _High betweenness centrality (0.225) - this node is a cross-community bridge._
- **What connects `forward-manager.sh script`, `currentRules`, `loginScreen` to the rest of the system?**
  _125 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `web_server.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11363636363636363 - nodes in this community are weakly interconnected._
- **Why does `XForwarder Master Architecture Constitution` connect `.migrate_and_normalize_config` to `.agents/AGENTS.md`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08817204301075268 - nodes in this community are weakly interconnected._
- **Should `XForwarderEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.10887096774193548 - nodes in this community are weakly interconnected._
- **Should `engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10512820512820513 - nodes in this community are weakly interconnected._
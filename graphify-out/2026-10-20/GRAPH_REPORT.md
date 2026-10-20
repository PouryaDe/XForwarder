# Graph Report - Forward-Manager  (2026-10-20)

## Corpus Check
- 55 files · ~53,694 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .service 4, (none) 2, .example 1)

## Summary
- 751 nodes · 1290 edges · 43 communities (39 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8b6f8327`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestXForwarderSecurity
- app.js
- .do_POST
- showDashboard
- 🛠 بخش اول: بهینه‌سازی سمت سرور (Server-Side Optimizations)
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
- os
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- renderDestinationRow
- showToast
- renderRules
- engine.py
- syntax-check.py
- web_server.py
- load_config
- XForwarderEngine
- TestUIAndAPIEdgeCases
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- XForwarder Operations Runbook
- json
- Session State & Task Handoff Rule (XForwarder)
- haproxy_parser.py
- get_network_interfaces_info
- TestNginxStreamEngine
- sync_system_rules
- XForwarder Master Architecture Constitution
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- test_export_import.py

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 41 edges
2. `TestUIAndAPIEdgeCases` - 25 edges
3. `load_config()` - 19 edges
4. `xforwarder.sh script` - 19 edges
5. `XForwarderWebHandler` - 18 edges
6. `check_root()` - 18 edges
7. `import_config_data()` - 15 edges
8. `validate_rule()` - 15 edges
9. `msg_ok()` - 15 edges
10. `resolve_active_config()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `۱. رندر هوشمند و تفکیکی بدون تخریب کل DOM (`web/app.js`)` --references--> `renderRules()`  [INFERRED]
  implement.md → web/app.js
- `2. Core Dynamics & Low-Resource Relay Safeguards` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `4. Invariants & Rules for AI Agents` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `2. Root Cause / Core Dynamics` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/007-fix-haproxy-silent-drop-and-state-wipeout.md → core/engine.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/web_server.py

## Import Cycles
- None detected.

## Communities (43 total, 4 thin omitted)

### Community 0 - "TestXForwarderSecurity"
Cohesion: 0.09
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 1 - "app.js"
Cohesion: 0.02
Nodes (106): basePath, batchSelect, btnAddDestination, btnCancelImportModal, btnCancelModal, btnCancelSecurity, btnClearLogs, btnClearSearch (+98 more)

### Community 2 - ".do_POST"
Cohesion: 0.17
Nodes (6): get_system_stats(), load_state(), notify_engine_wakeup(), sync_rules_and_notify(), XForwarderWebHandler, 📋 ترتیب مراحل پیاده‌سازی (Execution Steps)

### Community 3 - "showDashboard"
Cohesion: 0.33
Nodes (6): checkAuth(), checkImportableRules(), closeMobileSidebar(), showDashboard(), showLogin(), switchSection()

### Community 4 - "🛠 بخش اول: بهینه‌سازی سمت سرور (Server-Side Optimizations)"
Cohesion: 0.12
Nodes (16): 🎯 اصول و خطوط قرمز طراحی (Core Principles), 🛠 بخش اول: بهینه‌سازی سمت سرور (Server-Side Optimizations), 🎨 بخش دوم: بهینه‌سازی سمت فرانت‌اند (Frontend Optimizations), 🔒 بخش سوم: اعتبارسنجی امنیتی، ساختاری و جلوگیری از Over-Engineering, نقشه اجرایی بهینه‌سازی عملکرد و شتاب‌بخشی XForwarder (Implementation Plan), ۱. رندر هوشمند و تفکیکی بدون تخریب کل DOM (`web/app.js`), ۱. فشرده‌سازی درجا با Gzip در وب‌سرور (`core/web_server.py`), ۲. دی‌بانس (Debounce) ورودی جستجو (`web/app.js`) (+8 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.34
Nodes (29): backup_restore_menu(), change_all_web_settings(), change_password(), change_web_password(), change_web_port(), change_web_secret_path(), change_web_ssl(), change_web_username() (+21 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

### Community 8 - ".migrate_and_normalize_config"
Cohesion: 0.07
Nodes (13): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup (+5 more)

### Community 9 - "experiences/README.md"
Cohesion: 0.05
Nodes (32): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+24 more)

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
Cohesion: 0.29
Nodes (6): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 3. Failover & Recovery Dynamics, 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "os"
Cohesion: 0.29
Nodes (5): check_file(), main(), get_next_number(), main(), slugify()

### Community 16 - "Large Files Inspection & Surgical Editing Rule"
Cohesion: 0.40
Nodes (4): 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite), 3. Immediate Syntax Verification, Large Files Inspection & Surgical Editing Rule

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 19 - ".agents/AGENTS.md"
Cohesion: 0.29
Nodes (4): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 22 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 23 - "renderDestinationRow"
Cohesion: 0.22
Nodes (13): addDestinationRow(), editRule(), getPrioTagClass(), handleModalPrioDragEnd(), handleModalPrioDragLeave(), handleModalPrioDragOver(), handleModalPrioDragStart(), handleModalPrioDrop() (+5 more)

### Community 24 - "showToast"
Cohesion: 0.22
Nodes (10): applyTheme(), copyIpToClipboard(), copyText(), fallbackCopy(), handleExportConfig(), initTheme(), runLivePacketLossTest(), showToast() (+2 more)

### Community 25 - "renderRules"
Cohesion: 0.13
Nodes (22): addLogEntry(), askConfirm(), computeRulesFingerprint(), deleteRule(), escapeHtml(), fetchStatus(), formatConciseReason(), formatEngineVersion() (+14 more)

### Community 27 - "syntax-check.py"
Cohesion: 0.24
Nodes (7): check_syntax(), get_modified_py_files(), main(), main(), run_step(), show_git_status(), validate_json_files()

### Community 28 - "web_server.py"
Cohesion: 0.11
Nodes (5): check_rate_limit(), is_valid_target(), record_failed_login(), validate_rule(), verify_password()

### Community 29 - "load_config"
Cohesion: 0.20
Nodes (4): export_config_data(), import_config_data(), load_config(), TestExportImport

### Community 30 - "XForwarderEngine"
Cohesion: 0.05
Nodes (14): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout, 3. Network Probing Standards (+6 more)

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 34 - "json"
Cohesion: 0.52
Nodes (4): load_state(), main(), save_state(), show_state()

### Community 35 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 36 - "haproxy_parser.py"
Cohesion: 0.17
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 37 - "get_network_interfaces_info"
Cohesion: 0.14
Nodes (10): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder), get_network_interfaces_info(), do_ping(), is_ignored_interface() (+2 more)

### Community 39 - "sync_system_rules"
Cohesion: 0.11
Nodes (13): 🔍 Codebase Knowledge Graph (graphify), ⚡ Core Rules & Constraints, 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering (+5 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

## Knowledge Gaps
- **244 isolated node(s):** `basePath`, `currentRules`, `lastRuntime`, `loginScreen`, `dashboardScreen` (+239 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 378 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `📋 ترتیب مراحل پیاده‌سازی (Execution Steps)` connect `.do_POST` to `renderRules`, `🛠 بخش اول: بهینه‌سازی سمت سرور (Server-Side Optimizations)`?**
  _High betweenness centrality (0.355) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `XForwarderWebHandler`) actually correct?**
  _`XForwarderEngine` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `basePath`, `currentRules`, `lastRuntime` to the rest of the system?**
  _244 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestXForwarderSecurity` be split into smaller, more focused modules?**
  _Cohesion score 0.08547008547008547 - nodes in this community are weakly interconnected._
- **Why does `renderRules()` connect `renderRules` to `app.js`, `.do_POST`, `🛠 بخش اول: بهینه‌سازی سمت سرور (Server-Side Optimizations)`, `renderDestinationRow`?**
  _High betweenness centrality (0.328) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.01652892561983471 - nodes in this community are weakly interconnected._
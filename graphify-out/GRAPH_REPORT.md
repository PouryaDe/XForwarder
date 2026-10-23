# Graph Report - Forward-Manager  (2026-10-23)

## Corpus Check
- 65 files · ~83,985 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .service 4, (none) 2, .example 1)

## Summary
- 1099 nodes · 2000 edges · 80 communities (40 shown, 40 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9f3f7df2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestXForwarderSecurity
- app.js
- TestPerformanceAndOptimizations
- initSystemUpdateManager
- TestFastFailoverAndAntiFlap
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- .migrate_and_normalize_config
- test_metrics_subsystem.py
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- Architecture & Failover Rules (XForwarder)
- The 8-Point Audit Checklist
- LossMonitorScheduler
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- renderDestinationRow
- showToast
- fetchStatus
- XForwarder Operations Runbook
- experiences/README.md
- web_server.py
- DummyHandler
- load_config
- .sync_firewall_and_proxies
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- nftables_parser.py
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Session State & Task Handoff Rule (XForwarder)
- os
- get_network_interfaces_info
- TestNginxStreamEngine
- escapeHtml
- XForwarder Master Architecture Constitution
- syntax-check.py
- TestEngineProbes
- XForwarderEngine
- .do_POST
- 3. Architecture & Solution Implemented
- renderRuleCard
- TestUIAndAPIEdgeCases

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 63 edges
2. `TestUIAndAPIEdgeCases` - 45 edges
3. `load_config()` - 23 edges
4. `TestPerformanceAndOptimizations` - 23 edges
5. `XForwarderWebHandler` - 22 edges
6. `xforwarder.sh script` - 20 edges
7. `showToast()` - 18 edges
8. `escapeHtml()` - 18 edges
9. `check_root()` - 18 edges
10. `validate_rule()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/web_server.py
- `2. Root Cause / Core Dynamics` --references--> `XForwarderEngine`  [INFERRED]
  .agents/experiences/007-fix-haproxy-silent-drop-and-state-wipeout.md → core/engine.py
- `2. Core Dynamics & Low-Resource Relay Safeguards` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `4. Invariants & Rules for AI Agents` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `2. Root Cause / Core Dynamics` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/007-fix-haproxy-silent-drop-and-state-wipeout.md → core/engine.py

## Import Cycles
- None detected.

## Communities (80 total, 40 thin omitted)

### Community 0 - "TestXForwarderSecurity"
Cohesion: 0.05
Nodes (13): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting, 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization (+5 more)

### Community 1 - "app.js"
Cohesion: 0.01
Nodes (120): basePath, batchSelect, btnAddDestination, btnCancelImportModal, btnCancelModal, btnCancelSecurity, btnClearLogs, btnClearSearch (+112 more)

### Community 3 - "initSystemUpdateManager"
Cohesion: 0.24
Nodes (10): checkAuth(), checkImportableRules(), closeMobileSidebar(), closeSystemUpdateModal(), fetchSystemVersionInfo(), initSystemUpdateManager(), openSystemUpdateModal(), showDashboard() (+2 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.32
Nodes (31): backup_restore_menu(), change_all_web_settings(), change_password(), change_web_password(), change_web_port(), change_web_secret_path(), change_web_ssl(), change_web_username() (+23 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

### Community 8 - ".migrate_and_normalize_config"
Cohesion: 0.07
Nodes (13): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup (+5 more)

### Community 9 - "test_metrics_subsystem.py"
Cohesion: 0.12
Nodes (11): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), measure_packet_loss_50(), parse_ping_output(), prune_old_metrics() (+3 more)

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

### Community 15 - "LossMonitorScheduler"
Cohesion: 0.05
Nodes (14): 🔍 Codebase Knowledge Graph (graphify), ⚡ Core Rules & Constraints, 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering (+6 more)

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
Nodes (13): addDestinationRow(), editRule(), handleModalPrioDragEnd(), handleModalPrioDragLeave(), handleModalPrioDragOver(), handleModalPrioDragStart(), handleModalPrioDrop(), moveDestinationRow() (+5 more)

### Community 24 - "showToast"
Cohesion: 0.18
Nodes (13): applyTheme(), copyIpToClipboard(), copyText(), fallbackCopy(), handleExportConfig(), handleServiceRestart(), initServiceRestartControls(), initTheme() (+5 more)

### Community 25 - "fetchStatus"
Cohesion: 0.17
Nodes (16): 4. Client-Side Smoothness, askConfirm(), computeRulesFingerprint(), deleteRule(), fetchStatus(), formatEngineVersion(), handleOverrideChange(), handlePathDrop() (+8 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "experiences/README.md"
Cohesion: 0.04
Nodes (41): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+33 more)

### Community 28 - "web_server.py"
Cohesion: 0.07
Nodes (15): check_rate_limit(), get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_sessions_file_path(), get_system_stats(), get_update_state_file_path() (+7 more)

### Community 30 - "load_config"
Cohesion: 0.20
Nodes (4): export_config_data(), import_config_data(), load_config(), TestExportImport

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "nftables_parser.py"
Cohesion: 0.05
Nodes (30): 3. Implemented Solution & Architecture, get_next_number(), main(), slugify(), main(), run_step(), show_git_status(), validate_json_files() (+22 more)

### Community 34 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 35 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 36 - "os"
Cohesion: 0.17
Nodes (7): load_state(), main(), save_state(), show_state(), handle_sig(), get_config_path(), save_config()

### Community 37 - "get_network_interfaces_info"
Cohesion: 0.09
Nodes (11): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder), get_network_interfaces_info(), do_ping(), get_services_status() (+3 more)

### Community 39 - "escapeHtml"
Cohesion: 0.23
Nodes (13): addLogEntry(), appendLogEntry(), escapeHtml(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics(), parseAndValidateImportJson(), pollUpdateProgress() (+5 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 43 - "syntax-check.py"
Cohesion: 0.25
Nodes (5): check_file(), main(), check_syntax(), get_modified_py_files(), main()

### Community 49 - ".do_POST"
Cohesion: 0.06
Nodes (24): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+16 more)

### Community 59 - "3. Architecture & Solution Implemented"
Cohesion: 0.16
Nodes (10): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout, is_haproxy_listening() (+2 more)

### Community 60 - "renderRuleCard"
Cohesion: 0.33
Nodes (6): formatConciseReason(), formatLatencyBadge(), formatProtoBadge(), getPrioTagClass(), renderRuleCard(), renderRuleListRow()

## Knowledge Gaps
- **263 isolated node(s):** `basePath`, `currentRules`, `lastRuntime`, `loginScreen`, `dashboardScreen` (+258 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 542 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `TestPerformanceAndOptimizations`, `os`, `TestFastFailoverAndAntiFlap`, `TestNginxStreamEngine`, `.test_packet_loss_calculation_and_probes`, `.migrate_and_normalize_config`, `.check_destination`, `.test_nftables_dual_stack_rules_generation`, `TestEngineProbes`, `LossMonitorScheduler`, `.do_POST`, `TestUIAndAPIEdgeCases`, `3. Architecture & Solution Implemented`, `web_server.py`, `.sync_firewall_and_proxies`?**
  _High betweenness centrality (0.302) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `basePath`, `currentRules`, `lastRuntime` to the rest of the system?**
  _263 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestXForwarderSecurity` be split into smaller, more focused modules?**
  _Cohesion score 0.05226480836236934 - nodes in this community are weakly interconnected._
- **Why does `3. Architecture & Solution Implemented` connect `.do_POST` to `escapeHtml`?**
  _High betweenness centrality (0.281) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.014705882352941176 - nodes in this community are weakly interconnected._
# Graph Report - Forward-Manager  (2026-10-24)

## Corpus Check
- 71 files · ~99,057 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .service 4, (none) 2, .example 1)

## Summary
- 1267 nodes · 2389 edges · 97 communities (55 shown, 42 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 128 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b1bb0cab`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
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
- nftables_parser.py
- The 8-Point Audit Checklist
- .do_POST
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- renderDestinationRow
- ⚡ Core Rules & Constraints
- showToast
- XForwarder Operations Runbook
- traffic.py
- web_server.py
- get_update_status
- DummyHandler
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- subprocess
- haproxy_parser.py
- Architectural Solutions Implemented
- get_network_interfaces_info
- TestNginxStreamEngine
- escapeHtml
- XForwarder Master Architecture Constitution
- test_security.py
- .evaluate_rule
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- XForwarderEngine
- Backward Compatibility & Automated Schema Migration Rule (XForwarder)
- TestUIAndAPIEdgeCases
- 3. Architecture & Solution Implemented
- get_full_version_status
- validate_rule
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- re
- engine.py
- sync_system_rules
- Architecture & Failover Rules (XForwarder)
- openTrafficModal
- Experience 004: Backward Compatibility and Automated Schema Migrations
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- ._persist_active_priorities
- experiences/README.md
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- experience-logging.md

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 70 edges
2. `TestUIAndAPIEdgeCases` - 48 edges
3. `load_config()` - 25 edges
4. `TestPerformanceAndOptimizations` - 25 edges
5. `showToast()` - 25 edges
6. `XForwarderWebHandler` - 24 edges
7. `escapeHtml()` - 22 edges
8. `import_config_data()` - 20 edges
9. `xforwarder.sh script` - 20 edges
10. `TestTrafficSubsystem` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `2. Root Cause / Core Dynamics` --references--> `XForwarderEngine`  [INFERRED]
  .agents/experiences/007-fix-haproxy-silent-drop-and-state-wipeout.md → core/engine.py
- `⚡ Core Rules & Constraints` --references--> `sync_system_rules()`  [INFERRED]
  AGENTS.md → core/engine.py
- `2. Core Dynamics & Low-Resource Relay Safeguards` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `4. Invariants & Rules for AI Agents` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py

## Import Cycles
- None detected.

## Communities (97 total, 42 thin omitted)

### Community 1 - "app.js"
Cohesion: 0.01
Nodes (120): basePath, batchSelect, btnAddDestination, btnCancelImportModal, btnCancelModal, btnCancelSecurity, btnClearJsonText, btnClearLogs (+112 more)

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
Cohesion: 0.11
Nodes (3): 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`), Required Normalization Rules:, TestXForwarderMigration

### Community 9 - "test_metrics_subsystem.py"
Cohesion: 0.09
Nodes (12): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), LossMonitorScheduler, measure_packet_loss_50(), parse_ping_output() (+4 more)

### Community 10 - "Mandatory Task Completion & Verification Workflow (XForwarder)"
Cohesion: 0.18
Nodes (10): 0. Requirements Clarification & Blast Radius, 1. Code Verification & Syntax, 2. Automated Verification Pipeline, 3. Requirement Convergence, 4. Documentation Synchronization, 5. UI Consistency (If Web Modified), 6. Experience Logging, 7. Safe Git Operations & Token Efficiency (+2 more)

### Community 11 - "Workflow: Add Port Rule"
Cohesion: 0.33
Nodes (5): Step 1: Gather Rule Parameters, Step 2: Validate Target Reachability, Step 3: Register Rule in Configuration, Step 4: Verify Synchronization, Workflow: Add Port Rule

### Community 12 - "Workflow: Diagnose Failover & Forwarding"
Cohesion: 0.33
Nodes (5): Step 1: Check Runtime Daemon State, Step 2: Check Systemd Logs, Step 3: Verify Zero-Collision Rule Enforcement, Step 4: Test Manual Override, Workflow: Diagnose Failover & Forwarding

### Community 13 - "nftables_parser.py"
Cohesion: 0.09
Nodes (16): 3. Implemented Solution & Architecture, backup_legacy_nftables(), _build_xforwarder_rule_from_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), discover_all_relay_rules(), discover_importable_nftables_rules(), find_candidate_nftables_files() (+8 more)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - ".do_POST"
Cohesion: 0.07
Nodes (16): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, 4. Invariants & Rules for AI Agents, export_config_data(), get_config_path(), import_config_data(), load_config() (+8 more)

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
Cohesion: 0.18
Nodes (7): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder), Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops)

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
Cohesion: 0.20
Nodes (14): addDestinationRow(), editRule(), handleModalPrioDragEnd(), handleModalPrioDragLeave(), handleModalPrioDragOver(), handleModalPrioDragStart(), handleModalPrioDrop(), moveDestinationRow() (+6 more)

### Community 24 - "⚡ Core Rules & Constraints"
Cohesion: 0.20
Nodes (12): 2. Non-Negotiable Architectural Constraints, 🔍 Codebase Knowledge Graph (graphify), ⚡ Core Rules & Constraints, 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide, copyCategoryJson(), copyJsonToClipboard() (+4 more)

### Community 25 - "showToast"
Cohesion: 0.10
Nodes (31): 4. Client-Side Smoothness, 5. Web UI Real-Time Visibility, applyTheme(), askConfirm(), computeRulesFingerprint(), copyIpToClipboard(), copyText(), deleteRule() (+23 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "traffic.py"
Cohesion: 0.06
Nodes (15): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_stats_csv(), parse_nftables_counters_json(), parse_proc_net_dev() (+7 more)

### Community 28 - "web_server.py"
Cohesion: 0.13
Nodes (4): load_state(), main(), save_state(), show_state()

### Community 29 - "get_update_status"
Cohesion: 0.08
Nodes (16): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, get_script_path(), get_sessions_file_path(), get_update_log_path() (+8 more)

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "subprocess"
Cohesion: 0.27
Nodes (7): check_syntax(), get_modified_py_files(), main(), main(), run_step(), show_git_status(), validate_json_files()

### Community 35 - "haproxy_parser.py"
Cohesion: 0.19
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 36 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 37 - "get_network_interfaces_info"
Cohesion: 0.08
Nodes (13): 3. Architecture & Solution Implemented, 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder), get_network_interfaces_info(), do_ping() (+5 more)

### Community 39 - "escapeHtml"
Cohesion: 0.12
Nodes (26): addLogEntry(), appendLogEntry(), escapeHtml(), formatBytes(), formatConciseReason(), formatLatencyBadge(), formatProtoBadge(), getPrioTagClass() (+18 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "test_security.py"
Cohesion: 0.05
Nodes (17): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting, 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization (+9 more)

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "XForwarderEngine"
Cohesion: 0.16
Nodes (3): 2. Selective Service Reloading, 1. High-Risk Core Components, XForwarderEngine

### Community 46 - "Backward Compatibility & Automated Schema Migration Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup, 4. Legacy Path & CLI Compatibility, Backward Compatibility & Automated Schema Migration Rule (XForwarder)

### Community 48 - "3. Architecture & Solution Implemented"
Cohesion: 0.28
Nodes (4): 3. Architecture & Solution Implemented, is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service()

### Community 50 - "get_full_version_status"
Cohesion: 0.17
Nodes (4): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info()

### Community 53 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 54 - "re"
Cohesion: 0.29
Nodes (5): check_file(), main(), get_next_number(), main(), slugify()

### Community 55 - "engine.py"
Cohesion: 0.15
Nodes (7): handle_sig(), aggregate_window(), classify_status(), compute_score(), decide_route(), pick_best_now(), summarize_cycle()

### Community 57 - "sync_system_rules"
Cohesion: 0.17
Nodes (11): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Invariants & Rules for AI Agents (+3 more)

### Community 58 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 60 - "openTrafficModal"
Cohesion: 0.50
Nodes (4): closeTrafficModal(), initTrafficAnalytics(), openTrafficModal(), populateTrafficEntitySelect()

### Community 62 - "Experience 004: Backward Compatibility and Automated Schema Migrations"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 87 - "experiences/README.md"
Cohesion: 0.29
Nodes (4): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, XForwarder Architectural Experiences Catalog

### Community 88 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 89 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 91 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

## Knowledge Gaps
- **267 isolated node(s):** `basePath`, `currentRules`, `lastRuntime`, `loginScreen`, `dashboardScreen` (+262 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 613 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **42 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `TestPerformanceAndOptimizations`, `TestFastFailoverAndAntiFlap`, `.migrate_and_normalize_config`, `test_metrics_subsystem.py`, `.do_POST`, `⚡ Core Rules & Constraints`, `traffic.py`, `web_server.py`, `TestNginxStreamEngine`, `.evaluate_rule`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `3. Architecture & Solution Implemented`, `engine.py`, `sync_system_rules`, `.test_haproxy_performance_fallback_on_old_binary`, `.test_packet_loss_calculation_and_probes`, `.test_engine_pid_file_lifecycle`, `.test_nftables_dual_stack_rules_generation`, `.test_selective_service_reload_nftables`, `.test_haproxy_single_core_omits_nbthread_and_cpumap`, `.test_haproxy_multicore_renders_both_nbthread_and_cpumap`, `._persist_active_priorities`, `.test_nginx_udp_proxy_timeout_rendered`, `.test_nginx_stream_sync_firewall_udp_and_proxy_protocol`?**
  _High betweenness centrality (0.275) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `basePath`, `currentRules`, `lastRuntime` to the rest of the system?**
  _267 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.06896551724137931 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `⚡ Core Rules & Constraints` to `.migrate_and_normalize_config`, `test_metrics_subsystem.py`, `.evaluate_rule`, `XForwarder Master Architecture Constitution`, `nftables_parser.py`, `.do_POST`?**
  _High betweenness centrality (0.223) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.014705882352941176 - nodes in this community are weakly interconnected._
# Graph Report - Forward-Manager  (2026-10-24)

## Corpus Check
- 94 files · ~99,970 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1267 nodes · 2821 edges · 120 communities (63 shown, 57 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 175 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `db60d171`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
- web_server.py
- TestPerformanceAndOptimizations
- state.js
- TestFastFailoverAndAntiFlap
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- time
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- nftables_parser.py
- The 8-Point Audit Checklist
- rule_modal.js
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- Architectural Solutions Implemented
- haproxy_parser.py
- rules.js
- XForwarder Operations Runbook
- traffic.py
- os
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- Experience 008: Full-Stack Performance Optimization & Fast IPC
- LossMonitorScheduler
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- engine.py
- escapeHtml
- re
- system_info.py
- TestNginxStreamEngine
- DummyHandler
- XForwarder Master Architecture Constitution
- TestXForwarderSecurity
- test_ui_and_api_edge_cases.py
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- .evaluate_rule
- auth.js
- TestUIAndAPIEdgeCases
- is_port_in_use_by_external_service
- app.js
- auth.py
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- test_modular_subsystems.py
- import_config_data
- 2. Mandatory Helper Centralization
- Architecture & Failover Rules (XForwarder)
- TestTrafficSubsystem
- shutil
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- import_export.js
- sync_system_rules
- .collect_cycle
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- experiences/README.md
- .do_POST
- parse_proc_net_dev
- syntax-check.py
- TrafficCollector
- Experience 004: Backward Compatibility and Automated Schema Migrations
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- XForwarderEngine
- migrate_and_normalize_config
- parse_haproxy_stats_csv
- parse_nftables_counters_json
- XForwarder - Agent Development Guide
- Backward Compatibility & Automated Schema Migration Rule (XForwarder)
- showToast
- export_config_data

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 66 edges
2. `TestUIAndAPIEdgeCases` - 51 edges
3. `showToast()` - 40 edges
4. `escapeHtml()` - 29 edges
5. `import_config_data()` - 27 edges
6. `TestPerformanceAndOptimizations` - 25 edges
7. `XForwarderWebHandler` - 23 edges
8. `validate_rule()` - 20 edges
9. `TestTrafficSubsystem` - 20 edges
10. `xforwarder.sh script` - 20 edges

## Surprising Connections (you probably didn't know these)
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `3. Architecture & Solution Implemented` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `4. Invariants & Rules for AI Agents` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py

## Import Cycles
- None detected.

## Communities (120 total, 57 thin omitted)

### Community 0 - "TestRouteQualityEngine"
Cohesion: 0.06
Nodes (7): aggregate_window(), classify_status(), compute_score(), decide_route(), pick_best_now(), summarize_cycle(), TestRouteQualityEngine

### Community 1 - "web_server.py"
Cohesion: 0.10
Nodes (15): 3. Architecture & Solution Implemented, get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_status() (+7 more)

### Community 3 - "state.js"
Cohesion: 0.16
Nodes (12): currentRules, lastRuntime, lastTrafficData, setCurrentRules(), setLastRuntime(), setLastTrafficData(), state, copyIpToClipboard() (+4 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.32
Nodes (31): backup_restore_menu(), change_all_web_settings(), change_password(), change_web_password(), change_web_port(), change_web_secret_path(), change_web_ssl(), change_web_username() (+23 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

### Community 9 - "time"
Cohesion: 0.14
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

### Community 13 - "nftables_parser.py"
Cohesion: 0.09
Nodes (16): 3. Implemented Solution & Architecture, backup_legacy_nftables(), _build_xforwarder_rule_from_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), discover_all_relay_rules(), discover_importable_nftables_rules(), find_candidate_nftables_files() (+8 more)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.23
Nodes (18): closeRuleModal(), currentModalDestinations, getPrioTagClass(), handleDestTypeChange(), handleModalPrioDragEnd(), handleModalPrioDragLeave(), handleModalPrioDragOver(), handleModalPrioDragStart() (+10 more)

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

### Community 23 - "Architectural Solutions Implemented"
Cohesion: 0.17
Nodes (11): 4. Client-Side Smoothness, 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, 5. Web UI Real-Time Visibility, Architectural Solutions Implemented, Context & Motivation (+3 more)

### Community 24 - "haproxy_parser.py"
Cohesion: 0.20
Nodes (6): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 25 - "rules.js"
Cohesion: 0.16
Nodes (19): getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart(), handlePathDrop(), initRulesViewControls() (+11 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "traffic.py"
Cohesion: 0.21
Nodes (7): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), prune_old_traffic_records(), reset_traffic_counter()

### Community 28 - "os"
Cohesion: 0.10
Nodes (13): get_next_number(), main(), slugify(), load_state(), main(), save_state(), show_state(), main() (+5 more)

### Community 29 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 30 - "Experience 008: Full-Stack Performance Optimization & Fast IPC"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "engine.py"
Cohesion: 0.17
Nodes (7): check_destination(), fast_confirm_burst(), get_route_interface(), is_interface_up(), is_private_or_tunnel_target(), probe_destination_icmp(), validate_probe_route()

### Community 35 - "escapeHtml"
Cohesion: 0.31
Nodes (16): renderRuleListRow(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadTrafficModalData(), openTrafficModal() (+8 more)

### Community 37 - "system_info.py"
Cohesion: 0.12
Nodes (8): get_network_interfaces_info(), do_ping(), get_services_status(), get_system_stats(), is_ignored_interface(), ping_target(), get_network_interfaces_info(), TestNetworkInterfaces

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 42 - "test_ui_and_api_edge_cases.py"
Cohesion: 0.17
Nodes (8): get_update_state_file_path(), load_update_state(), get_sessions_file_path(), get_update_state_file_path(), load_sessions_from_disk(), load_update_state(), save_sessions_to_disk(), save_update_state()

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 46 - "auth.js"
Cohesion: 0.23
Nodes (18): fetchStatus(), initApp(), startAuthenticatedSession(), stopAuthenticatedSession(), fetchApi(), checkSession(), closeSecurityModal(), evaluatePasswordStrength() (+10 more)

### Community 48 - "is_port_in_use_by_external_service"
Cohesion: 0.17
Nodes (9): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout, is_haproxy_listening(), is_nginx_listening() (+1 more)

### Community 49 - "app.js"
Cohesion: 0.21
Nodes (15): _architecturalCompliance(), pendingOverrides, previousActivePriorities, trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), closeMobileSidebar() (+7 more)

### Community 50 - "auth.py"
Cohesion: 0.15
Nodes (6): get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), verify_password()

### Community 53 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 54 - "test_modular_subsystems.py"
Cohesion: 0.12
Nodes (8): check_rate_limit(), get_config_path(), get_state_file_path(), is_valid_target(), load_state(), save_config(), update_state_rules(), validate_rule()

### Community 56 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 57 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 59 - "shutil"
Cohesion: 0.12
Nodes (8): apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), apply_haproxy(), apply_nginx(), generate_haproxy_cfg(), generate_nginx_cfg()

### Community 60 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 62 - "import_export.js"
Cohesion: 0.26
Nodes (13): 2. Non-Negotiable Architectural Constraints, ⚡ Core Rules & Constraints, checkImportableRules(), closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig() (+5 more)

### Community 63 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 67 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 68 - "experiences/README.md"
Cohesion: 0.18
Nodes (8): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction, XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 72 - ".do_POST"
Cohesion: 0.17
Nodes (8): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, 4. Invariants & Rules for AI Agents, load_config(), notify_engine_wakeup(), sync_rules_and_notify(), XForwarderWebHandler

### Community 74 - "syntax-check.py"
Cohesion: 0.53
Nodes (3): check_syntax(), get_modified_py_files(), main()

### Community 78 - "Experience 004: Backward Compatibility and Automated Schema Migrations"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 88 - "XForwarderEngine"
Cohesion: 0.14
Nodes (4): 2. Selective Service Reloading, Key Decisions & Architectural Changes, 1. High-Risk Core Components, XForwarderEngine

### Community 89 - "migrate_and_normalize_config"
Cohesion: 0.15
Nodes (4): 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`), Required Normalization Rules:, migrate_and_normalize_config(), TestModularSubsystems

### Community 106 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 108 - "Backward Compatibility & Automated Schema Migration Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup, 4. Legacy Path & CLI Compatibility, Backward Compatibility & Automated Schema Migration Rule (XForwarder)

### Community 110 - "showToast"
Cohesion: 0.22
Nodes (16): API_BASE, cleanPath, initDiagPacketLossTool(), deleteRule(), closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls() (+8 more)

## Knowledge Gaps
- **154 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `currentModalDestinations`, `pendingOverrides` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 518 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `web_server.py`, `engine.py`, `TestPerformanceAndOptimizations`, `TestFastFailoverAndAntiFlap`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `test_ui_and_api_edge_cases.py`, `TrafficCollector`, `TestEngineProbes`, `.evaluate_rule`, `TestUIAndAPIEdgeCases`, `is_port_in_use_by_external_service`, `.test_nftables_dual_stack_rules_generation`, `.test_packet_loss_calculation_and_probes`, `os`, `sync_system_rules`, `LossMonitorScheduler`?**
  _High betweenness centrality (0.275) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.06475485661424607 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `import_export.js` to `XForwarder Master Architecture Constitution`, `time`, `.evaluate_rule`, `nftables_parser.py`, `is_port_in_use_by_external_service`, `import_config_data`, `migrate_and_normalize_config`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `web_server.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10420168067226891 - nodes in this community are weakly interconnected._
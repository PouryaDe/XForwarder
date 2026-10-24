# Graph Report - Forward-Manager  (2026-10-24)

## Corpus Check
- 94 files · ~99,533 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1264 nodes · 2800 edges · 112 communities (60 shown, 52 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 174 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6fa76999`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
- web_server.py
- TestPerformanceAndOptimizations
- app.js
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
- migrate_and_normalize_config
- haproxy_parser.py
- rules.js
- XForwarder Operations Runbook
- traffic.py
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- Experience 008: Full-Stack Performance Optimization & Fast IPC
- LossMonitorScheduler
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- engine.py
- escapeHtml
- sys
- get_network_interfaces_info
- TestNginxStreamEngine
- DummyHandler
- XForwarder Master Architecture Constitution
- TestXForwarderSecurity
- save_sessions_to_disk
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- .evaluate_rule
- auth.js
- TestUIAndAPIEdgeCases
- 2. Non-Negotiable Architectural Constraints
- showToast
- auth.py
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- system.js
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- 2. Mandatory Helper Centralization
- Architecture & Failover Rules (XForwarder)
- is_port_in_use_by_external_service
- os
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- verify-all.py
- .sync_firewall_and_proxies
- Session State & Task Handoff Rule (XForwarder)
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- experiences/README.md
- .do_POST
- session-state.py
- syntax-check.py
- restart_services_action
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- XForwarderEngine
- TestModularSubsystems

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 66 edges
2. `TestUIAndAPIEdgeCases` - 50 edges
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
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `2. Mandatory Helper Centralization` --references--> `hash_password()`  [INFERRED]
  .agents/rules/clean-code-dry.md → core/auth.py
- `2. Non-Negotiable Architectural Constraints` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/AGENTS.md → core/config_manager.py

## Import Cycles
- None detected.

## Communities (112 total, 52 thin omitted)

### Community 0 - "TestRouteQualityEngine"
Cohesion: 0.06
Nodes (7): aggregate_window(), classify_status(), compute_score(), decide_route(), pick_best_now(), summarize_cycle(), TestRouteQualityEngine

### Community 1 - "web_server.py"
Cohesion: 0.09
Nodes (18): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+10 more)

### Community 3 - "app.js"
Cohesion: 0.11
Nodes (32): _architecturalCompliance(), fetchStatus(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), stopAuthenticatedSession(), trackFailoverEvents(), checkImportableRules() (+24 more)

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

### Community 23 - "migrate_and_normalize_config"
Cohesion: 0.05
Nodes (36): 🔍 Codebase Knowledge Graph (graphify), ⚡ Core Rules & Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations (+28 more)

### Community 24 - "haproxy_parser.py"
Cohesion: 0.17
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 25 - "rules.js"
Cohesion: 0.20
Nodes (17): getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart(), handlePathDrop(), initRulesViewControls() (+9 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "traffic.py"
Cohesion: 0.05
Nodes (16): classify_tunnel_type(), get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_stats_csv(), parse_nftables_counters_json() (+8 more)

### Community 29 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

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
Cohesion: 0.11
Nodes (11): apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), check_destination(), fast_confirm_burst(), get_route_interface(), is_interface_up() (+3 more)

### Community 35 - "escapeHtml"
Cohesion: 0.29
Nodes (17): renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadTrafficModalData(), openTrafficModal(), populateTrafficEntitySelect() (+9 more)

### Community 36 - "sys"
Cohesion: 0.20
Nodes (6): check_file(), main(), get_next_number(), main(), slugify(), handle_sig()

### Community 37 - "get_network_interfaces_info"
Cohesion: 0.15
Nodes (6): get_network_interfaces_info(), do_ping(), is_ignored_interface(), ping_target(), get_network_interfaces_info(), TestNetworkInterfaces

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 42 - "save_sessions_to_disk"
Cohesion: 0.24
Nodes (6): get_sessions_file_path(), load_sessions_from_disk(), save_sessions_to_disk(), get_sessions_file_path(), load_sessions_from_disk(), save_sessions_to_disk()

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 46 - "auth.js"
Cohesion: 0.31
Nodes (13): checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth(), initInlineSecurityForm(), initSecurityModal() (+5 more)

### Community 48 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.20
Nodes (7): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 49 - "showToast"
Cohesion: 0.19
Nodes (18): API_BASE, cleanPath, fetchApi(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig(), addLogEntry() (+10 more)

### Community 50 - "auth.py"
Cohesion: 0.15
Nodes (4): check_rate_limit(), hash_password(), record_failed_login(), verify_password()

### Community 53 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 54 - "system.js"
Cohesion: 0.38
Nodes (9): closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress() (+1 more)

### Community 55 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 56 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 57 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 58 - "is_port_in_use_by_external_service"
Cohesion: 0.33
Nodes (3): is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service()

### Community 59 - "os"
Cohesion: 0.11
Nodes (10): get_state_file_path(), is_valid_target(), update_state_rules(), validate_rule(), apply_haproxy(), apply_nginx(), generate_haproxy_cfg(), generate_nginx_cfg() (+2 more)

### Community 60 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 62 - "verify-all.py"
Cohesion: 0.53
Nodes (4): main(), run_step(), show_git_status(), validate_json_files()

### Community 64 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

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
Cohesion: 0.33
Nodes (4): XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 72 - ".do_POST"
Cohesion: 0.06
Nodes (14): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, 4. Invariants & Rules for AI Agents, export_config_data(), get_config_path(), import_config_data(), load_config() (+6 more)

### Community 73 - "session-state.py"
Cohesion: 0.53
Nodes (4): load_state(), main(), save_state(), show_state()

### Community 74 - "syntax-check.py"
Cohesion: 0.53
Nodes (3): check_syntax(), get_modified_py_files(), main()

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

## Knowledge Gaps
- **154 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `currentModalDestinations`, `pendingOverrides` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 517 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `web_server.py`, `engine.py`, `TestPerformanceAndOptimizations`, `TestFastFailoverAndAntiFlap`, `sys`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `TestEngineProbes`, `.evaluate_rule`, `json`, `TestUIAndAPIEdgeCases`, `2. Non-Negotiable Architectural Constraints`, `migrate_and_normalize_config`, `traffic.py`, `LossMonitorScheduler`, `.test_nftables_dual_stack_rules_generation`, `.sync_firewall_and_proxies`?**
  _High betweenness centrality (0.271) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.06475485661424607 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `.do_POST`, `time`, `XForwarder Master Architecture Constitution`, `nftables_parser.py`, `.evaluate_rule`, `showToast`, `migrate_and_normalize_config`, `rules.js`?**
  _High betweenness centrality (0.217) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `web_server.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09024390243902439 - nodes in this community are weakly interconnected._
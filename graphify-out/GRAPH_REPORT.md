# Graph Report - Forward-Manager  (2026-10-27)

## Corpus Check
- 100 files · ~113,695 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1396 nodes · 3098 edges · 113 communities (62 shown, 51 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 193 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5c24ce4c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
- json
- TestPerformanceAndOptimizations
- traffic.py
- TestFastFailoverAndAntiFlap
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- decide_route
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
- import_config_data
- config_manager.py
- app.js
- XForwarder Operations Runbook
- Architectural Solutions Implemented
- subprocess
- syntax-check.py
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- time
- traffic.js
- TestToggleDestination
- fetchStatus
- TestNginxStreamEngine
- engine.py
- XForwarder Master Architecture Constitution
- os
- 2. Non-Negotiable Architectural Constraints
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- navigation.js
- auth.js
- TestUIAndAPIEdgeCases
- .evaluate_rule
- DummyHandler
- web_server.py
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- TestXForwarderSecurity
- validate_rule
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- haproxy_parser.py
- TestTargetMetricCache
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- parse_ping_replies
- 2. Mandatory Helper Centralization
- XForwarderEngine
- showToast
- sync_system_rules
- Architecture & Failover Rules (XForwarder)
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- experiences/README.md
- Session State & Task Handoff Rule (XForwarder)
- route_quality.py
- classify_status
- escapeHtml
- .do_POST
- Experience 003: Native Python Zero-Dependency Web Server
- XForwarder - Agent Development Guide
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- system.js
- Experience 008: Full-Stack Performance Optimization & Fast IPC

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 76 edges
2. `TestUIAndAPIEdgeCases` - 52 edges
3. `showToast()` - 43 edges
4. `escapeHtml()` - 36 edges
5. `import_config_data()` - 27 edges
6. `XForwarderWebHandler` - 25 edges
7. `TestPerformanceAndOptimizations` - 25 edges
8. `TestRouteQualityEngine` - 24 edges
9. `validate_rule()` - 22 edges
10. `decide_route()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `2. Mandatory Helper Centralization` --references--> `hash_password()`  [INFERRED]
  .agents/rules/clean-code-dry.md → core/auth.py
- `2. Non-Negotiable Architectural Constraints` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/AGENTS.md → core/config_manager.py

## Import Cycles
- None detected.

## Communities (113 total, 51 thin omitted)

### Community 1 - "json"
Cohesion: 0.12
Nodes (6): main(), run_step(), show_git_status(), validate_json_files(), handle_sig(), TestFamilySelection

### Community 3 - "traffic.py"
Cohesion: 0.05
Nodes (16): classify_tunnel_type(), get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_stats_csv(), parse_nftables_counters_json() (+8 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.32
Nodes (31): backup_restore_menu(), change_all_web_settings(), change_password(), change_web_password(), change_web_port(), change_web_secret_path(), change_web_ssl(), change_web_username() (+23 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

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
Cohesion: 0.19
Nodes (8): 3. Implemented Solution & Architecture, backup_legacy_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), get_live_nftables_rules(), import_all_relay_rules_into_config(), import_nftables_rules_into_config(), _is_valid_target()

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
Nodes (7): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering), Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 22 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 23 - "import_config_data"
Cohesion: 0.06
Nodes (17): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup (+9 more)

### Community 24 - "config_manager.py"
Cohesion: 0.14
Nodes (8): get_config_path(), get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), is_valid_target(), save_config(), update_state_rules()

### Community 25 - "app.js"
Cohesion: 0.20
Nodes (22): pendingOverrides, previousActivePriorities, getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart() (+14 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "Architectural Solutions Implemented"
Cohesion: 0.17
Nodes (11): 4. Client-Side Smoothness, 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, 5. Web UI Real-Time Visibility, Architectural Solutions Implemented, Context & Motivation (+3 more)

### Community 28 - "subprocess"
Cohesion: 0.06
Nodes (20): 3. Architecture & Solution Implemented, apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), apply_haproxy(), apply_nginx(), generate_haproxy_cfg() (+12 more)

### Community 29 - "syntax-check.py"
Cohesion: 0.53
Nodes (3): check_syntax(), get_modified_py_files(), main()

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "time"
Cohesion: 0.14
Nodes (7): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), get_system_stats()

### Community 35 - "traffic.js"
Cohesion: 0.31
Nodes (15): closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadTrafficModalData(), openTrafficModal(), populateTrafficEntitySelect(), promptResetTraffic() (+7 more)

### Community 37 - "fetchStatus"
Cohesion: 0.12
Nodes (21): fetchStatus(), stopAuthenticatedSession(), updateCategoryDatalist(), currentRules, lastLatestLoss, lastRuntime, lastTrafficData, setCurrentRules() (+13 more)

### Community 39 - "engine.py"
Cohesion: 0.07
Nodes (21): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, _c_locale_env(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), _ip_family_flag() (+13 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "os"
Cohesion: 0.13
Nodes (10): check_file(), main(), get_next_number(), main(), slugify(), load_state(), main(), save_state() (+2 more)

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.22
Nodes (6): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "navigation.js"
Cohesion: 0.43
Nodes (6): _architecturalCompliance(), closeMobileSidebar(), initNavigation(), openMobileSidebar(), SECTIONS, switchSection()

### Community 46 - "auth.js"
Cohesion: 0.22
Nodes (16): API_BASE, cleanPath, fetchApi(), checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout() (+8 more)

### Community 50 - "web_server.py"
Cohesion: 0.11
Nodes (15): get_full_version_status(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_update_state(), save_update_state(), _worker(), get_sessions_file_path() (+7 more)

### Community 51 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 53 - "TestXForwarderSecurity"
Cohesion: 0.09
Nodes (3): reset_rate_limit(), verify_password(), TestXForwarderSecurity

### Community 55 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 56 - "haproxy_parser.py"
Cohesion: 0.06
Nodes (15): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), _build_xforwarder_rule_from_nftables(), discover_all_relay_rules() (+7 more)

### Community 58 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 60 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 61 - "XForwarderEngine"
Cohesion: 0.16
Nodes (4): 2. Selective Service Reloading, Key Decisions & Architectural Changes, 1. High-Risk Core Components, XForwarderEngine

### Community 62 - "showToast"
Cohesion: 0.28
Nodes (14): ⚡ Core Rules & Constraints, closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig(), initImportExport(), openImportModal() (+6 more)

### Community 63 - "sync_system_rules"
Cohesion: 0.29
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, 2. Root Cause / Core Dynamics, sync_system_rules()

### Community 64 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "experiences/README.md"
Cohesion: 0.25
Nodes (4): XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 70 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 71 - "route_quality.py"
Cohesion: 0.22
Nodes (4): aggregate_window(), compute_score(), pick_best_now(), summarize_cycle()

### Community 74 - "escapeHtml"
Cohesion: 0.23
Nodes (15): initApp(), trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics() (+7 more)

### Community 77 - ".do_POST"
Cohesion: 0.06
Nodes (14): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, 4. Invariants & Rules for AI Agents, export_config_data(), load_config(), load_state(), is_ignored_interface() (+6 more)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 83 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 89 - "system.js"
Cohesion: 0.29
Nodes (11): startAuthenticatedSession(), checkImportableRules(), closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal() (+3 more)

### Community 125 - "Experience 008: Full-Stack Performance Optimization & Fast IPC"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons

## Knowledge Gaps
- **157 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `SECTIONS`, `currentModalDestinations` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 565 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `json`, `TestPerformanceAndOptimizations`, `traffic.py`, `TestFastFailoverAndAntiFlap`, `TestToggleDestination`, `TestNginxStreamEngine`, `engine.py`, `TestXForwarderMigration`, `2. Non-Negotiable Architectural Constraints`, `.test_packet_loss_calculation_and_probes`, `TestEngineProbes`, `.test_nftables_dual_stack_rules_generation`, `TestUIAndAPIEdgeCases`, `.evaluate_rule`, `web_server.py`, `TestTargetMetricCache`, `sync_system_rules`, `TestMetricsSubsystem`?**
  _High betweenness centrality (0.289) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _157 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `engine.py`, `XForwarder Master Architecture Constitution`, `.evaluate_rule`, `import_config_data`, `haproxy_parser.py`, `app.js`, `parse_ping_replies`, `showToast`?**
  _High betweenness centrality (0.204) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `json` be split into smaller, more focused modules?**
  _Cohesion score 0.11711711711711711 - nodes in this community are weakly interconnected._
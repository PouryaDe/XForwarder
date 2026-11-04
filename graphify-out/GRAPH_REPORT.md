# Graph Report - Forward-Manager  (2026-11-04)

## Corpus Check
- 105 files · ~137,373 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1555 nodes · 3410 edges · 133 communities (62 shown, 71 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 217 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9571d109`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- session-state.py
- traffic.py
- TestPerformanceAndOptimizations
- metrics.py
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- decide_route
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- json
- The 8-Point Audit Checklist
- app.js
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- classify_status
- syntax-check.py
- rules.js
- XForwarder Operations Runbook
- TestRouteQualityEngine
- TestI18nAndRTL
- engine.py
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- service_manager.py
- escapeHtml
- TestToggleDestination
- initTheme
- TestNginxStreamEngine
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- XForwarder Master Architecture Constitution
- migrate_and_normalize_config
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- experiences/README.md
- showToast
- TestUIAndAPIEdgeCases
- XForwarderEngine
- DummyHandler
- aggregate_window
- TestFastFailoverAndAntiFlap
- TestXForwarderSecurity
- sync_system_rules
- nftables_parser.py
- TestTargetMetricCache
- restart_services_action
- parse_ping_replies
- 2. Mandatory Helper Centralization
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- system.js
- 5. Verification & Testing
- utils.js
- web_server.py
- .do_POST
- Experience 003: Native Python Zero-Dependency Web Server
- experience-logging.md
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- t
- import_export.js
- 3. Architecture & Solution Implemented
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- .evaluate_rule
- TestTrafficSubsystem
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- Architecture & Failover Rules (XForwarder)
- os
- XForwarder - Agent Development Guide

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 76 edges
2. `TestUIAndAPIEdgeCases` - 57 edges
3. `showToast()` - 48 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 40 edges
6. `decide_route()` - 39 edges
7. `import_config_data()` - 27 edges
8. `t()` - 27 edges
9. `validate_rule()` - 26 edges
10. `XForwarderWebHandler` - 25 edges

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

## Communities (133 total, 71 thin omitted)

### Community 0 - "session-state.py"
Cohesion: 0.24
Nodes (7): get_next_number(), main(), slugify(), load_state(), main(), save_state(), show_state()

### Community 1 - "traffic.py"
Cohesion: 0.09
Nodes (14): classify_tunnel_type(), get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_stats_csv(), parse_nftables_counters_json() (+6 more)

### Community 3 - "metrics.py"
Cohesion: 0.07
Nodes (19): _c_locale_env(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), _ip_family_flag(), measure_packet_loss_50() (+11 more)

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

### Community 13 - "json"
Cohesion: 0.09
Nodes (15): main(), run_step(), show_git_status(), validate_json_files(), get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service() (+7 more)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "app.js"
Cohesion: 0.15
Nodes (31): fetchStatus(), pendingOverrides, previousActivePriorities, stopAuthenticatedSession(), closeRuleModal(), currentModalDestinations, getPrioTagClass(), handleDestTypeChange() (+23 more)

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

### Community 24 - "syntax-check.py"
Cohesion: 0.53
Nodes (3): check_syntax(), get_modified_py_files(), main()

### Community 25 - "rules.js"
Cohesion: 0.16
Nodes (21): closeSwitchLogsModal(), copySwitchLogsToClipboard(), fallbackCopy(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver() (+13 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 29 - "engine.py"
Cohesion: 0.07
Nodes (13): handle_sig(), apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), get_route_interface(), is_interface_up(), apply_haproxy() (+5 more)

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "service_manager.py"
Cohesion: 0.13
Nodes (11): get_full_version_status(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_update_state(), save_update_state(), start_system_update() (+3 more)

### Community 35 - "escapeHtml"
Cohesion: 0.27
Nodes (20): renderRuleListRow(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData() (+12 more)

### Community 37 - "initTheme"
Cohesion: 1.00
Nodes (3): initTheme(), toggleTheme(), updateThemeToggleUI()

### Community 39 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "migrate_and_normalize_config"
Cohesion: 0.04
Nodes (26): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 4. Client-Side Smoothness, 1. Rapid Failure Detection & Confirmation Burst (<1s) (+18 more)

### Community 42 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "experiences/README.md"
Cohesion: 0.29
Nodes (4): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, XForwarder Architectural Experiences Catalog

### Community 46 - "showToast"
Cohesion: 0.13
Nodes (32): initApp(), startAuthenticatedSession(), trackFailoverEvents(), API_BASE, cleanPath, fetchApi(), checkSession(), closeSecurityModal() (+24 more)

### Community 48 - "XForwarderEngine"
Cohesion: 0.18
Nodes (5): 2. Selective Service Reloading, Key Decisions & Architectural Changes, 1. High-Risk Core Components, XForwarderEngine, TrafficCollector

### Community 51 - "aggregate_window"
Cohesion: 0.12
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window()

### Community 54 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 56 - "nftables_parser.py"
Cohesion: 0.06
Nodes (23): 3. Implemented Solution & Architecture, _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), backup_legacy_nftables() (+15 more)

### Community 58 - "restart_services_action"
Cohesion: 0.15
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, restart_services_action()

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 61 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 70 - "system.js"
Cohesion: 0.38
Nodes (9): closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress() (+1 more)

### Community 73 - "utils.js"
Cohesion: 0.18
Nodes (12): lastTrafficData, copyIpToClipboard(), lastSystemStats, renderServicesStatus(), renderStats(), renderSystemStats(), _trafficModeRate, copyText() (+4 more)

### Community 75 - "web_server.py"
Cohesion: 0.09
Nodes (20): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), verify_password(), export_config_data() (+12 more)

### Community 77 - ".do_POST"
Cohesion: 0.06
Nodes (17): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, 4. Invariants & Rules for AI Agents, get_config_path(), import_config_data(), load_config(), save_config() (+9 more)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 83 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "t"
Cohesion: 0.18
Nodes (20): _architecturalCompliance(), applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage() (+12 more)

### Community 89 - "import_export.js"
Cohesion: 0.26
Nodes (13): 2. Non-Negotiable Architectural Constraints, ⚡ Core Rules & Constraints, checkImportableRules(), closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig() (+5 more)

### Community 96 - "3. Architecture & Solution Implemented"
Cohesion: 0.18
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 114 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, Architecture & Failover Rules (XForwarder)

### Community 116 - "os"
Cohesion: 0.10
Nodes (3): check_file(), main(), pick_best_now()

### Community 146 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

## Knowledge Gaps
- **171 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `TRANSLATIONS`, `DEFAULT_LANG` (+166 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 637 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **71 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `3. Architecture & Solution Implemented`, `TestPerformanceAndOptimizations`, `.evaluate_rule`, `metrics.py`, `TestToggleDestination`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `.test_nftables_dual_stack_rules_generation`, `web_server.py`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `os`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `.test_packet_loss_calculation_and_probes`, `engine.py`, `TestMetricsSubsystem`?**
  _High betweenness centrality (0.244) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _171 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `traffic.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08668076109936575 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `import_export.js` to `3. Architecture & Solution Implemented`, `.evaluate_rule`, `metrics.py`, `XForwarder Master Architecture Constitution`, `migrate_and_normalize_config`, `.do_POST`, `t`, `nftables_parser.py`, `parse_ping_replies`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
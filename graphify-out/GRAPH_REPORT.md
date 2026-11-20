# Graph Report - Forward-Manager  (2026-11-20)

## Corpus Check
- 107 files · ~140,444 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1633 nodes · 3555 edges · 155 communities (67 shown, 88 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 231 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `245e2d42`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DummyHandler
- traffic.py
- TestPerformanceAndOptimizations
- haproxy_parser.py
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- decide_route
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- TestModularSubsystems
- The 8-Point Audit Checklist
- rule_modal.js
- .agents/AGENTS.md
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- Session State & Task Handoff Rule (XForwarder)
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- classify_status
- engine.py
- rules.js
- XForwarder Operations Runbook
- route_quality.py
- TestI18nAndRTL
- os
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TestTrafficSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- TestTrafficAwareFailover
- escapeHtml
- TestToggleDestination
- config_manager.py
- TestNginxStreamEngine
- pick_best_now
- migrate_and_normalize_config
- Experience 004: Backward Compatibility and Automated Schema Migrations
- 2. Non-Negotiable Architectural Constraints
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- experiences/README.md
- showToast
- validate_rule
- XForwarderEngine
- TrafficCollector
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- .sync_firewall_and_proxies
- TestFastFailoverAndAntiFlap
- XForwarderWebServer
- sync_system_rules
- nftables_parser.py
- TestTargetMetricCache
- parse_ping_replies
- import_config_data
- TestMetricsSubsystem
- subprocess
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- experiences/README.md
- initApp
- 5. Verification & Testing
- app.js
- save_sessions_to_disk
- web_server.py
- .do_POST
- Architectural Solutions Implemented
- navigation.js
- get_network_interfaces_info
- system.js
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- i18n.js
- experience-logging.md
- test_modular_subsystems.py
- 3. Architecture & Solution Implemented
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- .collect_cycle
- Backward Compatibility & Automated Schema Migration Rule (XForwarder)
- TestUIAndAPIEdgeCases
- parse_proc_net_dev
- 5. Verification & Testing
- read_haproxy_backend_health
- TestToggleDestinationApi
- notify_engine_wakeup
- parse_nftables_counters_json
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- XForwarder - Agent Development Guide
- _coerce_bool
- json
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- 2. Mandatory Helper Centralization
- Interactive Requirements Clarification (Reverse Prompt Engineering)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 80 edges
2. `TestUIAndAPIEdgeCases` - 56 edges
3. `showToast()` - 48 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 40 edges
6. `decide_route()` - 39 edges
7. `t()` - 27 edges
8. `validate_rule()` - 26 edges
9. `import_config_data()` - 26 edges
10. `TestPerformanceAndOptimizations` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `4. Invariants & Rules for AI Agents` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py

## Import Cycles
- None detected.

## Communities (155 total, 88 thin omitted)

### Community 1 - "traffic.py"
Cohesion: 0.19
Nodes (7): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), prune_old_traffic_records(), reset_traffic_counter()

### Community 3 - "haproxy_parser.py"
Cohesion: 0.15
Nodes (8): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), find_candidate_nftables_files(), TestHAProxyParser

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
Cohesion: 0.20
Nodes (10): 0. Requirements Clarification & Blast Radius, 1. Code Verification & Syntax, 2. Automated Verification Pipeline & Graph Sync, 3. Requirement Convergence, 4. Documentation Synchronization, 5. UI Consistency (If Web Modified), 6. Experience Logging, 7. Safe Git Operations & Token Efficiency (+2 more)

### Community 11 - "Workflow: Add Port Rule"
Cohesion: 0.33
Nodes (5): Step 1: Gather Rule Parameters, Step 2: Validate Target Reachability, Step 3: Register Rule in Configuration, Step 4: Verify Synchronization, Workflow: Add Port Rule

### Community 12 - "Workflow: Diagnose Failover & Forwarding"
Cohesion: 0.33
Nodes (5): Step 1: Check Runtime Daemon State, Step 2: Check Systemd Logs, Step 3: Verify Zero-Collision Rule Enforcement, Step 4: Test Manual Override, Workflow: Diagnose Failover & Forwarding

### Community 13 - "TestModularSubsystems"
Cohesion: 0.11
Nodes (4): get_installed_version(), get_local_version_info(), get_system_stats(), TestModularSubsystems

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.22
Nodes (19): closeRuleModal(), currentModalDestinations, getPrioTagClass(), handleDestTypeChange(), handleModalPrioDragEnd(), handleModalPrioDragLeave(), handleModalPrioDragOver(), handleModalPrioDragStart() (+11 more)

### Community 16 - ".agents/AGENTS.md"
Cohesion: 0.20
Nodes (6): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite), 3. Immediate Syntax Verification, Large Files Inspection & Surgical Editing Rule

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 19 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 22 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 24 - "engine.py"
Cohesion: 0.06
Nodes (24): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, 7. Dual-Feedback L4 Port & Traffic Blackhole Detection, _c_locale_env(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db() (+16 more)

### Community 25 - "rules.js"
Cohesion: 0.12
Nodes (32): ⚡ Core Rules & Constraints, t(), closeSwitchLogsModal(), copySwitchLogsToClipboard(), deleteRule(), fallbackCopy(), getPrioTagClass(), handleOverrideChange() (+24 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.22
Nodes (7): Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops), Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "route_quality.py"
Cohesion: 0.10
Nodes (8): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window(), compute_score(), summarize_cycle()

### Community 29 - "os"
Cohesion: 0.08
Nodes (14): check_file(), main(), get_next_number(), main(), slugify(), apply_nftables(), _find_conntrack_bin(), flush_conntrack() (+6 more)

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 35 - "escapeHtml"
Cohesion: 0.30
Nodes (18): renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData(), openTrafficModal() (+10 more)

### Community 37 - "config_manager.py"
Cohesion: 0.21
Nodes (5): get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), update_state_rules()

### Community 40 - "migrate_and_normalize_config"
Cohesion: 0.20
Nodes (8): 1. System Model, 2. Non-Negotiable Architectural Invariants, 3. On-Demand Rules, Skills & Tooling, XForwarder Master Architecture Constitution, 3. Architecture & Solution Implemented, 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`), Required Normalization Rules:, migrate_and_normalize_config()

### Community 41 - "Experience 004: Backward Compatibility and Automated Schema Migrations"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.17
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "experiences/README.md"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons

### Community 46 - "showToast"
Cohesion: 0.16
Nodes (23): API_BASE, cleanPath, fetchApi(), checkImportableRules(), closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport() (+15 more)

### Community 50 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (8): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, 2. Root Cause / Core Dynamics, sync_system_rules()

### Community 56 - "nftables_parser.py"
Cohesion: 0.09
Nodes (15): 3. Implemented Solution & Architecture, backup_legacy_nftables(), _build_xforwarder_rule_from_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), discover_all_relay_rules(), discover_importable_nftables_rules(), get_live_nftables_rules() (+7 more)

### Community 59 - "parse_ping_replies"
Cohesion: 0.13
Nodes (10): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 3. Two-Tier Intelligent Failover & Route Quality Architecture, 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder), parse_ping_replies(), _iputils_output() (+2 more)

### Community 60 - "import_config_data"
Cohesion: 0.19
Nodes (3): import_config_data(), TestExportImport, load_config()

### Community 64 - "subprocess"
Cohesion: 0.14
Nodes (12): check_syntax(), get_modified_py_files(), main(), _read_hook_stdin(), main(), run_step(), show_git_status(), validate_json_files() (+4 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "experiences/README.md"
Cohesion: 0.25
Nodes (4): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog

### Community 70 - "initApp"
Cohesion: 0.28
Nodes (15): initApp(), startAuthenticatedSession(), checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth() (+7 more)

### Community 73 - "app.js"
Cohesion: 0.12
Nodes (28): fetchStatus(), pendingOverrides, previousActivePriorities, stopAuthenticatedSession(), trackFailoverEvents(), addLogEntry(), appendLogEntry(), runLivePacketLossTest() (+20 more)

### Community 74 - "save_sessions_to_disk"
Cohesion: 0.24
Nodes (6): get_sessions_file_path(), load_sessions_from_disk(), save_sessions_to_disk(), get_sessions_file_path(), load_sessions_from_disk(), save_sessions_to_disk()

### Community 75 - "web_server.py"
Cohesion: 0.10
Nodes (16): 3. Architecture & Solution Implemented, get_full_version_status(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_update_state(), restart_services_action() (+8 more)

### Community 77 - ".do_POST"
Cohesion: 0.13
Nodes (9): 1. Server-Side HTTP Performance, 4. Invariants & Rules for AI Agents, export_config_data(), get_config_path(), load_config(), load_state(), save_config(), sync_rules_and_notify() (+1 more)

### Community 78 - "Architectural Solutions Implemented"
Cohesion: 0.17
Nodes (11): 4. Client-Side Smoothness, 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, 5. Web UI Real-Time Visibility, Architectural Solutions Implemented, Context & Motivation (+3 more)

### Community 79 - "navigation.js"
Cohesion: 0.27
Nodes (10): _architecturalCompliance(), initAmbientEffects(), SPOTLIGHT_SELECTOR, syncNavIndicatorMetrics(), updateNavIndicator(), closeMobileSidebar(), initNavigation(), openMobileSidebar() (+2 more)

### Community 80 - "get_network_interfaces_info"
Cohesion: 0.22
Nodes (4): is_ignored_interface(), get_network_interfaces_info(), _safe_flush_port_conntrack(), TestNetworkInterfaces

### Community 81 - "system.js"
Cohesion: 0.38
Nodes (9): closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress() (+1 more)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "i18n.js"
Cohesion: 0.38
Nodes (10): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), toggleLanguage() (+2 more)

### Community 86 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 94 - "test_modular_subsystems.py"
Cohesion: 0.11
Nodes (6): check_rate_limit(), hash_password(), record_failed_login(), reset_rate_limit(), verify_password(), TestXForwarderSecurity

### Community 96 - "3. Architecture & Solution Implemented"
Cohesion: 0.24
Nodes (5): 1. Context & Motivation, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 100 - "Backward Compatibility & Automated Schema Migration Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup, 4. Legacy Path & CLI Compatibility, Backward Compatibility & Automated Schema Migration Rule (XForwarder)

### Community 106 - "notify_engine_wakeup"
Cohesion: 0.33
Nodes (3): 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, notify_engine_wakeup()

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 111 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 116 - "json"
Cohesion: 0.11
Nodes (7): load_state(), main(), save_state(), show_state(), handle_sig(), get_remote_version_info(), get_full_version_status()

### Community 119 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 123 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 126 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

## Knowledge Gaps
- **88 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `3. Architecture & Solution Implemented`, `TestPerformanceAndOptimizations`, `TestTrafficAwareFailover`, `TestToggleDestination`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `.test_nftables_dual_stack_rules_generation`, `2. Non-Negotiable Architectural Constraints`, `web_server.py`, `TestEngineProbes`, `.sync_firewall_and_proxies`, `json`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `engine.py`, `TestTargetMetricCache`, `TestMetricsSubsystem`?**
  _High betweenness centrality (0.219) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TestEngineProbes`) actually correct?**
  _`XForwarderEngine` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Should `DummyHandler` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Why does `⚡ Core Rules & Constraints` connect `rules.js` to `migrate_and_normalize_config`, `read_haproxy_backend_health`, `showToast`, `XForwarder - Agent Development Guide`, `sync_system_rules`, `engine.py`, `nftables_parser.py`, `parse_ping_replies`, `import_config_data`, `TestMetricsSubsystem`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._
- **Why does `decide_route()` connect `decide_route` to `5. Verification & Testing`, `5. Verification & Testing`, `5. Verification & Testing`, `XForwarderEngine`, `json`, `engine.py`, `route_quality.py`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Should `haproxy_parser.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._
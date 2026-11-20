# Graph Report - Forward-Manager  (2026-11-20)

## Corpus Check
- 107 files · ~146,498 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1702 nodes · 3798 edges · 158 communities (66 shown, 92 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 242 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `45f07b63`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DummyHandler
- time
- TestPerformanceAndOptimizations
- engine.py
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
- parse_nftables_text
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- XForwarderWebHandler
- Intermediate Relay VPS Constraints Rule (XForwarder)
- classify_status
- firewall.py
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
- parse_haproxy_stats_csv
- TestNginxStreamEngine
- TestRouteQualityEngine
- XForwarderEngine
- 2. Non-Negotiable Architectural Constraints
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- Architectural Solutions Implemented
- initApp
- TestUIAndAPIEdgeCases
- sanitize_target_host
- subprocess
- run_scheduled_ping_round
- TestFastFailoverAndAntiFlap
- TestXForwarderSecurity
- sync_system_rules
- haproxy_parser.py
- TestTargetMetricCache
- parse_ping_replies
- import_config_data
- record_ping_result
- json
- Networking & Kernel Standards (XForwarder)
- TrafficCollector
- experiences/README.md
- get_network_interfaces_info
- 5. Verification & Testing
- quality.js
- system.js
- ⚡ Core Rules & Constraints
- session-state.py
- web_server.py
- Architectural Solutions Implemented
- app.js
- stats.js
- .test_scenario_custom_port_mapping_uses_rule_port_for_telemetry_and_dest_port_for_l4
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- i18n.js
- route_quality.py
- parse_proc_net_dev
- Session State & Task Handoff Rule (XForwarder)
- Large Files Inspection & Surgical Editing Rule
- 3. Architecture & Solution Implemented
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- Backward Compatibility & Automated Schema Migration Rule (XForwarder)
- .collect_cycle
- TestToggleDestinationApi
- get_latest_metrics_per_target
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- XForwarder - Agent Development Guide
- test_performance_and_optimizations.py
- Experience 004: Backward Compatibility and Automated Schema Migrations
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- 2. Mandatory Helper Centralization
- Interactive Requirements Clarification (Reverse Prompt Engineering)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 82 edges
2. `TestUIAndAPIEdgeCases` - 60 edges
3. `showToast()` - 48 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 40 edges
6. `decide_route()` - 39 edges
7. `validate_rule()` - 28 edges
8. `import_config_data()` - 28 edges
9. `t()` - 28 edges
10. `TestPerformanceAndOptimizations` - 25 edges

## Surprising Connections (you probably didn't know these)
- `2. Non-Negotiable Architectural Invariants` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/AGENTS.md → core/config_manager.py
- `3. Architecture & Solution Implemented` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `4. Invariants & Rules for AI Agents` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `Required Normalization Rules:` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/rules/backward-compatibility-and-migrations.md → core/config_manager.py

## Import Cycles
- None detected.

## Communities (158 total, 92 thin omitted)

### Community 1 - "time"
Cohesion: 0.12
Nodes (9): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_nftables_counters_json(), prune_old_traffic_records(), read_nftables_port_stats() (+1 more)

### Community 3 - "engine.py"
Cohesion: 0.09
Nodes (13): _c_locale_env(), _ip_family_flag(), measure_packet_loss_50(), parse_ping_output(), check_destination(), fast_confirm_burst(), get_route_interface(), is_interface_up() (+5 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.16
Nodes (55): apt_install_safe(), ask(), ask_secret(), backup_restore_menu(), card_copy(), card_end(), card_kv(), card_sep() (+47 more)

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

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.22
Nodes (23): t(), closeRuleModal(), currentModalDestinations, getCurrentInboundSpec(), getPrioTagClass(), handleDestTypeChange(), handleModalPrioDragEnd(), handleModalPrioDragLeave() (+15 more)

### Community 16 - ".agents/AGENTS.md"
Cohesion: 0.14
Nodes (10): 1. System Model, 2. Non-Negotiable Architectural Invariants, 3. On-Demand Rules, Skills & Tooling, XForwarder Master Architecture Constitution, 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`) (+2 more)

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 19 - "parse_nftables_text"
Cohesion: 0.05
Nodes (22): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Implemented Solution & Architecture, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction, ports_overlap(), _build_xforwarder_range_rule_from_nftables(), _build_xforwarder_rule_from_nftables() (+14 more)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "XForwarderWebHandler"
Cohesion: 0.23
Nodes (3): 1. Server-Side HTTP Performance, 4. Invariants & Rules for AI Agents, XForwarderWebHandler

### Community 22 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 24 - "firewall.py"
Cohesion: 0.19
Nodes (5): apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), fake_apply_nftables()

### Community 25 - "rules.js"
Cohesion: 0.15
Nodes (23): closeSwitchLogsModal(), copySwitchLogsToClipboard(), fallbackCopy(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver() (+15 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.22
Nodes (7): Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops), Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "route_quality.py"
Cohesion: 0.12
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window()

### Community 29 - "os"
Cohesion: 0.07
Nodes (14): check_file(), main(), get_protected_ports(), split_port_interval_excluding(), handle_sig(), _find_conntrack_bin(), _apply_protected_port_splits(), backup_legacy_nftables() (+6 more)

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
Cohesion: 0.22
Nodes (23): deleteRule(), renderRuleListRow(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart() (+15 more)

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.15
Nodes (8): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup, 3. Two-Tier Intelligent Failover & Route Quality Architecture, sync_rules_and_notify()

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

### Community 46 - "initApp"
Cohesion: 0.28
Nodes (15): initApp(), startAuthenticatedSession(), checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth() (+7 more)

### Community 48 - "sanitize_target_host"
Cohesion: 0.15
Nodes (3): Key Decisions & Architectural Changes, sanitize_target_host(), summarize_cycle()

### Community 49 - "subprocess"
Cohesion: 0.23
Nodes (9): check_syntax(), get_modified_py_files(), main(), _read_hook_stdin(), main(), run_step(), show_git_status(), validate_json_files() (+1 more)

### Community 51 - "run_scheduled_ping_round"
Cohesion: 0.15
Nodes (9): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, Architecture & Failover Rules (XForwarder), get_unique_targets_from_config(), prune_old_metrics() (+1 more)

### Community 54 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 56 - "haproxy_parser.py"
Cohesion: 0.15
Nodes (8): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), find_candidate_nftables_files(), TestHAProxyParser

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 60 - "import_config_data"
Cohesion: 0.05
Nodes (5): import_config_data(), LossMonitorScheduler, TestExportImport, TestMetricsSubsystem, load_config()

### Community 63 - "record_ping_result"
Cohesion: 0.22
Nodes (4): get_metrics_db_path(), get_metrics_history(), init_metrics_db(), record_ping_result()

### Community 64 - "json"
Cohesion: 0.07
Nodes (19): get_full_version_status(), get_installed_version(), get_local_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_update_state() (+11 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "TrafficCollector"
Cohesion: 0.12
Nodes (5): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact, TrafficCollector

### Community 68 - "experiences/README.md"
Cohesion: 0.18
Nodes (7): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 70 - "get_network_interfaces_info"
Cohesion: 0.18
Nodes (5): get_system_stats(), is_ignored_interface(), get_network_interfaces_info(), _safe_flush_port_conntrack(), TestNetworkInterfaces

### Community 72 - "quality.js"
Cohesion: 0.17
Nodes (19): trackFailoverEvents(), API_BASE, cleanPath, fetchApi(), addLogEntry(), appendLogEntry(), fallbackCopyLogs(), initLogs() (+11 more)

### Community 73 - "system.js"
Cohesion: 0.38
Nodes (9): closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress() (+1 more)

### Community 74 - "⚡ Core Rules & Constraints"
Cohesion: 0.18
Nodes (6): ⚡ Core Rules & Constraints, 2. Selective Service Reloading, 7. Dual-Feedback L4 Port & Traffic Blackhole Detection, 1. High-Risk Core Components, parse_haproxy_backend_csv(), read_haproxy_backend_health()

### Community 75 - "session-state.py"
Cohesion: 0.24
Nodes (7): get_next_number(), main(), slugify(), load_state(), main(), save_state(), show_state()

### Community 77 - "web_server.py"
Cohesion: 0.06
Nodes (29): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), verify_password(), _coerce_bool() (+21 more)

### Community 78 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 79 - "app.js"
Cohesion: 0.15
Nodes (26): _architecturalCompliance(), pendingOverrides, previousActivePriorities, initAmbientEffects(), SPOTLIGHT_SELECTOR, syncNavIndicatorMetrics(), updateNavIndicator(), checkImportableRules() (+18 more)

### Community 80 - "stats.js"
Cohesion: 0.14
Nodes (18): fetchStatus(), stopAuthenticatedSession(), lastLatestLoss, lastRuntime, lastTrafficData, setCurrentRules(), setLastLatestLoss(), setLastRuntime() (+10 more)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "i18n.js"
Cohesion: 0.38
Nodes (10): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), toggleLanguage() (+2 more)

### Community 89 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 94 - "Large Files Inspection & Surgical Editing Rule"
Cohesion: 0.40
Nodes (4): 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite), 3. Immediate Syntax Verification, Large Files Inspection & Surgical Editing Rule

### Community 96 - "3. Architecture & Solution Implemented"
Cohesion: 0.28
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 100 - "Backward Compatibility & Automated Schema Migration Rule (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup, 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`), 4. Legacy Path & CLI Compatibility, Backward Compatibility & Automated Schema Migration Rule (XForwarder), Required Normalization Rules:

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 111 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 114 - "Experience 004: Backward Compatibility and Automated Schema Migrations"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations

### Community 119 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 123 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 126 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

## Knowledge Gaps
- **92 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `time`, `TestPerformanceAndOptimizations`, `engine.py`, `.test_nftables_dual_stack_rules_generation`, `TestXForwarderMigration`, `os`, `TestTrafficAwareFailover`, `TestToggleDestination`, `TestNginxStreamEngine`, `2. Non-Negotiable Architectural Constraints`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `sanitize_target_host`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `import_config_data`, `⚡ Core Rules & Constraints`, `web_server.py`, `3. Architecture & Solution Implemented`, `test_performance_and_optimizations.py`?**
  _High betweenness centrality (0.255) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TestEngineProbes`) actually correct?**
  _`XForwarderEngine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `DummyHandler` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Why does `⚡ Core Rules & Constraints` connect `⚡ Core Rules & Constraints` to `engine.py`, `escapeHtml`, `web_server.py`, `app.js`, `sanitize_target_host`, `XForwarder - Agent Development Guide`, `run_scheduled_ping_round`, `parse_nftables_text`, `sync_system_rules`, `rules.js`, `parse_ping_replies`, `import_config_data`, `os`?**
  _High betweenness centrality (0.184) - this node is a cross-community bridge._
- **Should `time` be split into smaller, more focused modules?**
  _Cohesion score 0.12012012012012012 - nodes in this community are weakly interconnected._
- **Why does `TestUIAndAPIEdgeCases` connect `TestUIAndAPIEdgeCases` to `.test_services_status_api_and_dom`, `time`, `.test_nftables_destination_must_be_ip_address`, `.test_nftables_dual_stack_rules_generation`, `.test_ovira_effects_module_and_pointer_safety`, `.test_ovira_login_split_screen_and_controls_integrity`, `.test_drag_and_drop_edge_cases_and_reorder_logic`, `.test_ui_proxy_protocol_and_test_target_dom`, `.test_drag_and_drop_priority_reordering_integrity`, `.test_static_asset_cache_control_and_versioning`, `.test_rules_view_toggle_and_category_assets`, `.test_packet_loss_diagnostic_tool_elements`, `.test_validate_rule_arbitrary_priorities`, `.test_switch_logs_modal_and_event_persistence`, `.test_overview_relay_engines_alignment_and_responsive`, `.test_validate_rule_empty_destinations_rejected`, `.test_topology_and_engines_grid_layout`, `.test_validate_rule_destination_defaults_port_if_missing`, `.test_rule_update_created_at_preservation`, `firewall.py`, `.test_pre_auth_flicker_prevention`, `.test_signin_button_direct_click_and_deferred_execution_safety`, `.test_tcp_udp_protocol_formatting_and_no_both`, `.test_validate_rule_haproxy_requires_ipv6`, `.test_validate_rule_port_boundary_conditions`, `.test_service_restart_dom_and_ui_wiring`, `XForwarderEngine`, `sanitize_target_host`, `.test_service_restart_edge_cases_and_failures`, `.test_latency_badge_classification_edge_cases`, `TestXForwarderSecurity`, `.test_override_endpoint_flushes_conntrack`, `web_server.py`, `.test_cli_ovira_mint_tui_design_and_safety_guards`, `.test_validate_rule_invalid_characters_rejected`, `.test_topbar_extended_system_metrics_and_api`, `.test_frontend_css_no_hover_motion_transforms`, `.test_restart_services_action_logic`, `.test_system_update_dom_and_ui_wiring`, `.test_security_settings_responsive_layout_and_info_item_wrapping`, `.test_copy_port_and_category_json_and_import_modal`, `.test_frontend_js_latency_and_priority_shortening`, `.test_full_responsive_system_integrity`, `.test_nova_admin_design_system_and_login_cleanup`, `.test_static_assets_integrity`, `.test_installer_nginx_ipv6_and_dpkg_recovery_guards`, `.test_version_detection_with_commit_file_and_fallback`, `.test_rule_category_and_created_at_validation`, `.test_login_form_event_prevention_and_auth_integrity`, `.test_get_update_status_parsing_and_ansi_cleaning`, `.test_session_token_header_authentication_flow`, `.test_service_restart_api_endpoints`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
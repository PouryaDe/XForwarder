# Graph Report - Forward-Manager  (2026-11-16)

## Corpus Check
- 107 files · ~142,372 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1624 nodes · 3567 edges · 145 communities (65 shown, 80 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 253 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0c09d1a7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- re
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
- time
- The 8-Point Audit Checklist
- rule_modal.js
- Large Files Inspection & Surgical Editing Rule
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- .agents/AGENTS.md
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Intermediate Relay VPS Constraints Rule (XForwarder)
- classify_status
- engine.py
- rules.js
- XForwarder Operations Runbook
- aggregate_window
- TestI18nAndRTL
- os
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- TestTrafficAwareFailover
- escapeHtml
- TestToggleDestination
- initTheme
- TestNginxStreamEngine
- TestRouteQualityEngine
- XForwarder Master Architecture Constitution
- Experience 004: Backward Compatibility and Automated Schema Migrations
- 3. Architecture & Solution Implemented
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- Architectural Solutions Implemented
- showToast
- TestUIAndAPIEdgeCases
- XForwarderEngine
- session-state.py
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- Session State & Task Handoff Rule (XForwarder)
- TestFastFailoverAndAntiFlap
- TestXForwarderSecurity
- sync_system_rules
- nftables_parser.py
- TestTargetMetricCache
- parse_ping_replies
- TestExportImport
- prober.py
- json
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- experiences/README.md
- 5. Verification & Testing
- app.js
- TrafficCollector
- web_server.py
- XForwarderWebHandler
- Architectural Solutions Implemented
- .collect_cycle
- parse_proc_net_dev
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- t
- import_export.js
- read_haproxy_backend_health
- test_modular_subsystems.py
- 3. Architecture & Solution Implemented
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- 2. Non-Negotiable Architectural Constraints
- Backward Compatibility & Automated Schema Migration Rule (XForwarder)
- TestModularSubsystems
- TestTrafficSubsystem
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- sys
- XForwarder - Agent Development Guide

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 83 edges
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

## Communities (145 total, 80 thin omitted)

### Community 0 - "re"
Cohesion: 0.29
Nodes (3): get_next_number(), main(), slugify()

### Community 1 - "traffic.py"
Cohesion: 0.18
Nodes (7): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), prune_old_traffic_records(), reset_traffic_counter()

### Community 3 - "metrics.py"
Cohesion: 0.12
Nodes (11): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), measure_packet_loss_50(), parse_ping_output() (+3 more)

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

### Community 13 - "time"
Cohesion: 0.10
Nodes (10): fast_confirm_burst(), get_network_interfaces_info(), do_ping(), get_services_status(), get_system_stats(), is_ignored_interface(), ping_target(), get_network_interfaces_info() (+2 more)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.22
Nodes (19): closeRuleModal(), currentModalDestinations, getPrioTagClass(), handleDestTypeChange(), handleModalPrioDragEnd(), handleModalPrioDragLeave(), handleModalPrioDragOver(), handleModalPrioDragStart() (+11 more)

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
Cohesion: 0.13
Nodes (10): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule, 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering) (+2 more)

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
Cohesion: 0.11
Nodes (9): handle_sig(), apply_nftables(), _find_conntrack_bin(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), compute_score(), pick_best_now() (+1 more)

### Community 25 - "rules.js"
Cohesion: 0.13
Nodes (26): closeSwitchLogsModal(), copySwitchLogsToClipboard(), fallbackCopy(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver() (+18 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "aggregate_window"
Cohesion: 0.12
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window()

### Community 29 - "os"
Cohesion: 0.14
Nodes (11): check_syntax(), get_modified_py_files(), main(), main(), run_step(), show_git_status(), validate_json_files(), apply_haproxy() (+3 more)

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
Cohesion: 0.27
Nodes (20): renderRuleListRow(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData() (+12 more)

### Community 37 - "initTheme"
Cohesion: 1.00
Nodes (3): initTheme(), toggleTheme(), updateThemeToggleUI()

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "Experience 004: Backward Compatibility and Automated Schema Migrations"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations

### Community 42 - "3. Architecture & Solution Implemented"
Cohesion: 0.20
Nodes (5): 1. Context & Motivation, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

### Community 46 - "showToast"
Cohesion: 0.14
Nodes (30): initApp(), API_BASE, cleanPath, fetchApi(), checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin() (+22 more)

### Community 48 - "XForwarderEngine"
Cohesion: 0.10
Nodes (6): 2. Selective Service Reloading, Key Decisions & Architectural Changes, 1. High-Risk Core Components, XForwarderEngine, get_route_interface(), is_interface_up()

### Community 49 - "session-state.py"
Cohesion: 0.53
Nodes (4): load_state(), main(), save_state(), show_state()

### Community 50 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 51 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 54 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 56 - "nftables_parser.py"
Cohesion: 0.07
Nodes (22): 3. Implemented Solution & Architecture, _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), backup_legacy_nftables() (+14 more)

### Community 59 - "parse_ping_replies"
Cohesion: 0.16
Nodes (5): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestFamilySelection, TestPerReplyParsing

### Community 63 - "prober.py"
Cohesion: 0.12
Nodes (10): ⚡ Core Rules & Constraints, _c_locale_env(), _ip_family_flag(), sanitize_target_host(), _is_valid_target(), check_destination(), is_private_or_tunnel_target(), probe_destination_icmp() (+2 more)

### Community 64 - "json"
Cohesion: 0.10
Nodes (14): _coerce_bool(), export_config_data(), get_config_path(), import_config_data(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), is_valid_target() (+6 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "experiences/README.md"
Cohesion: 0.18
Nodes (7): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 73 - "app.js"
Cohesion: 0.12
Nodes (30): _architecturalCompliance(), fetchStatus(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), stopAuthenticatedSession(), trackFailoverEvents(), checkImportableRules() (+22 more)

### Community 75 - "web_server.py"
Cohesion: 0.08
Nodes (22): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+14 more)

### Community 77 - "XForwarderWebHandler"
Cohesion: 0.09
Nodes (9): 1. Server-Side HTTP Performance, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, XForwarderWebHandler (+1 more)

### Community 78 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 79 - ".collect_cycle"
Cohesion: 0.13
Nodes (4): classify_tunnel_type(), parse_nftables_counters_json(), read_haproxy_port_stats(), read_nftables_port_stats()

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "t"
Cohesion: 0.18
Nodes (22): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), t() (+14 more)

### Community 89 - "import_export.js"
Cohesion: 0.38
Nodes (9): closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig(), initImportExport(), openImportModal(), parseAndValidateImportJson() (+1 more)

### Community 94 - "test_modular_subsystems.py"
Cohesion: 0.13
Nodes (8): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), verify_password(), get_state_file_path()

### Community 96 - "3. Architecture & Solution Implemented"
Cohesion: 0.22
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 99 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.13
Nodes (10): 2. Non-Negotiable Architectural Constraints, 2. Root Cause / Core Dynamics, 1. System Overview, 2. Zero-Collision Rule (Mandatory), 3. Two-Tier Intelligent Failover & Route Quality Architecture, 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, 7. Dual-Feedback L4 Port & Traffic Blackhole Detection (+2 more)

### Community 100 - "Backward Compatibility & Automated Schema Migration Rule (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup, 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`), 4. Legacy Path & CLI Compatibility, Backward Compatibility & Automated Schema Migration Rule (XForwarder), Required Normalization Rules:

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 116 - "sys"
Cohesion: 0.12
Nodes (3): check_file(), main(), notify_engine_wakeup()

### Community 146 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

## Knowledge Gaps
- **174 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `TRANSLATIONS`, `DEFAULT_LANG` (+169 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 669 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `TestPerformanceAndOptimizations`, `metrics.py`, `TestXForwarderMigration`, `.test_nftables_dual_stack_rules_generation`, `time`, `engine.py`, `TestMetricsSubsystem`, `TestTrafficAwareFailover`, `TestToggleDestination`, `TestNginxStreamEngine`, `3. Architecture & Solution Implemented`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `json`, `TrafficCollector`, `web_server.py`, `3. Architecture & Solution Implemented`, `2. Non-Negotiable Architectural Constraints`, `sys`?**
  _High betweenness centrality (0.252) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _174 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.0420899854862119 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `json`, `metrics.py`, `XForwarder Master Architecture Constitution`, `XForwarderEngine`, `t`, `engine.py`, `import_export.js`, `nftables_parser.py`, `parse_ping_replies`, `rules.js`, `prober.py`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11931818181818182 - nodes in this community are weakly interconnected._
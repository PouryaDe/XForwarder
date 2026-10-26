# Graph Report - Forward-Manager  (2026-10-26)

## Corpus Check
- 99 files · ~108,877 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1329 nodes · 2969 edges · 117 communities (61 shown, 56 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 176 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b94dec2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
- engine.py
- TestPerformanceAndOptimizations
- traffic.py
- TestFastFailoverAndAntiFlap
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- test_metrics_subsystem.py
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
- web_server.py
- app.js
- XForwarder Operations Runbook
- os
- Architectural Solutions Implemented
- .do_POST
- escapeHtml
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- experiences/README.md
- json
- traffic.js
- subprocess
- stats.js
- TestNginxStreamEngine
- metrics.py
- XForwarder Master Architecture Constitution
- shutil
- 2. Non-Negotiable Architectural Constraints
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- .evaluate_rule
- auth.js
- TestUIAndAPIEdgeCases
- XForwarderEngine
- DummyHandler
- time
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- TestXForwarderSecurity
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- test_probe_accuracy.py
- TestTargetMetricCache
- LossMonitorScheduler
- parse_ping_replies
- navigation.js
- .sync_firewall_and_proxies
- showToast
- sync_system_rules
- Architecture & Failover Rules (XForwarder)
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- experience-logging.md
- Session State & Task Handoff Rule (XForwarder)
- is_interface_up
- 2. Mandatory Helper Centralization
- initTheme
- Architectural Solutions Implemented
- Experience 003: Native Python Zero-Dependency Web Server
- XForwarder - Agent Development Guide
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- system.js

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 68 edges
2. `TestUIAndAPIEdgeCases` - 49 edges
3. `showToast()` - 42 edges
4. `escapeHtml()` - 36 edges
5. `import_config_data()` - 27 edges
6. `TestPerformanceAndOptimizations` - 25 edges
7. `XForwarderWebHandler` - 22 edges
8. `TestTrafficSubsystem` - 20 edges
9. `validate_rule()` - 20 edges
10. `initApp()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `3. Fast IPC Engine Wake-Up` --references--> `notify_engine_wakeup()`  [INFERRED]
  .agents/experiences/008-full-stack-performance-and-fast-ipc.md → core/web_server.py

## Import Cycles
- None detected.

## Communities (117 total, 56 thin omitted)

### Community 0 - "TestRouteQualityEngine"
Cohesion: 0.06
Nodes (8): aggregate_window(), classify_status(), compute_score(), decide_route(), pick_best_now(), summarize_cycle(), TestSustainedCriticalClassification, TestRouteQualityEngine

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

### Community 9 - "test_metrics_subsystem.py"
Cohesion: 0.13
Nodes (8): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), prune_old_metrics(), record_ping_result(), run_scheduled_ping_round()

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
Cohesion: 0.06
Nodes (23): 3. Implemented Solution & Architecture, _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), backup_legacy_nftables() (+15 more)

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

### Community 23 - "migrate_and_normalize_config"
Cohesion: 0.12
Nodes (13): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup (+5 more)

### Community 24 - "web_server.py"
Cohesion: 0.07
Nodes (23): 3. Architecture & Solution Implemented, get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path() (+15 more)

### Community 25 - "app.js"
Cohesion: 0.18
Nodes (21): pendingOverrides, previousActivePriorities, getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart() (+13 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "os"
Cohesion: 0.23
Nodes (5): check_file(), main(), get_next_number(), main(), slugify()

### Community 28 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 29 - ".do_POST"
Cohesion: 0.06
Nodes (14): 1. Server-Side HTTP Performance, 4. Invariants & Rules for AI Agents, export_config_data(), get_config_path(), import_config_data(), load_config(), load_state(), save_config() (+6 more)

### Community 30 - "escapeHtml"
Cohesion: 0.31
Nodes (12): initApp(), trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics() (+4 more)

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "experiences/README.md"
Cohesion: 0.15
Nodes (10): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover, Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring (+2 more)

### Community 34 - "json"
Cohesion: 0.11
Nodes (10): load_state(), main(), save_state(), show_state(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), is_valid_target() (+2 more)

### Community 35 - "traffic.js"
Cohesion: 0.31
Nodes (15): closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadTrafficModalData(), openTrafficModal(), populateTrafficEntitySelect(), promptResetTraffic() (+7 more)

### Community 36 - "subprocess"
Cohesion: 0.27
Nodes (7): check_syntax(), get_modified_py_files(), main(), main(), run_step(), show_git_status(), validate_json_files()

### Community 37 - "stats.js"
Cohesion: 0.13
Nodes (19): fetchStatus(), stopAuthenticatedSession(), updateCategoryDatalist(), currentRules, lastRuntime, lastTrafficData, setCurrentRules(), setLastRuntime() (+11 more)

### Community 39 - "metrics.py"
Cohesion: 0.13
Nodes (10): _c_locale_env(), _ip_family_flag(), measure_packet_loss_50(), parse_ping_output(), sanitize_target_host(), check_destination(), fast_confirm_burst(), is_private_or_tunnel_target() (+2 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "shutil"
Cohesion: 0.11
Nodes (8): apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), apply_haproxy(), apply_nginx(), generate_haproxy_cfg(), generate_nginx_cfg()

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.20
Nodes (7): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 46 - "auth.js"
Cohesion: 0.31
Nodes (13): checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth(), initInlineSecurityForm(), initSecurityModal() (+5 more)

### Community 48 - "XForwarderEngine"
Cohesion: 0.16
Nodes (3): Key Decisions & Architectural Changes, XForwarderEngine, get_route_interface()

### Community 50 - "time"
Cohesion: 0.08
Nodes (14): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), verify_password(), get_network_interfaces_info() (+6 more)

### Community 51 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 53 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 55 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 56 - "test_probe_accuracy.py"
Cohesion: 0.31
Nodes (3): _iputils_output(), TestEngineIcmpProbe, TestFamilySelection

### Community 60 - "navigation.js"
Cohesion: 0.43
Nodes (6): _architecturalCompliance(), closeMobileSidebar(), initNavigation(), openMobileSidebar(), SECTIONS, switchSection()

### Community 62 - "showToast"
Cohesion: 0.22
Nodes (16): ⚡ Core Rules & Constraints, cleanPath, fetchApi(), closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig() (+8 more)

### Community 63 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 64 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 67 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 68 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 69 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 73 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 74 - "initTheme"
Cohesion: 1.00
Nodes (3): initTheme(), toggleTheme(), updateThemeToggleUI()

### Community 78 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

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
Cohesion: 0.26
Nodes (12): startAuthenticatedSession(), API_BASE, checkImportableRules(), closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager() (+4 more)

## Knowledge Gaps
- **157 isolated node(s):** `1. Project Overview & Terminology`, `3. Specialized Skills Index (Progressive Disclosure)`, `4. Active Workspace Rules (Conditional Disclosure)`, `5. Workflows & Automation Scripts`, `6. Experiences Catalog` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 531 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `engine.py`, `TestPerformanceAndOptimizations`, `traffic.py`, `TestFastFailoverAndAntiFlap`, `is_interface_up`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `2. Non-Negotiable Architectural Constraints`, `TestEngineProbes`, `.evaluate_rule`, `.test_packet_loss_calculation_and_probes`, `TestUIAndAPIEdgeCases`, `web_server.py`, `TestTargetMetricCache`, `LossMonitorScheduler`, `.sync_firewall_and_proxies`, `sync_system_rules`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `1. Project Overview & Terminology`, `3. Specialized Skills Index (Progressive Disclosure)`, `4. Active Workspace Rules (Conditional Disclosure)` to the rest of the system?**
  _157 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.058823529411764705 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `XForwarder Master Architecture Constitution`, `test_metrics_subsystem.py`, `.evaluate_rule`, `nftables_parser.py`, `migrate_and_normalize_config`, `app.js`, `parse_ping_replies`, `.do_POST`, `showToast`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._
- **Why does `XForwarder Master Architecture Constitution` connect `XForwarder Master Architecture Constitution` to `2. Non-Negotiable Architectural Constraints`, `.agents/AGENTS.md`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
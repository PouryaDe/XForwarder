# Graph Report - Forward-Manager  (2026-10-26)

## Corpus Check
- 99 files · ~108,384 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1324 nodes · 2958 edges · 111 communities (67 shown, 44 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 176 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b5085125`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
- os
- TestPerformanceAndOptimizations
- escapeHtml
- TestFastFailoverAndAntiFlap
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- metrics.py
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
- service_manager.py
- app.js
- XForwarder Operations Runbook
- TestTrafficSubsystem
- typing
- .do_POST
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- LossMonitorScheduler
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- re
- traffic.js
- web_server.py
- stats.js
- TestNginxStreamEngine
- subprocess
- XForwarder Master Architecture Constitution
- prober.py
- 2. Non-Negotiable Architectural Constraints
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- traffic.py
- auth.js
- TestUIAndAPIEdgeCases
- XForwarderEngine
- DummyHandler
- auth.py
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- TestXForwarderSecurity
- validate_rule
- restart_services_action
- engine.py
- TestTargetMetricCache
- import_config_data
- parse_ping_replies
- showToast
- sync_system_rules
- Architecture & Failover Rules (XForwarder)
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- experiences/README.md
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- .evaluate_rule
- test_modular_subsystems.py
- initTheme
- firewall.py
- get_network_interfaces_info
- notify_engine_wakeup
- .sync_firewall_and_proxies
- load_config
- Experience 003: Native Python Zero-Dependency Web Server
- XForwarder - Agent Development Guide
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- system.js
- export_config_data
- experience-logging.md

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 68 edges
2. `TestUIAndAPIEdgeCases` - 48 edges
3. `showToast()` - 42 edges
4. `escapeHtml()` - 34 edges
5. `import_config_data()` - 27 edges
6. `TestPerformanceAndOptimizations` - 25 edges
7. `XForwarderWebHandler` - 22 edges
8. `initApp()` - 20 edges
9. `xforwarder.sh script` - 20 edges
10. `TestTrafficSubsystem` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `3. Architecture & Solution Implemented` --references--> `start_system_update()`  [INFERRED]
  .agents/experiences/010-decoupled-in-panel-system-updates-and-reconnect-flow.md → core/service_manager.py
- `2. Root Cause / Core Dynamics` --references--> `XForwarderEngine`  [INFERRED]
  .agents/experiences/007-fix-haproxy-silent-drop-and-state-wipeout.md → core/engine.py
- `⚡ Core Rules & Constraints` --references--> `LossMonitorScheduler`  [INFERRED]
  AGENTS.md → core/metrics.py

## Import Cycles
- None detected.

## Communities (111 total, 44 thin omitted)

### Community 0 - "TestRouteQualityEngine"
Cohesion: 0.06
Nodes (3): classify_status(), TestSustainedCriticalClassification, TestRouteQualityEngine

### Community 1 - "os"
Cohesion: 0.13
Nodes (7): check_file(), main(), load_state(), main(), save_state(), show_state(), handle_sig()

### Community 3 - "escapeHtml"
Cohesion: 0.31
Nodes (12): initApp(), trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics() (+4 more)

### Community 5 - "🌐 XForwarder"
Cohesion: 0.14
Nodes (13): 🌐 XForwarder, روش اول — از طریق ترمینال سرور:, روش دوم — با دستور تک‌خطی از گیت‌هاب:, قانون عدم تداخل پورت‌ها (Zero-Collision Forwarding):, 📄 لایسنس (License), ⚡ ۱. نصب سریع با دستور تک‌خطی (Quick One-Liner Install), 🔄 ۲. بروزرسانی بدون قطعی (Zero-Downtime Update), 🏛 ۳. معماری و نحوه کارکرد سیستم (Architecture) (+5 more)

### Community 6 - "xforwarder.sh"
Cohesion: 0.32
Nodes (31): backup_restore_menu(), change_all_web_settings(), change_password(), change_web_password(), change_web_port(), change_web_secret_path(), change_web_ssl(), change_web_username() (+23 more)

### Community 7 - "Workflow: Deploy & Update Services"
Cohesion: 0.29
Nodes (6): Step 1: Backup Configuration, Step 2: Copy Updated Files to Installation Directory, Step 3: Syntax Verification, Step 4: Restart Daemons, Step 5: Post-Deployment Health Check, Workflow: Deploy & Update Services

### Community 9 - "metrics.py"
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

### Community 23 - "migrate_and_normalize_config"
Cohesion: 0.05
Nodes (25): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 4. Client-Side Smoothness, 1. Rapid Failure Detection & Confirmation Burst (<1s) (+17 more)

### Community 24 - "service_manager.py"
Cohesion: 0.11
Nodes (13): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+5 more)

### Community 25 - "app.js"
Cohesion: 0.13
Nodes (28): _architecturalCompliance(), pendingOverrides, previousActivePriorities, closeMobileSidebar(), initNavigation(), openMobileSidebar(), SECTIONS, switchSection() (+20 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "TestTrafficSubsystem"
Cohesion: 0.05
Nodes (5): get_traffic_resets(), get_traffic_summary(), parse_proc_net_dev(), read_proc_net_dev(), TestTrafficSubsystem

### Community 28 - "typing"
Cohesion: 0.14
Nodes (7): check_syntax(), get_modified_py_files(), main(), apply_haproxy(), apply_nginx(), generate_haproxy_cfg(), generate_nginx_cfg()

### Community 29 - ".do_POST"
Cohesion: 0.22
Nodes (4): 4. Invariants & Rules for AI Agents, load_state(), sync_rules_and_notify(), XForwarderWebHandler

### Community 30 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "re"
Cohesion: 0.33
Nodes (3): get_next_number(), main(), slugify()

### Community 35 - "traffic.js"
Cohesion: 0.31
Nodes (15): closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadTrafficModalData(), openTrafficModal(), populateTrafficEntitySelect(), promptResetTraffic() (+7 more)

### Community 36 - "web_server.py"
Cohesion: 0.13
Nodes (11): get_sessions_file_path(), load_sessions_from_disk(), save_sessions_to_disk(), get_sessions_file_path(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_sessions_from_disk() (+3 more)

### Community 37 - "stats.js"
Cohesion: 0.16
Nodes (16): fetchStatus(), stopAuthenticatedSession(), lastTrafficData, setCurrentRules(), setLastRuntime(), setLastTrafficData(), state, copyIpToClipboard() (+8 more)

### Community 39 - "subprocess"
Cohesion: 0.11
Nodes (12): 3. Architecture & Solution Implemented, main(), run_step(), show_git_status(), validate_json_files(), get_route_interface(), is_interface_up(), get_network_interfaces_info() (+4 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "prober.py"
Cohesion: 0.14
Nodes (8): _c_locale_env(), _ip_family_flag(), check_destination(), fast_confirm_burst(), is_private_or_tunnel_target(), probe_destination_icmp(), validate_probe_route(), TestFamilySelection

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.20
Nodes (7): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "traffic.py"
Cohesion: 0.13
Nodes (10): classify_tunnel_type(), get_traffic_db_path(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_stats_csv(), parse_nftables_counters_json(), prune_old_traffic_records(), read_haproxy_port_stats() (+2 more)

### Community 46 - "auth.js"
Cohesion: 0.31
Nodes (13): checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth(), initInlineSecurityForm(), initSecurityModal() (+5 more)

### Community 48 - "XForwarderEngine"
Cohesion: 0.15
Nodes (3): Key Decisions & Architectural Changes, XForwarderEngine, TrafficCollector

### Community 50 - "auth.py"
Cohesion: 0.12
Nodes (7): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule, check_rate_limit(), hash_password(), record_failed_login(), verify_password()

### Community 51 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 53 - "TestXForwarderSecurity"
Cohesion: 0.12
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 55 - "restart_services_action"
Cohesion: 0.18
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, restart_services_action()

### Community 56 - "engine.py"
Cohesion: 0.20
Nodes (5): aggregate_window(), compute_score(), decide_route(), pick_best_now(), summarize_cycle()

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 62 - "showToast"
Cohesion: 0.23
Nodes (16): ⚡ Core Rules & Constraints, cleanPath, fetchApi(), closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig() (+8 more)

### Community 63 - "sync_system_rules"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

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

### Community 68 - "experiences/README.md"
Cohesion: 0.33
Nodes (4): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, XForwarder Architectural Experiences Catalog

### Community 69 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 72 - "test_modular_subsystems.py"
Cohesion: 0.17
Nodes (6): get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), is_valid_target(), update_state_rules()

### Community 74 - "initTheme"
Cohesion: 1.00
Nodes (3): initTheme(), toggleTheme(), updateThemeToggleUI()

### Community 75 - "firewall.py"
Cohesion: 0.24
Nodes (4): apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported()

### Community 76 - "get_network_interfaces_info"
Cohesion: 0.28
Nodes (3): is_ignored_interface(), get_network_interfaces_info(), TestNetworkInterfaces

### Community 78 - "notify_engine_wakeup"
Cohesion: 0.29
Nodes (4): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, notify_engine_wakeup()

### Community 80 - "load_config"
Cohesion: 0.40
Nodes (3): get_config_path(), load_config(), save_config()

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

### Community 96 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

## Knowledge Gaps
- **157 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `0. Requirements Clarification & Blast Radius`, `1. Code Verification & Syntax`, `2. Automated Verification Pipeline` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 529 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `.evaluate_rule`, `XForwarder Master Architecture Constitution`, `metrics.py`, `nftables_parser.py`, `migrate_and_normalize_config`, `app.js`, `import_config_data`, `parse_ping_replies`, `showToast`?**
  _High betweenness centrality (0.204) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `0. Requirements Clarification & Blast Radius` to the rest of the system?**
  _157 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.06031746031746032 - nodes in this community are weakly interconnected._
- **Why does `XForwarderEngine` connect `XForwarderEngine` to `os`, `TestPerformanceAndOptimizations`, `.test_haproxy_performance_fallback_on_old_binary`, `web_server.py`, `TestFastFailoverAndAntiFlap`, `.evaluate_rule`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `prober.py`, `2. Non-Negotiable Architectural Constraints`, `.test_packet_loss_calculation_and_probes`, `TestEngineProbes`, `.sync_firewall_and_proxies`, `engine.py`, `TestTargetMetricCache`, `LossMonitorScheduler`, `.test_nftables_dual_stack_rules_generation`, `sync_system_rules`?**
  _High betweenness centrality (0.180) - this node is a cross-community bridge._
- **Should `os` be split into smaller, more focused modules?**
  _Cohesion score 0.13306451612903225 - nodes in this community are weakly interconnected._
- **Why does `XForwarder Master Architecture Constitution` connect `XForwarder Master Architecture Constitution` to `2. Non-Negotiable Architectural Constraints`, `.agents/AGENTS.md`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
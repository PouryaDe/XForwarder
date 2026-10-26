# Graph Report - Forward-Manager  (2026-10-26)

## Corpus Check
- 100 files · ~112,196 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1370 nodes · 3042 edges · 117 communities (63 shown, 54 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 176 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eac7d8ea`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestRouteQualityEngine
- os
- TestPerformanceAndOptimizations
- traffic.py
- TestFastFailoverAndAntiFlap
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- nftables_parser.py
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- deactivate_legacy_rules
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
- proxy_gen.py
- app.js
- XForwarder Operations Runbook
- json
- shutil
- subprocess
- get_route_interface
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- time
- traffic.js
- TestToggleDestination
- stats.js
- TestNginxStreamEngine
- engine.py
- XForwarder Master Architecture Constitution
- re
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
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- haproxy_parser.py
- TestTargetMetricCache
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- parse_ping_replies
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- XForwarderEngine
- showToast
- get_services_status
- Architecture & Failover Rules (XForwarder)
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- experience-logging.md
- get_network_interfaces_info
- route_quality.py
- test_probe_accuracy.py
- escapeHtml
- .do_POST
- TestEngineIcmpProbe
- Experience 003: Native Python Zero-Dependency Web Server
- XForwarder - Agent Development Guide
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- system.js
- experiences/README.md

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 73 edges
2. `TestUIAndAPIEdgeCases` - 49 edges
3. `showToast()` - 43 edges
4. `escapeHtml()` - 36 edges
5. `import_config_data()` - 27 edges
6. `TestPerformanceAndOptimizations` - 25 edges
7. `XForwarderWebHandler` - 23 edges
8. `validate_rule()` - 22 edges
9. `initApp()` - 20 edges
10. `TestTrafficSubsystem` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `2. Non-Negotiable Architectural Constraints` --references--> `import_config_data()`  [INFERRED]
  .agents/AGENTS.md → core/config_manager.py
- `2. Non-Negotiable Architectural Constraints` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/AGENTS.md → core/config_manager.py
- `2. Non-Negotiable Architectural Constraints` --references--> `get_unique_targets_from_config()`  [INFERRED]
  .agents/AGENTS.md → core/metrics.py
- `2. Non-Negotiable Architectural Constraints` --references--> `parse_ping_replies()`  [INFERRED]
  .agents/AGENTS.md → core/metrics.py

## Import Cycles
- None detected.

## Communities (117 total, 54 thin omitted)

### Community 1 - "os"
Cohesion: 0.13
Nodes (3): check_file(), main(), handle_sig()

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

### Community 9 - "nftables_parser.py"
Cohesion: 0.18
Nodes (9): _build_xforwarder_rule_from_nftables(), discover_all_relay_rules(), discover_importable_nftables_rules(), find_candidate_nftables_files(), get_live_nftables_rules(), _is_valid_target(), parse_iptables_text(), parse_nftables_json() (+1 more)

### Community 10 - "Mandatory Task Completion & Verification Workflow (XForwarder)"
Cohesion: 0.18
Nodes (10): 0. Requirements Clarification & Blast Radius, 1. Code Verification & Syntax, 2. Automated Verification Pipeline, 3. Requirement Convergence, 4. Documentation Synchronization, 5. UI Consistency (If Web Modified), 6. Experience Logging, 7. Safe Git Operations & Token Efficiency (+2 more)

### Community 11 - "Workflow: Add Port Rule"
Cohesion: 0.33
Nodes (5): Step 1: Gather Rule Parameters, Step 2: Validate Target Reachability, Step 3: Register Rule in Configuration, Step 4: Verify Synchronization, Workflow: Add Port Rule

### Community 12 - "Workflow: Diagnose Failover & Forwarding"
Cohesion: 0.33
Nodes (5): Step 1: Check Runtime Daemon State, Step 2: Check Systemd Logs, Step 3: Verify Zero-Collision Rule Enforcement, Step 4: Test Manual Override, Workflow: Diagnose Failover & Forwarding

### Community 13 - "deactivate_legacy_rules"
Cohesion: 0.11
Nodes (7): 3. Implemented Solution & Architecture, backup_legacy_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), import_all_relay_rules_into_config(), import_nftables_rules_into_config(), TestNFTablesParser

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

### Community 24 - "proxy_gen.py"
Cohesion: 0.21
Nodes (4): apply_haproxy(), apply_nginx(), generate_haproxy_cfg(), generate_nginx_cfg()

### Community 25 - "app.js"
Cohesion: 0.17
Nodes (22): pendingOverrides, previousActivePriorities, getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart() (+14 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "json"
Cohesion: 0.20
Nodes (7): load_state(), main(), save_state(), show_state(), get_sessions_file_path(), load_sessions_from_disk(), save_sessions_to_disk()

### Community 28 - "shutil"
Cohesion: 0.19
Nodes (5): apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), restart_services_action()

### Community 29 - "subprocess"
Cohesion: 0.27
Nodes (7): check_syntax(), get_modified_py_files(), main(), main(), run_step(), show_git_status(), validate_json_files()

### Community 31 - "TestMetricsSubsystem"
Cohesion: 0.06
Nodes (3): LossMonitorScheduler, TestMetricsSubsystem, load_config()

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "time"
Cohesion: 0.08
Nodes (16): check_rate_limit(), record_failed_login(), export_config_data(), get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), is_valid_target() (+8 more)

### Community 35 - "traffic.js"
Cohesion: 0.31
Nodes (15): closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadTrafficModalData(), openTrafficModal(), populateTrafficEntitySelect(), promptResetTraffic() (+7 more)

### Community 37 - "stats.js"
Cohesion: 0.13
Nodes (19): fetchStatus(), stopAuthenticatedSession(), updateCategoryDatalist(), currentRules, lastRuntime, lastTrafficData, setCurrentRules(), setLastRuntime() (+11 more)

### Community 39 - "engine.py"
Cohesion: 0.08
Nodes (19): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, _c_locale_env(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), _ip_family_flag() (+11 more)

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "re"
Cohesion: 0.25
Nodes (3): get_next_number(), main(), slugify()

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.16
Nodes (7): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

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
Cohesion: 0.09
Nodes (21): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+13 more)

### Community 51 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 53 - "TestXForwarderSecurity"
Cohesion: 0.05
Nodes (14): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting, 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization (+6 more)

### Community 55 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 56 - "haproxy_parser.py"
Cohesion: 0.17
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 58 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.50
Nodes (3): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact

### Community 59 - "parse_ping_replies"
Cohesion: 0.28
Nodes (3): parse_ping_replies(), _iputils_output(), TestPerReplyParsing

### Community 60 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 61 - "XForwarderEngine"
Cohesion: 0.16
Nodes (5): 2. Selective Service Reloading, Key Decisions & Architectural Changes, 1. High-Risk Core Components, XForwarderEngine, is_interface_up()

### Community 62 - "showToast"
Cohesion: 0.28
Nodes (14): ⚡ Core Rules & Constraints, closeImportModal(), copyCategoryJson(), copyRuleJson(), getSanitizedRuleForExport(), handleExportConfig(), initImportExport(), openImportModal() (+6 more)

### Community 63 - "get_services_status"
Cohesion: 0.14
Nodes (8): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules(), get_services_status()

### Community 64 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 71 - "route_quality.py"
Cohesion: 0.22
Nodes (4): aggregate_window(), compute_score(), pick_best_now(), summarize_cycle()

### Community 72 - "test_probe_accuracy.py"
Cohesion: 0.21
Nodes (3): classify_status(), TestFamilySelection, TestSustainedCriticalClassification

### Community 74 - "escapeHtml"
Cohesion: 0.23
Nodes (15): initApp(), trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics() (+7 more)

### Community 77 - ".do_POST"
Cohesion: 0.06
Nodes (13): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, 4. Invariants & Rules for AI Agents, get_config_path(), import_config_data(), load_config(), save_config() (+5 more)

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

### Community 125 - "experiences/README.md"
Cohesion: 0.29
Nodes (4): Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, XForwarder Architectural Experiences Catalog

## Knowledge Gaps
- **157 isolated node(s):** `1. Project Overview & Terminology`, `3. Specialized Skills Index (Progressive Disclosure)`, `4. Active Workspace Rules (Conditional Disclosure)`, `5. Workflows & Automation Scripts`, `6. Experiences Catalog` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 552 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **54 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `os`, `TestPerformanceAndOptimizations`, `TestFastFailoverAndAntiFlap`, `TestToggleDestination`, `TestNginxStreamEngine`, `engine.py`, `TestXForwarderMigration`, `2. Non-Negotiable Architectural Constraints`, `.test_packet_loss_calculation_and_probes`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `.evaluate_rule`, `web_server.py`, `TestTargetMetricCache`, `TestMetricsSubsystem`, `get_route_interface`, `get_services_status`?**
  _High betweenness centrality (0.256) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TestEngineProbes`) actually correct?**
  _`XForwarderEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `1. Project Overview & Terminology`, `3. Specialized Skills Index (Progressive Disclosure)`, `4. Active Workspace Rules (Conditional Disclosure)` to the rest of the system?**
  _157 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestRouteQualityEngine` be split into smaller, more focused modules?**
  _Cohesion score 0.06906906906906907 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `engine.py`, `XForwarder Master Architecture Constitution`, `nftables_parser.py`, `.do_POST`, `.evaluate_rule`, `migrate_and_normalize_config`, `app.js`, `parse_ping_replies`, `showToast`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Should `os` be split into smaller, more focused modules?**
  _Cohesion score 0.12941176470588237 - nodes in this community are weakly interconnected._
- **Why does `XForwarder Master Architecture Constitution` connect `XForwarder Master Architecture Constitution` to `2. Non-Negotiable Architectural Constraints`, `.agents/AGENTS.md`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
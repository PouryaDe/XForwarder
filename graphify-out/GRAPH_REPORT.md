# Graph Report - Forward-Manager  (2026-10-27)

## Corpus Check
- 102 files · ~120,543 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1438 nodes · 3186 edges · 135 communities (64 shown, 71 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c5bed9d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- 5. Verification & Testing
- metrics.py
- TestPerformanceAndOptimizations
- prober.py
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- TestRouteQualityEngine
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- traffic.py
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
- get_network_interfaces_info
- rules.js
- XForwarder Operations Runbook
- Architectural Solutions Implemented
- json
- TestXForwarderSecurity
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- LossMonitorScheduler
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- os
- escapeHtml
- TestToggleDestination
- fetchStatus
- TestNginxStreamEngine
- record_ping_result
- XForwarder Master Architecture Constitution
- engine.py
- 3. Architecture & Solution Implemented
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- import_config_data
- initApp
- TestUIAndAPIEdgeCases
- TestMetricsSubsystem
- DummyHandler
- web_server.py
- nftables_parser.py
- TestFastFailoverAndAntiFlap
- sync_system_rules
- haproxy_parser.py
- TestTargetMetricCache
- .sync_firewall_and_proxies
- parse_ping_replies
- verify-all.py
- XForwarderEngine
- showToast
- is_port_in_use_by_external_service
- XForwarder - Agent Development Guide
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- experiences/README.md
- TestModularSubsystems
- route_quality.py
- Architecture & Failover Rules (XForwarder)
- quality.js
- syntax-check.py
- XForwarderWebHandler
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Experience 003: Native Python Zero-Dependency Web Server
- experience-logging.md
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- Session State & Task Handoff Rule (XForwarder)
- parse_ping_output
- app.js
- 5. Verification & Testing
- is_interface_up
- get_route_interface
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 76 edges
2. `TestUIAndAPIEdgeCases` - 53 edges
3. `showToast()` - 43 edges
4. `escapeHtml()` - 39 edges
5. `TestRouteQualityEngine` - 29 edges
6. `import_config_data()` - 27 edges
7. `decide_route()` - 27 edges
8. `validate_rule()` - 25 edges
9. `XForwarderWebHandler` - 25 edges
10. `TestPerformanceAndOptimizations` - 25 edges

## Surprising Connections (you probably didn't know these)
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `4. Invariants & Rules for AI Agents` --references--> `aggregate_window()`  [INFERRED]
  .agents/experiences/016-fix-window-expiration-loop-and-switch-decision-logging.md → core/route_quality.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py

## Import Cycles
- None detected.

## Communities (135 total, 71 thin omitted)

### Community 1 - "metrics.py"
Cohesion: 0.23
Nodes (6): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_unique_targets_from_config(), measure_packet_loss_50(), prune_old_metrics(), run_scheduled_ping_round(), sanitize_target_host()

### Community 3 - "prober.py"
Cohesion: 0.17
Nodes (6): _c_locale_env(), _ip_family_flag(), fast_confirm_burst(), is_private_or_tunnel_target(), probe_destination_icmp(), validate_probe_route()

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

### Community 13 - "traffic.py"
Cohesion: 0.05
Nodes (16): classify_tunnel_type(), get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_stats_csv(), parse_nftables_counters_json() (+8 more)

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
Nodes (7): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule, Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 22 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 23 - "classify_status"
Cohesion: 0.17
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, classify_status(), TestSustainedCriticalClassification

### Community 24 - "get_network_interfaces_info"
Cohesion: 0.15
Nodes (6): get_network_interfaces_info(), do_ping(), is_ignored_interface(), ping_target(), get_network_interfaces_info(), TestNetworkInterfaces

### Community 25 - "rules.js"
Cohesion: 0.15
Nodes (20): deleteRule(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart(), handlePathDrop() (+12 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "Architectural Solutions Implemented"
Cohesion: 0.17
Nodes (11): 4. Client-Side Smoothness, 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, 5. Web UI Real-Time Visibility, Architectural Solutions Implemented, Context & Motivation (+3 more)

### Community 28 - "json"
Cohesion: 0.08
Nodes (13): get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_update_state(), save_update_state(), start_system_update(), _worker() (+5 more)

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "os"
Cohesion: 0.17
Nodes (9): check_file(), main(), get_next_number(), main(), slugify(), load_state(), main(), save_state() (+1 more)

### Community 35 - "escapeHtml"
Cohesion: 0.27
Nodes (20): renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData(), openTrafficModal() (+12 more)

### Community 37 - "fetchStatus"
Cohesion: 0.12
Nodes (20): fetchStatus(), stopAuthenticatedSession(), updateCategoryDatalist(), currentRules, lastLatestLoss, lastRuntime, lastTrafficData, setCurrentRules() (+12 more)

### Community 39 - "record_ping_result"
Cohesion: 0.17
Nodes (5): get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), init_metrics_db(), record_ping_result()

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 41 - "engine.py"
Cohesion: 0.08
Nodes (12): handle_sig(), apply_nftables(), flush_conntrack(), generate_nftables_ruleset(), is_ipv6_supported(), check_destination(), apply_haproxy(), apply_nginx() (+4 more)

### Community 42 - "3. Architecture & Solution Implemented"
Cohesion: 0.24
Nodes (5): 1. Context & Motivation, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "import_config_data"
Cohesion: 0.07
Nodes (17): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup (+9 more)

### Community 46 - "initApp"
Cohesion: 0.30
Nodes (14): initApp(), checkSession(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth(), initInlineSecurityForm() (+6 more)

### Community 50 - "web_server.py"
Cohesion: 0.08
Nodes (23): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), reset_rate_limit(), save_sessions_to_disk(), verify_password() (+15 more)

### Community 51 - "nftables_parser.py"
Cohesion: 0.18
Nodes (8): 3. Implemented Solution & Architecture, import_haproxy_rules_into_config(), backup_legacy_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), import_all_relay_rules_into_config(), import_nftables_rules_into_config(), _is_valid_target()

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (8): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, 2. Root Cause / Core Dynamics, sync_system_rules()

### Community 56 - "haproxy_parser.py"
Cohesion: 0.07
Nodes (15): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), parse_haproxy_content(), parse_haproxy_file(), _build_xforwarder_rule_from_nftables(), discover_all_relay_rules(), discover_importable_nftables_rules() (+7 more)

### Community 59 - "parse_ping_replies"
Cohesion: 0.16
Nodes (5): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestFamilySelection, TestPerReplyParsing

### Community 60 - "verify-all.py"
Cohesion: 0.53
Nodes (4): main(), run_step(), show_git_status(), validate_json_files()

### Community 61 - "XForwarderEngine"
Cohesion: 0.15
Nodes (3): Key Decisions & Architectural Changes, 3. Two-Tier Intelligent Failover & Route Quality Architecture, XForwarderEngine

### Community 62 - "showToast"
Cohesion: 0.22
Nodes (18): 2. Non-Negotiable Architectural Constraints, ⚡ Core Rules & Constraints, API_BASE, cleanPath, fetchApi(), closeImportModal(), copyCategoryJson(), copyRuleJson() (+10 more)

### Community 63 - "is_port_in_use_by_external_service"
Cohesion: 0.33
Nodes (3): is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service()

### Community 64 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "experiences/README.md"
Cohesion: 0.29
Nodes (4): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog

### Community 70 - "TestModularSubsystems"
Cohesion: 0.09
Nodes (6): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_full_version_status(), TestModularSubsystems

### Community 71 - "route_quality.py"
Cohesion: 0.16
Nodes (4): aggregate_window(), compute_score(), pick_best_now(), summarize_cycle()

### Community 72 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 74 - "quality.js"
Cohesion: 0.26
Nodes (10): trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics(), renderDisruptionsTable() (+2 more)

### Community 75 - "syntax-check.py"
Cohesion: 0.53
Nodes (3): check_syntax(), get_modified_py_files(), main()

### Community 77 - "XForwarderWebHandler"
Cohesion: 0.07
Nodes (14): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+6 more)

### Community 78 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 80 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 83 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 89 - "app.js"
Cohesion: 0.18
Nodes (22): _architecturalCompliance(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), checkImportableRules(), closeMobileSidebar(), initNavigation(), openMobileSidebar() (+14 more)

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

## Knowledge Gaps
- **163 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `SECTIONS`, `currentModalDestinations` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 583 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **71 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `metrics.py`, `TestPerformanceAndOptimizations`, `TestXForwarderMigration`, `traffic.py`, `json`, `LossMonitorScheduler`, `TestToggleDestination`, `TestNginxStreamEngine`, `engine.py`, `3. Architecture & Solution Implemented`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `TestMetricsSubsystem`, `web_server.py`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `.sync_firewall_and_proxies`, `is_interface_up`, `.test_packet_loss_calculation_and_probes`, `get_route_interface`, `.test_haproxy_performance_fallback_on_old_binary`, `.test_engine_load_config_returns_dict`?**
  _High betweenness centrality (0.246) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _163 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.06896551724137931 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `showToast` to `metrics.py`, `XForwarder Master Architecture Constitution`, `3. Architecture & Solution Implemented`, `import_config_data`, `haproxy_parser.py`, `parse_ping_replies`, `XForwarderEngine`?**
  _High betweenness centrality (0.184) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `🌐 XForwarder` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
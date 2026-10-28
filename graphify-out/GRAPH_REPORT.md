# Graph Report - Forward-Manager  (2026-10-28)

## Corpus Check
- 104 files · ~126,764 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .css 6, .service 4, (none) 2)

## Summary
- 1495 nodes · 3270 edges · 142 communities (64 shown, 78 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 216 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d4938f62`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- 5. Verification & Testing
- traffic.py
- TestPerformanceAndOptimizations
- metrics.py
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- TestRouteQualityEngine
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- web_server.py
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
- Dynamic Packet-Loss Driven Failover Engine & Rule Switch Logs
- rules.js
- XForwarder Operations Runbook
- route_quality.py
- os
- time
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TestMetricsSubsystem
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- json
- escapeHtml
- TestToggleDestination
- initApp
- TestNginxStreamEngine
- get_network_interfaces_info
- XForwarder Master Architecture Constitution
- TestTrafficSubsystem
- 2. Non-Negotiable Architectural Constraints
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- import_config_data
- showToast
- TestUIAndAPIEdgeCases
- XForwarderEngine
- DummyHandler
- Architectural Solutions Implemented
- prober.py
- TestFastFailoverAndAntiFlap
- validate_rule
- sync_system_rules
- nftables_parser.py
- TestTargetMetricCache
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- parse_ping_replies
- engine.py
- .sync_firewall_and_proxies
- LossMonitorScheduler
- .collect_cycle
- XForwarder - Agent Development Guide
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- test_traffic.py
- Architectural Solutions Implemented
- system.js
- 5. Verification & Testing
- TestToggleDestinationApi
- Architecture & Failover Rules (XForwarder)
- quality.js
- Session State & Task Handoff Rule (XForwarder)
- .do_POST
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Experience 003: Native Python Zero-Dependency Web Server
- experience-logging.md
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- XForwarderWebServer
- app.js
- pick_best_now
- parse_proc_net_dev
- TrafficCollector
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- experiences/README.md
- parse_haproxy_stats_csv
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- parse_ping_output
- get_route_interface
- is_interface_up
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 76 edges
2. `TestUIAndAPIEdgeCases` - 54 edges
3. `TestRouteQualityEngine` - 43 edges
4. `showToast()` - 43 edges
5. `escapeHtml()` - 41 edges
6. `decide_route()` - 39 edges
7. `import_config_data()` - 27 edges
8. `validate_rule()` - 25 edges
9. `XForwarderWebHandler` - 25 edges
10. `TestPerformanceAndOptimizations` - 25 edges

## Surprising Connections (you probably didn't know these)
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `3. Fast IPC Engine Wake-Up` --references--> `notify_engine_wakeup()`  [INFERRED]
  .agents/experiences/008-full-stack-performance-and-fast-ipc.md → core/web_server.py

## Import Cycles
- None detected.

## Communities (142 total, 78 thin omitted)

### Community 1 - "traffic.py"
Cohesion: 0.21
Nodes (6): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), reset_traffic_counter()

### Community 3 - "metrics.py"
Cohesion: 0.12
Nodes (11): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), measure_packet_loss_50(), prune_old_metrics() (+3 more)

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

### Community 13 - "web_server.py"
Cohesion: 0.10
Nodes (14): get_full_version_status(), get_update_log_path(), get_update_state_file_path(), get_update_status(), load_update_state(), get_full_version_status(), get_sessions_file_path(), get_update_log_path() (+6 more)

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

### Community 24 - "Dynamic Packet-Loss Driven Failover Engine & Rule Switch Logs"
Cohesion: 0.12
Nodes (16): Dynamic Packet-Loss Driven Failover Engine & Rule Switch Logs, اصول سه گانه سیستم جدید:, الف) باگ‌های منطقی در سناریوهای شبکه واقعی (Logical Edge Cases), ب) باگ‌های ساختاری و همزمانی (Structural & Concurrency Bugs), برنامه جامع پیاده‌سازی سیستم اولویت‌بندی و سوئیچینگ داینامیک و ماژول لاگ‌ها, ج) باگ‌ها و الزامات امنیتی (Security & Defense in Depth), گام‌های الگوریتم:, ۱. دکمه لاگ در هر کارت پورت (`Rule Card`) و ردیف لیست (`Rule Row`): (+8 more)

### Community 25 - "rules.js"
Cohesion: 0.16
Nodes (22): closeSwitchLogsModal(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver(), handlePathDragStart(), handlePathDrop() (+14 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.40
Nodes (5): Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "route_quality.py"
Cohesion: 0.10
Nodes (8): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window(), compute_score(), summarize_cycle()

### Community 28 - "os"
Cohesion: 0.11
Nodes (11): 3. Architecture & Solution Implemented, apply_haproxy(), apply_nginx(), generate_haproxy_cfg(), generate_nginx_cfg(), get_script_path(), restart_services_action(), save_update_state() (+3 more)

### Community 29 - "time"
Cohesion: 0.10
Nodes (9): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), reset_rate_limit(), save_sessions_to_disk(), verify_password() (+1 more)

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 34 - "json"
Cohesion: 0.11
Nodes (14): load_state(), main(), save_state(), show_state(), check_syntax(), get_modified_py_files(), main(), main() (+6 more)

### Community 35 - "escapeHtml"
Cohesion: 0.25
Nodes (21): deleteRule(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData() (+13 more)

### Community 37 - "initApp"
Cohesion: 0.11
Nodes (24): fetchStatus(), initApp(), startAuthenticatedSession(), stopAuthenticatedSession(), checkSession(), showDashboard(), showLogin(), updateCategoryDatalist() (+16 more)

### Community 39 - "get_network_interfaces_info"
Cohesion: 0.19
Nodes (5): do_ping(), is_ignored_interface(), ping_target(), get_network_interfaces_info(), TestNetworkInterfaces

### Community 40 - "XForwarder Master Architecture Constitution"
Cohesion: 0.33
Nodes (6): 1. Project Overview & Terminology, 3. Specialized Skills Index (Progressive Disclosure), 4. Active Workspace Rules (Conditional Disclosure), 5. Workflows & Automation Scripts, 6. Experiences Catalog, XForwarder Master Architecture Constitution

### Community 42 - "2. Non-Negotiable Architectural Constraints"
Cohesion: 0.17
Nodes (9): 2. Non-Negotiable Architectural Constraints, 1. Context & Motivation, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout, is_haproxy_listening(), is_nginx_listening() (+1 more)

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "import_config_data"
Cohesion: 0.07
Nodes (17): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations, 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup (+9 more)

### Community 46 - "showToast"
Cohesion: 0.24
Nodes (16): API_BASE, cleanPath, fetchApi(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth() (+8 more)

### Community 48 - "XForwarderEngine"
Cohesion: 0.14
Nodes (3): Key Decisions & Architectural Changes, 3. Two-Tier Intelligent Failover & Route Quality Architecture, XForwarderEngine

### Community 50 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 51 - "prober.py"
Cohesion: 0.13
Nodes (8): _c_locale_env(), _ip_family_flag(), check_destination(), fast_confirm_burst(), is_private_or_tunnel_target(), probe_destination_icmp(), validate_probe_route(), TestFamilySelection

### Community 54 - "validate_rule"
Cohesion: 0.07
Nodes (6): is_valid_target(), validate_rule(), get_installed_version(), get_local_version_info(), get_system_stats(), TestModularSubsystems

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (8): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, 2. Root Cause / Core Dynamics, sync_system_rules()

### Community 56 - "nftables_parser.py"
Cohesion: 0.05
Nodes (28): 3. Implemented Solution & Architecture, check_file(), main(), get_next_number(), main(), slugify(), _build_xforwarder_rule(), discover_importable_rules() (+20 more)

### Community 58 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 60 - "engine.py"
Cohesion: 0.12
Nodes (4): handle_sig(), apply_nftables(), generate_nftables_ruleset(), is_ipv6_supported()

### Community 63 - ".collect_cycle"
Cohesion: 0.18
Nodes (3): classify_tunnel_type(), read_haproxy_port_stats(), read_nftables_port_stats()

### Community 64 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. Table Isolation in NFTables, 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "Architectural Solutions Implemented"
Cohesion: 0.20
Nodes (9): 1. Server-Side HTTP Performance, 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility (+1 more)

### Community 70 - "system.js"
Cohesion: 0.38
Nodes (9): closeSystemUpdateModal(), fetchSystemVersionInfo(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress() (+1 more)

### Community 73 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 74 - "quality.js"
Cohesion: 0.26
Nodes (10): trackFailoverEvents(), addLogEntry(), appendLogEntry(), initLogs(), initDiagPacketLossTool(), initNetworkQualityMonitor(), loadNetworkQualityMetrics(), renderDisruptionsTable() (+2 more)

### Community 75 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 77 - ".do_POST"
Cohesion: 0.12
Nodes (11): 4. Invariants & Rules for AI Agents, export_config_data(), get_config_path(), get_state_file_path(), load_config(), load_state(), save_config(), update_state_rules() (+3 more)

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

### Community 89 - "app.js"
Cohesion: 0.16
Nodes (24): ⚡ Core Rules & Constraints, _architecturalCompliance(), pendingOverrides, previousActivePriorities, checkImportableRules(), closeImportModal(), copyCategoryJson(), copyRuleJson() (+16 more)

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 99 - "experiences/README.md"
Cohesion: 0.25
Nodes (4): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog

### Community 101 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

## Knowledge Gaps
- **177 isolated node(s):** `previousActivePriorities`, `pendingOverrides`, `cleanPath`, `SECTIONS`, `currentModalDestinations` (+172 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 612 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **78 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `TestPerformanceAndOptimizations`, `metrics.py`, `TestXForwarderMigration`, `.test_nftables_dual_stack_rules_generation`, `web_server.py`, `TestMetricsSubsystem`, `json`, `TestToggleDestination`, `TestNginxStreamEngine`, `2. Non-Negotiable Architectural Constraints`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `engine.py`, `.sync_firewall_and_proxies`, `LossMonitorScheduler`, `.test_packet_loss_calculation_and_probes`, `TrafficCollector`, `get_route_interface`, `is_interface_up`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `LossMonitorScheduler`) actually correct?**
  _`XForwarderEngine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `previousActivePriorities`, `pendingOverrides`, `cleanPath` to the rest of the system?**
  _177 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
- **Why does `2. Non-Negotiable Architectural Constraints` connect `2. Non-Negotiable Architectural Constraints` to `metrics.py`, `XForwarder Master Architecture Constitution`, `import_config_data`, `XForwarderEngine`, `nftables_parser.py`, `app.js`, `parse_ping_replies`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `TestUIAndAPIEdgeCases` (e.g. with `XForwarderEngine` and `XForwarderWebHandler`) actually correct?**
  _`TestUIAndAPIEdgeCases` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12310606060606061 - nodes in this community are weakly interconnected._
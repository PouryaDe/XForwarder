# Graph Report - Forward-Manager  (2026-11-21)

## Corpus Check
- 107 files · ~149,773 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1720 nodes · 3866 edges · 142 communities (66 shown, 76 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 248 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `046d7769`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- import_config_data
- traffic.py
- TestPerformanceAndOptimizations
- XForwarderWebHandler
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- decide_route
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- TestXForwarderSecurity
- The 8-Point Audit Checklist
- rule_modal.js
- .agents/AGENTS.md
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- route_quality.py
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- os
- nftables_parser.py
- classify_status
- session-state.py
- rules.js
- XForwarder Operations Runbook
- route_quality.py
- TestI18nAndRTL
- haproxy_parser.py
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- quality.js
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- experiences/README.md
- TestTrafficAwareFailover
- escapeHtml
- TestToggleDestination
- get_network_interfaces_info
- TestNginxStreamEngine
- TestRouteQualityEngine
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- XForwarderEngine
- parse_nftables_text
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- Architectural Solutions Implemented
- ⚡ Core Rules & Constraints
- TestUIAndAPIEdgeCases
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- syntax-check.py
- flush_conntrack
- get_rule_port_bounds
- TestFastFailoverAndAntiFlap
- auth.py
- sync_system_rules
- parse_nftables_text
- TestTargetMetricCache
- parse_ping_replies
- import_config_data
- engine.py
- web_server.py
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Architecture & Failover Rules (XForwarder)
- i18n.js
- 5. Verification & Testing
- showToast
- Session State & Task Handoff Rule (XForwarder)
- verify-all.py
- test_nftables_parser.py
- Architectural Solutions Implemented
- app.js
- stats.js
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Experience 003: Native Python Zero-Dependency Web Server
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- system.js
- TestModularSubsystems
- Intermediate Relay VPS Constraints Rule (XForwarder)
- 3. Architecture & Solution Implemented
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- restart_services_action
- Large Files Inspection & Surgical Editing Rule

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 82 edges
2. `TestUIAndAPIEdgeCases` - 59 edges
3. `showToast()` - 49 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 42 edges
6. `decide_route()` - 39 edges
7. `import_config_data()` - 30 edges
8. `t()` - 29 edges
9. `validate_rule()` - 29 edges
10. `TestPerformanceAndOptimizations` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `3. Fast IPC Engine Wake-Up` --references--> `notify_engine_wakeup()`  [INFERRED]
  .agents/experiences/008-full-stack-performance-and-fast-ipc.md → core/web_server.py
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py

## Import Cycles
- None detected.

## Communities (142 total, 76 thin omitted)

### Community 0 - "import_config_data"
Cohesion: 0.05
Nodes (25): 1. System Model, 2. Non-Negotiable Architectural Invariants, 3. On-Demand Rules, Skills & Tooling, XForwarder Master Architecture Constitution, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents (+17 more)

### Community 1 - "traffic.py"
Cohesion: 0.05
Nodes (17): classify_tunnel_type(), get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), parse_haproxy_backend_csv(), parse_haproxy_stats_csv() (+9 more)

### Community 3 - "XForwarderWebHandler"
Cohesion: 0.11
Nodes (4): 1. Server-Side HTTP Performance, 4. Invariants & Rules for AI Agents, XForwarderWebHandler, TestToggleDestinationApi

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
Cohesion: 0.17
Nodes (31): addExcludedTokens(), buildTunnelIfaceTagsHtml(), closeRuleModal(), currentExcludedTags, currentModalDestinations, ensureNetworkInterfacesLoaded(), getAvailableServerInterfaces(), getCurrentInboundSpec() (+23 more)

### Community 16 - ".agents/AGENTS.md"
Cohesion: 0.15
Nodes (8): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule, 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 19 - "route_quality.py"
Cohesion: 0.27
Nodes (3): compute_score(), pick_best_now(), summarize_cycle()

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "os"
Cohesion: 0.05
Nodes (28): check_file(), main(), export_config_data(), get_config_path(), get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service() (+20 more)

### Community 22 - "nftables_parser.py"
Cohesion: 0.19
Nodes (5): split_port_interval_excluding(), _build_xforwarder_range_rule_from_nftables(), find_candidate_nftables_files(), _invert_excluded_ports_to_ranges(), _is_valid_target()

### Community 24 - "session-state.py"
Cohesion: 0.24
Nodes (7): get_next_number(), main(), slugify(), load_state(), main(), save_state(), show_state()

### Community 25 - "rules.js"
Cohesion: 0.12
Nodes (32): ⚡ Core Rules & Constraints, t(), closeSwitchLogsModal(), copySwitchLogsToClipboard(), deleteRule(), fallbackCopy(), getPrioTagClass(), handleOverrideChange() (+24 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.22
Nodes (7): Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops), Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "route_quality.py"
Cohesion: 0.12
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window()

### Community 29 - "haproxy_parser.py"
Cohesion: 0.18
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 31 - "quality.js"
Cohesion: 0.27
Nodes (11): addLogEntry(), appendLogEntry(), fallbackCopyLogs(), initLogs(), currentDisruptions, initNetworkQualityMonitor(), loadNetworkQualityMetrics(), renderDisruptionsCurrentPage() (+3 more)

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "experiences/README.md"
Cohesion: 0.18
Nodes (7): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 35 - "escapeHtml"
Cohesion: 0.30
Nodes (18): renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData(), openTrafficModal() (+10 more)

### Community 37 - "get_network_interfaces_info"
Cohesion: 0.22
Nodes (4): is_ignored_interface(), get_network_interfaces_info(), _safe_flush_port_conntrack(), TestNetworkInterfaces

### Community 38 - "TestNginxStreamEngine"
Cohesion: 0.09
Nodes (4): 2. Selective Service Reloading, 1. Table Isolation in NFTables, 1. High-Risk Core Components, TestNginxStreamEngine

### Community 40 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 42 - "parse_nftables_text"
Cohesion: 0.14
Nodes (8): _apply_protected_port_splits(), _build_xforwarder_rule_from_nftables(), discover_importable_nftables_rules(), get_live_nftables_rules(), _merge_or_append_rule(), parse_iptables_text(), parse_nftables_json(), parse_nftables_text()

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

### Community 46 - "⚡ Core Rules & Constraints"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 48 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 49 - "syntax-check.py"
Cohesion: 0.48
Nodes (4): check_syntax(), get_modified_py_files(), main(), _read_hook_stdin()

### Community 50 - "flush_conntrack"
Cohesion: 0.17
Nodes (8): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup, 3. Two-Tier Intelligent Failover & Route Quality Architecture, sync_rules_and_notify()

### Community 51 - "get_rule_port_bounds"
Cohesion: 0.33
Nodes (4): get_rule_port_bounds(), ports_overlap(), rules_ports_overlap(), _conflicts_existing_or_discovered()

### Community 54 - "auth.py"
Cohesion: 0.10
Nodes (11): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), reset_rate_limit(), save_sessions_to_disk(), verify_password() (+3 more)

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 56 - "parse_nftables_text"
Cohesion: 0.13
Nodes (4): deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), _parse_port_tokens(), TestNFTablesParser

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 63 - "engine.py"
Cohesion: 0.06
Nodes (26): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, 7. Dual-Feedback L4 Port & Traffic Blackhole Detection, handle_sig(), is_ipv6_supported(), _c_locale_env(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history() (+18 more)

### Community 64 - "web_server.py"
Cohesion: 0.08
Nodes (18): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+10 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.33
Nodes (5): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 70 - "i18n.js"
Cohesion: 0.38
Nodes (10): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), toggleLanguage() (+2 more)

### Community 72 - "showToast"
Cohesion: 0.18
Nodes (23): API_BASE, cleanPath, fetchApi(), closeSecurityModal(), evaluatePasswordStrength(), handleLogin(), handleLogout(), initAuth() (+15 more)

### Community 73 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 74 - "verify-all.py"
Cohesion: 0.53
Nodes (4): main(), run_step(), show_git_status(), validate_json_files()

### Community 77 - "test_nftables_parser.py"
Cohesion: 0.16
Nodes (6): 3. Implemented Solution & Architecture, get_protected_ports(), backup_legacy_nftables(), discover_all_relay_rules(), import_all_relay_rules_into_config(), import_nftables_rules_into_config()

### Community 78 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 79 - "app.js"
Cohesion: 0.12
Nodes (33): _architecturalCompliance(), fetchStatus(), initApp(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), stopAuthenticatedSession(), trackFailoverEvents() (+25 more)

### Community 80 - "stats.js"
Cohesion: 0.16
Nodes (11): currentRules, lastLatestLoss, lastNetwork, lastRuntime, lastTrafficData, state, copyIpToClipboard(), lastSystemStats (+3 more)

### Community 81 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "system.js"
Cohesion: 0.42
Nodes (8): closeSystemUpdateModal(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress(), startSystemUpdateProcedure()

### Community 93 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 96 - "3. Architecture & Solution Implemented"
Cohesion: 0.22
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 119 - "restart_services_action"
Cohesion: 0.15
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, restart_services_action()

### Community 125 - "Large Files Inspection & Surgical Editing Rule"
Cohesion: 0.40
Nodes (4): 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite), 3. Immediate Syntax Verification, Large Files Inspection & Surgical Editing Rule

## Knowledge Gaps
- **76 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `⚡ Core Rules & Constraints` connect `rules.js` to `import_config_data`, `traffic.py`, `showToast`, `test_nftables_parser.py`, `⚡ Core Rules & Constraints`, `get_rule_port_bounds`, `nftables_parser.py`, `sync_system_rules`, `parse_ping_replies`, `import_config_data`, `engine.py`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TestEngineProbes`) actually correct?**
  _`XForwarderEngine` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Should `import_config_data` be split into smaller, more focused modules?**
  _Cohesion score 0.050505050505050504 - nodes in this community are weakly interconnected._
- **Why does `XForwarderEngine` connect `XForwarderEngine` to `3. Architecture & Solution Implemented`, `web_server.py`, `TestPerformanceAndOptimizations`, `TestTrafficAwareFailover`, `TestToggleDestination`, `.test_nftables_dual_stack_rules_generation`, `TestNginxStreamEngine`, `TestXForwarderMigration`, `TestEngineProbes`, `flush_conntrack`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `import_config_data`, `engine.py`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Should `traffic.py` be split into smaller, more focused modules?**
  _Cohesion score 0.045253164556962024 - nodes in this community are weakly interconnected._
- **Why does `TestUIAndAPIEdgeCases` connect `TestUIAndAPIEdgeCases` to `import_config_data`, `traffic.py`, `.test_nftables_dual_stack_rules_generation`, `.test_login_form_event_prevention_and_auth_integrity`, `XForwarderWebHandler`, `.test_services_status_api_and_dom`, `.test_nftables_destination_must_be_ip_address`, `.test_switch_logs_modal_and_event_persistence`, `.test_installer_nginx_ipv6_and_dpkg_recovery_guards`, `.test_rules_view_toggle_and_category_assets`, `.test_ui_proxy_protocol_and_test_target_dom`, `.test_frontend_css_no_hover_motion_transforms`, `.test_frontend_js_latency_and_priority_shortening`, `TestXForwarderSecurity`, `.test_drag_and_drop_edge_cases_and_reorder_logic`, `.test_overview_relay_engines_alignment_and_responsive`, `.test_validate_rule_arbitrary_priorities`, `.test_topology_and_engines_grid_layout`, `.test_validate_rule_empty_destinations_rejected`, `.test_nova_admin_design_system_and_login_cleanup`, `.test_system_version_and_update_apis`, `.test_validate_rule_destination_defaults_port_if_missing`, `XForwarderEngine`, `.test_latency_badge_classification_edge_cases`, `auth.py`, `.test_override_endpoint_flushes_conntrack`, `web_server.py`, `.test_rule_update_created_at_preservation`, `.test_signin_button_direct_click_and_deferred_execution_safety`, `.test_pre_auth_flicker_prevention`, `.test_tcp_udp_protocol_formatting_and_no_both`, `.test_validate_rule_haproxy_requires_ipv6`, `.test_version_detection_with_commit_file_and_fallback`, `.test_system_update_dom_and_ui_wiring`, `.test_validate_rule_port_boundary_conditions`, `.test_security_settings_responsive_layout_and_info_item_wrapping`, `.test_topbar_extended_system_metrics_and_api`, `.test_validate_rule_invalid_characters_rejected`, `.test_get_update_status_parsing_and_ansi_cleaning`, `.test_session_token_header_authentication_flow`, `.test_ovira_login_split_screen_and_controls_integrity`, `.test_static_asset_cache_control_and_versioning`, `restart_services_action`, `.test_dark_theme_tokens_and_restrained_highlights`, `.test_dark_and_light_theme_button_color_harmonization`, `.test_static_assets_integrity`, `.test_get_remote_version_info_rate_limit_fallback`, `.test_rule_category_and_created_at_validation`, `.test_service_restart_api_endpoints`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Should `TestPerformanceAndOptimizations` be split into smaller, more focused modules?**
  _Cohesion score 0.0420899854862119 - nodes in this community are weakly interconnected._
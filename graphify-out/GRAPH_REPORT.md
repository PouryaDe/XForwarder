# Graph Report - Forward-Manager  (2026-11-22)

## Corpus Check
- 107 files · ~151,132 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1730 nodes · 3896 edges · 168 communities (67 shown, 101 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 253 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `88a8a4ab`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- import_config_data
- traffic.py
- DummyHandler
- TestToggleDestinationApi
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
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- system_info.py
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- import_nftables_rules_into_config
- initApp
- classify_status
- engine.py
- rules.js
- XForwarder Operations Runbook
- route_quality.py
- TestI18nAndRTL
- haproxy_parser.py
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TrafficCollector
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- TestTrafficAwareFailover
- escapeHtml
- migrate_and_normalize_config
- prober.py
- TestNginxStreamEngine
- pick_best_now
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- XForwarderEngine
- firewall.py
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- Architectural Solutions Implemented
- ⚡ Core Rules & Constraints
- TestUIAndAPIEdgeCases
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- json
- LossMonitorScheduler
- nftables_parser.py
- TestFastFailoverAndAntiFlap
- .do_POST
- sync_system_rules
- parse_nftables_text
- TestTargetMetricCache
- parse_ping_replies
- measure_packet_loss_50
- metrics.py
- web_server.py
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Architecture & Failover Rules (XForwarder)
- i18n.js
- 5. Verification & Testing
- showToast
- Session State & Task Handoff Rule (XForwarder)
- TestModularSubsystems
- TestPerformanceAndOptimizations
- Architectural Solutions Implemented
- app.js
- stats.js
- 3. Architecture & Solution Implemented
- Experience 003: Native Python Zero-Dependency Web Server
- 5. Verification & Testing
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- system.js
- parse_nftables_counters_json
- Experience 010: Decoupled In-Panel System Updates and Reconnect Flow
- run_scheduled_ping_round
- Intermediate Relay VPS Constraints Rule (XForwarder)
- experience-logging.md
- 2. Mandatory Helper Centralization
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- get_route_interface
- is_interface_up
- TestTrafficSubsystem
- .collect_cycle
- read_haproxy_backend_health
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- parse_proc_net_dev
- Large Files Inspection & Surgical Editing Rule
- Interactive Requirements Clarification (Reverse Prompt Engineering)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 83 edges
2. `TestUIAndAPIEdgeCases` - 60 edges
3. `showToast()` - 49 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 43 edges
6. `decide_route()` - 39 edges
7. `import_config_data()` - 30 edges
8. `t()` - 29 edges
9. `validate_rule()` - 29 edges
10. `TestI18nAndRTL` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `2. Core Dynamics & Low-Resource Relay Safeguards` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `4. Invariants & Rules for AI Agents` --references--> `sync_system_rules()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/engine.py
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py

## Import Cycles
- None detected.

## Communities (168 total, 101 thin omitted)

### Community 0 - "import_config_data"
Cohesion: 0.16
Nodes (3): import_config_data(), TestExportImport, load_config()

### Community 1 - "traffic.py"
Cohesion: 0.19
Nodes (7): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), prune_old_traffic_records(), reset_traffic_counter()

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

### Community 13 - "time"
Cohesion: 0.07
Nodes (9): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), reset_rate_limit(), save_sessions_to_disk(), verify_password() (+1 more)

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.18
Nodes (32): t(), addExcludedTokens(), buildTunnelIfaceMenuHtml(), buildTunnelIfaceTriggerHtml(), closeRuleModal(), currentExcludedTags, currentModalDestinations, ensureNetworkInterfacesLoaded() (+24 more)

### Community 16 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 19 - "system_info.py"
Cohesion: 0.10
Nodes (10): get_network_interfaces_info(), do_ping(), get_services_status(), get_system_stats(), is_ignored_interface(), is_virtual_tunnel_interface(), ping_target(), get_network_interfaces_info() (+2 more)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "import_nftables_rules_into_config"
Cohesion: 0.13
Nodes (8): 3. Implemented Solution & Architecture, backup_legacy_nftables(), deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), discover_all_relay_rules(), import_all_relay_rules_into_config(), import_nftables_rules_into_config(), TestNFTablesParser

### Community 22 - "initApp"
Cohesion: 0.21
Nodes (16): trackFailoverEvents(), addLogEntry(), appendLogEntry(), fallbackCopyLogs(), initLogs(), currentDisruptions, initNetworkQualityMonitor(), loadNetworkQualityMetrics() (+8 more)

### Community 23 - "classify_status"
Cohesion: 0.15
Nodes (3): classify_status(), TestFamilySelection, TestSustainedCriticalClassification

### Community 24 - "engine.py"
Cohesion: 0.08
Nodes (11): check_file(), main(), get_next_number(), main(), slugify(), handle_sig(), _find_conntrack_bin(), apply_haproxy() (+3 more)

### Community 25 - "rules.js"
Cohesion: 0.14
Nodes (25): closeSwitchLogsModal(), copySwitchLogsToClipboard(), fallbackCopy(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave(), handlePathDragOver() (+17 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.22
Nodes (7): Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops), Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "route_quality.py"
Cohesion: 0.11
Nodes (8): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window(), compute_score(), summarize_cycle()

### Community 29 - "haproxy_parser.py"
Cohesion: 0.17
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.18
Nodes (7): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`), 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder)

### Community 33 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.29
Nodes (4): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog

### Community 35 - "escapeHtml"
Cohesion: 0.27
Nodes (20): renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData(), openTrafficModal() (+12 more)

### Community 36 - "migrate_and_normalize_config"
Cohesion: 0.06
Nodes (18): 1. System Model, 2. Non-Negotiable Architectural Invariants, 3. On-Demand Rules, Skills & Tooling, XForwarder Master Architecture Constitution, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents (+10 more)

### Community 37 - "prober.py"
Cohesion: 0.12
Nodes (9): 7. Dual-Feedback L4 Port & Traffic Blackhole Detection, _c_locale_env(), _ip_family_flag(), sanitize_target_host(), check_destination(), is_private_or_tunnel_target(), probe_destination_icmp(), probe_destination_l4_tcp() (+1 more)

### Community 38 - "TestNginxStreamEngine"
Cohesion: 0.08
Nodes (5): 2. Selective Service Reloading, 1. High-Risk Core Components, get_protected_ports(), parse_port_spec(), TestNginxStreamEngine

### Community 40 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 41 - "XForwarderEngine"
Cohesion: 0.08
Nodes (9): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout, Key Decisions & Architectural Changes, sync_system_rules() (+1 more)

### Community 42 - "firewall.py"
Cohesion: 0.17
Nodes (6): apply_nftables(), _format_postrouting_masquerades(), generate_nftables_ruleset(), is_ipv6_supported(), fast_confirm_burst(), fake_apply_nftables()

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

### Community 46 - "⚡ Core Rules & Constraints"
Cohesion: 0.33
Nodes (5): 🔍 Codebase Knowledge Graph (graphify), ⚡ Core Rules & Constraints, 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 48 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 49 - "json"
Cohesion: 0.19
Nodes (12): load_state(), main(), save_state(), show_state(), check_syntax(), get_modified_py_files(), main(), _read_hook_stdin() (+4 more)

### Community 51 - "nftables_parser.py"
Cohesion: 0.14
Nodes (11): 1. Table Isolation in NFTables, get_rule_port_bounds(), ports_overlap(), rules_ports_overlap(), split_port_interval_excluding(), _apply_protected_port_splits(), discover_importable_nftables_rules(), _conflicts_existing_or_discovered() (+3 more)

### Community 54 - ".do_POST"
Cohesion: 0.08
Nodes (19): 1. Server-Side HTTP Performance, 4. Invariants & Rules for AI Agents, _coerce_bool(), export_config_data(), get_config_path(), get_state_file_path(), is_haproxy_listening(), is_nginx_listening() (+11 more)

### Community 55 - "sync_system_rules"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering

### Community 56 - "parse_nftables_text"
Cohesion: 0.11
Nodes (8): _build_xforwarder_range_rule_from_nftables(), _build_xforwarder_rule_from_nftables(), get_live_nftables_rules(), _is_valid_target(), _merge_or_append_rule(), parse_iptables_text(), parse_nftables_json(), parse_nftables_text()

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 63 - "metrics.py"
Cohesion: 0.14
Nodes (8): 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config(), init_metrics_db(), prune_old_metrics(), record_ping_result()

### Community 64 - "web_server.py"
Cohesion: 0.06
Nodes (25): 3. Architecture & Solution Implemented, flush_conntrack(), get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path() (+17 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.29
Nodes (6): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 3. Two-Tier Intelligent Failover & Route Quality Architecture, 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder)

### Community 70 - "i18n.js"
Cohesion: 0.38
Nodes (10): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), toggleLanguage() (+2 more)

### Community 72 - "showToast"
Cohesion: 0.19
Nodes (18): API_BASE, BASE_PATH, fetchApi(), rawCleanPath, VALID_SECTIONS, checkSession(), closeSecurityModal(), evaluatePasswordStrength() (+10 more)

### Community 73 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 78 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 79 - "app.js"
Cohesion: 0.13
Nodes (32): _architecturalCompliance(), initApp(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), stopAuthenticatedSession(), initAmbientEffects(), SPOTLIGHT_SELECTOR (+24 more)

### Community 80 - "stats.js"
Cohesion: 0.13
Nodes (19): fetchStatus(), lastLatestLoss, lastNetwork, lastRuntime, lastTrafficData, setCurrentRules(), setLastLatestLoss(), setLastNetwork() (+11 more)

### Community 81 - "3. Architecture & Solution Implemented"
Cohesion: 0.22
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 85 - "system.js"
Cohesion: 0.42
Nodes (8): closeSystemUpdateModal(), handleServiceRestart(), initServiceRestartControls(), initSystemUpdateManager(), openSystemUpdateModal(), pollDashboardReconnection(), pollUpdateProgress(), startSystemUpdateProcedure()

### Community 89 - "Experience 010: Decoupled In-Panel System Updates and Reconnect Flow"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow

### Community 93 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 94 - "experience-logging.md"
Cohesion: 0.50
Nodes (3): 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 96 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 125 - "Large Files Inspection & Surgical Editing Rule"
Cohesion: 0.40
Nodes (4): 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite), 3. Immediate Syntax Verification, Large Files Inspection & Surgical Editing Rule

### Community 136 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

## Knowledge Gaps
- **101 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `.test_engine_wake_event_sets_and_clears`, `TestXForwarderMigration`, `.test_haproxy_performance_options_rendered`, `engine.py`, `.test_haproxy_single_core_omits_nbthread_and_cpumap`, `.test_haproxy_multicore_renders_both_nbthread_and_cpumap`, `.test_haproxy_syntax_validation_real_error_fails`, `TrafficCollector`, `.test_nginx_stream_sync_firewall_udp_and_proxy_protocol`, `TestTrafficAwareFailover`, `migrate_and_normalize_config`, `TestNginxStreamEngine`, `TestEngineProbes`, `LossMonitorScheduler`, `TestFastFailoverAndAntiFlap`, `TestTargetMetricCache`, `metrics.py`, `web_server.py`, `TestPerformanceAndOptimizations`, `3. Architecture & Solution Implemented`, `.test_haproxy_performance_fallback_on_old_binary`, `get_route_interface`, `is_interface_up`, `.test_nftables_dual_stack_rules_generation`?**
  _High betweenness centrality (0.215) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TrafficCollector`) actually correct?**
  _`XForwarderEngine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `🌐 XForwarder` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Why does `⚡ Core Rules & Constraints` connect `⚡ Core Rules & Constraints` to `import_config_data`, `escapeHtml`, `migrate_and_normalize_config`, `prober.py`, `XForwarderEngine`, `read_haproxy_backend_health`, `app.js`, `LossMonitorScheduler`, `nftables_parser.py`, `import_nftables_rules_into_config`, `rules.js`, `parse_ping_replies`, `metrics.py`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Should `TestXForwarderMigration` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Why does `TestUIAndAPIEdgeCases` connect `TestUIAndAPIEdgeCases` to `.test_services_status_api_and_dom`, `traffic.py`, `.test_ovira_effects_module_and_pointer_safety`, `.test_nftables_destination_must_be_ip_address`, `.test_installer_nginx_ipv6_and_dpkg_recovery_guards`, `.test_rules_view_toggle_and_category_assets`, `.test_drag_and_drop_edge_cases_and_reorder_logic`, `.test_restart_services_action_logic`, `.test_frontend_css_no_hover_motion_transforms`, `.test_tcp_udp_protocol_formatting_and_no_both`, `.test_service_restart_dom_and_ui_wiring`, `.test_overview_relay_engines_alignment_and_responsive`, `.test_validate_rule_arbitrary_priorities`, `.test_topology_and_engines_grid_layout`, `.test_service_restart_edge_cases_and_failures`, `.test_nova_admin_design_system_and_login_cleanup`, `.test_system_version_and_update_apis`, `.test_validate_rule_destination_defaults_port_if_missing`, `.test_copy_port_and_category_json_and_import_modal`, `.test_clean_page_headers_dedicated_updates_and_hashless_routing`, `.test_validate_rule_haproxy_requires_ipv6`, `.test_validate_rule_port_boundary_conditions`, `.test_packet_loss_diagnostic_tool_elements`, `.test_rule_category_and_created_at_validation`, `.test_security_settings_responsive_layout_and_info_item_wrapping`, `.test_isolated_ping_latency_and_packet_loss_badges_and_v1_4_0_standards`, `.test_full_responsive_system_integrity`, `XForwarderEngine`, `firewall.py`, `.test_latency_badge_classification_edge_cases`, `.test_override_endpoint_flushes_conntrack`, `web_server.py`, `.test_system_update_dom_and_ui_wiring`, `.test_validate_rule_invalid_characters_rejected`, `.test_login_form_event_prevention_and_auth_integrity`, `.test_version_detection_with_commit_file_and_fallback`, `.test_switch_logs_modal_and_event_persistence`, `.test_topbar_extended_system_metrics_and_api`, `.test_ssl_web_server_graceful_fallback`, `.test_rule_update_created_at_preservation`, `.test_get_update_status_parsing_and_ansi_cleaning`, `.test_session_token_header_authentication_flow`, `.test_ui_proxy_protocol_and_test_target_dom`, `.test_ovira_login_split_screen_and_controls_integrity`, `.test_static_asset_cache_control_and_versioning`, `.test_signin_button_direct_click_and_deferred_execution_safety`, `.test_dark_theme_tokens_and_restrained_highlights`, `.test_dark_and_light_theme_button_color_harmonization`, `.test_validate_rule_empty_destinations_rejected`, `.test_nftables_dual_stack_rules_generation`, `.test_get_remote_version_info_rate_limit_fallback`, `.test_service_restart_api_endpoints`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Should `decide_route` be split into smaller, more focused modules?**
  _Cohesion score 0.058673469387755105 - nodes in this community are weakly interconnected._
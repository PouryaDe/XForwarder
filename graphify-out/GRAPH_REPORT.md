# Graph Report - Forward-Manager  (2026-11-22)

## Corpus Check
- 108 files · ~155,543 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1761 nodes · 4013 edges · 146 communities (68 shown, 78 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 267 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ef106986`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- import_config_data
- traffic.py
- get_rule_port_bounds
- TestNFTablesParser
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- decide_route
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- sanitize_target_host
- The 8-Point Audit Checklist
- rule_modal.js
- .agents/AGENTS.md
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- get_system_stats
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- nftables_parser.py
- showToast
- classify_status
- os
- rules.js
- XForwarder Operations Runbook
- aggregate_window
- TestI18nAndRTL
- haproxy_parser.py
- Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting
- TrafficCollector
- Python Core Standards (`core/engine.py` & `core/web_server.py`)
- Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring
- TestTrafficAwareFailover
- escapeHtml
- TestToggleDestination
- prober.py
- TestNginxStreamEngine
- TestRouteQualityEngine
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- XForwarderEngine
- config_manager.py
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- XForwarderWebHandler
- quality.js
- TestUIAndAPIEdgeCases
- generate_nftables_ruleset
- json
- LossMonitorScheduler
- nftables_parser.py
- TestFastFailoverAndAntiFlap
- time
- sync_system_rules
- route_quality.py
- TestTargetMetricCache
- parse_ping_replies
- TestMetricsSubsystem
- metrics.py
- web_server.py
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- Architecture & Failover Rules (XForwarder)
- i18n.js
- 5. Verification & Testing
- Architectural Solutions Implemented
- Session State & Task Handoff Rule (XForwarder)
- validate_rule
- TestPerformanceAndOptimizations
- Architectural Solutions Implemented
- 3. Architecture & Solution Implemented
- app.js
- stats.js
- Architecture & Failover Rules (XForwarder)
- Experience 003: Native Python Zero-Dependency Web Server
- re
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- parse_proc_net_dev
- XForwarderWebServer
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- parse_nftables_counters_json
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- 2. Mandatory Helper Centralization
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- split_port_interval_excluding
- is_interface_up
- TestTrafficSubsystem
- _ip_family_flag
- get_route_interface
- is_private_or_tunnel_target
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- Large Files Inspection & Surgical Editing Rule
- Interactive Requirements Clarification (Reverse Prompt Engineering)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 91 edges
2. `TestUIAndAPIEdgeCases` - 60 edges
3. `showToast()` - 49 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 43 edges
6. `decide_route()` - 39 edges
7. `validate_rule()` - 33 edges
8. `import_config_data()` - 30 edges
9. `t()` - 30 edges
10. `TestI18nAndRTL` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py
- `3. Fast IPC Engine Wake-Up` --references--> `notify_engine_wakeup()`  [INFERRED]
  .agents/experiences/008-full-stack-performance-and-fast-ipc.md → core/web_server.py
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `3. Architecture & Solution Implemented` --references--> `get_services_status()`  [INFERRED]
  .agents/experiences/006-host-subsystem-inspection-and-drag-drop-priorities.md → core/system_info.py
- `4. Invariants & Rules for AI Agents` --references--> `hash_password()`  [INFERRED]
  .agents/experiences/005-pbkdf2-salted-auth-and-adaptive-rate-limiting.md → core/auth.py

## Import Cycles
- None detected.

## Communities (146 total, 78 thin omitted)

### Community 0 - "import_config_data"
Cohesion: 0.06
Nodes (23): 1. System Model, 2. Non-Negotiable Architectural Invariants, 3. On-Demand Rules, Skills & Tooling, XForwarder Master Architecture Constitution, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents (+15 more)

### Community 1 - "traffic.py"
Cohesion: 0.17
Nodes (7): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), prune_old_traffic_records(), reset_traffic_counter()

### Community 2 - "get_rule_port_bounds"
Cohesion: 0.16
Nodes (8): get_rule_port_bounds(), rules_ports_overlap(), _apply_protected_port_splits(), discover_importable_nftables_rules(), _conflicts_existing_or_discovered(), find_candidate_nftables_files(), get_live_nftables_rules(), parse_iptables_text()

### Community 3 - "TestNFTablesParser"
Cohesion: 0.16
Nodes (3): deactivate_legacy_rules(), deactivate_legacy_rules_for_ports(), TestNFTablesParser

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

### Community 13 - "sanitize_target_host"
Cohesion: 0.24
Nodes (5): get_unique_targets_from_config(), measure_packet_loss_50(), parse_ping_output(), run_scheduled_ping_round(), sanitize_target_host()

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.18
Nodes (34): t(), addExcludedTokens(), buildDestTypeOptionsHtml(), buildTunnelIfaceMenuHtml(), buildTunnelIfaceTriggerHtml(), closeRuleModal(), currentExcludedTags, currentModalDestinations (+26 more)

### Community 16 - ".agents/AGENTS.md"
Cohesion: 0.20
Nodes (6): 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 19 - "get_system_stats"
Cohesion: 0.13
Nodes (6): get_system_stats(), is_ignored_interface(), is_virtual_tunnel_interface(), get_network_interfaces_info(), _safe_flush_port_conntrack(), TestNetworkInterfaces

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "nftables_parser.py"
Cohesion: 0.15
Nodes (7): _build_xforwarder_range_rule_from_nftables(), _build_xforwarder_rule_from_nftables(), _is_valid_target(), _merge_or_append_rule(), parse_nftables_json(), parse_nftables_text(), _parse_port_tokens()

### Community 22 - "showToast"
Cohesion: 0.14
Nodes (29): API_BASE, BASE_PATH, fetchApi(), rawCleanPath, VALID_SECTIONS, closeSecurityModal(), evaluatePasswordStrength(), handleLogin() (+21 more)

### Community 24 - "os"
Cohesion: 0.07
Nodes (12): check_file(), main(), handle_sig(), apply_nftables(), ensure_dsr_sysctl(), _find_conntrack_bin(), flush_conntrack(), apply_haproxy() (+4 more)

### Community 25 - "rules.js"
Cohesion: 0.14
Nodes (27): closeSwitchLogsModal(), copySwitchLogsToClipboard(), fallbackCopy(), formatDestTypeLabel(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave() (+19 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.22
Nodes (7): Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops), Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "aggregate_window"
Cohesion: 0.12
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window()

### Community 29 - "haproxy_parser.py"
Cohesion: 0.17
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 31 - "TrafficCollector"
Cohesion: 0.10
Nodes (3): classify_tunnel_type(), read_haproxy_port_stats(), TrafficCollector

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.18
Nodes (7): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 35 - "escapeHtml"
Cohesion: 0.25
Nodes (21): deleteRule(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData() (+13 more)

### Community 37 - "prober.py"
Cohesion: 0.13
Nodes (9): is_nftables_type(), is_ipv6_supported(), _c_locale_env(), check_destination(), fast_confirm_burst(), is_nftables_type(), probe_destination_icmp(), probe_destination_l4_tcp() (+1 more)

### Community 38 - "TestNginxStreamEngine"
Cohesion: 0.07
Nodes (11): 2. Selective Service Reloading, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup, 3. Two-Tier Intelligent Failover & Route Quality Architecture (+3 more)

### Community 40 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 42 - "config_manager.py"
Cohesion: 0.11
Nodes (10): export_config_data(), get_config_path(), get_state_file_path(), is_haproxy_listening(), is_nginx_listening(), is_port_in_use_by_external_service(), load_config(), ports_overlap() (+2 more)

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - "XForwarderWebHandler"
Cohesion: 0.10
Nodes (8): 1. Server-Side HTTP Performance, 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, XForwarderWebHandler, TestToggleDestinationApi

### Community 46 - "quality.js"
Cohesion: 0.22
Nodes (13): trackFailoverEvents(), addLogEntry(), appendLogEntry(), fallbackCopyLogs(), initLogs(), currentDisruptions, initDiagPacketLossTool(), initNetworkQualityMonitor() (+5 more)

### Community 48 - "generate_nftables_ruleset"
Cohesion: 0.16
Nodes (7): _format_postrouting_masquerades(), generate_nftables_ruleset(), fake_apply_nft(), fake_apply_nft(), fake_apply_nft(), fake_apply_nft(), fake_apply_nftables()

### Community 49 - "json"
Cohesion: 0.18
Nodes (12): load_state(), main(), save_state(), show_state(), check_syntax(), get_modified_py_files(), main(), _read_hook_stdin() (+4 more)

### Community 51 - "nftables_parser.py"
Cohesion: 0.16
Nodes (6): 3. Implemented Solution & Architecture, get_protected_ports(), backup_legacy_nftables(), discover_all_relay_rules(), import_all_relay_rules_into_config(), import_nftables_rules_into_config()

### Community 54 - "time"
Cohesion: 0.07
Nodes (14): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), reset_rate_limit(), save_sessions_to_disk(), verify_password() (+6 more)

### Community 55 - "sync_system_rules"
Cohesion: 0.25
Nodes (7): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, sync_system_rules()

### Community 56 - "route_quality.py"
Cohesion: 0.27
Nodes (3): compute_score(), pick_best_now(), summarize_cycle()

### Community 59 - "parse_ping_replies"
Cohesion: 0.20
Nodes (4): parse_ping_replies(), _iputils_output(), TestEngineIcmpProbe, TestPerReplyParsing

### Community 63 - "metrics.py"
Cohesion: 0.12
Nodes (7): load_state(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), init_metrics_db(), record_ping_result(), get_installed_version()

### Community 64 - "web_server.py"
Cohesion: 0.07
Nodes (23): 3. Architecture & Solution Implemented, get_full_version_status(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+15 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.17
Nodes (8): 🔍 Codebase Knowledge Graph (graphify), ⚡ Core Rules & Constraints, 🧭 Project Architecture, 7. Dual-Feedback L4 Port & Traffic Blackhole Detection, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide, parse_haproxy_backend_csv(), read_haproxy_backend_health()

### Community 70 - "i18n.js"
Cohesion: 0.38
Nodes (10): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), toggleLanguage() (+2 more)

### Community 72 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

### Community 73 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 77 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 78 - "3. Architecture & Solution Implemented"
Cohesion: 0.28
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 007: Fix HAProxy Silent Drop and State Wipeout

### Community 79 - "app.js"
Cohesion: 0.14
Nodes (31): _architecturalCompliance(), initApp(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), stopAuthenticatedSession(), checkSession(), showDashboard() (+23 more)

### Community 80 - "stats.js"
Cohesion: 0.13
Nodes (19): fetchStatus(), lastLatestLoss, lastNetwork, lastRuntime, lastTrafficData, setCurrentRules(), setLastLatestLoss(), setLastNetwork() (+11 more)

### Community 81 - "Architecture & Failover Rules (XForwarder)"
Cohesion: 0.18
Nodes (7): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, Architecture & Failover Rules (XForwarder), prune_old_metrics()

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 83 - "re"
Cohesion: 0.33
Nodes (3): get_next_number(), main(), slugify()

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 90 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 94 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 96 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 99 - "split_port_interval_excluding"
Cohesion: 0.40
Nodes (3): 1. Table Isolation in NFTables, split_port_interval_excluding(), _invert_excluded_ports_to_ranges()

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
- **78 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `⚡ Core Rules & Constraints` connect `Architecture & Failover Rules (XForwarder)` to `import_config_data`, `get_rule_port_bounds`, `split_port_interval_excluding`, `escapeHtml`, `prober.py`, `sanitize_target_host`, `LossMonitorScheduler`, `nftables_parser.py`, `showToast`, `sync_system_rules`, `os`, `rules.js`, `parse_ping_replies`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TestEngineProbes`) actually correct?**
  _`XForwarderEngine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `import_config_data` be split into smaller, more focused modules?**
  _Cohesion score 0.05939716312056738 - nodes in this community are weakly interconnected._
- **Why does `XForwarderEngine` connect `XForwarderEngine` to `TestXForwarderMigration`, `os`, `TestTrafficAwareFailover`, `TestToggleDestination`, `prober.py`, `TestNginxStreamEngine`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `generate_nftables_ruleset`, `TestFastFailoverAndAntiFlap`, `sync_system_rules`, `TestTargetMetricCache`, `TestMetricsSubsystem`, `web_server.py`, `validate_rule`, `TestPerformanceAndOptimizations`, `3. Architecture & Solution Implemented`, `is_interface_up`, `get_route_interface`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Should `🌐 XForwarder` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Why does `decide_route()` connect `decide_route` to `web_server.py`, `5. Verification & Testing`, `.test_relay_failback_to_priority_1_not_blocked_by_relay_warmup`, `5. Verification & Testing`, `TestRouteQualityEngine`, `XForwarderEngine`, `.test_multi_priority_chain_failback`, `os`, `.test_tier1_emergency_failover_bypasses_hold_and_streak`, `route_quality.py`, `aggregate_window`, `.test_tier2_sustained_streak_confirmation`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Should `TestXForwarderMigration` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
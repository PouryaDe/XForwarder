# Graph Report - Forward-Manager  (2026-11-22)

## Corpus Check
- 108 files · ~157,644 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .css 7, .service 4, (none) 2)

## Summary
- 1776 nodes · 4044 edges · 143 communities (66 shown, 77 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 273 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3c552eca`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestMetricsSubsystem
- traffic.py
- nftables_parser.py
- TestNFTablesParser
- mock_check
- 🌐 XForwarder
- xforwarder.sh
- Workflow: Deploy & Update Services
- TestXForwarderMigration
- TestRouteQualityEngine
- Mandatory Task Completion & Verification Workflow (XForwarder)
- Workflow: Add Port Rule
- Workflow: Diagnose Failover & Forwarding
- classify_status
- The 8-Point Audit Checklist
- rule_modal.js
- .agents/AGENTS.md
- Systematic Debugging Skill (XForwarder)
- UI Design & Universal Consistency Standards (`web/`)
- parse_haproxy_stats_csv
- Web Dashboard & Security Standards (`web/` & `core/web_server.py`)
- parse_nftables_text
- showToast
- Intermediate Relay VPS Constraints Rule (XForwarder)
- engine.py
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
- config_manager.py
- TestNginxStreamEngine
- route_quality.py
- Experience 001: Zero-Collision HAProxy and NFTables Failover
- XForwarderEngine
- engine.py
- Experience 002: Atomic File Persistence and Tmp Renaming
- TestEngineProbes
- .do_POST
- quality.js
- TestUIAndAPIEdgeCases
- generate_nftables_ruleset
- json
- parse_proc_net_dev
- nftables_parser.py
- TestFastFailoverAndAntiFlap
- web_server.py
- sync_system_rules
- parse_nftables_counters_json
- TestTargetMetricCache
- parse_ping_replies
- Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup
- metrics.py
- web_server.py
- Networking & Kernel Standards (XForwarder)
- Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine
- XForwarder - Agent Development Guide
- i18n.js
- 5. Verification & Testing
- Architectural Solutions Implemented
- Session State & Task Handoff Rule (XForwarder)
- TestXForwarderSecurity
- TestPerformanceAndOptimizations
- Architectural Solutions Implemented
- 2. Mandatory Helper Centralization
- app.js
- stats.js
- Interactive Requirements Clarification (Reverse Prompt Engineering)
- Experience 003: Native Python Zero-Dependency Web Server
- os
- Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization
- parse_haproxy_backend_csv
- Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction
- Bash CLI & Deployment Standards (`xforwarder.sh`)
- Experience 017: Resilient Failover and Non-Disruptive Failback
- 5. Verification & Testing
- ._hot_toggle_rule_priority
- TestTrafficSubsystem
- Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover
- Experience 004: Backward Compatibility and Automated Schema Migrations
- restart_services_action
- Backward Compatibility & Automated Schema Migration Rule (XForwarder)

## God Nodes (most connected - your core abstractions)
1. `XForwarderEngine` - 91 edges
2. `TestUIAndAPIEdgeCases` - 60 edges
3. `showToast()` - 49 edges
4. `TestRouteQualityEngine` - 43 edges
5. `escapeHtml()` - 43 edges
6. `decide_route()` - 39 edges
7. `validate_rule()` - 35 edges
8. `import_config_data()` - 30 edges
9. `t()` - 30 edges
10. `TrafficCollector` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Key Decisions & Architectural Changes` --references--> `TrafficCollector`  [INFERRED]
  .agents/experiences/014-per-port-and-per-tunnel-traffic-accounting-and-delta-engine.md → core/traffic.py
- `2. Non-Negotiable Architectural Invariants` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/AGENTS.md → core/config_manager.py
- `3. Architecture & Solution Implemented` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `4. Invariants & Rules for AI Agents` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/004-backward-compatibility-and-schema-migrations.md → core/config_manager.py
- `Key Invariants & Lessons` --references--> `migrate_and_normalize_config()`  [INFERRED]
  .agents/experiences/009-fast-failover-multi-metric-and-anti-flapping.md → core/config_manager.py

## Import Cycles
- None detected.

## Communities (143 total, 77 thin omitted)

### Community 1 - "traffic.py"
Cohesion: 0.19
Nodes (7): get_traffic_db_path(), get_traffic_resets(), get_traffic_summary(), get_traffic_timeseries(), init_traffic_db(), prune_old_traffic_records(), reset_traffic_counter()

### Community 2 - "nftables_parser.py"
Cohesion: 0.10
Nodes (12): 1. Table Isolation in NFTables, rules_ports_overlap(), split_port_interval_excluding(), _apply_protected_port_splits(), deactivate_legacy_rules_for_ports(), discover_importable_nftables_rules(), _conflicts_existing_or_discovered(), find_candidate_nftables_files() (+4 more)

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

### Community 13 - "classify_status"
Cohesion: 0.15
Nodes (3): classify_status(), TestFamilySelection, TestSustainedCriticalClassification

### Community 14 - "The 8-Point Audit Checklist"
Cohesion: 0.18
Nodes (10): 1. Zero-Collision Forwarding Invariant (CRITICAL), 2. Native Standard Library Only (CRITICAL), 3. Atomic File Persistence (CRITICAL), 4. Non-Blocking Probing & Socket Safety (CRITICAL), 5. NFTables Table Isolation (CRITICAL), 6. HAProxy Graceful Reloading, 7. Authentication & API Security, 8. Pure Vanilla Frontend (+2 more)

### Community 15 - "rule_modal.js"
Cohesion: 0.18
Nodes (34): t(), addExcludedTokens(), buildDestTypeOptionsHtml(), buildTunnelIfaceMenuHtml(), buildTunnelIfaceTriggerHtml(), closeRuleModal(), currentExcludedTags, currentModalDestinations (+26 more)

### Community 16 - ".agents/AGENTS.md"
Cohesion: 0.14
Nodes (10): 1. System Model, 2. Non-Negotiable Architectural Invariants, 3. On-Demand Rules, Skills & Tooling, XForwarder Master Architecture Constitution, 2. Constitution Check Gate, Pre-Execution Blast Radius & Impact Analysis Rule (XForwarder), 1. Targeted Inspection (Knowledge Graph First), 2. Surgical Edits (Zero Full-File Overwrite) (+2 more)

### Community 17 - "Systematic Debugging Skill (XForwarder)"
Cohesion: 0.33
Nodes (5): Phase 1: Evidence Gathering & Observation, Phase 2: Path Isolation & Testing, Phase 3: Root Cause Analysis, Phase 4: Fix, Verification & Experience Logging, Systematic Debugging Skill (XForwarder)

### Community 18 - "UI Design & Universal Consistency Standards (`web/`)"
Cohesion: 0.17
Nodes (11): 1. Prime Directive: Universal Visual Consistency, 2. Dual-Theme Design System (Dark & Light Mode), 3. Brand Identity & Iconography Across Screens, 4. Universal Theme Switcher Availability, 5. Typography Standards, 6. Components & Form Controls, 7. Strict Vanilla Technology Stack, 8. Rule Matrix & Card Layout Architecture (+3 more)

### Community 20 - "Web Dashboard & Security Standards (`web/` & `core/web_server.py`)"
Cohesion: 0.40
Nodes (4): 1. Frontend Technology Stack, 2. Aesthetics & Design Guidelines, 3. Authentication & Security Model, Web Dashboard & Security Standards (`web/` & `core/web_server.py`)

### Community 21 - "parse_nftables_text"
Cohesion: 0.13
Nodes (10): _build_xforwarder_range_rule_from_nftables(), _build_xforwarder_rule_from_nftables(), _expand_map_entries(), _extract_json_map_entries(), _is_valid_target(), _merge_or_append_rule(), _parse_map_element_chunk(), parse_nftables_json() (+2 more)

### Community 22 - "showToast"
Cohesion: 0.14
Nodes (29): API_BASE, BASE_PATH, fetchApi(), rawCleanPath, VALID_SECTIONS, closeSecurityModal(), evaluatePasswordStrength(), handleLogin() (+21 more)

### Community 23 - "Intermediate Relay VPS Constraints Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Strict Resource Ceilings, 2. Non-Blocking Probing & Socket Safety, 3. Kernel Isolation, Intermediate Relay VPS Constraints Rule (XForwarder)

### Community 24 - "engine.py"
Cohesion: 0.11
Nodes (4): get_state_file_path(), load_state(), update_state_rules(), handle_sig()

### Community 25 - "rules.js"
Cohesion: 0.14
Nodes (27): closeSwitchLogsModal(), copySwitchLogsToClipboard(), fallbackCopy(), formatDestTypeLabel(), getPrioTagClass(), handleOverrideChange(), handlePathDragEnd(), handlePathDragLeave() (+19 more)

### Community 26 - "XForwarder Operations Runbook"
Cohesion: 0.22
Nodes (7): Quick CLI Command Reference, XForwarder Operations Runbook (Legacy Alias: fwdman-ops), Configuration Schema (`/etc/xforwarder/config.json`), Health Check Simulation, Quick CLI Command Reference, XForwarder Operations Runbook, Zero-Collision Invariant Checks

### Community 27 - "aggregate_window"
Cohesion: 0.15
Nodes (7): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 016: Fix Window Expiration Loop and Switch Decision Logging, aggregate_window()

### Community 29 - "haproxy_parser.py"
Cohesion: 0.18
Nodes (7): _build_xforwarder_rule(), discover_importable_rules(), find_candidate_haproxy_files(), import_haproxy_rules_into_config(), parse_haproxy_content(), parse_haproxy_file(), TestHAProxyParser

### Community 30 - "Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 005: PBKDF2 Salted Auth and Adaptive Rate Limiting

### Community 32 - "Python Core Standards (`core/engine.py` & `core/web_server.py`)"
Cohesion: 0.33
Nodes (5): 1. Native Python 3 Standard Library Only, 2. Thread Safety & Atomic File Operations, 3. Network Probing Standards, 4. Signal & Process Lifecycle, Python Core Standards (`core/engine.py` & `core/web_server.py`)

### Community 33 - "Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring"
Cohesion: 0.18
Nodes (7): Context & Motivation, Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring, Verification & Impact, XForwarder Architectural Experiences Catalog, 1. When to Log an Experience, 2. Standard Logging Protocol, Architectural Experience Logging Rule (XForwarder)

### Community 35 - "escapeHtml"
Cohesion: 0.25
Nodes (21): deleteRule(), renderNetworkTopology(), closeTrafficModal(), handleTrafficEntityChange(), handleTrafficPeriodChange(), initTrafficAnalytics(), loadOverviewTrafficChart(), loadTrafficModalData() (+13 more)

### Community 37 - "config_manager.py"
Cohesion: 0.08
Nodes (16): 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`), Required Normalization Rules:, _coerce_bool(), is_nftables_type(), is_valid_target(), migrate_and_normalize_config(), parse_excluded_ports(), parse_port_spec() (+8 more)

### Community 38 - "TestNginxStreamEngine"
Cohesion: 0.10
Nodes (4): 2. Selective Service Reloading, 1. High-Risk Core Components, get_rule_port_bounds(), TestNginxStreamEngine

### Community 39 - "route_quality.py"
Cohesion: 0.11
Nodes (3): compute_score(), pick_best_now(), summarize_cycle()

### Community 40 - "Experience 001: Zero-Collision HAProxy and NFTables Failover"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 001: Zero-Collision HAProxy and NFTables Failover

### Community 42 - "engine.py"
Cohesion: 0.08
Nodes (11): 3. Architecture & Solution Implemented, apply_nftables(), ensure_dsr_sysctl(), _find_conntrack_bin(), flush_conntrack(), is_ipv6_supported(), apply_haproxy(), apply_nginx() (+3 more)

### Community 43 - "Experience 002: Atomic File Persistence and Tmp Renaming"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 002: Atomic File Persistence and Tmp Renaming

### Community 45 - ".do_POST"
Cohesion: 0.06
Nodes (13): 1. Server-Side HTTP Performance, 4. Invariants & Rules for AI Agents, get_config_path(), import_config_data(), load_config(), save_config(), notify_engine_wakeup(), sync_rules_and_notify() (+5 more)

### Community 46 - "quality.js"
Cohesion: 0.22
Nodes (13): trackFailoverEvents(), addLogEntry(), appendLogEntry(), fallbackCopyLogs(), initLogs(), currentDisruptions, initDiagPacketLossTool(), initNetworkQualityMonitor() (+5 more)

### Community 48 - "generate_nftables_ruleset"
Cohesion: 0.16
Nodes (7): _format_postrouting_masquerades(), generate_nftables_ruleset(), TestNFTablesDSRMethods, fake_apply_nft(), fake_apply_nft(), fake_apply_nft(), fake_apply_nft()

### Community 49 - "json"
Cohesion: 0.11
Nodes (13): check_syntax(), get_modified_py_files(), main(), _read_hook_stdin(), main(), run_step(), show_git_status(), validate_json_files() (+5 more)

### Community 51 - "nftables_parser.py"
Cohesion: 0.16
Nodes (6): 3. Implemented Solution & Architecture, get_protected_ports(), backup_legacy_nftables(), discover_all_relay_rules(), import_all_relay_rules_into_config(), import_nftables_rules_into_config()

### Community 54 - "web_server.py"
Cohesion: 0.07
Nodes (21): check_rate_limit(), get_sessions_file_path(), hash_password(), load_sessions_from_disk(), record_failed_login(), save_sessions_to_disk(), verify_password(), export_config_data() (+13 more)

### Community 55 - "sync_system_rules"
Cohesion: 0.13
Nodes (13): 1. Context & Motivation, 2. Core Dynamics & Low-Resource Relay Safeguards, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering, 1. Context & Motivation, 2. Root Cause / Core Dynamics (+5 more)

### Community 59 - "parse_ping_replies"
Cohesion: 0.13
Nodes (10): 1. System Overview, 2. Zero-Collision Rule (Mandatory), 3. Two-Tier Intelligent Failover & Route Quality Architecture, 4. State & Configuration Persistence, 5. Strict Interface & Route Isolation for Destination Probes, Architecture & Failover Rules (XForwarder), parse_ping_replies(), _iputils_output() (+2 more)

### Community 60 - "Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 018: Post-Sync UDP Conntrack Flushing and Boundary Cleanup

### Community 63 - "metrics.py"
Cohesion: 0.09
Nodes (17): ⚡ Core Rules & Constraints, 6. Long-Term Packet Loss Monitoring & Deduplicated Probing, 7. Dual-Feedback L4 Port & Traffic Blackhole Detection, _c_locale_env(), get_latest_metrics_per_target(), get_metrics_db_path(), get_metrics_history(), get_unique_targets_from_config() (+9 more)

### Community 64 - "web_server.py"
Cohesion: 0.08
Nodes (18): get_full_version_status(), get_installed_version(), get_local_version_info(), get_remote_version_info(), get_script_path(), get_update_log_path(), get_update_state_file_path(), get_update_status() (+10 more)

### Community 65 - "Networking & Kernel Standards (XForwarder)"
Cohesion: 0.33
Nodes (5): 2. HAProxy Zero-Tunnel Relay, 3. Kernel Forwarding Requirements, 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`), 5. Golden NIC Offload Profile (`tso on gso on gro off`), Networking & Kernel Standards (XForwarder)

### Community 66 - "Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine"
Cohesion: 0.40
Nodes (4): Context & Motivation, Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine, Key Decisions & Architectural Changes, Verification & Impact

### Community 68 - "XForwarder - Agent Development Guide"
Cohesion: 0.40
Nodes (4): 🔍 Codebase Knowledge Graph (graphify), 🧭 Project Architecture, 🛠 Workflows, Skills & Verification Pipeline, XForwarder - Agent Development Guide

### Community 70 - "i18n.js"
Cohesion: 0.38
Nodes (10): applyI18nToDOM(), DEFAULT_LANG, getCurrentLang(), initI18n(), languageChangeListeners, onLanguageChanged(), setLanguage(), toggleLanguage() (+2 more)

### Community 72 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 3. Fast IPC Engine Wake-Up, 4. Client-Side Smoothness, Architectural Solutions Implemented, Context & Motivation, Experience 008: Full-Stack Performance Optimization & Fast IPC, Key Invariants & Lessons, 5. Web UI Real-Time Visibility, computeRulesFingerprint()

### Community 73 - "Session State & Task Handoff Rule (XForwarder)"
Cohesion: 0.50
Nodes (3): 1. Structure & Storage, 2. Managing Session State via CLI, Session State & Task Handoff Rule (XForwarder)

### Community 74 - "TestXForwarderSecurity"
Cohesion: 0.08
Nodes (3): reset_rate_limit(), XForwarderWebServer, TestXForwarderSecurity

### Community 77 - "Architectural Solutions Implemented"
Cohesion: 0.22
Nodes (8): 1. Rapid Failure Detection & Confirmation Burst (<1s), 2. Multi-Metric Composite Quality Scoring, 3. Anti-Flapping Route Damping & 10% Hysteresis, 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle, Architectural Solutions Implemented, Context & Motivation, Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability, Key Invariants & Lessons

### Community 78 - "2. Mandatory Helper Centralization"
Cohesion: 0.50
Nodes (3): 1. Absolute Prohibition of Duplicated Logic, 2. Mandatory Helper Centralization, Clean Code & DRY (Don't Repeat Yourself) Rule

### Community 79 - "app.js"
Cohesion: 0.14
Nodes (31): _architecturalCompliance(), initApp(), pendingOverrides, previousActivePriorities, startAuthenticatedSession(), stopAuthenticatedSession(), checkSession(), showDashboard() (+23 more)

### Community 80 - "stats.js"
Cohesion: 0.13
Nodes (19): fetchStatus(), lastLatestLoss, lastNetwork, lastRuntime, lastTrafficData, setCurrentRules(), setLastLatestLoss(), setLastNetwork() (+11 more)

### Community 81 - "Interactive Requirements Clarification (Reverse Prompt Engineering)"
Cohesion: 0.50
Nodes (3): 1. Zero-Assumption Policy & Triggers, 2. Rules of Engagement, Interactive Requirements Clarification (Reverse Prompt Engineering)

### Community 82 - "Experience 003: Native Python Zero-Dependency Web Server"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 003: Native Python Zero-Dependency Web Server

### Community 83 - "os"
Cohesion: 0.13
Nodes (10): check_file(), main(), get_next_number(), main(), slugify(), load_state(), main(), save_state() (+2 more)

### Community 84 - "Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

### Community 90 - "Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction"
Cohesion: 0.40
Nodes (4): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 4. Key Learnings & Verification, Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

### Community 94 - "Bash CLI & Deployment Standards (`xforwarder.sh`)"
Cohesion: 0.40
Nodes (4): 1. Shell Scripting Conventions, 2. Directory & Path Hierarchy, 3. Service Lifecycle Management, Bash CLI & Deployment Standards (`xforwarder.sh`)

### Community 97 - "Experience 017: Resilient Failover and Non-Disruptive Failback"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 017: Resilient Failover and Non-Disruptive Failback

### Community 109 - "Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover"
Cohesion: 0.33
Nodes (5): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

### Community 116 - "Experience 004: Backward Compatibility and Automated Schema Migrations"
Cohesion: 0.29
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 4. Invariants & Rules for AI Agents, 5. Verification & Testing, Experience 004: Backward Compatibility and Automated Schema Migrations

### Community 120 - "restart_services_action"
Cohesion: 0.15
Nodes (6): 1. Context & Motivation, 2. Root Cause / Core Dynamics, 3. Architecture & Solution Implemented, 5. Verification & Testing, Experience 010: Decoupled In-Panel System Updates and Reconnect Flow, restart_services_action()

### Community 121 - "Backward Compatibility & Automated Schema Migration Rule (XForwarder)"
Cohesion: 0.40
Nodes (4): 1. Prime Directive: Zero Data Loss Across Updates, 2. Mandatory Pre-Update Atomic Backup, 4. Legacy Path & CLI Compatibility, Backward Compatibility & Automated Schema Migration Rule (XForwarder)

## Knowledge Gaps
- **77 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `XForwarderEngine` connect `XForwarderEngine` to `TestMetricsSubsystem`, `TestXForwarderMigration`, `engine.py`, `TrafficCollector`, `TestTrafficAwareFailover`, `TestToggleDestination`, `config_manager.py`, `TestNginxStreamEngine`, `engine.py`, `TestEngineProbes`, `TestUIAndAPIEdgeCases`, `generate_nftables_ruleset`, `json`, `TestFastFailoverAndAntiFlap`, `web_server.py`, `sync_system_rules`, `TestTargetMetricCache`, `metrics.py`, `TestPerformanceAndOptimizations`, `os`, `._hot_toggle_rule_priority`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `XForwarderEngine` (e.g. with `2. Root Cause / Core Dynamics` and `TrafficCollector`) actually correct?**
  _`XForwarderEngine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `TestMetricsSubsystem` be split into smaller, more focused modules?**
  _Cohesion score 0.07575757575757576 - nodes in this community are weakly interconnected._
- **Why does `⚡ Core Rules & Constraints` connect `metrics.py` to `TestMetricsSubsystem`, `nftables_parser.py`, `escapeHtml`, `XForwarder - Agent Development Guide`, `config_manager.py`, `engine.py`, `.do_POST`, `nftables_parser.py`, `os`, `showToast`, `sync_system_rules`, `rules.js`, `parse_ping_replies`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Should `nftables_parser.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10098522167487685 - nodes in this community are weakly interconnected._
- **Why does `migrate_and_normalize_config()` connect `config_manager.py` to `TestToggleDestination`, `TestNginxStreamEngine`, `.do_POST`, `Architectural Solutions Implemented`, `.agents/AGENTS.md`, `generate_nftables_ruleset`, `Experience 004: Backward Compatibility and Automated Schema Migrations`, `web_server.py`, `engine.py`, `metrics.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Should `🌐 XForwarder` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
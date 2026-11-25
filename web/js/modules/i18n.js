// ============================================================================
// XForwarder - Internationalization (i18n) Module
// Native ES Module providing English & Persian (Farsi) with RTL Support
// ============================================================================

export const TRANSLATIONS = {
    en: {
        // App & Brand
        "brand.title": "XForwarder",
        "brand.shield": "SHIELD",
        "brand.subtitle": "Multi-Path Priority Relay & Failover Engine",

        // Login Screen
        "login.title": "XForwarder",
        "login.subtitle": "Multi-Path Priority Relay & Failover Engine",
        "login.lockout_title": "Security Lockout Active",
        "login.lockout_desc": "Too many failed login attempts.",
        "login.username": "Username",
        "login.username_placeholder": "admin",
        "login.password": "Password",
        "login.password_placeholder": "••••••••",
        "login.caps_lock": "Caps Lock is ON",
        "login.submit": "Sign In to Dashboard",
        "login.submitting": "Signing In...",
        "login.failed": "Invalid username or password",
        "login.theme": "Theme",
        "login.lang": "فارسی",
        "login.art_badge": "MULTI-PATH FAILOVER ENGINE",
        "login.art_pitch": "Every port, tunnel and failover in one place.",

        // Navigation & Sidebar
        "nav.main": "MAIN NAVIGATION",
        "nav.rules": "Ports",
        "nav.overview": "Overview",
        "nav.traffic": "Network",
        "nav.services": "Services",
        "nav.updates": "Updates",
        "nav.security": "Security",
        "nav.logs": "Logs",
        "user.admin": "Administrator",
        "user.role": "Administrator",

        // Network Quality & Diagnostics Section
        "traffic_section.title": "Network",
        "traffic_section.sub": "30-day packet loss timeline, live probe diagnostics, and route quality.",

        // Service Warning Banner
        "services_warning.title": "Core Relay Packages Missing",
        "services_warning.desc": "One or more core forwarding services are not installed on this server.",
        "services_warning.dismiss": "Dismiss",

        // Section 1: Port Rules
        "rules.title": "Port Routing & Multi-Path Matrix",
        "rules.desc": "Each port routes user traffic through Priority 1 and automatically cascades to backup priorities on packet loss.",
        "rules.export": "Export",
        "rules.import": "Import",
        "rules.traffic": "Traffic",
        "rules.switch_logs": "Switch Logs",
        "rules.add_rule": "Add Port Rule",
        "rules.search_placeholder": "Search ports, IPs, categories, or comments...",
        "rules.sort_port_asc": "Port: Low to High",
        "rules.sort_port_desc": "Port: High to Low",
        "rules.sort_date_desc": "Newest First",
        "rules.sort_date_asc": "Oldest First",
        "rules.sort_status": "Health Status",
        "rules.sort_category": "Category (A–Z)",
        "rules.view_cards": "Cards",
        "rules.view_list": "List",
        "rules.auto_failover": "Auto Failover",
        "rules.force_prio": "Force #{prio}",
        "rules.primary": "Primary",
        "rules.backup": "Backup",
        "rules.active": "Active",
        "rules.hold": "Hold {sec}s",
        "rules.switch_in": "Switch in {sec}s",
        "rules.relay": "Relay",
        "rules.test": "Test",
        "rules.copy_json": "Copy Rule JSON",
        "rules.copy_all_json": "Copy All JSON",
        "rules.empty_title": "No forwarding rules found",
        "rules.empty_desc": "Click 'Add Port Rule' to create your first relay",
        "rules.last_switch": "Last switch:",
        "rules.import_banner_title": "Pre-existing Relay Rules Detected",
        "rules.import_banner_desc": "Discovered existing port forwarding rules on this server.",
        "rules.import_all": "Import All Rules",
        "rules.dismiss": "Dismiss",
        "rules.uncategorized": "Uncategorized",
        "rules.forced": "Forced",
        "rules.ports_count": "{count} Ports",
        "rules.copy_category_json": "Copy Category JSON",
        "rules.copy_category_json_tooltip": "Copies all '{cat}' ports as JSON",
        "rules.toggle_cat_hide": "Hide category ports",
        "rules.toggle_cat_show": "Show category ports",
        "rules.delete_category_tooltip": "Delete all ports in '{cat}'",
        "confirm.delete_category_title": "Delete Category Ports?",
        "confirm.delete_category_msg": "Delete all {count} ports in '{cat}'? Forwarding on these ports will stop immediately.",
        "confirm.delete_category_btn": "Delete All",
        "rules.forwarding_label": "Forwarding:",
        "rules.copy_port_num": "Copy Port Number",
        "rules.copy_dest_ip": "Copy Destination IP",
        "rules.edit_rule": "Edit Rule",
        "rules.delete_rule": "Delete Rule",
        "rules.switch_logs_tooltip": "Switch Decision Logs & History",
        "rules.traffic_analytics_tooltip": "Traffic & Bandwidth Analytics",
        "rules.copy_rule_json": "Copy Port Configuration (JSON)",
        "rules.priority_on_tooltip": "Priority #{prio} is ON (Click to turn OFF)",
        "rules.priority_off_tooltip": "Priority #{prio} is OFF (Click to turn ON)",
        "rules.relay_tooltip": "Mid Server: The engine anchors on Priority 1 and only fails over here on outage, packet loss, or latency > 150ms.",
        "rules.switch_pending_tooltip": "Candidate P{prio} sustained quality advantage. Switching after streak confirmation.",
        "rules.min_hold_tooltip": "Route held stable to prevent disruption (Min Hold: 10m)",
        "rules.cooldown_tooltip": "Post-Critical Cooldown active",
        "rules.flapping_tooltip": "Repeated route flapping detected. Cooldown extended.",
        "rules.flap_guard": "Flap Guard",
        "rules.traffic_cycle_tooltip": "Billing Cycle Traffic: ↑ {tx} · ↓ {rx} (Click for details & reset)",
        "rules.lb_badge": "LB",
        "rules.lb_pool_up": "{healthy}/{total} UP",
        "rules.lb_pool_tooltip": "Load-Balanced Pool ({algo}) · {healthy}/{total} healthy nodes actively receiving traffic. Down nodes are excluded automatically.",
        "rules.lb_show_more": "+{count} more",
        "rules.lb_show_less": "Show less",
        "rules.lb_ip_family_warn": "NFTables LB pool cannot mix IPv4 and IPv6 addresses",

        // Section 2: Overview
        "overview.title": "Overview",
        "overview.desc": "Live server telemetry, daily bandwidth accounting, tunnel topology, and 30-day packet loss analytics.",
        "overview.cpu": "CPU & Load",
        "overview.cpu_load": "Processor Load",
        "overview.memory": "Memory",
        "overview.active_sockets": "Active Sockets",
        "overview.live_bandwidth": "Live Bandwidth",
        "overview.traffic_sub": "Real-time throughput · Click to toggle",
        "overview.stat_forwarded": "Forwarded Ports",
        "overview.stat_forwarded_sub": "Active Inbound Mappings",
        "overview.stat_proxy": "Active Proxy (L4)",
        "overview.stat_proxy_sub": "Layer-4 Direct Relay",
        "overview.stat_nftables": "Active NFTables (L3)",
        "overview.stat_nftables_sub": "Kernel Tunnel Routing",
        "overview.stat_quality": "Network Quality (24h)",
        "overview.stat_quality_sub": "0% Loss · 15m Engine",
        "overview.daily_traffic_title": "Daily Traffic & Bandwidth Usage",
        "overview.daily_traffic_sub": "Hourly traffic accounting across all forwarded ports and kernel tunnels · SQLite WAL",
        "overview.past_24h": "Past 24 Hours",
        "overview.24h": "24 Hours",
        "overview.7d": "7 Days",
        "overview.30d": "30 Days",
        "overview.full_analytics": "Full Analytics",
        "overview.traffic_total": "24h Total Traffic",
        "overview.traffic_total_sub": "All active ports & tunnels",
        "overview.download_rx": "Download (RX)",
        "overview.download_rx_sub": "Client inbound stream",
        "overview.upload_tx": "Upload (TX)",
        "overview.upload_tx_sub": "Exit server response stream",
        "overview.peak_hourly": "Peak Hourly Usage",
        "overview.peak_hourly_sub": "Peak throughput window",
        "overview.chart_title": "Hourly Bandwidth Distribution (Past 24 Hours)",
        "overview.legend_tx": "Upload (TX)",
        "overview.legend_rx": "Download (RX)",
        "overview.ticks_24h": "24h ago",
        "overview.ticks_18h": "18h ago",
        "overview.ticks_12h": "12h ago",
        "overview.ticks_6h": "6h ago",
        "overview.ticks_now": "Now",
        "overview.net_title": "Server Network & Tunnel Topology",
        "overview.net_sub": "Server WAN public addresses, active tunnel interfaces, and latency",
        "overview.server_ips": "Server Host IP(s):",
        "overview.tunnels_count": "{count} Tunnels",
        "overview.detecting": "Detecting...",
        "overview.engines_title": "Relay Engines",
        "overview.engines_sub": "Kernel NAT & user-space stream proxies",
        "overview.all_active": "ALL ACTIVE",
        "overview.nft_name": "NFTables DNAT",
        "overview.nft_desc": "Kernel Layer-3 Tunnel Forwarding",
        "overview.haproxy_name": "HAProxy Relay",
        "overview.haproxy_desc": "Layer-4 Direct TCP/UDP Stream",
        "overview.nginx_name": "Nginx Stream",
        "overview.nginx_desc": "High-Concurrency TCP/UDP Proxy",
        "overview.zero_collision": "Zero-Collision Isolation Active",
        "overview.quality_title": "Network Quality & Packet Loss Timeline",
        "overview.quality_sub": "Automated 15-minute 50-probe test (ping [ip] -c 50 -i 0.2) · 30-Day Retention",
        "overview.target_ip": "Target IP:",
        "overview.all_targets": "All Tracked Targets",
        "overview.run_round": "Run Round",
        "overview.quality_label": "Network Quality",
        "overview.avg_latency": "Average Latency",
        "overview.avg_loss": "Avg / Peak Loss",
        "overview.disruptions": "Disruption Incidents",
        "overview.timeline_title": "Network Health Timeline",
        "overview.clean": "Clean (0% Loss)",
        "overview.degraded": "Degraded (1-20%)",
        "overview.disrupted": "Disrupted (>20%)",
        "overview.disruptions_log": "Network Disruption Incidents Log",
        "overview.disruptions_sub": "Timestamps where packet loss > 0% or connection failures occurred",
        "overview.col_time": "Timestamp",
        "overview.col_target": "Target Host",
        "overview.col_loss": "Packet Loss",
        "overview.col_latency": "Round-Trip Latency",
        "overview.col_probes": "Probes",
        "overview.col_status": "Severity / Status",
        "overview.prev": "Prev",
        "overview.next": "Next",

        // Section 3: Relay Services
        "services.title": "Relay Services & Forwarding Engines",
        "services.desc": "Manage, reload, and re-synchronize active proxy engines and kernel packet tables.",
        "services.restart_engine": "Restart Engine",
        "services.restart_all": "Restart All Services",
        "services.haproxy_title": "HAProxy Zero-Tunnel Engine",
        "services.haproxy_sub": "User-space Layer-4 TCP/UDP IPv6 Relay",
        "services.haproxy_desc": "Direct IPv6 user-space relay without any encapsulation overhead. Non-disruptive reload on priority change.",
        "services.config_location": "Config Location",
        "services.installation": "Installation",
        "services.service_status": "Service Status",
        "services.binary_version": "Binary Version",
        "services.reload_mechanism": "Reload Mechanism",
        "services.active_bindings": "Active Bindings",
        "services.reload_haproxy": "Reload",
        "services.restart_haproxy": "Restart",
        "services.nftables_title": "NFTables Kernel DNAT",
        "services.nftables_sub": "Layer-3 Kernel Tunnel Forwarding",
        "services.nftables_desc": "High-speed kernel DNAT over GRE, IPIP, FakeTCP, or AmneziaWG tunnels. Zero interference with system firewall.",
        "services.isolated_tables": "Isolated Tables",
        "services.kernel_status": "Kernel Status",
        "services.flush_safety": "Flush Safety",
        "services.flush_safety_val": "Never executes flush ruleset",
        "services.sync_nftables": "Sync",
        "services.restart_nftables": "Restart",
        "services.nginx_title": "Nginx Stream Proxy Engine",
        "services.nginx_sub": "Layer-4 High-Throughput Stream Forwarder",
        "services.nginx_desc": "High-concurrency stream TCP/UDP proxy with epoll multi-accept architecture. Managed dynamically by XForwarder.",
        "services.sync_nginx": "Sync",
        "services.nginx_sync_mode_title": "Choose Nginx Sync Direction",
        "services.nginx_sync_mode_msg": "Choose whether to apply XForwarder rules onto Nginx config, or update XForwarder's Nginx priorities from the actual Nginx configuration on the server (if Nginx is empty, Nginx priorities in Ports will be removed).",
        "services.nginx_sync_push_btn": "XForwarder → Nginx",
        "services.nginx_sync_pull_btn": "Nginx → XForwarder",
        "services.reload_nginx": "Reload",
        "services.restart_nginx": "Restart",
        "services.name_all": "All Relay Services & Daemons",
        "services.name_engine": "XForwarder Core Failover Engine",
        "services.name_haproxy": "HAProxy Relay Service",
        "services.name_nginx": "Nginx Stream Proxy",
        "services.name_nftables": "NFTables Table 'xfwd_orchestrator'",
        "services.restarting_toast": "Restarting {service}...",
        "services.reloaded_toast": "{service} reloaded successfully!",
        "services.restarted_toast": "{service} restarted successfully!",
        "services.restart_failed_toast": "Failed to restart {service}: {error}",
        "services.discovery_title": "Pre-existing Relay Rules Discovery",
        "services.discovery_sub": "Auto-discover and import active HAProxy & NFTables rules into XForwarder",
        "services.scan_server": "Scan Server",
        "services.discovery_desc": "If this server was previously configured with HAProxy or active NFTables/iptables DNAT forwarding rules, XForwarder can automatically detect them, extract inbound ports, backends, and protocols, backup legacy tables, and import them with zero port collisions.",
        "services.scan_prompt": "Click \"Scan Server\" to check for unmanaged HAProxy and NFTables forwarding rules.",
        "services.kernel_opt_title": "Kernel & Network Optimizer",
        "services.kernel_opt_sub": "Adaptive BBR, fq qdisc, conntrack scaling, MTU probing & ESP Spoof / DSR safety (rp_filter=0)",
        "services.kernel_opt_refresh": "Refresh",
        "services.kernel_opt_apply": "Optimize Now",
        "services.kernel_opt_applying": "Optimizing...",
        "services.kernel_opt_profile_lbl": "Host Profile",
        "services.kernel_opt_tcp_lbl": "TCP / Qdisc",
        "services.kernel_opt_rp_lbl": "RP Filter (ESP/DSR)",
        "services.kernel_opt_ct_lbl": "Conntrack",
        "services.kernel_opt_reset_title": "Clean & replace previous sysctl settings before applying",
        "services.kernel_opt_reset_desc": "Backs up and clears /etc/sysctl.conf, conflicting /etc/sysctl.d/*.conf files, and duplicate nf_conntrack lines in /etc/modules.",
        "services.kernel_opt_confirm_title": "Apply Kernel & Network Optimization?",
        "services.kernel_opt_confirm_msg": "Applies adaptive BBR, fq qdisc, conntrack scaling, MTU probing, and ESP/DSR-safe rp_filter=0 in /etc/sysctl.d/99-xforwarder.conf without disconnecting active tunnels.",
        "services.kernel_opt_confirm_reset_msg": "Creates a backup in /etc/xforwarder/backups, clears previous /etc/sysctl.conf and conflicting /etc/sysctl.d/*.conf drop-ins, deduplicates /etc/modules, and applies clean ESP/DSR-safe optimization.",
        "services.kernel_opt_conflict_hdr": "Conflicts / legacy kernel settings detected (recommend checking 'Clean & replace' below):",

        "network.spoof_title": "IP Spoof / DSR Capability Tester",
        "network.spoof_sub": "Check if this server & datacenter allow spoofed-source packets for DSR.",
        "network.spoof_listen_title": "Peer Listener (Iran Server)",
        "network.spoof_listen_desc": "Open a temporary UDP port to receive test probes.",
        "network.spoof_listen_start": "Start Listener",
        "network.spoof_listen_stop": "Stop Listener",
        "network.spoof_udp_port": "UDP Port",
        "network.spoof_port_short": "Port",
        "network.spoof_cli_hint": "CLI command (run on Outside VPS):",
        "network.spoof_run_title": "Egress Test (Outside VPS)",
        "network.spoof_run_desc": "Send normal & spoofed probes to your Peer Listener.",
        "network.spoof_peer_ip": "Peer IP",
        "network.spoof_src_ip": "Spoof IP",
        "network.spoof_run_btn": "Run Spoof / DSR Test",
        "network.spoof_running": "Testing...",
        "common.copy": "Copy",

        // Section 4: Security & Access
        "security.title": "Security & Access",
        "security.desc": "Export sanitized configuration backups, import rules, and manage dashboard administrator credentials.",
        "security.backup_title": "Backup & Migration",
        "security.backup_sub": "Export or import routing rules and server parameters",
        "security.backup_desc": "Safely backup or restore your forwarding rules and operational parameters. Exported files are cryptographically sanitized to exclude administrative passwords.",
        "security.export_btn": "Export Backup JSON",
        "security.import_btn": "Import Config",
        "security.admin_title": "Admin Credentials",
        "security.admin_sub": "Change web dashboard administrator username and password",
        "security.current_pwd": "Current Admin Password *",
        "security.current_pwd_placeholder": "Current password",
        "security.new_user": "New Username (optional)",
        "security.new_user_placeholder": "Leave empty to keep current",
        "security.new_pwd": "New Password (optional)",
        "security.new_pwd_placeholder": "Minimum 8 characters",
        "security.confirm_pwd": "Confirm New Password",
        "security.confirm_pwd_placeholder": "Repeat new password",
        "security.update_btn": "Update Credentials",
        "security.panel_title": "Panel Access (Port & Path)",
        "security.panel_sub": "Change web dashboard listening port and secret URL path",
        "security.panel_port": "Panel Port *",
        "security.panel_path": "Secret URL Path",
        "security.panel_path_placeholder": "xfwd-admin (or leave empty for /)",
        "security.panel_save_btn": "Save & Restart Panel",
        "security.updates_title": "System & Software Updates",
        "security.updates_sub": "Check GitHub releases, auto-migrate schema & upgrade services",
        "security.installed_version": "Installed Version",
        "security.local_commit": "Local Git Commit",
        "security.remote_commit": "Latest GitHub Commit",
        "security.last_checked": "Last Checked",
        "security.never": "Never",
        "security.check_updates": "Check for Updates",
        "security.update_latest": "Update to Latest",
        "security.update_note": "Updates automatically backup active configuration (config.json.bak), migrate schema structures, and preserve all custom ports and credentials with zero data loss.",

        // REST API & API Keys
        "api.title": "REST API & API Keys",
        "api.sub": "Create scoped Bearer / X-API-Key tokens for external automation and inspect API docs",
        "api.download_openapi": "OpenAPI JSON",
        "api.view_docs": "API Reference",
        "api.key_name": "Key Name",
        "api.key_name_placeholder": "e.g. WHMCS / Automation Bot",
        "api.scope": "Permission Scope",
        "api.scope_admin": "Admin (Full Access)",
        "api.scope_write": "Write (Rules & Probes)",
        "api.scope_read": "Read-Only",
        "api.expiry": "Expiration",
        "api.exp_never": "Never Expires",
        "api.exp_30": "30 Days",
        "api.exp_90": "90 Days",
        "api.exp_365": "365 Days",
        "api.generate_btn": "Generate API Key",
        "api.reveal_title": "Copy your new API key now — it will not be shown again:",
        "api.copy_key": "Copy Key",
        "api.empty": "No API keys created yet. Generate one above for scripts or external integrations.",
        "api.docs_title": "XForwarder REST API Reference",
        "api.docs_sub": "Supports Bearer Token, X-API-Key, and Session auth across /api/* and /api/v1/*",
        "api.base_url": "Base URL:",
        "api.auth_headers": "Headers:",
        "api.cat_all": "All",
        "api.cat_auth": "Auth & Keys",
        "api.cat_rules": "Rules CRUD",
        "api.cat_failover": "Failover & Probes",
        "api.cat_traffic": "Traffic & Metrics",
        "api.cat_system": "System & Settings",
        "api.never": "Never",
        "api.status_expired": "EXPIRED",
        "api.disable_btn": "Disable",
        "api.enable_btn": "Enable",
        "api.no_expiry": "No expiry",
        "api.last_used": "Last used:",
        "api.expires": "Expires:",
        "api.revoke_btn": "Revoke",
        "api.updated_toast": "API key updated",
        "api.revoke_confirm_title": "Revoke API Key?",
        "api.revoke_confirm_msg": "Revoke API key \"{name}\"? Any integration using it will immediately receive 401 Unauthorized.",
        "api.revoked_toast": "API key revoked",
        "api.name_required": "Please enter an API key name",
        "api.created_toast": "API key generated! Copy it now.",
        "api.copied_secret": "API key copied to clipboard!",
        "api.openapi_downloaded": "OpenAPI 3.0 spec downloaded",

        // Section 5: System Updates
        "updates.title": "System Updates",
        "updates.desc": "Check GitHub releases, automatically migrate schemas, and upgrade relay services.",
        "updates.pipeline_title": "Automated Upgrade Pipeline",
        "updates.pipeline_sub": "Zero-downtime execution sequence",
        "updates.step1_title": "Atomic Configuration Snapshot",
        "updates.step1_desc": "Creates a timestamped backup of active rules and auth before pulling code.",
        "updates.step2_title": "Idempotent Schema Migration",
        "updates.step2_desc": "Normalizes config structures while preserving custom ports and credentials.",
        "updates.step3_title": "Decoupled Service Reload",
        "updates.step3_desc": "Executes via isolated systemd-run unit to prevent active session drops.",
        "updates.safety_title": "Release Integrity & Data Safety",
        "updates.safety_sub": "Backward compatibility guarantees",
        "updates.pill_backup": "Auto Backup (.bak)",
        "updates.pill_rules": "Rules & Ports Preserved",
        "updates.pill_auth": "PBKDF2 Auth Retained",
        "updates.transport_title": "GitHub Connection & Active Tunnel Fallback",
        "updates.transport_tip": "For servers with restricted or unstable direct access to GitHub: automatically or manually route update checks and downloads through active L3 tunnel interfaces (wg/awg/tun/gre/ipip), local SOCKS5/HTTP proxies (Xray/Sing-box/SSH -D), or a GitHub mirror without disturbing active relay ports.",
        "updates.transport_auto_short": "Auto Discovery",
        "updates.scan_tunnels": "Scan Tunnels",
        "updates.save_test_transport": "Save & Test",
        "updates.mode_label": "Connection Method",
        "updates.mode_auto": "Auto (Direct -> Active Tunnels / Local Proxies)",
        "updates.mode_direct": "Direct Internet Only",
        "updates.mode_iface": "Active Server Tunnel Interface (L3)",
        "updates.mode_proxy": "Local / Custom Proxy (SOCKS5 / HTTP)",
        "updates.mode_mirror": "GitHub Mirror URL",
        "updates.iface_label": "Select Active Tunnel Interface",
        "updates.iface_empty": "No active tunnel interfaces detected",
        "updates.proxy_label": "Proxy Address (SOCKS5h / HTTP)",
        "updates.proxy_detected": "Detected Local Proxies",
        "updates.mirror_label": "Mirror Base or Repo URL",
        "updates.auto_hint": "Tries Direct GitHub first; on timeout or block, automatically fails over through detected local proxies and UP tunnel interfaces using isolated host routes.",
        "updates.via_prefix": "Route: {label}",
        "updates.detected_summary": "{tunnels} UP tunnel(s) · {proxies} local proxy(s) ready",

        // Section 6: Logs & Probes
        "logs.title": "Real-time Failover & Probe Logs",
        "logs.desc": "Live timeline of socket health checks, priority transitions, and failover triggers.",
        "logs.copy": "Copy Logs",
        "logs.clear": "Clear Log",
        "logs.live_active": "Live Feed Active",
        "logs.live_paused": "Feed Paused",
        "logs.filter_placeholder": "Filter logs by port, IP, or event...",

        // Modals: Rule Modal
        "modal.rule_title_configure": "Configure Port Rule",
        "modal.rule_title_add": "Add Port Forwarding Rule",
        "modal.inbound_port": "Inbound Port",
        "modal.port_placeholder": "443, 1000-20000, or != 22",
        "modal.range_hint_nft_only": "NFTables 1:1 range mode",
        "modal.dest_port_range_placeholder": "Same range or port",
        "modal.excluded_ports": "Exclude Ports",
        "modal.excluded_ports_opt": "(Optional · NFTables only)",
        "modal.excluded_placeholder": "+ port",
        "modal.tunnel_iface": "Outbound Interface",
        "modal.tunnel_iface_auto": "Auto (Kernel Route)",
        "modal.tunnel_iface_auto_tag": "Auto",
        "modal.ingress_iface": "Inbound Tunnel Interface",
        "modal.ingress_iface_auto": "Auto (All Non-WAN)",
        "modal.spoof_ip": "Iran / Spoof IP",
        "modal.spoof_ip_opt": "Ingress IP (Optional)",
        "modal.spoof_ip_iran_opt": "Iran Public IP (Optional)",
        "modal.suggested_ip": "Suggested:",
        "modal.suggested": "Suggested",
        "modal.snat_ip": "Relay SNAT IP",
        "modal.proto": "Protocol",
        "modal.proto_both": "TCP + UDP",
        "modal.proto_tcp": "TCP Only",
        "modal.proto_udp": "UDP Only",
        "modal.category": "Category",
        "modal.category_opt": "(Optional)",
        "modal.category_placeholder": "e.g. Tehran Tunnels, VIP",
        "modal.failover_chain": "Failover Chain",
        "modal.failover_chain_sub": "Cascades in order from #1 to #2, #3 on failure",
        "modal.add_priority": "Add Failover Priority",
        "modal.dest_type": "Type",
        "modal.dest_target": "Target Host",
        "modal.dest_port": "Port",
        "modal.proxy_proto": "Send PROXY v2 Header",
        "modal.is_relay": "Intermediate Relay (Hop 1 Ping)",
        "modal.primary_path": "Primary Path",
        "modal.backup_path": "Backup Path",
        "modal.comment_label": "Label",
        "modal.comment_placeholder": "e.g. Foreign Node 1",
        "modal.test_target": "Test Target",
        "modal.mid_server": "Mid Server",
        "modal.send_proxy_v2": "PROXY v2",
        "modal.drag_hint": "Drag to reorder priority",
        "modal.tip_inbound_port": "Single port (443), NFTables 1:1 range (10000-20000 — forwards each port to the same port or a fixed target port), or != 22,443 for All-Except.",
        "modal.tip_excluded_ports": "Optional (NFTables only). SSH & panel ports are auto-protected. Example: 22, 443, 1001",
        "modal.tip_category": "Optional group name to organize ports with divider lines. Example: Tehran Tunnels, VIP",
        "modal.tip_failover_chain": "Traffic cascades from Priority #1 to #2, #3 on failure. Drag cards to reorder.",
        "modal.tip_outbound_iface": "Optional (NFTables). Bind probes & routing to a specific tunnel or WAN interface.",
        "modal.tip_ingress_iface": "Tunnel interface receiving packets from the Iran server (e.g. esp-link, gre15, ipip1). Required for DSR Direct; optional (Auto) for DSR Relay.",
        "modal.tip_spoof_ip": "Iran server public IP used as spoofed source on direct download return packets (required for DSR Relay & DSR Direct; auto-detected from WAN if empty on DSR Iran / SYN-ACK).",
        "modal.tip_snat_ip": "Optional (DSR Relay). Public WAN IP of this relay server used for SNAT toward exit nodes. Auto-detected if empty.",
        "modal.tip_comment": "Optional note for this path. Example: Foreign Server 1 - IPv6",
        "modal.tip_proxy_v2": "Send PROXY Protocol v2 header. Enable only if upstream (e.g. Xray acceptProxyProtocol) expects it.",
        "modal.tip_mid_server": "Partial hop node: anchors on Priority #1 unless #1 fails, has loss, or exceeds 150ms.",
        "modal.target_outside_tunnel": "Outside Tunnel IP",
        "modal.target_local_tunnel": "Local Tunnel IP",
        "modal.port_tunnel_relay": "Tunnel Relay Port",
        "modal.port_tunnel_listen": "Tunnel Listen Port",
        "modal.exit_relay_title": "3rd Exit Server Relay (Optional · 3-Server Mode)",
        "modal.exit_relay_sub": "Leave empty if Xray/3x-ui runs on this server. Fill if Xray/3x-ui runs on a 3rd server (e.g. Germany).",
        "modal.exit_target": "Exit Server IP",
        "modal.exit_port": "Exit Port",
        "modal.tip_exit_relay": "XForwarder will automatically start an isolated HAProxy listener on the Local Tunnel IP:Port and splice traffic onward to this Exit Server.",
        "modal.dsr_flow_label": "Traffic Flow Preview",
        "modal.dsr_mode_synack": "SYN-ACK Bypass",
        "modal.dsr_mode_direct_3hop": "3-Server Relay",
        "modal.dsr_mode_direct_local": "Local Service",
        "modal.dsr_direct_outside": "Download Direct from Outside",
        "modal.dsr_conflict_msg": "Port {port} on {target} is already used by rule :{rule}. Stateless DSR requires a unique backend port per rule.",
        "modal.dsr_use_port": "Use :{port}",
        "modal.lb_toggle": "Load Balance",
        "modal.lb_mode_label": "Distribution Algorithm",
        "modal.lb_equalize": "Equalize",
        "modal.lb_add_target": "Add Backend IP",
        "modal.lb_weight_label": "Weight",
        "modal.lb_algo_ip_hash": "IP Hash (Sticky Session)",
        "modal.lb_algo_least_conn": "Least Connections",
        "modal.lb_algo_round_robin": "Round-Robin",
        "modal.lb_algo_random": "Random",
        "modal.lb_hint_ip_hash": "Sticky per client IP — recommended for VPN, Xray, Reality & WireGuard so active sessions never jump servers.",
        "modal.lb_hint_least_conn": "Routes each new connection to the backend with the fewest active connections (weighted). Ideal for uneven session lengths.",
        "modal.lb_hint_round_robin": "Distributes each new connection sequentially across healthy backends according to their weights.",
        "modal.lb_hint_random": "Randomly selects a healthy backend per new connection according to weights (Nginx uses Power of Two Choices).",
        "modal.lb_nft_family_note": "NFTables requires all pool IPs to be the same family (all IPv4 or all IPv6). Down nodes are auto-excluded.",
        "modal.lb_nginx_note": "Nginx passively skips failed TCP targets (max_fails=2) and the engine auto-prunes dead nodes every 15s.",
        "modal.tip_lb_toggle": "Distribute traffic across multiple backend IPs within this priority. Unreachable nodes are automatically excluded until they recover.",
        "modal.tip_lb_mode": "Choose how connections are distributed: IP Hash keeps each user pinned to one server (best for VPN/TLS/WireGuard); Least Conn sends new sessions to the least busy Nginx backend; Round-Robin & Random spread new connections evenly by weight.",
        "modal.tip_lb_weight": "Relative traffic share (1–100). Example: weights 2 and 1 send ~67% to the first IP and ~33% to the second.",
        "modal.cancel": "Cancel",
        "modal.save_rule": "Save & Apply Changes",

        // Modals: Import Config
        "import.title": "Import Configuration",
        "import.sub": "Upload or paste an XForwarder backup configuration JSON",
        "import.mode": "Import Mode",
        "import.merge_title": "Merge (Recommended)",
        "import.merge_desc": "Appends and updates port rules. Preserves existing non-conflicting rules.",
        "import.replace_title": "Replace All Rules",
        "import.replace_desc": "Replaces all port rules with the imported set. Admin credentials and panel port remain safe.",
        "import.paste_label": "Configuration JSON",
        "import.btn_paste": "Paste",
        "import.btn_format": "Format",
        "import.btn_clear": "Clear",
        "import.drop_text": "Click or drag & drop backup JSON file here",
        "import.or_file": "or import from file",
        "import.apply": "Import & Apply",

        // Modals: Traffic Modal
        "traffic_modal.title": "Traffic & Bandwidth Analytics",
        "traffic_modal.sub": "Real-time bandwidth accounting across ports and tunnels",
        "traffic_modal.target": "Target:",
        "traffic_modal.all_ports_tunnels": "All Ports & Tunnels",
        "traffic_modal.forwarded_ports": "Forwarded Ports",
        "traffic_modal.methods_tunnels": "Forwarding Methods & Tunnel Types",
        "traffic_modal.tunnel_ifaces": "Tunnel Interfaces",
        "traffic_modal.billing_cycle": "Billing Cycle",
        "traffic_modal.active_since": "Active since:",
        "traffic_modal.reset": "Reset",
        "traffic_modal.outbound_tx": "Download (TX)",
        "traffic_modal.outbound_badge": "↓ Outbound",
        "traffic_modal.outbound_meta": "Sent to clients / targets",
        "traffic_modal.inbound_rx": "Upload (RX)",
        "traffic_modal.inbound_badge": "↑ Inbound",
        "traffic_modal.inbound_meta": "Received from clients",
        "traffic_modal.total_bandwidth": "Total Bandwidth",
        "traffic_modal.combined_badge": "Combined",
        "traffic_modal.period_meta": "Across selected period",
        "traffic_modal.breakdown_title": "Forwarding Path & Tunnel Breakdown",
        "traffic_modal.breakdown_sub": "Distribution by relay method",
        "traffic_modal.chart_title": "Bandwidth Consumption Timeline",
        "traffic_modal.table_title": "Detailed Records",
        "traffic_modal.col_period": "Period / Time",
        "traffic_modal.col_rx": "Upload (RX)",
        "traffic_modal.col_tx": "Download (TX)",
        "traffic_modal.col_total": "Total Usage",
        "traffic_modal.col_share": "Share",
        "traffic_modal.wipe_history": "Wipe History",
        "traffic_modal.close": "Close",

        // Modals: Switch Decision Logs
        "switch_logs.title": "Switch Decision Logs",
        "switch_logs.sub": "Real-time audit log of multi-path failovers and automated decision reasons",
        "switch_logs.filter": "Filter Rule:",
        "switch_logs.all_rules": "All Port Rules",
        "switch_logs.showing_recent": "Showing recent switch events",
        "switch_logs.copy": "Copy Logs",
        "switch_logs.close": "Close",

        // Modals: System Update
        "update_modal.title": "XForwarder System Update",
        "update_modal.sub": "Pull latest release from GitHub, execute schema migrations, and reload daemons",
        "update_modal.ready_title": "Ready to Update",
        "update_modal.ready_sub": "The update will run in an isolated systemd job.",
        "update_modal.step1": "Fetches latest commits from PouryaDe/XForwarder",
        "update_modal.step2": "Automated backup of config.json before applying changes",
        "update_modal.step3": "Executes idempotent schema normalization (migrate_and_normalize_config)",
        "update_modal.step4": "Non-disruptively restarts core failover engine and web dashboard",
        "update_modal.step5": "Dashboard will automatically reconnect and refresh when complete",
        "update_modal.start_btn": "Start Update Now",
        "update_modal.cancel": "Cancel",

        // Confirm & Sync Dialogs
        "confirm.delete_title": "Delete Port Forwarding Rule?",
        "confirm.delete_msg": "Are you sure you want to delete this forwarding rule? Traffic routing on this port will stop immediately.",
        "confirm.delete_rule_msg": "Are you sure you want to delete forwarding rule '{id}'? Routing on this port will stop immediately.",
        "confirm.cancel": "Cancel",
        "confirm.delete_btn": "Delete Rule",
        "confirm.confirm_btn": "Confirm",
        "confirm.restart_btn": "Restart Service",
        "confirm.reload_btn": "Reload Service",
        "confirm.sync_btn": "Sync Table",
        "confirm.reset_btn": "Reset Counter",
        "confirm.wipe_btn": "Wipe History",
        "confirm.restart_svc_title": "Restart {service}?",
        "confirm.reload_svc_title": "Reload {service}?",
        "confirm.sync_svc_title": "Synchronize {service}?",
        "confirm.restart_all_msg": "Are you sure you want to restart {service}? The web dashboard will temporarily disconnect and reconnect automatically in ~2 seconds.",
        "confirm.restart_svc_msg": "Are you sure you want to restart {service}? Configuration will be re-synchronized and the service will restart cleanly.",
        "confirm.reload_svc_msg": "Are you sure you want to reload/restart {service}? Active client connections will be preserved.",
        "sync_error.title": "Server Synchronization Notice",
        "sync_error.msg": "Configuration was saved, but one or more server commands reported an issue:",
        "sync_error.dismiss": "Dismiss",
        "sync_error.retry": "Retry Server Sync",

        // General Status & Verbs
        "status.healthy": "HEALTHY",
        "status.down": "DOWN",
        "status.degraded": "DEGRADED",
        "status.standby": "STANDBY",
        "status.critical": "CRITICAL",
        "status.off": "OFF",
        "status.active": "ACTIVE",
        "status.inactive": "INACTIVE",
        "status.failover": "FAILOVER",
        "status.checking": "Checking...",
        "status.installed": "Installed",
        "status.not_installed": "Not Installed",
        "status.not_installed_caps": "NOT INSTALLED",
        "status.running": "RUNNING",
        "status.active_running": "Active & Running",
        "status.standby_stopped": "Standby (Stopped)",
        "status.active_synced": "ACTIVE & SYNCED",
        "status.table_idle": "Active (Table Idle)",
        "status.table_loaded": "Active & Orchestrator Loaded",
        "status.probing": "Probing...",
        "status.reachable": "Reachable",
        "status.unreachable": "Unreachable",
        "status.enter_target": "Enter target IP",
        "status.enter_port": "Enter port",
        "status.ipv6_required": "IPv6 required for HAProxy",
        "status.network_error": "Network Error",
        "status.ready_caps": "READY",
        "status.optimal": "Optimal",
        "status.normal": "Normal",
        "status.elevated": "Elevated",
        "status.heavy": "Heavy",
        "status.synced": "SYNCED",
        "common.edit": "Edit",
        "common.delete": "Delete",
        "common.test": "Test",
        "common.testing": "Testing...",
        "common.copied": "Copied to clipboard!",
        "common.copy_fail": "Failed to copy to clipboard",
        "theme.light": "Light",
        "theme.dark": "Dark"
    },
    fa: {
        // App & Brand
        "brand.title": "ایکس‌فورواردِر",
        "brand.shield": "سپر امنیتی",
        "brand.subtitle": "موتور هوشمند رله و تغییر مسیر خودکار چندمسیره",

        // Login Screen
        "login.title": "ایکس‌فورواردِر",
        "login.subtitle": "موتور هوشمند رله و تغییر مسیر خودکار چندمسیره",
        "login.lockout_title": "قفل امنیتی فعال است",
        "login.lockout_desc": "تعداد تلاش‌های ناموفق بیش از حد مجاز است.",
        "login.username": "نام کاربری",
        "login.username_placeholder": "admin",
        "login.password": "رمز عبور",
        "login.password_placeholder": "••••••••",
        "login.caps_lock": "کلید Caps Lock روشن است",
        "login.submit": "ورود به داشبورد",
        "login.submitting": "در حال ورود...",
        "login.failed": "نام کاربری یا رمز عبور نامعتبر است",
        "login.theme": "پوسته",
        "login.lang": "English",
        "login.art_badge": "موتور رله و فیل‌اور چندمسیره",
        "login.art_pitch": "کنترل کامل پورت‌ها، تونل‌ها و فیل‌اور هوشمند در یک جا.",

        // Navigation & Sidebar
        "nav.main": "منوی اصلی",
        "nav.rules": "پورت‌ها",
        "nav.overview": "نمای کلی",
        "nav.traffic": "شبکه",
        "nav.services": "سرویس‌ها",
        "nav.updates": "آپدیت",
        "nav.security": "امنیت",
        "nav.logs": "لاگ‌ها",
        "user.admin": "مدیر سیستم",
        "user.role": "مدیر سیستم",

        // Network Quality & Diagnostics Section
        "traffic_section.title": "کیفیت شبکه",
        "traffic_section.sub": "خط زمانی ۳۰ روزه پکت‌لاس، وضعیت پایداری مسیرها و تست زنده کیفیت شبکه.",

        // Service Warning Banner
        "services_warning.title": "پکیج‌های هسته رله نصب نیستند",
        "services_warning.desc": "یک یا چند سرویس اصلی فورواردینگ بر روی این سرور نصب نشده‌اند.",
        "services_warning.dismiss": "بستن",

        // Section 1: Port Rules
        "rules.title": "مسیریابی پورت‌ها و ماتریس چندمسیره",
        "rules.desc": "ترافیک هر پورت از طریق اولویت ۱ هدایت شده و در صورت افت بسته یا قطعی، خودکار به اولویت‌های پشتیبان منتقل می‌شود.",
        "rules.export": "خروجی",
        "rules.import": "ورودی",
        "rules.traffic": "ترافیک",
        "rules.switch_logs": "لاگ جابجایی",
        "rules.add_rule": "افزودن پورت",
        "rules.search_placeholder": "جستجوی پورت، آی‌پی، دسته‌بندی یا توضیحات...",
        "rules.sort_port_asc": "پورت: کم به زیاد",
        "rules.sort_port_desc": "پورت: زیاد به کم",
        "rules.sort_date_desc": "جدیدترین",
        "rules.sort_date_asc": "قدیمی‌ترین",
        "rules.sort_status": "وضعیت سلامت",
        "rules.sort_category": "دسته‌بندی (الف - ی)",
        "rules.view_cards": "کارت‌ها",
        "rules.view_list": "لیست",
        "rules.auto_failover": "جابجایی خودکار",
        "rules.force_prio": "اجبار اولویت #{prio}",
        "rules.primary": "اصلی",
        "rules.backup": "پشتیبان",
        "rules.active": "فعال",
        "rules.hold": "تثبیت {sec} ثانیه",
        "rules.switch_in": "تغییر در {sec} ثانیه",
        "rules.relay": "رله",
        "rules.test": "تست",
        "rules.copy_json": "کپی JSON قانون",
        "rules.copy_all_json": "کپی کل JSON",
        "rules.empty_title": "قانونی برای فوروارد یافت نشد",
        "rules.empty_desc": "برای ایجاد اولین فوروارد، روی دکمه «افزودن پورت» کلیک کنید.",
        "rules.last_switch": "آخرین تغییر مسیر:",
        "rules.import_banner_title": "قوانین رله از پیش موجود شناسایی شد",
        "rules.import_banner_desc": "قوانین فوروارد پورت از قبل فعال روی این سرور پیدا شدند.",
        "rules.import_all": "درون‌ریزی تمام قوانین",
        "rules.dismiss": "بستن",
        "rules.uncategorized": "بدون دسته‌بندی",
        "rules.forced": "اجباری",
        "rules.ports_count": "{count} پورت",
        "rules.copy_category_json": "کپی JSON دسته‌بندی",
        "rules.copy_category_json_tooltip": "کپی JSON همه پورت‌های «{cat}»",
        "rules.toggle_cat_hide": "مخفی کردن پورت‌های دسته",
        "rules.toggle_cat_show": "نمایش پورت‌های دسته",
        "rules.delete_category_tooltip": "حذف همه پورت‌های «{cat}»",
        "confirm.delete_category_title": "حذف همه پورت‌های دسته‌بندی؟",
        "confirm.delete_category_msg": "آیا از حذف هر {count} پورت در دسته «{cat}» مطمئن هستید؟ هدایت ترافیک این پورت‌ها متوقف می‌شود.",
        "confirm.delete_category_btn": "حذف همه",
        "rules.forwarding_label": "هدایت ترافیک:",
        "rules.copy_port_num": "کپی شماره پورت",
        "rules.copy_dest_ip": "کپی آی‌پی مقصد",
        "rules.edit_rule": "ویرایش رله",
        "rules.delete_rule": "حذف رله",
        "rules.switch_logs_tooltip": "تاریخچه و لاگ تصمیمات جابجایی",
        "rules.traffic_analytics_tooltip": "آمار ترافیک و پهنای باند",
        "rules.copy_rule_json": "کپی تنظیمات پورت (JSON)",
        "rules.priority_on_tooltip": "اولویت #{prio} روشن است (برای خاموش کردن کلیک کنید)",
        "rules.priority_off_tooltip": "اولویت #{prio} خاموش است (برای روشن کردن کلیک کنید)",
        "rules.relay_tooltip": "سرور میانی: موتور روی اولویت ۱ تثبیت شده و فقط در صورت قطعی، افت بسته یا پینگ بالای ۱۵۰ میلی‌ثانیه به این مسیر جابجا می‌شود.",
        "rules.switch_pending_tooltip": "کاندید P{prio} برتری کیفیت پایدار دارد. انتقال پس از تأیید پایداری.",
        "rules.min_hold_tooltip": "مسیر برای جلوگیری از اختلال تثبیت شده است (حداقل ۱۰ دقیقه)",
        "rules.cooldown_tooltip": "دوره خنک‌سازی پس از قطعی بحرانی فعال است",
        "rules.flapping_tooltip": "نوسان مکرر مسیر تشخیص داده شد. زمان تثبیت افزایش یافت.",
        "rules.flap_guard": "محافظ نوسان",
        "rules.traffic_cycle_tooltip": "ترافیک دوره جاری: ارسال ↑ {tx} · دریافت ↓ {rx} (برای جزئیات و صفر کردن کلیک کنید)",
        "rules.lb_badge": "LB",
        "rules.lb_pool_up": "{healthy}/{total} فعال",
        "rules.lb_pool_tooltip": "استخر توزیع بار ({algo}) · {healthy} از {total} سرور سالم در حال سرویس‌دهی هستند. نودهای قطع‌شده خودکار کنار گذاشته می‌شوند.",
        "rules.lb_show_more": "+{count} مورد دیگر",
        "rules.lb_show_less": "نمایش کمتر",
        "rules.lb_ip_family_warn": "در استخر LB برای NFTables نمی‌توان IPv4 و IPv6 را با هم ترکیب کرد",

        // Section 2: Overview
        "overview.title": "نمای کلی",
        "overview.desc": "پایش لحظه‌ای منابع سرور، آمار مصرف روزانه پهنای باند، توپولوژی تونل‌ها و تحلیل ۳۰ روزه افت بسته.",
        "overview.cpu": "پردازنده و بار سیستم",
        "overview.cpu_load": "بار پردازنده",
        "overview.memory": "حافظه رم",
        "overview.active_sockets": "سوکت‌های فعال",
        "overview.live_bandwidth": "پهنای باند لحظه‌ای",
        "overview.traffic_sub": "ترافیک زنده شبکه · برای تغییر کلیک کنید",
        "overview.stat_forwarded": "پورت‌های فوروارد شده",
        "overview.stat_forwarded_sub": "مسیرهای ورودی فعال",
        "overview.stat_proxy": "پروکسی فعال (L4)",
        "overview.stat_proxy_sub": "رله مستقیم لایه ۴",
        "overview.stat_nftables": "ان‌اف‌تیبلز فعال (L3)",
        "overview.stat_nftables_sub": "مسیریابی تونل در سطح هسته",
        "overview.stat_quality": "کیفیت شبکه (۲۴ ساعت)",
        "overview.stat_quality_sub": "۰٪ پکت‌لاس · پایش مستمر",
        "overview.daily_traffic_title": "مصرف ترافیک و پهنای باند روزانه",
        "overview.daily_traffic_sub": "محاسبه دقیق ساعتی ترافیک روی تمامی پورت‌ها و تونل‌ها · پایگاه داده SQLite WAL",
        "overview.past_24h": "۲۴ ساعت گذشته",
        "overview.24h": "۲۴ ساعت",
        "overview.7d": "۷ روز",
        "overview.30d": "۳۰ روز",
        "overview.full_analytics": "تحلیل کامل",
        "overview.traffic_total": "کل ترافیک ۲۴ ساعت",
        "overview.traffic_total_sub": "تمامی پورت‌ها و تونل‌های فعال",
        "overview.download_rx": "دانلود (ورودی)",
        "overview.download_rx_sub": "ترافیک ورودی کاربران",
        "overview.upload_tx": "آپلود (خروجی)",
        "overview.upload_tx_sub": "ترافیک ارسالی به مقصد",
        "overview.peak_hourly": "اوج مصرف ساعتی",
        "overview.peak_hourly_sub": "بازه اوج پهنای باند",
        "overview.chart_title": "توزیع ساعتی پهنای باند (۲۴ ساعت گذشته)",
        "overview.legend_tx": "آپلود (TX)",
        "overview.legend_rx": "دانلود (RX)",
        "overview.ticks_24h": "۲۴ ساعت پیش",
        "overview.ticks_18h": "۱۸ ساعت پیش",
        "overview.ticks_12h": "۱۲ ساعت پیش",
        "overview.ticks_6h": "۶ ساعت پیش",
        "overview.ticks_now": "اکنون",
        "overview.net_title": "توپولوژی شبکه و تونل‌های سرور",
        "overview.net_sub": "آدرس‌های عمومی WAN سرور، اینترفیس‌های فعال تونل و پینگ",
        "overview.server_ips": "آی‌پی(های) سرور:",
        "overview.tunnels_count": "{count} تونل",
        "overview.detecting": "در حال شناسایی...",
        "overview.engines_title": "موتورهای رله",
        "overview.engines_sub": "مسیریابی NAT هسته و پروکسی‌های ترافیک",
        "overview.all_active": "همه فعال هستند",
        "overview.nft_name": "دی‌نت NFTables",
        "overview.nft_desc": "فورواردینگ لایه ۳ تونل در هسته",
        "overview.haproxy_name": "رله HAProxy",
        "overview.haproxy_desc": "ترافیک مستقیم TCP/UDP لایه ۴",
        "overview.nginx_name": "جریان Nginx",
        "overview.nginx_desc": "پروکسی همزمان بالا برای TCP/UDP",
        "overview.zero_collision": "جداسازی بدون تداخل پورت فعال است",
        "overview.quality_title": "خط زمانی کیفیت شبکه و پکت‌لاس",
        "overview.quality_sub": "آزمون خودکار ۵۰ پروب هر ۱۵ دقیقه · نگهداری ۳۰ روزه سوابق",
        "overview.target_ip": "آی‌پی مقصد:",
        "overview.all_targets": "تمامی مقصدهای پایش‌شده",
        "overview.run_round": "اجرای تست",
        "overview.quality_label": "کیفیت شبکه",
        "overview.avg_latency": "میانگین تأخیر",
        "overview.avg_loss": "میانگین / حداکثر افت بسته",
        "overview.disruptions": "رویدادهای اختلال",
        "overview.timeline_title": "خط زمانی سلامت شبکه",
        "overview.clean": "پایدار (۰٪ افت)",
        "overview.degraded": "ناپایدار (۱-۲۰٪)",
        "overview.disrupted": "مختل (>۲۰٪)",
        "overview.disruptions_log": "ثبت رخدادهای اختلال شبکه",
        "overview.disruptions_sub": "زمان‌هایی که افت بسته یا قطعی ارتباط رخ داده است",
        "overview.col_time": "زمان",
        "overview.col_target": "میزبان مقصد",
        "overview.col_loss": "افت بسته (Loss)",
        "overview.col_latency": "تأخیر (پینگ)",
        "overview.col_probes": "تعداد پروب",
        "overview.col_status": "شدت / وضعیت",
        "overview.prev": "قبلی",
        "overview.next": "بعدی",

        // Section 3: Relay Services
        "services.title": "سرویس‌های رله و موتورهای فورواردینگ",
        "services.desc": "مدیریت، بارگذاری مجدد و همگام‌سازی موتورهای پروکسی و جداول بسته هسته.",
        "services.restart_engine": "راه‌اندازی مجدد موتور",
        "services.restart_all": "راه‌اندازی مجدد تمام سرویس‌ها",
        "services.haproxy_title": "موتور HAProxy بدون تونل",
        "services.haproxy_sub": "رله مستقیم لایه ۴ برای TCP/UDP با IPv6",
        "services.haproxy_desc": "رله مستقیم بدون سربار بسته‌بندی شبکه. بارگذاری مجدد بدون قطع اتصال هنگام تغییر اولویت.",
        "services.config_location": "مسیر فایل تنظیمات",
        "services.installation": "وضعیت نصب",
        "services.service_status": "وضعیت سرویس",
        "services.binary_version": "نسخه برنامه",
        "services.reload_mechanism": "روش بارگذاری مجدد",
        "services.active_bindings": "پورت‌های فعال متصل",
        "services.reload_haproxy": "ریلود",
        "services.restart_haproxy": "ریستارت",
        "services.nftables_title": "دی‌نت هسته NFTables",
        "services.nftables_sub": "فورواردینگ لایه ۳ تونل در سطح هسته",
        "services.nftables_desc": "فورواردینگ پرسرعت روی تونل‌های GRE، IPIP، FakeTCP یا AmneziaWG بدون تداخل با فایروال سیستم.",
        "services.isolated_tables": "جدول ایزوله",
        "services.kernel_status": "وضعیت هسته",
        "services.flush_safety": "ایمنی دستورات",
        "services.flush_safety_val": "هرگز دستور حذف کل قوانین فایروال اجرا نمی‌شود",
        "services.sync_nftables": "همگام‌سازی",
        "services.restart_nftables": "ریستارت",
        "services.nginx_title": "موتور پروکسی جریان Nginx",
        "services.nginx_sub": "فورواردینگ با کارایی بالا در لایه ۴",
        "services.nginx_desc": "پروکسی همزمان TCP/UDP با معماری چندگانه epoll، مدیریت‌شده به صورت پویا توسط XForwarder.",
        "services.sync_nginx": "همگام‌سازی",
        "services.nginx_sync_mode_title": "انتخاب جهت همگام‌سازی Nginx",
        "services.nginx_sync_mode_msg": "انتخاب کنید تنظیمات XForwarder روی Nginx اعمال شود، یا اولویت‌های Nginx در بخش پورت‌ها بر اساس وضعیت فعلی Nginx روی سرور همگام شوند (اگر Nginx خالی باشد، اولویت‌های Nginx از رول‌ها حذف می‌شوند).",
        "services.nginx_sync_push_btn": "XForwarder → Nginx",
        "services.nginx_sync_pull_btn": "Nginx → XForwarder",
        "services.reload_nginx": "ریلود",
        "services.restart_nginx": "ریستارت",
        "services.name_all": "تمامی سرویس‌ها و دیمون‌های رله",
        "services.name_engine": "موتور هسته فیل‌اور XForwarder",
        "services.name_haproxy": "سرویس رله HAProxy",
        "services.name_nginx": "پروکسی استریم Nginx",
        "services.name_nftables": "جدول NFTables (xfwd_orchestrator)",
        "services.restarting_toast": "در حال راه‌اندازی مجدد {service}...",
        "services.reloaded_toast": "{service} با موفقیت بازخوانی شد!",
        "services.restarted_toast": "{service} با موفقیت راه‌اندازی مجدد شد!",
        "services.restart_failed_toast": "خطا در راه‌اندازی مجدد {service}: {error}",
        "services.discovery_title": "شناسایی قوانین رله از پیش موجود",
        "services.discovery_sub": "شناسایی خودکار و درون‌ریزی قوانین فعال HAProxy و NFTables در XForwarder",
        "services.scan_server": "اسکن سرور",
        "services.discovery_desc": "اگر این سرور قبلاً دارای قوانین HAProxy یا DNAT بوده، این ابزار می‌تواند بدون تداخل پورت‌ها آن‌ها را شناسایی و درون‌ریزی کند.",
        "services.scan_prompt": "برای بررسی قوانین مدیریت‌نشده HAProxy و NFTables روی «اسکن سرور» کلیک کنید.",
        "services.kernel_opt_title": "بهینه‌ساز کرنل و شبکه",
        "services.kernel_opt_sub": "تنظیم هوشمند BBR، صف fq، conntrack، MTU Probing و ایمن‌سازی ESP Spoof / DSR (rp_filter=0)",
        "services.kernel_opt_refresh": "بروزرسانی",
        "services.kernel_opt_apply": "بهینه‌سازی اکنون",
        "services.kernel_opt_applying": "در حال بهینه‌سازی...",
        "services.kernel_opt_profile_lbl": "پروفایل سرور",
        "services.kernel_opt_tcp_lbl": "TCP / Qdisc",
        "services.kernel_opt_rp_lbl": "فیلتر RP (ESP/DSR)",
        "services.kernel_opt_ct_lbl": "Conntrack",
        "services.kernel_opt_reset_title": "پاک‌سازی تنظیمات قبلی و اعمال پروفایل تمیز",
        "services.kernel_opt_reset_desc": "از /etc/sysctl.conf و فایل‌های متداخل /etc/sysctl.d/*.conf بکاپ گرفته، آن‌ها را پاک می‌کند، خطوط تکراری nf_conntrack در /etc/modules را تمیز کرده و تنظیمات جدید را اعمال می‌کند.",
        "services.kernel_opt_confirm_title": "اعمال بهینه‌سازی کرنل و شبکه؟",
        "services.kernel_opt_confirm_msg": "تنظیمات هوشمند BBR، fq، conntrack، MTU Probing و rp_filter=0 (سازگار با ESP Spoof / DSR) در /etc/sysctl.d/99-xforwarder.conf بدون قطعی تانل‌ها اعمال می‌شود.",
        "services.kernel_opt_confirm_reset_msg": "ابتدا از /etc/sysctl.conf و فایل‌های متداخل بکاپ در /etc/xforwarder/backups گرفته می‌شود، تنظیمات قبلی و تکرارهای /etc/modules حذف شده و پروفایل تمیز و سازگار با ESP Spoof اعمال می‌گردد.",
        "services.kernel_opt_conflict_hdr": "تداخل یا تنظیمات قدیمی شناسایی شد (پیشنهاد می‌شود گزینه «پاک‌سازی تنظیمات قبلی» را تیک بزنید):",

        "network.spoof_title": "تست قابلیت IP Spoof / DSR",
        "network.spoof_sub": "بررسی مجاز بودن ارسال پکت با آی‌پی اسپوف‌شده در این سرور و دیتاسنتر.",
        "network.spoof_listen_title": "گیرنده تست (سرور ایران)",
        "network.spoof_listen_desc": "باز کردن پورت موقت UDP برای دریافت پکت‌های تست.",
        "network.spoof_listen_start": "شروع گیرنده",
        "network.spoof_listen_stop": "توقف گیرنده",
        "network.spoof_udp_port": "پورت UDP",
        "network.spoof_port_short": "پورت",
        "network.spoof_cli_hint": "دستور اجرا روی سرور خارج:",
        "network.spoof_run_title": "تست خروج (سرور خارج)",
        "network.spoof_run_desc": "ارسال پکت عادی و اسپوف‌شده به سمت گیرنده ایران.",
        "network.spoof_peer_ip": "آی‌پی ایران",
        "network.spoof_src_ip": "آی‌پی اسپوف",
        "network.spoof_run_btn": "اجرای تست Spoof / DSR",
        "network.spoof_running": "در حال تست...",
        "common.copy": "کپی",

        // Section 4: Security & Access
        "security.title": "امنیت و دسترسی",
        "security.desc": "پشتیبان‌گیری امن از تنظیمات، درون‌ریزی قوانین و مدیریت اطلاعات ورود مدیر سیستم.",
        "security.backup_title": "پشتیبان‌گیری و مهاجرت",
        "security.backup_sub": "خروجی گرفتن و درون‌ریزی قوانین مسیریابی و تنظیمات سرور",
        "security.backup_desc": "تهیه فایل پشتیبان مطمئن از قوانین فوروارد. فایل‌های خروجی برای حفظ امنیت فاقد رمز عبور مدیر هستند.",
        "security.export_btn": "خروجی فایل JSON",
        "security.import_btn": "درون‌ریزی تنظیمات",
        "security.admin_title": "اطلاعات ورود مدیر",
        "security.admin_sub": "تغییر نام کاربری و رمز عبور داشبورد وب",
        "security.current_pwd": "رمز عبور فعلی مدیر *",
        "security.current_pwd_placeholder": "رمز عبور فعلی",
        "security.new_user": "نام کاربری جدید (اختیاری)",
        "security.new_user_placeholder": "جهت حفظ نام فعلی خالی بگذارید",
        "security.new_pwd": "رمز عبور جدید (اختیاری)",
        "security.new_pwd_placeholder": "حداقل ۸ کاراکتر",
        "security.confirm_pwd": "تکرار رمز عبور جدید",
        "security.confirm_pwd_placeholder": "تکرار رمز جدید",
        "security.update_btn": "به‌روزرسانی اطلاعات ورود",
        "security.panel_title": "دسترسی پنل (پورت و مسیر URL)",
        "security.panel_sub": "تغییر پورت داشبورد وب و مسیر مخفی آدرس پنل",
        "security.panel_port": "پورت پنل *",
        "security.panel_path": "مسیر مخفی (Path)",
        "security.panel_path_placeholder": "xfwd-admin (یا خالی برای /)",
        "security.panel_save_btn": "ذخیره و ریستارت پنل",
        "security.updates_title": "به‌روزرسانی سیستم و نرم‌افزار",
        "security.updates_sub": "بررسی نسخه‌های جدید گیت‌هاب، مهاجرت خودکار ساختار و ارتقای سرویس‌ها",
        "security.installed_version": "نسخه نصب‌شده",
        "security.local_commit": "کد کامیت محلی",
        "security.remote_commit": "آخرین کامیت گیت‌هاب",
        "security.last_checked": "آخرین بررسی",
        "security.never": "هرگز",
        "security.check_updates": "بررسی نسخه‌های جدید",
        "security.update_latest": "ارتقا به آخرین نسخه",
        "security.update_note": "به‌روزرسانی‌ها به طور خودکار فایل پشتیبان تهیه کرده و داده‌ها را با صفر درصد قطعی حفظ می‌کنند.",

        // REST API & API Keys
        "api.title": "وب‌سرویس REST API و کلیدهای دسترسی",
        "api.sub": "ساخت توکن‌های Bearer / X-API-Key با سطح دسترسی مشخص و مشاهده مستندات کامل API",
        "api.download_openapi": "فایل OpenAPI JSON",
        "api.view_docs": "راهنمای API",
        "api.key_name": "نام کلید",
        "api.key_name_placeholder": "مثال: ربات مدیریت یا پنل فروش",
        "api.scope": "سطح دسترسی",
        "api.scope_admin": "ادمین (دسترسی کامل)",
        "api.scope_write": "نوشتن (قوانین و تست‌ها)",
        "api.scope_read": "فقط خواندن (Read-Only)",
        "api.expiry": "انقضا",
        "api.exp_never": "بدون انقضا",
        "api.exp_30": "۳۰ روز",
        "api.exp_90": "۹۰ روز",
        "api.exp_365": "۳۶۵ روز",
        "api.generate_btn": "ساخت کلید API",
        "api.reveal_title": "کلید API جدید را همین الان کپی کنید — دیگر نمایش داده نخواهد شد:",
        "api.copy_key": "کپی کلید",
        "api.empty": "هنوز کلید API ساخته نشده است. برای اتصال اسکریپت‌ها یا پنل‌های دیگر یک کلید بسازید.",
        "api.docs_title": "مستندات جامع REST API در XForwarder",
        "api.docs_sub": "پشتیبانی از Bearer Token، X-API-Key و Session روی مسیرهای /api/* و /api/v1/*",
        "api.base_url": "آدرس پایه:",
        "api.auth_headers": "هدرهای احراز هویت:",
        "api.cat_all": "همه",
        "api.cat_auth": "احراز هویت و کلیدها",
        "api.cat_rules": "مدیریت قوانین (CRUD)",
        "api.cat_failover": "فیل‌اور و تست‌ها",
        "api.cat_traffic": "ترافیک و متریک‌ها",
        "api.cat_system": "سیستم و تنظیمات",
        "api.never": "هرگز",
        "api.status_expired": "منقضی‌شده",
        "api.disable_btn": "غیرفعال",
        "api.enable_btn": "فعال‌سازی",
        "api.no_expiry": "نامحدود",
        "api.last_used": "آخرین استفاده:",
        "api.expires": "انقضا:",
        "api.revoke_btn": "ابطال کلید",
        "api.updated_toast": "وضعیت کلید API به‌روزرسانی شد",
        "api.revoke_confirm_title": "ابطال کلید API؟",
        "api.revoke_confirm_msg": "آیا از ابطال کلید «{name}» مطمئن هستید؟ تمامی سرویس‌های متصل با این کلید فوراً خطای 401 دریافت خواهند کرد.",
        "api.revoked_toast": "کلید API با موفقیت ابطال شد",
        "api.name_required": "لطفاً نام کلید API را وارد کنید",
        "api.created_toast": "کلید API ساخته شد! همین الان آن را کپی کنید.",
        "api.copied_secret": "کلید API در کلیپ‌بورد کپی شد!",
        "api.openapi_downloaded": "فایل OpenAPI 3.0 دانلود شد",

        // Section 5: System Updates
        "updates.title": "به‌روزرسانی سیستم",
        "updates.desc": "بررسی نسخه‌های جدید گیت‌هاب، مهاجرت خودکار ساختار تنظیمات و ارتقای ایمن سرویس‌های رله.",
        "updates.pipeline_title": "روند ارتقای خودکار",
        "updates.pipeline_sub": "ترتیب اجرای بدون قطعی",
        "updates.step1_title": "نسخه پشتیبان اتمیک از تنظیمات",
        "updates.step1_desc": "ایجاد بکاپ زمان‌دار از قوانین فعال و اطلاعات ورود پیش از دریافت کد جدید.",
        "updates.step2_title": "مهاجرت خودکار ساختار (Schema)",
        "updates.step2_desc": "همگام‌سازی ساختار فایل تنظیمات با حفظ کامل پورت‌های اختصاصی و رمزها.",
        "updates.step3_title": "راه‌اندازی مجدد ایزوله سرویس‌ها",
        "updates.step3_desc": "اجرا در واحد مستقل systemd-run جهت جلوگیری از قطع نشست‌های فعال.",
        "updates.safety_title": "یکپارچگی نسخه و امنیت داده‌ها",
        "updates.safety_sub": "تضمین سازگاری با نسخه‌های قبلی",
        "updates.pill_backup": "بکاپ خودکار (.bak)",
        "updates.pill_rules": "حفظ قوانین و پورت‌ها",
        "updates.pill_auth": "حفظ رمزنگاری PBKDF2",
        "updates.transport_title": "مسیر اتصال به گیت‌هاب و استفاده از تونل‌های فعال سرور",
        "updates.transport_tip": "مناسب برای سرورهایی که دسترسی مستقیم به گیت‌هاب در آن‌ها مسدود یا ناپایدار است: بررسی نسخه و دانلود آپدیت به صورت خودکار یا دستی از طریق اینترفیس‌های تونل فعال سرور (wg/awg/tun/gre/ipip)، پروکسی‌های لوکال (SOCKS5/HTTP مثل Xray/SSH) یا آینه گیت‌هاب بدون هیچ اختلالی در پورت‌های فوروارد انجام می‌شود.",
        "updates.transport_auto_short": "تشخیص خودکار",
        "updates.scan_tunnels": "اسکن تونل‌ها",
        "updates.save_test_transport": "ذخیره و تست",
        "updates.mode_label": "روش اتصال برای آپدیت",
        "updates.mode_auto": "خودکار (مستقیم ← تونل‌ها و پروکسی‌های فعال سرور)",
        "updates.mode_direct": "فقط اینترنت مستقیم (بدون تونل)",
        "updates.mode_iface": "اینترفیس تونل فعال روی سرور (L3)",
        "updates.mode_proxy": "پروکسی لوکال یا سفارشی (SOCKS5 / HTTP)",
        "updates.mode_mirror": "آدرس آینه (GitHub Mirror)",
        "updates.iface_label": "انتخاب اینترفیس تونل فعال",
        "updates.iface_empty": "هیچ اینترفیس تونل فعالی روی سرور شناسایی نشد",
        "updates.proxy_label": "آدرس پروکسی (SOCKS5h / HTTP)",
        "updates.proxy_detected": "پروکسی‌های لوکال شناسایی‌شده",
        "updates.mirror_label": "آدرس پایه آینه یا مخزن",
        "updates.auto_hint": "ابتدا اتصال مستقیم به گیت‌هاب تست می‌شود؛ در صورت قطع یا محدودیت، به صورت خودکار از پروکسی‌های لوکال و تونل‌های UP سرور (با مسیر موقت ایزوله) برای آپدیت استفاده می‌کند.",
        "updates.via_prefix": "مسیر فعال: {label}",
        "updates.detected_summary": "{tunnels} تونل UP · {proxies} پروکسی لوکال آماده",

        // Section 6: Logs & Probes
        "logs.title": "لاگ‌های زنده پروب و تغییر مسیر",
        "logs.desc": "خط زمانی زنده بررسی سلامت سوکت‌ها، تغییر اولویت‌ها و تحریک فیل‌اور.",
        "logs.copy": "کپی لاگ‌ها",
        "logs.clear": "پاکسازی لاگ",
        "logs.live_active": "دریافت زنده فعال است",
        "logs.live_paused": "دریافت زنده متوقف شد",
        "logs.filter_placeholder": "فیلتر لاگ‌ها بر اساس پورت، آی‌پی یا رویداد...",

        // Modals: Rule Modal
        "modal.rule_title_configure": "پیکربندی قانون پورت",
        "modal.rule_title_add": "افزودن قانون فوروارد پورت",
        "modal.inbound_port": "پورت ورودی",
        "modal.port_placeholder": "443، 1000-20000 یا != 22",
        "modal.range_hint_nft_only": "حالت رنج ۱:۱ در NFTables",
        "modal.dest_port_range_placeholder": "رنج یکسان یا تک‌پورت",
        "modal.excluded_ports": "پورت‌های استثناء",
        "modal.excluded_ports_opt": "(اختیاری · فقط NFTables)",
        "modal.excluded_placeholder": "+ پورت",
        "modal.tunnel_iface": "اینترفیس خروجی",
        "modal.tunnel_iface_auto": "خودکار (مسیر کرنل)",
        "modal.tunnel_iface_auto_tag": "خودکار",
        "modal.ingress_iface": "اینترفیس تونل ورودی",
        "modal.ingress_iface_auto": "خودکار (غیر WAN)",
        "modal.spoof_ip": "آی‌پی ایران (Spoof IP)",
        "modal.spoof_ip_opt": "آی‌پی ورودی (اختیاری)",
        "modal.spoof_ip_iran_opt": "آی‌پی عمومی ایران (اختیاری)",
        "modal.suggested_ip": "پیشنهادی:",
        "modal.suggested": "پیشنهادی",
        "modal.snat_ip": "آی‌پی SNAT واسط",
        "modal.proto": "پروتکل",
        "modal.proto_both": "TCP + UDP",
        "modal.proto_tcp": "فقط TCP",
        "modal.proto_udp": "فقط UDP",
        "modal.category": "دسته‌بندی",
        "modal.category_opt": "(اختیاری)",
        "modal.category_placeholder": "مثال: تونل تهران، ویژه",
        "modal.failover_chain": "زنجیره اولویت فیل‌اور",
        "modal.failover_chain_sub": "انتقال خودکار از اولویت ۱ به ۲، ۳ هنگام اختلال",
        "modal.add_priority": "افزودن اولویت جدید",
        "modal.dest_type": "نوع مقصد",
        "modal.dest_target": "آدرس میزبان",
        "modal.dest_port": "پورت",
        "modal.proxy_proto": "ارسال هدر PROXY Protocol v2",
        "modal.is_relay": "رله میانی (پینگ گام اول)",
        "modal.primary_path": "مسیر اصلی",
        "modal.backup_path": "مسیر پشتیبان",
        "modal.comment_label": "برچسب",
        "modal.comment_placeholder": "مثال: سرور خارج ۱",
        "modal.test_target": "تست مقصد",
        "modal.mid_server": "سرور میانی",
        "modal.send_proxy_v2": "PROXY v2",
        "modal.drag_hint": "برای تغییر ترتیب اولویت بکشید",
        "modal.tip_inbound_port": "تک‌پورت (443)، رنج ۱:۱ در NFTables (مثل 10000-20000؛ هر پورت به همان پورت یا یک پورت ثابت مقصد فوروارد می‌شود) یا != 22,443.",
        "modal.tip_excluded_ports": "اختیاری (فقط NFTables). پورت‌های SSH و پنل خودکار محافظت می‌شوند. مثال: 22, 443, 1001",
        "modal.tip_category": "نام گروه اختیاری برای دسته‌بندی پورت‌ها با خط جداکننده. مثال: تونل تهران، ویژه",
        "modal.tip_failover_chain": "ترافیک به ترتیب از اولویت ۱ به ۲ و ۳ منتقل می‌شود. کارت‌ها را برای تغییر ترتیب بکشید.",
        "modal.tip_outbound_iface": "اختیاری (NFTables). محدود کردن پروب و مسیریابی به یک تانل یا اینترفیس مشخص.",
        "modal.tip_ingress_iface": "اینترفیس تونلی که پکت‌ها از سرور ایران وارد آن می‌شوند (مثل esp-link، gre15 یا ipip1). در حالت DSR Direct الزامی و در DSR Relay اختیاری است.",
        "modal.tip_spoof_ip": "آی‌پی عمومی سرور ایران که روی بسته‌های برگشتی استفاده می‌شود (در حالت DSR Relay و DSR Direct الزامی؛ در DSR ایران و SYN-ACK در صورت خالی بودن از WAN تشخیص داده می‌شود).",
        "modal.tip_snat_ip": "اختیاری (DSR Relay). آی‌پی عمومی کارت شبکه این سرور واسط برای SNAT به سمت سرورهای خارج. در صورت خالی بودن خودکار تشخیص داده می‌شود.",
        "modal.tip_comment": "یادداشت اختیاری برای این مسیر. مثال: سرور خارج ۱ - IPv6",
        "modal.tip_proxy_v2": "ارسال هدر PROXY Protocol v2. فقط در صورت فعال‌بودن روی سرور مقصد (مثل Xray acceptProxyProtocol) تیک بزنید.",
        "modal.tip_mid_server": "نود میانی: تا زمانی که اولویت ۱ سالم است و زیر 150ms پینگ دارد، روی اولویت ۱ قفل می‌ماند.",
        "modal.target_outside_tunnel": "آی‌پی تانل سرور خارج",
        "modal.target_local_tunnel": "آی‌پی تانل همین سرور",
        "modal.port_tunnel_relay": "پورت تانل",
        "modal.port_tunnel_listen": "پورت شنود تانل",
        "modal.exit_relay_title": "انتقال به سرور سوم خروجی (اختیاری · سناریوی ۳ سروره)",
        "modal.exit_relay_sub": "اگر Xray/3x-ui روی همین سرور است خالی بگذارید. اگر پنل روی سرور سوم (مثلاً آلمان) است آی‌پی و پورت آن را وارد کنید.",
        "modal.exit_target": "آی‌پی سرور خروجی",
        "modal.exit_port": "پورت خروجی",
        "modal.tip_exit_relay": "XForwarder به‌صورت خودکار روی آی‌پی و پورت تانل همین سرور گوش می‌دهد و ترافیک را با HAProxy به سرور سوم منتقل می‌کند.",
        "modal.dsr_flow_label": "پیش‌نمایش مسیر ترافیک",
        "modal.dsr_mode_synack": "بایپس SYN-ACK",
        "modal.dsr_mode_direct_3hop": "رله ۳ سروره",
        "modal.dsr_mode_direct_local": "سرویس محلی",
        "modal.dsr_direct_outside": "دانلود مستقیم از سرور خارج",
        "modal.dsr_conflict_msg": "پورت {port} روی آی‌پی {target} قبلاً توسط رول :{rule} استفاده شده است. در حالت DSR بدون کانترک هر رول باید پورت پشتِ تانل یکتایی داشته باشد.",
        "modal.dsr_use_port": "استفاده از :{port}",
        "modal.lb_toggle": "توزیع بار (LB)",
        "modal.lb_mode_label": "الگوریتم توزیع ترافیک",
        "modal.lb_equalize": "توزیع مساوی",
        "modal.lb_add_target": "افزودن آی‌پی مقصد",
        "modal.lb_weight_label": "وزن",
        "modal.lb_algo_ip_hash": "چسبندگی IP کاربر (IP Hash)",
        "modal.lb_algo_least_conn": "کمترین اتصال (Least Conn)",
        "modal.lb_algo_round_robin": "چرخشی (Round-Robin)",
        "modal.lb_algo_random": "تصادفی (Random)",
        "modal.lb_hint_ip_hash": "چسبنده به IP کاربر — پیشنهادی برای VPN، Xray، Reality و WireGuard تا اتصال کاربران وسط کار بین سرورها نپرد.",
        "modal.lb_hint_least_conn": "هر اتصال جدید را به سروری با کمترین کانکشن فعال (با لحاظ وزن) می‌فرستد. مناسب برای بارهای نامتقارن.",
        "modal.lb_hint_round_robin": "اتصالات جدید را به نوبت و متناسب با وزن بین سرورهای سالم پخش می‌کند.",
        "modal.lb_hint_random": "برای هر اتصال جدید به‌صورت تصادفی و متناسب با وزن یک سرور سالم انتخاب می‌کند.",
        "modal.lb_nft_family_note": "در NFTables تمام آی‌پی‌های استخر باید هم‌خانواده باشند (همه IPv4 یا همه IPv6). نودهای قطع‌شده خودکار کنار گذاشته می‌شوند.",
        "modal.lb_nginx_note": "انجین‌اکس نودهای خطادار TCP را فوری رد می‌کند و موتور پایش هر ۱۵ ثانیه نودهای قطع‌شده را خودکار حذف/برمی‌گرداند.",
        "modal.tip_lb_toggle": "ترافیک این اولویت را بین چند آی‌پی مقصد پخش می‌کند. نودهای قطع‌شده به‌صورت خودکار تا زمان رفع مشکل از استخر حذف می‌شوند.",
        "modal.tip_lb_mode": "روش پخش ترافیک را انتخاب کنید: «چسبندگی IP کاربر» هر کاربر را ثابت روی یک سرور نگه می‌دارد (بهترین برای VPN/Xray/WireGuard)؛ «کمترین اتصال» (Nginx) به خلوت‌ترین سرور می‌فرستد؛ «چرخشی» و «تصادفی» اتصالات جدید را بر اساس وزن پخش می‌کنند.",
        "modal.tip_lb_weight": "نسبت سهم ترافیک هر سرور (۱ تا ۱۰۰). مثال: وزن ۲ و ۱ حدود ۶۷٪ ترافیک را به سرور اول و ۳۳٪ را به سرور دوم می‌فرستد.",
        "modal.cancel": "انصراف",
        "modal.save_rule": "ذخیره و اعمال تغییرات",

        // Modals: Import Config
        "import.title": "درون‌ریزی تنظیمات",
        "import.sub": "آپلود یا جای‌گذاری فایل JSON پشتیبان XForwarder",
        "import.mode": "حالت درون‌ریزی",
        "import.merge_title": "ترکیب (پیشنهادی)",
        "import.merge_desc": "قوانین جدید را اضافه و به‌روزرسانی می‌کند و قوانین فعلی را حفظ می‌نماید.",
        "import.replace_title": "جایگزینی تمام قوانین",
        "import.replace_desc": "تمام قوانین را جایگزین می‌کند. اطلاعات کاربری و پورت پنل دست‌نخورده باقی می‌ماند.",
        "import.paste_label": "کد JSON تنظیمات",
        "import.btn_paste": "جای‌گذاری",
        "import.btn_format": "مرتب‌سازی",
        "import.btn_clear": "پاکسازی",
        "import.drop_text": "فایل JSON پشتیبان را اینجا بکشید یا کلیک کنید",
        "import.or_file": "یا درون‌ریزی از فایل",
        "import.apply": "درون‌ریزی و اعمال",

        // Modals: Traffic Modal
        "traffic_modal.title": "تحلیل ترافیک و مصرف پهنای باند",
        "traffic_modal.sub": "محاسبه دقیق لحظه‌ای پهنای باند روی پورت‌ها و تونل‌ها",
        "traffic_modal.target": "هدف:",
        "traffic_modal.all_ports_tunnels": "تمامی پورت‌ها و تونل‌ها",
        "traffic_modal.forwarded_ports": "پورت‌های فوروارد شده",
        "traffic_modal.methods_tunnels": "روش‌های فورواردینگ و انواع تونل",
        "traffic_modal.tunnel_ifaces": "اینترفیس‌های تونل",
        "traffic_modal.billing_cycle": "دوره جاری",
        "traffic_modal.active_since": "فعال از:",
        "traffic_modal.reset": "ریست دوره",
        "traffic_modal.outbound_tx": "دانلود (TX)",
        "traffic_modal.outbound_badge": "↓ خروجی",
        "traffic_modal.outbound_meta": "ارسال‌شده به کاربران / سرورها",
        "traffic_modal.inbound_rx": "آپلود (RX)",
        "traffic_modal.inbound_badge": "↑ ورودی",
        "traffic_modal.inbound_meta": "دریافت‌شده از کاربران",
        "traffic_modal.total_bandwidth": "مجموع پهنای باند",
        "traffic_modal.combined_badge": "مجموع",
        "traffic_modal.period_meta": "در بازه انتخابی",
        "traffic_modal.breakdown_title": "تفکیک بر اساس مسیر و اینترفیس تونل",
        "traffic_modal.breakdown_sub": "سهم هر روش رله از کل ترافیک",
        "traffic_modal.chart_title": "نمودار زمانی مصرف پهنای باند",
        "traffic_modal.table_title": "گزارش تفصیلی رکوردها",
        "traffic_modal.col_period": "بازه / زمان",
        "traffic_modal.col_rx": "آپلود (ورودی)",
        "traffic_modal.col_tx": "دانلود (خروجی)",
        "traffic_modal.col_total": "مصرف کل",
        "traffic_modal.col_share": "سهم درصد",
        "traffic_modal.wipe_history": "حذف کامل سوابق",
        "traffic_modal.close": "بستن",

        // Modals: Switch Decision Logs
        "switch_logs.title": "لاگ‌های تصمیم‌گیری جابجایی مسیر",
        "switch_logs.sub": "ثبت مستند رخدادهای تغییر مسیر خودکار و دلایل آن",
        "switch_logs.filter": "فیلتر قانون:",
        "switch_logs.all_rules": "تمامی پورت‌ها",
        "switch_logs.showing_recent": "نمایش آخرین رویدادهای جابجایی",
        "switch_logs.copy": "کپی لاگ‌ها",
        "switch_logs.close": "بستن",

        // Modals: System Update
        "update_modal.title": "ارتقا و به‌روزرسانی سیستم XForwarder",
        "update_modal.sub": "دریافت آخرین نسخه از گیت‌هاب، ارتقای ساختار داده و راه‌اندازی مجدد سرویس‌ها",
        "update_modal.ready_title": "آماده ارتقا",
        "update_modal.ready_sub": "عملیات ارتقا در یک تسک مستقل سیستمی اجرا خواهد شد.",
        "update_modal.step1": "دریافت آخرین کامیت‌ها از مخزن PouryaDe/XForwarder",
        "update_modal.step2": "پشتیبان‌گیری خودکار از config.json قبل از اعمال تغییرات",
        "update_modal.step3": "اجرای یکسان‌سازی خودکار ساختار داده (migrate_and_normalize_config)",
        "update_modal.step4": "راه‌اندازی مجدد بدون قطعی موتور فیل‌اور و داشبورد وب",
        "update_modal.step5": "داشبورد به طور خودکار پس از اتمام متصل و رفرش خواهد شد",
        "update_modal.start_btn": "شروع ارتقا اکنون",
        "update_modal.cancel": "انصراف",

        // Confirm & Sync Dialogs
        "confirm.delete_title": "آیا از حذف این قانون مطمئن هستید؟",
        "confirm.delete_msg": "با حذف این قانون فوروارد، مسیریابی روی این پورت بلافاصله متوقف خواهد شد.",
        "confirm.delete_rule_msg": "آیا از حذف قانون فوروارد «{id}» مطمئن هستید؟ مسیریابی روی این پورت بلافاصله متوقف خواهد شد.",
        "confirm.cancel": "انصراف",
        "confirm.delete_btn": "حذف قانون",
        "confirm.confirm_btn": "تأیید",
        "confirm.restart_btn": "راه‌اندازی مجدد سرویس",
        "confirm.reload_btn": "بارگذاری مجدد سرویس",
        "confirm.sync_btn": "همگام‌سازی جدول",
        "confirm.reset_btn": "ریست شمارنده",
        "confirm.wipe_btn": "حذف کامل سوابق",
        "confirm.restart_svc_title": "راه‌اندازی مجدد {service}؟",
        "confirm.reload_svc_title": "بارگذاری مجدد {service}؟",
        "confirm.sync_svc_title": "همگام‌سازی {service}؟",
        "confirm.restart_all_msg": "آیا از راه‌اندازی مجدد {service} مطمئن هستید؟ داشبورد وب به طور موقت قطع شده و طی حدود ۲ ثانیه به صورت خودکار متصل خواهد شد.",
        "confirm.restart_svc_msg": "آیا از راه‌اندازی مجدد {service} مطمئن هستید؟ تنظیمات مجدداً همگام‌سازی شده و سرویس از نو راه‌اندازی خواهد شد.",
        "confirm.reload_svc_msg": "آیا از بارگذاری/راه‌اندازی مجدد {service} مطمئن هستید؟ اتصالات فعال کاربران حفظ خواهد شد.",
        "sync_error.title": "پیام همگام‌سازی سرور",
        "sync_error.msg": "تنظیمات ذخیره شد، اما در اجرای دستورات سرور خطایی گزارش گردید:",
        "sync_error.dismiss": "بستن",
        "sync_error.retry": "تلاش مجدد همگام‌سازی",

        // General Status & Verbs
        "status.healthy": "سالم",
        "status.down": "قطع",
        "status.degraded": "ناپایدار",
        "status.standby": "آماده‌باش",
        "status.critical": "بحرانی",
        "status.off": "غیرفعال",
        "status.active": "فعال",
        "status.inactive": "غیرفعال",
        "status.failover": "پشتیبان",
        "status.checking": "در حال بررسی...",
        "status.installed": "نصب شده",
        "status.not_installed": "نصب نشده",
        "status.not_installed_caps": "نصب نشده",
        "status.running": "در حال اجرا",
        "status.active_running": "فعال و در حال اجرا",
        "status.standby_stopped": "آماده‌باش (متوقف)",
        "status.active_synced": "فعال و همگام",
        "status.table_idle": "فعال (جدول بیکار)",
        "status.table_loaded": "فعال و جدول بارگذاری‌شده",
        "status.probing": "در حال بررسی...",
        "status.reachable": "در دسترس",
        "status.unreachable": "خارج از دسترس",
        "status.enter_target": "آدرس مقصد را وارد کنید",
        "status.enter_port": "پورت را وارد کنید",
        "status.ipv6_required": "برای HAProxy آدرس IPv6 الزامی است",
        "status.network_error": "خطای شبکه",
        "status.ready_caps": "آماده",
        "status.optimal": "بهینه",
        "status.normal": "عادی",
        "status.elevated": "بالا",
        "status.heavy": "سنگین",
        "status.synced": "همگام",
        "common.edit": "ویرایش",
        "common.delete": "حذف",
        "common.test": "تست",
        "common.testing": "در حال تست...",
        "common.copied": "در کلیپ‌بورد کپی شد!",
        "common.copy_fail": "کپی در کلیپ‌بورد ناموفق بود",
        "theme.light": "حالت روشن",
        "theme.dark": "حالت تاریک"
    }
};

export const DEFAULT_LANG = "en";

let currentLanguage = DEFAULT_LANG;
const languageChangeListeners = [];

/**
 * Retrieves the currently active language code ('en' or 'fa').
 * Reads from localStorage when available, defaulting to 'en'.
 * @returns {string} The active two-letter language code.
 */
export function getCurrentLang() {
    try {
        const saved = localStorage.getItem("xfwd_lang");
        if (saved === "fa" || saved === "en") {
            currentLanguage = saved;
        }
    } catch (_) {}
    return currentLanguage;
}

/**
 * Translates a key according to the active language with fallback to English.
 * Supports placeholder token replacement (e.g. {count}, {sec}).
 * Uses a functional replacer to prevent regex replacement pattern injection ($&, $$, etc.).
 *
 * @param {string} key - Translation dictionary key.
 * @param {Object<string, string|number>} [params={}] - Key-value map for dynamic token substitution.
 * @param {string} [fallback=""] - Fallback string if key is not found in either dictionary.
 * @returns {string} Translated and formatted text.
 */
export function t(key, params = {}, fallback = "") {
    const lang = getCurrentLang();
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
    let str = dict[key];
    if (str === undefined) {
        str = TRANSLATIONS.en[key];
    }
    if (str === undefined) {
        str = fallback || key;
    }

    if (typeof str === "string" && params && typeof params === "object") {
        Object.keys(params).forEach(pKey => {
            const escapedKey = pKey.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            str = str.replace(new RegExp(`\\{${escapedKey}\\}`, "g"), () => String(params[pKey]));
        });
    }
    return str;
}

/**
 * Sets the active application language, updates DOM attributes, and notifies subscribers.
 * Automatically toggles the `dir` attribute on <html> ('rtl' for 'fa', 'ltr' for 'en').
 *
 * @param {string} lang - Target language ('en' or 'fa').
 */
export function setLanguage(lang) {
    if (lang !== "fa" && lang !== "en") lang = "en";
    currentLanguage = lang;
    try {
        localStorage.setItem("xfwd_lang", lang);
    } catch (_) {}

    const isRtl = (lang === "fa");
    if (typeof document !== "undefined" && document.documentElement) {
        document.documentElement.setAttribute("lang", lang);
        document.documentElement.setAttribute("dir", isRtl ? "rtl" : "ltr");
    }

    applyI18nToDOM();
    updateLangToggleUI();

    // Notify registered callback listeners
    for (const listener of languageChangeListeners) {
        try {
            listener(lang);
        } catch (err) {
            console.warn("Language change listener error:", err);
        }
    }

    // Dispatch DOM event for custom integrations
    try {
        window.dispatchEvent(new CustomEvent("xfwd:langchange", { detail: { lang } }));
    } catch (_) {}
}

/**
 * Toggles the application language between English and Persian.
 *
 * @param {Event} [e] - Optional DOM event to prevent default link/button action.
 */
export function toggleLanguage(e) {
    if (e && typeof e.preventDefault === "function") {
        e.preventDefault();
    }
    const current = getCurrentLang();
    const next = current === "fa" ? "en" : "fa";
    setLanguage(next);
}

/**
 * Subscribes a listener callback to language change events.
 *
 * @param {function(string): void} cb - Callback invoked with the new language code.
 */
export function onLanguageChanged(cb) {
    if (typeof cb === "function") {
        languageChangeListeners.push(cb);
    }
}

/**
 * Scans the DOM and applies translations to all elements with data-i18n attributes.
 * Updates text content, placeholders, titles, and optgroup labels.
 * Enforces textContent assignment for security against DOM-based XSS.
 */
export function applyI18nToDOM() {
    if (typeof document === "undefined") return;
    const lang = getCurrentLang();

    // 1. Text elements [data-i18n]
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (key) {
            el.textContent = t(key);
        }
    });

    // 2. Placeholders [data-i18n-placeholder]
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (key) {
            el.placeholder = t(key);
        }
    });

    // 3. Titles [data-i18n-title]
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
        const key = el.getAttribute("data-i18n-title");
        if (key) {
            el.title = t(key);
        }
    });

    // 4. Optgroup Labels [data-i18n-label]
    document.querySelectorAll("[data-i18n-label]").forEach(el => {
        const key = el.getAttribute("data-i18n-label");
        if (key) {
            el.label = t(key);
        }
    });

    // 5. Hover Info Tooltips [data-i18n-tip]
    document.querySelectorAll("[data-i18n-tip]").forEach(el => {
        const key = el.getAttribute("data-i18n-tip");
        if (key) {
            el.setAttribute("data-tip", t(key));
        }
    });
}

/**
 * Synchronizes language toggle button labels and hover titles across all views.
 */
export function updateLangToggleUI() {
    const lang = getCurrentLang();
    const isFa = (lang === "fa");
    const nextShortLabel = isFa ? "EN" : "FA";
    const nextLoginLabel = isFa ? "English" : "فارسی";
    const nextTitle = isFa ? "Switch to English" : "تغییر زبان به فارسی";

    const sidebarLang = document.getElementById("sidebarLangLabel");
    if (sidebarLang) sidebarLang.textContent = nextShortLabel;

    const loginLang = document.getElementById("loginLangName");
    if (loginLang) loginLang.textContent = nextLoginLabel;

    const btnSidebarLang = document.getElementById("btnSidebarLangToggle");
    if (btnSidebarLang) btnSidebarLang.title = nextTitle;

    const btnLoginLang = document.getElementById("btnLoginLangToggle");
    if (btnLoginLang) btnLoginLang.title = nextTitle;

    // Update Theme Toggle button labels concisely as Light / Dark
    const isDark = (document.documentElement.getAttribute("data-theme") === "dark");
    const themeLabels = document.querySelectorAll(".theme-toggle-label");
    const themeLabelText = isDark ? "Light" : "Dark";
    themeLabels.forEach(el => { el.textContent = themeLabelText; });

    const btnTheme = document.getElementById("btnThemeToggle");
    if (btnTheme) {
        btnTheme.title = isFa
            ? (isDark ? "تغییر به حالت روشن" : "تغییر به حالت تاریک")
            : (isDark ? "Switch to Light Mode" : "Switch to Dark Mode");
    }
}

/**
 * Initializes the internationalization subsystem on application startup.
 * Attaches click handlers to language toggle buttons and performs initial DOM translation.
 *
 * @param {function(string): void} [onLangChangeCallback] - Optional callback to re-render dynamic views.
 */
export function initI18n(onLangChangeCallback) {
    const saved = getCurrentLang();
    setLanguage(saved);

    if (onLangChangeCallback) {
        onLanguageChanged(onLangChangeCallback);
    }

    const btnSidebarLang = document.getElementById("btnSidebarLangToggle");
    if (btnSidebarLang) {
        btnSidebarLang.onclick = (e) => toggleLanguage(e);
    }

    const btnLoginLang = document.getElementById("btnLoginLangToggle");
    if (btnLoginLang) {
        btnLoginLang.onclick = (e) => toggleLanguage(e);
    }

    updateLangToggleUI();
}

if (typeof window !== "undefined") {
    window.toggleLanguage = toggleLanguage;
    window.setLanguage = setLanguage;
    window.t = t;
    window.getCurrentLang = getCurrentLang;
}

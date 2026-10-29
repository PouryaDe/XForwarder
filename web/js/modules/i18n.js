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

        // Navigation & Sidebar
        "nav.main": "MAIN NAVIGATION",
        "nav.rules": "Port Matrix",
        "nav.overview": "Overview & Health",
        "nav.services": "Relay Services",
        "nav.security": "Security & Access",
        "nav.logs": "Logs & Probes",
        "nav.breadcrumb_root": "Dashboard",
        "topbar.logout": "Logout",
        "user.admin": "Administrator",
        "user.role": "Administrator",

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
        "rules.sort_port_asc": "Sort: Port (Low → High)",
        "rules.sort_port_desc": "Sort: Port (High → Low)",
        "rules.sort_date_desc": "Sort: Newest Added",
        "rules.sort_date_asc": "Sort: Oldest Added",
        "rules.sort_status": "Sort: Status / Health",
        "rules.sort_category": "Sort: Category (A → Z)",
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

        // Section 2: Overview & Health
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
        "services.reload_haproxy": "Reload HAProxy",
        "services.nftables_title": "NFTables Kernel DNAT",
        "services.nftables_sub": "Layer-3 Kernel Tunnel Forwarding",
        "services.nftables_desc": "High-speed kernel DNAT over GRE, IPIP, FakeTCP, or AmneziaWG tunnels. Zero interference with system firewall.",
        "services.isolated_tables": "Isolated Tables",
        "services.kernel_status": "Kernel Status",
        "services.flush_safety": "Flush Safety",
        "services.flush_safety_val": "Never executes flush ruleset",
        "services.sync_nftables": "Sync NFTables Table",
        "services.nginx_title": "Nginx Stream Proxy Engine",
        "services.nginx_sub": "Layer-4 High-Throughput Stream Forwarder",
        "services.nginx_desc": "High-concurrency stream TCP/UDP proxy with epoll multi-accept architecture. Managed dynamically by XForwarder.",
        "services.reload_nginx": "Reload Nginx",
        "services.discovery_title": "Pre-existing Relay Rules Discovery",
        "services.discovery_sub": "Auto-discover and import active HAProxy & NFTables rules into XForwarder",
        "services.scan_server": "Scan Server",
        "services.discovery_desc": "If this server was previously configured with HAProxy or active NFTables/iptables DNAT forwarding rules, XForwarder can automatically detect them, extract inbound ports, backends, and protocols, backup legacy tables, and import them with zero port collisions.",
        "services.scan_prompt": "Click \"Scan Server\" to check for unmanaged HAProxy and NFTables forwarding rules.",

        // Section 4: Security & Access
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

        // Section 5: Logs & Probes
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
        "modal.inbound_port": "Inbound Listening Port",
        "modal.port_placeholder": "e.g. 2023",
        "modal.proto": "Transport Protocol",
        "modal.proto_both": "TCP + UDP (Recommended)",
        "modal.proto_tcp": "TCP Only",
        "modal.proto_udp": "UDP Only",
        "modal.category": "Category / Group",
        "modal.category_opt": "(Optional - for grouping ports with divider lines)",
        "modal.category_placeholder": "e.g. Tehran Tunnels, VIP Users, Games (leave empty for none)",
        "modal.failover_chain": "Failover Priority Chain",
        "modal.failover_chain_sub": "Traffic cascades in order from Priority 1 to 2, 3, etc. on failure",
        "modal.add_priority": "+ Add Another Failover Priority",
        "modal.dest_type": "Destination Type",
        "modal.dest_target": "Target Host / IP",
        "modal.dest_port": "Target Port",
        "modal.proxy_proto": "Send PROXY v2 Header",
        "modal.is_relay": "Intermediate Relay (Hop 1 Ping)",
        "modal.primary_path": "Primary Path",
        "modal.backup_path": "Backup Path",
        "modal.comment_label": "Comment / Label",
        "modal.test_target": "Test Target",
        "modal.mid_server": "Mid Server",
        "modal.send_proxy_v2": "Send PROXY Protocol v2 (Advanced)",
        "modal.drag_hint": "Drag to reorder priority",
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
        "confirm.cancel": "Cancel",
        "confirm.delete_btn": "Delete Rule",
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
        "theme.light": "Light Mode",
        "theme.dark": "Dark Mode"
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

        // Navigation & Sidebar
        "nav.main": "ناوبری اصلی",
        "nav.rules": "ماتریس پورت‌ها",
        "nav.overview": "نمای کلی و سلامت",
        "nav.services": "سرویس‌های رله",
        "nav.security": "امنیت و دسترسی",
        "nav.logs": "لاگ‌ها و پروب‌ها",
        "nav.breadcrumb_root": "داشبورد",
        "topbar.logout": "خروج",
        "user.admin": "مدیر سیستم",
        "user.role": "مدیر سیستم",

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
        "rules.sort_port_asc": "مرتب‌سازی: شماره پورت (صعودی)",
        "rules.sort_port_desc": "مرتب‌سازی: شماره پورت (نزولی)",
        "rules.sort_date_desc": "مرتب‌سازی: جدیدترین",
        "rules.sort_date_asc": "مرتب‌سازی: قدیمی‌ترین",
        "rules.sort_status": "مرتب‌سازی: وضعیت سلامت",
        "rules.sort_category": "مرتب‌سازی: دسته‌بندی (الف - ی)",
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

        // Section 2: Overview & Health
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
        "services.reload_haproxy": "بارگذاری مجدد HAProxy",
        "services.nftables_title": "دی‌نت هسته NFTables",
        "services.nftables_sub": "فورواردینگ لایه ۳ تونل در سطح هسته",
        "services.nftables_desc": "فورواردینگ پرسرعت روی تونل‌های GRE، IPIP، FakeTCP یا AmneziaWG بدون تداخل با فایروال سیستم.",
        "services.isolated_tables": "جدول ایزوله",
        "services.kernel_status": "وضعیت هسته",
        "services.flush_safety": "ایمنی دستورات",
        "services.flush_safety_val": "هرگز دستور حذف کل قوانین فایروال اجرا نمی‌شود",
        "services.sync_nftables": "همگام‌سازی جدول NFTables",
        "services.nginx_title": "موتور پروکسی جریان Nginx",
        "services.nginx_sub": "فورواردینگ با کارایی بالا در لایه ۴",
        "services.nginx_desc": "پروکسی همزمان TCP/UDP با معماری چندگانه epoll، مدیریت‌شده به صورت پویا توسط XForwarder.",
        "services.reload_nginx": "بارگذاری مجدد Nginx",
        "services.discovery_title": "شناسایی قوانین رله از پیش موجود",
        "services.discovery_sub": "شناسایی خودکار و درون‌ریزی قوانین فعال HAProxy و NFTables در XForwarder",
        "services.scan_server": "اسکن سرور",
        "services.discovery_desc": "اگر این سرور قبلاً دارای قوانین HAProxy یا DNAT بوده، این ابزار می‌تواند بدون تداخل پورت‌ها آن‌ها را شناسایی و درون‌ریزی کند.",
        "services.scan_prompt": "برای بررسی قوانین مدیریت‌نشده HAProxy و NFTables روی «اسکن سرور» کلیک کنید.",

        // Section 4: Security & Access
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

        // Section 5: Logs & Probes
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
        "modal.inbound_port": "پورت ورودی شنود",
        "modal.port_placeholder": "مثال: 2023",
        "modal.proto": "پروتکل انتقال",
        "modal.proto_both": "TCP + UDP (پیشنهادی)",
        "modal.proto_tcp": "فقط TCP",
        "modal.proto_udp": "فقط UDP",
        "modal.category": "دسته‌بندی / گروه",
        "modal.category_opt": "(اختیاری - برای گروه‌بندی پورت‌ها با خط جداکننده)",
        "modal.category_placeholder": "مثال: تونل تهران، کاربران ویژه، بازی‌ها",
        "modal.failover_chain": "زنجیره اولویت‌های فیل‌اور",
        "modal.failover_chain_sub": "ترافیک هنگام اختلال به ترتیب از اولویت ۱ به ۲، ۳ و غیره جابجا می‌شود",
        "modal.add_priority": "+ افزودن اولویت فیل‌اور جدید",
        "modal.dest_type": "نوع مقصد",
        "modal.dest_target": "میزبان / آی‌پی مقصد",
        "modal.dest_port": "پورت مقصد",
        "modal.proxy_proto": "ارسال هدر PROXY Protocol v2",
        "modal.is_relay": "رله میانی (پینگ گام اول)",
        "modal.primary_path": "مسیر اصلی",
        "modal.backup_path": "مسیر پشتیبان",
        "modal.comment_label": "یادداشت / برچسب",
        "modal.test_target": "تست مقصد",
        "modal.mid_server": "سرور میانی",
        "modal.send_proxy_v2": "ارسال پروتکل PROXY v2 (پیشرفته)",
        "modal.drag_hint": "برای تغییر ترتیب اولویت بکشید",
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
        "confirm.cancel": "انصراف",
        "confirm.delete_btn": "حذف قانون",
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

    // 5. Update dynamic titles & breadcrumbs
    const breadcrumbRoot = document.querySelector(".breadcrumb-root");
    if (breadcrumbRoot) {
        breadcrumbRoot.textContent = t("nav.breadcrumb_root");
    }

    const breadcrumbCurrent = document.getElementById("breadcrumbSection");
    if (breadcrumbCurrent) {
        const activeNav = document.querySelector(".nav-item.active[data-section]");
        if (activeNav) {
            const sec = activeNav.getAttribute("data-section");
            const navKey = `nav.${sec}`;
            breadcrumbCurrent.textContent = t(navKey);
        }
    }
}

/**
 * Synchronizes language toggle button labels and hover titles across all views.
 */
export function updateLangToggleUI() {
    const lang = getCurrentLang();
    const isFa = (lang === "fa");
    const nextLabel = isFa ? "English" : "فارسی";
    const nextTitle = isFa ? "Switch to English" : "تغییر زبان به فارسی";

    const topbarLang = document.getElementById("topbarLangName");
    if (topbarLang) topbarLang.textContent = nextLabel;

    const sidebarLang = document.getElementById("sidebarLangLabel");
    if (sidebarLang) sidebarLang.textContent = nextLabel;

    const loginLang = document.getElementById("loginLangName");
    if (loginLang) loginLang.textContent = nextLabel;

    const btnLangToggle = document.getElementById("btnLangToggle");
    if (btnLangToggle) btnLangToggle.title = nextTitle;

    const btnSidebarLang = document.getElementById("btnSidebarLangToggle");
    if (btnSidebarLang) btnSidebarLang.title = nextTitle;

    const btnLoginLang = document.getElementById("btnLoginLangToggle");
    if (btnLoginLang) btnLoginLang.title = nextTitle;
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

    const btnLangToggle = document.getElementById("btnLangToggle");
    if (btnLangToggle) {
        btnLangToggle.onclick = (e) => toggleLanguage(e);
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

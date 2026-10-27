#!/usr/bin/env bash
#
# XForwarder - Installer & CLI Controller
# Manages multi-path priority failover, HAProxy zero-tunnel relays, and NFTables tunnels.
# Features a 24/7 authenticated Web UI.
#

set -Eeuo pipefail

# Reconnect stdin to terminal if piped (e.g. curl ... | bash)
if [[ ! -t 0 && -e /dev/tty ]]; then
    exec < /dev/tty 2>/dev/null || true
fi

SCRIPT_VERSION="1.4.0"
INSTALL_DIR="/opt/xforwarder"
CONFIG_DIR="/etc/xforwarder"
CONFIG_FILE="$CONFIG_DIR/config.json"
LEGACY_CONFIG_DIR="/etc/forward-manager"
LEGACY_CONFIG_FILE="$LEGACY_CONFIG_DIR/config.json"

BIN_LINK="/usr/local/bin/xforwarder"
SHORT_LINK="/usr/local/bin/xfwd"
LEGACY_BIN_LINK="/usr/local/bin/forward-manager"
LEGACY_SHORT_LINK="/usr/local/bin/fwdman"

DAEMON_SERVICE="xforwarder"
WEB_SERVICE="xforwarder-web"

# ANSI Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

msg_info() { printf "%b[INFO]%b %s\n" "$CYAN" "$NC" "$*"; }
msg_ok()   { printf "%b[OK]%b %s\n" "$GREEN" "$NC" "$*"; }
msg_warn() { printf "%b[WARN]%b %s\n" "$YELLOW" "$NC" "$*"; }
msg_err()  { printf "%b[ERROR]%b %s\n" "$RED" "$NC" "$*" >&2; }

check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        msg_err "This command must be run as root."
        exit 1
    fi
}

detect_wan_ip() {
    local ip
    ip=$(curl -s4m 3 https://api.ipify.org || curl -s4m 3 https://icanhazip.com || echo "YOUR_SERVER_IP")
    echo "$ip"
}

detect_wan_iface() {
    local iface
    iface=$(ip -o route show default 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "dev") { print $(i + 1); exit }}')
    if [[ -z "$iface" ]]; then
        iface=$(ip -br link 2>/dev/null | awk '$1 !~ /lo|gre|ipip|tun|wg|awg/ {print $1; exit}')
    fi
    echo "${iface:-eth0}"
}

ensure_dependencies() {
    msg_info "Checking system dependencies (NFTables, HAProxy, Nginx, Python3)..."
    local pkgs=()
    command -v python3 >/dev/null 2>&1 || pkgs+=(python3)
    command -v haproxy >/dev/null 2>&1 || pkgs+=(haproxy)
    command -v nginx >/dev/null 2>&1 || pkgs+=(nginx)
    command -v nft >/dev/null 2>&1 || pkgs+=(nftables)
    command -v curl >/dev/null 2>&1 || pkgs+=(curl)
    command -v git >/dev/null 2>&1 || pkgs+=(git)

    # Ensure Layer 4 stream proxy module is installed for Nginx
    if command -v apt-get >/dev/null 2>&1; then
        dpkg -s libnginx-mod-stream >/dev/null 2>&1 || pkgs+=(libnginx-mod-stream)
    elif command -v dnf >/dev/null 2>&1; then
        rpm -q nginx-mod-stream >/dev/null 2>&1 || pkgs+=(nginx-mod-stream)
    elif command -v yum >/dev/null 2>&1; then
        rpm -q nginx-mod-stream >/dev/null 2>&1 || pkgs+=(nginx-mod-stream)
    fi

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        msg_info "Installing missing dependencies: ${pkgs[*]}..."
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update -q || true
            DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${pkgs[@]}"
        elif command -v dnf >/dev/null 2>&1; then
            dnf install -y -q "${pkgs[@]}"
        elif command -v yum >/dev/null 2>&1; then
            yum install -y -q "${pkgs[@]}"
        elif command -v pacman >/dev/null 2>&1; then
            pacman -Sy --noconfirm "${pkgs[@]}"
        elif command -v apk >/dev/null 2>&1; then
            apk add --no-cache "${pkgs[@]}"
        else
            msg_warn "Could not auto-detect package manager. Please install manually: ${pkgs[*]}"
        fi
    fi

    # Apply dynamic high-performance kernel network tuning, BBR & system limits
    tune_network

    # Disable system nftables service to prevent boot-time flush conflicts with XForwarder
    systemctl disable --now nftables >/dev/null 2>&1 || true

    # Ensure runtime and configuration directories exist
    mkdir -p /run/haproxy /run/xforwarder /etc/nginx/modules-enabled /etc/nginx/conf.d /var/log/nginx

    # Enable proxy services so they are active on system boot
    if command -v haproxy >/dev/null 2>&1; then
        systemctl enable haproxy >/dev/null 2>&1 || true
    fi
    if command -v nginx >/dev/null 2>&1; then
        systemctl enable nginx >/dev/null 2>&1 || true
    fi

    # Unlink default Nginx welcome site to prevent it from holding port 80
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf >/dev/null 2>&1 || true

    # Verification of Core Relay Dependencies
    if command -v nft >/dev/null 2>&1; then
        msg_ok "NFTables is installed and available."
    else
        msg_warn "NFTables is NOT installed. Kernel DNAT tunnel forwarding may not work."
    fi

    if command -v haproxy >/dev/null 2>&1; then
        msg_ok "HAProxy is installed and available."
    else
        msg_warn "HAProxy is NOT installed. Direct IPv6 user-space relay may not work."
    fi

    if command -v nginx >/dev/null 2>&1; then
        msg_ok "Nginx is installed and available."
    else
        msg_warn "Nginx is NOT installed. Stream proxy forwarding may not work."
    fi
}

tune_network() {
    msg_info "Applying high-performance kernel network tuning & system limits..."
    local sys_mem_mb sys_cores
    sys_mem_mb=$(awk '/MemTotal/ { printf "%.0f", $2/1024 }' /proc/meminfo 2>/dev/null || echo 1024)
    sys_cores=$(nproc 2>/dev/null || echo 1)

    local dyn_maxconn dyn_rmem_def dyn_wmem_def dyn_rmem_max dyn_wmem_max dyn_conntrack_max dyn_somaxconn
    if (( sys_mem_mb < 1000 )); then
        # Tier 1: Small VPS (< 1 GB RAM)
        dyn_maxconn=15000
        dyn_rmem_def=131072       # 128 KB
        dyn_wmem_def=131072       # 128 KB
        dyn_rmem_max=33554432     # 32 MB
        dyn_wmem_max=33554432     # 32 MB
        dyn_conntrack_max=131072
        dyn_somaxconn=32768
    elif (( sys_mem_mb < 2500 )); then
        # Tier 2: Medium VPS (1 GB - 2.5 GB RAM)
        dyn_maxconn=35000
        dyn_rmem_def=262144       # 256 KB
        dyn_wmem_def=262144       # 256 KB
        dyn_rmem_max=33554432     # 32 MB
        dyn_wmem_max=33554432     # 32 MB
        dyn_conntrack_max=262144
        dyn_somaxconn=65535
    elif (( sys_mem_mb < 4500 )); then
        # Tier 3: Large VPS (2.5 GB - 4.5 GB RAM)
        dyn_maxconn=75000
        dyn_rmem_def=262144       # 256 KB
        dyn_wmem_def=262144       # 256 KB
        dyn_rmem_max=67108864     # 64 MB
        dyn_wmem_max=67108864     # 64 MB
        dyn_conntrack_max=524288
        dyn_somaxconn=65535
    else
        # Tier 4: High-End VPS / Dedicated (> 4.5 GB RAM)
        dyn_maxconn=150000
        dyn_rmem_def=262144       # 256 KB
        dyn_wmem_def=262144       # 256 KB
        dyn_rmem_max=67108864     # 64 MB
        dyn_wmem_max=67108864     # 64 MB
        dyn_conntrack_max=1048576
        dyn_somaxconn=65535
    fi

    # Congestion Control (BBR)
    local avail bbr=0
    avail=$(sysctl -n net.ipv4.tcp_available_congestion_control 2>/dev/null || true)
    if [[ " $avail " != *" bbr "* ]]; then
        modprobe tcp_bbr >/dev/null 2>&1 || true
        avail=$(sysctl -n net.ipv4.tcp_available_congestion_control 2>/dev/null || true)
    fi
    if [[ " $avail " == *" bbr "* ]]; then
        bbr=1
        mkdir -p /etc/modules-load.d
        echo "tcp_bbr" > /etc/modules-load.d/bbr.conf 2>/dev/null || true
    fi

    local sysctl_conf="/etc/sysctl.d/99-xforwarder.conf"
    mkdir -p /etc/sysctl.d
    {
        echo "# Generated by XForwarder - Dynamic High-Performance Network Tuning"
        echo "# Detected: ${sys_mem_mb} MB RAM, ${sys_cores} CPU core(s)"
        echo "net.ipv4.ip_forward = 1"
        if (( bbr )); then
            echo "# BBR Congestion Control: maximum throughput & low latency over lossy links"
            echo "net.core.default_qdisc = fq"
            echo "net.ipv4.tcp_congestion_control = bbr"
        fi
        cat <<EOF

# Connection backlog & socket queues
net.core.somaxconn = $dyn_somaxconn
net.core.netdev_max_backlog = 16384
net.ipv4.tcp_max_syn_backlog = $dyn_somaxconn

# Ephemeral outgoing port range & rapid connection recycling
net.ipv4.ip_local_port_range = 20000 65535
net.ipv4.ip_local_reserved_ports = 80,443,2053,2083,2087,2096,8443,9000-9999
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15

# Faster handshakes, PMTU black hole mitigation, and no slow start after idle
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_base_mss = 1024
net.ipv4.tcp_slow_start_after_idle = 0

# Idle connection health checks & keepalive
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 5

# Dynamic socket buffer sizes
net.core.rmem_default = $dyn_rmem_def
net.core.wmem_default = $dyn_wmem_def
net.core.rmem_max = $dyn_rmem_max
net.core.wmem_max = $dyn_wmem_max
net.ipv4.tcp_rmem = 4096 $dyn_rmem_def $dyn_rmem_max
net.ipv4.tcp_wmem = 4096 $dyn_wmem_def $dyn_wmem_max
net.ipv4.udp_rmem_min = 16384
net.ipv4.udp_wmem_min = 16384
EOF
        local cur_files
        cur_files=$(sysctl -n fs.file-max 2>/dev/null | tr -cd '0-9' || echo 0)
        if (( ${cur_files:-0} < 2097152 )); then
            echo "fs.file-max = 2097152"
        fi
        local cur_ct
        cur_ct=$(sysctl -n net.netfilter.nf_conntrack_max 2>/dev/null | tr -cd '0-9' || true)
        if [[ -n "$cur_ct" && "$cur_ct" =~ ^[0-9]+$ ]]; then
            echo
            echo "# Connection tracking scaling"
            if (( cur_ct < dyn_conntrack_max )); then
                echo "net.netfilter.nf_conntrack_max = $dyn_conntrack_max"
            fi
            echo "net.netfilter.nf_conntrack_tcp_timeout_established = 7200"
            echo "net.netfilter.nf_conntrack_udp_timeout_stream = 60"
        fi
    } > "$sysctl_conf"

    # Apply sysctl settings safely
    sysctl -p "$sysctl_conf" >/dev/null 2>&1 || sysctl --system >/dev/null 2>&1 || true

    # Systemd LimitNOFILE override for HAProxy
    mkdir -p /etc/systemd/system/haproxy.service.d
    cat <<'EOF' > /etc/systemd/system/haproxy.service.d/override.conf
[Service]
LimitNOFILE=1048576
EOF
    systemctl daemon-reload >/dev/null 2>&1 || true

    # Golden NIC offload tuning: TSO/GSO on for low CPU proxying, GRO off to prevent GRE/IPIP tunnel drops
    if command -v ethtool >/dev/null 2>&1; then
        local def_iface
        def_iface=$(ip route show default 2>/dev/null | awk '{print $5; exit}')
        if [[ -n "$def_iface" ]]; then
            ethtool -K "$def_iface" tso on gso on gro off >/dev/null 2>&1 || true
        fi
    fi

    msg_ok "Kernel network tuning and system limits applied (Profile: ${sys_mem_mb}MB RAM, BBR=$(( bbr )))."
}

resolve_active_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        echo "$CONFIG_FILE"
    elif [[ -f "$LEGACY_CONFIG_FILE" ]]; then
        echo "$LEGACY_CONFIG_FILE"
    else
        echo "$CONFIG_FILE"
    fi
}

is_installed() {
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ -f "$active_cfg" && -f "$INSTALL_DIR/core/engine.py" && -f "$INSTALL_DIR/core/web_server.py" ]]; then
        return 0
    elif [[ -f "$active_cfg" && -f "/opt/forward-manager/core/engine.py" ]]; then
        return 0
    fi
    return 1
}

install_xforwarder() {
    check_root
    ensure_dependencies

    local script_dir
    script_dir=$(dirname "$(readlink -f "$0")")
    local cleanup_tmp=""

    if [[ ! -d "$script_dir/core" || ! -d "$script_dir/web" ]]; then
        msg_info "Remote installation detected. Fetching latest XForwarder repository..."
        local tmp_clone
        tmp_clone=$(mktemp -d /tmp/xfwd_install.XXXXXX)
        git clone --depth 1 https://github.com/PouryaDe/XForwarder.git "$tmp_clone"
        script_dir="$tmp_clone"
        cleanup_tmp="$tmp_clone"
    fi

    msg_info "Installing XForwarder into $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"

    cp -r "$script_dir/core" "$INSTALL_DIR/"
    cp -r "$script_dir/web" "$INSTALL_DIR/"
    cp "$script_dir/xforwarder.sh" "$INSTALL_DIR/xforwarder.sh"
    chmod +x "$INSTALL_DIR/xforwarder.sh" "$INSTALL_DIR/core/engine.py" "$INSTALL_DIR/core/web_server.py"

    # Persist commit metadata for in-panel version tracking
    if command -v git >/dev/null 2>&1 && git -C "$script_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$script_dir" rev-parse --short HEAD > "$INSTALL_DIR/.commit" 2>/dev/null || true
        git -C "$script_dir" log -1 --format=%cd --date=short > "$INSTALL_DIR/.commit_date" 2>/dev/null || true
        git -C "$script_dir" log -1 --format=%s > "$INSTALL_DIR/.commit_msg" 2>/dev/null || true
    fi

    # Backup pre-existing configurations to avoid data loss
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    if [[ -f /etc/haproxy/haproxy.cfg ]] && ! grep -q "Generated by XForwarder" /etc/haproxy/haproxy.cfg 2>/dev/null; then
        msg_warn "Pre-existing HAProxy configuration found! Backing up to /etc/haproxy/haproxy.cfg.bak.$timestamp..."
        cp /etc/haproxy/haproxy.cfg "/etc/haproxy/haproxy.cfg.bak.$timestamp"
    fi

    if [[ -f /etc/nginx/nginx.conf ]] && ! grep -q "Generated by XForwarder" /etc/nginx/nginx.conf 2>/dev/null; then
        msg_warn "Pre-existing Nginx configuration found! Backing up to /etc/nginx/nginx.conf.bak.$timestamp..."
        cp /etc/nginx/nginx.conf "/etc/nginx/nginx.conf.bak.$timestamp"
    fi

    # Unlink default Nginx welcome site to prevent it from holding port 80
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf >/dev/null 2>&1 || true

    # Migrate legacy config if exists
    if [[ ! -f "$CONFIG_FILE" && -f "$LEGACY_CONFIG_FILE" ]]; then
        msg_info "Migrating configuration from $LEGACY_CONFIG_FILE to $CONFIG_FILE..."
        cp "$LEGACY_CONFIG_FILE" "$CONFIG_FILE"
    fi

    # Wizard for initial configuration
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo
        printf "%b=======================================================%b\n" "$CYAN" "$NC"
        printf "%b  XForwarder Setup Wizard%b\n" "$BOLD" "$NC"
        printf "%b=======================================================%b\n\n" "$CYAN" "$NC"

        local default_iface
        default_iface=$(detect_wan_iface)
        read -r -p "WAN Interface name [$default_iface]: " user_iface
        user_iface="${user_iface:-$default_iface}"

        local default_port="8090"
        read -r -p "Web Management Port [$default_port]: " user_port
        user_port="${user_port:-$default_port}"

        local default_user="admin"
        read -r -p "Admin Username [$default_user]: " user_name
        user_name="${user_name:-$default_user}"

        local user_pass=""
        while [[ -z "$user_pass" ]]; do
            read -r -s -p "Admin Password: " user_pass
            echo
            if [[ -z "$user_pass" ]]; then
                msg_warn "Password cannot be empty. Please enter a valid password."
            fi
        done

        local default_secret="xfwd-admin"
        read -r -p "Security Secret Path (URL slug) [$default_secret]: " user_secret
        user_secret="${user_secret:-$default_secret}"
        user_secret=$(echo "$user_secret" | sed -e 's/^[ \t\/]*//' -e 's/[ \t\/]*$//')
        user_secret="${user_secret:-xfwd-admin}"

        echo
        local user_ssl_cert=""
        local user_ssl_key=""
        read -r -p "Enable SSL/TLS (HTTPS) for Web Panel? [y/N]: " ask_ssl
        if [[ "$ask_ssl" =~ ^[Yy]$ ]]; then
            while true; do
                read -r -p "SSL Certificate Path (e.g. /etc/letsencrypt/live/domain/fullchain.pem): " user_ssl_cert
                user_ssl_cert=$(echo "$user_ssl_cert" | tr -d '[:space:]')
                if [[ -z "$user_ssl_cert" ]]; then
                    msg_warn "Certificate path cannot be empty if SSL is enabled."
                    continue
                fi
                if [[ ! -f "$user_ssl_cert" ]]; then
                    msg_warn "File '$user_ssl_cert' does not exist on this server right now."
                    read -r -p "Save path anyway? [y/N]: " confirm_cert
                    if [[ "$confirm_cert" =~ ^[Yy]$ ]]; then
                        break
                    fi
                else
                    break
                fi
            done

            while true; do
                read -r -p "SSL Private Key Path (e.g. /etc/letsencrypt/live/domain/privkey.pem): " user_ssl_key
                user_ssl_key=$(echo "$user_ssl_key" | tr -d '[:space:]')
                if [[ -z "$user_ssl_key" ]]; then
                    msg_warn "Private key path cannot be empty if SSL is enabled."
                    continue
                fi
                if [[ ! -f "$user_ssl_key" ]]; then
                    msg_warn "File '$user_ssl_key' does not exist on this server right now."
                    read -r -p "Save path anyway? [y/N]: " confirm_key
                    if [[ "$confirm_key" =~ ^[Yy]$ ]]; then
                        break
                    fi
                else
                    break
                fi
            done
        fi

        local pass_hash
        pass_hash=$(python3 -c "import sys, hashlib, secrets; salt = secrets.token_hex(16); derived = hashlib.pbkdf2_hmac('sha256', sys.argv[1].encode('utf-8'), bytes.fromhex(salt), 100000).hex(); print(f'pbkdf2:sha256:100000\${salt}\${derived}')" "$user_pass")

        cat <<EOF > "$CONFIG_FILE"
{
  "wan_interface": "$user_iface",
  "check_interval_seconds": 8,
  "failure_threshold": 3,
  "recovery_threshold": 3,
  "web": {
    "bind_host": "0.0.0.0",
    "port": $user_port,
    "secret_path": "$user_secret",
    "ssl_cert": "$user_ssl_cert",
    "ssl_key": "$user_ssl_key",
    "auth": {
      "username": "$user_name",
      "password_hash": "$pass_hash"
    }
  },
  "rules": []
}
EOF
        msg_ok "Configuration initialized at $CONFIG_FILE"

        # Auto-discover and import pre-existing HAProxy & NFTables port rules if available
        python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
from core.nftables_parser import import_all_relay_rules_into_config
count, ports, logs = import_all_relay_rules_into_config('$CONFIG_FILE', deactivate_legacy=True)
if count > 0:
    print(f'\033[0;32m[OK] Auto-imported {count} pre-existing relay port rules (HAProxy/NFTables): {ports}\033[0m')
" 2>/dev/null || true
    fi

    # Install systemd service units
    cp "$script_dir/systemd/xforwarder.service" /etc/systemd/system/
    cp "$script_dir/systemd/xforwarder-web.service" /etc/systemd/system/
    systemctl daemon-reload

    # Disable old legacy services if active
    systemctl stop forward-manager.service forward-manager-web.service >/dev/null 2>&1 || true
    systemctl disable forward-manager.service forward-manager-web.service >/dev/null 2>&1 || true

    # Enable and start BOTH core daemon and web server 24/7
    systemctl enable --now "$DAEMON_SERVICE"
    systemctl enable --now "$WEB_SERVICE"
    msg_ok "XForwarder Engine & 24/7 Web Server started."

    # Symlink CLI (both xforwarder/xfwd and legacy forward-manager/fwdman)
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$BIN_LINK"
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$SHORT_LINK"
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$LEGACY_BIN_LINK"
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$LEGACY_SHORT_LINK"

    if [[ -n "$cleanup_tmp" && -d "$cleanup_tmp" ]]; then
        rm -rf "$cleanup_tmp"
    fi

    msg_ok "CLI commands installed: xforwarder and xfwd (aliases: forward-manager, fwdman)"
    show_web_access_info
}

update_xforwarder() {
    check_root
    msg_info "Starting XForwarder update & automatic migration..."

    local script_dir
    script_dir=$(dirname "$(readlink -f "$0")")
    local cleanup_tmp=""

    # If running from installed location (/opt/xforwarder) or a non-git directory, always clone fresh from GitHub
    if [[ "$script_dir" == "$INSTALL_DIR" || ! -d "$script_dir/core" || ! -d "$script_dir/web" ]] || ! (command -v git >/dev/null 2>&1 && git -C "$script_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1); then
        msg_info "Fetching latest XForwarder release from GitHub..."
        local tmp_clone
        tmp_clone=$(mktemp -d /tmp/xfwd_update.XXXXXX)
        git clone --depth 1 https://github.com/PouryaDe/XForwarder.git "$tmp_clone"
        script_dir="$tmp_clone"
        cleanup_tmp="$tmp_clone"
    else
        msg_info "Checking for remote updates via Git in $script_dir..."
        if git -C "$script_dir" remote >/dev/null 2>&1; then
            git -C "$script_dir" pull --rebase origin main >/dev/null 2>&1 || msg_warn "Could not pull updates; proceeding with current source files."
        fi
    fi

    local active_cfg
    active_cfg=$(resolve_active_config)
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    # Backup existing configuration to prevent any data loss
    if [[ -f "$active_cfg" ]]; then
        local backup_cfg="${active_cfg}.bak.${timestamp}"
        cp "$active_cfg" "$backup_cfg"
        msg_ok "Configuration safely backed up to $backup_cfg"
    fi

    # Ensure required runtime packages
    ensure_dependencies

    msg_info "Synchronizing core components to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
    cp -r "$script_dir/core" "$INSTALL_DIR/"
    cp -r "$script_dir/web" "$INSTALL_DIR/"
    cp "$script_dir/xforwarder.sh" "$INSTALL_DIR/xforwarder.sh"
    chmod +x "$INSTALL_DIR/xforwarder.sh" "$INSTALL_DIR/core/engine.py" "$INSTALL_DIR/core/web_server.py"

    # Persist commit metadata for in-panel version tracking
    if command -v git >/dev/null 2>&1 && git -C "$script_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$script_dir" rev-parse --short HEAD > "$INSTALL_DIR/.commit" 2>/dev/null || true
        git -C "$script_dir" log -1 --format=%cd --date=short > "$INSTALL_DIR/.commit_date" 2>/dev/null || true
        git -C "$script_dir" log -1 --format=%s > "$INSTALL_DIR/.commit_msg" 2>/dev/null || true
    fi

    # Migrate legacy configuration path if applicable
    if [[ ! -f "$CONFIG_FILE" && -f "$LEGACY_CONFIG_FILE" ]]; then
        msg_info "Migrating configuration file from $LEGACY_CONFIG_FILE to $CONFIG_FILE..."
        cp "$LEGACY_CONFIG_FILE" "$CONFIG_FILE"
        active_cfg="$CONFIG_FILE"
    fi

    # Unlink default Nginx welcome site to prevent it from holding port 80
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf >/dev/null 2>&1 || true

    # Execute automated Python schema migration & normalization
    if [[ -f "$active_cfg" ]]; then
        msg_info "Running schema migration on $active_cfg..."
        python3 "$INSTALL_DIR/core/engine.py" --migrate "$active_cfg"
    else
        msg_info "Initializing configuration at $CONFIG_FILE..."
        python3 "$INSTALL_DIR/core/engine.py" --migrate "$CONFIG_FILE"
        active_cfg="$CONFIG_FILE"
    fi

    # Update systemd service units
    if [[ -d "$script_dir/systemd" ]]; then
        cp "$script_dir/systemd/xforwarder.service" /etc/systemd/system/ 2>/dev/null || true
        cp "$script_dir/systemd/xforwarder-web.service" /etc/systemd/system/ 2>/dev/null || true
        systemctl daemon-reload
    fi

    # Disable old legacy services if active
    systemctl stop forward-manager.service forward-manager-web.service >/dev/null 2>&1 || true
    systemctl disable forward-manager.service forward-manager-web.service >/dev/null 2>&1 || true

    # Refresh CLI symlinks
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$BIN_LINK"
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$SHORT_LINK"
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$LEGACY_BIN_LINK"
    ln -sf "$INSTALL_DIR/xforwarder.sh" "$LEGACY_SHORT_LINK"

    if [[ -n "$cleanup_tmp" && -d "$cleanup_tmp" ]]; then
        rm -rf "$cleanup_tmp"
    fi

    # Apply latest kernel network tuning & NIC offloads automatically on update
    tune_network

    # Restart services cleanly
    msg_info "Restarting XForwarder services..."
    systemctl restart "$DAEMON_SERVICE" 2>/dev/null || true

    # Restart HAProxy so new LimitNOFILE and zero-copy splice take effect immediately
    if systemctl is-active --quiet haproxy 2>/dev/null; then
        systemctl restart haproxy 2>/dev/null || true
    fi
    if systemctl is-active --quiet nginx 2>/dev/null; then
        systemctl reload nginx 2>/dev/null || true
    fi

    # Verify active daemon status and log successful completion
    sleep 1
    if systemctl is-active --quiet "$DAEMON_SERVICE" 2>/dev/null; then
        msg_ok "XForwarder updated successfully! All services are active and running."
    else
        msg_warn "Services restarted, but status check reported a potential issue. Run: xfwd status"
    fi

    # Smoothly reload/restart web dashboard service
    if systemctl is-active --quiet "$WEB_SERVICE" 2>/dev/null; then
        systemctl restart "$WEB_SERVICE" 2>/dev/null || true
    fi

    if [[ -n "$cleanup_tmp" && -d "$cleanup_tmp" ]]; then
        rm -rf "$cleanup_tmp"
    fi

    show_web_access_info
}

change_web_port() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local current_port
    current_port=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('port', 8090))" 2>/dev/null || echo "8090")

    read -r -p "Enter new Web Management Port [$current_port]: " new_port
    new_port="${new_port:-$current_port}"

    if ! [[ "$new_port" =~ ^[0-9]+$ ]] || (( new_port < 1 || new_port > 65535 )); then
        msg_err "Invalid port number. Must be between 1 and 65535."
        return 1
    fi

    python3 - "$active_cfg" "$new_port" << 'PYEOF'
import sys, json, os

cfg_path = sys.argv[1]
port = int(sys.argv[2])

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' not in cfg:
    cfg['web'] = {}
cfg['web']['port'] = port

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "Web management port updated to $new_port. Service restarted."
    show_web_access_info
}

change_web_username() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local current_user
    current_user=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('auth', {}).get('username', 'admin'))" 2>/dev/null || echo "admin")

    read -r -p "Enter new Admin Username [$current_user]: " new_user
    new_user="${new_user:-$current_user}"
    new_user=$(echo "$new_user" | tr -d '[:space:]')

    if [[ -z "$new_user" ]]; then
        msg_err "Username cannot be empty."
        return 1
    fi

    python3 - "$active_cfg" "$new_user" << 'PYEOF'
import sys, json, os

cfg_path = sys.argv[1]
user = sys.argv[2]

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' not in cfg:
    cfg['web'] = {}
if 'auth' not in cfg['web']:
    cfg['web']['auth'] = {}
cfg['web']['auth']['username'] = user

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "Admin username updated to '$new_user'. Service restarted."
    show_web_access_info
}

change_web_password() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local new_pass=""
    while [[ -z "$new_pass" ]]; do
        read -r -s -p "Enter new Admin Password: " new_pass
        echo
        if [[ -z "$new_pass" ]]; then
            msg_warn "Password cannot be empty. Please enter a valid password."
        fi
    done

    python3 - "$active_cfg" "$new_pass" << 'PYEOF'
import sys, json, hashlib, secrets, os

cfg_path = sys.argv[1]
password = sys.argv[2]

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' not in cfg:
    cfg['web'] = {}
if 'auth' not in cfg['web']:
    cfg['web']['auth'] = {}

salt = secrets.token_hex(16)
derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000).hex()
cfg['web']['auth']['password_hash'] = f"pbkdf2:sha256:100000${salt}${derived}"

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "Admin password updated successfully. Service restarted."
}

change_web_secret_path() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local current_secret
    current_secret=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('secret_path', 'xfwd-admin'))" 2>/dev/null || echo "xfwd-admin")

    read -r -p "Enter new Security Path (e.g. xfwd-admin, secret, panel) [$current_secret]: " new_secret
    new_secret="${new_secret:-$current_secret}"
    new_secret=$(echo "$new_secret" | sed -e 's/^[ \t\/]*//' -e 's/[ \t\/]*$//')
    new_secret="${new_secret:-xfwd-admin}"

    python3 - "$active_cfg" "$new_secret" << 'PYEOF'
import sys, json, os

cfg_path = sys.argv[1]
secret = sys.argv[2].strip().strip('/')

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' not in cfg:
    cfg['web'] = {}
cfg['web']['secret_path'] = secret

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "Security path updated to '/$new_secret/'. Service restarted."
    show_web_access_info
}

change_web_ssl() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local current_cert current_key
    current_cert=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_cert', ''))" 2>/dev/null || echo "")
    current_key=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_key', ''))" 2>/dev/null || echo "")

    echo
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "%b   Configure SSL/TLS (HTTPS) for Web Panel%b\n" "$BOLD" "$NC"
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "Enter paths to your SSL certificate (fullchain.pem / cert.crt)\nand private key (privkey.pem / server.key).\n\n"

    local new_cert new_key
    while true; do
        read -r -p "SSL Certificate File Path [${current_cert:-/etc/letsencrypt/live/domain/fullchain.pem}]: " new_cert
        new_cert="${new_cert:-$current_cert}"
        new_cert=$(echo "$new_cert" | tr -d '[:space:]')
        if [[ -z "$new_cert" ]]; then
            msg_warn "Certificate path cannot be empty."
            continue
        fi
        if [[ ! -f "$new_cert" ]]; then
            msg_warn "File '$new_cert' does not exist on this server right now."
            read -r -p "Save path anyway? [y/N]: " confirm_cert
            if [[ "$confirm_cert" =~ ^[Yy]$ ]]; then
                break
            fi
        else
            break
        fi
    done

    while true; do
        read -r -p "SSL Private Key File Path [${current_key:-/etc/letsencrypt/live/domain/privkey.pem}]: " new_key
        new_key="${new_key:-$current_key}"
        new_key=$(echo "$new_key" | tr -d '[:space:]')
        if [[ -z "$new_key" ]]; then
            msg_warn "Private key path cannot be empty."
            continue
        fi
        if [[ ! -f "$new_key" ]]; then
            msg_warn "File '$new_key' does not exist on this server right now."
            read -r -p "Save path anyway? [y/N]: " confirm_key
            if [[ "$confirm_key" =~ ^[Yy]$ ]]; then
                break
            fi
        else
            break
        fi
    done

    python3 - "$active_cfg" "$new_cert" "$new_key" << 'PYEOF'
import sys, json, os

cfg_path = sys.argv[1]
cert = sys.argv[2].strip()
key = sys.argv[3].strip()

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' not in cfg:
    cfg['web'] = {}
cfg['web']['ssl_cert'] = cert
cfg['web']['ssl_key'] = key

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "SSL/TLS certificates configured successfully. Web service restarted."
    show_web_access_info
}

disable_web_ssl() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    python3 - "$active_cfg" << 'PYEOF'
import sys, json, os

cfg_path = sys.argv[1]
with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' in cfg:
    cfg['web']['ssl_cert'] = ""
    cfg['web']['ssl_key'] = ""

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "SSL/TLS disabled. Web panel reverted to HTTP."
    show_web_access_info
}

change_all_web_settings() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local current_port current_user current_secret current_cert current_key
    current_port=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('port', 8090))" 2>/dev/null || echo "8090")
    current_user=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('auth', {}).get('username', 'admin'))" 2>/dev/null || echo "admin")
    current_secret=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('secret_path', 'xfwd-admin'))" 2>/dev/null || echo "xfwd-admin")
    current_cert=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_cert', ''))" 2>/dev/null || echo "")
    current_key=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_key', ''))" 2>/dev/null || echo "")

    echo
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "%b   Web Panel Settings Wizard%b\n" "$BOLD" "$NC"
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    read -r -p "Web Management Port [$current_port]: " new_port
    new_port="${new_port:-$current_port}"
    if ! [[ "$new_port" =~ ^[0-9]+$ ]] || (( new_port < 1 || new_port > 65535 )); then
        msg_err "Invalid port number. Must be between 1 and 65535."
        return 1
    fi

    read -r -p "Admin Username [$current_user]: " new_user
    new_user="${new_user:-$current_user}"
    new_user=$(echo "$new_user" | tr -d '[:space:]')
    if [[ -z "$new_user" ]]; then
        msg_err "Username cannot be empty."
        return 1
    fi

    local new_pass=""
    while [[ -z "$new_pass" ]]; do
        read -r -s -p "Admin Password: " new_pass
        echo
        if [[ -z "$new_pass" ]]; then
            msg_warn "Password cannot be empty."
        fi
    done

    read -r -p "Security Secret Path [$current_secret]: " new_secret
    new_secret="${new_secret:-$current_secret}"
    new_secret=$(echo "$new_secret" | sed -e 's/^[ \t\/]*//' -e 's/[ \t\/]*$//')
    new_secret="${new_secret:-xfwd-admin}"

    local new_cert="$current_cert"
    local new_key="$current_key"
    echo
    read -r -p "Configure SSL/TLS (HTTPS) Certificates? [y/N]: " ask_ssl_wiz
    if [[ "$ask_ssl_wiz" =~ ^[Yy]$ ]]; then
        read -r -p "SSL Certificate Path [${current_cert}]: " input_cert
        new_cert="${input_cert:-$current_cert}"
        read -r -p "SSL Private Key Path [${current_key}]: " input_key
        new_key="${input_key:-$current_key}"
    fi

    python3 - "$active_cfg" "$new_port" "$new_user" "$new_pass" "$new_secret" "$new_cert" "$new_key" << 'PYEOF'
import sys, json, hashlib, secrets, os

cfg_path = sys.argv[1]
port = int(sys.argv[2])
user = sys.argv[3]
password = sys.argv[4]
secret = sys.argv[5].strip().strip('/')
cert = sys.argv[6].strip()
key = sys.argv[7].strip()

with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

if 'web' not in cfg:
    cfg['web'] = {}
cfg['web']['port'] = port
cfg['web']['secret_path'] = secret
cfg['web']['ssl_cert'] = cert
cfg['web']['ssl_key'] = key
if 'auth' not in cfg['web']:
    cfg['web']['auth'] = {}
cfg['web']['auth']['username'] = user

salt = secrets.token_hex(16)
derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000).hex()
cfg['web']['auth']['password_hash'] = f"pbkdf2:sha256:100000${salt}${derived}"

tmp_path = f"{cfg_path}.tmp.{os.getpid()}"
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, cfg_path)
PYEOF

    systemctl restart "$WEB_SERVICE"
    msg_ok "All Web settings updated successfully. Service restarted."
    show_web_access_info
}

modify_web_settings_menu() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration not found. Please install first."
        return 1
    fi

    local current_port current_user current_secret current_cert current_key current_ssl_status
    current_port=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('port', 8090))" 2>/dev/null || echo "8090")
    current_user=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('auth', {}).get('username', 'admin'))" 2>/dev/null || echo "admin")
    current_secret=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('secret_path', 'xfwd-admin'))" 2>/dev/null || echo "xfwd-admin")
    current_cert=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_cert', ''))" 2>/dev/null || echo "")
    current_key=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_key', ''))" 2>/dev/null || echo "")

    if [[ -n "$current_cert" && -n "$current_key" ]]; then
        current_ssl_status="Enabled (HTTPS)"
    else
        current_ssl_status="Disabled (HTTP)"
    fi

    echo
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "%b   Web Panel Settings Management%b\n" "$BOLD" "$NC"
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "  %bCurrent Port:%b          %s\n" "$BOLD" "$NC" "$current_port"
    printf "  %bCurrent Username:%b      %s\n" "$BOLD" "$NC" "$current_user"
    printf "  %bCurrent Security Path:%b /%s/\n" "$BOLD" "$NC" "${current_secret:-}"
    printf "  %bCurrent SSL/TLS:%b       %s\n" "$BOLD" "$NC" "$current_ssl_status"
    if [[ -n "$current_cert" ]]; then
        printf "  %bSSL Cert File:%b         %s\n" "$BOLD" "$NC" "$current_cert"
        printf "  %bSSL Key File:%b          %s\n" "$BOLD" "$NC" "$current_key"
    fi
    printf "%b-------------------------------------------------------%b\n" "$CYAN" "$NC"
    echo "1) Change Web Port"
    echo "2) Change Admin Username"
    echo "3) Change Admin Password"
    echo "4) Change Security Path (Secret URL Slug)"
    echo "5) Configure SSL/TLS Certificates (Enable HTTPS)"
    echo "6) Disable SSL/TLS (Revert to HTTP)"
    echo "7) Change All Web Settings (Interactive Wizard)"
    echo "0) Return to Main Menu"
    echo
    read -r -p "Select an option [0-7]: " web_choice

    case "$web_choice" in
        1) change_web_port ;;
        2) change_web_username ;;
        3) change_web_password ;;
        4) change_web_secret_path ;;
        5) change_web_ssl ;;
        6) disable_web_ssl ;;
        7) change_all_web_settings ;;
        0) return 0 ;;
        *) msg_warn "Invalid selection." ;;
    esac
}

change_password() {
    change_web_password
}

show_web_access_info() {
    local active_cfg
    active_cfg=$(resolve_active_config)
    if [[ ! -f "$active_cfg" ]]; then
        msg_err "Configuration file not found. Run: xforwarder install"
        return 1
    fi

    local port username secret_path wan_ip cert key scheme
    port=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('port', 8090))" 2>/dev/null || echo "8090")
    username=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('auth', {}).get('username', 'admin'))" 2>/dev/null || echo "admin")
    secret_path=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('secret_path', 'xfwd-admin'))" 2>/dev/null || echo "xfwd-admin")
    secret_path=$(echo "$secret_path" | sed -e 's/^[ \t\/]*//' -e 's/[ \t\/]*$//')
    cert=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_cert', ''))" 2>/dev/null || echo "")
    key=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_key', ''))" 2>/dev/null || echo "")
    wan_ip=$(detect_wan_ip)

    scheme="http"
    if [[ -n "$cert" && -n "$key" ]]; then
        scheme="https"
    fi

    local access_url
    if [[ -n "$secret_path" ]]; then
        access_url="${scheme}://${wan_ip}:${port}/${secret_path}/"
    else
        access_url="${scheme}://${wan_ip}:${port}/"
    fi

    echo
    printf "%b===============================================================%b\n" "$GREEN" "$NC"
    printf "%b  XForwarder Web Dashboard (24/7 Online)%b\n" "$BOLD" "$NC"
    printf "%b===============================================================%b\n" "$GREEN" "$NC"
    printf "  %bURL:%b           %s\n" "$BOLD" "$NC" "$access_url"
    printf "  %bPort:%b          %s\n" "$BOLD" "$NC" "$port"
    printf "  %bSecurity Path:%b /%s/\n" "$BOLD" "$NC" "${secret_path:-}"
    printf "  %bUsername:%b      %s\n" "$BOLD" "$NC" "$username"
    printf "  %bSSL/TLS:%b       %s\n" "$BOLD" "$NC" "$([[ "$scheme" == "https" ]] && echo "Enabled (HTTPS)" || echo "Disabled (HTTP)")"
    printf "  %bStatus:%b        Active (24/7 Enabled)\n" "$BOLD" "$NC"
    printf "%b===============================================================%b\n\n" "$GREEN" "$NC"
}

show_status() {
    check_root
    local state_file="/run/xforwarder/state.json"
    if [[ ! -f "$state_file" ]]; then
        state_file="/run/forward-manager/state.json"
    fi

    if [[ ! -f "$state_file" ]]; then
        msg_warn "State file not available yet. Checking system services..."
        systemctl status "$DAEMON_SERVICE" "$WEB_SERVICE" --no-pager 2>/dev/null || true
        return 0
    fi

    python3 -c "
import json

try:
    with open('$state_file') as f:
        data = json.load(f)
    cfg = data.get('config', {})
    rt = data.get('runtime', {})
    rules = cfg.get('rules', [])

    print('\n--------------------------------------------------------------')
    print(' XForwarder - Real-time Status')
    print('--------------------------------------------------------------')
    print(f' WAN Interface:    {rt.get("wan_interface", "unknown")}')
    print(f' Active Services:  HAProxy: {rt.get("active_services", {}).get("haproxy")} | Nginx: {rt.get("active_services", {}).get("nginx")} | NFTables: {rt.get("active_services", {}).get("nftables")}')
    try:
        import shutil, subprocess
        nft_ok = 'Active' if (shutil.which('nft') and subprocess.run(['nft', 'list', 'tables'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0) else ('Installed' if shutil.which('nft') else 'Not Installed')
        ha_ok = 'Running' if (shutil.which('haproxy') and subprocess.run(['systemctl', 'is-active', 'haproxy'], stdout=subprocess.PIPE, text=True).stdout.strip() == 'active') else ('Installed' if shutil.which('haproxy') else 'Not Installed')
        ngx_ok = 'Running' if (shutil.which('nginx') and subprocess.run(['systemctl', 'is-active', 'nginx'], stdout=subprocess.PIPE, text=True).stdout.strip() == 'active') else ('Installed' if shutil.which('nginx') else 'Not Installed')
        print(f' System Engines:   NFTables: {nft_ok} | HAProxy: {ha_ok} | Nginx: {ngx_ok}')
    except Exception:
        pass
    print(f' Rules Configured: {len(rules)}')
    print('--------------------------------------------------------------')

    if not rules:
        print(' No port forwarding rules configured. Login to Web UI to add rules.')
    else:
        fmt = '{:<8} {:<10} {:<10} {:<30} {:<15}'
        print(fmt.format('Port', 'Proto', 'Active', 'Current Destination', 'Status'))
        print('-' * 75)
        for r in rules:
            p = r.get('port')
            proto = r.get('protocol', 'both')
            proto_str = 'TCP+UDP' if str(proto).lower() == 'both' else str(proto).upper()
            act_prio = r.get('active_priority', 1)
            dest = next((d for d in r.get('destinations', []) if d.get('priority') == act_prio), None)
            if dest:
                dest_str = f\"{dest.get('type')}: {dest.get('target')}:{dest.get('port', p)}\"
            else:
                dest_str = 'None'
            prio_tag = f'Priority {act_prio}'
            print(fmt.format(f':{p}', proto_str, prio_tag, dest_str, 'HEALTHY'))
    print('--------------------------------------------------------------\n')
except Exception as e:
    print('Error parsing state:', e)
"
}

import_relay_rules() {
    check_root
    local active_cfg
    active_cfg=$(resolve_active_config)
    msg_info "Scanning for pre-existing HAProxy & NFTables relay rules on this server..."
    python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
from core.nftables_parser import import_all_relay_rules_into_config
count, ports, logs = import_all_relay_rules_into_config('$active_cfg', deactivate_legacy=True)
for log in logs:
    print(f'   \033[0;36m*\033[0m {log}')
if count > 0:
    print(f'\033[0;32m[OK] Successfully imported {count} relay port rule(s) into XForwarder: {ports}\033[0m')
else:
    print('\033[1;33m[INFO] No new unimported HAProxy or NFTables forwarding rules found.\033[0m')
"
    systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE" >/dev/null 2>&1 || true
    msg_ok "XForwarder services synced with imported rules."
    show_status
}

import_haproxy_rules() {
    import_relay_rules
}

export_config_cli() {
    check_root
    local target_path="${1:-}"
    if [[ -z "$target_path" ]]; then
        local ts
        ts=$(date +%Y%m%d_%H%M%S)
        target_path="./xforwarder-backup-$ts.json"
    fi

    local active_cfg
    active_cfg=$(resolve_active_config)
    export XFWD_CONFIG_PATH="$active_cfg"

    msg_info "Exporting configuration from $active_cfg..."
    python3 -c "
import sys, json, os
target_path = sys.argv[1]
sys.path.insert(0, '$INSTALL_DIR')
from core.web_server import export_config_data
try:
    data = export_config_data()
    out_dir = os.path.dirname(os.path.abspath(target_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    tmp_path = f'{target_path}.tmp.{os.getpid()}'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, target_path)
    rule_count = len(data.get('rules', []))
    print(f'\033[0;32m[OK] Successfully exported configuration ({rule_count} rules) to {target_path}\033[0m')
except Exception as e:
    print(f'\033[0;31m[ERROR] Failed to export configuration: {e}\033[0m', file=sys.stderr)
    sys.exit(1)
" "$target_path"
}

import_config_cli() {
    check_root
    local file_path="${1:-}"
    local mode="${2:---merge}"

    if [[ -z "$file_path" ]]; then
        echo
        printf "%bEnter path to backup JSON file to import:%b " "$YELLOW" "$NC"
        read -r file_path
    fi

    if [[ ! -f "$file_path" ]]; then
        msg_err "File not found: $file_path"
        return 1
    fi

    local clean_mode="merge"
    if [[ "$mode" == "--replace" || "$mode" == "replace" ]]; then
        clean_mode="replace"
    fi

    local active_cfg
    active_cfg=$(resolve_active_config)
    export XFWD_CONFIG_PATH="$active_cfg"

    msg_info "Importing configuration from $file_path (mode: $clean_mode)..."
    python3 -c "
import sys, json
file_path = sys.argv[1]
import_mode = sys.argv[2]
sys.path.insert(0, '$INSTALL_DIR')
from core.web_server import import_config_data

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
except Exception as e:
    print(f'\033[0;31m[ERROR] Failed to read JSON file: {e}\033[0m', file=sys.stderr)
    sys.exit(1)

ok, err, info = import_config_data(payload, mode=import_mode)
if ok:
    imported_cnt = info.get('imported_count', 0)
    total_cnt = info.get('count', 0)
    backup_file = info.get('backup', '')
    print(f'\033[0;32m[OK] Successfully imported {imported_cnt} rule(s) in {info.get(\"mode\")} mode.\033[0m')
    print(f'\033[0;32m[OK] Total active rules: {total_cnt}.\033[0m')
    if backup_file:
        print(f'\033[1;33m[INFO] Pre-restore atomic backup saved to: {backup_file}\033[0m')
else:
    print(f'\033[0;31m[ERROR] Import failed: {err}\033[0m', file=sys.stderr)
    sys.exit(1)
" "$file_path" "$clean_mode" || return 1

    systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE" >/dev/null 2>&1 || true
    msg_ok "XForwarder services restarted and synced with imported rules."
    show_status
}

backup_restore_menu() {
    clear
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "%b   Backup & Restore (Export / Import Configuration)%b\n" "$BOLD" "$NC"
    printf "%b=======================================================%b\n\n" "$CYAN" "$NC"

    echo "1) Export Configuration to JSON file"
    echo "2) Import Configuration (Merge mode - keeps existing non-conflicting rules)"
    echo "3) Import Configuration (Replace mode - replaces all rules)"
    echo "0) Back to Main Menu"
    echo
    read -r -p "Select an option [0-3]: " bchoice

    case "$bchoice" in
        1)
            echo
            printf "%bEnter export file path (leave empty for default timestamped file):%b " "$YELLOW" "$NC"
            read -r dest
            export_config_cli "$dest"
            echo
            read -r -p "Press Enter to continue..."
            ;;
        2)
            echo
            printf "%bEnter path to backup JSON file to import:%b " "$YELLOW" "$NC"
            read -r src
            import_config_cli "$src" "--merge"
            echo
            read -r -p "Press Enter to continue..."
            ;;
        3)
            echo
            printf "%bWARNING: Replace mode will replace all existing port rules!%b\n" "$RED" "$NC"
            printf "%bEnter path to backup JSON file to import:%b " "$YELLOW" "$NC"
            read -r src
            printf "%bAre you sure you want to proceed with REPLACE mode? (y/N):%b " "$YELLOW" "$NC"
            read -r confirm
            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                import_config_cli "$src" "--replace"
            else
                msg_info "Import cancelled."
            fi
            echo
            read -r -p "Press Enter to continue..."
            ;;
        0)
            return 0
            ;;
        *)
            msg_warn "Invalid selection."
            ;;
    esac
}

show_menu() {
    clear
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "%b   XForwarder (v%s)%b\n" "$BOLD" "$SCRIPT_VERSION" "$NC"
    printf "%b   Multi-Path Priority, HAProxy Relay & NFTables Failover%b\n" "$CYAN" "$NC"
    printf "%b=======================================================%b\n\n" "$CYAN" "$NC"

    echo "1) Show Web Dashboard Access URL"
    echo "2) Show Status & Active Port Routes"
    echo "3) Web Panel Settings (Port, Username, Password, Secret Path, SSL/TLS)"
    echo "4) Restart XForwarder Services"
    echo "5) View Core Engine Live Logs"
    echo "6) Update XForwarder (Auto-Migrate & Preserve Rules)"
    echo "7) Re-install / Full Setup Wizard"
    echo "8) Import Pre-existing Relay Rules (HAProxy & NFTables)"
    echo "9) Backup & Restore (Export / Import Settings JSON)"
    echo "10) Check & Install System Dependencies (NFTables, HAProxy, Nginx)"
    echo "11) Network Performance Tuning (BBR, Sysctl & Systemd Limits)"
    echo "0) Exit"
    echo
    read -r -p "Select an option [0-11]: " choice

    case "$choice" in
        1) show_web_access_info ;;
        2) show_status ;;
        3) modify_web_settings_menu ;;
        4) systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE" && msg_ok "Services restarted." ;;
        5) journalctl -u "$DAEMON_SERVICE" -f ;;
        6) update_xforwarder ;;
        7) install_xforwarder ;;
        8) import_relay_rules ;;
        9) backup_restore_menu ;;
        10) check_root; ensure_dependencies ;;
        11) check_root; tune_network ;;
        0) exit 0 ;;
        *) msg_warn "Invalid selection." ;;
    esac
}

# CLI dispatcher
case "${1:-}" in
    install)
        install_xforwarder
        ;;
    import|import-rules|import-all|import-haproxy|import-nftables)
        import_relay_rules
        ;;
    update|upgrade)
        if ! is_installed; then
            echo
            printf "%b=======================================================%b\n" "$CYAN" "$NC"
            printf "%b   XForwarder is not installed on this system.%b\n" "$YELLOW" "$NC"
            printf "%b   Starting initial installation wizard...%b\n" "$GREEN" "$NC"
            printf "%b=======================================================%b\n\n" "$CYAN" "$NC"
            install_xforwarder
        else
            update_xforwarder
        fi
        ;;
    status)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        show_status
        ;;
    url|web)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        show_web_access_info
        ;;
    port)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        change_web_port
        ;;
    username)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        change_web_username
        ;;
    password)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        change_web_password
        ;;
    path|secret)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        change_web_secret_path
        ;;
    settings|web-config)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        modify_web_settings_menu
        ;;
    restart)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE"
        msg_ok "XForwarder services restarted."
        ;;
    log|logs)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        journalctl -u "$DAEMON_SERVICE" -f
        ;;
    export|export-config)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        shift
        export_config_cli "${1:-}"
        ;;
    import-config)
        if ! is_installed; then
            msg_err "XForwarder is not installed. Please run installation first."
            exit 1
        fi
        shift
        import_config_cli "$@"
        ;;
    check-deps|install-deps|deps)
        check_root
        ensure_dependencies
        ;;
    optimize|tune|tune-network)
        check_root
        tune_network
        ;;
    "")
        if ! is_installed; then
            echo
            printf "%b=======================================================%b\n" "$CYAN" "$NC"
            printf "%b   XForwarder is not installed on this system.%b\n" "$YELLOW" "$NC"
            printf "%b   Starting initial installation wizard...%b\n" "$GREEN" "$NC"
            printf "%b=======================================================%b\n\n" "$CYAN" "$NC"
            install_xforwarder
        else
            show_menu
        fi
        ;;
    *)
        echo "Usage: xforwarder {install|update|tune|check-deps|status|url|port|username|password|path|settings|export|import-config|restart|logs}"
        exit 1
        ;;
esac

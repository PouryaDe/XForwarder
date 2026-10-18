#!/usr/bin/env bash
#
# Forward Manager - Installer & CLI Controller
# Manages multi-path priority failover, HAProxy zero-tunnel relays, and NFTables tunnels.
# Features a 24/7 authenticated Web UI.
#

set -Eeuo pipefail

SCRIPT_VERSION="1.1.0"
INSTALL_DIR="/opt/forward-manager"
CONFIG_DIR="/etc/forward-manager"
CONFIG_FILE="$CONFIG_DIR/config.json"
BIN_LINK="/usr/local/bin/forward-manager"
SHORT_LINK="/usr/local/bin/fwdman"

DAEMON_SERVICE="forward-manager"
WEB_SERVICE="forward-manager-web"

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
    msg_info "Checking system dependencies..."
    local pkgs=()
    command -v python3 >/dev/null 2>&1 || pkgs+=(python3)
    command -v haproxy >/dev/null 2>&1 || pkgs+=(haproxy)
    command -v nft >/dev/null 2>&1 || pkgs+=(nftables)
    command -v curl >/dev/null 2>&1 || pkgs+=(curl)

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        msg_info "Installing missing packages: ${pkgs[*]}..."
        apt-get update -q
        DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${pkgs[@]}"
    fi

    # Ensure IP forward is permanently active in kernel
    sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
    if ! grep -q "net.ipv4.ip_forward = 1" /etc/sysctl.conf 2>/dev/null; then
        echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
    fi

    # Disable system nftables service to avoid boot flushing conflicts
    systemctl disable --now nftables >/dev/null 2>&1 || true
}

install_forward_manager() {
    check_root
    ensure_dependencies

    local script_dir
    script_dir=$(dirname "$(readlink -f "$0")")

    msg_info "Installing Forward-Manager into $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"

    cp -r "$script_dir/core" "$INSTALL_DIR/"
    cp -r "$script_dir/web" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/core/engine.py" "$INSTALL_DIR/core/web_server.py"

    # Wizard for initial configuration
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo
        printf "%b=======================================================%b\n" "$CYAN" "$NC"
        printf "%b  Forward-Manager Setup Wizard%b\n" "$BOLD" "$NC"
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

        local pass_hash
        pass_hash=$(python3 -c "import hashlib; print(hashlib.sha256('$user_pass'.encode()).hexdigest())")

        cat <<EOF > "$CONFIG_FILE"
{
  "wan_interface": "$user_iface",
  "check_interval_seconds": 8,
  "failure_threshold": 3,
  "recovery_threshold": 3,
  "web": {
    "bind_host": "0.0.0.0",
    "port": $user_port,
    "auth": {
      "username": "$user_name",
      "password_hash": "$pass_hash"
    }
  },
  "rules": []
}
EOF
        msg_ok "Configuration initialized at $CONFIG_FILE"
    fi

    # Install systemd service units
    cp "$script_dir/systemd/forward-manager.service" /etc/systemd/system/
    cp "$script_dir/systemd/forward-manager-web.service" /etc/systemd/system/
    systemctl daemon-reload

    # Enable and start BOTH core daemon and web server 24/7
    systemctl enable --now "$DAEMON_SERVICE"
    systemctl enable --now "$WEB_SERVICE"
    msg_ok "Forward-Manager Engine & 24/7 Web Server started."

    # Symlink CLI
    ln -sf "$(readlink -f "$0")" "$BIN_LINK"
    ln -sf "$(readlink -f "$0")" "$SHORT_LINK"

    msg_ok "CLI commands installed: forward-manager and fwdman"
    show_web_access_info
}

change_password() {
    check_root
    if [[ ! -f "$CONFIG_FILE" ]]; then
        msg_err "Configuration not found. Please install first."
        exit 1
    fi

    read -r -p "Enter new username: " new_user
    read -r -s -p "Enter new password: " new_pass
    echo

    if [[ -z "$new_user" || -z "$new_pass" ]]; then
        msg_err "Username and password cannot be empty."
        exit 1
    fi

    python3 -c "
import json, hashlib
with open('$CONFIG_FILE', 'r') as f:
    cfg = json.load(f)
cfg['web']['auth'] = {
    'username': '$new_user',
    'password_hash': hashlib.sha256('$new_pass'.encode()).hexdigest()
}
with open('$CONFIG_FILE', 'w') as f:
    json.dump(cfg, f, indent=2)
"
    systemctl restart "$WEB_SERVICE"
    msg_ok "Credentials updated successfully. Web server reloaded."
}

show_web_access_info() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        msg_err "Configuration file not found. Run: forward-manager install"
        return 1
    fi

    local port username wan_ip
    port=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['web']['port'])" 2>/dev/null || echo "8090")
    username=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['web']['auth']['username'])" 2>/dev/null || echo "admin")
    wan_ip=$(detect_wan_ip)

    echo
    printf "%b===============================================================%b\n" "$GREEN" "$NC"
    printf "%b  Forward Manager Web Dashboard (24/7 Online)%b\n" "$BOLD" "$NC"
    printf "%b===============================================================%b\n" "$GREEN" "$NC"
    printf "  %bURL:%b      http://%s:%s/\n" "$BOLD" "$NC" "$wan_ip" "$port"
    printf "  %bUsername:%b %s\n" "$BOLD" "$NC" "$username"
    printf "  %bStatus:%b   Active (24/7 Enabled)\n" "$BOLD" "$NC"
    printf "%b===============================================================%b\n\n" "$GREEN" "$NC"
}

show_status() {
    check_root
    local state_file="/run/forward-manager/state.json"
    if [[ ! -f "$state_file" ]]; then
        msg_warn "State file not available yet. Checking system services..."
        systemctl status "$DAEMON_SERVICE" "$WEB_SERVICE" --no-pager
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
    print(' Forward Manager - Real-time Status')
    print('--------------------------------------------------------------')
    print(f' WAN Interface:    {rt.get(\"wan_interface\", \"unknown\")}')
    print(f' Active Services:  HAProxy: {rt.get(\"active_services\", {}).get(\"haproxy\")} | NFTables: {rt.get(\"active_services\", {}).get(\"nftables\")}')
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
            act_prio = r.get('active_priority', 1)
            dest = next((d for d in r.get('destinations', []) if d.get('priority') == act_prio), None)
            if dest:
                dest_str = f\"{dest.get('type')}: {dest.get('target')}:{dest.get('port', p)}\"
            else:
                dest_str = 'None'
            prio_tag = f'Priority {act_prio}'
            print(fmt.format(f':{p}', proto.upper(), prio_tag, dest_str, 'HEALTHY'))
    print('--------------------------------------------------------------\n')
except Exception as e:
    print('Error parsing state:', e)
"
}

show_menu() {
    clear
    printf "%b=======================================================%b\n" "$CYAN" "$NC"
    printf "%b   Forward Manager (v%s)%b\n" "$BOLD" "$SCRIPT_VERSION" "$NC"
    printf "%b   Multi-Path Priority, HAProxy Relay & NFTables Failover%b\n" "$CYAN" "$NC"
    printf "%b=======================================================%b\n\n" "$CYAN" "$NC"

    echo "1) Show Web Dashboard Access URL"
    echo "2) Show Status & Active Port Routes"
    echo "3) Change Web Admin Username / Password"
    echo "4) Restart Forward-Manager Services"
    echo "5) View Core Engine Live Logs"
    echo "6) Re-install / Update Components"
    echo "0) Exit"
    echo
    read -r -p "Select an option [0-6]: " choice

    case "$choice" in
        1) show_web_access_info ;;
        2) show_status ;;
        3) change_password ;;
        4) systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE" && msg_ok "Services restarted." ;;
        5) journalctl -u "$DAEMON_SERVICE" -f ;;
        6) install_forward_manager ;;
        0) exit 0 ;;
        *) msg_warn "Invalid selection." ;;
    esac
}

# CLI dispatcher
case "${1:-}" in
    install)
        install_forward_manager
        ;;
    status)
        show_status
        ;;
    url|web)
        show_web_access_info
        ;;
    password)
        change_password
        ;;
    restart)
        systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE"
        msg_ok "Forward-Manager services restarted."
        ;;
    log|logs)
        journalctl -u "$DAEMON_SERVICE" -f
        ;;
    "")
        show_menu
        ;;
    *)
        echo "Usage: forward-manager {install|status|url|password|restart|logs}"
        exit 1
        ;;
esac

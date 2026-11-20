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

SCRIPT_VERSION="1.5.0"
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

# ── Ovira Mint Terminal UI Engine (Zero External Dependencies) ──────────────
UI_FD=""
UI_ROWS=24
UI_COLS=80
UI_KEY=""
UTF=0
COLOR=0
MENU_ACTIVE=0
UPDATED_CLI=0

# Legacy color variables mapped safely to Mint/Teal palette
CYAN='\033[38;5;44m'
GREEN='\033[38;5;84m'
YELLOW='\033[38;5;220m'
RED='\033[38;5;203m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

ACC=""
RST=""
GRN=""
TEAL=""
PURPLE=""
GRAY=""
YEL=""
SEL_BG=""
LOGO_TINT=("" "" "" "" "")
G_TL="+" G_TR="+" G_BL="+" G_BR="+" G_V="|" G_H="-" G_LT="+" G_SEC="*"
G_OK="+" G_ERR="x" G_ON="*" G_OFF="o" G_HALF="~" G_ARR=">" G_SEL=">" G_MID="-"
G_UD="Up/Down" G_FLOW="->"

ui_init() {
    case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in *[Uu][Tt][Ff]-8*|*[Uu][Tt][Ff]8*) UTF=1 ;; esac
    if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
        COLOR=1
    fi

    if (( COLOR )); then
        if [[ "${COLORTERM:-}" == *truecolor* || "${COLORTERM:-}" == *24bit* ]]; then
            ACC=$'\033[38;2;52;224;161m'
        else
            ACC=$'\033[38;5;78m'
        fi
        BOLD=$'\033[1m'; DIM=$'\033[2m'; RST=$'\033[0m'; NC="$RST"
        GRN=$'\033[38;5;84m'; TEAL=$'\033[38;5;44m'; PURPLE=$'\033[38;5;141m'
        GRAY=$'\033[38;5;245m'; YEL=$'\033[38;5;220m'; RED=$'\033[38;5;203m'
        CYAN="$TEAL"; GREEN="$GRN"; YELLOW="$YEL"
        SEL_BG=$'\033[48;5;237m'
        LOGO_TINT=($'\033[38;5;154m' $'\033[38;5;118m' $'\033[38;5;84m' $'\033[38;5;79m' $'\033[38;5;44m')
    else
        ACC=""; BOLD=""; DIM=""; RST=""; GRN=""; TEAL=""; PURPLE=""; GRAY=""; YEL=""; RED=""; SEL_BG=""
        CYAN=""; GREEN=""; YELLOW=""; NC=""
        LOGO_TINT=("" "" "" "" "")
    fi

    if (( UTF )); then
        G_TL="╭"; G_TR="╮"; G_BL="╰"; G_BR="╯"; G_V="│"; G_H="─"; G_LT="├"; G_SEC="◆"
        G_OK="✓"; G_ERR="✗"; G_ON="●"; G_OFF="○"; G_HALF="◐"; G_ARR="›"; G_SEL="❯"; G_MID="·"
        G_UD="↑/↓"; G_FLOW="→"
    fi

    UI_FD=""
    if (( ${YES:-0} == 0 )); then
        if [[ -t 0 ]]; then
            UI_FD=0
        elif [[ -r /dev/tty && -w /dev/tty ]] && { : < /dev/tty; } 2>/dev/null; then
            exec 3< /dev/tty
            UI_FD=3
        fi
    fi
}

ui_restore_terminal() {
    if [[ -t 1 ]]; then
        printf '\033[?25h\033[?7h'
    fi
    if [[ -n "${UI_FD:-}" ]]; then
        stty echo icanon <&"$UI_FD" 2>/dev/null || true
    fi
}

ui_has_input() { [[ -n "${UI_FD:-}" ]]; }
ui_rich() { [[ -n "${UI_FD:-}" && -t 1 ]]; }

ui_term_size() {
    local size=""
    [[ -n "${UI_FD:-}" ]] && size=$(stty size <&"$UI_FD" 2>/dev/null || true)
    UI_ROWS=${size%% *}
    UI_COLS=${size##* }
    [[ "$UI_ROWS" =~ ^[0-9]+$ ]] && (( UI_ROWS > 0 )) || UI_ROWS=${LINES:-24}
    [[ "$UI_COLS" =~ ^[0-9]+$ ]] && (( UI_COLS > 0 )) || UI_COLS=${COLUMNS:-80}
}

ui_width() {
    local w=$(( UI_COLS - 4 ))
    (( w > 72 )) && w=72
    (( w < 44 )) && w=44
    printf '%d' "$w"
}

ui_line() {
    local n="${1:-0}" line=""
    (( n < 0 )) && n=0
    printf -v line '%*s' "$n" ''
    printf '%s' "${line// /${2:-$G_H}}"
}

msg_info() { printf '  %s%s%s %s\n' "$TEAL" "$G_ARR" "$RST" "$*"; }
msg_ok()   { printf '  %s%s%s %s\n' "$GRN" "$G_OK" "$RST" "$*"; }
msg_warn() { printf '  %s!%s %s\n' "$YEL" "$RST" "$*"; }
msg_err()  { printf '  %s%s %s%s\n' "$RED" "$G_ERR" "$*" "$RST" >&2; }

ui_logo() {
    local -a art=(
        '__  _______ ___  ______        ___    ____  ____  _____ ____  '
        '\ \/ /  ___/ _ \|  _ \ \      / / \  |  _ \|  _ \| ____|  _ \ '
        ' \  /| |_ | | | | |_) \ \ /\ / / _ \ | |_) | | | |  _| | |_) |'
        ' /  \|  _|| |_| |  _ < \ V  V / ___ \|  _ <| |_| | |___|  _ < '
        '/_/\_\_|   \___/|_| \_\ \_/\_/_/   \_\_| \_\____/|_____|_| \_\'
    )
    local i
    for i in "${!art[@]}"; do
        printf '  %s%s%s\n' "$BOLD${LOGO_TINT[i]}" "${art[i]}" "$RST"
    done
    printf '  %sXForwarder Multi-Path Failover Engine%s  %s·  v%s  ·  Linux Relay%s\n' \
        "$ACC" "$RST" "$GRAY" "$SCRIPT_VERSION" "$RST"
}

ui_title_bar() {
    local w inner title="XForwarder" tag="${1:-Relay Panel}" ver="v${SCRIPT_VERSION}" pad
    w=$(ui_width); inner=$(( w - 2 ))
    pad=$(( inner - 4 - ${#title} - 2 - ${#tag} - ${#ver} - 2 ))
    (( pad < 1 )) && pad=1
    printf '  %s%s%s%s%s\n' "$DIM$TEAL" "$G_TL" "$(ui_line "$inner")" "$G_TR" "$RST"
    printf '  %s%s%s  %s%s %s%s  %s%s%s%*s%s%s%s  %s%s%s\n' \
        "$DIM$TEAL" "$G_V" "$RST" "$BOLD$ACC" "$G_SEC" "$title" "$RST" "$PURPLE" "$tag" "$RST" \
        "$pad" "" "$GRAY" "$ver" "$RST" "$DIM$TEAL" "$G_V" "$RST"
    printf '  %s%s%s%s%s\n' "$DIM$TEAL" "$G_BL" "$(ui_line "$inner")" "$G_BR" "$RST"
}

ui_header() {
    ui_term_size
    if ui_rich && (( ${MENU_ACTIVE:-0} )); then
        printf '\033[H\033[2J\033[3J'
    fi
    if [[ "${1:-}" == "big" ]] && (( UI_ROWS >= 28 && UI_COLS >= 66 )); then
        echo; ui_logo
    else
        echo; ui_title_bar "${2:-Multi-Path Failover Panel}"
    fi
}

section() {
    printf '\n  %s%s %s%s\n' "$BOLD$PURPLE" "$G_SEC" "$1" "$RST"
    printf '  %s%s%s\n' "$DIM$TEAL" "$(ui_line "$(ui_width)")" "$RST"
}

step() {
    printf '\n  %s%s Step %s/%s %s %s%s\n' "$BOLD$PURPLE" "$G_SEC" "$1" "$2" "$G_MID" "$3" "$RST"
    printf '  %s%s%s\n' "$DIM$TEAL" "$(ui_line "$(ui_width)")" "$RST"
}

card_top() {
    local rem=$(( $(ui_width) - ${#1} - 4 ))
    (( rem < 2 )) && rem=2
    printf '\n  %s%s%s %s%s%s %s%s%s\n' "$DIM$TEAL" "$G_TL" "$G_H" "$BOLD$ACC" "$1" "$RST" "$DIM$TEAL" "$(ui_line "$rem")" "$RST"
}
card_sep() {
    local rem=$(( $(ui_width) - ${#1} - 4 ))
    (( rem < 2 )) && rem=2
    printf '  %s%s%s %s %s%s\n' "$DIM$TEAL" "$G_LT" "$G_H" "$1" "$(ui_line "$rem")" "$RST"
}
card_text() { printf '  %s%s%s  %s\n' "$DIM$TEAL" "$G_V" "$RST" "$1"; }
card_kv()   { printf '  %s%s%s  %s%-16s%s %s%s%s\n' "$DIM$TEAL" "$G_V" "$RST" "$GRAY" "$1" "$RST" "${3:-}" "$2" "$RST"; }
card_copy() { printf '\n  %s%s%s\n\n' "$BOLD$ACC" "$1" "$RST"; }
card_end()  { printf '  %s%s%s%s\n' "$DIM$TEAL" "$G_BL" "$(ui_line $(( $(ui_width) - 1 )))" "$RST"; }

ui_read_key() {
    local key="" rest="" status=0
    UI_KEY=""
    IFS= read -rsn1 -t 1 key <&"$UI_FD" || status=$?
    (( status > 128 )) && return 2
    (( status == 0 )) || return 1
    case "$key" in
        "") UI_KEY="enter"; return 0 ;;
        $'\177'|$'\b') UI_KEY="backspace"; return 0 ;;
        $'\033') ;;
        *) UI_KEY="$key"; return 0 ;;
    esac
    IFS= read -rsn2 -t 0.05 rest <&"$UI_FD" || true
    case "$rest" in
        '[A'|'OA') UI_KEY="up" ;;
        '[B'|'OB') UI_KEY="down" ;;
        '[H'|'OH') UI_KEY="home" ;;
        '[F'|'OF') UI_KEY="end" ;;
        '') UI_KEY="esc" ;;
        *) UI_KEY="other"; IFS= read -rsn1 -t 0.05 _ <&"$UI_FD" || true ;;
    esac
    return 0
}

ui_choose() {
    local -n __uc_out="$1"
    local __uc_sel="$2" __uc_i __uc_n __uc_drawn=0 __uc_w __uc_pad __uc_line __uc_frame __uc_ans __uc_status __uc_num_pad
    shift 2
    local -a __uc_opts=("$@")
    __uc_n=${#__uc_opts[@]}
    (( __uc_sel >= 0 && __uc_sel < __uc_n )) || __uc_sel=0
    if [[ -z "${UI_FD:-}" ]]; then __uc_out=$__uc_sel; return 0; fi

    if ! ui_rich; then
        for __uc_i in "${!__uc_opts[@]}"; do
            printf '    [%d] %s\n' $(( __uc_i + 1 )) "${__uc_opts[__uc_i]}"
        done
        while :; do
            printf '  Select 1-%d [%d]: ' "$__uc_n" $(( __uc_sel + 1 ))
            IFS= read -r __uc_ans <&"$UI_FD" || return 1
            __uc_ans=${__uc_ans:-$(( __uc_sel + 1 ))}
            if [[ "$__uc_ans" =~ ^[0-9]+$ ]] && (( __uc_ans >= 1 && __uc_ans <= __uc_n )); then break; fi
        done
        __uc_out=$(( __uc_ans - 1 ))
        return 0
    fi

    ui_term_size
    __uc_w=$(ui_width)
    for __uc_i in "${!__uc_opts[@]}"; do
        (( ${#__uc_opts[__uc_i]} + 10 > __uc_w )) && __uc_w=$(( ${#__uc_opts[__uc_i]} + 10 ))
    done
    (( __uc_w > UI_COLS - 3 )) && __uc_w=$(( UI_COLS - 3 ))
    printf '\033[?25l\033[?7l'
    stty -echo <&"$UI_FD" 2>/dev/null || true
    while :; do
        __uc_frame=""
        (( __uc_drawn )) && __uc_frame+=$'\033'"[${__uc_drawn}A"$'\r'
        for __uc_i in "${!__uc_opts[@]}"; do
            __uc_num_pad=$(( __uc_i + 1 ))
            if (( __uc_i == __uc_sel )); then
                __uc_pad=$(( __uc_w - 9 - ${#__uc_opts[__uc_i]} ))
                (( __uc_pad < 1 )) && __uc_pad=1
                printf -v __uc_line '  %s%s%s %s %2d  %s%*s%s' "$ACC" "$G_SEL" "$RST" "$SEL_BG$BOLD" \
                    "$__uc_num_pad" "${__uc_opts[__uc_i]}" "$__uc_pad" "" "$RST"
            else
                printf -v __uc_line '    %s%2d%s  %s' "$GRAY" "$__uc_num_pad" "$RST" "${__uc_opts[__uc_i]}"
            fi
            __uc_frame+="${__uc_line}"$'\033[K\n'
        done
        __uc_frame+=$'\n'"  ${DIM}${GRAY}${G_UD} move ${G_MID} Enter select ${G_MID} q back${RST}"$'\033[K\n'
        printf '%s' "$__uc_frame"
        __uc_drawn=$(( __uc_n + 2 ))

        __uc_status=0
        ui_read_key || __uc_status=$?
        case $__uc_status in
            1) UI_KEY="esc" ;;
            2) continue ;;
        esac
        case "$UI_KEY" in
            up|k) (( __uc_sel = (__uc_sel - 1 + __uc_n) % __uc_n )) || true ;;
            down|j|$'\t') (( __uc_sel = (__uc_sel + 1) % __uc_n )) || true ;;
            home) __uc_sel=0 ;;
            end) __uc_sel=$(( __uc_n - 1 )) ;;
            [1-9]) (( UI_KEY <= __uc_n )) && __uc_sel=$(( UI_KEY - 1 )) ;;
            enter) break ;;
            esc|q|Q)
                printf '\033[%dA\r\033[J\033[?7h\033[?25h' "$__uc_drawn"
                stty echo <&"$UI_FD" 2>/dev/null || true
                return 1
                ;;
        esac
    done
    printf '\033[%dA\r\033[J\033[?7h\033[?25h' "$__uc_drawn"
    stty echo <&"$UI_FD" 2>/dev/null || true
    printf '  %s%s%s %s\n' "$GRN" "$G_OK" "$RST" "${__uc_opts[__uc_sel]}"
    __uc_out="$__uc_sel"
    return 0
}

pick_yesno() {
    local a def=0 d="${2:-n}"
    [[ "${d,,}" == y* ]] || def=1
    ui_has_input || { (( def == 0 )); return; }
    printf '\n  %s%s%s\n' "$BOLD" "$1" "$RST"
    ui_choose a "$def" "Yes" "No" || return 1
    (( a == 0 ))
}

ask() {
    local -n __ask_out="$1"
    local __ask_q="$2" __ask_def="${3-}" __ask_line="" __ask_p
    if [[ -z "${UI_FD:-}" ]]; then __ask_out=$__ask_def; return 0; fi
    __ask_p="  ${BOLD}${ACC}?${RST} ${__ask_q}"
    [[ -n "$__ask_def" ]] && __ask_p+=" ${GRAY}[${__ask_def}]${RST}"
    read -e -r -p "${__ask_p}: " __ask_line <&"$UI_FD" || __ask_line=""
    __ask_out="${__ask_line:-$__ask_def}"
}

ask_secret() {
    local -n __sec_out="$1"
    local __sec_q="$2" __sec_val=""
    while [[ -z "$__sec_val" ]]; do
        read -r -s -p "  ${BOLD}${ACC}?${RST} ${__sec_q}: " __sec_val <&"${UI_FD:-0}" || __sec_val=""
        echo
        if [[ -z "$__sec_val" ]]; then
            msg_warn "Password cannot be empty. Please enter a valid password."
        fi
    done
    __sec_out="$__sec_val"
}

read_ssl_path() {
    local -n __ssl_out="$1"
    local __label="$2" __default_path="$3" __val=""
    while true; do
        ask __val "$__label" "$__default_path"
        __val=$(echo "$__val" | tr -d '[:space:]')
        if [[ -z "$__val" ]]; then
            msg_warn "Path cannot be empty."
            continue
        fi
        if [[ ! -f "$__val" ]]; then
            msg_warn "File '$__val' does not exist on this server right now."
            if pick_yesno "Save path anyway?" n; then
                break
            fi
        else
            break
        fi
    done
    __ssl_out="$__val"
}

ui_init
trap ui_restore_terminal EXIT

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

apt_install_safe() {
    local pkgs=("$@")
    local created_policy=0
    local rc=0
    local has_pending_dpkg=0
    local nginx_status=""

    nginx_status=$(dpkg-query -W -f='${Status}\n' nginx 2>/dev/null || true)
    if [[ -n "$(dpkg --audit 2>/dev/null || true)" ]] || [[ -n "$nginx_status" && "$nginx_status" != "install ok installed" ]]; then
        has_pending_dpkg=1
        # Unlink default Nginx site (`listen [::]:80`) before configuring half-installed packages
        rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf >/dev/null 2>&1 || true
    fi

    if [[ "$has_pending_dpkg" -eq 0 && ${#pkgs[@]} -eq 0 ]]; then
        return 0
    fi

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        msg_info "Installing missing dependencies: ${pkgs[*]}..."
    fi

    # Temporarily defer daemon autostart via Debian policy-rc.d so default configs
    # (`listen [::]:80` on IPv6-disabled VPS or busy port 80) do not abort dpkg postinst.
    if [[ ! -e /usr/sbin/policy-rc.d ]]; then
        printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
        chmod 755 /usr/sbin/policy-rc.d
        created_policy=1
    fi

    if [[ "$has_pending_dpkg" -eq 1 ]]; then
        msg_info "Completing pending dpkg configuration safely..."
        DEBIAN_FRONTEND=noninteractive dpkg --configure -a || rc=$?
    fi

    if [[ $rc -eq 0 && ${#pkgs[@]} -gt 0 ]]; then
        apt-get update -q || true
        DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${pkgs[@]}" || rc=$?
    fi

    if [[ "$created_policy" -eq 1 ]]; then
        rm -f /usr/sbin/policy-rc.d
    fi

    # Strip default Nginx welcome site immediately so IPv6 `[::]:80` binds are never retained
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf >/dev/null 2>&1 || true

    return "$rc"
}

ensure_dependencies() {
    msg_info "Checking system dependencies (NFTables, HAProxy, Nginx, Python3)..."
    local pkgs=()
    command -v python3 >/dev/null 2>&1 || pkgs+=(python3)
    command -v haproxy >/dev/null 2>&1 || pkgs+=(haproxy)
    command -v nginx >/dev/null 2>&1 || pkgs+=(nginx)
    command -v nft >/dev/null 2>&1 || pkgs+=(nftables)
    command -v conntrack >/dev/null 2>&1 || pkgs+=(conntrack)
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

    if command -v apt-get >/dev/null 2>&1; then
        apt_install_safe ${pkgs[@]+"${pkgs[@]}"}
    elif [[ ${#pkgs[@]} -gt 0 ]]; then
        msg_info "Installing missing dependencies: ${pkgs[*]}..."
        if command -v dnf >/dev/null 2>&1; then
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
    ui_header big "Linux Multi-Path Relay Setup"

    step 1 4 "System Dependencies & Kernel Tuning"
    ensure_dependencies

    step 2 4 "Sync Repository & Backups"
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

    # Interactive Configuration Wizard (Step 3 & Step 4)
    if [[ ! -f "$CONFIG_FILE" ]]; then
        step 3 4 "Network & Web Dashboard Access"

        local default_iface user_iface
        default_iface=$(detect_wan_iface)
        ask user_iface "WAN interface name" "$default_iface"

        local default_port="8090" user_port
        ask user_port "Web management port" "$default_port"

        local default_user="admin" user_name
        ask user_name "Admin username" "$default_user"

        local user_pass=""
        ask_secret user_pass "Admin password"

        local default_secret="xfwd-admin" user_secret
        ask user_secret "Security secret path (URL slug)" "$default_secret"
        user_secret=$(echo "$user_secret" | sed -e 's/^[ \t\/]*//' -e 's/[ \t\/]*$//')
        user_secret="${user_secret:-xfwd-admin}"

        step 4 4 "HTTPS Certificate & Review"
        local user_ssl_cert="" user_ssl_key="" ssl_idx=1
        ui_choose ssl_idx 1 \
            "Enable HTTPS with existing TLS certificate & key files" \
            "Plain HTTP (default / behind reverse proxy)" || ssl_idx=1
        if (( ssl_idx == 0 )); then
            read_ssl_path user_ssl_cert "SSL certificate path" "/etc/letsencrypt/live/domain/fullchain.pem"
            read_ssl_path user_ssl_key "SSL private key path" "/etc/letsencrypt/live/domain/privkey.pem"
        fi

        card_top "CONFIGURATION SUMMARY"
        card_kv "WAN Interface" "$user_iface"
        card_kv "Web Port" "${user_port}/tcp"
        card_kv "Admin User" "$user_name"
        card_kv "Secret Path" "/${user_secret}/"
        card_kv "HTTPS / TLS" "$([[ -n "$user_ssl_cert" ]] && echo "Enabled" || echo "Disabled (HTTP)")"
        card_end

        if ui_has_input && ! pick_yesno "Write configuration and start XForwarder services?" y; then
            msg_warn "Setup cancelled before writing configuration."
            if [[ -n "$cleanup_tmp" && -d "$cleanup_tmp" ]]; then
                rm -rf "$cleanup_tmp"
            fi
            return 0
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
    print(f'  \033[38;5;84m✓\033[0m Auto-imported {count} pre-existing relay port rules (HAProxy/NFTables): {ports}')
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

    msg_ok "CLI commands ready: xforwarder / xfwd (aliases: forward-manager, fwdman)"
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

    UPDATED_CLI=1

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

    ui_header "" "Web Panel Port"
    local current_port new_port
    current_port=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('port', 8090))" 2>/dev/null || echo "8090")

    ask new_port "New web management port" "$current_port"

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

    # Wake core failover engine immediately so any wide port ranges split around the new web port
    if systemctl is-active --quiet "$DAEMON_SERVICE" 2>/dev/null; then
        systemctl kill -s SIGUSR1 "$DAEMON_SERVICE" >/dev/null 2>&1 || true
    fi
    if command -v conntrack >/dev/null 2>&1; then
        conntrack -D -p tcp --dport "$new_port" >/dev/null 2>&1 || true
    fi

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

    ui_header "" "Admin Username"
    local current_user new_user
    current_user=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('auth', {}).get('username', 'admin'))" 2>/dev/null || echo "admin")

    ask new_user "New admin username" "$current_user"
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

    ui_header "" "Admin Password"
    local new_pass=""
    ask_secret new_pass "New admin password"

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

    ui_header "" "Security URL Slug"
    local current_secret new_secret
    current_secret=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('secret_path', 'xfwd-admin'))" 2>/dev/null || echo "xfwd-admin")

    ask new_secret "New security path (e.g. xfwd-admin, panel)" "$current_secret"
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

    ui_header "" "HTTPS / TLS Certificates"
    local current_cert current_key
    current_cert=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_cert', ''))" 2>/dev/null || echo "")
    current_key=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_key', ''))" 2>/dev/null || echo "")

    section "TLS CERTIFICATE PATHS"
    msg_info "Provide paths to your certificate (fullchain.pem) and private key (privkey.pem)."

    local new_cert new_key
    read_ssl_path new_cert "SSL certificate file path" "${current_cert:-/etc/letsencrypt/live/domain/fullchain.pem}"
    read_ssl_path new_key "SSL private key file path" "${current_key:-/etc/letsencrypt/live/domain/privkey.pem}"

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

    ui_header "" "Web Panel Setup Wizard"
    local current_port current_user current_secret current_cert current_key
    current_port=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('port', 8090))" 2>/dev/null || echo "8090")
    current_user=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('auth', {}).get('username', 'admin'))" 2>/dev/null || echo "admin")
    current_secret=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('secret_path', 'xfwd-admin'))" 2>/dev/null || echo "xfwd-admin")
    current_cert=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_cert', ''))" 2>/dev/null || echo "")
    current_key=$(python3 -c "import json; print(json.load(open('$active_cfg')).get('web', {}).get('ssl_key', ''))" 2>/dev/null || echo "")

    local new_port new_user new_pass="" new_secret
    ask new_port "Web management port" "$current_port"
    if ! [[ "$new_port" =~ ^[0-9]+$ ]] || (( new_port < 1 || new_port > 65535 )); then
        msg_err "Invalid port number. Must be between 1 and 65535."
        return 1
    fi

    ask new_user "Admin username" "$current_user"
    new_user=$(echo "$new_user" | tr -d '[:space:]')
    if [[ -z "$new_user" ]]; then
        msg_err "Username cannot be empty."
        return 1
    fi

    ask_secret new_pass "Admin password"

    ask new_secret "Security secret path" "$current_secret"
    new_secret=$(echo "$new_secret" | sed -e 's/^[ \t\/]*//' -e 's/[ \t\/]*$//')
    new_secret="${new_secret:-xfwd-admin}"

    local new_cert="$current_cert"
    local new_key="$current_key"
    if pick_yesno "Configure SSL/TLS (HTTPS) certificates?" n; then
        read_ssl_path new_cert "SSL certificate path" "${current_cert:-/etc/letsencrypt/live/domain/fullchain.pem}"
        read_ssl_path new_key "SSL private key path" "${current_key:-/etc/letsencrypt/live/domain/privkey.pem}"
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

    if systemctl is-active --quiet "$DAEMON_SERVICE" 2>/dev/null; then
        systemctl kill -s SIGUSR1 "$DAEMON_SERVICE" >/dev/null 2>&1 || true
    fi
    if command -v conntrack >/dev/null 2>&1; then
        conntrack -D -p tcp --dport "$new_port" >/dev/null 2>&1 || true
    fi

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

    ui_header "" "Web Panel Settings"
    card_top "CURRENT WEB SETTINGS"
    card_kv "Port" "${current_port}/tcp"
    card_kv "Username" "$current_user"
    card_kv "Security Path" "/${current_secret:-}/"
    card_kv "SSL / TLS" "$current_ssl_status"
    if [[ -n "$current_cert" ]]; then
        card_kv "SSL Cert" "$current_cert"
        card_kv "SSL Key" "$current_key"
    fi
    card_end
    echo

    local web_idx=0
    ui_choose web_idx 0 \
        "Change Web Port" \
        "Change Admin Username" \
        "Change Admin Password" \
        "Change Security Path (URL Slug)" \
        "Configure SSL/TLS Certificates (HTTPS)" \
        "Disable SSL/TLS (Revert to HTTP)" \
        "Run Full Web Settings Wizard" \
        "Back to Main Menu" || return 0

    case "$web_idx" in
        0) change_web_port ;;
        1) change_web_username ;;
        2) change_web_password ;;
        3) change_web_secret_path ;;
        4) change_web_ssl ;;
        5) disable_web_ssl ;;
        6) change_all_web_settings ;;
        7) return 0 ;;
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

    card_top "READY · XForwarder v${SCRIPT_VERSION}"
    card_kv "Username" "$username" "$BOLD"
    card_kv "Port" "${port}/tcp"
    card_kv "Security Path" "/${secret_path:-}/"
    card_kv "SSL / TLS" "$([[ "$scheme" == "https" ]] && echo "Enabled (HTTPS)" || echo "Disabled (HTTP)")"
    card_kv "Status" "Active (24/7 Online)" "$GRN"
    card_sep "Dashboard URL (open in browser)"
    card_copy "$access_url"
    card_sep "Quick guide"
    card_text "Run ${BOLD}xfwd${RST} or ${BOLD}xforwarder${RST} any time for interactive management."
    card_end
}

show_status() {
    check_root
    ui_header "" "Live Relay Status"
    local state_file="/run/xforwarder/state.json"
    if [[ ! -f "$state_file" ]]; then
        state_file="/run/forward-manager/state.json"
    fi

    if [[ ! -f "$state_file" ]]; then
        msg_warn "State file not available yet. Checking systemd services..."
        systemctl status "$DAEMON_SERVICE" "$WEB_SERVICE" --no-pager 2>/dev/null || true
        return 0
    fi

    python3 - "$state_file" << 'PYEOF'
import json, shutil, subprocess, sys

state_file = sys.argv[1]
MINT = "\033[38;2;52;224;161m"
TEAL = "\033[38;5;44m"
GRN  = "\033[38;5;84m"
GRAY = "\033[38;5;245m"
BOLD = "\033[1m"
RST  = "\033[0m"
if not sys.stdout.isatty():
    MINT = TEAL = GRN = GRAY = BOLD = RST = ""

try:
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = data.get("config", {})
    rt = data.get("runtime", {})
    rules = cfg.get("rules", [])

    nft_ok = "Active" if (shutil.which("nft") and subprocess.run(["nft", "list", "tables"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0) else ("Installed" if shutil.which("nft") else "Missing")
    ha_ok  = "Running" if (shutil.which("haproxy") and subprocess.run(["systemctl", "is-active", "haproxy"], stdout=subprocess.PIPE, text=True).stdout.strip() == "active") else ("Installed" if shutil.which("haproxy") else "Missing")
    ngx_ok = "Running" if (shutil.which("nginx") and subprocess.run(["systemctl", "is-active", "nginx"], stdout=subprocess.PIPE, text=True).stdout.strip() == "active") else ("Installed" if shutil.which("nginx") else "Missing")
    svcs = rt.get("active_services", {})

    print(f"\n  {TEAL}╭─ {BOLD}{MINT}RUNTIME & SYSTEM ENGINES{RST} {TEAL}{'─'*42}{RST}")
    print(f"  {TEAL}│{RST}  {GRAY}{'WAN Interface':18s}{RST} {rt.get('wan_interface', 'unknown')}")
    print(f"  {TEAL}│{RST}  {GRAY}{'Active Routing':18s}{RST} HAProxy: {svcs.get('haproxy')} · Nginx: {svcs.get('nginx')} · NFTables: {svcs.get('nftables')}")
    print(f"  {TEAL}│{RST}  {GRAY}{'System Engines':18s}{RST} NFTables: {nft_ok} · HAProxy: {ha_ok} · Nginx: {ngx_ok}")
    print(f"  {TEAL}│{RST}  {GRAY}{'Rules Configured':18s}{RST} {len(rules)}")
    print(f"  {TEAL}╰{'─'*69}{RST}\n")

    if not rules:
        print(f"  {GRAY}› No port forwarding rules configured yet. Login to the Web UI to add rules.{RST}\n")
    else:
        fmt = "  {:<14} {:<9} {:<11} {:<30} {}"
        print(f"{BOLD}" + fmt.format("PORT / RANGE", "PROTO", "ACTIVE", "CURRENT DESTINATION", "STATE") + f"{RST}")
        print(f"  {GRAY}{'─'*74}{RST}")
        for r in rules:
            p_disp = r.get("port_range") or r.get("port")
            proto = r.get("protocol", "both")
            proto_str = "TCP+UDP" if str(proto).lower() == "both" else str(proto).upper()
            act_prio = r.get("active_priority", 1)
            dest = next((d for d in r.get("destinations", []) if d.get("priority") == act_prio), None)
            if dest:
                d_port = dest.get("port_range") or dest.get("port", p_disp)
                dest_str = f"{dest.get('type')}: {dest.get('target')}:{d_port}"
            else:
                dest_str = "None"
            print(fmt.format(f":{p_disp}", proto_str, f"Priority #{act_prio}", dest_str, f"{GRN}● HEALTHY{RST}"))
        print()
except Exception as e:
    print(f"  Error parsing state: {e}")
PYEOF
}

import_relay_rules() {
    check_root
    ui_header "" "Import Pre-Existing Rules"
    local active_cfg
    active_cfg=$(resolve_active_config)
    msg_info "Scanning for pre-existing HAProxy & NFTables relay rules on this server..."
    python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
from core.nftables_parser import import_all_relay_rules_into_config
count, ports, logs = import_all_relay_rules_into_config('$active_cfg', deactivate_legacy=True)
for log in logs:
    print(f'   \033[38;5;44m·\033[0m {log}')
if count > 0:
    print(f'  \033[38;5;84m✓\033[0m Successfully imported {count} relay port rule(s) into XForwarder: {ports}')
else:
    print('  \033[38;5;220m!\033[0m No new unimported HAProxy or NFTables forwarding rules found.')
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
    print(f'  \033[38;5;84m✓\033[0m Successfully exported configuration ({rule_count} rules) to {target_path}')
except Exception as e:
    print(f'  \033[38;5;203m✗\033[0m Failed to export configuration: {e}', file=sys.stderr)
    sys.exit(1)
" "$target_path"
}

import_config_cli() {
    check_root
    local file_path="${1:-}"
    local mode="${2:---merge}"

    if [[ -z "$file_path" ]]; then
        ask file_path "Path to backup JSON file to import" ""
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
    print(f'  \033[38;5;203m✗\033[0m Failed to read JSON file: {e}', file=sys.stderr)
    sys.exit(1)

ok, err, info = import_config_data(payload, mode=import_mode)
if ok:
    imported_cnt = info.get('imported_count', 0)
    total_cnt = info.get('count', 0)
    backup_file = info.get('backup', '')
    print(f'  \033[38;5;84m✓\033[0m Imported {imported_cnt} rule(s) in {info.get(\"mode\")} mode (total: {total_cnt}).')
    if backup_file:
        print(f'  \033[38;5;44m›\033[0m Pre-restore atomic backup saved to: {backup_file}')
else:
    print(f'  \033[38;5;203m✗\033[0m Import failed: {err}', file=sys.stderr)
    sys.exit(1)
" "$file_path" "$clean_mode" || return 1

    systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE" >/dev/null 2>&1 || true
    msg_ok "XForwarder services restarted and synced with imported rules."
    show_status
}

backup_restore_menu() {
    ui_header "" "Backup & Restore (JSON)"
    local b_idx=0 dest="" src=""
    ui_choose b_idx 0 \
        "Export configuration to JSON file" \
        "Import configuration (Merge — preserve non-conflicting rules)" \
        "Import configuration (Replace — overwrite all existing rules)" \
        "Back to Main Menu" || return 0

    case "$b_idx" in
        0)
            ask dest "Export file path (blank = timestamped file)" ""
            export_config_cli "$dest"
            ;;
        1)
            ask src "Path to backup JSON file to import" ""
            import_config_cli "$src" "--merge"
            ;;
        2)
            msg_warn "Replace mode will overwrite all existing port forwarding rules!"
            ask src "Path to backup JSON file to import" ""
            if pick_yesno "Proceed with REPLACE mode?" n; then
                import_config_cli "$src" "--replace"
            else
                msg_info "Import cancelled."
            fi
            ;;
        3)
            return 0
            ;;
    esac
}

show_menu() {
    ui_has_input || { show_status; return 0; }
    MENU_ACTIVE=1
    local choice=0
    while :; do
        ui_header big "Control Menu"
        ui_choose choice "$choice" \
            "Show Web Dashboard Access URL" \
            "Show Live Status & Active Port Routes" \
            "Web Panel Settings (Port, User, Password, Path, SSL)" \
            "Restart XForwarder Services" \
            "View Core Engine Live Logs (Ctrl+C exits)" \
            "Update XForwarder (Auto-Migrate & Preserve Rules)" \
            "Re-install / Run Setup Wizard" \
            "Import Pre-existing Relay Rules (HAProxy & NFTables)" \
            "Backup & Restore (Export / Import JSON)" \
            "Check & Install System Dependencies" \
            "Network Performance Tuning (BBR, Sysctl & Limits)" \
            "Exit" || break

        MENU_ACTIVE=0
        UPDATED_CLI=0
        echo ""
        case "$choice" in
            0) show_web_access_info ;;
            1) show_status ;;
            2) modify_web_settings_menu ;;
            3) check_root && systemctl restart "$DAEMON_SERVICE" "$WEB_SERVICE" && msg_ok "Services restarted." ;;
            4) check_root && journalctl -u "$DAEMON_SERVICE" -f || true ;;
            5) update_xforwarder ;;
            6) install_xforwarder ;;
            7) import_relay_rules ;;
            8) backup_restore_menu ;;
            9) check_root; ensure_dependencies ;;
            10) check_root; tune_network ;;
            11) break ;;
        esac
        echo ""
        read -r -p "  Press Enter to return to menu..." _ <&"$UI_FD" || break
        if (( UPDATED_CLI )) && [[ -x "$BIN_LINK" ]]; then
            ui_restore_terminal
            exec "$BIN_LINK"
        fi
        MENU_ACTIVE=1
    done
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
            ui_header big "Initial Setup"
            msg_warn "XForwarder is not installed on this system. Starting setup wizard..."
            install_xforwarder
        else
            ui_header "" "System Update"
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
        ui_header "" "System Dependencies"
        ensure_dependencies
        ;;
    optimize|tune|tune-network)
        check_root
        ui_header "" "Kernel & BBR Tuning"
        tune_network
        ;;
    "")
        if ! is_installed; then
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

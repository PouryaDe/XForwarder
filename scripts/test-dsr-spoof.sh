#!/usr/bin/env bash
# ============================================================================
# XForwarder - Outbound IP Spoofing / DSR Compatibility Tester
# Verifies whether an Outside (Kharej) VPS and its datacenter allow outbound
# packets with spoofed source IPs (required for nftables_dsr_direct / synack),
# or block them via BCP38 / Strict uRPF / Anti-Spoofing filters.
#
# Quick Usage:
#   1) On Peer / Iran server (start temporary UDP listener):
#        bash <(curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/scripts/test-dsr-spoof.sh) --listen
#   2) On Outside server to test:
#        bash <(curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/scripts/test-dsr-spoof.sh) --outside <PEER_IP>
# ============================================================================

set -euo pipefail

PORT=55199
MODE=""
PEER_IP=""
SPOOF_IP=""
COUNT=5
TIMEOUT=180

# Allow interactive prompts even when piped (curl ... | bash)
if [[ ! -t 0 && -r /dev/tty ]]; then
    if (exec < /dev/tty) 2>/dev/null; then
        exec < /dev/tty
    fi
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

usage() {
    cat <<'EOF'
Usage:
  test-dsr-spoof.sh --listen [--port 55199] [--timeout 180]
      Run on a Peer / Iran server as a temporary UDP receiver.

  test-dsr-spoof.sh --outside <PEER_IP> [--spoof-ip <IP>] [--port 55199] [--count 5]
      Run on the Outside (Kharej) server you want to test for Spoof / DSR support.

  test-dsr-spoof.sh --local-only
      Only inspect local Linux kernel/container capabilities (does not test ISP uRPF).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --listen|-l)
            MODE="listen"
            shift
            ;;
        --outside|-o)
            MODE="outside"
            PEER_IP="${2:-}"
            shift 2
            ;;
        --spoof-ip|-s)
            SPOOF_IP="${2:-}"
            shift 2
            ;;
        --port|-p)
            PORT="${2:-55199}"
            shift 2
            ;;
        --count|-c)
            COUNT="${2:-5}"
            shift 2
            ;;
        --timeout|-t)
            TIMEOUT="${2:-180}"
            shift 2
            ;;
        --local-only)
            MODE="local"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}[ERR] Unknown option: $1${NC}" >&2
            usage
            exit 1
            ;;
    esac
done

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}[ERR] python3 is required to run this test.${NC}" >&2
    exit 1
fi

if [[ -z "$MODE" ]]; then
    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo -e "${CYAN}${BOLD}   XForwarder - IP Spoof / DSR Capability Tester${NC}"
    echo -e "${CYAN}${BOLD}============================================================${NC}"
    echo ""
    echo "  To test if an Outside server allows IP Spoofing (not blocked by"
    echo "  datacenter uRPF/BCP38), you run a temporary receiver on a Peer"
    echo "  server (e.g. Iran) and run the test on your Outside server."
    echo ""
    echo "  1) Start Receiver (Run this on Iran / Peer Server)"
    echo "  2) Test Outside Server (Run this on the Outside Server to verify)"
    echo "  3) Local Kernel/Container Checks Only (No peer test)"
    echo "  0) Exit"
    echo ""
    read -r -p "  Select [1/2/3/0]: " sel
    case "$sel" in
        1) MODE="listen" ;;
        2)
            MODE="outside"
            read -r -p "  Enter Peer/Listener Server IP: " PEER_IP
            read -r -p "  Optional custom Spoof IP [auto]: " SPOOF_IP
            ;;
        3) MODE="local" ;;
        *) exit 0 ;;
    esac
fi

if [[ "$MODE" == "outside" && -z "$PEER_IP" ]]; then
    echo -e "${RED}[ERR] --outside requires <PEER_IP>.${NC}" >&2
    exit 1
fi

if [[ "$MODE" == "outside" || "$MODE" == "local" ]]; then
    if [[ "$(id -u)" -ne 0 ]]; then
        echo -e "${RED}[ERR] Please run as root (needed for raw spoof packet sockets).${NC}" >&2
        exit 1
    fi
fi

python3 - "$MODE" "$PORT" "$PEER_IP" "$SPOOF_IP" "$COUNT" "$TIMEOUT" <<'PYEOF'
import os
import re
import sys
import time
import json
import uuid
import shutil
import socket
import struct
import subprocess

mode = sys.argv[1]
port = int(sys.argv[2])
peer_ip = (sys.argv[3] or "").strip()
spoof_ip_arg = (sys.argv[4] or "").strip()
count = max(2, min(int(sys.argv[5]), 20))
timeout_sec = max(15, min(int(sys.argv[6]), 600))

G = "\033[0;32m"
R = "\033[0;31m"
Y = "\033[1;33m"
C = "\033[0;36m"
B = "\033[1m"
N = "\033[0m"


def detect_wan_ip(target="1.1.1.1"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def detect_wan_iface():
    try:
        out = subprocess.check_output(["ip", "-o", "-4", "route", "show", "to", "default"], text=True, timeout=2)
        m = re.search(r"\bdev\s+([^\s]+)", out or "")
        return m.group(1) if m else ""
    except Exception:
        return ""


def pick_default_spoof_ip(dst_ip, wan_ip):
    """Picks a routable, non-self IPv4 close to dst_ip so strict rp_filter on the listener does not falsely drop it."""
    parts = [int(x) for x in dst_ip.split(".")]
    d = parts[3]
    for delta in (2, -2, 1, -1, 3, -3):
        cand = d + delta
        if 2 <= cand <= 253 and cand != d:
            candidate_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{cand}"
            if candidate_ip != wan_ip and candidate_ip != dst_ip:
                return candidate_ip
    return "198.51.100.77" if dst_ip != "198.51.100.77" else "198.51.100.78"


def ip_checksum(data):
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF


def send_raw_udp(src_ip, dst_ip, sport, dport, payload):
    udp_len = 8 + len(payload)
    udp_hdr = struct.pack("!HHHH", sport, dport, udp_len, 0)
    ip_hdr_zero = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, 20 + udp_len, os.getpid() & 0xFFFF, 0, 64,
        socket.IPPROTO_UDP, 0, socket.inet_aton(src_ip), socket.inet_aton(dst_ip),
    )
    ck = ip_checksum(ip_hdr_zero)
    ip_hdr = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, 20 + udp_len, os.getpid() & 0xFFFF, 0, 64,
        socket.IPPROTO_UDP, ck, socket.inet_aton(src_ip), socket.inet_aton(dst_ip),
    )
    raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    raw.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    try:
        raw.sendto(ip_hdr + udp_hdr + payload, (dst_ip, 0))
    finally:
        raw.close()


def check_local_capabilities():
    print(f"\n{C}{B}=== 1. Local Server & Kernel Readiness ==={N}")
    issues = []
    wan_ip = detect_wan_ip(peer_ip or "1.1.1.1")
    wan_if = detect_wan_iface()
    print(f"  WAN Interface / IP : {wan_if or '?'} ({wan_ip or '?'})")

    try:
        rs = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        rs.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        rs.close()
        print(f"  Raw Socket (HDRINCL): {G}OK{N}")
    except Exception as e:
        print(f"  Raw Socket (HDRINCL): {R}FAIL ({e}){N}")
        issues.append(f"Raw sockets blocked ({e}); likely container virtualization restriction.")

    for label, path in (
        ("ip_forward", "/proc/sys/net/ipv4/ip_forward"),
        ("conf.all.rp_filter", "/proc/sys/net/ipv4/conf/all/rp_filter"),
        ("conf.default.rp_filter", "/proc/sys/net/ipv4/conf/default/rp_filter"),
    ):
        try:
            val = open(path, encoding="utf-8").read().strip()
            print(f"  {label:<20}: {val}")
        except Exception:
            pass

    has_nft = bool(shutil.which("nft"))
    has_ip = bool(shutil.which("ip"))
    print(f"  nft / iproute2      : nft={'OK' if has_nft else 'MISSING'}, ip={'OK' if has_ip else 'MISSING'}")
    if not has_nft:
        issues.append("nftables (`nft`) binary not found.")
    return wan_ip, issues


if mode == "listen":
    wan_ip = detect_wan_ip()
    print(f"\n{C}{B}=== XForwarder Spoof / DSR Test Listener (UDP :{port}) ==={N}")
    print(f"  Listening on 0.0.0.0:{port} for up to {timeout_sec}s (Ctrl+C to stop)")
    print(f"  {Y}Note:{N} Make sure UDP port {port} is open in cloud/host firewall.")
    if wan_ip:
        print(f"\n  Run this on the {B}Outside{N} server you want to test:")
        print(f"    {G}curl -fsSL https://raw.githubusercontent.com/PouryaDe/XForwarder/main/scripts/test-dsr-spoof.sh | bash -s -- --outside {wan_ip} --port {port}{N}\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(1.0)

    sessions = {}
    deadline = time.time() + timeout_sec
    try:
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            msg = data.decode("utf-8", "replace").strip()
            parts = msg.split(":")
            kind = parts[0] if parts else ""
            token = parts[1] if len(parts) > 1 else ""
            if kind == "PING":
                sock.sendto(f"PONG:{token}".encode("utf-8"), addr)
            elif kind == "CTRL" and token:
                st = sessions.setdefault(token, {"ctrl": [], "spoof": []})
                st["ctrl"].append(addr[0])
                print(f"  [CTRL ] token={token[:8]} from={addr[0]}:{addr[1]}")
            elif kind == "SPOOF" and token:
                st = sessions.setdefault(token, {"ctrl": [], "spoof": []})
                st["spoof"].append(addr[0])
                print(f"  {G}[SPOOF]{N} token={token[:8]} from={addr[0]}:{addr[1]} (SPOOFED PACKET DELIVERED!)")
            elif kind == "QUERY" and token:
                st = sessions.get(token, {"ctrl": [], "spoof": []})
                resp = json.dumps({
                    "ok": True,
                    "ctrl_count": len(st["ctrl"]),
                    "ctrl_ips": list(set(st["ctrl"])),
                    "spoof_count": len(st["spoof"]),
                    "spoof_ips": list(set(st["spoof"])),
                }).encode("utf-8")
                sock.sendto(resp, addr)
                print(f"  [DONE ] token={token[:8]} -> ctrl={len(st['ctrl'])}, spoof={len(st['spoof'])}")
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
    sys.exit(0)


wan_ip, local_issues = check_local_capabilities()
if mode == "local":
    if local_issues:
        print(f"\n{R}Local checks failed:{N}")
        for x in local_issues:
            print(f"  - {x}")
        sys.exit(1)
    print(f"\n{G}Local kernel capabilities look OK. Run with --outside <PEER_IP> to test datacenter Anti-Spoof/uRPF.{N}")
    sys.exit(0)

if local_issues:
    print(f"\n{R}[FAIL] Local prerequisites blocked Spoof/DSR:{N}")
    for x in local_issues:
        print(f"  - {x}")
    sys.exit(2)

if not wan_ip:
    print(f"{R}[ERR] Could not determine local WAN IPv4.{N}")
    sys.exit(1)

spoof_ip = spoof_ip_arg or pick_default_spoof_ip(peer_ip, wan_ip)
if spoof_ip == peer_ip:
    print(f"{Y}[WARN] Spoof IP equals Listener IP ({peer_ip}); Linux may drop self-source packets locally as Martian.{N}")

token = uuid.uuid4().hex[:12]
print(f"\n{C}{B}=== 2. Datacenter Egress Spoof / uRPF Test ==={N}")
print(f"  Peer Listener : {peer_ip}:{port}/udp")
print(f"  Real Source   : {wan_ip}")
print(f"  Spoof Source  : {spoof_ip}")

# Verify listener reachability first so firewall blocks don't look like spoof drops
probe_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
probe_sock.settimeout(2.0)
reachable = False
for _ in range(3):
    try:
        probe_sock.sendto(f"PING:{token}".encode("utf-8"), (peer_ip, port))
        reply, _ = probe_sock.recvfrom(1024)
        if reply.decode("utf-8", "replace").startswith(f"PONG:{token}"):
            reachable = True
            break
    except Exception:
        time.sleep(0.3)

if not reachable:
    probe_sock.close()
    print(f"\n{R}[ERR] Could not reach listener at {peer_ip}:{port}/udp.{N}")
    print(f"  Make sure you ran `--listen --port {port}` on {peer_ip} and UDP/{port} is not blocked.")
    sys.exit(1)

print(f"  Listener Ping : {G}REACHABLE{N}")
print(f"  Sending {count} control + {count} spoofed UDP packets...")

for i in range(count):
    send_raw_udp(wan_ip, peer_ip, 41000 + i, port, f"CTRL:{token}".encode("utf-8"))
    send_raw_udp(spoof_ip, peer_ip, 42000 + i, port, f"SPOOF:{token}:{spoof_ip}".encode("utf-8"))
    time.sleep(0.06)

time.sleep(1.0)

result = None
for _ in range(3):
    try:
        probe_sock.sendto(f"QUERY:{token}".encode("utf-8"), (peer_ip, port))
        raw_resp, _ = probe_sock.recvfrom(4096)
        result = json.loads(raw_resp.decode("utf-8", "replace"))
        break
    except Exception:
        time.sleep(0.4)
probe_sock.close()

if not result or not result.get("ok"):
    print(f"\n{R}[ERR] Failed to retrieve test results from {peer_ip}:{port}.{N}")
    sys.exit(1)

ctrl_ok = int(result.get("ctrl_count", 0))
spoof_ok = int(result.get("spoof_count", 0))

print(f"\n{C}{B}=== 3. Result ==={N}")
print(f"  Real IP Packets Delivered    ({wan_ip})   : {ctrl_ok}/{count}")
print(f"  Spoofed IP Packets Delivered ({spoof_ip}) : {spoof_ok}/{count}\n")

if ctrl_ok > 0 and spoof_ok > 0:
    print(f"{G}{B}[PASS] SPOOF / DSR IS SUPPORTED!{N}")
    print("  This server & datacenter allow outbound packets with spoofed source IPs.")
    print("  Both `nftables_dsr_direct` and `nftables_dsr_synack` will work cleanly.")
    sys.exit(0)
elif ctrl_ok > 0 and spoof_ok == 0:
    print(f"{R}{B}[FAIL] SPOOF / DSR IS BLOCKED BY DATACENTER (Anti-Spoofing / uRPF / BCP38)!{N}")
    print(f"  Control packets arrived ({ctrl_ok}/{count}), but 0/{count} spoofed packets escaped.")
    print("  Recommendations:")
    print("    - Do NOT use `nftables_dsr_direct`, `nftables_dsr_synack`, or `nftables_dsr` on this VPS.")
    print("    - Use symmetric forwarding instead (`haproxy` or standard `nftables` over your tunnel).")
    sys.exit(2)
else:
    print(f"{Y}[WARN] Inconclusive: control packets did not arrive ({ctrl_ok}/{count}). Check UDP filtering.{N}")
    sys.exit(1)
PYEOF

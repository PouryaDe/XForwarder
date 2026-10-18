---
name: systematic-debugging
description: "4-phase systematic debugging procedure for relay forwarding, probe failures, port collisions, and service anomalies."
---

# Systematic Debugging Skill (XForwarder)

Follow this rigorous 4-phase debugging procedure when investigating routing anomalies, probe flaps, or service failures.

---

## Phase 1: Evidence Gathering & Observation
Collect objective data before making any changes:

```bash
# 1. Inspect active runtime state
cat /run/xforwarder/state.json | jq .

# 2. Check live systemd journal logs
journalctl -u xforwarder -n 50 --no-pager

# 3. Check socket binding on the affected port
ss -tulpn | grep :<port>

# 4. Check active NFTables rules
nft list table ip xfwd_orchestrator
```

## Phase 2: Path Isolation & Testing
Isolate the two forwarding paths to determine whether the issue is local or remote:

1. **Test Primary Destination (IPv6 HAProxy):**
   ```python
   python3 -c "import socket; s=socket.create_connection(('<TARGET_IPV6>', <PORT>), timeout=3); print('OK'); s.close()"
   ```
2. **Test Backup Destination (IPv4 Tunnel):**
   ```bash
   ping -c 3 -W 2 <TUNNEL_IP>
   nc -zvw 3 <TUNNEL_IP> <PORT>
   ```
3. **Lock Path with Manual Override:**
   Lock the rule to Priority 1 or Priority 2 via API or UI to see if traffic flows when probing is eliminated.

## Phase 3: Root Cause Analysis
Determine the exact failure point:
- **Port Collision:** Port is bound by HAProxy while an NFTables DNAT rule is active simultaneously.
- **Probe Failure:** Uplink socket probe timed out due to ISP routing or firewall dropping SYN packets.
- **Masquerade Missing:** Tunnel interface packets are leaving with WAN IP instead of tunnel IP because interface name doesn't match `oifname` masks.
- **Kernel IP Forwarding Disabled:** `net.ipv4.ip_forward` was reset to 0 after server reboot.

## Phase 4: Fix, Verification & Experience Logging
1. Apply the minimal surgical fix.
2. Run automated verification:
   ```bash
   python .agents/scripts/verify-all.py
   ```
3. Restart daemons and verify client traffic:
   ```bash
   xforwarder restart
   xforwarder status
   ```
4. If a non-obvious root cause or edge case was discovered, log it in `.agents/experiences/`:
   ```bash
   python .agents/scripts/log-experience.py "Description of Issue" Networking
   ```

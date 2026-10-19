---
trigger: always_on
description: Architectural principles, multi-path priority failover logic, and zero-collision forwarding rules for XForwarder.
---

# Architecture & Failover Rules (XForwarder)

## 1. System Overview
XForwarder runs on intermediate relay servers (e.g., Iran VPS) to route inbound client traffic towards foreign exit servers across multiple redundant paths.

```text
Inbound Traffic (Iran WAN)
          │
          ├──> Priority 1: Direct IPv6 Relay via HAProxy (TCP/UDP user-space)
          └──> Priority 2: Kernel L3 Tunnel via NFTables DNAT (GRE, IPIP, FakeTCP, AmneziaWG)
```

## 2. Zero-Collision Rule (Mandatory)
A port must **NEVER** be bound by HAProxy and forwarded by NFTables DNAT at the same time:
1. When a port rule's active priority is **Priority 1 (HAProxy)**:
   - HAProxy binds `*:<port>` in `/etc/haproxy/haproxy.cfg`.
   - Any NFTables DNAT rule for that port is removed from `table ip xfwd_orchestrator`.
2. When a port rule fails over to **Priority 2 (NFTables)**:
   - The HAProxy listener for `<port>` is removed or deactivated.
   - Kernel DNAT rules are added to `table ip xfwd_orchestrator prerouting` chain:
     `iifname "<WAN>" (tcp|udp) dport <port> dnat to <tunnel_target>:<target_port>`.

## 3. Failover & Recovery Dynamics
- **Detection Cycle**: Configurable via `check_interval_seconds` (default: 8s).
- **Failure Threshold**: Configurable via `failure_threshold` (default: 3 consecutive failed probes before marking `failed`).
- **Recovery Threshold**: Configurable via `recovery_threshold` (default: 3 consecutive healthy probes before marking `healthy`).
- **Failback**: As soon as Priority 1 recovers, the engine automatically switches traffic back to Priority 1 (unless `force_override` is active).
- **Force Override Modes**:
  - `0`: Auto Failover (default)
  - `1`: Force Priority 1 (Primary)
  - `2`: Force Priority 2 (Backup)

## 4. State & Configuration Persistence
- **Persistent Configuration**: `/etc/xforwarder/config.json` (fallback: `/etc/forward-manager/config.json` or `config/config.json`).
- **Runtime Ephemeral State**: `/run/xforwarder/state.json` (fallback: `/run/forward-manager/state.json`).
- **Atomic Writes**: Never write directly to configuration or state files without atomic renaming (`tmp.<pid>` -> `os.replace`).

## 5. Strict Interface & Route Isolation for Destination Probes
- **No WAN Leakage for Private/Tunnel Targets:** Tunnel destinations (e.g. `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`, IPv6 ULA) must never be probed over the WAN interface (`eth0`). If `ip route get <target>` routes to the WAN interface, the tunnel interface is undefined on the host and the probe MUST be marked `failed` immediately.
- **Explicit Interface Binding:** When `tunnel_iface` is specified, verify `/sys/class/net/<iface>` exists and is UP. All ICMP and TCP probes must be strictly bound to `<tunnel_iface>` (`ping -I <iface>`, `SO_BINDTODEVICE`).
- **Zero Synthetic Guessing:** Never synthesize or guess arbitrary peer IP targets (e.g. `+1` or `-1` on the last octet). A tunnel target must strictly be an explicit peer configured on the interface or a configured rule destination.


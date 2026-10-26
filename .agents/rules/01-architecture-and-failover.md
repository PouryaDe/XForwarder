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

## 3. Two-Tier Intelligent Failover & Route Quality Architecture
- **ICMP Multi-Probe Precision (10-Ping Sampling)**:
  - Probing uses native 10-probe ICMP ping bursts (`ping -c 10 -i 0.2 -W 1`) with 2-packet tail padding (`ICMP_TAIL_PADDING = 2`), `LC_ALL=C`, and IPv4/IPv6 support.
  - Per-reply sequence parsing (`parse_ping_replies`) evaluates strictly sequence 1..10, eliminating false packet loss caused by iputils ping's early exit timer on long RTTs.
  - Extracts average latency, packet loss, and within-cycle jitter (`mdev` on Linux / `(max-min)/2` fallback).
  - Cross-rule deduplicated parallel probing (`_probe_all_destinations`) executes via a persistent worker pool, probing each unique destination IP only once per cycle regardless of port count.
  - **60-Second In-Memory Target Cache**: Probes execute 10 consecutive pings and persist metrics in memory for 60 seconds (`target_probe_interval_seconds = 60s`). All rules sharing the same destination IP consume identical latency, loss, and composite quality scores, guaranteeing synchronized failovers and eliminating inter-port latency divergence. Route or interface invalidation immediately evicts the cached entry.
- **Two-Tier Decision Engine (`core/route_quality.py`)**:
  - **Tier 1 (Emergency Outage / Sustained Critical Loss Bypass)**:
    - Triggers on total failure (100% loss), route invalidation (WAN leak), or sustained critical degradation ($\ge \text{critical\_loss\_percent}$, default: 30% across $\ge 2$ cycles in the short window).
    - Active outages trigger micro-probe bursts (`_fast_confirm_burst`, 5 packets, `BURST_TCP_TIMEOUT = 0.5s`).
    - Bypasses minimum hold-down and streak confirmation immediately.
    - Critical switches execute conntrack flushing (`conntrack -D`) to clear dead states.
    - Transient single-cycle packet loss degrades quality score without triggering disruptive emergency failovers.
  - **Tier 2 (Conservative Planned Quality Switching)**:
    - Designed to prevent frequent, disruptive route flapping on live client sessions.
    - Evaluates performance over a 5-minute sliding window (`quality_window_seconds = 300s`) requiring $\ge 60\%$ window warm-up.
    - **10-Minute Hold-Down**: Newly activated routes remain locked for at least 10 minutes (`min_hold_seconds = 600s`).
    - **Packet Loss Shield**: Never trades lower latency for higher packet loss (`cand_loss > curr_loss + 0.5` is rejected).
    - **Significant Advantage Margin**: Candidate must beat current score by $\ge 20\%$ (`hysteresis_percent = 20%`) AND $\ge 15$ points.
    - **120-Second Streak Confirmation**: Candidate must maintain superior quality continuously for 120 seconds (`switch_confirm_seconds = 120s`). UI displays countdown badge (`Switch in Ns`).
    - **Socket Preservation**: Planned switches reload HAProxy seamlessly without flushing conntrack, preserving existing client connections while new traffic routes via the superior path.
- **Composite Quality Formula**:
  $$\text{Composite Score} = \text{Avg Latency (ms)} + 2 \times \text{Jitter (ms)} + 20 \times \text{Loss Pct} + \text{Priority Bias}$$
- **Anti-Flap Damping**: $\ge 3$ route switches within 10 minutes triggers flap damping, dynamically doubling `min_hold` (to 20m) and `cooldown` (to 2m).
- **Force Override Modes**:
  - `0`: Auto Failover (default)
  - `1`: Force Priority 1 (Primary)
  - `2`: Force Priority 2 (Backup)
  - *Changing override mode immediately clears hold-down guards and recalculates best priority via `pick_best_now`.*

## 4. State & Configuration Persistence
- **Persistent Configuration**: `/etc/xforwarder/config.json` (fallback: `/etc/forward-manager/config.json` or `config/config.json`).
- **Runtime Ephemeral State**: `/run/xforwarder/state.json` (fallback: `/run/forward-manager/state.json`).
- **Atomic Writes**: Never write directly to configuration or state files without atomic renaming (`tmp.<pid>` -> `os.replace`).

## 5. Strict Interface & Route Isolation for Destination Probes
- **No WAN Leakage for Private/Tunnel Targets:** Tunnel destinations (e.g. `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`, IPv6 ULA) must never be probed over the WAN interface (`eth0`). If `ip route get <target>` routes to the WAN interface, the tunnel interface is undefined on the host and the probe MUST be marked `failed` immediately.
- **Bilateral Tunnel Peer Resolution:** Point-to-point tunnel interfaces (e.g. GRE, IPIP, WireGuard /30) between Iran and foreign relay servers conventionally allocate bilateral peer addresses (`.1` ↔ `.2`, or `/30` partner octets `(last_oct % 4 == 1 ? +1 : -1)`). If the kernel does not explicitly provide a peer address and no matching rule destination is configured, the system auto-resolves the bilateral counterpart as the peer endpoint and ping target (bound strictly to `<tunnel_iface>`). Arbitrary guessing for non-point-to-point subnets is forbidden.

## 6. Long-Term Packet Loss Monitoring & Deduplicated Probing
- **Dedicated 50-Probe Engine:** Precise packet loss evaluation uses `ping [ip] -c 50 -i 0.2 -W 1` (<10s).
- **Scheduled Rounds & Deduplication:** Background daemon (`LossMonitorScheduler`) triggers a round every 15 minutes (`LOSS_CHECK_INTERVAL_SECONDS = 900`). All targets across configured rules and ports are deduplicated (`get_unique_targets_from_config`), guaranteeing that an IP configured on 10 different ports is probed only ONCE per round.
- **SQLite Persistence & 30-Day Retention:** Probe history is recorded in `/etc/xforwarder/metrics.db` (WAL mode). Records older than 30 days are automatically pruned (`prune_old_metrics`) to prevent disk bloat.
- **Parameter Bounds & Injection Shielding:** Target hosts and interface flags must be strictly sanitized against command argument injection.



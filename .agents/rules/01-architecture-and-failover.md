---
trigger: model_decision
always_on: false
description: Architectural principles, multi-path priority failover logic, route quality scoring, L4/blackhole probing, and zero-collision forwarding rules for XForwarder. Load when editing failover, probing, or routing logic.
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
  - **60-Second In-Memory Target Cache & 15-Second Fast Liveness**: Probes execute 10 consecutive pings and persist metrics in memory for 60 seconds (`target_probe_interval_seconds = 60s`). Every 15 seconds (`fast_liveness_interval_seconds = 15s`), a fast liveness check tests target reachability; if unresponsive, the cached metrics are invalidated immediately and Tier 1 emergency failover triggers without waiting for the 60s cycle. When responsive, the fine-grained 10-ping average latency and composite score remain stable. Target routes that become invalid or dropped are evicted immediately from cache. Short aggregation windows dynamically scale (`max(120.0, probe_interval * 2.5)`) with recent sample tolerance fallback to eliminate phantom window expiration.
- **Two-Tier Decision Engine (`core/route_quality.py`)**:
  - **Tier 1 (Emergency Outage / Sustained Critical Loss Bypass)**:
    - Triggers on total failure (100% loss), route invalidation (WAN leak), or sustained critical degradation ($\ge \text{critical\_loss\_percent}$, default: 30% across $\ge 2$ cycles in the short window).
    - Active outages trigger micro-probe bursts (`_fast_confirm_burst`, 5 packets, `BURST_TCP_TIMEOUT = 0.5s`).
    - Bypasses minimum hold-down and streak confirmation immediately.
    - Critical switches execute conntrack flushing (`conntrack -D`) to clear dead states.
    - Transient single-cycle packet loss degrades quality score without triggering disruptive emergency failovers.
    - **Deadlock Prevention on Complete Outage & Severe Loss**: If the active path is completely dead (100% loss) or severely degraded (>=60% loss with >=20% candidate advantage), the engine selects the candidate with the lowest packet loss, preventing traffic blackholing on dead routes.
    - **Degraded Backup Escape & Multi-Priority Failback**: If active on a backup path (Priority > 1) and packet loss occurs, the engine immediately fails back to Priority 1 or any cleaner higher-priority path (`1..current_active-1`) preserving active client sockets without conntrack flush. Higher backup paths are evaluated naturally without being gated by the primary latency ceiling, and individual rules can define custom `max_primary_latency_ms` overrides.
  - **Tier 2 (Conservative Planned Quality Switching)**:
    - Designed to prevent frequent, disruptive route flapping on live client sessions.
    - Evaluates performance over a 5-minute sliding window (`quality_window_seconds = 300s`) requiring $\ge 60\%$ window warm-up.
    - **10-Minute Hold-Down with Loss Exemption**: Newly activated routes remain locked for at least 10 minutes (`min_hold_seconds = 600s`) to prevent flapping between clean routes. However, if the active route experiences packet loss (degraded / >=5%) and an eligible candidate offers lower packet loss, the hold guard is waived to prevent trapping client sessions on degraded paths.
    - **Packet Loss Shield**: Never trades lower latency for higher packet loss (`cand_loss > curr_loss + 0.5` is rejected).
    - **Significant Advantage Margin**: Candidate must beat current score by $\ge 20\%$ (`hysteresis_percent = 20%`) AND $\ge 15$ points.
    - **120-Second Streak Confirmation & Anti-Reset Guard**: Candidate must maintain superior quality continuously for 120 seconds (`switch_confirm_seconds = 120s`). UI displays countdown badge (`Switch in Ns`). The Anti-Reset Guard prevents candidate streak resets caused by slight ping jitter between two close backup routes.
    - **Priority 1 Primary Route Stickiness & 150ms Ceiling (Primary Anchor Pattern)**: When Priority 1 is active, the engine never switches away to backup routes merely for lower ping (10-30ms lower ping). It strictly stays on Priority 1 unless Priority 1 packet loss is worse than candidate (`curr_loss > cand_loss + 0.5`), or latency exceeds 150ms (`max_primary_latency_ms = 150`), or upon critical failure.
    - **Intermediate Relay Server (`is_relay`) Subsystem**: Intermediate tunnel and relay hops with partial-hop ping measurements can be explicitly marked (`is_relay: true`). The engine guarantees that viable Priority 1 (`loss <= 1%`, `latency <= 150ms`) is never superseded by intermediate relay ping, and triggers guaranteed failback to Priority 1 when active on an intermediate relay.
    - **Socket Preservation**: Planned switches reload HAProxy seamlessly without flushing TCP conntrack, preserving existing TCP client connections while new traffic routes via the superior path. When a planned switch crosses between kernel DNAT (`nftables`) and user-space proxies (`nginx`/`haproxy`) on a `udp` or `both` rule, only UDP conntrack (`proto="udp"`) is flushed **after** `sync_firewall_and_proxies()` so continuous UDP/WireGuard traffic cannot remain trapped in kernel NAT. In contrast, hard outages ('critical'), disabling the active priority ('disabled_active_fallback'), and administrative overrides ('override') execute targeted per-port conntrack flushes (`flush_conntrack(port)`) **after** firewall/proxy synchronization (`sync_firewall_and_proxies()` / `sync_rules_and_notify()`) to purge stale states without race-condition NAT recreation or affecting other ports.
    - **Switch Decision Logs & Modal UI**: Every priority switch records an immutable audit log detailing old/new priority, decision reason, packet loss, latency, and human-readable explanation, displayed in the dashboard via `#switchLogsModal` and per-rule decision banners.
- **Composite Quality Formula**:
  $$\text{Composite Score} = \text{Avg Latency (ms)} + 2 \times \text{Jitter (ms)} + 20 \times \text{Loss Pct} + \text{Priority Bias}$$
- **Anti-Flap Damping**: $\ge 3$ route switches within 10 minutes triggers flap damping, dynamically doubling `min_hold` (to 20m) and `cooldown` (to 2m).
- **Force Override Modes**:
  - `0`: Auto Failover (default)
  - `1`: Force Priority 1 (Primary)
  - `2`: Force Priority 2 (Backup)
  - *Changing override mode immediately clears hold-down guards, flushes port conntrack, and recalculates best priority via `pick_best_now`.*

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
- **In-Panel Display & Tooltip Age:** Web UI renders the latest 50-probe packet loss beside each path's ping readout (`.loss50-pill`) with hover tooltip indicating the test age (e.g. `Tested 4m ago`). Manual 'Test Loss' button is retired.
- **Parameter Bounds & Injection Shielding:** Target hosts and interface flags must be strictly sanitized against command argument injection.

## 7. Dual-Feedback L4 Port & Traffic Blackhole Detection
- **L4 Protocol-Aware TCP Probing (`probe_destination_l4_tcp`)**:
  - Evaluates actual Layer-4 TCP SYN-ACK reachability to `(target, target_port)` with strict `sanitize_target_host()` validation, bounded timeouts (`1.5s`), `SO_BINDTODEVICE` when `iface` is given, and 15-second thread-safe in-memory caching (`_check_l4_port_cached`).
  - **No ICMP Fallback for HAProxy TCP**: When a HAProxy TCP/both route fails L4 TCP probing (e.g. IPv6 answers ICMP ping but firewall/ISP blocks the TCP port), it is immediately marked `failed` (`packet_loss=100%`, `packets_received=0`) and NEVER falls back to ICMP ping. Non-HAProxy routes (`nftables` tunnel interfaces, `nginx`, and UDP) preserve ICMP fallback compatibility.
- **HAProxy C-Native Backend Health Integration**:
  - HAProxy listener entries (`listen fwd_<rule_port>`) attach `check inter 3s fall 2 rise 2` on `server srv_<rule_port>`.
  - `read_haproxy_backend_health()` parses `show stat` rows from `/run/haproxy/admin.sock`, cached for 3s (`_get_cached_haproxy_backend_health`), keying strictly on `rule_port`. When `status == "DOWN"`, active routes trigger immediate Tier 1 emergency failover.
- **In-Band Asymmetric Traffic Blackhole Detection (`TrafficCollector.check_traffic_blackhole`)**:
  - Monitors per-`rule_port` RX/TX byte deltas per collection cycle (`_collect_seq`).
  - Flags a traffic blackhole only when incoming client traffic is significant (`RX >= 20480` bytes) while server return traffic collapses (`TX == 0` or `TX < 0.01 * RX`) across `>= 2` distinct collection cycles.
  - Sequence deduplication prevents rapid engine loops (`run_loop`) from double-counting the same delta sample; silent periods (`RX == 0`) reset deltas and streaks; priority transitions invoke `reset_port_blackhole(rule_port)` so newly activated routes start clean.
  - Exempts `nftables_dsr` (stateless upload-only DSR) where zero `TX` on the ingress relay is expected by design.

## 8. Health-Aware Load-Balanced Pools (NFTables & Nginx)
- **Supported Paths & Limits:** Multi-target load balancing (`lb_enabled: true`) is allowed strictly on standard `nftables` and `nginx` destinations with up to `MAX_LB_TARGETS = 16` nodes (`ip`, optional `port`, `weight` `1..100`, `enabled`, `tunnel_iface`). Single-target paths (`haproxy`, `nftables_dsr`, `nftables_dsr_relay`) ignore/reject `lb_enabled`.
- **Pool Evaluation & Dynamic Pruning:** `_evaluate_lb_destination()` probes every enabled pool member (reusing the 60s/15s IP cache) and builds the effective active subset (`_effective_lb_ips`), applying re-admission hysteresis so recovered nodes do not flap back immediately.
- **Targeted Session Cleanup:** Removing a dead node from a live pool queues `reply_src` conntrack flushes (`_pending_targeted_conntrack_flushes`) executed *after* NFTables/Nginx sync, dropping only sessions bound to the failed backend IP while preserving live client connections on surviving nodes.
- **Pool Exhaustion Failover:** Priority-level failover activates only when zero healthy enabled backends remain in the pool (or an asymmetric blackhole affects the active pool).
- **Zero-Redundancy Metrics & Import Sync:** `core/metrics.py` (`get_unique_targets_from_config`) deduplicates all `lb_targets` IPs alongside primary destination IPs, and `core/service_manager.py` preserves Nginx multi-server `upstream` blocks cleanly across sync/import.

## 9. Asymmetric SYN-ACK & Direct-Return DSR (`nftables_dsr_synack` / `nftables_dsr_direct`)
- **Iran Server (`nftables_dsr_synack`):** Forwards inbound client TCP traffic statelessly (`notrack`) via `tunnel_iface` to the Outside tunnel IP (`target:port`), translates `SYN-ACK` packets returned through the tunnel back to `spoof_ip` (Iran public IP) and client port, and exempts traffic blackhole checks since bulk download bypasses Iran.
- **Outside Server (`nftables_dsr_direct`):** Marks local `SYN-ACK` responses with `fwmark 0x42600001+` to return through `ingress_iface` via isolated FIB table `42600+` (`throw <spoof_ip>/32`, `default dev <ingress_iface>`), while rewriting non-`SYN-ACK` download packets egressing WAN directly to `<spoof_ip>:<client_port>`. Policy routing inspection safely treats non-existent kernel FIB tables as empty before slot creation.
- **Optional 3rd-Hop Exit Bridge (`exit_target` / `exit_port`):** When Xray/3x-ui runs on a 3rd server without spoof support, `nftables_dsr_direct` validates `exit_target` + `exit_port` (rejecting self-loops and protected-port collisions), emits a bound HAProxy zero-copy splice listener (`bind <local_tunnel_ip>:<backend_port>`) toward `<exit_target>:<exit_port>`, and monitors L4 TCP + ICMP health of the exit endpoint once `ingress_iface` is confirmed UP.




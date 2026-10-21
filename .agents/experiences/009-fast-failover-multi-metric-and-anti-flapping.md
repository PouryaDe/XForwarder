# Experience 009: Fast Sub-Second Failover, Multi-Metric Evaluation & Anti-Flapping Stability

## Context & Motivation
In high-throughput relay setups (e.g. Iran intermediate VPS forwarding traffic to foreign endpoints), traditional health probing suffered from two major limitations:
1. **Slow Failure Detection & Client Drops**: Binary socket probing over standard intervals (8 seconds, requiring 3 consecutive failures = 24 seconds) caused clients to experience noticeable connection blackouts during upstream route failure.
2. **Ping-Pong Route Oscillation (Flapping)**: Routing decisions based solely on raw millisecond ping differences caused rapid, disruptive switching back and forth whenever two uplinks had closely fluctuating latencies (e.g., 48ms vs 52ms).
3. **Ignoring Real Packet Loss**: A server could have a 30ms latency on successful probes while suffering 40% packet drops, yet the engine would treat it as completely healthy.

## Architectural Solutions Implemented

### 1. Rapid Failure Detection & Confirmation Burst (<1s)
- **Fast Probe Burst**: When an active route probe fails or times out, the engine does not wait 24 seconds. It immediately executes `_fast_confirm_burst(dest, port, burst_count=3, timeout=0.25, interval=0.1)`.
- If 3 consecutive micro-probes fail within ~800ms, the destination is immediately confirmed as failed.
- **Emergency Failover Bypass**: When an active route suffers total failure (100% packet loss), any active cooldown hold-down timer is bypassed immediately, triggering instant sub-second failover.

### 2. Multi-Metric Composite Quality Scoring
- **Sliding Window History**: Destinations maintain a rolling ring-buffer history ($W = 8$ probe samples) tracking both `latency_ms` and boolean `success`.
- **Rolling Packet Loss Calculation**: `loss_pct = (failures / total_samples) * 100.0`.
- **Composite Score Formula**:
  $$\text{Composite Score} = \text{Avg Latency (ms)} + (\text{Loss Pct} \times \text{loss\_penalty\_weight})$$
  *(Default `loss_penalty_weight = 10`)*. A route with 40ms latency and 10% packet loss evaluates to $40 + 100 = 140$, making it correctly deprioritized compared to a 60ms route with 0% loss (Score = 60).
- **Max Acceptable Loss Ceiling**: Destinations with packet loss exceeding `max_acceptable_loss` (default: 25%) are marked as degraded and disqualified from automatic selection if an alternative healthy route exists.

### 3. Anti-Flapping Route Damping & 10% Hysteresis
- **Route Cooldown Hold-Down Timer**: Following an automatic switch, a route enters a hold-down cooldown period (`cooldown_seconds = 60s`), preventing premature switches.
- **10% Hysteresis Advantage Requirement**: An alternative route cannot take over solely because it is 1ms faster; its composite quality score must be at least **10% better** (`score_alt <= score_current * (1 - 0.10)`).
- **Flap Damping Multiplier**: The engine records switch timestamps in a 10-minute sliding window. If a rule experiences $\ge 3$ switches within 10 minutes, the hold-down cooldown period is dynamically doubled (e.g. 120s) with a UI "Flap Guard" badge.
- **Asymmetric Failback**: While failing over away from a broken route is rapid, failback to a recovered primary route requires sustained recovery with 0% packet loss over the evaluation window.
- **Instant Manual Override**: Manual overrides (`POST /api/override`) by the administrator immediately clear cooldown timers and force immediate routing.

### 4. Zero-Collision Hot Runtime Handover & Nginx Lifecycle
- **Dynamic HAProxy Runtime Socket (`/run/haproxy/admin.sock`)**: Native `AF_UNIX` client toggles frontends without full service reloads.
- **Zero-Collision Invariant**: Exactly one engine (HAProxy, NFTables, or Nginx) handles a given port at any time. When switching priority, the departing engine releases the listener before the arriving engine binds it.
- **Nginx Dynamic Lifecycle**: When zero rules utilize Nginx, the daemon stops Nginx (`systemctl stop nginx`) to free memory and sockets. When Nginx rules become active, Nginx is automatically started or reloaded.
- **Conntrack TCP State Flushing**: Active kernel conntrack states for switched ports are flushed to prevent stale connection hangs.

### 5. Web UI Real-Time Visibility
- **Quality Readout**: Rule cards display real-time loss percentage (`0% loss`), quality composite score tooltips, and degraded status warnings.
- **Cooldown & Flap Badges**: Active hold-down timers (`Hold 42s`) and anti-flapping guard (`Flap Guard`) badges appear reactively on affected cards.
- **Smart DOM Fingerprint Diffing**: Updated `computeRulesFingerprint()` to incorporate cooldown seconds and composite scores without unnecessary DOM destruction.

## Key Invariants & Lessons
- `ms <= 0` latency suppression in `web/app.js` must be preserved for backward compatibility with test assertions.
- Manual administrator action must always supersede automated anti-flap timers.
- Configuration migration (`migrate_and_normalize_config`) must safely assign all 6 parameters with clamping to sensible limits (e.g., hysteresis between 5% and 50%).

# Experience 013: Two-Tier Intelligent Route Switching & Jitter Monitoring

## Context & Motivation
In intermediate relay operations, frequent route switching causes connection drops, TCP resets, and degraded user experience on real-time protocols (VoIP, SSH, live streaming). While rapid failover is essential for hard outages, switching routes on transient latency fluctuations or marginal improvements causes disruptive flapping. Furthermore, upstream proxies (e.g., Xray, Trojan) or network interference often exhibit high jitter and packet loss before complete failure.

## Key Decisions & Architectural Changes
1. **10-Ping Sampling with Jitter Extraction**:
   - Upgraded routine destination probing from single-socket tests to native 10-probe ICMP bursts (`ping -c 10 -i 0.2 -W 1`) with `LC_ALL=C` and IPv4/IPv6 compatibility.
   - Extracted within-cycle jitter (`mdev` on Linux / `(max-min)/2` fallback) and integrated root-mean-square jitter into rolling metrics.
   - Deduplicated unique target endpoints across all rules to probe each unique IP/interface endpoint strictly once per cycle via a persistent worker pool (`ThreadPoolExecutor`).

2. **Two-Tier Decision Engine (`core/route_quality.py`)**:
   - **Tier 1 (Emergency Outage / Critical Loss Bypass)**:
     - Hard failures (100% loss), route invalidations, or critical degradation ($\ge 30\%$ packet loss) bypass hold times and streak confirmation immediately.
     - Outages on active routes trigger a sub-second micro-probe burst (`_fast_confirm_burst`, <1s confirmation).
     - Critical switches flush stale kernel conntrack states (`conntrack -D`).
   - **Tier 2 (Conservative Planned Quality Switching)**:
     - Evaluates composite performance over a 5-minute sliding window (`quality_window_seconds = 300s`) requiring $\ge 60\%$ window warm-up.
     - Enforces a 10-minute hold-down guard (`min_hold_seconds = 600s`).
     - **Packet Loss Protection**: Never trades lower latency for higher packet loss (`cand_loss > curr_loss + 0.5` rejected).
     - **20% & 15-Point Score Margin**: Candidate must beat current route by $\ge 20\%$ (`hysteresis_percent = 20%`) AND $\ge 15$ points.
     - **120-Second Streak Confirmation**: Candidate must maintain superior quality continuously for 120 seconds (`switch_confirm_seconds = 120s`). UI displays countdown badge (`Switch in Ns`).
     - **Socket Preservation**: Planned switches reload HAProxy seamlessly without flushing conntrack, preserving existing client connections.

3. **Composite Quality Scoring Formula**:
   $$\text{Score} = \text{Avg Latency (ms)} + 2 \times \text{Jitter (ms)} + 20 \times \text{Loss Pct} + \text{Priority Bias}$$

4. **Flap Damping & Safe State Persistence**:
   - $\ge 3$ route switches in 10 minutes dynamically doubles `min_hold` to 20m and `cooldown` to 2m.
   - Core engine persists priority transitions via atomic partial merging (`_persist_active_priorities`), eliminating lost updates when rules are added/edited in the web dashboard during a probe cycle.
   - `/api/status` strips raw probe samples before serialization, keeping the API payload lean and fast.

## Verification & Impact
- 162 unit tests pass 100% across all 13 test suites (`tests/test_route_quality.py`, `tests/test_fast_failover_and_antiflap.py`, `tests/test_migration.py`, etc.).
- Antigravity verification pipeline (`.agents/scripts/verify-all.py`) verified syntax, anti-pattern compliance, and schema migration without external pip dependencies.

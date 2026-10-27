# Experience 016: Fix Window Expiration Loop and Switch Decision Logging

**Date:** 2026-10-27  
**Category:** Routing & Quality Engine  
**Status:** Active  

---

## 1. Context & Motivation
Under two-tier intelligent route switching with intermediate relay failover, a critical flapping bug was observed:
Routes would periodically transition to `DEGRADED` with a phantom `Loss: 100.0%` subtitle, trigger Tier 1 emergency failover to a backup tunnel (e.g. NFTables / Mid Server), and when both routes returned to `HEALTHY`, the engine would enter streak confirmation (`Switch in 120s... 94s`) to return to Priority 1. However, before the 120s countdown could complete, the streak would abruptly reset and the cycle would repeat indefinitely without ever restoring Priority 1.

Furthermore, operators lacked transparent visibility into the exact rationale behind each priority switch in daemon logs and dashboard feeds.

## 2. Root Cause / Core Dynamics
1. **Window Size Mismatch (`window_seconds=40.0` vs `probe_interval=60.0s`)**:
   Full ICMP 10-ping probes are deduplicated and cached for 60 seconds (`target_probe_interval_seconds = 60s`). However, short rolling window aggregation hardcoded `window_seconds=40.0`. Exactly 40 seconds after each probe cycle, all samples aged out of the 40s window, causing `aggregate_window` to find zero samples and return `packet_loss: 100.0%`.
2. **False DEGRADED Status**:
   In `classify_status`, single-cycle 100% loss without burst confirmation was categorized as `status="degraded"` with `reason="Active probe loss: 100.0% in rolling window"`.
3. **Emergency Outage Triggering on Non-Failed State**:
   In `decide_route`, `is_curr_failed = (curr_status == "failed" or curr_short_loss >= 100.0)` incorrectly treated `short_loss >= 100.0` as an emergency outage even when `curr_status` was merely "degraded", forcing an immediate failover to Priority 2 and conntrack flush.
4. **Streak Cancellation Trap**:
   When active on an intermediate relay with Priority 1 healthy, Tier 2 planned failback initiated a 120-second streak confirmation. At second 40 into the probe cycle, Priority 1's short window expired and jumped to 100% loss, invalidating `prio1_is_viable` (`short_loss <= 1%`), discarding candidate 1, and resetting `switch_streak_start` to 0. The countdown could mathematically never reach 120 seconds.

## 3. Architecture & Solution Implemented
1. **Dynamic Short Window Sizing**:
   `short_window_sec = max(120.0, probe_interval * 2.5)` (150s for 60s probe interval) ensures samples remain valid across cycles and never expire prematurely.
2. **Recent Sample Tolerance Fallback**:
   In `aggregate_window`, if `valid_samples` is empty but recent samples exist within extended tolerance (`max(window_seconds * 1.5, window_seconds + 30.0)`), the engine falls back to the latest sample rather than falsely reporting 100% loss.
3. **Strict Emergency Failure Separation**:
   In `decide_route`, `is_curr_failed = (curr_status == "failed")`, strictly adhering to `classify_status` authority.
4. **Resilient Priority 1 Viability**:
   `prio1_is_viable` permits up to 5% loss tolerance (`prio1_short_loss <= 5.0`), preventing minor single-packet drops from aborting failback.
5. **Structured Switch Decision Logging & Ring Buffers**:
   - Console/Journal output: `[SWITCH] [timestamp] Rule :<port> (<id>) | Switched Priority #<old> -> Priority #<new> | Reason: <reason> | <explanation>`.
   - Ring buffers: `rule_state["switch_events"]` (bounded to 20 events per rule) and `runtime_state["recent_switches"]` (bounded to 50 global events).
   - Web UI feed (`web/app.js`): Renders detailed switch explanation and metrics directly in the "Logs & Probes" console.

## 4. Invariants & Rules for AI Agents
- Rolling short aggregation windows must always dynamically scale with `target_probe_interval_seconds` (`window >= probe_interval * 2`).
- `aggregate_window` must never report 100% loss if recent valid samples exist within the probe interval.
- Only confirmed `failed` or sustained `critical` states may trigger Tier 1 emergency failover with conntrack flush; `degraded` routes must remain in Tier 2.
- All routing priority switches must generate structured, human-readable switch logs with machine reason and telemetry details.

## 5. Verification & Testing
- `test_aggregate_window_extended_tolerance_fallback`: Validates fallback to recent sample at 45s without 100% loss.
- `test_decide_route_does_not_emergency_failover_on_degraded`: Confirms degraded status does not bypass hold-down guards.
- `test_switch_events_ring_buffer_capped_at_max`: Verifies memory bounds on switch event history.
- `test_short_window_aggregates_sample_at_50_seconds`: Confirms zero phantom loss at 50s into a 60s cycle.
- Run `python .agents/scripts/verify-all.py` to confirm zero regression.

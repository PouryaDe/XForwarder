# Experience 015: Intermediate Relay Subsystem & Primary Anchor Failover

**Date:** 2026-10-27  
**Category:** Networking & Architecture  
**Status:** Active  

---

## 1. Context & Motivation
In intermediate relay and tunnel environments (e.g. Iran VPS $\to$ Intermediate Relay / Tunnel $\to$ Foreign Exit Node), measuring latency via ICMP ping to an intermediate hop only captures the first hop latency (e.g. 10ms), while the unknown second hop to the foreign exit is invisible to the relay. Comparing hop-1 ping directly against end-to-end direct exit routes (Priority 1, e.g. 80ms) created a deceptive bias where the engine would erroneously switch to or remain locked onto intermediate relays.

## 2. Root Cause / Core Dynamics
- **Deceptive Partial-Hop Ping**: Ping to an intermediate relay (like a local tunnel endpoint `10.88.1.2`) measures 5-15ms, but does not include the 60-100ms egress hop from the relay to the foreign destination.
- **Asymmetric Role of Priority 1**: Priority 1 represents the intended, direct egress route. Intermediate hops (Priority 2+) are fallback safety nets, not competitive alternatives for lower latency.

## 3. Architecture & Solution Implemented
1. **Schema & Config**: Added `is_relay` (boolean, default: `False`) to destination schema in `core/config_manager.py` with automatic self-healing migration and smart auto-detection for private RFC1918 IPs in the UI.
2. **Primary Anchor Pattern**:
   - Priority 1 is protected as the anchor destination. When Priority 1 is active, the engine never switches away to an `is_relay` backup merely for lower latency.
   - Switch away from Priority 1 occurs strictly on:
     a) Hard outage (Tier 1 emergency / 100% loss).
     b) Packet loss on Priority 1.
     c) Latency exceeding `max_primary_latency_ms` (150ms).
   - When on an intermediate relay, the engine initiates failback to Priority 1 as soon as Priority 1 recovers (loss $\le 1\%$, latency $\le 150\text{ms}$).
3. **Web Dashboard UI**:
   - Checkbox added to rule modal (`Intermediate Relay Server (سرور واسط)`).
   - Clean `.badge-relay-pill` rendered in both card and list views in the Port Matrix.

## 4. Invariants & Rules for AI Agents
- Never treat `is_relay` destinations as having a lower true end-to-end latency than direct routes.
- Always guarantee failback from an intermediate relay to Priority 1 when Priority 1 is viable.
- `is_relay` must remain optional and backward-compatible (default: `False`).

## 5. Verification & Testing
- Unit test suite: `tests/test_route_quality.py` (`test_is_relay_backup_cannot_steal_traffic_from_healthy_priority_1`, `test_is_relay_fails_over_when_priority_1_latency_exceeds_150ms`, `test_is_relay_failback_to_priority_1_when_priority_1_recovers_even_with_zero_loss_on_relay`, `test_pick_best_now_penalizes_is_relay_over_direct_exit`).
- Verify pipeline: `python .agents/scripts/verify-all.py`.

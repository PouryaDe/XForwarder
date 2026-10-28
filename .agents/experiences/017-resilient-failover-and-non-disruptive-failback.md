# Experience 017: Resilient Failover and Non-Disruptive Failback

**Date:** 2026-10-28  
**Category:** Routing & Reliability  
**Status:** Active  

---

## 1. Context & Motivation
During comprehensive audit of the two-tier multi-path failover engine (`core/route_quality.py` and `core/engine.py`), several subtle behavioral and logical bugs were uncovered in multi-priority fallback and state transitions:
1. `failback_degraded` was categorized under `is_critical=True`, triggering kernel `flush_conntrack(port)` and terminating live client connections whenever the engine restored traffic to healthy Priority 1.
2. Deadlock prevention on complete outage (`is_curr_failed`) failed to trigger when the active route suffered severe critical degradation (e.g. 80-90% loss), leaving traffic trapped on a nearly blackholed route.
3. Priority 1 stickiness ceiling (`prio1_max_lat`) was mistakenly copied into the evaluation of higher backup paths (`P2 vs P3`), preventing selection of healthy tunnel backups that naturally operate at 160-200ms latency.
4. Failback to Priority 1 could occur even when Priority 1 had higher packet loss than the current active backup.

## 2. Root Cause / Core Dynamics
- **Over-Aggressive Conntrack Flush**: Flushing conntrack is only necessary when an endpoint is hard-dead (100% loss) to evict stale NAT states. Triggering it during soft failback unnecessarily severed active downloads, web sessions, and proxies.
- **Copy-Paste Gate in Backup Comparisons**: `prio1_max_lat` is strictly a Primary Anchor parameter (direct egress path ceiling). Applying it to backups (like GRE/IPIP or AmneziaWG tunnels) blocked valid failovers.
- **Deadlock Scope Limitation**: Outage deadlock checks only looked at `is_curr_failed` (100% loss), ignoring severe critical degradation (>=60% loss).

## 3. Architecture & Solution Implemented
1. **Non-Disruptive Failback**:
   - In `core/engine.py`, removed `failback_degraded` from `is_crit`. Conntrack is now preserved during failbacks to Primary or cleaner higher backups, enabling smooth proxy draining without dropped sockets.
2. **Severe Critical Deadlock Escape**:
   - In `core/route_quality.py`, extended deadlock escape to `is_severe_critical = (is_curr_critical and curr_short_loss >= 60.0)`.
   - To prevent oscillation between two degraded routes, required an advantage margin of $\ge 20\%$ lower loss (`curr_short_loss - cand_loss >= 20.0`).
3. **Unshackled Backup Tunnels**:
   - Removed `prio1_max_lat` from higher backup priority checks (`higher_p > 1`), allowing tunnels with natural 160-250ms latency to serve as cleaner backups when Priority 3 is degraded.
4. **Clean-Route Guarantee on Failback**:
   - Enforced `and (prio1_short_loss <= 1.0 or prio1_short_loss < curr_short_loss)` in `hp_is_viable` so Priority 1 will never steal traffic if its packet loss is worse than the active backup.
5. **Per-Rule Latency Ceiling Support**:
   - Propagated `rule.get("max_primary_latency_ms")` to `rule_state`, allowing individual rules with foreign servers in North America/Asia to set custom primary ceilings.

## 4. Invariants & Rules for AI Agents
- Never flush conntrack during soft failback (`failback_degraded`); reserve conntrack flushes for hard dead states (`critical`/`failed`).
- Never gate backup priorities ($P > 1$) by `max_primary_latency_ms`.
- Never failback to Priority 1 if Priority 1 suffers higher packet loss than the active backup.

## 5. Verification & Testing
- `test_severe_critical_loss_triggers_deadlock_prevention_when_candidate_significantly_better`: Confirms deadlock escape on 80% loss with candidate at 35% loss.
- `test_severe_critical_loss_does_not_deadlock_switch_if_advantage_under_20_percent`: Prevents flapping when gap is < 20%.
- `test_multi_priority_failback_allows_backup_with_natural_higher_latency`: Verifies P2 with 175ms latency is chosen when P3 is degraded.
- `test_failback_degraded_does_not_switch_to_dirtier_priority_1`: Confirms no switch if P1 has worse loss than P2.
- `test_evaluate_rule_failback_from_degraded_backup_clears_hold_remaining`: Validates `is_critical=False` on `_hot_toggle_rule_priority`.
- All 274 unit tests passing cleanly.

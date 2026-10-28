#!/usr/bin/env python3
"""
XForwarder - Route Quality and Decision Module
Pure mathematical and state evaluation logic for intelligent, conservative multi-path switching.
Evaluates 10-ping ICMP metrics (latency, jitter, packet loss) across sliding windows.
Zero third-party dependencies (system standard library only).
"""

import math
import time
from typing import Dict, List, Any, Optional, Tuple, Union


def summarize_cycle(parsed_ping: Dict[str, Any], timestamp: Optional[float] = None) -> List[Any]:
    """
    Summarizes a single probe cycle into a compact list format:
    [timestamp, packets_sent, packets_received, avg_latency_ms, jitter_ms]
    """
    ts = timestamp if timestamp is not None else time.time()
    sent = int(parsed_ping.get("packets_sent", 10))
    if "packets_received" in parsed_ping:
        recv = int(parsed_ping["packets_received"])
    else:
        loss = float(parsed_ping.get("packet_loss", 0.0 if parsed_ping.get("healthy") else 100.0))
        recv = max(0, round(sent * (1.0 - (loss / 100.0))))
    lat = parsed_ping.get("latency_ms")
    avg_lat = float(lat) if lat is not None else None
    jit = parsed_ping.get("jitter_ms")
    jitter = float(jit) if jit is not None else 0.0
    return [ts, sent, recv, avg_lat, jitter]


def aggregate_window(samples: List[List[Any]], window_seconds: float, now: Optional[float] = None) -> Dict[str, Any]:
    """
    Aggregates historical cycle samples within window_seconds.
    Calculates composite packet loss, sample-weighted latency, and root-mean-square jitter.
    """
    curr_time = now if now is not None else time.time()
    valid_samples = [s for s in (samples or []) if len(s) >= 5 and (curr_time - float(s[0])) <= window_seconds]

    if not valid_samples:
        # Fallback to most recent valid sample if available and within extended window tolerance (e.g. probe interval jitter)
        all_valid = [s for s in (samples or []) if len(s) >= 5]
        if all_valid and (curr_time - float(all_valid[-1][0])) <= max(window_seconds * 1.5, window_seconds + 30.0):
            valid_samples = [all_valid[-1]]
        else:
            return {
                "samples_count": 0,
                "packets_sent": 0,
                "packets_received": 0,
                "packet_loss": 100.0,
                "avg_latency_ms": None,
                "jitter_ms": 0.0,
                "fill_ratio": 0.0,
                "span_seconds": 0.0
            }

    total_sent = sum(int(s[1]) for s in valid_samples)
    total_recv = sum(int(s[2]) for s in valid_samples)
    loss_pct = round(((total_sent - total_recv) / total_sent) * 100.0, 1) if total_sent > 0 else 100.0

    # Weighted latency across received packets
    lat_samples = [s for s in valid_samples if s[3] is not None and int(s[2]) > 0]
    if lat_samples and total_recv > 0:
        weighted_lat = sum(float(s[3]) * int(s[2]) for s in lat_samples) / sum(int(s[2]) for s in lat_samples)
        avg_lat = round(weighted_lat, 1)
    else:
        avg_lat = None

    # Jitter calculation: RMS of within-cycle mdev + standard deviation across cycles
    if lat_samples:
        # 1. Within-cycle jitter (mean of squares)
        mdev_sq_sum = sum((float(s[4]) ** 2) * int(s[2]) for s in lat_samples)
        mdev_rms = math.sqrt(mdev_sq_sum / sum(int(s[2]) for s in lat_samples))

        # 2. Between-cycle variance
        mean_l = avg_lat or 0.0
        var_between = sum(int(s[2]) * ((float(s[3]) - mean_l) ** 2) for s in lat_samples) / sum(int(s[2]) for s in lat_samples)
        std_between = math.sqrt(max(0.0, var_between))

        combined_jitter = round(math.sqrt((mdev_rms ** 2) + (std_between ** 2)), 1)
    else:
        combined_jitter = 0.0

    earliest = min(float(s[0]) for s in valid_samples)
    span = max(0.0, curr_time - earliest)
    fill_ratio = round(min(1.0, span / max(1.0, window_seconds)), 2)

    return {
        "samples_count": len(valid_samples),
        "packets_sent": total_sent,
        "packets_received": total_recv,
        "packet_loss": loss_pct,
        "avg_latency_ms": avg_lat,
        "jitter_ms": combined_jitter,
        "fill_ratio": fill_ratio,
        "span_seconds": round(span, 1)
    }


def compute_score(
    avg_lat: Optional[float],
    jitter: Optional[float],
    loss_pct: float,
    loss_weight: float = 20.0,
    jitter_weight: float = 2.0,
    priority_bias: float = 0.0
) -> float:
    """
    Computes route quality score:
    Score = Latency + (2 * Jitter) + (20 * Loss%) - PriorityBias
    Lower score is strictly better.
    """
    lat = avg_lat if avg_lat is not None else 1000.0
    jit = jitter if jitter is not None else 0.0
    loss = max(0.0, min(100.0, float(loss_pct)))
    score = lat + (jit * float(jitter_weight)) + (loss * float(loss_weight)) - float(priority_bias)
    return round(max(0.0, score), 1)


def classify_status(
    short_loss: float,
    long_loss: float,
    last_cycle_loss: float,
    burst_confirmed_dead: bool,
    route_invalid: bool,
    max_acceptable_loss: float = 25.0,
    critical_loss: float = 30.0,
    lossy_cycles: Optional[int] = None,
    return_reason: bool = False
) -> Union[str, Tuple[str, str]]:
    """
    Determines route health classification:
    - 'failed': Target unreachable / route invalid / 100% loss confirmed by burst.
    - 'critical': Severe sustained packet loss (>= critical_loss over short window).
    - 'degraded': Noticeable packet loss (>= max_acceptable_loss / 2 or long-term loss >= 5%).
    - 'healthy': Clean operational health.

    When return_reason=True, returns (status: str, reason: str) tuple.
    """
    if route_invalid:
        status, reason = "failed", "Invalid route (leaks to WAN or missing interface)"
    elif burst_confirmed_dead:
        status, reason = "failed", "Target unreachable (100% loss confirmed by fast burst)"
    elif last_cycle_loss >= 100.0 and short_loss >= 100.0:
        status, reason = "failed", "Target host unresponsive (100% packet loss)"
    else:
        sustained = (lossy_cycles is None or lossy_cycles >= 2)
        if short_loss >= critical_loss and sustained:
            cycles_str = f" across {lossy_cycles} cycles" if lossy_cycles else ""
            status, reason = "critical", f"Critical packet loss ({short_loss:.1f}%{cycles_str})"
        elif short_loss >= min(10.0, max_acceptable_loss / 2.0) or (short_loss >= 5.0 and sustained):
            status, reason = "degraded", f"Active probe loss: {short_loss:.1f}% in rolling window"
        elif long_loss >= 5.0 and (short_loss > 1.0 or last_cycle_loss > 1.0):
            status, reason = "degraded", f"Sustained 5m packet loss: {long_loss:.1f}%"
        elif short_loss > 1.0 or last_cycle_loss > 1.0:
            status, reason = "degraded", f"Intermittent packet loss ({max(short_loss, last_cycle_loss):.1f}%)"
        else:
            status, reason = "healthy", "Clean connectivity (0% loss)"

    if return_reason:
        return status, reason
    return status


def pick_best_now(
    dest_stats: Dict[str, Any],
    destinations: List[Dict[str, Any]],
    current_active: int = 1
) -> int:
    """
    Picks the best available route priority for immediate manual override resets.
    Filters out 'failed' and 'critical' routes, selecting lowest composite score.
    If all routes have loss, selects the enabled route with lowest packet loss.
    """
    if not destinations:
        return 1

    dests = sorted(destinations, key=lambda d: d.get("priority", 99))
    eligible: List[Tuple[float, int]] = []

    for d in dests:
        if not d.get("enabled", True):
            continue
        p = d.get("priority", 1)
        st = dest_stats.get(f"prio_{p}", {})
        status = st.get("status", "unknown")
        loss = float(st.get("packet_loss", 100.0))
        score = float(st.get("composite_score", 999.0))

        if status not in ("failed", "critical", "disabled") and loss < 100.0:
            # Healthy routes get bonus priority
            adj_score = score if status == "healthy" else score + 50.0
            is_relay = bool(d.get("is_relay", False) or st.get("is_relay", False))
            if is_relay and p > 1:
                # Penalize intermediate relay hop so it does not falsely beat a healthy direct route
                adj_score += 100.0
            eligible.append((adj_score, p))

    if eligible:
        eligible.sort(key=lambda x: x[0])
        return eligible[0][1]

    # If all routes are degraded or failed, return first enabled priority or 1
    enabled_dests = [d for d in dests if d.get("enabled", True)]
    if enabled_dests:
        return enabled_dests[0].get("priority", 1)
    return dests[0].get("priority", 1)


def decide_route(
    rule_state: Dict[str, Any],
    dest_metrics: Dict[int, Dict[str, Any]],
    current_active: int,
    config: Dict[str, Any],
    now: Optional[float] = None
) -> Tuple[int, str, int]:
    """
    Master two-tier route decision engine:
    Tier 1 (Emergency): Immediate failover on hard failure or critical degradation.
           Prevents deadlocks: if current is failed and all backups critical, picks lowest loss backup.
    Tier 2 (Conservative Quality): Natural priority hierarchy (P1 > P2 > P3).
           Packet-loss driven: never trades latency for higher loss.
           Relay ping neutrality: intermediate relay (mid-server) ping cannot steal from direct routes.
           Anti-reset streak guard: prevents candidate jitter flapping between close backups.
           Instant failback from degraded backups to viable higher priorities.

    Returns:
    (target_priority: int, reason: str, switch_pending_seconds: int)
    reason values: 'hold', 'critical', 'planned', 'failback_degraded', 'warmup', 'pending'
    """
    curr_time = now if now is not None else time.time()
    last_switch = float(rule_state.get("last_switch_time", 0.0))
    time_since_switch = max(0.0, curr_time - last_switch)

    min_hold = float(config.get("min_hold_seconds", 600))
    cooldown = float(config.get("cooldown_seconds", 60))
    hysteresis_pct = float(config.get("hysteresis_percent", 20))
    confirm_sec = float(config.get("switch_confirm_seconds", 120))
    prio1_max_lat = float(config.get("max_primary_latency_ms", 150.0))
    is_flapping = bool(rule_state.get("is_flapping", False))

    if is_flapping:
        min_hold = min(3600.0, min_hold * 2.0)
        cooldown = min(600.0, cooldown * 2.0)

    # 1. Inspect Current Active Route State
    curr_m = dest_metrics.get(current_active, {})
    curr_status = curr_m.get("status", "unknown")
    curr_short_loss = float(curr_m.get("short_loss", 100.0))
    curr_long_score = float(curr_m.get("long_score", 999.0))
    curr_long_loss = float(curr_m.get("long_loss", 100.0))

    is_curr_failed = (curr_status == "failed")
    is_curr_critical = (curr_status == "critical")

    # ── Tier 1: Emergency / Critical Outage Bypass ──
    if is_curr_failed or is_curr_critical:
        best_emerg_cand = None
        best_emerg_score = 999999.0

        for p, m in dest_metrics.items():
            if p == current_active:
                continue
            cand_status = m.get("status", "unknown")
            cand_short_loss = float(m.get("short_loss", 100.0))
            if cand_status not in ("failed", "critical") and cand_short_loss < 100.0:
                score = float(m.get("short_score", 999.0))
                if cand_status == "healthy":
                    score -= 50.0  # Preference for healthy routes
                if score < best_emerg_score:
                    best_emerg_score = score
                    best_emerg_cand = p

        # Deadlock Prevention (LOGIC-01):
        # If current active is 100% dead (failed) and no healthy/degraded alternative exists,
        # find ANY enabled candidate with < 100% loss (even if critical), because a partially
        # working route is infinitely better than blackholing traffic on a dead route!
        if best_emerg_cand is None and is_curr_failed:
            lowest_cand_loss = 100.0
            best_cand_emerg_score = 999999.0
            for p in sorted(dest_metrics.keys()):
                if p == current_active:
                    continue
                m = dest_metrics[p]
                cand_loss = float(m.get("short_loss", 100.0))
                cand_status = m.get("status", "unknown")
                cand_score = float(m.get("short_score", 999.0))
                if cand_status != "failed" and (cand_loss < lowest_cand_loss or (cand_loss == lowest_cand_loss and cand_score < best_cand_emerg_score)):
                    lowest_cand_loss = cand_loss
                    best_cand_emerg_score = cand_score
                    best_emerg_cand = p

        if best_emerg_cand is not None:
            # If current is critical (not completely failed), only switch if candidate is significantly better
            if is_curr_critical and not is_curr_failed:
                cand_short_loss = float(dest_metrics[best_emerg_cand].get("short_loss", 100.0))
                if curr_short_loss - cand_short_loss >= 15.0:
                    return best_emerg_cand, "critical", 0
            else:
                return best_emerg_cand, "critical", 0

    # Scenario 2: Degraded Backup Escape (Immediate Failback to viable higher priority)
    # If active route is a backup (current_active > 1) and suffers packet loss (degraded/loss > 0)
    # while Priority 1 (or any higher priority) is viable or cleaner:
    # Immediately failback bypassing hold-down guards!
    prio1_m = dest_metrics.get(1, {})
    prio1_status = prio1_m.get("status", "unknown")
    prio1_short_loss = float(prio1_m.get("short_loss", prio1_m.get("long_loss", 100.0)))
    prio1_long_loss = float(prio1_m.get("long_loss", 100.0))
    prio1_lat = prio1_m.get("avg_latency_ms")
    if prio1_lat is None:
        prio1_lat = prio1_m.get("latency_ms")
    prio1_lat_val = float(prio1_lat) if prio1_lat is not None else float(prio1_m.get("short_score", 999.0))

    # Priority 1 is viable for failback if it is not failed/critical, has clean/low loss, and latency <= ceiling
    prio1_is_viable = (
        prio1_status not in ("failed", "critical")
        and prio1_short_loss <= 5.0
        and prio1_lat_val <= prio1_max_lat
    )

    backup_has_loss = False
    if current_active > 1:
        backup_has_loss = (
            curr_status in ("failed", "critical", "degraded")
            or curr_short_loss > 0.0
            or curr_long_loss > 0.0
        )
        # Check higher priorities in ascending order (1, 2, ... current_active - 1)
        for higher_p in range(1, current_active):
            hp_m = dest_metrics.get(higher_p)
            if not hp_m:
                continue
            hp_status = hp_m.get("status", "unknown")
            hp_short_loss = float(hp_m.get("short_loss", hp_m.get("long_loss", 100.0)))
            hp_lat = hp_m.get("avg_latency_ms")
            if hp_lat is None:
                hp_lat = hp_m.get("latency_ms")
            hp_lat_val = float(hp_lat) if hp_lat is not None else float(hp_m.get("short_score", 999.0))
            if higher_p == 1:
                # Priority 1 is the Primary Anchor (direct path). Viable if loss <= 5% and latency <= ceiling
                hp_is_viable = (
                    hp_status not in ("failed", "critical")
                    and hp_short_loss <= 5.0
                    and hp_lat_val <= prio1_max_lat
                )
                hp_strictly_better = (
                    hp_status not in ("failed", "critical")
                    and hp_lat_val <= prio1_max_lat
                    and (hp_short_loss <= 1.0 or hp_short_loss < curr_short_loss)
                )
                if backup_has_loss and (hp_is_viable or hp_strictly_better):
                    return 1, "failback_degraded", 0
            else:
                # Higher backup paths (e.g. P2 when active is P3):
                # Must be strictly cleaner than current backup to avoid jumping to another lossy backup!
                hp_strictly_better = (
                    hp_status not in ("failed", "critical")
                    and hp_lat_val <= prio1_max_lat
                    and hp_short_loss < curr_short_loss
                    and hp_short_loss <= 5.0
                )
                if backup_has_loss and hp_strictly_better:
                    return higher_p, "failback_degraded", 0

    # ── Tier 2: Conservative Quality Switching ──
    # Check hold-down guards
    in_post_crit_cooldown = (time_since_switch < cooldown and rule_state.get("last_switch_reason") in ("critical", "failback_degraded"))
    in_min_hold = (time_since_switch < min_hold)

    curr_is_relay = bool(curr_m.get("is_relay", False))
    # When on a backup route, NEVER lock traffic to the backup if Priority 1 is viable
    # or if the current backup route has packet loss / is degraded or is an intermediate relay!
    if current_active > 1 and (prio1_is_viable or backup_has_loss or curr_is_relay or curr_short_loss > 0.0 or curr_long_loss > 0.0):
        in_min_hold = False

    # NEVER lock traffic in min_hold if the currently active route suffers packet loss
    # and a cleaner candidate route is available!
    curr_effective_loss = max(curr_short_loss, curr_long_loss)
    curr_has_loss = (
        curr_status in ("failed", "critical", "degraded")
        or curr_effective_loss >= 5.0
    )
    if curr_has_loss:
        for p, m in dest_metrics.items():
            if p == current_active:
                continue
            cand_loss = float(m.get("long_loss", m.get("short_loss", 100.0)))
            cand_status = m.get("status", "unknown")
            if cand_status not in ("failed", "critical") and cand_loss < (curr_effective_loss - 0.5):
                in_min_hold = False
                break

    if in_post_crit_cooldown or in_min_hold:
        # Hold route to prevent flapping
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return current_active, "hold", 0

    # Minimum window warm-up check: need at least 60% fill ratio unless test mode (min_hold=0 and confirm=0)
    is_test_mode = (min_hold == 0.0 and confirm_sec == 0.0)
    curr_fill = float(curr_m.get("fill_ratio", 0.0))
    if not is_test_mode and curr_fill < 0.60 and not (current_active > 1 and curr_is_relay and prio1_is_viable) and not curr_has_loss:
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return current_active, "warmup", 0

    # Evaluate all candidate alternatives on 5-minute aggregated quality
    best_cand = None
    best_cand_score = curr_long_score

    # Check Priority 1 failback when active route is an intermediate relay
    if current_active > 1 and prio1_is_viable and curr_is_relay:
        best_cand = 1
        best_cand_score = prio1_lat_val
    else:
        for p, m in dest_metrics.items():
            if p == current_active:
                continue
            cand_status = m.get("status", "unknown")
            if cand_status in ("failed", "critical"):
                continue

            cand_fill = float(m.get("fill_ratio", 0.0))
            if not is_test_mode and cand_fill < 0.60 and not curr_has_loss:
                continue

            cand_loss = float(m.get("long_loss", 100.0))
            # Never trade lower latency for higher packet loss!
            if cand_loss > (curr_effective_loss + 0.5):
                continue

            cand_is_relay = bool(m.get("is_relay", False))
            # Intermediate Relay (Mid-Server) Ping Rule:
            # Mid-server ping is only hop-1 (fake low ping). It must NEVER beat a healthy
            # direct route based on latency! Only eligible if current route has packet loss or latency > 150ms.
            if cand_is_relay and current_active == 1:
                curr_lat = curr_m.get("avg_latency_ms")
                if curr_lat is None:
                    curr_lat = curr_m.get("latency_ms")
                curr_lat_val = float(curr_lat) if curr_lat is not None else float(curr_m.get("long_score", 0.0))
                if not curr_has_loss and curr_lat_val <= prio1_max_lat:
                    continue

            # ── Primary Route (Priority 1) Stickiness Rule ──
            # When Priority 1 is currently active, do NOT switch away to backup paths (p > 1)
            # merely because the backup has 10-30ms lower latency (especially if backup is an intermediate relay)!
            # Only switch away from Priority 1 if:
            # 1) Priority 1 packet loss is worse than candidate (curr_effective_loss > cand_loss + 0.5), OR
            # 2) Priority 1 latency exceeds prio1_max_lat (default: 150ms).
            if current_active == 1 and p > 1:
                curr_lat = curr_m.get("avg_latency_ms")
                if curr_lat is None:
                    curr_lat = curr_m.get("latency_ms")
                curr_lat_val = float(curr_lat) if curr_lat is not None else float(curr_m.get("long_score", 0.0))
                loss_is_worse = (curr_effective_loss > cand_loss + 0.5)
                latency_exceeded = (curr_lat_val > prio1_max_lat)

                if not loss_is_worse and not latency_exceeded:
                    # Priority 1 is healthy and <= 150ms with clean loss; keep Priority 1 active!
                    continue

            cand_score = float(m.get("long_score", 999.0))
            if cand_is_relay and p > 1:
                # Neutralize fake low hop-1 ping for mid-servers
                cand_score += 100.0

            # Hysteresis requirement: candidate must beat current score by at least hysteresis_percent% AND >= 15 points (or 10 in test mode)
            min_adv = 10.0 if is_test_mode else 15.0
            required_advantage = max(min_adv, curr_long_score * (hysteresis_pct / 100.0))
            if (curr_long_score - cand_score) >= required_advantage:
                if cand_score < best_cand_score:
                    best_cand_score = cand_score
                    best_cand = p

    # Anti-Reset Guard (LOGIC-02):
    # If tracked_cand is already undergoing streak confirmation and is still a valid candidate
    # that beats current_active, do NOT abort/reset streak just because another backup fluctuated by 1ms!
    tracked_cand = rule_state.get("switch_candidate")
    streak_start = float(rule_state.get("switch_streak_start", 0.0))

    if tracked_cand is not None and tracked_cand in dest_metrics and tracked_cand != current_active:
        tc_m = dest_metrics[tracked_cand]
        tc_status = tc_m.get("status", "unknown")
        tc_loss = float(tc_m.get("long_loss", 100.0))
        tc_is_relay = bool(tc_m.get("is_relay", False))

        # Check relay eligibility: if tracked_cand is a relay and current_active is 1,
        # but Priority 1 is healthy (no loss, lat <= 150), relay cannot be tracked
        tc_relay_eligible = True
        if tc_is_relay and current_active == 1:
            curr_lat = curr_m.get("avg_latency_ms")
            if curr_lat is None:
                curr_lat = curr_m.get("latency_ms")
            curr_lat_val = float(curr_lat) if curr_lat is not None else float(curr_m.get("long_score", 0.0))
            if not curr_has_loss and curr_lat_val <= prio1_max_lat:
                tc_relay_eligible = False

        if tc_relay_eligible and tc_status not in ("failed", "critical") and tc_loss <= (curr_effective_loss + 0.5):
            tc_score = float(tc_m.get("long_score", 999.0))
            if tc_is_relay and tracked_cand > 1:
                tc_score += 100.0
            min_adv = 10.0 if is_test_mode else 15.0
            req_adv = max(min_adv, curr_long_score * (hysteresis_pct / 100.0))
            if (curr_long_score - tc_score) >= req_adv:
                # Tracked candidate is still valid and superior! Keep tracking it to prevent reset trap!
                best_cand = tracked_cand

    if best_cand is None:
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return current_active, "hold", 0

    if confirm_sec == 0.0:
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return best_cand, "planned", 0

    # Sustained advantage streak confirmation
    if tracked_cand != best_cand or streak_start <= 0.0:
        rule_state["switch_candidate"] = best_cand
        rule_state["switch_streak_start"] = curr_time
        remaining = int(confirm_sec)
        return current_active, "pending", remaining

    elapsed_streak = curr_time - streak_start
    if elapsed_streak >= confirm_sec:
        # Candidate has maintained superiority for full confirmation duration!
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return best_cand, "planned", 0

    remaining = max(1, round(confirm_sec - elapsed_streak))
    return current_active, "pending", remaining


#!/usr/bin/env python3
"""
XForwarder - Route Quality and Decision Module
Pure mathematical and state evaluation logic for intelligent, conservative multi-path switching.
Evaluates 10-ping ICMP metrics (latency, jitter, packet loss) across sliding windows.
Zero third-party dependencies (system standard library only).
"""

import math
import time
from typing import Dict, List, Any, Optional, Tuple


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
    lossy_cycles: Optional[int] = None
) -> str:
    """
    Determines route health classification:
    - 'failed': Target unreachable / route invalid / 100% loss confirmed by burst.
    - 'critical': Severe sustained packet loss (>= critical_loss over short window).
    - 'degraded': Noticeable packet loss (>= max_acceptable_loss / 2 or long-term loss >= 5%).
    - 'healthy': Clean operational health.

    lossy_cycles: number of probe cycles inside the short window that lost at least one
    packet. When provided, 'critical' requires loss in >= 2 cycles so that one transient
    blip (a single fully-lost 10-ping cycle = 33% of a 3-cycle window) cannot trigger an
    emergency switch on its own. Confirmed total outages are still caught as 'failed'.
    """
    if route_invalid or burst_confirmed_dead or (last_cycle_loss >= 100.0 and short_loss >= 100.0):
        return "failed"
    sustained = (lossy_cycles is None or lossy_cycles >= 2)
    if short_loss >= critical_loss and sustained:
        return "critical"
    if short_loss >= (max_acceptable_loss / 2.0) or long_loss >= 5.0:
        return "degraded"
    return "healthy"


def pick_best_now(
    dest_stats: Dict[str, Any],
    destinations: List[Dict[str, Any]],
    current_active: int = 1
) -> int:
    """
    Picks the best available route priority for immediate manual override resets.
    Filters out 'failed' and 'critical' routes, selecting lowest composite score.
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
        loss = st.get("packet_loss", 100.0)
        score = st.get("composite_score", 999.0)

        if status not in ("failed", "critical", "disabled") and loss < 100.0:
            # Healthy routes get bonus priority
            adj_score = score if status == "healthy" else score + 50.0
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
    Tier 2 (Conservative Quality): Requires min_hold expiration, significant score advantage
           (hysteresis >= 20% & >= 15 abs), non-worse packet loss, and sustained confirmation (120s).
           Protects Priority 1: never switches away to backup routes merely for 10-20ms lower ping,
           unless Priority 1 has worse packet loss or its latency exceeds max_primary_latency_ms (default: 150ms).

    Returns:
    (target_priority: int, reason: str, switch_pending_seconds: int)
    reason values: 'hold', 'critical', 'planned', 'no_candidate', 'override'
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

    is_curr_failed = (curr_status == "failed" or curr_short_loss >= 100.0)
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

        if best_emerg_cand is not None:
            # If current is critical (not completely failed), only switch if candidate is significantly better
            if is_curr_critical and not is_curr_failed:
                cand_short_loss = float(dest_metrics[best_emerg_cand].get("short_loss", 100.0))
                if curr_short_loss - cand_short_loss >= 15.0:
                    return best_emerg_cand, "critical", 0
            else:
                return best_emerg_cand, "critical", 0

    # Scenario 2: Degraded Backup Escape (Immediate Failback to Priority 1)
    # If active route is a backup (current_active > 1) and suffers packet loss (degraded/loss > 0)
    # while Priority 1 is healthy and under 150ms ceiling:
    # Immediately failback to Priority 1 bypassing hold-down guards!
    prio1_m = dest_metrics.get(1, {})
    prio1_status = prio1_m.get("status", "unknown")
    prio1_loss = float(prio1_m.get("short_loss", prio1_m.get("long_loss", 100.0)))
    prio1_lat = prio1_m.get("avg_latency_ms")
    if prio1_lat is None:
        prio1_lat = prio1_m.get("latency_ms")
    prio1_lat_val = float(prio1_lat) if prio1_lat is not None else float(prio1_m.get("short_score", 999.0))
    prio1_is_healthy = (prio1_status == "healthy" and prio1_loss <= 1.0 and prio1_lat_val <= prio1_max_lat)

    if current_active > 1 and prio1_is_healthy:
        backup_has_loss = (curr_status in ("failed", "critical", "degraded") or curr_short_loss > 0.0 or curr_long_loss > 0.0)
        if backup_has_loss:
            return 1, "failback_degraded", 0

    # ── Tier 2: Conservative Quality Switching ──
    # Check hold-down guards
    in_post_crit_cooldown = (time_since_switch < cooldown and rule_state.get("last_switch_reason") in ("critical", "failback_degraded"))
    in_min_hold = (time_since_switch < min_hold)

    # When on a backup and Priority 1 has fully recovered, do not lock traffic to the backup
    if current_active > 1 and prio1_is_healthy:
        in_min_hold = False

    if in_post_crit_cooldown or in_min_hold:
        # Hold route to prevent flapping
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return current_active, "hold", 0

    # Minimum window warm-up check: need at least 60% fill ratio unless test mode (min_hold=0 and confirm=0)
    is_test_mode = (min_hold == 0.0 and confirm_sec == 0.0)
    curr_fill = float(curr_m.get("fill_ratio", 0.0))
    if not is_test_mode and curr_fill < 0.60:
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return current_active, "warmup", 0

    # Evaluate all candidate alternatives on 5-minute aggregated quality
    best_cand = None
    best_cand_score = curr_long_score

    for p, m in dest_metrics.items():
        if p == current_active:
            continue
        cand_status = m.get("status", "unknown")
        if cand_status in ("failed", "critical"):
            continue

        cand_fill = float(m.get("fill_ratio", 0.0))
        if not is_test_mode and cand_fill < 0.60:
            continue

        cand_loss = float(m.get("long_loss", 100.0))
        # Never trade lower latency for higher packet loss!
        if cand_loss > (curr_long_loss + 0.5):
            continue

        # ── Primary Route (Priority 1) Stickiness Rule ──
        # When Priority 1 is currently active, do NOT switch away to backup paths (p > 1)
        # merely because the backup has 10-30ms lower latency!
        # Only switch away from Priority 1 if:
        # 1) Priority 1 packet loss is worse than candidate (curr_long_loss > cand_loss + 0.5), OR
        # 2) Priority 1 latency exceeds prio1_max_lat (default: 150ms).
        if current_active == 1 and p > 1:
            curr_lat = curr_m.get("avg_latency_ms")
            if curr_lat is None:
                curr_lat = curr_m.get("latency_ms")
            curr_lat_val = float(curr_lat) if curr_lat is not None else float(curr_m.get("long_score", 0.0))
            loss_is_worse = (curr_long_loss > cand_loss + 0.5)
            latency_exceeded = (curr_lat_val > prio1_max_lat)

            if not loss_is_worse and not latency_exceeded:
                # Priority 1 is healthy and <= 150ms with clean loss; keep Priority 1 active!
                continue

        cand_score = float(m.get("long_score", 999.0))
        # Hysteresis requirement: candidate must beat current score by at least hysteresis_percent% AND >= 15 points (or 10 in test mode)
        min_adv = 10.0 if is_test_mode else 15.0
        required_advantage = max(min_adv, curr_long_score * (hysteresis_pct / 100.0))
        if (curr_long_score - cand_score) >= required_advantage:
            if cand_score < best_cand_score:
                best_cand_score = cand_score
                best_cand = p

    if best_cand is None:
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return current_active, "hold", 0

    if confirm_sec == 0.0:
        rule_state["switch_candidate"] = None
        rule_state["switch_streak_start"] = 0.0
        return best_cand, "planned", 0

    # Sustained advantage streak confirmation
    tracked_cand = rule_state.get("switch_candidate")
    streak_start = float(rule_state.get("switch_streak_start", 0.0))

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

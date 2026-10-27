#!/usr/bin/env python3
"""
Unit tests for XForwarder Route Quality & Intelligent Decision Engine.
Verifies:
1. summarize_cycle extraction and fallback calculation
2. aggregate_window weighted latency, packet loss %, and RMS jitter
3. compute_score formula: Latency + 2*Jitter + 20*Loss% + bias
4. classify_status classification matrix (healthy, degraded, critical, failed)
5. Tier 1 Emergency Failover (<1s immediate switch on hard failure / critical degradation)
6. Tier 2 Conservative Quality Switching:
   - 10m minimum hold guard
   - 60% window warm-up guard
   - Packet loss protection (never trade lower latency for higher packet loss)
   - 20% & 15-point hysteresis margin
   - 120s sustained streak confirmation
   - Flap damping doubling
7. pick_best_now selection

Standard library unittest only. Zero pip dependencies.
"""

import os
import sys
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.route_quality import (
    summarize_cycle,
    aggregate_window,
    compute_score,
    classify_status,
    pick_best_now,
    decide_route
)


class TestRouteQualityEngine(unittest.TestCase):

    def test_summarize_cycle(self):
        """Verifies parsing and fallback calculation of cycle samples."""
        now = 1000.0
        # Case A: full parsed ICMP ping
        p1 = {
            "packets_sent": 10,
            "packets_received": 9,
            "latency_ms": 42.5,
            "jitter_ms": 3.8
        }
        s1 = summarize_cycle(p1, now)
        self.assertEqual(s1, [1000.0, 10, 9, 42.5, 3.8])

        # Case B: fallback derivation from packet_loss (when packets_received omitted)
        p2 = {
            "packets_sent": 10,
            "packet_loss": 30.0,
            "latency_ms": 50.0,
            "healthy": True
        }
        s2 = summarize_cycle(p2, now)
        self.assertEqual(s2[0], 1000.0)
        self.assertEqual(s2[1], 10)
        self.assertEqual(s2[2], 7)  # 10 * (1 - 0.3) = 7
        self.assertEqual(s2[3], 50.0)
        self.assertEqual(s2[4], 0.0)

    def test_aggregate_window_math(self):
        """Verifies sliding-window weighted latency, composite loss, and jitter math."""
        now = 1000.0
        samples = [
            # [ts, sent, recv, avg_lat, jitter]
            [now - 120, 10, 10, 40.0, 2.0],
            [now - 60,  10,  8, 50.0, 4.0],
            [now - 10,  10, 10, 42.0, 1.5],
            [now - 500, 10, 10, 99.0, 9.0],  # Out of 300s window!
        ]
        agg = aggregate_window(samples, window_seconds=300.0, now=now)
        self.assertEqual(agg["samples_count"], 3)
        self.assertEqual(agg["packets_sent"], 30)
        self.assertEqual(agg["packets_received"], 28)
        # Loss: (30 - 28) / 30 = 6.7%
        self.assertAlmostEqual(agg["packet_loss"], 6.7, places=1)
        # Weighted latency across 28 packets: (10*40 + 8*50 + 10*42) / 28 = 1220 / 28 = 43.57ms
        self.assertAlmostEqual(agg["avg_latency_ms"], 43.6, places=1)
        self.assertGreater(agg["jitter_ms"], 0.0)
        # Span: 120 / 300 = 0.4
        self.assertAlmostEqual(agg["fill_ratio"], 0.4, places=2)

    def test_composite_score_formula(self):
        """Verifies Score = Latency + 2*Jitter + 20*Loss% + priority_bias."""
        # 40ms, 3.5ms jitter, 5% loss, default weights (loss_weight=20, jitter_weight=2)
        # Score = 40.0 + (3.5 * 2) + (5.0 * 20) = 40.0 + 7.0 + 100.0 = 147.0
        score = compute_score(
            avg_lat=40.0,
            jitter=3.5,
            loss_pct=5.0,
            loss_weight=20.0,
            jitter_weight=2.0,
            priority_bias=0.0
        )
        self.assertEqual(score, 147.0)

        # Null latency fallback: 1000 base + 20*100 = 3000.0
        score_null = compute_score(None, 0.0, 100.0)
        self.assertEqual(score_null, 3000.0)

    def test_classify_status_matrix(self):
        """Verifies classification into healthy, degraded, critical, and failed states."""
        # Healthy: 0% loss
        s_healthy = classify_status(short_loss=0, long_loss=0, last_cycle_loss=0, burst_confirmed_dead=False, route_invalid=False)
        self.assertEqual(s_healthy, "healthy")

        # Healthy when recovered: historical long_loss was 6.0%, but short_loss is 0% and last_cycle is 0%
        s_recovered = classify_status(short_loss=0, long_loss=6.0, last_cycle_loss=0, burst_confirmed_dead=False, route_invalid=False)
        self.assertEqual(s_recovered, "healthy")

        # Degraded: loss between 25% and 30%
        s_degraded = classify_status(short_loss=26.0, long_loss=26.0, last_cycle_loss=20.0, burst_confirmed_dead=False, route_invalid=False, max_acceptable_loss=25.0, critical_loss=30.0)
        self.assertEqual(s_degraded, "degraded")

        # Critical: loss >= 30%
        s_critical = classify_status(short_loss=32.0, long_loss=20.0, last_cycle_loss=30.0, burst_confirmed_dead=False, route_invalid=False, critical_loss=30.0)
        self.assertEqual(s_critical, "critical")

        # Failed: burst confirmed dead
        s_burst_dead = classify_status(short_loss=100.0, long_loss=50.0, last_cycle_loss=100.0, burst_confirmed_dead=True, route_invalid=False)
        self.assertEqual(s_burst_dead, "failed")

        # Failed: route invalid or 100% loss sustained
        s_invalid = classify_status(short_loss=100.0, long_loss=100.0, last_cycle_loss=100.0, burst_confirmed_dead=False, route_invalid=True)
        self.assertEqual(s_invalid, "failed")

        # Descriptive reasons with return_reason=True
        stat_deg, reason_deg = classify_status(short_loss=15.0, long_loss=10.0, last_cycle_loss=10.0, burst_confirmed_dead=False, route_invalid=False, max_acceptable_loss=25.0, return_reason=True)
        self.assertEqual(stat_deg, "degraded")
        self.assertIn("Active probe loss: 15.0%", reason_deg)

        stat_ok, reason_ok = classify_status(short_loss=0.0, long_loss=0.0, last_cycle_loss=0.0, burst_confirmed_dead=False, route_invalid=False, return_reason=True)
        self.assertEqual(stat_ok, "healthy")
        self.assertIn("Clean connectivity", reason_ok)

    def test_tier1_emergency_failover_bypasses_hold_and_streak(self):
        """Verifies that hard failure or critical outage triggers immediate switch without delay."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 30.0,  # Only 30s ago (within 600s hold!)
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "failed",
                "short_loss": 100.0,
                "long_loss": 100.0,
                "short_score": 2999.0,
                "long_score": 2999.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 45.0,
                "long_score": 45.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "cooldown_seconds": 60,
            "switch_confirm_seconds": 120
        }

        target_prio, reason, pending = decide_route(
            rule_state=rule_state,
            dest_metrics=dest_metrics,
            current_active=1,
            config=config,
            now=now
        )
        self.assertEqual(target_prio, 2)
        self.assertEqual(reason, "critical")
        self.assertEqual(pending, 0)

    def test_tier2_planned_switch_blocked_during_min_hold(self):
        """Verifies conservative planned switch is blocked while route is in 10-minute hold."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 300.0,  # 5 minutes into 10m hold
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 120.0,
                "long_score": 120.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 40.0,  # Way better (66% better)
                "long_score": 40.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "cooldown_seconds": 60,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20
        }

        target_prio, reason, pending = decide_route(
            rule_state=rule_state,
            dest_metrics=dest_metrics,
            current_active=1,
            config=config,
            now=now
        )
        # Must stay on Priority 1 until min_hold expires
        self.assertEqual(target_prio, 1)
        self.assertEqual(reason, "hold")
        self.assertEqual(pending, 0)

    def test_tier2_never_trades_latency_for_packet_loss(self):
        """Verifies candidate with lower latency but higher packet loss is firmly rejected."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,  # min_hold expired
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 80.0,
                "long_score": 80.0,
                "fill_ratio": 1.0
            },
            2: {
                # Candidate has 20ms latency but 3% packet loss (long_loss > curr_loss)
                "status": "healthy",
                "short_loss": 3.0,
                "long_loss": 3.0,
                "short_score": 30.0,
                "long_score": 30.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20
        }

        target_prio, reason, pending = decide_route(
            rule_state=rule_state,
            dest_metrics=dest_metrics,
            current_active=1,
            config=config,
            now=now
        )
        # Rejected because candidate loss (3%) > current loss (0%)
        self.assertEqual(target_prio, 1)
        self.assertEqual(reason, "hold")

    def test_tier2_sustained_streak_confirmation(self):
        """Verifies that planned switch requires 120s sustained advantage streak before switching."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,  # min_hold expired
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                # Current route has 160ms latency (exceeds 150ms ceiling, allowing switch to backup)
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 160.0,
                "long_score": 160.0,
                "avg_latency_ms": 160.0,
                "fill_ratio": 1.0
            },
            2: {
                # Candidate has 50ms latency (50% advantage, beats 20% margin)
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 50.0,
                "long_score": 50.0,
                "avg_latency_ms": 50.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }

        # Step 1: First cycle detecting superiority -> Starts streak timer (pending 120s)
        target, reason, rem = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)  # Has not switched yet
        self.assertEqual(reason, "pending")
        self.assertEqual(rem, 120)
        self.assertEqual(rule_state["switch_candidate"], 2)
        self.assertEqual(rule_state["switch_streak_start"], now)

        # Step 2: 60s into streak -> Still pending (60s remaining)
        target2, reason2, rem2 = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now + 60.0)
        self.assertEqual(target2, 1)
        self.assertEqual(reason2, "pending")
        self.assertEqual(rem2, 60)

        # Step 3: 120s elapsed -> Streak confirmed! Switches to candidate 2 with reason "planned"
        target3, reason3, rem3 = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now + 120.0)
        self.assertEqual(target3, 2)
        self.assertEqual(reason3, "planned")
        self.assertEqual(rem3, 0)
        self.assertIsNone(rule_state["switch_candidate"])

    def test_pick_best_now(self):
        """Verifies pick_best_now selects the best healthy route based on composite score."""
        dest_stats = {
            "prio_1": {"status": "healthy", "packet_loss": 0, "composite_score": 85.0},
            "prio_2": {"status": "healthy", "packet_loss": 0, "composite_score": 35.0},
            "prio_3": {"status": "critical", "packet_loss": 50, "composite_score": 20.0}
        }
        dests = [
            {"priority": 1, "target": "1.1.1.1"},
            {"priority": 2, "target": "2.2.2.2"},
            {"priority": 3, "target": "3.3.3.3"}
        ]
        # P3 is critical so excluded. P2 has score 35 vs P1 score 85 -> P2 wins!
        best = pick_best_now(dest_stats, dests, current_active=1)
        self.assertEqual(best, 2)

    def test_aggregate_window_edge_cases_empty_or_malformed(self):
        """Verifies resilience to empty samples, None, truncated items, and 100% loss."""
        # 1. None or empty list
        agg_none = aggregate_window(None, 300.0)
        self.assertEqual(agg_none["samples_count"], 0)
        self.assertEqual(agg_none["packet_loss"], 100.0)
        self.assertIsNone(agg_none["avg_latency_ms"])
        self.assertEqual(agg_none["jitter_ms"], 0.0)

        # 2. Malformed samples (length < 5) ignored safely
        malformed = [[1000.0, 10], [1000.0, "bad", "format"]]
        agg_malformed = aggregate_window(malformed, 300.0, now=1000.0)
        self.assertEqual(agg_malformed["samples_count"], 0)

        # 3. 100% loss sample (recv = 0)
        loss_samples = [
            [1000.0, 10, 0, None, 0.0]
        ]
        agg_loss = aggregate_window(loss_samples, 300.0, now=1000.0)
        self.assertEqual(agg_loss["samples_count"], 1)
        self.assertEqual(agg_loss["packet_loss"], 100.0)
        self.assertIsNone(agg_loss["avg_latency_ms"])

    def test_tier1_all_destinations_failed_stays_on_current(self):
        """Verifies that when all destinations are failed or critical, system stays on current_active without crashing or flapping."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 30.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "failed",
                "short_loss": 100.0,
                "long_loss": 100.0,
                "short_score": 3000.0,
                "long_score": 3000.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "failed",
                "short_loss": 100.0,
                "long_loss": 100.0,
                "short_score": 3000.0,
                "long_score": 3000.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        # Should remain on current active because no alternative is operational
        self.assertEqual(target, 1)
        self.assertEqual(reason, "hold")
        self.assertEqual(pending, 0)

    def test_tier2_flap_damping_doubles_hold_time(self):
        """Verifies that is_flapping doubles min_hold from 600s to 1200s."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,  # 700s elapsed (exceeds normal 600s hold!)
            "is_flapping": True,              # Flapping detected -> hold doubles to 1200s
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {"status": "healthy", "short_loss": 0.0, "long_loss": 0.0, "long_score": 100.0, "fill_ratio": 1.0},
            2: {"status": "healthy", "short_loss": 0.0, "long_loss": 0.0, "long_score": 40.0, "fill_ratio": 1.0}
        }
        config = {"min_hold_seconds": 600, "switch_confirm_seconds": 120, "hysteresis_percent": 20}
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        # 700s < 1200s damped hold -> must be held
        self.assertEqual(target, 1)
        self.assertEqual(reason, "hold")

    def test_tier2_window_warmup_guard_blocks_premature_switch(self):
        """Verifies that fill_ratio < 0.60 blocks planned switches until sample history warms up."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,  # min_hold satisfied
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {"status": "healthy", "short_loss": 0.0, "long_loss": 0.0, "long_score": 100.0, "fill_ratio": 0.30},  # < 60%
            2: {"status": "healthy", "short_loss": 0.0, "long_loss": 0.0, "long_score": 40.0, "fill_ratio": 1.0}
        }
        config = {"min_hold_seconds": 600, "switch_confirm_seconds": 120, "hysteresis_percent": 20}
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "warmup")

    def test_pick_best_now_fallback_when_all_failed_or_empty(self):
        """Verifies pick_best_now returns safe default when destinations list is empty or all routes failed."""
        # 1. Empty destinations
        self.assertEqual(pick_best_now({}, []), 1)

        # 2. All routes critical or failed
        dest_stats = {
            "prio_1": {"status": "failed", "packet_loss": 100, "composite_score": 999.0},
            "prio_2": {"status": "critical", "packet_loss": 80, "composite_score": 850.0}
        }
        dests = [{"priority": 1, "target": "1.1.1.1"}, {"priority": 2, "target": "2.2.2.2"}]
        # When all fail, falls back to priority 1
        self.assertEqual(pick_best_now(dest_stats, dests, current_active=1), 1)

    def test_tier2_priority_1_protected_when_under_150ms_and_clean_loss(self):
        """Verifies Priority 1 does NOT switch to backup merely because backup has 20-30ms lower ping."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 75.0,
                "long_score": 75.0,
                "avg_latency_ms": 75.0,
                "fill_ratio": 1.0
            },
            2: {
                # Backup has 45ms ping (30ms lower, >20% better score)
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 45.0,
                "long_score": 45.0,
                "avg_latency_ms": 45.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        # Because Priority 1 is healthy, loss is 0%, and latency (75ms) <= 150ms,
        # it MUST remain on Priority 1 and NOT start a switch to Priority 2!
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "hold")
        self.assertEqual(pending, 0)
        self.assertIsNone(rule_state.get("switch_candidate"))

    def test_tier2_priority_1_switches_when_latency_exceeds_150ms(self):
        """Verifies Priority 1 initiates switch to backup when latency exceeds 150ms ceiling."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                # Priority 1 elevated ping > 150ms
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 175.0,
                "long_score": 175.0,
                "avg_latency_ms": 175.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 50.0,
                "long_score": 50.0,
                "avg_latency_ms": 50.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)  # pending streak confirmation
        self.assertEqual(reason, "pending")
        self.assertEqual(pending, 120)
        self.assertEqual(rule_state.get("switch_candidate"), 2)

    def test_tier2_priority_1_switches_when_packet_loss_worse(self):
        """Verifies Priority 1 initiates switch to backup when it has higher packet loss."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                # Ping is good (60ms <= 150ms), but packet loss is 6%
                "status": "degraded",
                "short_loss": 6.0,
                "long_loss": 6.0,
                "short_score": 180.0,
                "long_score": 180.0,
                "avg_latency_ms": 60.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 70.0,
                "long_score": 70.0,
                "avg_latency_ms": 70.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)  # pending streak confirmation
        self.assertEqual(reason, "pending")
        self.assertEqual(pending, 120)
        self.assertEqual(rule_state.get("switch_candidate"), 2)

    def test_tier1_degraded_backup_escape_immediate_failback_to_prio1(self):
        """
        Exact scenario from production:
        Current active is Priority 2 (Backup NFTables: 10.81.7.2:9121).
        Priority 2 has degraded quality (93.7ms, 10% packet loss).
        Priority 1 is healthy (100.3ms <= 150ms ceiling, 0% packet loss).
        Even if within min_hold (switch happened 15 seconds ago),
        the engine must IMMEDIATELY fail back to Priority 1 without holding.
        """
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 15.0,  # Only 15s ago, deep inside min_hold (600s)!
            "switch_candidate": None,
            "switch_streak_start": 0.0,
            "last_switch_reason": "planned"
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 100.3,
                "long_score": 100.3,
                "avg_latency_ms": 100.3,
                "fill_ratio": 1.0
            },
            2: {
                "status": "degraded",
                "short_loss": 0.0,
                "long_loss": 10.0,
                "short_score": 293.7,
                "long_score": 293.7,
                "avg_latency_ms": 93.7,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=2, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "failback_degraded")
        self.assertEqual(pending, 0)

    def test_failback_from_lossy_backup_even_if_flapping_and_prio1_was_degraded(self):
        """
        Exact user bug report scenario:
        - Port :9224 is on Priority 2 (NFTables 10.81.8.2:9224)
        - Priority 2 has 4% packet loss, 123.3ms latency, and is labeled 'degraded'
        - Priority 1 (HAProxy IPv6) has 0% short loss, 110.6ms latency (<= 150ms ceiling),
          but status was 'degraded' due to older samples in the 5-minute window!
        - Flap Guard is active (is_flapping=True) with 1200s hold (switched only 20s ago).
        The engine MUST immediately return (1, 'failback_degraded', 0) without holding for 1200s!
        """
        now = 2000.0
        rule_state = {
            "last_switch_time": now - 20.0,  # Switched 20 seconds ago
            "switch_candidate": None,
            "switch_streak_start": 0.0,
            "is_flapping": True,             # Flap guard active (1200s hold!)
            "last_switch_reason": "critical"
        }
        dest_metrics = {
            1: {
                "status": "degraded",       # Still labeled degraded from older window!
                "short_loss": 0.0,          # But 0% current loss
                "long_loss": 5.5,
                "short_score": 110.6,
                "long_score": 220.6,
                "avg_latency_ms": 110.6,
                "fill_ratio": 1.0
            },
            2: {
                "status": "degraded",
                "short_loss": 4.0,          # 4% packet loss on active backup
                "long_loss": 4.0,
                "short_score": 203.3,
                "long_score": 203.3,
                "avg_latency_ms": 123.3,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=2, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "failback_degraded")
        self.assertEqual(pending, 0)

    def test_is_relay_backup_cannot_steal_traffic_from_healthy_priority_1(self):
        """
        Verifies that an intermediate relay (is_relay=True) with deceptively low hop ping (e.g. 12ms)
        CANNOT steal traffic from Priority 1 when Priority 1 is healthy (80ms <= 150ms, 0% loss).
        """
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 80.0,
                "long_score": 80.0,
                "avg_latency_ms": 80.0,
                "fill_ratio": 1.0,
                "is_relay": False
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 12.0,
                "long_score": 12.0,
                "avg_latency_ms": 12.0,
                "fill_ratio": 1.0,
                "is_relay": True  # Intermediate Relay Server!
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "hold")
        self.assertEqual(pending, 0)

    def test_is_relay_fails_over_when_priority_1_latency_exceeds_150ms(self):
        """Verifies that traffic fails over to intermediate relay when Priority 1 exceeds 150ms."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 175.0,
                "long_score": 175.0,
                "avg_latency_ms": 175.0,  # > 150ms ceiling!
                "fill_ratio": 1.0,
                "is_relay": False
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 15.0,
                "long_score": 15.0,
                "avg_latency_ms": 15.0,
                "fill_ratio": 1.0,
                "is_relay": True
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "pending")
        self.assertEqual(rule_state.get("switch_candidate"), 2)

    def test_is_relay_failback_to_priority_1_when_priority_1_recovers_even_with_zero_loss_on_relay(self):
        """
        Verifies that when currently on an intermediate relay (is_relay=True) with 0% loss and 15ms ping,
        as soon as Priority 1 recovers (<= 150ms, 0% loss), the engine initiates failback to Priority 1
        instead of staying trapped on the intermediate relay!
        """
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 700.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                # Recovered direct exit server
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 75.0,
                "long_score": 75.0,
                "avg_latency_ms": 75.0,
                "fill_ratio": 1.0,
                "is_relay": False
            },
            2: {
                # Active intermediate relay with lower ping (15ms vs 75ms)
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 15.0,
                "long_score": 15.0,
                "avg_latency_ms": 15.0,
                "fill_ratio": 1.0,
                "is_relay": True
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=2, config=config, now=now)
        self.assertEqual(target, 2)  # pending streak confirmation towards 1
        self.assertEqual(reason, "pending")
        self.assertEqual(rule_state.get("switch_candidate"), 1)

    def test_pick_best_now_penalizes_is_relay_over_direct_exit(self):
        """Verifies pick_best_now selects direct Priority 1 (80ms) over intermediate relay (15ms)."""
        dest_stats = {
            "prio_1": {
                "status": "healthy",
                "packet_loss": 0.0,
                "composite_score": 80.0
            },
            "prio_2": {
                "status": "healthy",
                "packet_loss": 0.0,
                "composite_score": 15.0
            }
        }
        destinations = [
            {"priority": 1, "enabled": True, "is_relay": False},
            {"priority": 2, "enabled": True, "is_relay": True}
        ]
        best = pick_best_now(dest_stats, destinations, current_active=1)
        self.assertEqual(best, 1)

    def test_pick_best_now_accidental_is_relay_on_priority_1_does_not_penalize_priority_1(self):
        """Verifies that accidental is_relay=True on Priority 1 does not add a penalty to Priority 1."""
        dest_stats = {
            "prio_1": {
                "status": "healthy",
                "packet_loss": 0.0,
                "composite_score": 50.0
            },
            "prio_2": {
                "status": "healthy",
                "packet_loss": 0.0,
                "composite_score": 60.0
            }
        }
        destinations = [
            {"priority": 1, "enabled": True, "is_relay": True},  # Accidental is_relay on P1
            {"priority": 2, "enabled": True, "is_relay": False}
        ]
        best = pick_best_now(dest_stats, destinations, current_active=1)
        self.assertEqual(best, 1)

    def test_relay_failback_to_priority_1_not_blocked_by_relay_warmup(self):
        """
        Verifies that when on an intermediate relay (curr_is_relay=True) with low fill_ratio (e.g. 0.20),
        failback to a viable Priority 1 is NOT blocked by the warmup check.
        """
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 30.0,  # Switch happened 30s ago
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 80.0,
                "long_score": 80.0,
                "avg_latency_ms": 80.0,
                "fill_ratio": 1.0,
                "is_relay": False
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 20.0,
                "long_score": 20.0,
                "avg_latency_ms": 20.0,
                "fill_ratio": 0.20,  # Relay is in warmup (< 0.60)
                "is_relay": True
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20,
            "max_primary_latency_ms": 150
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=2, config=config, now=now)
        # Must initiate pending switch to Priority 1 rather than returning 'warmup'
        self.assertEqual(target, 2)
        self.assertEqual(reason, "pending")
        self.assertEqual(rule_state.get("switch_candidate"), 1)

    def test_aggregate_window_extended_tolerance_fallback(self):
        """Verifies aggregate_window falls back to recent sample instead of falsely returning 100% loss on slight window gap."""
        now = 1045.0
        # Sample taken 45s ago (e.g. at 1000.0s), 10 sent, 10 received, latency 55.0ms, jitter 1.5ms
        samples = [
            [1000.0, 10, 10, 55.0, 1.5]
        ]
        # With window_seconds=40.0, sample at 1000.0 is 45s old, but within 40.0 * 1.5 = 60s tolerance
        agg = aggregate_window(samples, window_seconds=40.0, now=now)
        self.assertEqual(agg["samples_count"], 1)
        self.assertEqual(agg["packet_loss"], 0.0)
        self.assertEqual(agg["avg_latency_ms"], 55.0)

    def test_decide_route_does_not_emergency_failover_on_degraded(self):
        """Verifies that a route with status='degraded' does not trigger Tier 1 emergency failover (stays on active during streak)."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 30.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "degraded",
                "short_loss": 15.0,
                "long_loss": 15.0,
                "short_score": 150.0,
                "long_score": 150.0,
                "avg_latency_ms": 70.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "healthy",
                "short_loss": 0.0,
                "long_loss": 0.0,
                "short_score": 50.0,
                "long_score": 50.0,
                "avg_latency_ms": 50.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        # Does NOT trigger Tier 1 emergency switch (target remains 1, not immediately 2, reason is pending not critical)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "pending")
        self.assertEqual(pending, 120)
        self.assertEqual(rule_state.get("switch_candidate"), 2)

    def test_priority1_with_10_percent_loss_bypasses_min_hold_and_switches(self):
        """
        Verifies that Priority 1 with 10% packet loss (degraded) bypasses the 10-minute hold
        and selects Priority 2 (with 2% loss) via Tier 2 planned confirmation.
        """
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 419.0,  # 181s left of 600s min_hold!
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "degraded",
                "short_loss": 10.0,
                "long_loss": 10.0,
                "avg_latency_ms": 93.3,
                "long_score": 293.3,
                "fill_ratio": 1.0
            },
            2: {
                "status": "degraded",
                "short_loss": 2.0,
                "long_loss": 2.0,
                "avg_latency_ms": 86.7,
                "long_score": 126.7,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20
        }
        # First check: min_hold is waived because P1 has 10% loss and P2 has 2% loss
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "pending")
        self.assertEqual(pending, 120)
        self.assertEqual(rule_state.get("switch_candidate"), 2)

        # After confirmation duration (120s), planned switch to Priority 2 completes!
        target_done, reason_done, pending_done = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now + 120.0)
        self.assertEqual(target_done, 2)
        self.assertEqual(reason_done, "planned")
        self.assertEqual(pending_done, 0)

    def test_hold_not_bypassed_when_candidate_has_equal_or_worse_loss(self):
        """Verifies that hold is preserved if candidate does not offer lower packet loss."""
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 30.0,  # inside 600s min_hold
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "degraded",
                "short_loss": 10.0,
                "long_loss": 10.0,
                "long_score": 250.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "degraded",
                "short_loss": 10.0,
                "long_loss": 10.0,
                "long_score": 220.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        # Should remain on Priority 1 in 'hold' because Candidate 2 does not have lower loss
        self.assertEqual(target, 1)
        self.assertEqual(reason, "hold")

    def test_candidate_evaluated_when_curr_long_loss_zero_but_short_loss_elevated(self):
        """
        Verifies that when Priority 1 has short-term loss spike (short_loss=10%, long_loss=0%),
        Candidate 2 (with long_loss=2%) is correctly evaluated and NOT rejected by long_loss comparisons.
        """
        now = 1000.0
        rule_state = {
            "last_switch_time": now - 30.0,
            "switch_candidate": None,
            "switch_streak_start": 0.0
        }
        dest_metrics = {
            1: {
                "status": "degraded",
                "short_loss": 10.0,
                "long_loss": 0.0,
                "long_score": 290.0,
                "fill_ratio": 1.0
            },
            2: {
                "status": "healthy",
                "short_loss": 2.0,
                "long_loss": 2.0,
                "long_score": 120.0,
                "fill_ratio": 1.0
            }
        }
        config = {
            "min_hold_seconds": 600,
            "switch_confirm_seconds": 120,
            "hysteresis_percent": 20
        }
        target, reason, pending = decide_route(rule_state, dest_metrics, current_active=1, config=config, now=now)
        self.assertEqual(target, 1)
        self.assertEqual(reason, "pending")
        self.assertEqual(pending, 120)
        self.assertEqual(rule_state.get("switch_candidate"), 2)


if __name__ == "__main__":
    unittest.main()



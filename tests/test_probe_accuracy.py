#!/usr/bin/env python3
"""
Regression tests for probe measurement accuracy and false-switch prevention.
Verifies:
1. Per-reply parsing ignores tail-padding probes and DUPs (no false tail loss)
2. BusyBox 0-based sequence numbering is handled
3. Hostname targets are not forced to IPv4 (AAAA-only names stay probeable)
4. Engine ICMP probe sends padding probes and scores only the measured window
5. A single transient lossy cycle cannot trip 'critical' (Tier-1 emergency switch)

Standard library unittest only.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.metrics import parse_ping_replies, _ip_family_flag
from core.route_quality import classify_status
from core import prober


def _iputils_output(received_seqs, sent, rtt=50.0):
    lines = ["PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data."]
    for seq in received_seqs:
        lines.append(f"64 bytes from 10.0.0.2: icmp_seq={seq} ttl=64 time={rtt:.1f} ms")
    recv = len(received_seqs)
    loss = round((sent - recv) / sent * 100)
    lines.append("")
    lines.append("--- 10.0.0.2 ping statistics ---")
    lines.append(f"{sent} packets transmitted, {recv} received, {loss}% packet loss, time 2000ms")
    if recv:
        lines.append(f"rtt min/avg/max/mdev = {rtt:.3f}/{rtt:.3f}/{rtt:.3f}/0.000 ms")
    return "\n".join(lines)


class TestPerReplyParsing(unittest.TestCase):
    def test_padding_replies_are_ignored(self):
        # 12 sent (10 measured + 2 padding); padding seq 12 lost by ping's exit timer
        out = _iputils_output(list(range(1, 12)), sent=12)
        res = parse_ping_replies(out, 10)
        self.assertEqual(res["packets_sent"], 10)
        self.assertEqual(res["packets_received"], 10)
        self.assertEqual(res["packet_loss"], 0.0)
        self.assertTrue(res["healthy"])

    def test_real_loss_inside_window_is_counted(self):
        out = _iputils_output([1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12], sent=12)
        res = parse_ping_replies(out, 10)
        self.assertEqual(res["packets_received"], 9)
        self.assertEqual(res["packet_loss"], 10.0)

    def test_duplicates_not_double_counted(self):
        out = _iputils_output([1, 1, 2, 2], sent=12) + "\n64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=9.0 ms (DUP!)"
        res = parse_ping_replies(out, 10)
        self.assertEqual(res["packets_received"], 2)
        self.assertEqual(res["packet_loss"], 80.0)

    def test_unreachable_lines_not_counted(self):
        out = "From 10.0.0.1 icmp_seq=1 Destination Host Unreachable\n" + \
              "64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=20.0 ms"
        res = parse_ping_replies(out, 2)
        self.assertEqual(res["packets_received"], 1)

    def test_busybox_zero_based(self):
        out = "\n".join(f"64 bytes from 10.0.0.2: seq={s} ttl=64 time=10.0 ms" for s in range(0, 10))
        res = parse_ping_replies(out, 10)
        self.assertEqual(res["packets_received"], 10)
        self.assertEqual(res["packet_loss"], 0.0)

    def test_no_reply_lines_returns_none(self):
        self.assertIsNone(parse_ping_replies("", 10))
        self.assertIsNone(parse_ping_replies("ping: unknown host", 10))

    def test_jitter_is_population_stddev(self):
        out = "\n".join([
            "64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=10.0 ms",
            "64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=30.0 ms",
        ])
        res = parse_ping_replies(out, 2)
        self.assertEqual(res["latency_ms"], 20.0)
        self.assertEqual(res["jitter_ms"], 10.0)

    def test_out_of_order_packets(self):
        # Packets arrive out of order: 3, 1, 2, 5, 4
        out = "\n".join([
            "64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=15.0 ms",
            "64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=10.0 ms",
            "64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=12.0 ms",
            "64 bytes from 10.0.0.2: icmp_seq=5 ttl=64 time=20.0 ms",
            "64 bytes from 10.0.0.2: icmp_seq=4 ttl=64 time=18.0 ms",
        ])
        res = parse_ping_replies(out, 5)
        self.assertEqual(res["packets_received"], 5)
        self.assertEqual(res["packet_loss"], 0.0)
        self.assertEqual(res["min_lat"], 10.0)
        self.assertEqual(res["max_lat"], 20.0)

    def test_invalid_or_zero_expected_count(self):
        self.assertIsNone(parse_ping_replies("64 bytes: icmp_seq=1 time=1ms", 0))
        self.assertIsNone(parse_ping_replies("64 bytes: icmp_seq=1 time=1ms", -1))


class TestFamilySelection(unittest.TestCase):
    def test_family_flags(self):
        self.assertEqual(_ip_family_flag("1.2.3.4"), "-4")
        self.assertEqual(_ip_family_flag("2001:db8::1"), "-6")
        self.assertIsNone(_ip_family_flag("relay.example.com"))
        self.assertIsNone(_ip_family_flag(""))
        self.assertIsNone(_ip_family_flag("999.999.999.999"))


class TestEngineIcmpProbe(unittest.TestCase):
    def _run(self, target, stdout):
        proc = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch.object(prober.sys, "platform", "linux"), \
             patch("core.prober.subprocess.run", return_value=proc) as mock_run:
            res = prober.probe_destination_icmp(target, iface="gre1", count=10, interval_ms=200)
        return res, mock_run.call_args[0][0]

    def test_padding_sent_and_window_scored(self):
        res, cmd = self._run("10.0.0.2", _iputils_output(list(range(1, 12)), sent=12))
        self.assertEqual(cmd[cmd.index("-c") + 1], str(10 + prober.ICMP_TAIL_PADDING))
        self.assertIn("-4", cmd)
        self.assertIn("gre1", cmd)
        self.assertEqual(res["packets_sent"], 10)
        self.assertEqual(res["packet_loss"], 0.0)

    def test_hostname_not_forced_ipv4(self):
        _, cmd = self._run("relay.example.com", _iputils_output(list(range(1, 13)), sent=12))
        self.assertNotIn("-4", cmd)
        self.assertNotIn("-6", cmd)

    def test_total_loss_reports_measured_count(self):
        res, _ = self._run("10.0.0.2", _iputils_output([], sent=12))
        self.assertEqual(res["packets_sent"], 10)
        self.assertEqual(res["packets_received"], 0)
        self.assertEqual(res["packet_loss"], 100.0)

    def test_summary_only_fallback_when_replies_absent(self):
        # When output lacks per-reply lines but has valid summary (e.g. 12 transmitted, 10 received)
        summary_only = "12 packets transmitted, 10 received, 16.7% packet loss\nrtt min/avg/max = 20.0/22.0/25.0 ms"
        res, _ = self._run("10.0.0.2", summary_only)
        # Should normalize packets_sent to safe_count (10) and calculate loss accurately
        self.assertEqual(res["packets_sent"], 10)
        self.assertEqual(res["packets_received"], 10)
        self.assertEqual(res["packet_loss"], 0.0)


class TestSustainedCriticalClassification(unittest.TestCase):
    def test_single_blip_cycle_is_not_critical(self):
        # One fully-lost cycle among 3 = 33.3% short loss, but only 1 lossy cycle
        status = classify_status(short_loss=33.3, long_loss=3.0, last_cycle_loss=0.0,
                                 burst_confirmed_dead=False, route_invalid=False,
                                 lossy_cycles=1)
        self.assertEqual(status, "degraded")

    def test_sustained_loss_is_critical(self):
        status = classify_status(short_loss=40.0, long_loss=20.0, last_cycle_loss=40.0,
                                 burst_confirmed_dead=False, route_invalid=False,
                                 lossy_cycles=2)
        self.assertEqual(status, "critical")

    def test_backward_compatible_none_lossy_cycles(self):
        # When lossy_cycles is omitted (legacy callers), critical_loss threshold applies directly
        status = classify_status(short_loss=35.0, long_loss=20.0, last_cycle_loss=35.0,
                                 burst_confirmed_dead=False, route_invalid=False,
                                 lossy_cycles=None)
        self.assertEqual(status, "critical")

    def test_confirmed_outage_still_fails_immediately(self):
        status = classify_status(short_loss=33.3, long_loss=3.0, last_cycle_loss=100.0,
                                 burst_confirmed_dead=True, route_invalid=False,
                                 lossy_cycles=1)
        self.assertEqual(status, "failed")


if __name__ == "__main__":
    unittest.main()


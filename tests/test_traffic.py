#!/usr/bin/env python3
"""
Unit tests for XForwarder Traffic Accounting Subsystem (core/traffic.py).
Standard library unittest only.
"""

import os
import sys
import time
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.traffic import (
    parse_proc_net_dev,
    parse_haproxy_stats_csv,
    parse_nftables_counters_json,
    init_traffic_db,
    TrafficCollector,
    get_traffic_summary,
    get_traffic_timeseries,
    reset_traffic_counter,
    prune_old_traffic_records
)


SAMPLE_PROC_NET_DEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 1250000    5000    0    0    0     0          0         0  1250000    5000    0    0    0     0       0          0
  eth0: 9540000000 6800000    0    0    0     0          0         0 14200000000 7200000    0    0    0     0       0          0
  gre1: 2147483648 1500000    0    0    0     0          0         0  4294967296 2800000    0    0    0     0       0          0
 ipip1: 104857600  120000    0    0    0     0          0         0   209715200  210000    0    0    0     0       0          0
"""

SAMPLE_HAPROXY_STATS_CSV = """# pxname,svname,qcur,qmax,scur,smax,slim,spkt,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,comp_in,comp_out,comp_byp,comp_rsp,lastsess,last_chk,last_agt,qtime,ctime,rtime,ttime,agent_status,agent_code,agent_duration,
xfwd_standby,FRONTEND,,,0,0,100000,0,0,0,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,0,0,0,,,,0,0,0,0,0,0,,0,0,0,,,0,0,0,0,,,,,,,,
fwd_443,FRONTEND,,,2,45,100000,1200,1073741824,3221225472,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,5,0,25,,,,0,0,0,0,0,0,,5,25,450,,,0,0,0,0,,,,,,,,
fwd_443,srv_443,0,0,2,45,,1200,1073741824,3221225472,,0,,0,0,0,0,no check,1,1,0,,,,,,1,2,1,,450,,2,5,,25,,,,0,0,0,0,0,0,0,,,,0,0,,,,,,,,
fwd_8080,FRONTEND,,,0,12,100000,300,52428800,104857600,0,0,0,,,,,OPEN,,,,,,,,,1,3,0,,,,0,1,0,10,,,,0,0,0,0,0,0,,1,10,120,,,0,0,0,0,,,,,,,,
fwd_8080,srv_8080,0,0,0,12,,300,52428800,104857600,,0,,0,0,0,0,no check,1,1,0,,,,,,1,3,1,,120,,2,1,,10,,,,0,0,0,0,0,0,0,,,,0,0,,,,,,,,
"""

SAMPLE_NFTABLES_COUNTERS_JSON = """{
  "nftables": [
    {"metainfo": {"version": "0.9.8", "release_name": "E发布的", "json_schema_version": 1}},
    {"counter": {"family": "ip", "table": "xfwd_orchestrator", "name": "cnt_in_443", "handle": 1, "packets": 5000, "bytes": 524288000}},
    {"counter": {"family": "ip", "table": "xfwd_orchestrator", "name": "cnt_out_443", "handle": 2, "packets": 9000, "bytes": 1572864000}},
    {"counter": {"family": "ip", "table": "xfwd_orchestrator", "name": "cnt_in_9090", "handle": 3, "packets": 800, "bytes": 83886080}},
    {"counter": {"family": "ip", "table": "xfwd_orchestrator", "name": "cnt_out_9090", "handle": 4, "packets": 1200, "bytes": 125829120}}
  ]
}"""


class TestTrafficSubsystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_traffic.db")
        init_traffic_db(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_proc_net_dev(self):
        """Validates parsing of /proc/net/dev lines into interface rx/tx bytes."""
        stats = parse_proc_net_dev(SAMPLE_PROC_NET_DEV)
        self.assertIn("eth0", stats)
        self.assertIn("gre1", stats)
        self.assertIn("ipip1", stats)

        self.assertEqual(stats["gre1"]["rx_bytes"], 2147483648)
        self.assertEqual(stats["gre1"]["tx_bytes"], 4294967296)
        self.assertEqual(stats["ipip1"]["rx_bytes"], 104857600)
        self.assertEqual(stats["ipip1"]["tx_bytes"], 209715200)

    def test_parse_haproxy_stats_csv(self):
        """Validates parsing of HAProxy CSV stats output extracting bin and bout per port."""
        stats = parse_haproxy_stats_csv(SAMPLE_HAPROXY_STATS_CSV)
        self.assertIn(443, stats)
        self.assertIn(8080, stats)

        # Port 443: bin=1073741824 (1GB rx), bout=3221225472 (3GB tx)
        self.assertEqual(stats[443]["rx_bytes"], 1073741824)
        self.assertEqual(stats[443]["tx_bytes"], 3221225472)

        # Port 8080: bin=52428800 (50MB rx), bout=104857600 (100MB tx)
        self.assertEqual(stats[8080]["rx_bytes"], 52428800)
        self.assertEqual(stats[8080]["tx_bytes"], 104857600)

    def test_parse_nftables_counters_json(self):
        """Validates parsing of nft -j list counters extracting cnt_in and cnt_out."""
        stats = parse_nftables_counters_json(SAMPLE_NFTABLES_COUNTERS_JSON)
        self.assertIn(443, stats)
        self.assertIn(9090, stats)

        self.assertEqual(stats[443]["rx_bytes"], 524288000)
        self.assertEqual(stats[443]["tx_bytes"], 1572864000)
        self.assertEqual(stats[9090]["rx_bytes"], 83886080)
        self.assertEqual(stats[9090]["tx_bytes"], 125829120)

    def test_traffic_collector_delta_and_persistence(self):
        """Tests that TrafficCollector computes deltas and handles initial baseline without inflating."""
        collector = TrafficCollector(db_path=self.db_path)

        # Cycle 1: Initial baseline run (deltas should be 0 so no artificial jump)
        with patch("core.traffic.read_haproxy_port_stats", return_value={443: {"rx_bytes": 1000, "tx_bytes": 2000}}), \
             patch("core.traffic.read_nftables_port_stats", return_value={}), \
             patch("core.traffic.read_proc_net_dev", return_value={"gre1": {"rx_bytes": 5000, "tx_bytes": 6000}}):
            res1 = collector.collect_cycle(ports=[443], tunnel_ifaces=["gre1"])
            self.assertEqual(res1["entities_updated"], 0)

        # Cycle 2: Traffic arrives (+500 rx, +1000 tx on port 443; +200 rx, +300 tx on gre1)
        with patch("core.traffic.read_haproxy_port_stats", return_value={443: {"rx_bytes": 1500, "tx_bytes": 3000}}), \
             patch("core.traffic.read_nftables_port_stats", return_value={}), \
             patch("core.traffic.read_proc_net_dev", return_value={"gre1": {"rx_bytes": 5200, "tx_bytes": 6300}}):
            res2 = collector.collect_cycle(ports=[443], tunnel_ifaces=["gre1"])
            self.assertEqual(res2["entities_updated"], 2)

        # Verify SQLite contents
        summary = get_traffic_summary(period="24h", db_path=self.db_path)
        self.assertEqual(summary["total_rx"], 500 + 200)
        self.assertEqual(summary["total_tx"], 1000 + 300)
        self.assertEqual(summary["total_bytes"], 2000)

        self.assertIn("port:443", summary["entities"])
        self.assertEqual(summary["entities"]["port:443"]["rx_bytes"], 500)
        self.assertEqual(summary["entities"]["port:443"]["tx_bytes"], 1000)

        self.assertIn("tunnel:gre1", summary["entities"])
        self.assertEqual(summary["entities"]["tunnel:gre1"]["rx_bytes"], 200)
        self.assertEqual(summary["entities"]["tunnel:gre1"]["tx_bytes"], 300)

    def test_delta_handling_on_reboot_and_reload(self):
        """Verifies that when HAProxy or kernel counters reset to lower value, delta engine handles it smoothly."""
        collector = TrafficCollector(db_path=self.db_path)

        # Baseline
        with patch("core.traffic.read_haproxy_port_stats", return_value={443: {"rx_bytes": 10000, "tx_bytes": 20000}}), \
             patch("core.traffic.read_nftables_port_stats", return_value={}), \
             patch("core.traffic.read_proc_net_dev", return_value={}):
            collector.collect_cycle(ports=[443])

        # Service reloaded: raw counter reset to 300 rx and 500 tx
        with patch("core.traffic.read_haproxy_port_stats", return_value={443: {"rx_bytes": 300, "tx_bytes": 500}}), \
             patch("core.traffic.read_nftables_port_stats", return_value={}), \
             patch("core.traffic.read_proc_net_dev", return_value={}):
            res = collector.collect_cycle(ports=[443])
            # Delta should be 300 and 500, not negative!
            self.assertEqual(res["deltas"]["port:443"]["rx"], 300)
            self.assertEqual(res["deltas"]["port:443"]["tx"], 500)

        summary = get_traffic_summary(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(summary["total_rx"], 300)
        self.assertEqual(summary["total_tx"], 500)

    def test_reset_traffic_counter_cycle_and_wipe(self):
        """Tests reset_traffic_counter: billing cycle resets to 0 while history remains intact, and wipe_history removes rows."""
        collector = TrafficCollector(db_path=self.db_path)

        # Insert some traffic
        with patch("core.traffic.read_haproxy_port_stats", return_value={443: {"rx_bytes": 0, "tx_bytes": 0}}), \
             patch("core.traffic.read_nftables_port_stats", return_value={}), \
             patch("core.traffic.read_proc_net_dev", return_value={}):
            collector.collect_cycle(ports=[443])

        with patch("core.traffic.read_haproxy_port_stats", return_value={443: {"rx_bytes": 1000, "tx_bytes": 2000}}), \
             patch("core.traffic.read_nftables_port_stats", return_value={}), \
             patch("core.traffic.read_proc_net_dev", return_value={}):
            collector.collect_cycle(ports=[443])

        # Prior to reset
        s_before = get_traffic_summary(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(s_before["cycle_bytes"], 3000)
        self.assertEqual(s_before["total_bytes"], 3000)

        # Execute Cycle Reset (wipe_history=False)
        reset_res = reset_traffic_counter(entity_type="port", entity_id="443", wipe_history=False, db_path=self.db_path)
        self.assertTrue(reset_res["success"])

        # After cycle reset: cycle_bytes is reset, total_bytes is preserved!
        s_after = get_traffic_summary(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(s_after["cycle_bytes"], 0)
        self.assertEqual(s_after["total_bytes"], 3000)

        # Now wipe completely
        wipe_res = reset_traffic_counter(entity_type="port", entity_id="443", wipe_history=True, db_path=self.db_path)
        self.assertTrue(wipe_res["success"])

        s_wiped = get_traffic_summary(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(s_wiped["total_bytes"], 0)

    def test_get_traffic_timeseries(self):
        """Verifies that get_traffic_timeseries returns chronological buckets."""
        now = time.time()
        hour_start = int(now // 3600) * 3600

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO traffic_hourly (entity_type, entity_id, period_start, rx_bytes, tx_bytes, total_bytes)
            VALUES ('port', '443', ?, 100, 200, 300);
        """, (hour_start,))
        conn.commit()
        conn.close()

        ts = get_traffic_timeseries(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(len(ts), 1)
        self.assertEqual(ts[0]["rx_bytes"], 100)
        self.assertEqual(ts[0]["tx_bytes"], 200)
        self.assertEqual(ts[0]["total_bytes"], 300)

    def test_prune_old_traffic_records(self):
        """Verifies that prune_old_traffic_records removes rows older than retention days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        old_time = int(time.time() - (100 * 86400))  # 100 days old
        cursor.execute("""
            INSERT INTO traffic_hourly (entity_type, entity_id, period_start, rx_bytes, tx_bytes, total_bytes)
            VALUES ('port', '443', ?, 50, 50, 100);
        """, (old_time,))
        conn.commit()
        conn.close()

        deleted = prune_old_traffic_records(retention_days=90, db_path=self.db_path)
        self.assertEqual(deleted, 1)


    def test_api_traffic_endpoints(self):
        """Tests that web_server exposes /api/traffic/summary, timeseries, and reset endpoints with auth."""
        from core.web_server import XForwarderWebHandler
        handler = MagicMock()
        handler.headers = {"Host": "127.0.0.1:8080", "Origin": "http://127.0.0.1:8080"}
        handler.is_authenticated.return_value = True
        handler.check_origin.return_value = True

        # Test GET summary
        handler.path = "/api/traffic/summary?period=24h"
        handler.resolve_path.return_value = (True, "/api/traffic/summary", "")
        with patch("core.web_server.get_traffic_summary", return_value={"total_bytes": 5000}):
            XForwarderWebHandler.do_GET(handler)
            handler.send_json.assert_called_with({"ok": True, "data": {"total_bytes": 5000}})

        # Test GET timeseries
        handler.path = "/api/traffic/timeseries?period=7d"
        handler.resolve_path.return_value = (True, "/api/traffic/timeseries", "")
        with patch("core.web_server.get_traffic_timeseries", return_value=[{"label": "2026-10-23", "total_bytes": 1000}]):
            XForwarderWebHandler.do_GET(handler)
            handler.send_json.assert_called_with({"ok": True, "data": [{"label": "2026-10-23", "total_bytes": 1000}]})


    def test_reset_all_entities_individual_offsets(self):
        """Verifies that global reset populates individual offsets so single entity queries remain accurate."""
        now = time.time()
        hour_start = int(now // 3600) * 3600

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO traffic_hourly VALUES ('port', '443', ?, 1000, 2000, 3000);", (hour_start,))
        cursor.execute("INSERT INTO traffic_hourly VALUES ('port', '80', ?, 500, 500, 1000);", (hour_start,))
        cursor.execute("INSERT INTO traffic_hourly VALUES ('tunnel', 'gre1', ?, 5000, 5000, 10000);", (hour_start,))
        conn.commit()
        conn.close()

        # Reset all
        res = reset_traffic_counter(entity_type="all", entity_id="all", wipe_history=False, db_path=self.db_path)
        self.assertTrue(res["success"])

        # Query single port 443 -> cycle must be 0, total 3000
        s_443 = get_traffic_summary(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(s_443["cycle_bytes"], 0)
        self.assertEqual(s_443["total_bytes"], 3000)

        # Add new traffic of 500 bytes to port 443
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE traffic_hourly SET rx_bytes = rx_bytes + 200, tx_bytes = tx_bytes + 300, total_bytes = total_bytes + 500
            WHERE entity_type = 'port' AND entity_id = '443';
        """)
        conn.commit()
        conn.close()

        s_443_new = get_traffic_summary(period="24h", entity_type="port", entity_id="443", db_path=self.db_path)
        self.assertEqual(s_443_new["cycle_bytes"], 500)
        self.assertEqual(s_443_new["total_bytes"], 3500)

    def test_wipe_history_resets_offset_to_zero(self):
        """Verifies that wipe_history=True zeroes baseline offsets so new traffic counts immediately from 0."""
        now = time.time()
        hour_start = int(now // 3600) * 3600

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO traffic_hourly VALUES ('port', '8443', ?, 50000, 50000, 100000);", (hour_start,))
        conn.commit()
        conn.close()

        # Wipe history
        res = reset_traffic_counter(entity_type="port", entity_id="8443", wipe_history=True, db_path=self.db_path)
        self.assertTrue(res["success"])

        # New traffic arrives after wipe
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO traffic_hourly VALUES ('port', '8443', ?, 300, 400, 700);", (hour_start,))
        conn.commit()
        conn.close()

        s = get_traffic_summary(period="24h", entity_type="port", entity_id="8443", db_path=self.db_path)
        self.assertEqual(s["cycle_bytes"], 700)
        self.assertEqual(s["total_bytes"], 700)

    def test_proc_net_dev_corrupt_and_empty_edge_cases(self):
        """Verifies parse_proc_net_dev handles corrupt data, missing columns, and empty strings gracefully."""
        self.assertEqual(parse_proc_net_dev(""), {})
        self.assertEqual(parse_proc_net_dev("Just some random text\nno colons anywhere"), {})
        # Missing column values
        corrupt = "eth0: 100 200\n"
        self.assertEqual(parse_proc_net_dev(corrupt), {})
        # Non-numeric values
        non_num = "eth0: foo bar baz 0 0 0 0 0 0 qux 0\n"
        self.assertEqual(parse_proc_net_dev(non_num), {})

    def test_haproxy_csv_corrupt_and_partial_edge_cases(self):
        """Verifies parse_haproxy_stats_csv handles empty or corrupted CSV without crashing."""
        self.assertEqual(parse_haproxy_stats_csv(""), {})
        self.assertEqual(parse_haproxy_stats_csv("# pxname,svname\n"), {})
        # Malformed lines with non-int ports or non-numeric bin/bout
        bad_csv = "# pxname,svname,bin,bout\nfwd_abc,FRONTEND,100,200\nfwd_443,FRONTEND,not_a_number,200\n"
        res = parse_haproxy_stats_csv(bad_csv)
        self.assertNotIn("abc", res)

    def test_api_traffic_reset_input_validation(self):
        """Verifies that /api/traffic/reset strictly validates entity_type, port numbers, and tunnel names."""
        import io
        from core.web_server import XForwarderWebHandler
        handler = MagicMock()
        handler.headers = {"Host": "127.0.0.1:8080", "Origin": "http://127.0.0.1:8080"}
        handler.is_authenticated.return_value = True
        handler.check_origin.return_value = True
        handler.resolve_path.return_value = (True, "/api/traffic/reset", "")

        def set_body(payload):
            raw = json.dumps(payload).encode("utf-8")
            handler.headers["Content-Length"] = str(len(raw))
            handler.rfile = io.BytesIO(raw)

        # 1. Invalid entity_type
        set_body({"entity_type": "malicious"})
        XForwarderWebHandler.do_POST(handler)
        handler.send_json.assert_called_with({"ok": False, "error": "Invalid entity_type 'malicious'. Must be 'all', 'port', or 'tunnel'."}, 400)

        # 2. Invalid port number (out of bounds)
        set_body({"entity_type": "port", "entity_id": "70000"})
        XForwarderWebHandler.do_POST(handler)
        handler.send_json.assert_called_with({"ok": False, "error": "Invalid port number '70000'. Must be 1-65535 or 'all'."}, 400)

        # 3. Invalid tunnel interface name (injection characters)
        set_body({"entity_type": "tunnel", "entity_id": "gre1; rm -rf /"})
        XForwarderWebHandler.do_POST(handler)
        handler.send_json.assert_called_with({"ok": False, "error": "Invalid tunnel interface name 'gre1; rm -rf /'."}, 400)


if __name__ == "__main__":
    unittest.main()

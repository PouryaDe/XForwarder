#!/usr/bin/env python3
"""
Unit tests for Kernel & Network Optimizer (`core/kernel_tuner.py`),
`/api/system/optimize` endpoint, UI wiring, and CLI support.
Native Python Standard Library unittest only.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.kernel_tuner import (
    compute_tuning_profile,
    detect_system_capacity,
    get_kernel_tuning_status,
    apply_kernel_tuning,
)


def _seed_fake_proc(root: str, mem_kb: int = 2048000, rp_all: str = "2", rp_def: str = "2", ct_max: str = "262144"):
    meminfo = os.path.join(root, "meminfo")
    with open(meminfo, "w", encoding="utf-8") as f:
        f.write(f"MemTotal:       {mem_kb} kB\nMemFree:         512000 kB\n")

    proc_sys = os.path.join(root, "proc_sys")
    entries = {
        "net/ipv4/ip_forward": "1\n",
        "net/ipv6/conf/all/forwarding": "1\n",
        "net/ipv6/conf/default/forwarding": "1\n",
        "net/ipv4/tcp_congestion_control": "cubic\n",
        "net/ipv4/tcp_available_congestion_control": "reno cubic bbr\n",
        "net/core/default_qdisc": "pfifo_fast\n",
        "net/ipv4/conf/all/rp_filter": f"{rp_all}\n",
        "net/ipv4/conf/default/rp_filter": f"{rp_def}\n",
        "net/ipv4/conf/all/accept_source_route": "0\n",
        "net/ipv6/conf/all/accept_source_route": "0\n",
        "net/ipv4/tcp_mtu_probing": "0\n",
        "net/netfilter/nf_conntrack_max": f"{ct_max}\n",
        "net/core/rmem_max": "212992\n",
        "net/core/somaxconn": "4096\n",
        "net/core/netdev_budget": "300\n",
        "net/core/netdev_budget_usecs": "2000\n",
        "net/core/dev_weight": "64\n",
        "fs/file-max": "1048576\n",
    }
    for rel, val in entries.items():
        p = os.path.join(proc_sys, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(val)
    os.makedirs(os.path.join(proc_sys, "net", "ipv4", "conf", "eth0"), exist_ok=True)
    os.makedirs(os.path.join(proc_sys, "net", "ipv4", "conf", "esp1"), exist_ok=True)
    return meminfo, proc_sys


class TestKernelTuner(unittest.TestCase):

    def test_ram_tier_scaling_protects_low_ram_vps(self):
        p_low = compute_tuning_profile(512, 1)
        p_mid = compute_tuning_profile(2048, 2)
        p_high = compute_tuning_profile(8192, 8)
        self.assertEqual(p_low["tier"], "tier1_low")
        self.assertEqual(p_low["conntrack_max"], 131072)
        self.assertEqual(p_low["min_free_kbytes"], 32768)
        self.assertEqual(p_low["rmem_max"], 16777216)
        self.assertEqual(p_mid["tier"], "tier2_medium")
        self.assertEqual(p_mid["conntrack_max"], 262144)
        self.assertEqual(p_high["tier"], "tier4_high")
        self.assertEqual(p_high["conntrack_max"], 1048576)
        self.assertEqual(p_high["min_free_kbytes"], 131072)

    def test_detect_conflicts_and_clean_reset_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            meminfo, proc_sys = _seed_fake_proc(tmp, mem_kb=2048000, rp_all="2", rp_def="2")
            etc_dir = os.path.join(tmp, "etc")
            sysctl_conf = os.path.join(etc_dir, "sysctl.conf")
            sysctl_d = os.path.join(etc_dir, "sysctl.d")
            xfw_sysctl = os.path.join(sysctl_d, "99-xforwarder.conf")
            dsr_sysctl = os.path.join(sysctl_d, "99-xforwarder-dsr.conf")
            other_dropin = os.path.join(sysctl_d, "98-custom-ipsec.conf")
            distro_dropin = os.path.join(sysctl_d, "10-network-security.conf")
            modules_file = os.path.join(etc_dir, "modules")
            modules_load = os.path.join(etc_dir, "modules-load.d")
            haproxy_ov = os.path.join(tmp, "haproxy-override.conf")
            bak_dir = os.path.join(tmp, "backups")
            hashsize_file = os.path.join(tmp, "hashsize")

            os.makedirs(sysctl_d, exist_ok=True)
            with open(hashsize_file, "w", encoding="utf-8") as f:
                f.write("65536\n")
            # Legacy PouryaDe/ipsec/sysctl.conf with rp_filter=2 + duplicate nf_conntrack in /etc/modules
            with open(sysctl_conf, "w", encoding="utf-8") as f:
                f.write(
                    "net.ipv4.conf.all.rp_filter = 2\n"
                    "net.ipv4.conf.default.rp_filter = 2\n"
                    "net.netfilter.nf_conntrack_buckets = 262144\n"
                )
            with open(other_dropin, "w", encoding="utf-8") as f:
                f.write("net.ipv4.tcp_congestion_control = cubic\n")
            with open(distro_dropin, "w", encoding="utf-8") as f:
                f.write("net.ipv4.conf.all.rp_filter = 1\n")
            with open(dsr_sysctl, "w", encoding="utf-8") as f:
                f.write("net.ipv4.conf.all.rp_filter=0\n")
            with open(modules_file, "w", encoding="utf-8") as f:
                f.write("# /etc/modules\nnf_conntrack\nnf_conntrack\n")

            st_before = get_kernel_tuning_status(
                meminfo_path=meminfo,
                proc_sys_root=proc_sys,
                sysctl_conf_path=sysctl_conf,
                sysctl_d_dir=sysctl_d,
                xfw_sysctl_path=xfw_sysctl,
                dsr_sysctl_path=dsr_sysctl,
                modules_path=modules_file,
            )
            self.assertTrue(st_before["previous_tuning_detected"])
            codes = {c["code"] for c in st_before["conflicts"]}
            self.assertIn("rp_filter_nonzero", codes)
            self.assertIn("legacy_sysctl_conf", codes)
            self.assertIn("conflicting_sysctl_dropin", codes)
            self.assertIn("duplicate_etc_modules", codes)

            # Fake runner updates simulated /proc/sys when sysctl runs
            def fake_run(cmd, **kwargs):
                res = MagicMock()
                res.returncode = 0
                res.stdout = "default via 198.51.100.1 dev eth0\n"
                res.stderr = ""
                if os.path.basename(cmd[0]).startswith("sysctl") and "--system" in cmd:
                    for key, val in (
                        ("net/ipv4/conf/all/rp_filter", "0\n"),
                        ("net/ipv4/conf/default/rp_filter", "0\n"),
                        ("net/ipv4/tcp_congestion_control", "bbr\n"),
                        ("net/core/default_qdisc", "fq\n"),
                    ):
                        with open(os.path.join(proc_sys, key.replace("/", os.sep)), "w", encoding="utf-8") as pf:
                            pf.write(val)
                return res

            with patch("core.kernel_tuner._find_system_bin", side_effect=lambda name, *_a: f"/usr/sbin/{name}"):
                out = apply_kernel_tuning(
                    reset_existing=True,
                    meminfo_path=meminfo,
                    proc_sys_root=proc_sys,
                    sysctl_conf_path=sysctl_conf,
                    sysctl_d_dir=sysctl_d,
                    xfw_sysctl_path=xfw_sysctl,
                    dsr_sysctl_path=dsr_sysctl,
                    modules_path=modules_file,
                    modules_load_dir=modules_load,
                    haproxy_override_path=haproxy_ov,
                    backup_dir=bak_dir,
                    hashsize_param_path=hashsize_file,
                    run_fn=fake_run,
                )

            self.assertTrue(out["ok"], out)
            self.assertTrue(out["reset"]["performed"])
            self.assertTrue(out["reset"]["backup_dir"] and os.path.isdir(out["reset"]["backup_dir"]))
            # Conflicting third-party dropin removed, distro + DSR preserved
            self.assertFalse(os.path.exists(other_dropin))
            self.assertTrue(os.path.exists(distro_dropin))
            self.assertTrue(os.path.exists(dsr_sysctl))
            self.assertTrue(os.path.exists(xfw_sysctl))

            with open(xfw_sysctl, "r", encoding="utf-8") as f:
                xfw_text = f.read()
            self.assertIn("net.ipv4.conf.all.rp_filter = 0", xfw_text)
            self.assertIn("net.ipv4.conf.esp1.rp_filter = 0", xfw_text)
            self.assertIn("net.ipv4.tcp_congestion_control = bbr", xfw_text)
            self.assertIn("net.core.default_qdisc = fq", xfw_text)
            self.assertNotIn("nf_conntrack_buckets", xfw_text)

            # /etc/modules deduplicated to single nf_conntrack line
            with open(modules_file, "r", encoding="utf-8") as f:
                mod_lines = [ln.strip() for ln in f.read().splitlines() if ln.strip() and not ln.strip().startswith("#")]
            self.assertEqual(mod_lines.count("nf_conntrack"), 1)

            # /etc/sysctl.conf cleared cleanly after backup
            with open(sysctl_conf, "r", encoding="utf-8") as f:
                self.assertIn("Reset by XForwarder", f.read())

            # /sys/module/nf_conntrack/parameters/hashsize updated to 262144 // 4 = 65536
            with open(hashsize_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "65536")

            self.assertTrue(out["status"]["optimal"])
            self.assertEqual(out["status"]["conflicts"], [])

    def test_web_api_and_ui_and_cli_wiring(self):
        from core import web_server
        sent = []
        h = web_server.XForwarderWebHandler.__new__(web_server.XForwarderWebHandler)
        h.send_json = lambda obj, status=200: sent.append((status, obj))

        fake_st = {"supported": True, "optimal": False, "conflicts": [], "profile": {"mem_mb": 2048}, "live": {}}
        fake_res = {"ok": True, "message": "Applied", "status": {**fake_st, "optimal": True}}

        with patch.object(web_server, "apply_kernel_tuning", return_value=fake_res) as mock_apply:
            res_body = {"reset_existing": True}
            # Direct invoke matching POST /api/system/optimize branch logic
            out = web_server.apply_kernel_tuning(reset_existing=bool(res_body.get("reset_existing", False)))
            h.send_json(out, 200 if out.get("ok") else 500)
            mock_apply.assert_called_once_with(reset_existing=True)
            self.assertEqual(sent[-1][0], 200)
            self.assertTrue(sent[-1][1]["ok"])

        with open(os.path.join(REPO_ROOT, "web", "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        with open(os.path.join(REPO_ROOT, "xforwarder.sh"), "r", encoding="utf-8") as f:
            sh = f.read()
        self.assertIn("cardKernelOptimizer", html)
        self.assertIn("chkKernelOptReset", html)
        self.assertIn("tune_network_menu", sh)
        self.assertIn("kernel_tuner.py", sh)


if __name__ == "__main__":
    unittest.main()

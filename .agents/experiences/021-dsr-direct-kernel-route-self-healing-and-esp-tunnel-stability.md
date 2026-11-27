# Experience 021: DSR Direct Kernel Route Self-Healing and ESP Tunnel Stability

**Date:** 2026-11-27  
**Category:** Networking  
**Status:** Active  

---

## 1. Context & Motivation
Production relays using XForwarder `nftables_dsr_direct` over strongSwan XFRM `esp*` tunnels experienced prolonged (~30+ minute) blackouts across all DSR Direct ports after tunnel watchdog restarts, only recovering after restarting XForwarder or editing rules. Meanwhile, XFRM counters accumulated `XfrmInStateSeqError` drops and parallel duplicate `CHILD_SA` instances across short rekey windows.

## 2. Root Cause / Core Dynamics
- **Kernel Policy Route Eviction on Interface Flap:** When a tunnel script or watchdog ran `ip link del dev <iface>` (e.g., `esp3-down.sh` followed by `esp3-up.sh`), the Linux kernel immediately purged `default dev <iface>` and `throw <wan_ip>/32` from the slot's custom policy routing table (`table 42600+`), leaving packets marked `0x42600001+` falling back to `main` or failing routing (`TX` collapsed while `RX` remained active).
- **Sticky Skip Flag Without Kernel Verification:** XForwarder only applied `ensure_dsr_direct_policy_routing()` when nftables content changed (`_DSR_DIRECT_POLICY_APPLIED`), so once the NFTables ruleset matched, `reconcile_dsr_direct_kernel_routes()` never checked whether a subsequent netdev deletion had wiped `table 42600+`.
- **ESP XFRM Replay & Duplicate SA Churn:** Default `replay_window` (`32`), missing `unique = replace`, aggressive `rekey_time = 30m`, and `close_action = start` / `dpd_action = restart` on responder (`kharej`) nodes allowed overlapping SAs and watchdog-induced interface deletion. Additionally, `99-xmanager-tunnel.conf` loaded after `99-xforwarder.conf` in `sysctl`, overriding XForwarder's TCP buffer and NAPI tuning.

## 3. Architecture & Solution Implemented
- **Self-Healing Kernel Reconciliation (`core/firewall.py`, `core/engine.py`):**
  - Added `_parse_dsr_direct_ids()` (shared DRY validator bounded by `DSR_DIRECT_TABLE_BASE`, `DSR_DIRECT_PRIO_BASE`, `DSR_DIRECT_MARK_BASE`, `DSR_DIRECT_MAX_SLOTS`) and expanded `reconcile_dsr_direct_kernel_routes()` to treat `"fib table does not exist"` cleanly, restore missing `default dev <iface>`, `throw <ip>/32`, `ip rule` entries (checking parsed `prio`/`table_id`), and `rp_filter=0` in `/proc/sys/net/ipv4/conf/<iface>/rp_filter` when `/sys/class/net/<iface>` exists.
  - Updated `apply_nftables()` to verify `DSR_DIRECT_STATE_PATH` existence even when `_DSR_DIRECT_POLICY_APPLIED` is true, and updated `XForwarderEngine.run_loop()` to cache `_last_dsr_direct_routes` and either rebuild missing state files (`ensure_dsr_direct_policy_routing`) or reconcile routes on every tick.
- **ESP-Direct Tunnel Hardening (`XManager/Tunnels/ESP-Direct/esp-tunnel.sh` `v1.1.0`):**
  - Enabled `unique = replace`, `replay_window = 1024`, `rekey_time = 6h` (IKE) / `2h` (`rand_time = 10m`, `life_time = 2h30m` CHILD), and passive responder actions (`none`/`clear`/`none`) on `kharej`.
  - Replaced blind interface deletion in the watchdog with a 2-stage recovery (soft `swanctl` SA reset at 3 failures without deleting `esp*`, full restart only at 6+ failures) and immediate `/run/xforwarder/dsr_direct_routes.json` sync + `SIGUSR1` wakeup in `esp*-up.sh`.
  - Deferred `sysctl` ownership to XForwarder's `99-xforwarder.conf` (removing legacy `99-xmanager-tunnel.conf` via `--upgrade` / menu option `18`).

## 4. Invariants & Rules for AI Agents
- Rule 1: Never skip `ensure_dsr_direct_policy_routing()` based solely on an in-memory boolean if `DSR_DIRECT_STATE_PATH` is absent on disk.
- Rule 2: Always validate `table_id`, `priority`, `fwmark`, and interface names via `_parse_dsr_direct_ids()` and `IFACE_NAME_REGEX` (never allow path traversal like `../` into `/proc/sys/net/ipv4/conf/`).
- Rule 3: Prefer soft IKE/CHILD SA re-negotiation over `ip link del` on active XFRM netdevs used by policy routing tables.

## 5. Verification & Testing
- Verify with `python -m unittest tests.test_nftables_dsr -v` and `python .agents/scripts/verify-all.py`.
- Key unit test coverage: `test_reconcile_dsr_direct_kernel_routes_heals_missing_routes_rules_and_rp_filter`, `test_parse_dsr_direct_ids_and_reconcile_edge_cases`, and `test_engine_run_loop_rebuilds_or_reconciles_dsr_direct_routes` in `tests/test_nftables_dsr.py`.

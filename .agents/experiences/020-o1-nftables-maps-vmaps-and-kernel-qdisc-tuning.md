# Experience 020: O1 NFTables Maps VMaps and Kernel Qdisc Tuning

**Date:** 2026-11-24  
**Category:** Performance & Networking  
**Status:** Active  

---

## 1. Context & Motivation
Multi-port kernel forwarding nodes (especially 2-vCPU KVM relays with 20+ DSR/DNAT ports over FOU/GRE/IPIP tunnels) experienced elevated `NET_RX` SoftIRQ overhead, `nf_conntrack` hash restarts, and `tc fq` `flows_plimit` tail drops due to linear $O(N)$ NFTables chain traversal, empty active IPv6 Netfilter hooks, default 100p `fq` flow limits, and 2-hour conntrack retention.

## 2. Root Cause / Core Dynamics
1. **Linear NFTables Evaluation:** Per-port sequential rules in `raw_prerouting`, `prerouting`, and `4 * N` counter rules in `forward` plus per-target `tcp flags syn` MSS clamping forced every packet through $O(N)$ rule checks.
2. **Compatibility Pitfalls with `th` / `dnat ip to`:** Using `th dport` or `dnat ip to` fails on Ubuntu 20.04 (`nftables 0.9.3`), and mixing `notrack` with stateful rules in a single `raw_prerouting` map risks marking non-DSR ports untracked.
3. **Empty IPv6 Hooks:** Attaching `prerouting`, `postrouting`, and `forward` hooks to `table ip6 xfwd_orchestrator` when zero IPv6 rules exist incurs pointless hook traversal.
4. **NIC/Qdisc/NAPI Defaults:** UDP tunnel segmentation offloads (`tx-udp_tnl-segmentation`) cause GSO/checksum issues on FOU tunnels, kernel `fq` defaults to `flow_limit 100` (non-persistent across reboots), and low `netdev_budget` causes `time_squeeze`.

## 3. Architecture & Solution Implemented
1. **O(1) `map` / `vmap` + `syn_mss` in `core/firewall.py`:**
   - `_optimize_raw_rules` and `_optimize_dnat_rules` emit separate `tcp dport` and `udp dport` `map` lookups (no `th` or `dnat ip to`) for groups with `>= 2` same-port 1:1 entries, strictly keyed by `(iif_clause, daddr_clause, has_notrack, ip_kw)` with dedicated `@raw_nt_set_*` before `@raw_dst_map_*` for `notrack` rules and port/IP validation (`1..65535`).
   - `_build_forward_counter_vmaps` generates `vmap_in` / `vmap_out` with `c_in_<port>` / `c_out_<port>` chains preserving `cnt_in_<port>` / `cnt_out_<port>` compatibility for `core/traffic.py`.
   - `dsr_mss_rules` are isolated into `chain syn_mss` jumped via `tcp flags & (syn|rst) == syn jump syn_mss`.
   - `apply_nftables` automatically falls back to linear ruleset generation (`optimize_maps=False`) if `nft -c -f` rejects maps/vmaps on legacy kernels.
2. **Zero-Hook Empty IPv6 Table:** When all IPv6 rule lists are empty, `table ip6 xfwd_orchestrator` emits only `counter` blocks with zero Netfilter hook chains.
3. **NIC, Qdisc & Sysctl Tuning (`xforwarder.sh` & `core/engine.py`):**
   - Preserves `tso on gso on gro off` while disabling `tx-udp_tnl-segmentation off tx-udp_tnl-csum-segmentation off`.
   - Configures `net.core.netdev_budget = 1200`, `netdev_budget_usecs = 8000`, `dev_weight = 128`, `netdev_max_backlog = 100000`, `nf_conntrack_tcp_timeout_established = 3600`, `nf_conntrack_udp_timeout = 30`, `nf_conntrack_udp_timeout_stream = 60`.
   - Applies `tc qdisc replace dev <wan> root fq flow_limit 1000` in both `tune_network` and `ensure_fq_qdisc` at `XForwarderEngine.run_loop()` startup so it persists across reboots.

## 4. Invariants & Rules for AI Agents
- Never emit `th dport` or `dnat ip to` inside `table ip/ip6 xfwd_orchestrator` (keep `tcp dport` / `udp dport` for `nftables >= 0.9.3` compatibility).
- Never place `notrack` ahead of a map lookup without a port set guard (`@raw_nt_set_*`), and never merge `notrack` and stateful rules in `raw_prerouting`.
- Keep `gro off` as the default NIC offload profile alongside `tx-udp_tnl-segmentation off`.

## 5. Verification & Testing
- Run `python -m unittest tests/test_performance_and_optimizations.py tests/test_nftables_dsr.py`
- Run `python .agents/scripts/verify-all.py`

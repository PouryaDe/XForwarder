# Experience 019: Health-Aware Load Balancing for NFTables & Nginx Pools

**Date:** 2026-11-24  
**Category:** Architecture & Networking  
**Status:** Active  

---

## 1. Context & Motivation
Relay deployments often need to distribute traffic across multiple upstream exit servers behind a single listening port (e.g., to aggregate bandwidth or survive single-node drops) while preserving XForwarder's priority-based failover guarantee and zero-collision architecture.

## 2. Root Cause / Core Dynamics
1. **Stateful NAT port translation inside NFTables:** Kernel `nftables` `map` expressions can look up an IP (`dnat to jhash ip saddr mod N map { ... }`), or an IP:port pair (`vmap` -> subchains `chain xfwd_lb_<key>`), when per-backend ports differ from the inbound port or when an inbound `port_range` targets a fixed backend port (`is_inbound_range=True`), even if the fixed backend port numerically equals `inbound_start_port`.
2. **Pool-level vs. Node-level session disruption:** Flushing the entire port's conntrack when one backend node goes down terminates healthy sessions on surviving nodes; conversely, not flushing `reply_src` traps UDP/TCP flows against a dead backend.
3. **Config sync/import & security boundaries:** Multi-server Nginx `upstream` blocks require preservation during pull-sync (`sync_xforwarder_from_nginx`), and direct calls to `build_nft_lb_dnat_entries()` / `build_nginx_lb_upstream()` require explicit IP, port, and upstream-name sanitization.

## 3. Architecture & Solution Implemented
- **Schema (`core/config_manager.py`):** Added pool-per-priority fields (`lb_enabled`, `lb_mode`, `lb_targets` up to `MAX_LB_TARGETS = 16`, weights `1..100`, `enabled`, `tunnel_iface`, `note`) permitted exclusively on standard `nftables` and `nginx` destinations (disabled on `haproxy`, `nftables_dsr`, `nftables_dsr_relay`), with atomic validation and normalization.
- **Kernel & Proxy Generation (`core/firewall.py`, `core/proxy_gen.py`):** Implemented `normalize_lb_weights()`, `build_nft_lb_dnat_entries()` (supporting `ip_hash`, `round_robin`, `random`, IPv4/IPv6 `map`/`vmap` subchains, and `is_inbound_range` detection), and `build_nginx_lb_upstream()` (supporting `ip_hash`, `round_robin`, `least_conn`, `random` with regex/delimiter sanitization and `max_fails=2 fail_timeout=15s`).
- **Health-Aware Engine (`core/engine.py`):** Added `_evaluate_lb_destination()` (per-IP 60s/15s cache reuse, dynamic pruning of unhealthy backends, re-admission hysteresis, pool exhaustion failover) and `_queue_targeted_conntrack_flush()` (`reply_src` flush executed post-sync via `flush_conntrack(port, reply_src=..., family=...)`).
- **Metrics, Web & UI (`core/metrics.py`, `core/service_manager.py`, `core/web_server.py`, `web/`):** Deduplicated `lb_targets` IPs in the 50-probe scheduler, enriched `/api/status` with `lb_members`, preserved Nginx LB upstreams across sync/import, and built Ovira Mint Dark/Light RTL UI pools with inline testing and tooltips.

## 4. Invariants & Rules for AI Agents
- **Rule 1:** Only allow `lb_enabled` on standard `nftables` and `nginx` destinations (`LB_SUPPORTED_TYPES`); reject mixed IPv4/IPv6 pools within the same rule.
- **Rule 2:** Always pass `is_inbound_range=bool(port_range)` to `build_nft_lb_dnat_entries()` so `port_range -> fixed_port` always emits `vmap` + fixed `:port` DNAT chains even when `fixed_port == inbound_start_port`.
- **Rule 3:** Queue failed backend cleanups via `reply_src` in `_pending_targeted_conntrack_flushes` (post-sync) instead of wiping the whole port's conntrack on surviving healthy nodes.
- **Rule 4:** Keep `web/style.css` synchronized with `web/css/{tokens,base,layout,components,modals,rtl}.css`.

## 5. Verification & Testing
- Dedicated unit & edge-case tests in `tests/test_load_balancing.py`.
- Full repository verification: `python .agents/scripts/verify-all.py`.

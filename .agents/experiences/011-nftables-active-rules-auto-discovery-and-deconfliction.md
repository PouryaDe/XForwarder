# Experience 011: NFTables Active Rules Auto-Discovery and Deconfliction

**Date:** 2026-10-22  
**Category:** Firewall & Architecture  
**Status:** Active  

---

## 1. Context & Motivation
When users install XForwarder on a relay server that was previously running standalone kernel DNAT rules (via custom nftables scripts, `/etc/nftables.conf`, or iptables-nft), the installer originally only scanned `/etc/haproxy/haproxy.cfg`. Pre-existing active NFTables rules in the kernel or persistent configuration files were completely ignored, leaving `config.json` with an empty rules list. Furthermore, because legacy DNAT rules remained active in external tables (such as `table ip nat`), kernel PREROUTING hooks stole traffic before HAProxy could process it, causing port forwarding and priority failover anomalies.

## 2. Root Cause / Core Dynamics
1. **Isolated Orchestrator Table:** XForwarder intentionally isolates all managed forwarding rules in `table ip xfwd_orchestrator` and `table ip6 xfwd_orchestrator` to avoid flushing global rulesets or touching UFW/fail2ban. Consequently, unmanaged external tables were never inspected.
2. **Missing NFTables Parser:** The codebase only had `haproxy_parser.py`. There was no mechanism to parse JSON rulesets (`nft -j list ruleset`), textual rules (`nft -a list ruleset`), or persistent `/etc/nftables.conf` files.
3. **One-Way Sync:** XForwarder synchronizes configuration unidirectionally: `config.json -> HAProxy/NFTables`. Rules not present in `config.json` never appeared in the dashboard.
4. **Kernel PREROUTING Collision Risk:** If an imported port rule is switched to Priority 1 (HAProxy), but the legacy DNAT rule in `table ip nat` is still active, the Linux kernel executes DNAT in PREROUTING, completely bypassing the local listening socket in LOCAL_IN.

## 3. Implemented Solution & Architecture
1. **NFTables & iptables Parser (`core/nftables_parser.py`):**
   - High-performance, zero-dependency parser supporting JSON schema (`nft -j list ruleset`), textual rules with rule handles (`nft -a list ruleset`), and saved iptables format (`iptables-save`).
   - Ignores XForwarder's managed tables (`xfwd_orchestrator`, `fwdman_orchestrator`).
   - Extracts inbound listening ports, target IP/IPv6, target ports, and protocols (`tcp`, `udp`, `both`).
   - Generates standard XForwarder rules with Priority 2 (NFTables) active and an auto-configured Priority 1 primary.
2. **Atomic Pre-Deactivation Backup (`backup_legacy_nftables`):**
   - Saves a full snapshot of the host ruleset to `/etc/xforwarder/backups/legacy_nftables_<timestamp>.nft` before any deletion occurs.
3. **Handle-Based Non-Disruptive Deconfliction (`deactivate_legacy_rules`):**
   - Uses exact rule handles (`nft delete rule <family> <table> <chain> handle <id>`) to remove only the imported DNAT rules from external tables, leaving SSH, fail2ban, and system firewall rules 100% untouched.
4. **Unified Multi-Source Discovery (`discover_all_relay_rules`, `import_all_relay_rules_into_config`):**
   - Unifies discovery across HAProxy and NFTables into a single atomic routine.
   - Integrated into initial setup wizard (`xforwarder.sh install`), CLI menu (Option 8), and CLI dispatcher (`import`, `import-all`, `import-nftables`).
   - Integrated into Web REST API (`GET /api/import/discover`, `POST /api/import/all`, `POST /api/import/nftables`) and Web UI with real-time source breakdown and 1-click import.

## 4. Key Learnings & Verification
- Unit test suite `tests/test_nftables_parser.py` validates text parsing, JSON parsing, iptables fallback, deduplication, atomic writing, and handle deletion with 100% test coverage.
- All 129 tests across the repository pass cleanly in <6s.

# Experience 004: Backward Compatibility and Automated Schema Migrations

**Date:** 2026-10-18  
**Category:** Reliability & Upgrades  
**Status:** Active  

---

## 1. Context & Motivation
XForwarder is continuously maintained and updated on production relay servers. When users run script updates (`xforwarder update` or Option 6 in the interactive CLI menu), existing configurations created under earlier versions (e.g. v1.0, v1.1, v1.2, or Forward-Manager) must be seamlessly upgraded without losing a single port rule, destination target, or admin credential.

## 2. Root Cause / Core Dynamics
- Software schema evolution introduces new attributes (e.g. `schema_version`, `bind_host`, `id`, `force_override`, `protocol: both`, `type: nginx`).
- If an updated daemon expects these fields to exist, it might raise `KeyError`, misparse types (e.g., string `"443"` instead of integer `443`), or worse, overwrite the existing file with an empty default template, wiping out active production traffic.
- Sudden network disconnects or interruptions during updates could corrupt the configuration without a rollback point.

## 3. Architecture & Solution Implemented
1. **Pre-Update Atomic Backup:**
   - In `xforwarder.sh update`, before updating files or restarting services, the active configuration is copied to a timestamped backup:
     `cp "$active_cfg" "${active_cfg}.bak.$(date +%Y%m%d_%H%M%S)"`.
2. **Self-Healing Normalizer (`migrate_and_normalize_config`):**
   - Implemented in `core/engine.py` (and imported in `core/web_server.py`).
   - Automatically executes whenever the configuration is loaded.
   - Detects missing keys and backfills them with non-breaking defaults (`schema_version: 2`, `wan_interface: auto`, `bind_host: 0.0.0.0`, `check_interval_seconds: 8`).
   - Normalizes rule properties: converts string ports to `int`, protocols to lowercase, destination types to lowercase (`haproxy`, `nginx`, `nftables`), and auto-assigns IDs (`rule-<port>`).
   - Idempotent: Subsequent loads of an already-migrated configuration produce zero modifications (`modified == False`).
3. **Dedicated CLI Menu Option:**
   - Option 6 in `xforwarder.sh`: `Update XForwarder (Auto-Migrate & Preserve Rules)`.
   - CLI command: `xforwarder update` or `xfwd update`.
   - Runs `python3 /opt/xforwarder/core/engine.py --migrate "$active_cfg"`.
4. **Dual Path & Cookie Legacy Fallbacks:**
   - Supports both `/etc/xforwarder/config.json` and `/etc/forward-manager/config.json`.
   - Supports both `xfwd_session` and legacy `fwdman_session` cookies.

## 4. Invariants & Rules for AI Agents
- **Zero Data Loss:** Never overwrite or reset `config.json` during updates or code edits.
- **Always Backfill Defaults:** When introducing any new configuration key in Python or JSON schemas, always define a sane default in `migrate_and_normalize_config`.
- **Always Test Idempotence:** Ensure `migrate_and_normalize_config(migrate_and_normalize_config(cfg)[0])[1] is False`.

## 5. Verification & Testing
```bash
# Test migration on legacy dictionary
python3 -c "from core.engine import XForwarderEngine; cfg, mod = XForwarderEngine.migrate_and_normalize_config({'rules': [{'port': '443', 'destinations': [{'target': '2a01::1'}]}]}); print('Migrated:', cfg); assert cfg['rules'][0]['port'] == 443 and cfg['schema_version'] == 2"

# Test CLI migrate flag
python3 core/engine.py --migrate
```

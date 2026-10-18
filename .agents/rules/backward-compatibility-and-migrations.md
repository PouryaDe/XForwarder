# Backward Compatibility & Automated Schema Migration Rule (XForwarder)

## 1. Prime Directive: Zero Data Loss Across Updates
Any software update, CLI upgrade (`xforwarder update` or `xfwd update`), or configuration edit MUST guarantee 100% backward compatibility with all prior versions (including legacy Forward-Manager v1.0, v1.1, v1.2+). Under no circumstances may an update drop, overwrite, or corrupt:
- Existing user-configured port forwarding rules.
- Existing destination targets, comments, tunnel interfaces, or priorities.
- Existing administrator credentials (`username`, `password_hash`).
- Existing custom web ports or secret admin paths.

---

## 2. Mandatory Pre-Update Atomic Backup
Before executing any update, component sync, or schema modification, the update pipeline MUST create a timestamped backup of the active configuration:
```bash
cp "$active_cfg" "${active_cfg}.bak.$(date +%Y%m%d_%H%M%S)"
```
This guarantees an immediate rollback path if a disk write fails or power is interrupted.

---

## 3. Automated Self-Healing Schema Migration (`migrate_and_normalize_config`)
Both `core/engine.py` and `core/web_server.py` MUST run `migrate_and_normalize_config()` on startup and upon loading the configuration file.

### Required Normalization Rules:
1. **Schema Versioning:**
   - Detect absence of `schema_version` or legacy version numbers and upgrade cleanly to the current version (e.g. `schema_version: 2`).
2. **Backward-Compatible Defaults:**
   - Any newly introduced configuration option MUST provide a sane, non-disruptive default (e.g., `wan_interface: "auto"`, `bind_host: "0.0.0.0"`, `check_interval_seconds: 8`).
3. **Type Normalization & Sanitization:**
   - Safely convert string port representations (`"443"`) to integer (`443`).
   - Normalize protocols to lowercase (`"tcp"`, `"udp"`, `"both"`).
   - Normalize destination types to lowercase (`"haproxy"`, `"nginx"`, `"nftables"`).
   - Infer missing destination types (e.g., private IPs `10.x.x.x` or `192.168.x.x` default to `"nftables"`, while external IPv4/IPv6 default to `"haproxy"`).
   - Assign deterministic IDs to legacy rules missing an `id` field (`rule-<port>`).
4. **Idempotence:**
   - Passing an already normalized configuration through `migrate_and_normalize_config()` must result in zero modifications (`modified == False`).
5. **Atomic Persistence:**
   - If migrations occurred, persist changes atomically using temporary files and `os.replace` to prevent corrupted states.

---

## 4. Legacy Path & CLI Compatibility
XForwarder retains dual compatibility with legacy Forward-Manager installations:
- Configuration fallback: `/etc/xforwarder/config.json` -> `/etc/forward-manager/config.json`.
- State fallback: `/run/xforwarder/state.json` -> `/run/forward-manager/state.json`.
- CLI aliases: `/usr/local/bin/xforwarder`, `/usr/local/bin/xfwd`, `/usr/local/bin/forward-manager`, `/usr/local/bin/fwdman`.
- Service transition: Legacy `forward-manager` and `forward-manager-web` services must be cleanly stopped and disabled without breaking active traffic.
- Cookies: Support both `xfwd_session` and legacy `fwdman_session`.

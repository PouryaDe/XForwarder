---
name: fwdman-ops
description: Operational runbook and troubleshooting guide for XForwarder (formerly Forward-Manager) relay and multi-path failover management.
---

# XForwarder Operations Runbook (Legacy Alias: fwdman-ops)

> [!NOTE]
> This skill is maintained for backward compatibility. Please see [xfwd-ops](../xfwd-ops/SKILL.md) for the active primary operational skill.

## Quick CLI Command Reference
- Interactive Management Menu: `sudo xforwarder` (or `sudo xfwd`, `sudo fwdman`)
- Display Web Dashboard URL and credentials: `sudo xforwarder url`
- Display live terminal status table: `sudo xforwarder status`
- Change admin username or password: `sudo xforwarder password`
- Restart all services: `sudo xforwarder restart`
- Tail live engine logs: `sudo xforwarder logs`

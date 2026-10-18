---
trigger: always_on
description: Bash CLI conventions, deployment locations, systemd service management, and installer guidelines.
---

# Bash CLI & Deployment Standards (`xforwarder.sh`)

## 1. Shell Scripting Conventions
- **Strict Execution Mode**: Always include `set -Eeuo pipefail` at the top of bash scripts.
- **Root Enforcement**: Any mutating or system management command must check `check_root` (`EUID -ne 0`).
- **Standardized Messaging**:
  - `msg_info`: Cyan `[INFO]`
  - `msg_ok`: Green `[OK]`
  - `msg_warn`: Yellow `[WARN]`
  - `msg_err`: Red `[ERROR]` directed to `>&2`

## 2. Directory & Path Hierarchy
- Installation directory: `/opt/xforwarder/` (contains `core/` and `web/`).
- Persistent configuration: `/etc/xforwarder/config.json` (fallback: `/etc/forward-manager/config.json`).
- Systemd service units: `/etc/systemd/system/xforwarder.service` and `/etc/systemd/system/xforwarder-web.service`.
- Global CLI symlinks: `/usr/local/bin/xforwarder` and `/usr/local/bin/xfwd` (aliases: `/usr/local/bin/forward-manager`, `/usr/local/bin/fwdman`).

## 3. Service Lifecycle Management
- Both daemons must run 24/7 as standalone systemd units:
  - `xforwarder.service` (Core failover engine)
  - `xforwarder-web.service` (Web dashboard)
- When installing or reconfiguring, always execute:
  ```bash
  systemctl daemon-reload
  systemctl enable --now xforwarder.service xforwarder-web.service
  ```
- Graceful restart via CLI: `xforwarder restart` or `xfwd restart`.

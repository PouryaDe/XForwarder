---
name: xfwd-ops
description: Operational runbook and troubleshooting guide for XForwarder relay and multi-path failover management.
---

# XForwarder Operations Runbook

This skill guides the agent through operating, maintaining, configuring, and verifying the XForwarder system.

## Quick CLI Command Reference
- Interactive Management Menu: `sudo xforwarder` (or `sudo xfwd`)
- Display Web Dashboard URL and credentials: `sudo xforwarder url`
- Display live terminal status table: `sudo xforwarder status`
- Change admin username or password: `sudo xforwarder password`
- Restart all services: `sudo xforwarder restart`
- Tail live engine logs: `sudo xforwarder logs`
- Backward compatible aliases: `fwdman` and `forward-manager` also work interchangeably.

## Configuration Schema (`/etc/xforwarder/config.json`)

```json
{
  "wan_interface": "auto",
  "check_interval_seconds": 8,
  "failure_threshold": 3,
  "recovery_threshold": 3,
  "web": {
    "bind_host": "0.0.0.0",
    "port": 8090,
    "secret_path": "xfwd-admin",
    "auth": {
      "username": "admin",
      "password_hash": "<SHA256_HEX>"
    }
  },
  "rules": [
    {
      "id": "rule-2023",
      "port": 2023,
      "protocol": "both",
      "active_priority": 1,
      "force_override": 0,
      "destinations": [
        {
          "priority": 1,
          "type": "haproxy",
          "target": "2001:4ba0:cafe:84e::1",
          "port": 2023,
          "comment": "Foreign Server 1 - Primary IPv6 Relay"
        },
        {
          "priority": 2,
          "type": "nftables",
          "target": "10.88.1.2",
          "port": 2023,
          "tunnel_iface": "gre1",
          "comment": "Foreign Server 1 - Backup Tunnel"
        }
      ]
    }
  ]
}
```

## Health Check Simulation
To simulate destination checks locally:
```python
import socket

def test_conn(host, port, timeout=2.0):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception as e:
        return False
```

## Zero-Collision Invariant Checks
Always verify that no port has both HAProxy binding and NFTables DNAT:
1. `nft list table ip xfwd_orchestrator`
2. `cat /etc/haproxy/haproxy.cfg`
3. If both exist for the same port, check why `engine.py`'s `sync_firewall_and_proxies()` did not synchronize properly.

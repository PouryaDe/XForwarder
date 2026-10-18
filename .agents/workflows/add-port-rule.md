---
name: add-port-rule
description: Workflow for safely creating and validating a new forwarding rule in XForwarder.
---

# Workflow: Add Port Rule

Follow this workflow when defining a new multi-path forwarding rule for a port.

## Step 1: Gather Rule Parameters
- **Port**: Inbound port number (e.g., `2023`). Ensure it does not conflict with existing services.
- **Protocol**: `tcp`, `udp`, or `both`.
- **Priority 1 (Primary - HAProxy Relay)**:
  - Destination Type: `haproxy`
  - Target: Foreign IPv6 address (e.g., `2001:4ba0:cafe:84e::1`)
  - Target Port: Same as inbound port, or backend port.
  - Comment: Human-readable label (e.g., "Foreign Node 1 - IPv6 Relay").
- **Priority 2 (Backup - NFTables Tunnel)**:
  - Destination Type: `nftables`
  - Target: Foreign tunnel IPv4 address (e.g., `10.88.1.2`)
  - Target Port: Same or backend port.
  - Tunnel Interface: e.g., `gre1`, `ipip1`, `ftcp0`, `awg0`.
  - Comment: Human-readable label (e.g., "Foreign Node 1 - Backup Tunnel").

## Step 2: Validate Target Reachability
Before committing the rule, verify network reachability:
```bash
# Test IPv6 Primary connection
nc -zv6 -w 3 <IPv6_TARGET> <PORT>

# Test IPv4 Tunnel connection
ping -c 2 -W 2 <TUNNEL_IP>
```

## Step 3: Register Rule in Configuration
Add the rule object to the `rules` array in `/etc/xforwarder/config.json`:
```json
{
  "id": "rule-<PORT>",
  "port": <PORT>,
  "protocol": "both",
  "active_priority": 1,
  "force_override": 0,
  "destinations": [
    {
      "priority": 1,
      "type": "haproxy",
      "target": "<IPv6_TARGET>",
      "port": <PORT>,
      "comment": "<PRIMARY_LABEL>"
    },
    {
      "priority": 2,
      "type": "nftables",
      "target": "<TUNNEL_IP>",
      "port": <PORT>,
      "tunnel_iface": "<IFACE>",
      "comment": "<BACKUP_LABEL>"
    }
  ]
}
```

## Step 4: Verify Synchronization
Restart or reload the engine:
```bash
xforwarder restart
# Or check status
xforwarder status
```
Inspect `/run/xforwarder/state.json` to confirm `active_priority` is set and both destinations report status and latency.

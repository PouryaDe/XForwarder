---
name: diagnose-failover
description: Step-by-step diagnostic procedure for troubleshooting failover, port collisions, or probe anomalies.
---

# Workflow: Diagnose Failover & Forwarding

Follow this procedure when investigating unexpected failovers, unreachable ports, or service status discrepancies.

## Step 1: Check Runtime Daemon State
Inspect the runtime state file:
```bash
cat /run/xforwarder/state.json | jq .
```
- Verify `last_check_timestamp` is advancing (confirms engine loop is actively checking).
- Review `rules_state.<rule_id>.dest_stats`:
  - Check `consecutive_fails` and `consecutive_success`.
  - Check `latency_ms` and `status` (`healthy`, `failed`, or `unknown`).

## Step 2: Check Systemd Logs
View the live engine logs:
```bash
journalctl -u xforwarder -n 50 --no-pager
```
Search for:
- Socket connection timeouts or errors.
- Failure threshold reached messages: `[FAILOVER] Switching rule-<port> from Priority 1 to Priority 2`.
- NFTables or HAProxy reload errors.

## Step 3: Verify Zero-Collision Rule Enforcement
For the affected port:
1. If **Priority 1 (HAProxy)** is active:
   - Check if HAProxy is listening:
     ```bash
     ss -tulpn | grep :<PORT>
     ```
   - Verify NFTables does NOT contain a DNAT rule for this port:
     ```bash
     nft list table ip xfwd_orchestrator | grep :<PORT>
     ```
2. If **Priority 2 (NFTables)** is active:
   - Verify HAProxy is NOT binding this port:
     ```bash
     ss -tulpn | grep :<PORT>
     ```
   - Verify NFTables prerouting table contains the DNAT rule:
     ```bash
     nft list chain ip xfwd_orchestrator prerouting | grep :<PORT>
     ```

## Step 4: Test Manual Override
If automatic probing is inconclusive, test manual override to isolate network issues:
- Via Web UI: Change mode to `Force: Priority 1` or `Force: Priority 2`.
- Via API:
  ```bash
  curl -s -X POST http://127.0.0.1:8090/api/override \
    -H "Content-Type: application/json" \
    -d '{"rule_id": "rule-<PORT>", "force_override": 1}'
  ```
Confirm whether client traffic flows when locked to a specific path.

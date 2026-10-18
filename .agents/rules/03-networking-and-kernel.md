---
trigger: always_on
description: Kernel networking, NFTables table isolation, HAProxy configuration, and tunnel interface standards.
---

# Networking & Kernel Standards (XForwarder)

## 1. Table Isolation in NFTables
All DNAT routing managed by XForwarder must strictly reside inside the dedicated table:
`table ip xfwd_orchestrator`

- **Do Not Flush System Tables**: Never execute `nft flush ruleset`. Only delete and rebuild `table ip xfwd_orchestrator`.
- **Pre-Validation**: Always validate generated NFT rules using syntax dry-run before applying:
  ```bash
  nft -c -f - < generated_rules.nft
  ```
- **Masquerading Interface Masks**: The postrouting chain masquerades outbound traffic on recognized tunnel interfaces:
  `oifname { "gre*", "ipip*", "ftcp*", "awg*", "gnv*", "vxlan*" }} masquerade`

## 2. HAProxy Zero-Tunnel Relay
- **Config Path**: `/etc/haproxy/haproxy.cfg`
- **Protocol**: `mode tcp`, with TCP keepalives and appropriate timeouts (`timeout connect 5s`, `timeout client 1h`, `timeout server 1h`).
- **Proxy Protocol**: Backend servers receive client real IPs when configured with `send-proxy-v2`.
- **Reloading Mechanism**: Use non-disruptive reload (`systemctl reload haproxy`) to preserve existing connections during rule updates.

## 3. Kernel Forwarding Requirements
- Ensure `net.ipv4.ip_forward = 1` is persistently enabled via `/etc/sysctl.conf`.
- System nftables service should be disabled (`systemctl disable --now nftables`) to prevent boot-time flush conflicts with the dynamic orchestrator.

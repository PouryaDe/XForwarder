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
  `oifname { "gre*", "ipip*", "ftcp*", "awg*", "gnv*", "vxlan*", "wg*", "tun*" } masquerade`
- **TCP MSS Clamping**: The forward chain must clamp TCP MSS to the path MTU (`tcp flags syn tcp option maxseg size set rt mtu`) to prevent tunnel MTU packet drops and fragmentation over GRE, IPIP, and AWG tunnels.

## 2. HAProxy Zero-Tunnel Relay
- **Config Path**: `/etc/haproxy/haproxy.cfg`
- **Protocol**: `mode tcp`, with TCP keepalives and appropriate timeouts (`timeout connect 5s`, `timeout client 1h`, `timeout server 1h`).
- **Worker Lifecycle Management**: The `global` section must enforce `hard-stop-after 2m` so old worker processes from previous reloads terminate cleanly after 2 minutes instead of lingering as zombie workers.
- **Proxy Protocol**: Clean raw TCP forwarding is the default. Backend servers receive `send-proxy-v2` ONLY when `proxy_protocol` is explicitly toggled on for that destination. Never hardcode `send-proxy-v2`.
- **Reloading Mechanism**: Use non-disruptive reload (`systemctl reload haproxy`) to preserve existing connections during rule updates.

## 3. Kernel Forwarding Requirements
- Ensure `net.ipv4.ip_forward = 1` is persistently enabled via `/etc/sysctl.conf`.
- System nftables service should be disabled (`systemctl disable --now nftables`) to prevent boot-time flush conflicts with the dynamic orchestrator.

## 4. Topology & Interface Discovery Standards (`get_network_interfaces_info`)
- **Default Kernel Fallback Devices Excluded**: Never list Linux kernel template/fallback devices in `tunnel_interfaces`:
  `gre0`, `gretap0`, `erspan0`, `tunl0`, `sit0`, `ip6tnl0`, `ip6gre0`, `ip6erspan0`, `dummy0`, `teql0`.
- **Virtualization & Container Bridges Excluded**: Never list local container/hypervisor bridges:
  `docker*`, `veth*`, `virbr*`, `br-*`.
- **Unconfigured Inactive Devices Excluded**: Skip virtual interfaces that have no assigned local IP, no peer IP, and are in state `DOWN`.
- **Primary WAN Excluded from Tunnels**: Primary WAN interface (e.g. `eth0`) IPs are categorized strictly under `server_ips`, never under `tunnel_interfaces`.

## 5. Golden NIC Offload Profile (`tso on gso on gro off`)
- **Transmit Offloading (TSO/GSO on)**: Required for high-throughput HAProxy and proxy relays to delegate packet fragmentation to the NIC, reducing CPU software interrupt load (`ksoftirqd` / `si`).
- **Generic Receive Offload (GRO off)**: Must be disabled on physical interfaces handling GRE or IPIP encapsulation. If GRO is enabled, incoming packets are aggregated into 64KB super-packets which cannot be encapsulated over smaller MTU tunnels without hardware tunnel offload, causing silent packet drops and tunnel throttling.


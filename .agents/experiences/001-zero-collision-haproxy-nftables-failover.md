# Experience 001: Zero-Collision HAProxy and NFTables Failover

**Date:** 2026-10-18  
**Category:** Networking & Architecture  
**Status:** Active  

---

## 1. Context & Motivation
On intermediate Linux relay servers (e.g. Iran VPS), traffic forwarding towards foreign servers can use either:
- **Priority 1**: Direct IPv6 user-space relay via HAProxy.
- **Priority 2**: Kernel Layer-3 tunnels (GRE, IPIP, FakeTCP, AmneziaWG) via NFTables DNAT.

If both HAProxy and NFTables DNAT operate on the same port at the same time, severe socket collisions, packet dropping, and connection resets occur.

## 2. Root Cause / Core Dynamics
- HAProxy binds user-space socket listeners on `*:<port>`.
- NFTables DNAT hooks into `prerouting` priority `dstnat` in the Linux network stack before sockets receive packets.
- When DNAT is active, packets are redirected at the kernel level and never reach the HAProxy socket.
- Conversely, if HAProxy binds a port while DNAT is pointing elsewhere, UDP/TCP traffic experiences split-brain behavior.

## 3. Architecture & Solution Implemented
XForwarder enforces an absolute **Zero-Collision Invariant**:
1. When Priority 1 is active:
   - HAProxy writes `listen fwd_<port>` with `bind *:<port>` in `/etc/haproxy/haproxy.cfg`.
   - NFTables DNAT rule for that port is omitted from `table ip xfwd_orchestrator`.
2. When Priority 2 is active:
   - HAProxy does NOT bind `<port>`.
   - Kernel DNAT rule is added to `table ip xfwd_orchestrator prerouting`:
     `iifname "<WAN>" (tcp|udp) dport <port> dnat to <tunnel_target>:<target_port>`.
   - Outbound masquerading is dynamically scoped to tunnel interfaces:
     `oifname { "gre*", "ipip*", "ftcp*", "awg*", "gnv*", "vxlan*" } masquerade`.

## 4. Invariants & Rules for AI Agents
- A port must **NEVER** exist in both HAProxy listener config and NFTables DNAT rules simultaneously.
- Always validate NFTables syntax with `nft -c -f -` before applying.
- Never flush global system ruleset (`nft flush ruleset` is strictly prohibited); only flush and rebuild the dedicated `table ip xfwd_orchestrator`.

## 5. Verification & Testing
```bash
# Check HAProxy listener
ss -tulpn | grep :<port>

# Check NFTables DNAT
nft list table ip xfwd_orchestrator | grep :<port>
```
Confirm only one of the above handles the port at any given time.

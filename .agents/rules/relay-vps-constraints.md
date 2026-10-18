---
name: relay-vps-constraints
description: "Linux intermediate relay server resource limits, non-blocking network socket constraints, and isolation standards."
always_on: true
trigger: always_on
---

# Intermediate Relay VPS Constraints Rule (XForwarder)

XForwarder operates on low-resource Linux relay servers (e.g. Iran VPS with 512MB-1GB RAM) handling critical high-bandwidth, low-latency tunnel traffic.

---

## 1. Strict Resource Ceilings
- **Idle RAM Limit:** Combined RAM consumption of both `engine.py` and `web_server.py` must stay strictly under **15MB**.
- **CPU Overhead:** Probing and idle polling cycles must consume <1% CPU.
- **Zero Heavy Runtimes:** No Node.js, no Docker, and no external pip frameworks.

---

## 2. Non-Blocking Probing & Socket Safety
- **Socket Timeouts:** Destination health checks must always enforce explicit connection timeouts (`socket.create_connection(..., timeout=2.0)`).
- **Socket Cleanup:** Sockets must be closed immediately after testing (using `with` context or `finally` blocks) to prevent file descriptor leaks.
- **High File Descriptor Limits:** The systemd unit sets `LimitNOFILE=1048576` to ensure thousands of concurrent connections are supported without `Too many open files` errors.

---

## 3. Kernel Isolation
- **NFTables Isolation:** All DNAT and masquerading rules must reside exclusively in `table ip xfwd_orchestrator`.
- **Global Firewall Safety:** Never execute `nft flush ruleset` or `iptables -F`. Other system firewall rules (e.g. UFW, fail2ban, XManager tunnels) must remain unaffected.

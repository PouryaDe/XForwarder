# Experience 012: Kernel Zero-Copy Splicing, BBR Network Tuning, and Session Timeout Optimization

**Date:** 2026-10-22  
**Category:** Performance & Networking  
**Status:** Active  

---

## 1. Context & Motivation
When heavy proxy/VPN traffic was routed through XForwarder relay servers, significant CPU utilization and load average spikes occurred compared to the reference `haproxy.sh` standalone script. Investigation revealed that while HAProxy and Nginx were routing traffic, their operating configurations were copying all socket payloads through user space, generating verbose per-connection syslog records, holding UDP pseudo-sessions open for 3600 seconds, and operating on standard un-tuned Linux kernel defaults (CUBIC congestion control, 128 backlog, and low file descriptor limits).

## 2. Root Cause / Core Dynamics
1. **Absence of Zero-Copy Kernel Splicing:** Without `option splice-auto`, HAProxy invoked `recv()` and `send()` syscalls across every payload chunk, moving data back and forth between kernel buffers and user-space memory. This created thousands of context switches per second and saturated CPU cores under high bandwidth.
2. **Aggressive Connection Logging (`option tcplog`):** Logging every individual TCP session produced thousands of IPC records to `/dev/log` per minute under VPN workloads, starving CPU cycles across `systemd-journald` and driving up disk I/O wait.
3. **UDP Pseudo-Session Zombie Accumulation:** Setting `proxy_timeout 1h;` for connectionless UDP traffic caused Nginx to maintain epoll timers and kernel socket states for 3600 seconds after a single packet, accumulating tens of thousands of dormant sockets under DNS, QUIC, and gaming traffic.
4. **CUBIC Retransmission Storms & Small Backlogs:** Cross-border international VPS links suffer occasional packet loss. Standard CUBIC congestion control slashes window sizes by 50% on loss, causing retransmission storms. Furthermore, default Linux `somaxconn` (128) caused SYN drops under burst handshakes.

## 3. Architecture & Solution Implemented
1. **HAProxy Zero-Copy Splicing & Dynamic Pipes:**
   - Added `option splice-auto`, `tune.pipesize 262144`, `tune.bufsize 65536`, and multi-core CPU thread affinity (`nbthread` + `cpu-map`) in `core/engine.py`.
   - Replaced `option tcplog` with quiet `notice`-level logging (`log /dev/log local0 notice`, `option dontlognull`).
   - Enabled `option clitcpka` and `option srvtcpka` to sweep zombie client connections.
   - Built a pre-validation fallback: if an esoteric HAProxy build rejects `splice-auto` or threading directives, the engine automatically strips tuning directives and verifies syntax cleanly.
2. **60-Second UDP Session Timeout & 64k Buffers:**
   - Configured `proxy_timeout 60s;` on Nginx stream UDP servers and HAProxy UDP helper listeners.
   - Increased Nginx stream buffer size to `proxy_buffer_size 64k;`.
3. **Kernel Performance Engine (`tune_network` in `xforwarder.sh`):**
   - Automatically detects host RAM/CPU and applies dynamic resource profiles (Tiers 1-4).
   - Enables Google BBR congestion control (`net.ipv4.tcp_congestion_control = bbr` + `net.core.default_qdisc = fq`).
   - Scales connection queues (`somaxconn = 65535`, `tcp_max_syn_backlog = 65535`, `netdev_max_backlog = 16384`).
   - Configures `tcp_tw_reuse = 1`, `tcp_fin_timeout = 15`, `tcp_mtu_probing = 1`, and `nf_conntrack_udp_timeout_stream = 60`.
   - Deploys systemd drop-in override for HAProxy (`/etc/systemd/system/haproxy.service.d/override.conf`) setting `LimitNOFILE=1048576`.
   - Exposed via CLI (`xforwarder tune`) and menu item 11.

## 4. Invariants & Rules for AI Agents
- **Zero-Copy First:** HAProxy TCP configurations must always keep `option splice-auto` enabled with dynamic pipe sizing.
- **Never Enable `option tcplog` on Relay Forwarders:** Per-connection logging is strictly forbidden on forwarding relays. Log only errors and state changes.
- **UDP Timeouts Must Never Exceed 60s:** Stream proxying for UDP must enforce bounded timeouts (60 seconds) to prevent socket table exhaustion.
- **Auto-Tuning on Deployment:** `tune_network` must run automatically during installation and updates.

## 5. Verification & Testing
- Run `python -m unittest tests/test_performance_and_optimizations.py` to verify `option splice-auto`, `tune.pipesize`, `proxy_timeout 60s;`, and fallback logic.
- Run `python .agents/scripts/verify-all.py` to validate compliance across the entire repository.

# Experience 014: Per-Port and Per-Tunnel Traffic Accounting & Delta Engine

## Context & Motivation
Intermediate relay servers (e.g. Iran VPS) handle high-throughput client traffic across multiple forwarding ports and tunnel interfaces. Node operators and network administrators require precise, granular bandwidth accounting to monitor bandwidth quotas, detect heavy or abusive ports, and analyze traffic volume trends over hourly, daily, and monthly periods.

Key engineering challenges:
1. HAProxy and NFTables handle different ports simultaneously (Zero-Collision model); metrics must be collected from both without incurring CPU overhead or packet duplication.
2. Kernel and proxy counters reset on service reloads or system reboots.
3. Billing cycles need to be reset independently of historical analytical charts.
4. Relay servers are constrained (<15MB RAM idle, zero pip dependencies).

## Key Decisions & Architectural Changes

1. **Zero-Overhead Dual-Source Accounting**:
   - **NFTables Forward Counters**: Dynamic named counters in `chain forward` (`cnt_in_<port>` for RX/upload, `cnt_out_<port>` for TX/download) count established stream packets at kernel wire-speed with zero user-space overhead.
   - **HAProxy Runtime API Socket**: Communicates with `/run/haproxy/admin.sock` executing `show stat` to read client-side `bin` (Bytes In / RX) and `bout` (Bytes Out / TX) on each active `fwd_<port>` listener.
   - **Tunnel Interfaces**: Directly reads `/proc/net/dev` kernel virtual filesystem for point-to-point and overlay interfaces (`gre*`, `ipip*`, `awg*`, `ftcp*`).

2. **Monotonic Delta Engine**:
   - `TrafficCollector` samples raw counters periodically (~30s).
   - Computes non-negative monotonic deltas (`curr - prev`) for each entity.
   - Immune to counter resets: when a service reloads and counters drop below the previous reading, the new value is captured cleanly without negative spikes or double-counting.

3. **Pre-Aggregated Hourly SQLite Rollups**:
   - Stored in `/etc/xforwarder/metrics.db` in WAL mode under `traffic_hourly (entity_type, entity_id, period_start, rx_bytes, tx_bytes, total_bytes)`.
   - Analytical queries group by `strftime` for instant rendering across 24h (hourly buckets), 7d/30d (daily buckets), and 12m (monthly buckets).
   - Automatic 90-day retention pruning prevents disk storage bloat.

4. **Baseline Offset Reset Model (Billing Cycles)**:
   - Resetting a billing cycle stores current accumulated usage in `traffic_resets` as baseline offsets (`offset_rx`, `offset_tx`).
   - Current cycle usage = `max(0, current_total - offset)`.
   - The current billing cycle drops instantly to 0 while historical analytical time-series charts remain intact.
   - An optional `wipe_history=true` mode permanently purges hourly rows when full cleanup is desired.
   - Global `all:all` resets record individual baseline offsets for every distinct entity, ensuring subsequent single-entity queries remain accurate.

5. **Security & Input Validation**:
   - `/api/traffic/reset` strictly validates `entity_type` against whitelisted values (`all`, `port`, `tunnel`), port numbers (`1..65535`), and interface names (`^[a-zA-Z0-9_.-]{1,32}$`).
   - All endpoints enforce CSRF origin verification, session auth, and OWASP defense-in-depth headers.

6. **Nova Glassmorphism UI**:
   - Dedicated modal with target selector, period pills (24h, 7d, 30d, 12m), KPI cards with billing cycle reset, stacked visual bar charts with tooltips, and reverse-chronological data tables.
   - Adheres strictly to borderless hover transitions and zero-transform guidelines.

## Verification & Impact
- Full unit test suite expanded from 162 to 183 tests (`tests/test_traffic.py`).
- 100% pass rate in ~5.9s without third-party pip dependencies.
- Zero impact on core forwarding throughput or failover speed.

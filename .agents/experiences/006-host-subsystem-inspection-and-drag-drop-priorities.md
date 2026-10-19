# Experience 006: Host Subsystem Inspection and Drag-Drop Priority Reordering

**Date:** 2026-10-19  
**Category:** networking-and-ui  
**Status:** Active  

---

## 1. Context & Motivation
On intermediate relay servers (e.g. Iran VPS), operators deploy various forwarding subsystems (HAProxy, NFTables, Nginx). Previously:
1. Operators had no visual feedback in the Web UI on whether the required system binaries (HAProxy, NFTables, Nginx) were installed, running, or missing.
2. In hot paths, mutating a rule (or toggling manual test overrides) relied purely on background polling loops, causing a noticeable delay before changes took effect in firewall and proxy layers.
3. Changing priority ordering required tedious manual text editing in modals instead of rapid drag-and-drop reordering.

## 2. Core Dynamics & Low-Resource Relay Safeguards
1. **Subprocess Overhead on Low-RAM Relay VPS:** Spawning `nft`, `systemctl`, `haproxy -v`, and `nginx -v` on every API polling cycle would spike CPU overhead and deplete system file descriptors.
   - *Solution:* Implemented thread-safe in-memory caching (`_SERVICES_CACHE`) with a 6.0-second TTL in `core/web_server.py`.
2. **Dynamic Rule Synchronization with Retry:**
   - In `core/engine.py`, `sync_system_rules(max_retries=2, delay_between_retries=0.5)` automatically triggers pre-validated atomic reload of NFTables ruleset, HAProxy config, and Nginx stream configuration.
   - All mutating endpoints (`POST /api/rule`, `POST /api/override`, `POST /api/batch-override`, `POST /api/sync`, `DELETE /api/rule/<id>`) execute `sync_system_rules` and return explicit error diagnostics (`sync_ok`, `sync_errors`).
3. **HTML5 Drag-and-Drop Priority Reordering:**
   - On the web dashboard, users can drag any path card using the drag handle (`.drag-handle`) to reorder priorities on the fly.
   - The UI performs an immediate optimistic re-render, normalizes priorities sequentially (`P1, P2, P3...`), and sends an atomic POST to `/api/rule`.

## 3. Architecture & Solution Implemented
1. **Host Services Status Inspector (`get_services_status`):**
   - Inspects NFTables (installed, kernel ready, or table active), HAProxy (version, active state via systemctl/pgrep), and Nginx (version, active state).
   - Exposes `/api/services/status` and integrates directly into the main status payload.
2. **Top Relay Engines Health Bar & Missing Packages Banner:**
   - `servicesStatusBar` displays live pills with distinct glowing dots (`.dot-emerald`, `.dot-amber`, `.dot-rose`).
   - If any core package is missing, `servicesWarningBanner` alerts the administrator with a one-click copy hint to run `xfwd` in the terminal.
3. **Cross-Distro Dependency Management (`xforwarder.sh`):**
   - Automatically supports `apt-get`, `dnf`, `yum`, `pacman`, and `apk`.
   - Option 10 in interactive CLI menu ("Check & Install System Dependencies") and CLI subcommand `xfwd check-deps` / `xfwd deps`.
4. **Accurate Probe Latency Semantics:**
   - Destination probes return `latency_ms: None` when down (preventing false 0.0ms readings), and the UI renders latency badges exclusively for healthy endpoints.

## 4. Invariants & Rules for AI Agents
- **Rule 1 (Bounded Inspection Overhead):** Never call system binaries (`nft`, `haproxy`, `nginx`, `systemctl`) without leveraging `_SERVICES_CACHE` or bounded timeouts.
- **Rule 2 (Mandatory Dynamic Sync):** Any API or CLI modification that alters forwarding rules MUST invoke `sync_system_rules` to ensure firewall tables and proxy configs stay synchronized immediately.
- **Rule 3 (Sequential Priority Normalization):** When reordering paths (via drag-and-drop or API), destinations MUST always be assigned contiguous 1-based priorities (`P1, P2, ...`).

## 5. Verification & Testing
- Run `python -m unittest tests/test_ui_and_api_edge_cases.py` to verify services inspection API structure, DOM bindings, and error modals.
- Run `python -m unittest tests/test_engine_probes.py` to verify route isolation and latency reporting.
- Run `python .agents/scripts/verify-all.py` for comprehensive regression testing.

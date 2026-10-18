# Experience 002: Atomic File Persistence and Tmp Renaming

**Date:** 2026-10-18  
**Category:** Reliability & Concurrency  
**Status:** Active  

---

## 1. Context & Motivation
XForwarder runs 24/7 on Linux servers subject to sudden restarts, power loss, or service terminations. Direct file writing to `/etc/xforwarder/config.json` or `/run/xforwarder/state.json` can cause truncated or zero-byte files, permanently corrupting configuration or runtime metrics.

## 2. Root Cause / Core Dynamics
- Standard `open(path, "w")` truncates the file immediately upon opening.
- If the Python process crashes or gets killed (`kill -9`, SIGTERM, kernel OOM) during `json.dump()`, the configuration is left empty or invalid JSON.
- Consecutive reads by the web server or failover daemon fail with `json.decoder.JSONDecodeError`.

## 3. Architecture & Solution Implemented
All state and configuration persistence operations must follow the atomic rename pattern:
```python
tmp_path = f"{target_path}.tmp.{os.getpid()}"
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
os.replace(tmp_path, target_path)
```
On POSIX filesystems, `os.replace` (underlying `rename(2)` syscall) is guaranteed to be atomic. The existing destination file remains completely intact and valid until the moment the replacement completes.

## 4. Invariants & Rules for AI Agents
- Never use direct `open(target_path, "w")` when saving `config.json` or `state.json`.
- Always generate unique temporary paths using the current process ID (`os.getpid()`).
- Always synchronize access across threads with `threading.Lock()` when modifying `self.config`.

## 5. Verification & Testing
Validate that `.agents/scripts/check-anti-patterns.py` reports zero violations and verify that `config.json` contains valid JSON after concurrent web API updates.

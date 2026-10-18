---
trigger: always_on
description: Coding standards, lightweight constraints, and thread-safety rules for XForwarder Python daemons.
---

# Python Core Standards (`core/engine.py` & `core/web_server.py`)

## 1. Native Python 3 Standard Library Only
- **Zero Third-Party Pip Dependencies**: Do not introduce dependencies like Flask, FastAPI, Requests, Uvicorn, or Pydantic. Use only the standard library (`http.server`, `socket`, `threading`, `subprocess`, `json`, `hashlib`, `time`, `signal`).
- **Resource Footprint**: Keep idle RAM consumption below 15MB and CPU overhead under 1%.
- **Compatibility**: Code must run natively on Debian 11/12 and Ubuntu 20.04/22.04/24.04 with system Python 3.

## 2. Thread Safety & Atomic File Operations
- **Locking**: Always synchronize concurrent modifications to `self.config` or shared runtime states using `threading.Lock()`.
- **Atomic Persistence**:
  ```python
  tmp_path = f"{target_path}.tmp.{os.getpid()}"
  with open(tmp_path, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
  os.replace(tmp_path, target_path)
  ```
  This guarantees that sudden process termination or power loss cannot corrupt `config.json` or `state.json`.

## 3. Network Probing Standards
- **Low-Overhead Probes**: Destination health checking (`check_destination`) must use non-blocking or bounded-timeout sockets (`socket.create_connection(..., timeout=2.0)`).
- **Latency Measurement**: Accurate round-trip latency (`latency_ms`) must be recorded using `time.perf_counter()`.
- **Failure Resilience**: Connection errors (`socket.timeout`, `ConnectionRefusedError`, `OSError`) must be caught cleanly without raising unhandled exceptions into `run_loop()`.

## 4. Signal & Process Lifecycle
- Handle `SIGTERM` and `SIGINT` cleanly via signal handlers.
- Ensure all worker threads are daemonic (`daemon=True`) or clean up gracefully before termination.

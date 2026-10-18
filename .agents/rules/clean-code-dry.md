---
name: clean-code-dry
description: "Enforces DRY zero-duplication, atomic helper methods, and clean architecture standards in XForwarder."
always_on: false
trigger: model_decision
---

# Clean Code & DRY (Don't Repeat Yourself) Rule

All AI agents operating within this repository MUST adhere strictly to clean code principles, modularity, and the **Zero-Duplication (DRY)** policy.

---

## 1. Absolute Prohibition of Duplicated Logic
1. **No Copy-Pasted Code Blocks:**
   - Never copy-paste repeated parsing, socket probing, formatting, or config reading across methods or scripts.
   - Example: Resolving active config paths or formatting destination strings must use dedicated canonical helpers.
2. **No Ad-Hoc Inline Hacks:**
   - Do not write verbose, convoluted inline logic where a clean, declarative single-line method call should be used.
   - Any recurring domain concept (e.g. socket ping, destination health parsing, latency formatting) MUST have a dedicated helper.

---

## 2. Mandatory Helper Centralization
1. **Shared Daemon Helpers (`core/engine.py` & `core/web_server.py`):**
   - Keep shared logic cleanly abstracted in dedicated functions (`_resolve_config_path`, `load_config`, `save_config`, `hash_password`).
2. **Single Source of Truth:**
   - Persistent configuration resides in `/etc/xforwarder/config.json`.
   - Ephemeral runtime state resides in `/run/xforwarder/state.json`.

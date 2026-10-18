---
name: session-handoff
description: "Guidelines for tracking and resuming active task context and milestones via .agents/session-state.json."
always_on: false
trigger: model_decision
---

# Session State & Task Handoff Rule (XForwarder)

To prevent loss of context across extended conversations, model resets, or multi-phase tasks, AI agents operating in this repository SHOULD utilize the structured session state mechanism.

---

## 1. Structure & Storage

The active session state resides in [`.agents/session-state.json`](../session-state.json) and tracks:
- `active_task`: Current high-level user objective.
- `phase`: Current workflow phase (`Clarification`, `Implementation`, `Verification`, `Completed`).
- `completed_milestones`: List of verified, completed steps in the ongoing task.
- `next_steps`: Planned upcoming steps to prevent forgetting unfinished work.
- `notes`: High-level context and architectural decisions.

---

## 2. Managing Session State via CLI

Use the built-in helper script to interact with the session state:

```bash
# View current state snapshot
python .agents/scripts/session-state.py --show

# Update task and phase
python .agents/scripts/session-state.py --task="Feature Name" --phase="Implementation"

# Record a completed milestone
python .agents/scripts/session-state.py --milestone="Implemented UDP stream proxy in engine.py"

# Register an upcoming step
python .agents/scripts/session-state.py --next="Verify with verify-all pipeline"
```

---
name: experience-logging
description: "Guidelines and format requirements for logging architectural decisions and lessons learned in .agents/experiences/."
always_on: false
trigger: model_decision
---

# Architectural Experience Logging Rule (XForwarder)

To preserve lessons learned, avoid repeating past bugs, and build an institutional codebase memory, AI agents MUST log notable architectural decisions and edge-case fixes in [`.agents/experiences/`](../experiences/README.md).

---

## 1. When to Log an Experience
Log an experience whenever a task involves:
1. **Routing Invariants:** Changes to the Zero-Collision forwarding rule, failover state machines, or socket listeners.
2. **Kernel / Firewall Dynamics:** Lessons regarding NFTables chains, MASQUERADE masks, or HAProxy reload behavior.
3. **Subtle Bug Fixes:** Resolving tricky socket timeouts, thread race conditions, or file persistence edge cases.
4. **Security & Session Hardening:** Changes to session token TTL, cookie attributes, or API guards.

---

## 2. Standard Logging Protocol
Use the automated helper script to scaffold a new experience:

```bash
python .agents/scripts/log-experience.py "Short Title of Experience" Category
```

Each log follows this standard structure:
- **1. Context & Motivation:** The requirement or incident that prompted the decision.
- **2. Root Cause / Core Dynamics:** The underlying technical mechanism or conflict.
- **3. Architecture & Solution Implemented:** The pattern, algorithm, or configuration used.
- **4. Invariants & Rules for AI Agents:** Non-negotiable constraints to prevent regressions.
- **5. Verification & Testing:** Step-by-step commands to verify the invariant.

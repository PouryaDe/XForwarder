---
name: mandatory-checklist
description: "Universal task completion and verification checklist; execute proactively before finishing any coding task in XForwarder."
always_on: false
trigger: model_decision
---

# Mandatory Task Completion & Verification Workflow (XForwarder)

Universal protocol executed proactively at the conclusion of every coding task in this repository.

---

## 0. Requirements Clarification & Blast Radius
- **Zero-Assumption Clarification:** For new features, routing changes, or UI/UX modifications, follow `reverse-prompting.md`. Pause, ask one clear question with options and a recommended approach before coding.
- **Blast Radius Analysis:** Map components via Graphify (`graphify query`, `get_node`) before modifying shared components (`core/engine.py`, `core/web_server.py`, `xforwarder.sh`).

## 1. Code Verification & Syntax
- **Syntax Check:** Run `python .agents/scripts/syntax-check.py` or `python -m py_compile <file>`.
- **Anti-Pattern Audit:** Run `python .agents/scripts/check-anti-patterns.py`. Zero third-party pip dependencies, zero global firewall flushes.
- **Clean Code & DRY:** Extract repeated socket/IP formatting logic into clean, reusable methods.
- **Security Check:** Validate that `/api/*` endpoints require authentication, password hashes are SHA-256, and inputs are sanitized.

## 2. Automated Verification Pipeline
- Run `python .agents/scripts/verify-all.py`.
- Ensure all automated checks pass: Python syntax, anti-pattern scan, JSON validation, and clean Git state.

## 3. Requirement Convergence
- **Convergence Audit:** Verify that 100% of user requirements, edge cases, and error states are handled. Never leave unverified gaps.

## 4. Documentation Synchronization
- **AGENTS.md & README.md:** Synchronize architectural docs if configuration schemas, command-line interfaces, or systemd services were altered.

## 5. UI Consistency (If Web Modified)
- Comply with `ui-design-consistency.md`: Modern dark-mode glassmorphism, Inter and JetBrains Mono typography, debounce on live polling, and pure Vanilla JavaScript without build tools.

## 6. Experience Logging
- If a new architectural pattern, bug fix, or edge case was resolved, document it in `.agents/experiences/` using `python .agents/scripts/log-experience.py "<Title>" <Category>` and update `README.md`.

## 7. Safe Git Operations & Token Efficiency
- **Compact CLI:** Run terse commands to avoid flooding context (`git status --short`, `git diff --stat`).
- **NEVER Auto-Push:** Do NOT run `git push` automatically. Pushing is strictly under user control.

## 8. Zero Polling & Reactive Wakeup
- **NO Timers/Polling:** Never use `schedule` timers or loop over `manage_task(status)`. Await reactive wakeup automatically.

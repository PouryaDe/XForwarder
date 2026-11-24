---
name: versioning
description: "Post-change SemVer 2.0.0 versioning rule: evaluate whether runtime/UI/CLI changes require a PATCH, MINOR, or MAJOR version bump and synchronize all version targets."
always_on: false
trigger: model_decision
---

# Versioning & Release Synchronization Rule (XForwarder)

After completing any code modification in `core/`, `web/`, or `xforwarder.sh`, evaluate whether a version bump is warranted before concluding the task.

## When to Bump
- **Bump `PATCH` (`X.Y.Z+1`)**: Bug fixes, security/XSS/auth patches, validation fixes, or minor UI/i18n corrections in `core/`, `web/`, or `xforwarder.sh`.
- **Bump `MINOR` (`X.Y+1.0`)**: New features, new forwarding/failover modes, new API endpoints, or substantial backwards-compatible enhancements.
- **Bump `MAJOR` (`X+1.0.0`)**: Breaking config schema, API, or CLI changes.
- **Do NOT Bump**: Edits limited exclusively to `.agents/`, `README.md`/docs, or `tests/` without runtime/UI/CLI changes.

## Execution
When a bump is warranted, load and follow [`skills/release-version/SKILL.md`](../skills/release-version/SKILL.md) to update all synchronized version targets (`core/service_manager.py`, `xforwarder.sh`, `web/index.html`, `README.md`, and `tests/test_ui_and_api_edge_cases.py`) and run `python .agents/scripts/verify-all.py`.

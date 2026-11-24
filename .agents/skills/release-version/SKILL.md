---
name: release-version
description: "SemVer 2.0.0 release runbook: scope evaluation and synchronized version bumping across core/service_manager.py, xforwarder.sh, web/index.html, README.md, and tests."
---

# Semantic Versioning (SemVer 2.0.0) & Release Protocol

XForwarder strictly adheres to **Semantic Versioning 2.0.0** (`X.Y.Z` / `vX.Y.Z`). This skill governs change scope evaluation and synchronized version bumping across the repository.

---

## 1. SemVer Scope Evaluation Rubric

Evaluate the cumulative scope of changes since the last version bump:

| Version Level | Scope & Triggers | Action |
|---|---|---|
| **MAJOR (`X.0.0`)** | Breaking config schema or API contract changes, incompatible CLI/systemd service changes, or removing backward-compatible fallbacks. | Increment `MAJOR`, reset `MINOR` & `PATCH` to `0`. |
| **MINOR (`X.Y.0`)** | Substantial new features, new forwarding/failover methods, new API endpoints or dashboard modules, or high cumulative volume of backwards-compatible additions. | Increment `MINOR`, reset `PATCH` to `0`. |
| **PATCH (`X.Y.Z`)** | Isolated bug fixes, security patches, input sanitization, UI/i18n polish, or minor defensive guards. **Never use for new features.** | Increment `PATCH`. |

> [!IMPORTANT]
> **Skip Bump For Non-Runtime Changes:** Documentation-only (`README.md`, `docs/`), `.agents/`-only, or test-only edits do **not** require a version bump.

---

## 2. Release Execution Workflow

Execute systematically whenever a code change warrants a version bump:

### Step 1: Audit Scope
1. Review `git diff` / `git log` since the previous version commit.
2. Determine whether the change is **MAJOR**, **MINOR**, or **PATCH** using the rubric above.

### Step 2: Bump All Synchronized Version Targets
XForwarder enforces strict version alignment across all runtime, CLI, UI, and documentation surfaces. Update **every** target below to the exact same `X.Y.Z`:

1. **`core/service_manager.py`**:
   ```python
   APP_VERSION = "X.Y.Z"
   ```
2. **`xforwarder.sh`**:
   ```bash
   SCRIPT_VERSION="X.Y.Z"
   ```
3. **`web/index.html`**:
   - `#brandVersionBadge` -> `vX.Y.Z`
   - `#valInstalledVersion` -> `vX.Y.Z`
4. **`README.md`**:
   - Version badge -> `Version-X.Y.Z-success.svg`
5. **`tests/test_ui_and_api_edge_cases.py`**:
   - Update any version-alignment test assertions that check `APP_VERSION`, `SCRIPT_VERSION`, `#brandVersionBadge`, and `#valInstalledVersion`.

### Step 3: Verification Pipeline
```bash
python .agents/scripts/verify-all.py
```
Verify all checks pass (Python syntax, anti-patterns, ES imports, unit tests, JSON validation).

### Step 4: Local Git Commit
```bash
git add core/service_manager.py xforwarder.sh web/index.html README.md tests/test_ui_and_api_edge_cases.py
git commit -m "release: bump version to vX.Y.Z"
```
> [!CAUTION]
> Never run `git push` automatically unless the user explicitly instructs you to push.

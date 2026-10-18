---
name: large-files-handling
description: "Safety rules and surgical chunk edits for inspecting and modifying large files without context bloat."
always_on: false
trigger: model_decision
---

# Large Files Inspection & Surgical Editing Rule

When reading or modifying larger files (`core/engine.py`, `core/web_server.py`, `web/app.js`, `xforwarder.sh`), follow these safety constraints:

---

## 1. Targeted Inspection (Knowledge Graph First)
- **Prioritize Knowledge Graph Discovery:** For functions, classes, or methods, ALWAYS use Graphify (`graphify query "<name>"`) to pinpoint the exact definition and line number (`loc=Lxx`), then view only that small sliced range.
- **Do NOT view entire files at once:** Viewing huge files wastes context tokens and degrades attention.
- **Use Small Slices:** When viewing file contents directly, always specify `StartLine` and `EndLine` to read only the 20-50 lines surrounding the target area.

---

## 2. Surgical Edits (Zero Full-File Overwrite)
- **Never perform full file replacements on active code:** Overwriting large daemon files risks truncating unviewed sections and introducing regressions.
- **Use Chunk Replacement:** Always use `replace_file_content` targeting small, exact blocks of code.
- **Match Exact Indentation:** Verify exact whitespace and indentation of surrounding lines to ensure unique chunk matching.

---

## 3. Immediate Syntax Verification
- Immediately after editing any Python file, verify syntax using `python .agents/scripts/syntax-check.py` or `python -m py_compile <file>`.

#!/usr/bin/env python3
"""
Anti-Pattern and Architectural Violation Scanner for XForwarder
Enforces lightweight constraints, native Python standard library usage, and zero-collision safety.
"""

import sys
import os
import re
from typing import List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

# Forbidden import patterns in core/
FORBIDDEN_IMPORTS = [
    r"\bimport\s+(requests|flask|fastapi|uvicorn|httpx|aiohttp|pydantic|sqlalchemy|tornado)\b",
    r"\bfrom\s+(requests|flask|fastapi|uvicorn|httpx|aiohttp|pydantic|sqlalchemy|tornado)\s+import\b",
]

# Forbidden shell or kernel operations
FORBIDDEN_PATTERNS = [
    (r"nft\s+flush\s+ruleset", "CRITICAL: 'nft flush ruleset' wipes system tables. Only isolate table ip xfwd_orchestrator!"),
    (r"iptables\s+-F", "CRITICAL: 'iptables -F' wipes system firewall tables!"),
]


def check_file(filepath: str) -> List[Tuple[int, str]]:
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return [(0, f"Failed to read file: {e}")]

    is_core_py = filepath.replace("\\", "/").endswith(".py") and "/core/" in filepath.replace("\\", "/")

    for idx, line in enumerate(lines, 1):
        # Check forbidden imports in core/
        if is_core_py:
            for pat in FORBIDDEN_IMPORTS:
                if re.search(pat, line):
                    violations.append((idx, f"Forbidden third-party pip import: '{line.strip()}'. Use standard library only!"))

        # Check dangerous kernel flushes
        for pat, msg in FORBIDDEN_PATTERNS:
            if re.search(pat, line, re.IGNORECASE):
                violations.append((idx, msg))

    return violations


def main():
    print("=" * 65)
    print("  XForwarder Anti-Pattern & Architectural Compliance Check")
    print("=" * 65)

    all_violations = []

    scan_dirs = ["core", "web", "systemd"]
    for s_dir in scan_dirs:
        full_dir = os.path.join(REPO_ROOT, s_dir)
        if not os.path.exists(full_dir):
            continue
        for root, _, files in os.walk(full_dir):
            for f in files:
                if f.endswith((".py", ".sh", ".js")):
                    f_path = os.path.join(root, f)
                    violations = check_file(f_path)
                    for line_num, msg in violations:
                        rel = os.path.relpath(f_path, REPO_ROOT)
                        all_violations.append(f"{rel}:{line_num} -> {msg}")

    # Check root shell scripts
    for f in ["xforwarder.sh"]:
        f_path = os.path.join(REPO_ROOT, f)
        if os.path.exists(f_path):
            violations = check_file(f_path)
            for line_num, msg in violations:
                all_violations.append(f"{f}:{line_num} -> {msg}")

    if all_violations:
        print("\n[ERROR] Anti-pattern violations found:\n", file=sys.stderr)
        for v in all_violations:
            print(f"  * {v}", file=sys.stderr)
        print("\n" + "=" * 65, file=sys.stderr)
        sys.exit(1)
    else:
        print("[OK] Zero anti-pattern violations found across core daemons and scripts.")
        print("=" * 65 + "\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

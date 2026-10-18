#!/usr/bin/env python3
"""
Antigravity Lifecycle Hook for Automatic Python Syntax Checking
Handles PreInvocation (immediate feedback) and Stop (blocking exit if syntax errors exist).
"""

import sys
import os
import subprocess
import py_compile
from typing import List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def get_modified_py_files(repo_root: str) -> List[str]:
    try:
        res = subprocess.run(
            ["git", "-C", repo_root, "status", "--porcelain", "-uall"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        files = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                status, rel_path = parts
                if status == "D":
                    continue
                if rel_path.endswith(".py"):
                    full_path = os.path.normpath(os.path.join(repo_root, rel_path))
                    if os.path.exists(full_path):
                        files.append(full_path)
        return files
    except Exception:
        # Fallback: scan core/ directory directly
        core_dir = os.path.join(repo_root, "core")
        if os.path.exists(core_dir):
            return [os.path.join(core_dir, f) for f in os.listdir(core_dir) if f.endswith(".py")]
        return []


def check_syntax(files: List[str]) -> List[str]:
    errors = []
    for f in files:
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{f}: {e.msg}")
        except Exception as e:
            errors.append(f"{f}: {str(e)}")
    return errors


def main():
    is_stop_check = "--stop-check" in sys.argv
    is_pre_check = "--pre-check" in sys.argv

    files = get_modified_py_files(REPO_ROOT)
    if not files:
        if not is_pre_check:
            print("[OK] No modified Python files to verify.")
        sys.exit(0)

    errors = check_syntax(files)

    if errors:
        print("\n=======================================================", file=sys.stderr)
        print("  [ERROR] Python Syntax Errors Detected!", file=sys.stderr)
        print("=======================================================", file=sys.stderr)
        for err in errors:
            print(f"  * {err}", file=sys.stderr)
        print("=======================================================\n", file=sys.stderr)
        if is_stop_check:
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        if not is_pre_check:
            print(f"[OK] Python syntax verified cleanly across {len(files)} file(s).")
        sys.exit(0)


if __name__ == "__main__":
    main()

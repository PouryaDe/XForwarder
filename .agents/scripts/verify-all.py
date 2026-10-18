#!/usr/bin/env python3
"""
Pre-Commit & Task Completion Verification Pipeline for XForwarder
Runs syntax compilation, anti-pattern checks, JSON schema validation, and git status.
"""

import sys
import os
import subprocess
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def run_step(step_name: str, cmd: list) -> bool:
    print(f"\n[RUNNING] {step_name}...")
    res = subprocess.run(cmd, cwd=REPO_ROOT)
    if res.returncode == 0:
        print(f"[PASSED]  {step_name}")
        return True
    else:
        print(f"[FAILED]  {step_name} (exit code: {res.returncode})", file=sys.stderr)
        return False


def validate_json_files() -> bool:
    print("\n[RUNNING] Validating JSON files...")
    json_targets = [
        os.path.join(REPO_ROOT, "config", "config.json.example"),
        os.path.join(REPO_ROOT, ".agents", "mcp_config.json"),
        os.path.join(REPO_ROOT, ".agents", "hooks.json"),
        os.path.join(REPO_ROOT, ".agents", "session-state.json"),
    ]
    all_ok = True
    for j_path in json_targets:
        if os.path.exists(j_path):
            try:
                with open(j_path, "r", encoding="utf-8") as f:
                    json.load(f)
                print(f"  [OK] Valid JSON: {os.path.relpath(j_path, REPO_ROOT)}")
            except Exception as e:
                print(f"  [ERROR] Invalid JSON in {os.path.relpath(j_path, REPO_ROOT)}: {e}", file=sys.stderr)
                all_ok = False
    return all_ok


def show_git_status():
    print("\n" + "=" * 65)
    print("  Git Workspace Status")
    print("=" * 65)
    try:
        res = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, stdout=subprocess.PIPE, text=True)
        lines = res.stdout.strip().splitlines()
        if lines:
            for l in lines:
                print(f"  {l}")
        else:
            print("  (Working tree clean)")
    except Exception as e:
        print(f"  Error reading git status: {e}")
    print("=" * 65)


def main():
    print("\n" + "#" * 65)
    print("  XForwarder Universal Verification Pipeline")
    print("#" * 65)

    success = True

    # Step 1: Syntax compilation
    if not run_step("Python Syntax Verification", [sys.executable, os.path.join(SCRIPT_DIR, "syntax-check.py")]):
        success = False

    # Step 2: Anti-Pattern Verification
    if not run_step("Anti-Pattern & Architectural Rules", [sys.executable, os.path.join(SCRIPT_DIR, "check-anti-patterns.py")]):
        success = False

    # Step 3: Unit Tests & Regression Verification
    if os.path.isdir(os.path.join(REPO_ROOT, "tests")):
        if not run_step("Unit Tests & Regression Verification", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]):
            success = False

    # Step 4: JSON file validation
    if not validate_json_files():
        success = False

    show_git_status()

    if success:
        print("\n" + "=" * 65)
        print("  [ALL CHECKS PASSED] Workspace is healthy and ready to commit.")
        print("=" * 65 + "\n")
        sys.exit(0)
    else:
        print("\n" + "=" * 65, file=sys.stderr)
        print("  [VERIFICATION FAILED] Please resolve the issues above before finishing.", file=sys.stderr)
        print("=" * 65 + "\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

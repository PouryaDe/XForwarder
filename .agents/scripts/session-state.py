#!/usr/bin/env python3
"""
CLI Manager for .agents/session-state.json
Provides structured task context, milestone tracking, and seamless session handoff.
"""

import sys
import os
import json
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "session-state.json")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "active_task": "None",
        "active_spec": None,
        "phase": "Clarification",
        "completed_milestones": [],
        "next_steps": [],
        "notes": ""
    }


def save_state(state: dict) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp_path = f"{STATE_FILE}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, STATE_FILE)


def show_state(state: dict) -> None:
    print("\n" + "=" * 65)
    print("  XForwarder Agent Session State")
    print("=" * 65)
    print(f"  Active Task:  {state.get('active_task', 'None')}")
    print(f"  Phase:        {state.get('phase', 'Clarification')}")
    print(f"  Last Updated: {state.get('last_updated', 'Unknown')}")
    print("-" * 65)
    print("  Completed Milestones:")
    milestones = state.get("completed_milestones", [])
    if milestones:
        for idx, m in enumerate(milestones, 1):
            print(f"    [OK] {idx}. {m}")
    else:
        print("    (No milestones completed yet)")
    print("-" * 65)
    print("  Next Steps:")
    next_steps = state.get("next_steps", [])
    if next_steps:
        for idx, ns in enumerate(next_steps, 1):
            print(f"    -> {idx}. {ns}")
    else:
        print("    (No next steps defined)")
    if state.get("notes"):
        print("-" * 65)
        print(f"  Notes: {state['notes']}")
    print("=" * 65 + "\n")


def main():
    state = load_state()
    args = sys.argv[1:]

    if not args or "--show" in args:
        show_state(state)
        return

    modified = False

    for arg in args:
        if arg.startswith("--task="):
            state["active_task"] = arg.split("=", 1)[1].strip()
            modified = True
        elif arg.startswith("--phase="):
            state["phase"] = arg.split("=", 1)[1].strip()
            modified = True
        elif arg.startswith("--milestone="):
            m = arg.split("=", 1)[1].strip()
            if m and m not in state.setdefault("completed_milestones", []):
                state["completed_milestones"].append(m)
                modified = True
        elif arg.startswith("--next="):
            ns = arg.split("=", 1)[1].strip()
            if ns:
                state.setdefault("next_steps", []).append(ns)
                modified = True
        elif arg.startswith("--notes="):
            state["notes"] = arg.split("=", 1)[1].strip()
            modified = True
        elif arg == "--clear-milestones":
            state["completed_milestones"] = []
            modified = True
        elif arg == "--clear-next":
            state["next_steps"] = []
            modified = True

    if modified:
        save_state(state)
        print("[OK] Session state updated successfully.")
        show_state(state)


if __name__ == "__main__":
    main()

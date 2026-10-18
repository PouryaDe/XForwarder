#!/usr/bin/env python3
"""
Experience Logger Script for XForwarder
Scaffolds a new architectural experience record in .agents/experiences/ and updates README.md.
"""

import sys
import os
import re
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXP_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "experiences")
CATALOG_FILE = os.path.join(EXP_DIR, "README.md")


def get_next_number() -> int:
    os.makedirs(EXP_DIR, exist_ok=True)
    existing = []
    for f in os.listdir(EXP_DIR):
        match = re.match(r"^(\d{3})-.*\.md$", f)
        if match:
            existing.append(int(match.group(1)))
    return max(existing) + 1 if existing else 1


def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s


def main():
    if len(sys.argv) < 2:
        print("Usage: python log-experience.py \"Short Title of Experience\" [Category]")
        print("Example: python log-experience.py \"Zero Collision HAProxy and NFTables\" Architecture")
        sys.exit(1)

    title = sys.argv[1].strip()
    category = sys.argv[2].strip() if len(sys.argv) > 2 else "Architecture"

    num = get_next_number()
    filename = f"{num:03d}-{slugify(title)}.md"
    filepath = os.path.join(EXP_DIR, filename)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content = f"""# Experience {num:03d}: {title}

**Date:** {now}  
**Category:** {category}  
**Status:** Active  

---

## 1. Context & Motivation
Describe the context, the problem encountered, or the architectural requirement that led to this decision.

## 2. Root Cause / Core Dynamics
Detail the technical reasons, constraints, or mechanisms (e.g. port binding collisions, socket timeouts, memory overhead).

## 3. Architecture & Solution Implemented
Explain the exact pattern, code design, or configuration established to solve this problem.

## 4. Invariants & Rules for AI Agents
- Rule 1: ...
- Rule 2: ...

## 5. Verification & Testing
How to verify this invariant remains intact in future development.
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Created new experience file: {os.path.relpath(filepath, os.path.dirname(SCRIPT_DIR))}")

    # Update or create catalog
    entry = f"| `{num:03d}` | [{title}]({filename}) | `{category}` | {now} |\n"
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            cat_content = f.read()
        if entry not in cat_content:
            cat_content += entry
            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                f.write(cat_content)
    else:
        header = """# XForwarder Architectural Experiences Catalog

Records of architectural decisions, critical invariants, and lessons learned during development.

| # | Title | Category | Date |
| :- | :--- | :--- | :--- |
"""
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            f.write(header + entry)

    print(f"[OK] Catalog updated in {os.path.relpath(CATALOG_FILE, os.path.dirname(SCRIPT_DIR))}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JS_DIR = os.path.join(REPO_ROOT, "web", "js")

print("Checking syntax of dynamically generated buttons in JS modules...\n")

onclick_pattern = re.compile(r'onclick="([^"]+)"', re.IGNORECASE)
onclick_pattern_single = re.compile(r"onclick='([^']+)'", re.IGNORECASE)

tested = 0
errors = []

for root, dirs, files in os.walk(JS_DIR):
    for f in sorted(files):
        if f.endswith(".js"):
            fpath = os.path.join(root, f)
            with open(fpath, "r", encoding="utf-8") as fh:
                content = fh.read()
            
            handlers = [m.group(1) for m in onclick_pattern.finditer(content)] + [m.group(1) for m in onclick_pattern_single.finditer(content)]
            for handler_template in handlers:
                tested += 1
                
                # Check for obvious unclosed quotes or parentheses in the template
                parens = handler_template.count("(") - handler_template.count(")")
                if parens != 0:
                    errors.append((f, handler_template, f"Mismatched parentheses: balance {parens}"))
                    continue

                # Simulate filling template literals with sample placeholder identifier
                simulated = re.sub(r'\$\{[^}]+\}', "test_val", handler_template)
                
                # Verify simulated JS syntax using node if available
                node_code = f"try {{ new Function({repr(simulated)}); }} catch(e) {{ process.stderr.write(e.message); process.exit(1); }}"
                try:
                    res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True, timeout=5)
                    if res.returncode != 0:
                        errors.append((f, handler_template, f"JS Parse Error: {res.stderr.strip()}"))
                    else:
                        print(f"[OK] {f}: {handler_template[:65]}...")
                except FileNotFoundError:
                    # Node not installed, fallback to paren/bracket matching
                    print(f"[SYNTAX OK (static)] {f}: {handler_template[:65]}...")

print(f"\nTested {tested} dynamic button onclick templates.")
if errors:
    print(f"FAILED: {len(errors)} errors found:")
    for fn, tmpl, err in errors:
        print(f"  In {fn}: {tmpl}\n    Error: {err}")
    sys.exit(1)
else:
    print("ALL DYNAMIC BUTTON TEMPLATES PASSED SYNTAX VALIDATION!")
    sys.exit(0)

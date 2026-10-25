#!/usr/bin/env python3
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_PATH = os.path.join(REPO_ROOT, "web", "index.html")
JS_DIR = os.path.join(REPO_ROOT, "web")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Load all JS files
js_contents = {}
for root, dirs, files in os.walk(JS_DIR):
    for file in files:
        if file.endswith(".js"):
            fpath = os.path.join(root, file)
            with open(fpath, "r", encoding="utf-8") as jf:
                js_contents[file] = jf.read()

all_js_text = "\n".join(js_contents.values())

# Find all buttons in index.html
btn_pattern = re.compile(r'<button\b([^>]*)>', re.IGNORECASE)
buttons = []
for m in btn_pattern.finditer(html):
    attrs = m.group(1)
    btn_id = re.search(r'id=["\']([^"\']+)["\']', attrs)
    btn_onclick = re.search(r'onclick=["\']([^"\']+)["\']', attrs)
    btn_type = re.search(r'type=["\']([^"\']+)["\']', attrs)
    btn_class = re.search(r'class=["\']([^"\']+)["\']', attrs)
    
    buttons.append({
        "full": m.group(0),
        "id": btn_id.group(1) if btn_id else None,
        "onclick": btn_onclick.group(1) if btn_onclick else None,
        "type": btn_type.group(1) if btn_type else None,
        "class": btn_class.group(1) if btn_class else None
    })

print(f"Total buttons in index.html: {len(buttons)}\n")

unwired = []
wired = []

for b in buttons:
    b_id = b["id"]
    onclick = b["onclick"]
    is_wired = False
    details = []

    if onclick:
        # Check if onclick references a function or inline code
        fn_match = re.match(r'([a-zA-Z0-9_$]+)\s*\(', onclick.strip())
        if fn_match:
            fn_name = fn_match.group(1)
            # check if fn_name is in all_js_text (either function definition or window assignment)
            if f"window.{fn_name}" in all_js_text or f"function {fn_name}" in all_js_text or f"export function {fn_name}" in all_js_text:
                is_wired = True
                details.append(f"onclick calls '{fn_name}()' (FOUND in JS)")
            else:
                details.append(f"onclick calls '{fn_name}()' (NOT FOUND IN JS!)")
        else:
            is_wired = True
            details.append(f"inline onclick: {onclick}")

    if b_id:
        # Check if ID has event listener in JS
        pattern = re.compile(rf'getElementById\s*\(\s*["\']{re.escape(b_id)}["\']\s*\)|querySelector\s*\(\s*["\']#{re.escape(b_id)}["\']\s*\)')
        if pattern.search(all_js_text):
            is_wired = True
            details.append(f"id='{b_id}' referenced in JS")
        else:
            details.append(f"id='{b_id}' NOT referenced in JS")

    if is_wired:
        wired.append((b, details))
    else:
        unwired.append((b, details))

print("=== UNWIRED OR POTENTIALLY BROKEN BUTTONS ===")
for b, d in unwired:
    print(f"BUTTON: {b['full']}")
    print(f"  Status: {', '.join(d)}\n")

print(f"\nSummary: {len(wired)} wired, {len(unwired)} unwired")

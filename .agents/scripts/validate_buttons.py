#!/usr/bin/env python3
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_PATH = os.path.join(REPO_ROOT, "web", "index.html")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Load all JS files
js_dir = os.path.join(REPO_ROOT, "web")
all_js = {}
for root, dirs, files in os.walk(js_dir):
    for f in files:
        if f.endswith(".js"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8") as fh:
                all_js[f] = fh.read()

combined_js = "\n".join(all_js.values())

btn_pattern = re.compile(r'<button\b([^>]*)>', re.IGNORECASE)
buttons = []
for m in btn_pattern.finditer(html):
    attrs = m.group(1)
    btn_id = re.search(r'id=["\']([^"\']+)["\']', attrs)
    btn_onclick = re.search(r'onclick="([^"]+)"', attrs) or re.search(r"onclick='([^']+)'", attrs)
    btn_type = re.search(r'type=["\']([^"\']+)["\']', attrs)
    btn_class = re.search(r'class=["\']([^"\']+)["\']', attrs)
    btn_title = re.search(r'title=["\']([^"\']+)["\']', attrs)
    
    buttons.append({
        "full": m.group(0),
        "id": btn_id.group(1) if btn_id else None,
        "onclick": btn_onclick.group(1) if btn_onclick else None,
        "type": btn_type.group(1) if btn_type else None,
        "class": btn_class.group(1) if btn_class else None,
        "title": btn_title.group(1) if btn_title else None,
    })

print(f"Total <button> elements in index.html: {len(buttons)}\n")

unbound = []
bound = []

for idx, b in enumerate(buttons):
    bid = b["id"]
    onclick = b["onclick"]
    bclass = b["class"] or ""
    
    reasons = []
    is_ok = False
    
    # 1. Check onclick
    if onclick:
        # Check syntax: are brackets matched?
        if onclick.count("(") != onclick.count(")") or onclick.count("{") != onclick.count("}"):
            reasons.append(f"SYNTAX ERROR in onclick: {onclick}")
        else:
            fn_call = re.match(r'([a-zA-Z0-9_$]+)\s*\(', onclick.strip())
            if fn_call:
                fn_name = fn_call.group(1)
                if fn_name in combined_js:
                    is_ok = True
                    reasons.append(f"onclick calls {fn_name}()")
                else:
                    reasons.append(f"onclick calls unknown {fn_name}()")
            else:
                is_ok = True
                reasons.append(f"inline code: {onclick}")

    # 2. Check id listener
    if bid:
        pattern = re.compile(rf'getElementById\s*\(\s*["\']{re.escape(bid)}["\']\s*\)|querySelector\s*\(\s*["\']#{re.escape(bid)}["\']\s*\)')
        if pattern.search(combined_js):
            is_ok = True
            reasons.append(f"id '{bid}' bound in JS")

    # 3. Check class-based listener
    for cls in bclass.split():
        if cls in ["nav-item", "btn-range-tab"]:
            is_ok = True
            reasons.append(f"handled via class '.{cls}'")

    if is_ok:
        bound.append((idx + 1, b, reasons))
    else:
        unbound.append((idx + 1, b, reasons))

print(f"=== BOUND / WORKING BUTTONS: {len(bound)} ===")
for num, b, r in bound:
    print(f"#{num:02d} ID: {str(b['id']):28} | {', '.join(r)}")

print(f"\n=== UNBOUND / POTENTIALLY BROKEN BUTTONS: {len(unbound)} ===")
for num, b, r in unbound:
    print(f"#{num:02d} ID: {str(b['id']):28} | HTML: {b['full']}")

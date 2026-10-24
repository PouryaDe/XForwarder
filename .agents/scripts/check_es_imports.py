import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
web_dir = os.path.join(REPO_ROOT, "web")

js_files = {}
for root, _, files in os.walk(web_dir):
    for f in files:
        if f.endswith(".js"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8") as fh:
                js_files[p] = fh.read()

import_re = re.compile(r'import\s+\{([^}]+)\}\s+from\s+["\']([^"\']+)["\']')
export_re = re.compile(r'export\s+(?:let|const|var|function|async\s+function|class)\s+([a-zA-Z0-9_$]+)')

exports_by_file = {}
for path, content in js_files.items():
    norm_p = os.path.normpath(path)
    exports = set(export_re.findall(content))
    exports_by_file[norm_p] = exports

errors = []
for path, content in js_files.items():
    norm_p = os.path.normpath(path)
    dir_p = os.path.dirname(norm_p)
    for m in import_re.finditer(content):
        raw_symbols = m.group(1).split(",")
        symbols = [s.strip() for s in raw_symbols if s.strip()]
        rel_mod = m.group(2)
        target = os.path.normpath(os.path.join(dir_p, rel_mod))
        if target not in exports_by_file:
            errors.append(f"MISSING MODULE: {rel_mod} imported by {os.path.relpath(path, web_dir)}")
        else:
            avail = exports_by_file[target]
            for s in symbols:
                sym = s.split(" as ")[0].strip()
                if sym not in avail:
                    errors.append(f"MISSING EXPORT: '{sym}' from {os.path.basename(target)} imported by {os.path.relpath(path, web_dir)}")

if errors:
    print(f"Found {len(errors)} import/export issue(s):")
    for err in errors:
        print(f"  - {err}")
    exit(1)
else:
    print("ALL ES MODULE IMPORTS AND EXPORTS ARE 100% VALID!")
    exit(0)

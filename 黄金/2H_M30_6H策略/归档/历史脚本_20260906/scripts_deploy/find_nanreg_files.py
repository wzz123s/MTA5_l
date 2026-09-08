# -*- coding: utf-8 -*-
"""搜索 DAD3B8CC 里所有含 InpNanRegOn 的缓存文件."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

base = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
hits = []
for root, dirs, files in os.walk(base):
    for fn in files:
        if fn.lower().endswith(('.ini', '.set', '.cfg', '.txt', '.json')):
            p = os.path.join(root, fn)
            try:
                for enc in ['utf-16', 'utf-8', 'latin-1']:
                    try:
                        txt = open(p, 'r', encoding=enc).read()
                        break
                    except Exception:
                        continue
                if 'InpNanRegOn' in txt:
                    for line in txt.split('\n'):
                        if 'InpNanRegOn' in line:
                            hits.append((p.replace(base, ''), line.strip()))
                            break
            except Exception:
                pass

print("含 InpNanRegOn 的文件:")
for p, l in hits:
    print("  %s: %s" % (p, l))
print("\n共", len(hits), "处")

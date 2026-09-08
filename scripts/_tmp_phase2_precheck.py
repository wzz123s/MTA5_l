# -*- coding: utf-8 -*-
"""_tmp_phase2_precheck.py — Phase2 移动安全只读预检（2026-09-08）"""
import os, re, io

R = r"F:\use_code\MTA5_l"
G = os.path.join(R, "黄金")

print("== 1) 乖离反转 scripts\\ 现有文件（目标冲突面） ==")
sd = os.path.join(G, "乖离反转策略", "scripts")
if os.path.isdir(sd):
    for f in sorted(os.listdir(sd)):
        p = os.path.join(sd, f)
        print("  ", f + ("/" if os.path.isdir(p) else ""), os.stat(p).st_size if os.path.isfile(p) else "")

print("\n== 2) 乖离反转根 py：__file__ 依赖 / 互 import ==")
root = os.path.join(G, "乖离反转策略")
pys = sorted([f for f in os.listdir(root) if f.endswith(".py")])
for f in pys:
    txt = io.open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
    flags = []
    if re.search(r"__file__", txt): flags.append("USES-__file__")
    m = re.findall(r"^(?:from|import)\s+(backtest[\w]*|diag_[\w]+|fetch_[\w]+|deploy_[\w]+)", txt, re.M)
    m = [x for x in m if x + ".py" in pys]
    if m: flags.append("CROSS-IMPORT:" + ",".join(m))
    sp = re.findall(r"sys\.path\.insert\(\d+,\s*r?['\"]([^'\"]+)['\"]", txt)
    if sp: flags.append("syspath:" + ";".join(sp))
    print(f"  {f:<36} {' | '.join(flags) if flags else '(clean,abs-imports-only)'}")

print("\n== 3) 全树对乖离反转根脚本的【带路径】引用（排除备份/自身/归档） ==")
names = [f for f in pys]
pat = re.compile("|".join(re.escape(n) for n in names))
hits = 0
for dp, dns, fns in os.walk(R):
    dns[:] = [d for d in dns if d not in ("__pycache__", "node_modules", "backup_20260907", "归档", "_archive") and ".git" not in dp]
    for f in fns:
        if not f.endswith((".py", ".md", ".ps1", ".cmd", ".set", ".json")): continue
        p = os.path.join(dp, f)
        if os.path.normcase(p).startswith(os.path.normcase(root)): continue
        try: txt = io.open(p, encoding="utf-8", errors="ignore").read()
        except OSError: continue
        for ln_no, line in enumerate(txt.splitlines(), 1):
            if pat.search(line) and re.search(r"乖离反转策略[\\/]", line):
                print("  ", os.path.relpath(p, R) + f":{ln_no}: " + line.strip()[:110]); hits += 1
print("  带路径引用行数:", hits)

print("\n== 4) H1_M30_H4 根级 md 与目标目录 ==")
h1 = os.path.join(G, "H1_M30_H4策略")
for f in sorted(os.listdir(h1)):
    if f.endswith(".md"): print("   ", f)
print("   目标 说明文档\\ 存在:", os.path.isdir(os.path.join(h1, "说明文档")),
      "| 03_验证结果 存在:", os.path.isdir(os.path.join(h1, "说明文档", "03_验证结果")))

print("\n== 5) 30m2H validation 目录规模与 mtime 分布（归档判定输入） ==")
import datetime, collections
v = os.path.join(G, "30m2H策略", "data", "validation")
dirs = [d for d in os.listdir(v) if os.path.isdir(os.path.join(v, d))]
now = datetime.datetime.now().timestamp()
d14, d90, dold = [], [], []
for d in dirs:
    mt = os.stat(os.path.join(v, d)).st_mtime
    age = (now - mt) / 86400
    (d14 if age <= 14 else (dold if age > 90 else d90)).append(d)
print(f"   总数={len(dirs)}  ≤14天={len(d14)}  14-90天={len(d90)}  >90天={len(dold)}")
print("   ≤14天:", d14)

print("\n== 6) 全树对 validation 子目录名的引用（白名单输入，抽样验证可行） ==")
refpat = re.compile("|".join(re.escape(d) for d in dirs))
refd = set()
for dp, dns, fns in os.walk(R):
    dns[:] = [d for d in dns if d not in ("__pycache__", "node_modules") and ".git" not in dp]
    if os.path.normcase(dp).startswith(os.path.normcase(v)): continue
    for f in fns:
        if not f.endswith((".py", ".md", ".set", ".json", ".ps1", ".ini")): continue
        p = os.path.join(dp, f)
        try: txt = io.open(p, encoding="utf-8", errors="ignore").read()
        except OSError: continue
        for d in dirs:
            if d in txt: refd.add(d)
print("   被引用的 validation 目录数:", len(refd))
for d in sorted(refd): print("    REF", d)

# -*- coding: utf-8 -*-
"""check_project_rules.py — 工程卫生机检（只读扫描，输出违规清单，不改文件）
规则来源：00_项目规则.md R1-R9 + AGENTS.md A 段。用法：python scripts/check_project_rules.py
挂载：手动周检 / git pre-commit / DSH tool-jobs 巡检。退出码 0=无违规 1=有违规。
"""
import os, re, sys, io, csv, datetime

R = r"F:\use_code\MTA5_l"
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".obsidian", ".workbuddy", "observation_dashboard", "ea_alignment_logs", "backup_20260907", "archive"}
VIOL = []
now = datetime.datetime.now()

def age_days(p):
    return (now.timestamp() - os.stat(p).st_mtime) / 86400

# 1) R4：一次性脚本逾期未归档（_tmp_/_fix_/_inspect_/_exp_/_check_ 前缀，位于 scripts 根或工程根，>7天）
ONESHOT = re.compile(r"^(_tmp_|_fix_|_inspect_|_exp_|_check_|_dbg_|_mk_)")
for base in ("", "scripts"):
    p0 = os.path.join(R, base) if base else R
    for f in sorted(os.listdir(p0)):
        p = os.path.join(p0, f)
        if os.path.isfile(p) and ONESHOT.match(f) and f.endswith(".py") and age_days(p) > 7:
            VIOL.append(("R4-oneshot-overdue", os.path.relpath(p, R), f"{age_days(p):.0f}天未归档"))

# 2) R7：现役日期快照化——00_文档中心 根与工程根出现同名前缀多日期文件
for d in (os.path.join(R, "00_文档中心"), R):
    names = [f for f in os.listdir(d) if f.endswith(".md") and os.path.isfile(os.path.join(d, f))]
    groups = {}
    for f in names:
        stem = re.sub(r"_20\d{6}.*\.md$", "", f)
        if stem != f: groups.setdefault(stem, []).append(f)
    for stem, fs in groups.items():
        if len(fs) > 1:
            VIOL.append(("R7-dated-coexist", stem, "并存 " + ", ".join(sorted(fs))))

def _index_exempt(dp):
    """读取 validation 根 目录索引.md 的保留目录名集合（R6 存量豁免，00_项目规则.md R6）。"""
    idx = os.path.join(dp, "目录索引.md")
    if not os.path.isfile(idx):
        return set()
    try:
        rows = io.open(idx, encoding="utf-8-sig").read().splitlines()
    except Exception:
        return set()
    names = set()
    for row in rows:
        if row.startswith("|") and not row.startswith("| 目录"):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if cells:
                names.add(cells[0])
    return names

# 3) R6：validation 新增活跃目录 >20（_archive 与目录索引存量豁免除外）
for dp, dns, fns in os.walk(R):
    dns[:] = [x for x in dns if x not in SKIP_DIRS]
    if os.path.basename(dp) == "validation":
        exempt = _index_exempt(dp)
        active = [x for x in dns if x != "_archive" and x not in exempt]
        if len(active) > 20:
            VIOL.append(("R6-validation-flood", os.path.relpath(dp, R), f"活跃 {len(active)} 个(>20)"))
        dns[:] = []  # 不再深入 validation

# 4) 进阶8：裸实验——validation 活跃目录内无 .md 结论文件
    for x in (active if os.path.basename(dp) == "validation" else []):
        sub = os.path.join(dp, x)
        has_md = any(f.endswith(".md") for _, _, fs in os.walk(sub) for f in fs)
        has_any = any(fs for _, _, fs in os.walk(sub))
        if has_any and not has_md and age_days(sub) > 14:
            VIOL.append(("A2-8-naked-exp", os.path.relpath(sub, R), "有产物无结论md且>14天"))

# 5) R8：整理清单存在未执行项超7天
ld = os.path.join(R, "00_文档中心", "归档", "整理清单")
if os.path.isdir(ld):
    for f in os.listdir(ld):
        if f.endswith(".csv"):
            try:
                rows = list(csv.reader(io.open(os.path.join(ld, f), encoding="utf-8-sig")))
            except Exception: continue
            pend = [r for r in rows[1:] if len(r) >= 6 and r[5].strip() not in ("已执行", "") and "待确认" not in r[5] and "并入" not in r[5]]
            if pend and age_days(os.path.join(ld, f)) > 7:
                VIOL.append(("R8-list-pending", f, f"{len(pend)} 项未回填且清单>7天"))

# 6) 冻结区存在性哨兵（被误删/误挪时报）
FROZEN = ["QQ_AGENT_INSTRUCTIONS.md", "启动DSH-Web.cmd", "scripts\\monitor_all_strategies.py",
          "scripts\\strategy_research_common.py", "scripts\\replay_raw_signals_with_stops.py",
          "宏观日历研究\\data\\calendar_export.csv", "黄金\\30m2H策略\\参考实现工程",
          "observation_dashboard\\dashboard.csv", "黄金\\1H_M30_4H策略\\scripts\\signals"]
for fz in FROZEN:
    if not os.path.exists(os.path.join(R, fz)):
        VIOL.append(("FROZEN-missing", fz, "冻结区路径缺失！检查是否被误动"))

# 7) 进阶2：同因失败重复（启发式：ea_alignment_logs\_scratch 中同名 .py+.log 且 log 末行含 error/fail，>7天）
sc = os.path.join(R, "ea_alignment_logs", "_scratch")
if os.path.isdir(sc):
    logs = {}
    for f in os.listdir(sc):
        if f.endswith(".log"):
            try: tail = io.open(os.path.join(sc, f), encoding="utf-8", errors="ignore").read()[-400:].lower()
            except Exception: continue
            if ("error" in tail or "fail" in tail) and age_days(os.path.join(sc, f)) > 7:
                logs[f] = True
    if logs:
        VIOL.append(("A2-2-repeat-risk", "ea_alignment_logs\\_scratch", f"{len(logs)} 个失败态日志滞留>7天，重跑前先核根因"))

print(f"check_project_rules @ {now.strftime('%Y-%m-%d %H:%M')}  violations={len(VIOL)}")
for code, loc, note in VIOL:
    print(f"  [{code}] {loc} :: {note}")
if not VIOL: print("  （无违规）")
sys.exit(1 if VIOL else 0)

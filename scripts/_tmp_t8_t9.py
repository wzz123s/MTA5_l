# -*- coding: utf-8 -*-
"""_tmp_t8_t9.py — T8 中间方案 + T9 校验（2026-09-08，用户已批准）
T8：仅归档"零引用"validation 目录（全树代码+文档均未提及、且非近14天），生成 目录索引.md。
T9：zip 逐文件 sha256 校验（base_data_backup 原件、V反 features×4 原件）；全部 OK 才写入可删清单，
    删除动作由外层 PowerShell 依清单送回收站（本脚本不删任何文件；tester_agent 原件不校验不删）。
"""
import os, io, re, csv, shutil, zipfile, hashlib, datetime

R = r"F:\use_code\MTA5_l"
V = os.path.join(R, "黄金", "30m2H策略", "data", "validation")
NOW = datetime.datetime.now()
SKIP_DIR_MARK = ("\\archive\\", "backup_20260907", "_archive", "\\归档\\", "node_modules", "__pycache__", "\\.git\\", ".obsidian", ".workbuddy")
TEXT_EXT = (".py", ".md", ".txt", ".json", ".set", ".ini", ".ps1", ".mjs", ".mq5", ".cmd")

# ---------- 1) 收集活跃目录 ----------
act = sorted([d for d in os.listdir(V) if os.path.isdir(os.path.join(V, d)) and d != "_archive"])
recent14 = {d for d in act if (NOW.timestamp() - os.stat(os.path.join(V, d)).st_mtime) / 86400 <= 14}

# ---------- 2) 全树引用扫描（排除 validation 自身内部、归档区） ----------
name_pat = re.compile("|".join(re.escape(d) for d in act))
referenced = set()
n_files = 0
for dp, dns, fns in os.walk(R):
    dns[:] = [x for x in dns if x not in ("node_modules", "__pycache__")]
    full = dp + "\\"
    if any(m in full for m in SKIP_DIR_MARK): dns[:] = []; continue
    if os.path.normcase(dp).startswith(os.path.normcase(V)): dns[:] = []; continue
    for f in fns:
        if not f.endswith(TEXT_EXT): continue
        p = os.path.join(dp, f)
        try:
            if os.stat(p).st_size > 3_000_000: continue
            txt = io.open(p, encoding="utf-8", errors="ignore").read()
        except OSError: continue
        n_files += 1
        if n_files % 1500 == 0: print(f"  scanned {n_files} files, ref={len(referenced)}")
        for m in name_pat.finditer(txt): referenced.add(m.group(0))
zero = [d for d in act if d not in referenced and d not in recent14]
print(f"== T8 == 活跃={len(act)} 扫描文本={n_files} 被引用={len(referenced & set(act))} 近14天={len(recent14)} 零引用(将归档)={len(zero)}")

# ---------- 3) 归档零引用目录（先清单后移动） ----------
dry = os.path.join(R, "00_文档中心", "归档", "整理清单", "phase2c_t8_zero_ref_20260908.csv")
os.makedirs(os.path.dirname(dry), exist_ok=True)
moved_rows = []
for d in zero:
    s = os.path.join(V, d)
    ym = datetime.datetime.fromtimestamp(os.stat(s).st_mtime).strftime("%Y-%m")
    dst = os.path.join(V, "_archive", ym, d)
    if os.path.exists(dst): moved_rows.append((d, "", "SKIP-dst", "已执行")); continue
    os.makedirs(os.path.join(V, "_archive", ym), exist_ok=True)
    shutil.move(s, dst); moved_rows.append((d, os.path.relpath(dst, R), "零引用归档", "已执行"))
with io.open(dry, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["目录", "去向", "原因", "状态"]); w.writerows(moved_rows)
print(f"  归档完成 {len(moved_rows)}，清单 {os.path.basename(dry)}")

# ---------- 4) 生成 目录索引.md ----------
act2 = sorted([d for d in os.listdir(V) if os.path.isdir(os.path.join(V, d)) and d != "_archive"])
def dstat(d):
    p = os.path.join(V, d); n = 0; sz = 0
    for dp, _, fns in os.walk(p):
        for fn in fns:
            n += 1
            try: sz += os.stat(os.path.join(dp, fn)).st_size
            except OSError: pass
    return n, sz, datetime.datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%Y-%m-%d")
lines = ["# 30m2H data/validation 目录索引", "",
         f"> 生成：{NOW.strftime('%Y-%m-%d %H:%M')} ｜ T8 中间方案产物（用户批准：零引用归档+全量索引导航，被引用者一律不动）",
         f"> 口径：活跃 {len(act2)} 个 = 近14天 {len(recent14)} + 被现役文本引用保留 {len(act2)-len(recent14)}；零引用已沉 _archive\\（另见整理清单）",
         "> 新增实验纪律：00_项目规则.md R6（主题_YYYYMMDD 命名、收口必写结论、超20个需二次归档评估）", ""]
lines.append("| 目录 | 最后修改 | 文件数 | 体积MB | 保留原因 |")
lines.append("|---|---|---:|---:|---|")
for d in act2:
    n, sz, mt = dstat(d)
    why = "近14天活跃" if d in recent14 else "被现役代码/文档引用（历史结论记载）"
    lines.append(f"| {d} | {mt} | {n} | {sz/1e6:.1f} | {why} |")
arch_root = os.path.join(V, "_archive")
if os.path.isdir(arch_root):
    buckets = [x for x in os.listdir(arch_root) if os.path.isdir(os.path.join(arch_root, x))]
    an = sum(len(fs) for _, _, fs in os.walk(arch_root))
    asz = sum(os.path.getsize(os.path.join(dp, f)) for _, _, fs in os.walk(arch_root) for f in fs)
    lines += ["", f"已归档：_archive\\ 下 {len(buckets)} 个年月桶，共 {an} 文件 {asz/1e6:.0f} MB（含本轮 T8 {len(moved_rows)} 目录与 Phase2 首轮 30 目录）。"]
idx = os.path.join(V, "目录索引.md")
io.open(idx, "w", encoding="utf-8", newline="").write("\n".join(lines))
print(f"  索引已生成 {os.path.basename(idx)}（{len(act2)} 行）")

# ---------- 5) T9 校验（不删） ----------
def sha256_file(p, cs=4 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(cs), b""): h.update(b)
    return h.hexdigest()

rep = os.path.join(R, "00_文档中心", "归档", "整理清单", "t9_verify_report_20260908.txt")
out = ["# T9 zip 校验报告（仅 OK 条目允许外层送回收站）"]
def verify_zip_dir(zip_path, src_dir, label):
    ok_all = True
    zf = zipfile.ZipFile(zip_path)
    zmap = {i.filename: i for i in zf.infolist()}
    ofiles = {os.path.relpath(os.path.join(dp, fn), src_dir).replace("\\", "/") for dp, _, fns in os.walk(src_dir) for fn in fns}
    if set(zmap) != ofiles:
        ok_all = False; out.append(f"FAIL\tDIR\t{label}\t成员集不一致 仅zip={set(zmap)-ofiles} 仅原件={ofiles-set(zmap)}")
    for name in sorted(zmap):
        op = os.path.join(src_dir, name.replace("/", os.sep))
        if not os.path.exists(op): ok_all = False; out.append(f"FAIL\tFILE\t{op}\t原件缺失"); continue
        hh = hashlib.sha256()
        with zf.open(name) as gf:
            for b in iter(lambda: gf.read(4 << 20), b""): hh.update(b)
        a = sha256_file(op)
        if hh.hexdigest() == a and zmap[name].file_size == os.path.getsize(op):
            out.append(f"OK\tFILE\t{op}\tsha256一致 {zmap[name].file_size}B")
        else:
            ok_all = False; out.append(f"FAIL\tFILE\t{op}\thash或尺寸不符")
    if ok_all: out.append(f"OK\tDIR-DEL\t{src_dir}\t目录内全部文件校验通过，可删原件")
    print(f"  [{label}] all_ok={ok_all}")

def verify_zip_files(zip_path, base_dir, label):
    zf = zipfile.ZipFile(zip_path); ok_all = True
    for i in zf.infolist():
        op = os.path.join(base_dir, i.filename)
        if not os.path.exists(op): ok_all = False; out.append(f"FAIL\tFILE\t{op}\t原件缺失"); continue
        hh = hashlib.sha256()
        with zf.open(i) as gf:
            for b in iter(lambda: gf.read(4 << 20), b""): hh.update(b)
        if hh.hexdigest() == sha256_file(op): out.append(f"OK\tFILE\t{op}\tsha256一致 {i.file_size}B")
        else: ok_all = False; out.append(f"FAIL\tFILE\t{op}\thash不符")
    print(f"  [{label}] all_ok={ok_all}")
    return ok_all

bd = os.path.join(R, "黄金", "30m2H策略", "参考实现工程", "base_data_backup_20260811_200652")
if os.path.isdir(bd) and os.path.exists(bd + ".zip"):
    verify_zip_dir(bd + ".zip", bd, "base_data_backup")
elif os.path.isdir(bd):
    out.append(f"FAIL\tDIR\t{bd}\t无zip不校验")
else:
    print("  [base_data_backup] 目录已不存在（此前已删？），跳过")

vr = os.path.join(R, "V型反转策略", "data", "processed")
zpath = os.path.join(vr, "_compress_20260908.zip")
if os.path.exists(zpath):
    verify_zip_files(zpath, vr, "V反 features")
io.open(rep, "w", encoding="utf-8").write("\n".join(out) + "\n")
n_ok = sum(1 for l in out if l.startswith("OK\t"))
n_bad = sum(1 for l in out if l.startswith("FAIL"))
print(f"T9 校验: OK={n_ok} FAIL={n_bad}，报告 {os.path.basename(rep)}")
me = os.path.abspath(__file__)
shutil.move(me, os.path.join(R, "scripts", "_archive", "2026-09", os.path.basename(me)))
print("DONE (self-archived)")

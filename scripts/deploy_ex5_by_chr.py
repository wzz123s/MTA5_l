# -*- coding: utf-8 -*-
"""deploy_ex5_by_chr.py — 按 `chart*.chr` 的 `path=` 精确投递 .ex5 到终端（治 T22「假部署」）

为什么需要（00_README T22 / 问题记录 §二十三 A/D 阶段一第 7 条）：
  终端有两个 Experts 目录（`MQL5\\Experts\\` 与 `MQL5\\Experts\\Advisors\\`），同名 .ex5
  可能各存一份且版本不同；图表实际加载哪一份**只由 .chr 的 path= 决定**。2026-09-08 曾把
  主线 30m2H_Strategy_EA 的 M15 孤儿句柄修复版投到 Advisors\\，而 chart06 加载的是根目录
  09-07 旧版 → 修复从未在实盘生效。故投递目标必须取自 .chr，硬编码目录＝假部署。

谁在用（R3）：EA 源码改动后的部署（本轮 T11/T14/T22）；此后任何 .ex5 更新都应走本脚本。

安全设计：
  1) 默认 **dry-run**，只打印计划；`--apply` 才写文件；
  2) 投递前把目标备份为 `<name>.bak_<tag>`（已存在同名备份则加时间戳，不覆盖）；
  3) 投递后 **sha256 校验** 源 == 目标，不一致即报 FAIL；
  4) **不启动/不重启/不打断终端**：已挂载的 EA 继续跑内存中的旧版，新版需人工在终端
     逐图表刷新（右键→智能交易→刷新）才生效 —— 本脚本只负责把文件放对位置；
  5) 生成 R8 清单 CSV 到 `00_文档中心\\归档\\整理清单\\`，执行后回填状态；
  6) 源 .ex5 由工程内 `**/auto_trade/*.ex5` 扫描得到（跳过 backup/_archive 目录），
     不硬编码工程路径。

用法：
  python scripts\\deploy_ex5_by_chr.py                 # dry-run，看计划
  python scripts\\deploy_ex5_by_chr.py --apply         # 执行投递
  python scripts\\deploy_ex5_by_chr.py --apply --only 30m2H_ABC_EA,MCT_EA
  python scripts\\deploy_ex5_by_chr.py --apply --tag pre_t11t14_20260909
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_attribution as la                                    # noqa: E402

ROOT = la.ROOT
TERMINAL_DATA = la.TERMINAL_DATA
LIST_DIR = ROOT / "00_文档中心" / "归档" / "整理清单"
SKIP_DIR_PARTS = ("backup", "_archive", "归档", "deploy_backup")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def find_project_ex5() -> dict[str, Path]:
    """扫工程内 **/auto_trade/*.ex5 -> {EA 名: 路径}（跳过备份/归档目录）。"""
    out: dict[str, Path] = {}
    for p in sorted(ROOT.glob("**/auto_trade/*.ex5")):
        if any(part.lower() in SKIP_DIR_PARTS for part in p.parts):
            continue
        out.setdefault(p.stem, p)
    return out


def find_terminal_ex5(name: str) -> list[Path]:
    """终端两处 Experts 目录里同名的 .ex5（用于未挂载 EA 的同步与双副本检测）。"""
    hits = []
    for sub in (("MQL5", "Experts"), ("MQL5", "Experts", "Advisors")):
        p = TERMINAL_DATA.joinpath(*sub) / f"{name}.ex5"
        if p.exists():
            hits.append(p)
    return hits


def plan(only: set[str] | None) -> list[dict]:
    ea_paths = la.chart_ea_paths()                 # {EA: .chr 声明的终端相对路径}
    proj = find_project_ex5()
    rows = []
    for ea, src in sorted(proj.items()):
        if only and ea not in only:
            continue
        rel = ea_paths.get(ea)
        if rel:
            target = TERMINAL_DATA / "MQL5" / rel.replace("\\", "/")
            mounted = True
        else:
            hits = find_terminal_ex5(ea)
            if not hits:
                rows.append({"ea": ea, "src": src, "target": None, "mounted": False,
                             "note": "未挂载且终端无同名 .ex5 → 跳过"})
                continue
            target = hits[0]
            mounted = False
        dup = find_terminal_ex5(ea)
        note = ("双副本：" + "、".join(str(x.parent.name) for x in dup) if len(dup) > 1 else "")
        # 防版本回退：源比目标旧 → 拒绝投递。终端侧可能被独立编译过（例如
        # USOIL2H_CrossConfirm_EA 终端 09-06 15:36 比工程内 09-04 22:29 新），
        # 覆盖即丢失该改动。判据是时间戳比较，不写死 EA 名单（A2.5）。
        if target.exists() and src.stat().st_mtime < target.stat().st_mtime:
            rows.append({
                "ea": ea, "src": src, "target": None, "mounted": mounted,
                "note": "源({:%m-%d %H:%M}) 比目标({:%m-%d %H:%M}) 旧 → 拒绝投递(防版本回退)".format(
                    datetime.fromtimestamp(src.stat().st_mtime),
                    datetime.fromtimestamp(target.stat().st_mtime)),
            })
            continue
        rows.append({"ea": ea, "src": src, "target": target, "mounted": mounted, "note": note})
    return rows


def main() -> None:
    apply = "--apply" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = {x.strip() for x in sys.argv[sys.argv.index("--only") + 1].split(",") if x.strip()}
    tag = "pre_t11t14_20260909"
    if "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]

    rows = plan(only)
    print(f"模式: {'APPLY（写文件）' if apply else 'DRY-RUN（只打印计划）'}   tag={tag}")
    print(f"终端: {TERMINAL_DATA}\n")
    todo = []
    for r in rows:
        if r["target"] is None:
            print(f"[skip] {r['ea']}: {r['note']}")
            continue
        src, tgt = r["src"], r["target"]
        same = tgt.exists() and sha256(src) == sha256(tgt)
        flag = "已是最新（sha256 相同）" if same else "待投递"
        print(f"[{flag}] {r['ea']}  {'(已挂载)' if r['mounted'] else '(未挂载，同步副本)'}")
        print(f"    源  : {src.relative_to(ROOT)}  ({src.stat().st_size:,}B, "
              f"{datetime.fromtimestamp(src.stat().st_mtime):%Y-%m-%d %H:%M})")
        if tgt.exists():
            print(f"    目标: {tgt.relative_to(TERMINAL_DATA)}  ({tgt.stat().st_size:,}B, "
                  f"{datetime.fromtimestamp(tgt.stat().st_mtime):%Y-%m-%d %H:%M})")
        else:
            print(f"    目标: {tgt.relative_to(TERMINAL_DATA)}  (不存在，将新建)")
        if r["note"]:
            print(f"    备注: {r['note']}")
        if not same:
            todo.append(r)

    print(f"\n需投递 {len(todo)} 个（其余已是最新或跳过）")
    if not apply:
        if todo:
            print("\n将执行的动作（--apply 生效）：")
            for i, r in enumerate(todo, 1):
                bak = r["target"].with_name(r["target"].name + f".bak_{tag}")
                print(f"  {i}. 备份 {r['target'].name} -> {bak.name}（若目标存在）")
                print(f"     复制 {r['src'].name} -> {r['target'].relative_to(TERMINAL_DATA)}")
            print("\n确认无误后加 --apply 执行；执行后仍需在终端逐图表刷新 EA 才生效。")
        return

    LIST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    list_csv = LIST_DIR / f"ex5_deploy_{tag}.csv"
    csv_rows = [["序号", "动作", "源", "目标", "原因", "状态"]]
    ok = fail = 0
    for i, r in enumerate(todo, 1):
        src, tgt = r["src"], r["target"]
        tgt.parent.mkdir(parents=True, exist_ok=True)
        bak_note = "无（目标原不存在）"
        if tgt.exists():
            bak = tgt.with_name(tgt.name + f".bak_{tag}")
            if bak.exists():
                bak = tgt.with_name(tgt.name + f".bak_{tag}_{stamp}")
            shutil.copy2(tgt, bak)
            bak_note = bak.name
        shutil.copy2(src, tgt)
        good = sha256(src) == sha256(tgt)
        ok += 1 if good else 0
        fail += 0 if good else 1
        print(f"  [{'OK' if good else 'FAIL'}] {r['ea']} -> {tgt.relative_to(TERMINAL_DATA)}"
              f"  (备份 {bak_note})  sha256 {sha256(tgt)[:16]}…")
        csv_rows.append([i, "备份+复制", str(src.relative_to(ROOT)),
                         str(tgt.relative_to(TERMINAL_DATA)),
                         f"T11/T14 修复部署（T22：目标取自 .chr path=）；备份={bak_note}",
                         "已执行(sha256校验通过)" if good else "已执行但校验失败!"])
    with list_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        csv.writer(fh).writerows(csv_rows)
    print(f"\n[done] 投递 {ok} 成功 / {fail} 失败；R8 清单: {list_csv.relative_to(ROOT)}")
    print("提醒：文件已就位，但**运行中的 EA 仍是旧版**——需在终端逐图表刷新才生效。")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()

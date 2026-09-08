# -*- coding: utf-8 -*-
"""live_attribution.py — DEMO 实挂成交的血缘归因 + 终端实参读取（跨策略公共库）

谁在用（R3 登记）：
  - scripts\\monitor_all_strategies.py：dashboard 增列（已实现盈亏/EA 下单闸/台账可读性）
    与「真实成交归因（血缘口径）」节
  - scripts\\monitor_cycle.py：30 分钟监测报告总览表
建立：2026-09-09（00_README §6 T11/T14/T17~T19/T21 的 F 项落地）
依据：00_文档中心\\问题记录.md §二十三（含「补充取证二」的方法论约束）

口径铁律（违者归因即失真，均有实测证据）：
  1) 盈亏归因**只用 position_id 血缘 + 开仓 deal 的 magic**。
     禁用平仓侧 deal.magic（EA 主动平仓在 CTrade 未设 magic 时落 0，15/59 持仓因此错配）；
     禁用 deal.reason（实测不可靠：comment='[sl 4670.599]' 的亏损平仓被记 TP、
     人工 'manual close (TP overdue)' 被记 SL、全窗口 EXPERT 为 0 笔）。
  2) 平仓类型以 deal.comment 前缀判定：'[sl '→SL、'[tp '→TP、其余非空→OTHER、空→UNSPECIFIED。
     不做推断（A2.5 只做判断不写死逻辑：判据即前缀，可核验）。
  3) 时间统一为**服务器时间**（deal.time 即服务器时间戳，用 utcfromtimestamp 解）。
     台账/EA 日志亦为服务器时间；此前用本地时间会系统性 +8h（§二十三⑩）。
  4) vol==0 的 deal 是账务性（入金/归档），计入 deposits，不计入交易盈亏。

只读模块：不下单、不改终端设置、不写终端目录任何文件。
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"F:\use_code\MTA5_l")
TERMINAL_DATA = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
# 必须与 scripts/mt5/mt5_connection.MAIN_TERMINAL_PATH 一致：防止连到副调试终端。
MAIN_TERMINAL_PATH = r"F:\Program Files\MetaTrader 5\terminal64.exe"
CHARTS_DIR = TERMINAL_DATA / "MQL5" / "Profiles" / "Charts" / "Default"
FILES_DIR = TERMINAL_DATA / "MQL5" / "Files"

# magic -> (EA 文件, 策略行名, 分支/stage)。依据 §二十三②（源码 InpMagic + 日志 + deal comment 三方确证）
EA_MAGIC_MAP: dict[int, tuple[str, str, str]] = {
    302025: ("30m2H_Strategy_EA", "30m2H", "base(旧,2026-06)"),
    302026: ("30m2H_Strategy_EA", "30m2H", "stage1(旧)"),
    302027: ("30m2H_Strategy_EA", "30m2H", "stage2(旧)"),
    302028: ("30m2H_Strategy_EA", "30m2H", "stage3(旧)"),
    302036: ("30m2H_Strategy_EA", "30m2H", "base"),
    302037: ("30m2H_Strategy_EA", "30m2H", "stage1"),
    302038: ("30m2H_Strategy_EA", "30m2H", "stage2"),
    302039: ("30m2H_Strategy_EA", "30m2H", "stage3"),
    312025: ("1H_M30_4H_Strategy_EA", "1H_M30_4H", "base(未挂载)"),
    312026: ("1H_M30_4H_CurrentCandidate_EA", "1H_M30_4H", "candidate"),
    312027: ("1H_M30_4H_Strategy_EA", "1H_M30_4H", "stage2(未挂载)"),
    312028: ("1H_M30_4H_Strategy_EA", "1H_M30_4H", "stage3(未挂载)"),
    312036: ("1H_M30_4H_ABC_EA", "1H_M30_4H", "ABC"),
    342036: ("2H_M30_6H_ABC_EA", "2H_M30_6H", "ABC"),
    352036: ("30m2H_ABC_EA", "30m2H", "ABC"),
    362036: ("USOIL2H_CrossConfirm_EA", "USOIL2H", "causal"),
    362137: ("USOIL4H_Gate_On2H_EA", "USOIL4H", "gate"),
    372036: ("BiasReversal_Combo_EA", "BiasReversal", "long"),
    372037: ("BiasReversal_Combo_EA", "BiasReversal", "short"),
    411101: ("Gold_DataEvent_EA", "Gold_DataEvent", "event"),
    411102: ("Oil_DataEvent_EA", "Oil_DataEvent", "event"),
    411103: ("MCT_EA", "MCT", "mct"),
}

# 已知撞号（同一 magic 被两个来源主张），归因时按上表取值但必须告警（§二十三②/⑪）
MAGIC_CONFLICTS: dict[int, str] = {
    312026: "1H_M30_4H_CurrentCandidate_EA 的 InpMagic 与 1H_M30_4H_Strategy_EA 的 stage1(312025+1) 相同",
    302025: "auto_trader.py（Python 下单器）与 30m2H_Strategy_EA 旧 base 共用",
}

# 监控关心的台账（EA Files 导出名 -> 归属 EA）
LEDGER_FILES: dict[str, str] = {
    "30m2H_strategy_trade_ledger.csv": "30m2H_Strategy_EA",
    "30m2H_strategy_deal_history.csv": "30m2H_Strategy_EA",
    "30m2H_abc_trade_ledger.csv": "30m2H_ABC_EA",
    "1H_M30_4H_abc_trade_ledger.csv": "1H_M30_4H_ABC_EA",
    "1H_M30_4H_sim_deployment_trade_ledger.csv": "1H_M30_4H_CurrentCandidate_EA",
    "2H_M30_6H_abc_trade_ledger.csv": "2H_M30_6H_ABC_EA",
    "bias_reversal_combo_trade_ledger.csv": "BiasReversal_Combo_EA",
    "MCT_trade_ledger.csv": "MCT_EA",
    "Gold_DataEvent_trade_ledger.csv": "Gold_DataEvent_EA",
    "Oil_DataEvent_trade_ledger.csv": "Oil_DataEvent_EA",
}


def server_time(ts: int) -> str:
    """deal.time 是服务器时间戳 → 服务器时间字符串（不要用本地时间，会 +8h）。"""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def exit_tag(comment: str) -> str:
    """平仓类型判据＝comment 前缀（禁用 deal.reason，见模块头口径铁律 2）。"""
    c = (comment or "").strip()
    if c.startswith("[sl "):
        return "SL"
    if c.startswith("[tp "):
        return "TP"
    return "OTHER" if c else "UNSPECIFIED"


def _connect():
    """返回已初始化的 mt5 模块，失败返回 (None, 原因)。锁定主监控终端。"""
    try:
        import MetaTrader5 as mt5
    except Exception as e:                                    # 库缺失
        return None, f"MetaTrader5 库不可用: {e}"
    if not mt5.initialize(path=MAIN_TERMINAL_PATH):
        return None, f"mt5.initialize 失败: {mt5.last_error()}"
    return mt5, ""


def fetch_deals(mt5, since_year: int = 2025) -> list:
    from datetime import datetime as _dt
    return list(mt5.history_deals_get(_dt(since_year, 1, 1), _dt.utcnow()) or [])


def attribute_by_lineage(deals: list) -> dict:
    """按 position_id 血缘归因：每笔平仓的盈亏记到**开仓方 magic** 名下。

    返回 {"per_ea": {...}, "per_magic": {...}, "totals": {...}, "mismatches": [...]}
    per_ea 按 EA 汇总——主线有 7 个 magic、乖离有多/空 2 个 magic，会被合并成一行，
    故 branches/magics 用聚合集合（避免"首个 magic 冒充整个 EA"的标签失真）；
    per_magic 是精确明细。两者的 realized 合计必须相等（main 里有断言）。
    """
    positions: dict[int, dict] = {}
    deposits = 0.0
    for d in deals:
        if d.volume == 0:                                     # 账务性（入金/归档）
            deposits += float(d.profit)
            continue
        if not d.position_id:
            continue
        p = positions.setdefault(d.position_id, {"open": None, "closes": []})
        if d.entry == 0:                                      # IN
            if p["open"] is None:
                p["open"] = d
        elif d.entry == 1:                                    # OUT
            p["closes"].append(d)

    per_ea: dict[str, dict] = {}
    per_magic: dict = {}
    mismatches: list[dict] = []
    unknown: list[int] = []
    realized_total = 0.0

    for pid, p in positions.items():
        op = p["open"]
        if op is None:                                        # 窗口外开仓
            ea, strat, branch, omagic = "(窗口外开仓)", "-", "-", None
        else:
            omagic = int(op.magic)
            if omagic in EA_MAGIC_MAP:
                ea, strat, branch = EA_MAGIC_MAP[omagic]
            else:
                ea, strat, branch = f"(未登记 magic {omagic})", "-", "-"
                unknown.append(omagic)
        profit = sum(float(c.profit) for c in p["closes"])
        realized_total += profit

        e = per_ea.setdefault(ea, {
            "ea": ea, "strategy": strat, "branches": set(), "magics": set(),
            "positions": 0, "closed": 0, "still_open": 0,
            "realized": 0.0, "mismatched": 0, "by_exit": {},
        })
        m = per_magic.setdefault(omagic if omagic is not None else -1, {
            "magic": omagic, "ea": ea, "strategy": strat, "branch": branch,
            "positions": 0, "closed": 0, "still_open": 0,
            "realized": 0.0, "mismatched": 0, "by_exit": {},
        })
        for rec in (e, m):
            rec["positions"] += 1
            rec["realized"] += profit
            if not p["closes"]:
                rec["still_open"] += 1
        e["branches"].add(branch)
        if omagic is not None:
            e["magics"].add(omagic)
        for c in p["closes"]:
            tag = exit_tag(c.comment)
            for rec in (e, m):
                rec["closed"] += 1
                rec["by_exit"][tag] = rec["by_exit"].get(tag, 0) + 1
            if omagic is not None and int(c.magic) != omagic:   # 开平 magic 错配
                for rec in (e, m):
                    rec["mismatched"] += 1
                mismatches.append({
                    "position_id": pid, "open_magic": omagic, "close_magic": int(c.magic),
                    "open_time": server_time(op.time), "close_time": server_time(c.time),
                    "profit": round(float(c.profit), 2), "exit_tag": tag,
                    "comment": (c.comment or "")[:40],
                })

    for e in per_ea.values():                                  # set -> 排序字符串（可打印/可序列化）
        e["branches"] = ",".join(sorted(e["branches"]))
        e["magics"] = ",".join(str(x) for x in sorted(e["magics"])) or "-"

    totals = {
        "deals": len(deals),
        "positions": len(positions),
        "realized": round(realized_total, 2),
        "deposits": round(deposits, 2),
        "balance_expected": round(realized_total + deposits, 2),
        "mismatched_positions": len({m["position_id"] for m in mismatches}),
        "mismatched_closes": len(mismatches),
        "unknown_magics": sorted(set(unknown)),
        "magic_conflicts": MAGIC_CONFLICTS,
        "per_ea_sum": round(sum(e["realized"] for e in per_ea.values()), 2),
        "per_magic_sum": round(sum(m["realized"] for m in per_magic.values()), 2),
    }
    return {"per_ea": per_ea, "per_magic": per_magic, "totals": totals, "mismatches": mismatches}


def read_chart_params(collect_skipped: list | None = None) -> dict[str, dict]:
    """扫全部 chart*.chr，按 EA 名归组读实参（含 bool）。替代硬编码 chart10 的 read_ea_input。

    EA 名优先取 expert 块的 `.ex5` 路径行，回退 `^name=` 行：实测大体积 .chr（chart07，359KB）
    用单一 `^name=` 正则会漏识别 → 双路兜底；跳过原因回传给调用方，不静默（A2.11）。
    返回 {ea_name: {"charts": [chartNN.chr...], "symbol": ..., "inputs": {...}}}
    同一 EA 出现多张图表 => 双挂（§二十三⑧），调用方须告警。
    """
    out: dict[str, dict] = {}
    if not CHARTS_DIR.is_dir():
        if collect_skipped is not None:
            collect_skipped.append(("(Charts 目录)", f"不存在: {CHARTS_DIR}"))
        return out
    for p in sorted(CHARTS_DIR.glob("*.chr")):
        try:
            txt = p.read_text(encoding="utf-16", errors="replace")
        except PermissionError:
            if collect_skipped is not None:
                collect_skipped.append((p.name, "PermissionError(终端独占句柄)"))
            continue
        except Exception as e:
            if collect_skipped is not None:
                collect_skipped.append((p.name, f"读取失败:{type(e).__name__}"))
            continue
        # 只解析 <expert> 块：整文件扫描会把图表上指标的参数混进 EA 实参——实测
        # chart09（乖离反转）挂了 4 个 Custom Moving Average 指标，其 InpMAPeriod/
        # InpMAShift/InpMAMethod 会污染结果（源码 23 个 input vs 整文件扫描 26 个）。
        # 同理，大体积 .chr 的首个 ^name= 可能是指标的 name=Main，据此判定会整文件漏识别
        # （chart07 曾因此丢失，导致双挂只报出一张图）。
        exp = re.search(r"<expert>(.*?)</expert>", txt, re.S)
        if not exp:
            if collect_skipped is not None and re.search(r"\bInp[A-Za-z0-9_]+=", txt):
                collect_skipped.append((p.name, "有 Inp* 参数但无 <expert> 块"))
            continue
        block = exp.group(1)
        nm = re.search(r"^name=([A-Za-z0-9_]+)\s*$", block, re.M)
        ex5 = re.findall(r"([A-Za-z0-9_]+_EA)\.ex5", block)
        ea = nm.group(1) if nm and nm.group(1).endswith("_EA") else (ex5[0] if ex5 else None)
        if not ea:
            if collect_skipped is not None:
                collect_skipped.append((p.name, "<expert> 块内未识别出 EA 名"))
            continue
        inputs = {}
        inp_block = re.search(r"<inputs>(.*?)</inputs>", block, re.S)
        if inp_block:
            for im in re.finditer(r"^\s*(Inp[A-Za-z0-9_]+)=([^\r\n|]*)", inp_block.group(1), re.M):
                inputs.setdefault(im.group(1), im.group(2).strip())
        sym = re.search(r"\b(InpSymbol)=([A-Za-z0-9_.]+)", block)
        rec = out.setdefault(ea, {"charts": [], "symbol": sym.group(2) if sym else "", "inputs": {}})
        rec["charts"].append(p.name)
        if len(rec["charts"]) == 1:
            rec["inputs"] = inputs
        else:
            # 双挂：把第一张的实参也并入 per_chart，保证每张图都可独立判定下单闸
            pc = rec.setdefault("per_chart", {})
            if len(rec["charts"]) == 2:
                pc[rec["charts"][0]] = rec["inputs"]
            pc[p.name] = inputs
    return out


def trading_gate(charts: dict[str, dict]) -> list[dict]:
    """把 chart 实参折算成「哪些实例在真下单」（双闸：SimMode=false 且 AllowRealTrading=true）。"""
    rows = []
    for ea, rec in sorted(charts.items()):
        variants = [(",".join(rec["charts"]), rec["inputs"])]
        if "per_chart" in rec:
            variants = [(c, inp) for c, inp in sorted(rec["per_chart"].items())]
        for chart, inp in variants:
            sim = inp.get("InpSimMode", "")
            allow = inp.get("InpAllowRealTrading", "")
            live = (sim.lower() == "false" and allow.lower() == "true")
            rows.append({
                "ea": ea, "chart": chart, "symbol": rec.get("symbol", ""),
                "sim_mode": sim or "?", "allow_real": allow or "?",
                "magic": inp.get("InpMagic") or inp.get("InpMagicLong") or "?",
                "live_trading": live,
                "duplicate": len(rec["charts"]) > 1,
            })
    return rows


def chart_layout() -> tuple[dict, dict]:
    """返回 ({EA 名: [chart 文件...]}, {chart 文件: EA 名})。

    部署脚本据此**动态定位**，不再硬编码 chartNN——编号会随图表增删重排：
    实测 chart05/08/11 已空（原油三 EA 摘除）、chart12 从 Oil_DataEvent 变成了 MCT_EA。
    见 00_README T20。
    """
    by_ea = {ea: list(rec["charts"]) for ea, rec in read_chart_params().items()}
    by_chart = {c: ea for ea, cs in by_ea.items() for c in cs}
    return by_ea, by_chart


def guard_deploy(script: str, target_ea: str, target_chart: str,
                 template_chart: str = "", template_ea: str = "") -> None:
    """部署脚本前置守卫（T20）：不通过即 SystemExit，绝不带着失效假设去改终端。

    判据（均可核验，不写死编号）：
      1) target_ea 已挂在别的 chart → 再挂即双挂（同 magic 互相覆盖台账/信号，T13）
      2) target_chart 当前挂着别的 EA → 继续会顶掉它
      3) template_chart 的实际 EA != template_ea → chart 编号已漂移，模板假设失效
    默认拒绝；仅当命令行带 --force 才放行（放行前仍打印实际盘面）。
    重启/强杀终端属 AGENTS.md C 段禁区，本守卫不代劳，只拦"基于错误假设的写入"。
    """
    import sys
    # 注意：这里**不要** reconfigure stdout。守卫的输出总是给人看的（人工在 cmd 里跑部署脚本），
    # cmd 默认 GBK 能正常显示中文，只有 ⚠ 这类非 GBK 字符会炸 → 故本函数一律用 ASCII 标记 "!!"。
    # （markdown_section 里的 ⚠️ 是写进 UTF-8 报告文件的，不受此限制。）
    force = "--force" in sys.argv
    by_ea, by_chart = chart_layout()
    print(f"[guard:{script}] 当前 chart→EA 实际盘面：")
    for c, ea in sorted(by_chart.items()):
        mark = "   <== 目标" if c == target_chart else ("   <== 模板" if c == template_chart else "")
        print(f"    {c}: {ea}{mark}")
    problems = []
    hit = by_ea.get(target_ea)
    if hit:
        problems.append(f"{target_ea} 已挂在 {hit} → 再挂即双挂（同 magic 互相覆盖台账/信号，见 T13）")
    owner = by_chart.get(target_chart)
    if owner and owner != target_ea:
        problems.append(f"{target_chart} 当前挂的是 {owner} → 继续会顶掉它")
    if template_chart:
        towner = by_chart.get(template_chart)
        if towner != template_ea:
            problems.append(f"模板假设 {template_chart}={template_ea}，实测={towner or '无 EA'} → chart 编号已漂移")
    if not problems:
        print(f"[guard:{script}] 盘面与脚本假设一致，放行")
        return
    for p in problems:
        print(f"[guard:{script}] !! {p}")
    if force:
        print(f"[guard:{script}] --force 已给出：视为你已核对实际盘面，继续（风险自负）")
        return
    raise SystemExit(
        f"[abort:{script}] 上述 {len(problems)} 项与脚本内硬编码假设冲突，已中止（未改任何文件/终端）。\n"
        f"  处置：①目标 EA 若已在跑，通常无需重跑本脚本；②确需重挂，先在终端手工摘除旧实例，"
        f"或把脚本改为按 EA 名动态定位 chart；③明知风险仍要跑：加 --force。\n"
        f"  依据：00_README T20 ／ 00_文档中心\\问题记录.md §二十三 补充取证二4。")


def check_ledgers() -> dict[str, str]:
    """台账可读性体检：ok / header_only / PermissionError / missing / n_rows。"""
    res = {}
    for name in LEDGER_FILES:
        p = FILES_DIR / name
        if not p.exists():
            res[name] = "missing"
            continue
        try:
            with p.open(encoding="utf-8", errors="replace", newline="") as fh:
                rows = list(csv.reader(fh))
        except PermissionError:
            res[name] = "PermissionError(EA 独占句柄，缺 FILE_SHARE_READ)"
            continue
        except Exception as e:
            res[name] = f"读取失败:{type(e).__name__}"
            continue
        data = [r for r in rows[1:] if any((c or "").strip() for c in r)]
        res[name] = "header_only(0 数据行)" if not data else f"ok({len(data)} 行)"
    return res


def markdown_section(attr: dict, gates: list[dict], ledgers: dict[str, str]) -> str:
    """生成监控报告里的「真实成交归因」节（血缘口径，两层粒度）。"""
    t = attr["totals"]
    ln = ["### 真实成交归因（MT5 账户血缘口径，服务器时间）", ""]
    ln.append(f"- 成交 {t['deals']} 笔 / 持仓 {t['positions']} 个 ｜ **已实现盈亏 ${t['realized']:+,.2f}** "
              f"｜ 入金等账务 ${t['deposits']:+,.2f} ｜ 合计应为 balance ${t['balance_expected']:,.2f}")
    ln.append(f"- 开平 magic 错配：**{t['mismatched_positions']} 个持仓 / {t['mismatched_closes']} 笔平仓**"
              f"（故盈亏按开仓方归因，不按 deal.magic，也不用 deal.reason）")
    if t["unknown_magics"]:
        ln.append(f"- ⚠️ 未登记 magic：{t['unknown_magics']}（需补 EA_MAGIC_MAP）")
    ln += ["", "**按 EA 汇总**", "",
           "| EA | 分支 | magic | 持仓 | 已平 | 未平 | 已实现USD | 错配 | 平仓类型 |",
           "|---|---|---|---:|---:|---:|---:|---:|---|"]
    for e in sorted(attr["per_ea"].values(), key=lambda x: -x["realized"]):
        bx = ",".join(f"{k}×{v}" for k, v in sorted(e["by_exit"].items())) or "-"
        ln.append(f"| {e['ea']} | {e['branches']} | {e['magics']} | {e['positions']} | {e['closed']} | "
                  f"{e['still_open']} | {e['realized']:+,.2f} | {e['mismatched']} | {bx} |")
    ln += ["", "**按 magic 明细（精确归因粒度；stage/多空在此才分得开）**", "",
           "| magic | EA | 分支 | 持仓 | 已平 | 已实现USD | 错配 |",
           "|---:|---|---|---:|---:|---:|---:|"]
    for m in sorted(attr.get("per_magic", {}).values(),
                    key=lambda x: (x["magic"] is None, x["magic"])):
        ln.append(f"| {m['magic']} | {m['ea']} | {m['branch']} | {m['positions']} | "
                  f"{m['closed']} | {m['realized']:+,.2f} | {m['mismatched']} |")
    ln.append("")
    live = [g for g in gates if g["live_trading"]]
    ln.append(f"- 终端实参（chart*.chr）：**{len(gates)} 个实例，其中 {len(live)} 个双闸放开在真下单**："
              + "、".join(f"{g['ea']}({g['chart']},magic={g['magic']})" for g in live))
    idle = sorted({g["ea"] for g in live} - set(attr["per_ea"]))
    if idle:
        ln.append(f"- ⚠️ 下单闸已放开但窗口内无成交：{', '.join(idle)}（一旦出信号即真下单，不是"
                  f"只读监控）")
    dup = [g for g in gates if g["duplicate"]]
    if dup:
        ln.append("- ⚠️ 同一 EA 挂多张图表（双挂，台账/信号文件会互相覆盖）："
                  + "、".join(f"{g['ea']}→{g['chart']}" for g in dup))
    bad = {k: v for k, v in ledgers.items() if not v.startswith("ok")}
    if bad:
        ln.append("- ⚠️ 台账不可用：" + "；".join(f"{k}={v}" for k, v in sorted(bad.items())))
    return "\n".join(ln)


def snapshot() -> dict:
    """一次取全（供监控调用）。MT5 不可用时返回带 error 的降级结构，不静默。"""
    skipped: list = []
    mt5, err = _connect()
    if mt5 is None:
        return {"error": err, "per_ea": {}, "totals": {}, "gates": [],
                "ledgers": check_ledgers(), "charts_skipped": skipped}
    try:
        deals = fetch_deals(mt5)
        attr = attribute_by_lineage(deals)
    finally:
        mt5.shutdown()
    charts = read_chart_params(collect_skipped=skipped)
    attr["gates"] = trading_gate(charts)
    attr["ledgers"] = check_ledgers()
    attr["charts"] = charts
    attr["charts_skipped"] = skipped
    return attr


def main() -> None:
    """独立运行＝自校验：与 §二十三 已确证的数字对账（578.15 / 15 / 9 实例 / 6 真下单）。"""
    import sys
    # cmd 默认 GBK，报告里的 ⚠ 等字符会炸；本模块输出统一 UTF-8（与其余 scripts 一致）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = snapshot()
    if s.get("error"):
        print("[live_attribution] 降级：", s["error"])
        print("台账体检：")
        for k, v in sorted(s["ledgers"].items()):
            print(f"  {k}: {v}")
        return
    t = s["totals"]
    print(f"deals={t['deals']} positions={t['positions']} realized={t['realized']:+.2f} "
          f"deposits={t['deposits']:+.2f} balance_expected={t['balance_expected']:.2f}")
    print(f"mismatched: positions={t['mismatched_positions']} closes={t['mismatched_closes']}")
    print(f"unknown magics: {t['unknown_magics']}")
    live = [g for g in s["gates"] if g["live_trading"]]
    print(f"实例 {len(s['gates'])} 个，真下单 {len(live)} 个: " + ", ".join(g["ea"] + "(" + g["chart"] + ")" for g in live))
    dup = [g for g in s["gates"] if g["duplicate"]]
    print(f"双挂: {[(g['ea'], g['chart']) for g in dup]}")
    if s.get("charts_skipped"):
        print("未识别/跳过的 .chr:", s["charts_skipped"])
    print("台账:", {k: v for k, v in sorted(s["ledgers"].items())})
    print()
    print(markdown_section(s, s["gates"], s["ledgers"]))
    print()
    print("=== 对账断言（§二十三 已确证值）===")
    checks = [
        ("已实现盈亏 == 578.15", abs(t["realized"] - 578.15) < 0.01, t["realized"]),
        ("入金 == 2089.46", abs(t["deposits"] - 2089.46) < 0.01, t["deposits"]),
        ("balance == 2667.61", abs(t["balance_expected"] - 2667.61) < 0.01, t["balance_expected"]),
        ("错配持仓 == 15", t["mismatched_positions"] == 15, t["mismatched_positions"]),
        ("错配平仓 == 15", t["mismatched_closes"] == 15, t["mismatched_closes"]),
        ("无未登记 magic", not t["unknown_magics"], t["unknown_magics"]),
        ("图表实例 == 9", len(s["gates"]) == 9, len(s["gates"])),
        ("真下单实例 == 6", len(live) == 6, len(live)),
        ("30m2H_ABC_EA 双挂被识别", len(dup) == 2, [(g["ea"], g["chart"]) for g in dup]),
        ("EA 汇总 == magic 明细 == 总盈亏",
         abs(t["per_ea_sum"] - t["realized"]) < 0.01 and abs(t["per_magic_sum"] - t["realized"]) < 0.01,
         f"ea={t['per_ea_sum']} magic={t['per_magic_sum']} total={t['realized']}"),
    ]
    bad = 0
    for name, ok, got in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  (实测 {got})")
        bad += 0 if ok else 1
    print(f"结论: {'全部通过' if bad == 0 else str(bad) + ' 项不符 —— 不得接入监控，先查根因'}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Generate a consolidated range-test dashboard for the 30m x 2H strategy."""
import os
import sys
import bisect
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _pre_cross_range_test as pct
import _stage3_exit_compare as s3
from _h2_context import load_h2_context


DASHBOARD_PATH = os.path.join(ROOT, "30m2H策略", "参数范围测试面板.md")

BASE = {
    "bias55": 3.0,
    "pre_gap": 0.003,
    "spec": (5, 35),
    "post": (2, 6),
    "top_pct": 30,
    "m15_filter": "close_side",
    "stage3": "m30_merged_cross",
}


def stat_line(s):
    return f"{s['n']} | {s['wr']:.1f}% | {s['pf']:.2f} | {s['ev']:+.2f}pt | ${s['pnl']:.0f} | {s['ml']}"


def stat_text(s):
    return f"{s['n']} 笔，WR {s['wr']:.1f}%，PF {s['pf']:.2f}，EV {s['ev']:+.2f}pt，PnL ${s['pnl']:.0f}，MaxCL {s['ml']}"


def stat_cells(s):
    return [s["n"], f"{s['wr']:.1f}%", f"{s['pf']:.2f}", f"{s['ev']:+.2f}pt", f"${s['pnl']:.0f}", s["ml"]]


def md_table(headers, rows):
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def set_globals(spec, post):
    pct.SPEC_LO, pct.SPEC_HI = spec
    pct.POST_N_MIN, pct.POST_N_MAX = post


def precompute_h2_custom(h2_df, m30_times, bias55_thr):
    h2_times = pd.to_datetime(h2_df["date"]).values.astype("datetime64[ns]")
    h2_close = h2_df["close"].values
    sma5 = h2_df["SMA_5"].values
    sma13 = h2_df["SMA_13"].values
    sma55 = h2_df["SMA_55"].values
    bias55 = np.where(
        ~np.isnan(sma55) & (sma55 != 0),
        (h2_close - sma55) / sma55 * 100,
        np.nan,
    )
    bias5 = np.where(
        ~np.isnan(sma5) & (sma5 != 0),
        abs((h2_close - sma5) / sma5 * 100),
        np.nan,
    )
    bias13 = np.where(
        ~np.isnan(sma13) & (sma13 != 0),
        abs((h2_close - sma13) / sma13 * 100),
        np.nan,
    )

    m30_t = pd.to_datetime(m30_times).values.astype("datetime64[ns]")
    pass_set = set()
    factor_map = {}
    for i, t in enumerate(m30_t):
        idx = bisect.bisect_right(h2_times, t) - 1
        if idx < 0 or pd.isna(bias55[idx]):
            continue
        if abs(bias55[idx]) > bias55_thr:
            pass_set.add(i)
        factor_map[i] = {
            "Bias_5": bias5[idx],
            "Bias_13": bias13[idx],
            "Bias_55": abs(bias55[idx]),
        }
    return pass_set, factor_map


def build_result(df, h2, m15, bias55, pre_gap, spec, post, top_pct, apply_m15=True):
    set_globals(spec, post)
    pass_set, factor_map = precompute_h2_custom(h2, df["date"].values, bias55)
    pre = pct.build_pre_cross(df, pre_gap, pass_set, factor_map)
    cross = pct.build_cross(df, pass_set, factor_map)
    post_trades = pct.build_post_n(df, pass_set, factor_map)
    all_modes = pct.dedupe(pre + cross + post_trades)
    if len(all_modes) > 0:
        thr = all_modes["Bias_5"].quantile(1 - top_pct / 100)
        top = all_modes[all_modes["Bias_5"] >= thr].reset_index(drop=True)
    else:
        top = all_modes.iloc[0:0].copy()
    final = pct.apply_m15_close_side(top, m15) if apply_m15 else top
    return all_modes, top, final


def scan_axis(df, h2, m15, axis_name, values, make_params, format_value, min_best_n=50):
    rows = []
    best = None
    for v in values:
        params = {**BASE, **make_params(v)}
        _, _, final = build_result(
            df,
            h2,
            m15,
            bias55=params["bias55"],
            pre_gap=params["pre_gap"],
            spec=params["spec"],
            post=params["post"],
            top_pct=params["top_pct"],
            apply_m15=True,
        )
        s = pct.stats(final)
        formatted_value = format_value(v)
        rows.append([formatted_value, *stat_cells(s)])
        eligible = s["n"] >= min_best_n
        key = (1 if eligible else 0, s["pf"], s["ev"], s["pnl"], s["n"])
        if best is None or key > best[0]:
            best = (key, v, formatted_value, s)
    return {
        "axis": axis_name,
        "rows": rows,
        "best_raw_value": best[1],
        "best_value": best[2],
        "best_stats": best[3],
    }


def stage3_rows(m15):
    df, h2, signals = s3.build_signals(apply_m15=False)
    signals = pct.apply_m15_close_side(signals, m15)
    rows = []
    best = None
    for variant in ["m30_raw_cross", "m30_merged_cross", "h2_raw_cross", "h2_merged_flip"]:
        out = s3.summarize_variant(df, h2, signals, variant)
        total = s3.metric(out["total_points"].values)
        stage3 = s3.metric(out["stage3_pnl"].values)
        rows.append([
            variant,
            f"{total['wr']:.1f}%",
            f"{total['pf']:.2f}",
            f"{total['ev']:+.2f}pt",
            f"{total['pnl']:+.0f}pt",
            f"{stage3['wr']:.1f}%",
            f"{stage3['pf']:.2f}",
            f"{stage3['ev']:+.2f}pt",
            f"{stage3['pnl']:+.0f}pt",
            total["ml"],
        ])
        key = (total["pf"], total["ev"], total["pnl"])
        if best is None or key > best[0]:
            best = (key, variant, total, stage3)
    return rows, best


def main():
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()
    m15 = pct.load_m15_filter_context()

    _, base_top_pre_m15, base_top_m15 = build_result(
        df,
        h2,
        m15,
        bias55=BASE["bias55"],
        pre_gap=BASE["pre_gap"],
        spec=BASE["spec"],
        post=BASE["post"],
        top_pct=BASE["top_pct"],
        apply_m15=True,
    )
    base_pre_stats = pct.stats(base_top_pre_m15)
    base_m15_stats = pct.stats(base_top_m15)

    scans = [
        scan_axis(
            df, h2, m15,
            "Layer 1 Bias_55 threshold",
            [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.2, 3.4, 3.5, 3.6, 3.8, 4.0, 4.5, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0],
            lambda v: {"bias55": v},
            lambda v: f"{v:.1f}%",
        ),
        scan_axis(
            df, h2, m15,
            "pre_cross gap threshold",
            [0.0002, 0.0005, 0.0010, 0.0015, 0.0020, 0.0030, 0.0050, 0.0080, 0.0100],
            lambda v: {"pre_gap": v},
            lambda v: f"{v * 100:.3f}%",
        ),
        scan_axis(
            df, h2, m15,
            "stop spec range",
            [(3, 35), (5, 35), (5, 50), (5, 80), (5, 100), (3, 50)],
            lambda v: {"spec": v},
            lambda v: f"[{v[0]}, {v[1]}]",
        ),
        scan_axis(
            df, h2, m15,
            "post_n range",
            [(2, 3), (2, 4), (2, 5), (2, 6), (2, 8), (3, 6), (3, 8), (4, 6), (4, 8)],
            lambda v: {"post": v},
            lambda v: f"{v[0]}-{v[1]}",
        ),
        scan_axis(
            df, h2, m15,
            "Layer 3 Bias_5 top pct",
            [10, 15, 20, 25, 30, 35, 40, 50, 60, 70],
            lambda v: {"top_pct": v},
            lambda v: f"top {v}%",
        ),
    ]

    stage_rows, stage_best = stage3_rows(m15)

    summary_rows = [
        ["Layer 1", "`Bias_55` threshold", "0.5%-15.0%", "3.0%", "已测", "当前采用 3.0%，加 M15 后仍优先保证样本量；更严格阈值只作为候选"],
        ["Layer 2", "`pre_cross` gap", "0.020%-1.000%", "0.300%", "已测并采用", "pre_cross 已正式加入当前方案；M15 过滤后当前主线为 54 笔 / PF 13.50"],
        ["Layer 2", "`pre_cross` 口径", "close vs high/low", "close 穿越", "已确认", "使用 close 穿越 SMA13，不采用 high/low 刺穿作为当前基准"],
        ["Layer 2", "`pre_cross` SL", "上一段 / 当前 / 附近 SMA13", "上一段 SMA13 极值", "已确认", "与 cross 的止损口径保持一致"],
        ["Layer 2", "`post_n` N 范围", "2-3 至 4-8", "2-6", "已测", "当前采用 2-6，兼顾数量、PF 和 MaxCL"],
        ["Layer 2", "stop spec", "[3,35] 至 [5,100]", "[5,35]", "已测", "当前偏保守，优先信号质量和止损规范"],
        ["Layer 3", "`Bias_5` top pct", "top10%-top70%", "top30%", "已测", "当前采用 top30%，在质量与数量之间折中"],
        ["Layer 4", "M15 close-side", "on/off", "启用", "已进入主策略候选", "LONG: M15 close > SMA13；SHORT: M15 close < SMA13"],
        ["退出", "Stage 1 R", "1.0R/1.2R/1.5R/2.0R", "1.2R", "待专项复测", "会影响第一段落袋为安"],
        ["退出", "Stage 2 trail/force", "2R/3R 及附近", "2R trail, 3R force", "待专项复测", "会影响第二段利润保护"],
        ["退出", "Stage 3 exit", "M30/H2 raw/merged", "研究推荐 m30_merged；EA 当前 m30_raw", "已测", "本面板已按 M15 后 54 笔主线信号复算"],
        ["执行", "总手数/分段", "0.03/0.06/0.12 等档位", "0.06 = 0.02x3", "待资金曲线复测", "风险控制层，不改变信号质量"],
    ]

    lines = []
    lines.append("# 参数范围测试面板")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("本面板用于集中展示策略中所有需要范围测试的部分。以后策略更新时，先更新这里，再同步主文档和 EA。")
    lines.append("")
    lines.append("说明：除“M15 加入前后对比”外，各参数扫描均已把 M15 close-side 作为主策略过滤层；“当前最佳”默认要求样本数不少于 50 笔，再按 PF、EV、PnL 排序；小样本高 PF 只作参考。")
    lines.append("")
    lines.append("注意：“当前最佳”是单轴扫描结果，不必然等于当前采用值；当前采用值以“当前基准口径”和“总览”为准。")
    lines.append("")
    lines.append("## 当前基准口径")
    lines.append("")
    lines.append(md_table(
        ["项目", "当前值"],
        [
            ["Layer 1", f"`|Bias_55| > {BASE['bias55']:.1f}%`"],
            ["Layer 2", "`pre_cross + cross + post_n`"],
            ["pre_cross 口径", "`close` 穿越 SMA13，SMA5 仍在另一侧"],
            ["pre_cross gap", "`<= 0.300%`"],
            ["pre_cross SL", "上一段 SMA13 极值"],
            ["post_n", "`2-6`"],
            ["stop spec", "`[5, 35] pt`"],
            ["Layer 3", "`Bias_5 top 30%`"],
            ["M15 过滤", "`m15_close_side`: 交易方向一侧的 M15 close / SMA13 确认"],
            ["当前主线结果", stat_text(base_m15_stats)],
            ["Stage 3", "研究推荐 `m30_merged_cross`；EA 当前实现 `m30_raw_cross`"],
        ],
    ))
    lines.append("")
    lines.append("## M15 加入前后对比")
    lines.append("")
    lines.append(md_table(
        ["口径", "笔数", "WR", "PF", "EV", "PnL", "MaxCL"],
        [
            ["Layer1+Layer2+Layer3，未加 M15", *stat_cells(base_pre_stats)],
            ["再加 M15 close-side", *stat_cells(base_m15_stats)],
        ],
    ))
    lines.append("")
    lines.append("结论：M15 close-side 不再作为旁路影子观察，已进入当前主策略候选。它过滤掉与 M15 SMA13 位置不一致的信号，在当前基准下得到 54 笔，WR 68.5%，PF 13.50，EV +43.78pt。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(md_table(["层级", "参数", "测试范围", "当前采用/候选", "状态", "备注"], summary_rows))
    lines.append("")

    for scan in scans:
        lines.append(f"## {scan['axis']}")
        lines.append("")
        lines.append(f"当前最佳(样本>=50): `{scan['best_value']}` -> {stat_line(scan['best_stats'])}")
        lines.append("")
        lines.append(md_table(["取值", "笔数", "WR", "PF", "EV", "PnL", "MaxCL"], scan["rows"]))
        if scan["axis"] == "Layer 1 Bias_55 threshold":
            lines.append("")
            lines.append("结论：`Bias_55` 阈值不是简单越大越好。阈值升高通常会提高单笔质量，但样本数会快速衰减；M15 过滤进入主策略后，当前基准仍采用 3.0%，更严格阈值只作为候选保留。")
        elif scan["axis"] == "post_n range":
            lines.append("")
            lines.append("结论：单轴最佳是 2-3，但样本低于 50；当前基准保留 2-6，因为加 M15 后仍有 54 笔，PnL 更高且 MaxCL 更低。")
        elif scan["axis"] == "Layer 3 Bias_5 top pct":
            lines.append("")
            lines.append("结论：top20 单轴质量更高，但样本低于 50；当前基准保留 top30，以维持 54 笔样本和更平衡的信号频率。")
        lines.append("")

    lines.append("## Stage 3 exit")
    lines.append("")
    lines.append(f"当前最佳: `{stage_best[1]}`")
    lines.append("")
    lines.append(md_table(
        ["退出方式", "总WR", "总PF", "总EV", "总PnL", "Stage3 WR", "Stage3 PF", "Stage3 EV", "Stage3 PnL", "MaxCL"],
        stage_rows,
    ))
    lines.append("")
    lines.append("结论：本表按加入 M15 后的当前主线信号复算。若 `m30_merged_cross` 仍保持优势，EA 后续应把 Stage 3 从当前 `m30_raw_cross` 对齐到 `m30_merged_cross`。")
    lines.append("")
    lines.append("## 待补专项测试")
    lines.append("")
    lines.append(md_table(
        ["参数", "建议范围", "原因"],
        [
            ["Stage 1 R", "1.0 / 1.2 / 1.5 / 2.0", "确认第一段止盈是否过早或过晚"],
            ["Stage 2 trail start", "1.5R / 2.0R / 2.5R", "确认何时启动 SMA13 移动止盈"],
            ["Stage 2 force close", "2.5R / 3.0R / 4.0R", "确认第二段强平是否限制大行情"],
            ["仓位档位", "0.03 / 0.06 / 0.12 起步与分段", "确认小账户回撤和成长速度"],
        ],
    ))
    lines.append("")
    lines.append("## 已确认项")
    lines.append("")
    lines.append(md_table(
        ["项目", "结论"],
        [
            ["pre_cross 是否加入", "已加入当前策略主线"],
            ["pre_cross 穿越口径", "采用 close 穿越 SMA13，不采用 high/low 刺穿作为当前基准"],
            ["pre_cross SL", "采用上一段 SMA13 极值"],
            ["三机会 + Layer3", "80 笔，WR 65.0%，PF 8.06，EV +33.27pt，PnL $2662，MaxCL 5"],
            ["M15 close-side 进入主策略", "54 笔，WR 68.5%，PF 13.50，EV +43.78pt，PnL $2364，MaxCL 5"],
        ],
    ))
    lines.append("")
    lines.append("## 复跑命令")
    lines.append("")
    lines.append("```powershell")
    lines.append("python scripts\\_strategy_range_dashboard.py")
    lines.append("python scripts\\_pre_cross_range_test.py")
    lines.append("python scripts\\_stage3_exit_compare.py")
    lines.append("```")
    lines.append("")

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()

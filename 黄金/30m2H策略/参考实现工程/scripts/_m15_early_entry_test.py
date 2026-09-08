# -*- coding: utf-8 -*-
"""Test M15 early-entry variants against the current 30m x 2H baseline."""
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
from processing.smma import calc_smma
import _pre_cross_range_test as pct
from _h2_context import load_h2_context


SPEC_LO = 5
SPEC_HI = 35
PRE_GAP = 0.003
RESULT_ROOT = os.path.join(ROOT, "data", "results", "m15_h2_early_trigger_20260626")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "M15_H2提前触发测试结果.md")
DETAIL_PATH = os.path.join(RESULT_ROOT, "m15_early_entry_detail.csv")

DIR_COL = "方向"
DIR_MERGED_COL = "方向_合并后"
POST_COL = "merged_post_cross_n"


def stats(tdf):
    out = pct.stats(tdf)
    if len(tdf) == 0:
        out["avg_sd"] = 0.0
        out["median_sd"] = 0.0
        return out
    out["avg_sd"] = float(tdf["sd"].mean())
    out["median_sd"] = float(tdf["sd"].median())
    return out


def stat_cells(s):
    return [
        s["n"],
        f"{s['wr']:.1f}%",
        f"{s['pf']:.2f}",
        f"{s['ev']:+.2f}pt",
        f"${s['pnl']:.0f}",
        s["ml"],
        f"{s['avg_sd']:.2f}",
        f"{s['median_sd']:.2f}",
    ]


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def load_m15(path="base_data/XAUUSDm15.csv", add_hours=0):  # 服务器=UTC
    m15 = pd.read_csv(path, encoding="gbk")
    m15.columns = [
        "date", "open", "high", "low", "close", "volume",
        "spread", "real_volume", "symbol", "time_diff",
    ]
    m15["date"] = pd.to_datetime(m15["date"]) + pd.Timedelta(hours=add_hours)
    m15 = m15.sort_values("date").reset_index(drop=True)
    m15["SMA_5"] = calc_smma(m15["close"], 5).values
    m15["SMA_13"] = calc_smma(m15["close"], 13).values
    return m15


def latest_m15_before(m15, anchor_time):
    if len(m15) == 0:
        return None
    times = pd.to_datetime(m15["date"]).values.astype("datetime64[ns]")
    idx = bisect.bisect_right(times, pd.Timestamp(anchor_time).to_datetime64()) - 1
    if idx < 0:
        return None
    return m15.iloc[idx]


def add_factor(row, factor_map):
    if row["anchor_i"] in factor_map:
        row.update(factor_map[row["anchor_i"]])
    return row


def make_trade(df, i, mode, is_long, entry, stop, exit_i, factor_map):
    sd = abs(entry - stop)
    path = df.iloc[i + 1 : exit_i + 1]
    hit = (path["low"] <= stop).any() if is_long else (path["high"] >= stop).any()
    pnl = (df.iloc[exit_i]["close"] - entry) if is_long else (entry - df.iloc[exit_i]["close"])
    if hit:
        pnl = -sd
    row = {
        "anchor_i": i,
        "i": i,
        "date": df.iloc[i]["date"],
        "entry_time": df.iloc[i]["date"],
        "mode": mode,
        "dir": "L" if is_long else "S",
        "entry": entry,
        "stop": stop,
        "sd": sd,
        "exit_i": exit_i,
        "won": pnl > 0,
        "pnl": pnl,
        "variant": "m30_base",
    }
    return add_factor(row, factor_map)


def collect_pre_cross_candidates(df, layer1_pass_set, factor_map):
    direction = df[DIR_COL].values
    direction_merged = df[DIR_MERGED_COL].values
    sma5 = df["SMA_5"].values
    sma13 = df["SMA_13"].values
    close = df["close"].values
    rows = []
    for i in range(1, len(df) - 1):
        if i not in layer1_pass_set:
            continue
        if any(pd.isna(x) for x in (sma5[i], sma13[i], sma13[i - 1], close[i], close[i - 1])):
            continue
        if direction[i] in ("good", "bad"):
            continue
        gap = abs(sma5[i] - sma13[i]) / sma13[i]
        if gap > PRE_GAP:
            continue
        long_setup = close[i - 1] <= sma13[i - 1] and close[i] > sma13[i] and sma5[i] < sma13[i]
        short_setup = close[i - 1] >= sma13[i - 1] and close[i] < sma13[i] and sma5[i] > sma13[i]
        if not (long_setup or short_setup):
            continue
        is_long = long_setup
        entry = close[i]
        stop = pct.prior_segment_stop(i, is_long, direction, sma13)
        if pd.isna(stop):
            continue
        if is_long and stop >= entry:
            continue
        if (not is_long) and stop <= entry:
            continue
        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction_merged[j] != opp:
            j += 1
        # v3.36: 出场搜索失败不再丢弃 — EA 实时无法前瞻 (look-ahead)。
        # EA 语义: stage3 出场 = M30 merged cross, 永不翻转则持仓到数据末尾。
        if j >= len(df):
            j = len(df) - 1
        row = make_trade(df, i, "pre_cross", is_long, entry, stop, j, factor_map)
        row["gap"] = gap
        row["spec_pass"] = SPEC_LO <= row["sd"] <= SPEC_HI
        row["spec_reason"] = "ok" if row["spec_pass"] else ("too_wide" if row["sd"] > SPEC_HI else "too_tight")
        rows.append(row)
    return rows


def collect_cross_candidates(df, layer1_pass_set, factor_map, ea_mode=False):
    direction = df[DIR_COL].values
    sma13 = df["SMA_13"].values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    rows = []
    for i in range(len(df)):
        if i not in layer1_pass_set:
            continue
        d = direction[i]
        if d not in ("good", "bad") or pd.isna(sma13[i]):
            continue
        is_long = d == "good"
        # v3.36: EA 可执行口径 — EA 市价入场无法复刻典型价, 用 close 对齐
        # (spec 检查与 M30 close proxy 一致); 传统口径保留 (high+low+close)/3
        entry = close[i] if ea_mode else (high[i] + low[i] + close[i]) / 3.0
        stop = pct.prior_segment_stop(i, is_long, direction, sma13)
        if pd.isna(stop):
            continue
        if is_long and stop >= entry:
            continue
        if (not is_long) and stop <= entry:
            continue
        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction[j] != opp:
            j += 1
        # v3.36: 出场搜索失败不再丢弃 (EA 实时无前瞻)
        if j >= len(df):
            j = len(df) - 1
        row = make_trade(df, i, "cross", is_long, entry, stop, j, factor_map)
        row["spec_pass"] = SPEC_LO <= row["sd"] <= SPEC_HI
        row["spec_reason"] = "ok" if row["spec_pass"] else ("too_wide" if row["sd"] > SPEC_HI else "too_tight")
        rows.append(row)
    return rows


def collect_post_candidates(df, layer1_pass_set, factor_map):
    direction_merged = df[DIR_MERGED_COL].values
    post_n = df[POST_COL].values
    sma13 = df["SMA_13"].values
    close = df["close"].values
    rows = []
    for i in range(len(df)):
        if i not in layer1_pass_set:
            continue
        pn = post_n[i]
        if abs(pn) < pct.POST_N_MIN or abs(pn) > pct.POST_N_MAX:
            continue
        is_long = pn > 0
        entry = close[i]
        stop = sma13[i]
        if pd.isna(entry) or pd.isna(stop):
            continue
        if is_long and stop >= entry:
            continue
        if (not is_long) and stop <= entry:
            continue
        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction_merged[j] != opp:
            j += 1
        # v3.36: 出场搜索失败不再丢弃 (EA 实时无前瞻)
        if j >= len(df):
            j = len(df) - 1
        row = make_trade(df, i, f"post_n{abs(pn)}", is_long, entry, stop, j, factor_map)
        row["spec_pass"] = SPEC_LO <= row["sd"] <= SPEC_HI
        row["spec_reason"] = "ok" if row["spec_pass"] else ("too_wide" if row["sd"] > SPEC_HI else "too_tight")
        rows.append(row)
    return rows


def priority(mode):
    if mode == "pre_cross":
        return 0
    if mode == "cross":
        return 1
    return 2


def dedupe_anchor(trades):
    if not trades:
        return pd.DataFrame()
    tdf = pd.DataFrame(trades).copy()
    tdf["_pri"] = tdf["mode"].map(priority)
    tdf = tdf.sort_values(["anchor_i", "dir", "_pri", "entry_time"])
    tdf = tdf.drop_duplicates(subset=["anchor_i", "dir"], keep="first")
    return tdf.drop(columns=["_pri"]).reset_index(drop=True)


def layer3_top(tdf):
    if len(tdf) <= 30 or "Bias_5" not in tdf:
        return tdf.iloc[0:0].copy()
    thr = tdf["Bias_5"].quantile(1 - pct.BIAS_5_TOP_PCT / 100.0)
    return tdf[tdf["Bias_5"] >= thr].reset_index(drop=True)


def m15_window(m15, anchor_time):
    start = anchor_time - pd.Timedelta(minutes=30)
    seg = m15[(m15["date"] > start) & (m15["date"] <= anchor_time)].copy()
    return seg.sort_values("date").reset_index(drop=True)


def m15_same_side(m15_row, is_long):
    if pd.isna(m15_row["SMA_13"]):
        return False
    if is_long:
        return m15_row["close"] > m15_row["SMA_13"]
    return m15_row["close"] < m15_row["SMA_13"]


def choose_half1(seg, is_long, stop):
    if len(seg) == 0:
        return None
    row = seg.iloc[0]
    entry = float(row["close"])
    sd = abs(entry - stop)
    if is_long and entry <= stop:
        return None
    if (not is_long) and entry >= stop:
        return None
    if not m15_same_side(row, is_long):
        return None
    if not (SPEC_LO <= sd <= SPEC_HI):
        return None
    return row


def choose_slot1(seg, is_long, stop):
    if len(seg) == 0:
        return None
    row = seg.iloc[0]
    entry = float(row["close"])
    sd = abs(entry - stop)
    if is_long and entry <= stop:
        return None
    if (not is_long) and entry >= stop:
        return None
    if not m15_same_side(row, is_long):
        return None
    if not (SPEC_LO <= sd <= SPEC_HI):
        return None
    return row


def choose_slot1_by_distance(seg, is_long, stop):
    if len(seg) == 0:
        return None
    row = seg.iloc[0]
    entry = float(row["close"])
    sd = abs(entry - stop)
    if not m15_same_side(row, is_long):
        return None
    if not (SPEC_LO <= sd <= SPEC_HI):
        return None
    return row


def choose_any(seg, is_long, stop):
    for _, row in seg.iterrows():
        entry = float(row["close"])
        sd = abs(entry - stop)
        if is_long and entry <= stop:
            continue
        if (not is_long) and entry >= stop:
            continue
        if not m15_same_side(row, is_long):
            continue
        if SPEC_LO <= sd <= SPEC_HI:
            return row
    return None


def stop_hit_in_remainder(m15, entry_time, anchor_time, is_long, stop):
    seg = m15[(m15["date"] > entry_time) & (m15["date"] <= anchor_time)]
    if len(seg) == 0:
        return False
    if is_long:
        return bool((seg["low"] <= stop).any())
    return bool((seg["high"] >= stop).any())


def recalc_trade(trade, entry_time, entry_price, variant, m15, reanchor_stop_by_distance=False):
    out = trade.copy()
    out["entry_time"] = entry_time
    out["entry"] = float(entry_price)
    intended_dist = abs(out["entry"] - out["stop"])
    if reanchor_stop_by_distance:
        is_long = out["dir"] == "L"
        out["stop"] = out["entry"] - intended_dist if is_long else out["entry"] + intended_dist
    out["sd"] = abs(out["entry"] - out["stop"])
    out["spec_pass"] = SPEC_LO <= out["sd"] <= SPEC_HI
    out["spec_reason"] = "ok" if out["spec_pass"] else ("too_wide" if out["sd"] > SPEC_HI else "too_tight")
    out["variant"] = variant
    out["pnl"] = np.nan
    out["won"] = False
    return out


def finalize_trade(df, trade, m15):
    is_long = trade["dir"] == "L"
    stop = float(trade["stop"])
    if stop_hit_in_remainder(m15, pd.Timestamp(trade["entry_time"]), pd.Timestamp(trade["date"]), is_long, stop):
        trade["pnl"] = -trade["sd"]
        trade["won"] = False
        return trade

    path = df.iloc[int(trade["anchor_i"]) + 1 : int(trade["exit_i"]) + 1]
    hit = (path["low"] <= stop).any() if is_long else (path["high"] >= stop).any()
    if hit:
        trade["pnl"] = -trade["sd"]
        trade["won"] = False
        return trade

    exit_px = float(df.iloc[int(trade["exit_i"])]["close"])
    pnl = (exit_px - trade["entry"]) if is_long else (trade["entry"] - exit_px)
    trade["pnl"] = pnl
    trade["won"] = pnl > 0
    return trade


def apply_replace_variant(base_top, m15, chooser, variant_name, require_earlier=False, reanchor_stop_by_distance=False):
    rows = []
    changed = 0
    for _, trade in base_top.iterrows():
        row = trade.to_dict()
        seg = m15_window(m15, trade["date"])
        chosen = chooser(seg, trade["dir"] == "L", float(trade["stop"]))
        if chosen is None:
            row["variant"] = variant_name
            row["entry_time"] = trade["date"]
            rows.append(finalize_trade(df_global, row, m15))
            continue
        chosen_time = pd.Timestamp(chosen["date"])
        if require_earlier and chosen_time >= pd.Timestamp(trade["date"]):
            row["variant"] = variant_name
            row["entry_time"] = trade["date"]
            rows.append(finalize_trade(df_global, row, m15))
            continue
        row = recalc_trade(
            row,
            chosen_time,
            float(chosen["close"]),
            variant_name,
            m15,
            reanchor_stop_by_distance=reanchor_stop_by_distance,
        )
        row = finalize_trade(df_global, row, m15) if pd.isna(row["pnl"]) else row
        changed += int(chosen_time != pd.Timestamp(trade["date"]) or abs(float(chosen["close"]) - float(trade["entry"])) > 1e-9)
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.reset_index(drop=True), changed


def build_rescued_trades(rejected, m15, chooser, variant_name="m15_rescue_stop", reanchor_stop_by_distance=False):
    rows = []
    rescue_count = 0
    for _, trade in rejected.iterrows():
        seg = m15_window(m15, trade["date"])
        chosen = chooser(seg, trade["dir"] == "L", float(trade["stop"]))
        if chosen is None:
            continue
        row = trade.to_dict()
        row = recalc_trade(
            row,
            pd.Timestamp(chosen["date"]),
            float(chosen["close"]),
            variant_name,
            m15,
            reanchor_stop_by_distance=reanchor_stop_by_distance,
        )
        row = finalize_trade(df_global, row, m15) if pd.isna(row["pnl"]) else row
        rows.append(row)
        rescue_count += 1
    out = pd.DataFrame(rows)
    return out, rescue_count


def coverage_mask(tdf, start_time):
    return pd.to_datetime(tdf["date"]) >= start_time


def split_stats(tdf, split_date=pd.Timestamp("2023-01-01")):
    train = tdf[pd.to_datetime(tdf["entry_time"]) < split_date]
    test = tdf[pd.to_datetime(tdf["entry_time"]) >= split_date]
    return stats(train), stats(test)


def report_rows(variant_name, tdf, notes):
    s = stats(tdf)
    train_s, test_s = split_stats(tdf)
    return [
        variant_name,
        *stat_cells(s),
        train_s["n"],
        test_s["n"],
        f"{test_s['pf']:.2f}",
        f"{test_s['ev']:+.2f}pt",
        notes,
    ]


def main():
    global df_global
    df_global, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()
    m15 = load_m15()
    m15_start = pd.Timestamp(m15["date"].min())

    layer1_pass_set, factor_map = pct.precompute_h2(h2, df_global["date"].values)
    raw = (
        collect_pre_cross_candidates(df_global, layer1_pass_set, factor_map)
        + collect_cross_candidates(df_global, layer1_pass_set, factor_map)
        + collect_post_candidates(df_global, layer1_pass_set, factor_map)
    )
    raw_df = pd.DataFrame(raw)

    accepted = dedupe_anchor([r for r in raw if r["spec_pass"]])
    accepted_cov = accepted[coverage_mask(accepted, m15_start)].reset_index(drop=True)
    accepted_cov_top = layer3_top(accepted_cov)

    base_cov = accepted_cov_top
    replace_half1, changed_half1 = apply_replace_variant(base_cov, m15, choose_half1, "m15_replace_half1", require_earlier=True)
    replace_any, changed_any = apply_replace_variant(base_cov, m15, choose_any, "m15_replace_any")
    replace_any_cov, _ = apply_replace_variant(accepted_cov, m15, choose_any, "m15_replace_any", require_earlier=False)

    rejected_wide = raw_df[(~raw_df["spec_pass"]) & (raw_df["spec_reason"] == "too_wide") & coverage_mask(raw_df, m15_start)].copy()
    rescued, rescue_count = build_rescued_trades(rejected_wide, m15, choose_any)

    merged_rescue = dedupe_anchor(accepted_cov.to_dict("records") + rescued.to_dict("records"))
    merged_rescue_top = layer3_top(merged_rescue)

    merged_replace_rescue = dedupe_anchor(replace_any_cov.to_dict("records") + rescued.to_dict("records"))
    merged_replace_rescue_top = layer3_top(merged_replace_rescue)

    os.makedirs(RESULT_ROOT, exist_ok=True)
    detail_frames = []
    for name, frame in [
        ("baseline_m15_coverage", base_cov),
        ("m15_replace_half1", replace_half1),
        ("m15_replace_any", replace_any),
        ("m15_rescue_merged", merged_rescue_top),
        ("m15_replace_any_plus_rescue", merged_replace_rescue_top),
        ("rescued_raw", rescued),
    ]:
        if len(frame) == 0:
            continue
        tmp = frame.copy()
        tmp["report_variant"] = name
        detail_frames.append(tmp)
    if detail_frames:
        pd.concat(detail_frames, ignore_index=True).to_csv(DETAIL_PATH, index=False, encoding="utf-8-sig")

    rows = [
        report_rows("baseline_m15_coverage", base_cov, f"coverage from {m15_start:%Y-%m-%d %H:%M}"),
        report_rows("m15_replace_half1", replace_half1, f"changed {changed_half1} trades"),
        report_rows("m15_replace_any", replace_any, f"changed {changed_any} trades"),
        report_rows("m15_rescue_merged", merged_rescue_top, f"rescued raw {rescue_count}"),
        report_rows("m15_replace_any_plus_rescue", merged_replace_rescue_top, f"rescued raw {rescue_count}"),
    ]

    rescue_mode_rows = []
    if len(rescued) > 0:
        for mode, group in rescued.groupby("mode"):
            rescue_mode_rows.append([mode, *stat_cells(stats(group)), len(group)])

    lines = []
    lines.append("# M15 / H2 提前触发测试结果")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 第一轮：M15 early-entry")
    lines.append("")
    lines.append("这一轮先做保守版本：只测试同一根 M30 bar 内，用更早的 M15 close 替换 entry，或救回原本因为 stop spec 过宽而失败的机会。")
    lines.append("")
    lines.append(md_table(
        ["方案", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "avg_sd", "median_sd", "训练笔数", "验证笔数", "验证PF", "验证EV", "备注"],
        rows,
    ))
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append(f"- M15 覆盖期起点：`{m15_start:%Y-%m-%d %H:%M}`。因此所有 M15 early-entry 对比都基于 M15 覆盖期的基线子集，而不是 2018 全样本。")
    lines.append("- `m15_replace_half1`：只尝试同一根 M30 内前半根 M15。")
    lines.append("- `m15_replace_any`：在同一根 M30 内两根 M15 中，取最早满足条件且 stop spec 合格的一根。")
    lines.append("- `m15_rescue_merged`：只把原本 M30 进场 stop 过宽的候选，尝试用 M15 更早 close 救回。")
    lines.append("")
    if rescue_mode_rows:
        lines.append("## Rescue mode split")
        lines.append("")
        lines.append(md_table(
            ["mode", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "avg_sd", "median_sd", "rescued_count"],
            rescue_mode_rows,
        ))
        lines.append("")
    lines.append("## 当前判断")
    lines.append("")
    lines.append("- 如果 `replace` 方案主要改善 `avg_sd`，说明“过晚入场”问题是真实存在的。")
    lines.append("- 如果 `rescue` 方案能在 PF / EV 不明显恶化的前提下增加最终笔数，说明 M15 拆 M30 方向值得继续扩展。")
    lines.append("- 第二轮再决定是否继续做 `m15_add_pre_cross` 这类真正新增触发，而不是只做替换/救回。")
    lines.append("")
    lines.append("## 结果文件")
    lines.append("")
    lines.append(f"- `data\\results\\m15_h2_early_trigger_20260626\\{os.path.basename(DETAIL_PATH)}`")
    lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(md_table(
        ["方案", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "avg_sd", "median_sd", "训练笔数", "验证笔数", "验证PF", "验证EV", "备注"],
        rows,
    ))
    if rescue_mode_rows:
        print()
        print(md_table(
            ["mode", "笔数", "WR", "PF", "EV", "PnL", "MaxCL", "avg_sd", "median_sd", "rescued_count"],
            rescue_mode_rows,
        ))
    print()
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {DETAIL_PATH}")


if __name__ == "__main__":
    main()

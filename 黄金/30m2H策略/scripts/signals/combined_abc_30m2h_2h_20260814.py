# -*- coding: utf-8 -*-

"""Apply the 1H_M30_4H A+B+C combined logic to 30m2H and 2H_M30_6H.

Chain (same logic as the 1H experiment):
  A. M30 three opportunities (pre_cross / cross / post_n2-6) with
     previous-segment SMA13 extreme stops (post_n: current-bar SMA13),
     entry at next M30 open.
  Gate (strategy-native high-timeframe pool):
    30m2H: |H2 bias55| > 3.0%
    2H_M30_6H: 6H bias5+13+55 signed > 0
  C. High-timeframe bias5 same-direction magnitude filter (scanned).
    30m2H: |H2 bias5| >= thr and same sign as H2 bias55
    2H:     6H bias5 signed >= thr
  B. Three-stage exit 2.0R / 1.5R trail + 4.0R / M30 merged cross,
     stop spec scanned, 3% fixed-balance risk for the matrix,
     0.5%/1% compounding for the recommended combo.

Data: each strategy's own MT5 raw history; 30m2H 2018-2026 (signals from
2020-01-01), 2H refreshed to 2020-2026. Time alignment for gates uses the
same "last closed high-TF bar" convention as the 1H pipeline (no +2h shift).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)


import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    SPEC_5_35,
    add_m30_state,
    build_three_opportunities,
    markdown_table,
    metric,
    replay_three_stage,
    replay_signals,
    split_test,
    yearly_positive_count,
)
from replay_raw_signals_with_stops import (  # noqa: E402
    LOT_FOR_REPORT,
    add_indicators,
    attach_context,
    manifest_file,
    manifest_timeframe,
    read_json,
    standardize_mt5_csv,
)


STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
UNIT_SUM = 3.0
START_CAPITAL = 500.0
USD_PER_POINT_PER_LOT = 10.0
LOT_MIN = 0.01
LOT_MAX = 10.0
COSTS = [0.0, 0.5, 1.0, 1.5]
START_YEAR = 2020

STRATS = {
    "30m2H": {
        "strategy_dir": ROOT / "黄金" / "30m2H策略",
        "frames": ["M30", "H2"],
        "gate_tf": "H2",
        "gate_type": "abs_bias55_gt_3",
        "c_tf": "H2",
        "specs": [("5_35", SPEC_5_35)],
        "bias5_grid": [0.0, 0.2, 0.4, 0.6, 0.8],
    },
    "2H_M30_6H": {
        "strategy_dir": ROOT / "黄金" / "2H_M30_6H策略",
        "frames": ["M30", "H6"],
        "gate_tf": "H6",
        "gate_type": "bias5_55_pos",
        "c_tf": "H6",
        "specs": [("2_10", (2.0, 10.0)), ("5_35", SPEC_5_35)],
        "bias5_grid": [0.0, 0.2, 0.4, 0.6],
        "preferred": ("5_35", 0.0),
    },
}


def load_strategy(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = read_json(cfg["strategy_dir"] / "data" / "raw" / "raw_source_manifest.json")
    m30 = add_indicators(
        standardize_mt5_csv(manifest_file(manifest, "M30"), "30M", closed_time=False)
    )
    tf_label = str(cfg["gate_tf"])
    tf_hours_label = {"H2": "2H", "H6": "6H"}[tf_label]
    gate_tf = add_indicators(
        standardize_mt5_csv(
            manifest_file(manifest, manifest_timeframe(tf_label)),
            tf_hours_label,
            closed_time=True,
        )
    )
    return m30, gate_tf


R13_BAND_MIN = 3.0
R13_BAND_MAX = 5.0


def attach_r13_band(enriched: pd.DataFrame, gate_tf: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """附加 (SMA13-SMA55)/SMA55*100 (unsigned) 到每条信号对应的 gate_tf bar."""
    import bisect
    g = gate_tf.reset_index(drop=True)
    gt = pd.to_datetime(g["date"]).values.astype("datetime64[ns]")
    s13 = pd.to_numeric(g["SMA_13"], errors="coerce").values
    s55 = pd.to_numeric(g["SMA_55"], errors="coerce").values
    out = enriched.copy().reset_index(drop=True)
    times = pd.to_datetime(out["signal_time"]).values.astype("datetime64[ns]")
    vals = []
    for t in times:
        i = bisect.bisect_right(gt, t) - 1
        if i < 0 or not np.isfinite(s13[i]) or not np.isfinite(s55[i]) or s55[i] == 0:
            vals.append(np.nan)
        else:
            vals.append((s13[i] - s55[i]) / s55[i] * 100.0)
    out[f"{prefix}_r13_55_pct"] = vals
    return out


def gate_mask(enriched: pd.DataFrame, cfg: dict, bias5_thr: float) -> pd.Series:
    prefix = str(cfg["c_tf"]).lower()
    if cfg["gate_type"] == "abs_bias55_gt_3":
        b55 = pd.to_numeric(enriched[f"{prefix}_bias55_raw_pct"], errors="coerce")
        pool = b55.abs().gt(3.0)
        if bias5_thr > 0:
            b5 = pd.to_numeric(enriched[f"{prefix}_bias5_raw_pct"], errors="coerce")
            same_sign = (b55 > 0) & (b5 > 0) | (b55 < 0) & (b5 < 0)
            pool = pool & same_sign & b5.abs().ge(bias5_thr)
    else:  # bias5_55_pos: 6H bias5>0 AND bias55>0 (bias13 constraint dropped)
        pool = (
            pd.to_numeric(enriched[f"{prefix}_bias5_signed_pct"], errors="coerce").gt(0)
            & pd.to_numeric(enriched[f"{prefix}_bias55_signed_pct"], errors="coerce").gt(0)
        )
        if bias5_thr > 0:
            pool = pool & pd.to_numeric(
                enriched[f"{prefix}_bias5_signed_pct"], errors="coerce"
            ).ge(bias5_thr)
        # r13_55 结构带通 (2026-09-06 变体, 方向性, 与 EA Pass6HGate 一致):
        #   LONG: 3<=r13_55<=5 ; SHORT: -5<=r13_55<=-3
        r13 = enriched.get(f"{prefix}_r13_55_pct")
        if r13 is not None:
            rr = pd.to_numeric(r13, errors="coerce")
            side = enriched["dir"].astype(str).str.upper()
            pool = pool & (
                ((side == "L") & rr.between(R13_BAND_MIN, R13_BAND_MAX))
                | ((side == "S") & rr.between(-R13_BAND_MAX, -R13_BAND_MIN))
            )
    year = pd.to_datetime(enriched["signal_time"]).dt.year
    return pool & year.ge(START_YEAR)


def build_combo(enriched: pd.DataFrame, cfg: dict, bias5_thr: float) -> pd.DataFrame:
    mask = gate_mask(enriched, cfg, bias5_thr)
    trades = enriched.loc[mask].copy().reset_index(drop=True)
    trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
    return trades


def weighted_points(st: pd.DataFrame) -> pd.Series:
    return st["stage_pnl"].astype(float) * st["stage"].map(STAGE_UNITS)


def per_trade(st: pd.DataFrame, cost: float = 0.0) -> pd.DataFrame:
    st = st.copy()
    st["w"] = (st["stage_pnl"].astype(float) - cost) * st["stage"].map(STAGE_UNITS)
    per = st.groupby(["signal_time", "dir"], sort=True).agg(
        ts=("signal_time", "first"),
        w=("w", "sum"),
        stop=("stop_distance", "first"),
        mode=("mode", "first"),
    ).reset_index()
    per["ts"] = pd.to_datetime(per["ts"])
    per["year"] = per["ts"].dt.year
    return per


def summarize_combo(st: pd.DataFrame) -> dict:
    per = per_trade(st)
    m = metric(per["w"])
    test = split_test(per, "w")
    pos_years, total_years = yearly_positive_count(per, "w")
    side = per["dir"].astype(str).str.upper()
    return {
        "n": m["n"],
        "long_n": int(side.eq("L").sum()),
        "short_n": int(side.eq("S").sum()),
        "wr": m["wr"],
        "pf": m["pf"],
        "ev": m["ev"],
        "pnl_points": m["pnl"],
        "test_pf": test["test_pf"],
        "test_ev": test["test_ev"],
        "test_n": test["test_n"],
        "positive_years": pos_years,
        "total_years": total_years,
    }


def simulate_compounded(st: pd.DataFrame, risk_pct: float, cost: float = 0.0) -> pd.DataFrame:
    rows = []
    balance = START_CAPITAL
    peak = START_CAPITAL
    max_dd = 0.0
    for (signal_time, dir_), group in st.groupby(["signal_time", "dir"], sort=True):
        risk_usd = balance * risk_pct / 100.0
        pnl_usd = 0.0
        for _, r in group.iterrows():
            stop_pts = float(r["stop_distance"])
            if stop_pts <= 0 or not np.isfinite(stop_pts):
                continue
            unit_lot = risk_usd / (UNIT_SUM * stop_pts * USD_PER_POINT_PER_LOT)
            unit_lot = float(np.clip(unit_lot, LOT_MIN, LOT_MAX))
            lot = unit_lot * STAGE_UNITS[int(r["stage"])]
            pnl_usd += lot * (float(r["stage_pnl"]) - cost) * USD_PER_POINT_PER_LOT
        balance += pnl_usd
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append(
            {
                "signal_time": pd.Timestamp(signal_time),
                "dir": dir_,
                "pnl_usd": pnl_usd,
                "balance": balance,
                "max_dd_pct": max_dd / peak * 100.0 if peak > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def rolling_windows(per: pd.DataFrame, months: int) -> pd.DataFrame:
    scoped = per.copy()
    first = scoped["ts"].min().to_period("M").to_timestamp()
    last = scoped["ts"].max().to_period("M").to_timestamp()
    month_ends = pd.period_range(first, last, freq="M").to_timestamp()
    rows = []
    for end_start in month_ends:
        end_excl = end_start + pd.DateOffset(months=1)
        start = end_excl - pd.DateOffset(months=months)
        group = scoped.loc[(scoped["ts"] >= start) & (scoped["ts"] < end_excl)]
        if group.empty:
            continue
        m = metric(group["w"])
        rows.append(
            {
                "window_start": start.strftime("%Y-%m"),
                "window_end": end_start.strftime("%Y-%m"),
                "n": m["n"],
                "pf": m["pf"],
                "ev": m["ev"],
                "pnl_points": m["pnl"],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    for strategy, cfg in STRATS.items():
        out_dir = cfg["strategy_dir"] / "data" / "validation" / "experiments_20260814" / "combined_abc"
        out_dir.mkdir(parents=True, exist_ok=True)
        m30, gate_tf = load_strategy(cfg)
        m30_state = add_m30_state(m30)

        enriched_by_spec: dict[str, pd.DataFrame] = {}
        for spec_name, spec in cfg["specs"]:
            sig = build_three_opportunities(m30, spec_lo=spec[0], spec_hi=spec[1])
            replayed = replay_signals(sig, m30)
            enriched = attach_context(replayed, gate_tf, str(cfg["c_tf"]).lower())
            enriched_by_spec[spec_name] = enriched

        matrix_rows = []
        st_cache: dict[tuple[str, float], pd.DataFrame] = {}
        for spec_name, _ in cfg["specs"]:
            for bias5_thr in cfg["bias5_grid"]:
                trades = build_combo(enriched_by_spec[spec_name], cfg, bias5_thr)
                st = replay_three_stage(m30_state, trades)
                st_cache[(spec_name, bias5_thr)] = st
                s = summarize_combo(st)
                matrix_rows.append(
                    {
                        "spec": spec_name,
                        "bias5_thr": bias5_thr,
                        "desc": (
                            f"{'|H2 bias5|同向≥' if strategy == '30m2H' else '6H bias5 signed≥'}"
                            f"{bias5_thr:.1f}%"
                            + ("" if strategy == "30m2H" else " + bias55>0")
                        ),
                        **s,
                    }
                )
        matrix = pd.DataFrame(matrix_rows)
        matrix.to_csv(out_dir / "combined_matrix.csv", index=False, encoding="utf-8-sig")
        print(f"\n==== {strategy} combined matrix ====")
        print(
            matrix[["spec", "bias5_thr", "n", "long_n", "short_n", "wr", "pf", "ev",
                    "pnl_points", "test_pf", "positive_years", "total_years"]].to_string(index=False)
        )

        # ---- pick recommended: robust score = positive years + test PF + PF ----
        qual = matrix[(matrix["test_pf"] >= 1.0) & (matrix["n"] >= 50)]
        if qual.empty:
            qual = matrix[matrix["n"] >= 30]
        preferred = cfg.get("preferred")
        if preferred is not None:
            pre_mask = (matrix["spec"] == preferred[0]) & (
                matrix["bias5_thr"].sub(float(preferred[1])).abs() < 1e-9
            )
            if pre_mask.any():
                rec = matrix.loc[pre_mask].iloc[0]
            else:
                rec = qual.sort_values(["pf", "ev", "n"], ascending=[False, False, False]).iloc[0]
        else:
            sc = qual.copy()
            sc["_score"] = (
                sc["positive_years"] * 1000.0
                + sc["test_pf"] * 10.0
                + sc["pf"] * 5.0
                + sc["ev"] * 0.05
            )
            rec = sc.sort_values(["_score", "test_pf", "pf"], ascending=[False, False, False]).iloc[0]
        rec_key = (str(rec["spec"]), float(rec["bias5_thr"]))
        rec_st = st_cache[rec_key]
        print(f"recommended: spec={rec_key[0]} bias5={rec_key[1]:.1f} "
              f"n={rec['n']} pf={rec['pf']:.3f} test_pf={rec['test_pf']:.3f}")

        # ---- cost sensitivity ----
        cost_rows = []
        for cost in COSTS:
            per_c = per_trade(rec_st, cost)
            m_c = metric(per_c["w"])
            test_c = split_test(per_c, "w")
            pos_years_c, total_years_c = yearly_positive_count(per_c, "w")
            eq_c = simulate_compounded(rec_st, 3.0, cost=cost)
            cost_rows.append(
                {
                    "cost_pt_per_stage": cost,
                    "pf": m_c["pf"],
                    "test_pf": test_c["test_pf"],
                    "ev": m_c["ev"],
                    "final_balance_3pct": float(eq_c["balance"].iloc[-1]),
                    "positive_years": f"{pos_years_c}/{total_years_c}",
                }
            )
        cost_df = pd.DataFrame(cost_rows)
        cost_df.to_csv(out_dir / "recommended_cost_sensitivity.csv", index=False, encoding="utf-8-sig")

        # ---- rolling windows ----
        per0 = per_trade(rec_st)
        roll_rows = []
        for months in [6, 12]:
            roll = rolling_windows(per0, months)
            roll.to_csv(out_dir / f"recommended_rolling_{months}m.csv", index=False, encoding="utf-8-sig")
            if len(roll):
                worst = roll.sort_values("pnl_points").iloc[0]
                roll_rows.append(
                    {
                        "window_months": months,
                        "windows": int(len(roll)),
                        "positive_rate": float((roll["pnl_points"] > 0).mean() * 100.0),
                        "min_pnl": float(roll["pnl_points"].min()),
                        "median_pnl": float(roll["pnl_points"].median()),
                        "worst_window": f"{worst['window_start']}..{worst['window_end']}",
                        "worst_pnl": float(worst["pnl_points"]),
                    }
                )
        roll_df = pd.DataFrame(roll_rows)
        roll_df.to_csv(out_dir / "recommended_rolling_summary.csv", index=False, encoding="utf-8-sig")

        # ---- compounding risk frontier ----
        risk_rows = []
        for risk_pct in [0.5, 1.0, 2.0, 3.0]:
            eq = simulate_compounded(rec_st, risk_pct)
            risk_rows.append(
                {
                    "risk_pct": risk_pct,
                    "final_balance": float(eq["balance"].iloc[-1]),
                    "total_return_pct": (float(eq["balance"].iloc[-1]) / START_CAPITAL - 1.0) * 100.0,
                    "max_dd_pct": float(eq["max_dd_pct"].iloc[-1]),
                }
            )
        risk_df = pd.DataFrame(risk_rows)
        risk_df.to_csv(out_dir / "recommended_compounding_risk.csv", index=False, encoding="utf-8-sig")

        # ---- walk-forward ----
        wf_rows = []
        for train_end in [2023, 2022]:
            per_w = per0.copy()
            train = per_w[per_w["year"] <= train_end]
            test = per_w[per_w["year"] > train_end]
            if len(train) < 50 or len(test) == 0:
                continue
            m_tr = metric(train["w"])
            m_te = metric(test["w"])
            wf_rows.append(
                {
                    "train": f"2020-{train_end}",
                    "test": f"{train_end + 1}-2026",
                    "train_n": m_tr["n"],
                    "train_pf": m_tr["pf"],
                    "test_n": m_te["n"],
                    "test_pf": m_te["pf"],
                    "test_ev": m_te["ev"],
                    "test_pnl": m_te["pnl"],
                    "test_pos_years": f"{int((test.groupby('year')['w'].sum() > 0).sum())}/{len(test['year'].unique())}",
                }
            )
        wf_df = pd.DataFrame(wf_rows)
        wf_df.to_csv(out_dir / "recommended_walkforward.csv", index=False, encoding="utf-8-sig")

        # ---- yearly detail ----
        year_rows = []
        for year, g in per0.groupby("year", sort=True):
            m = metric(g["w"])
            side = g["dir"].astype(str).str.upper()
            year_rows.append(
                {
                    "year": int(year),
                    "n": m["n"],
                    "long_n": int(side.eq("L").sum()),
                    "short_n": int(side.eq("S").sum()),
                    "wr": m["wr"],
                    "pf": m["pf"],
                    "ev": m["ev"],
                    "pnl_points": m["pnl"],
                }
            )
        year_df = pd.DataFrame(year_rows)
        year_df.to_csv(out_dir / "recommended_yearly.csv", index=False, encoding="utf-8-sig")

        lines = [
            f"# {strategy} A+B+C 组合测试（2026-08-14）",
            "",
            "> 统一口径：三机会入场 + 段SMA13极值止损 + 下一根M30开盘入场 + 三段退出(2.0R/1.5R trail+4.0R/合并段反向) "
            "+ 高周期 bias5 同向过滤 + 3%固定余额风险(矩阵) / 0.5-3%复利(前沿)。",
            "> 与各策略原生回测的差异：未启用 M15/H2 early-gate/Layer3 top34/原生2H时间偏移；H2/H6 用收盘时间对齐。",
            "",
            "## 组合矩阵",
            "",
            markdown_table(
                matrix[["spec", "bias5_thr", "desc", "n", "long_n", "short_n", "wr", "pf", "ev",
                        "pnl_points", "test_pf", "test_ev", "positive_years", "total_years"]],
                ["spec", "bias5_thr", "desc", "n", "long_n", "short_n", "wr", "pf", "ev",
                 "pnl_points", "test_pf", "test_ev", "positive_years", "total_years"],
            ),
            "",
            f"## 推荐组合：{rec_key[0]} / bias5≥{rec_key[1]:.1f}%",
            "",
            "### 成本敏感性（每段往返）",
            "",
            markdown_table(cost_df, [str(c) for c in cost_df.columns], money_cols={"final_balance_3pct"}),
            "",
            "### 复利风险档位",
            "",
            markdown_table(risk_df, [str(c) for c in risk_df.columns], money_cols={"final_balance"}),
            "",
            "### 滚动窗口",
            "",
            markdown_table(roll_df, [str(c) for c in roll_df.columns]),
            "",
            "### Walk-forward",
            "",
            markdown_table(wf_df, [str(c) for c in wf_df.columns]),
            "",
            "### 年度明细",
            "",
            markdown_table(year_df, [str(c) for c in year_df.columns]),
        ]
        (out_dir / "combined_abc_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote report: {out_dir / 'combined_abc_report.md'}")


if __name__ == "__main__":
    main()

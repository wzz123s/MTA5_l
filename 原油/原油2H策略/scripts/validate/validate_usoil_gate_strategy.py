# -*- coding: utf-8 -*-
"""Independent full validation for each USOIL gate strategy (4H/6H/8H -> 2H).

Each strategy reads ONLY its own raw manifest and computes:
  data -> SMMA indicators -> way/vol_way -> 2H triggers (cross/pre_cross)
  -> 4H/6H/8H three-condition gate -> 2H structure stop (0.1-1.0%)
  -> metrics / walk-forward / rolling / yearly / cost sensitivity.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import bisect
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    build_three_opportunities,
    replay_signals,
)
from replay_raw_signals_with_stops import (  # noqa: E402
    add_indicators,
    manifest_file,
    read_json,
    standardize_mt5_csv,
)
from replay_1h_way_momentum_filter_scan import (  # noqa: E402
    add_way_grade,
    filter_short_segments,
    mark_direction,
)
from usoil_4h6h8h_strategies_20260815 import gate_arrays, markdown_table  # noqa: E402


PCT_LO, PCT_HI = 0.1, 1.0
STRATEGIES = {
    "原油4H门策略": {"gate_tf": "4H", "gate_src": "H4", "n_min": 8, "thr": 0.5, "amp": (0.5, 5.0)},
    "原油6H门策略": {"gate_tf": "6H", "gate_src": "H6", "n_min": 8, "thr": 0.5, "amp": (1.0, 8.0)},
    "原油8H门策略": {"gate_tf": "8H", "gate_src": None, "n_min": 12, "thr": 0.5, "amp": (1.0, 8.0)},
}
COSTS = [0.0, 0.02, 0.05, 0.10]


def load_2h(strategy_dir: Path) -> pd.DataFrame:
    manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
    frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H2"), "2H", closed_time=True))
    return frame.reset_index(drop=True)


def load_gate(strategy_dir: Path, cfg) -> pd.DataFrame:
    manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
    if cfg["gate_src"] is not None:
        label = {"4H": "4H", "6H": "6H"}[cfg["gate_tf"]]
        frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, cfg["gate_src"]), label, closed_time=True))
    else:  # 8H: resample M30
        m30 = standardize_mt5_csv(manifest_file(manifest, "M30"), "30M", closed_time=False).set_index("date")
        frame = (
            m30.resample("8h", label="right", closed="right")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                  "volume": "sum", "spread": "mean", "real_volume": "sum",
                  "symbol": "last", "time_diff": "last"})
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
        frame["bar_open_time"] = frame["date"] - pd.Timedelta(hours=8)
        frame["bar_close_time"] = frame["date"]
        frame = add_indicators(frame)
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    return add_way_grade(filter_short_segments(mark_direction(frame), min_len=8)).reset_index(drop=True)


def build_triggers(tf2: pd.DataFrame) -> pd.DataFrame:
    sig = build_three_opportunities(tf2, spec_lo=0.001, spec_hi=100.0)
    replayed = replay_signals(sig, tf2)
    replayed["stop_pct"] = (
        pd.to_numeric(replayed["stop_distance"], errors="coerce")
        / pd.to_numeric(replayed["entry"], errors="coerce")
        * 100.0
    )
    trig = replayed.loc[replayed["stop_pct"].between(PCT_LO, PCT_HI)].copy()
    trig = trig.loc[~trig["mode"].str.startswith("post_n")].copy()  # post_n rejected on 2H
    return trig.reset_index(drop=True)


def gate_check(gt, n_min, thr, amp_lo, amp_hi):
    times = pd.to_datetime(gt["bar_close_time"]).values.astype("datetime64[ns]")
    d, sl, w, v, amp = gate_arrays(gt)

    def check(t, need_long):
        idx = bisect.bisect_right(times, pd.Timestamp(t).to_datetime64()) - 1
        if idx < 0:
            return False
        if need_long:
            # BUG 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1], LONG gate 应判 >= 阈值(强势下跌)
            ok = d[idx] == -1 and sl[idx] >= n_min and w[idx] >= thr and v[idx] >= thr
        else:
            ok = d[idx] == 1 and sl[idx] >= n_min and w[idx] >= thr and v[idx] >= thr
        return ok and np.isfinite(amp[idx]) and amp_lo <= amp[idx] <= amp_hi

    return check


def metrics(pnl: pd.Series) -> dict:
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gw = wins.sum()
    gl = abs(losses.sum())
    return {
        "n": int(len(pnl)),
        "wr": float((pnl > 0).mean() * 100.0),
        "pf": float(gw / gl if gl > 0 else (999.0 if gw > 0 else 0.0)),
        "ev": float(pnl.mean()),
        "pnl": float(pnl.sum()),
    }


def test_pf(pnl: pd.Series, ts: pd.Series) -> float:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl}).sort_values("ts").reset_index(drop=True)
    cutoff_idx = min(max(int(len(df) * 0.70), 1), len(df) - 1)
    cutoff = df.loc[cutoff_idx, "ts"]
    test = df.loc[df["ts"] >= cutoff, "pnl"]
    tw = test[test > 0]
    tl = test[test < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def range_pf(pnl: pd.Series, ts: pd.Series, y0: int, y1: int) -> float:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl})
    vals = df.loc[(df["ts"].dt.year >= y0) & (df["ts"].dt.year <= y1), "pnl"]
    tw = vals[vals > 0]
    tl = vals[vals < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def rolling12(ts: pd.Series, pnl: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"ts": pd.to_datetime(ts), "pnl": pnl}).sort_values("ts").reset_index(drop=True)
    first = df["ts"].min().to_period("M").to_timestamp()
    last = df["ts"].max().to_period("M").to_timestamp()
    month_ends = pd.period_range(first, last, freq="M").to_timestamp()
    rows = []
    for end_start in month_ends:
        end_excl = end_start + pd.DateOffset(months=12)
        start = end_excl - pd.DateOffset(months=12)
        g = df.loc[(df["ts"] >= start) & (df["ts"] < end_excl)]
        if g.empty:
            continue
        rows.append({"window_start": start.strftime("%Y-%m"), "window_end": end_start.strftime("%Y-%m"),
                     "n": int(len(g)), "pnl": float(g["pnl"].sum())})
    return pd.DataFrame(rows)


def main() -> None:
    for name, cfg in STRATEGIES.items():
        strategy_dir = ROOT / "原油" / name
        out_dir = strategy_dir / "data" / "validation" / "experiments_20260815"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n==== {name} ====")
        tf2 = load_2h(strategy_dir)
        gt = load_gate(strategy_dir, cfg)
        trig = build_triggers(tf2)
        check = gate_check(gt, cfg["n_min"], cfg["thr"], *cfg["amp"])
        keep = [check(t, r["dir"] == "L") for t, r in zip(trig["signal_time"], trig.to_dict("records"))]
        trades = trig.loc[keep].copy().reset_index(drop=True)
        trades.to_csv(out_dir / "trades.csv", index=False, encoding="utf-8-sig")
        pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
        ts = pd.to_datetime(trades["signal_time"])
        m = metrics(pnl)
        years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].agg(["count", "sum"])
        yearly = pd.DataFrame([{"year": int(y), "n": int(r["count"]), "pnl": round(float(r["sum"]), 2)}
                               for y, r in years.iterrows()])
        yearly.to_csv(out_dir / "yearly.csv", index=False, encoding="utf-8-sig")
        wf = pd.DataFrame(
            [
                {"train": "2020-2023", "test": "2024-2026",
                 "train_pf": range_pf(pnl, ts, 2020, 2023),
                 "test_pf": range_pf(pnl, ts, 2024, 2026), "test_n": int((ts.dt.year >= 2024).sum())},
                {"train": "2020-2022", "test": "2023-2026",
                 "train_pf": range_pf(pnl, ts, 2020, 2022),
                 "test_pf": range_pf(pnl, ts, 2023, 2026), "test_n": int((ts.dt.year >= 2023).sum())},
            ]
        )
        wf.to_csv(out_dir / "walkforward.csv", index=False, encoding="utf-8-sig")
        roll = rolling12(ts, pnl)
        roll.to_csv(out_dir / "rolling_12m.csv", index=False, encoding="utf-8-sig")
        cost_rows = []
        for cost in COSTS[1:]:
            mc = metrics(pnl - cost)
            cost_rows.append({"cost_pt": cost, "pf": mc["pf"], "test_pf": test_pf(pnl - cost, ts)})
        cost_df = pd.DataFrame(cost_rows)
        cost_df.to_csv(out_dir / "cost_sensitivity.csv", index=False, encoding="utf-8-sig")

        lines = [
            f"# {name}：{cfg['gate_tf']} 机会门 → 2H 交易（独立全流程验证）",
            "",
            "> 数据：本策略自有 manifest（USOILm）；指标：mean-init SMMA + way/vol_way；",
            f"> 门：持续根数≥{cfg['n_min']} + 极值bar way/vol_way≥{cfg['thr']} + SMMA13极值幅度 {cfg['amp'][0]:g}-{cfg['amp'][1]:g}%；",
            "> 2H 触发：cross/pre_cross（不含 post_n）；2H 结构止损 0.1-1.0%；单段退出。",
            "",
            "## 总览",
            "",
            f"- 门内 2H 触发数：{len(trig)}，门后交易：{m['n']}（WR {m['wr']:.1f}%，PF {m['pf']:.3f}，EV {m['ev']:+.2f}pt）",
            f"- 样本外(后30%) PF：{test_pf(pnl, ts):.3f}",
            "",
            "## Walk-forward（日历样本外）",
            "",
            markdown_table(wf, [str(c) for c in wf.columns]),
            "",
            "## 12M 滚动窗口",
            "",
            f"- 窗口 {len(roll)} 个，正窗口 {(roll['pnl'] > 0).sum()}（{(roll['pnl'] > 0).mean() * 100:.0f}%），",
            f"最差 {roll.loc[roll['pnl'].idxmin(), 'window_start']}..{roll.loc[roll['pnl'].idxmin(), 'window_end']}（{roll['pnl'].min():+.1f}）",
            "",
            "## 分年",
            "",
            markdown_table(yearly, [str(c) for c in yearly.columns]),
            "",
            "## 成本敏感性（每笔往返，USOILm 真实口径）",
            "",
            markdown_table(cost_df, [str(c) for c in cost_df.columns]),
        ]
        (out_dir / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"trades={m['n']} pf0={m['pf']:.3f} test0={test_pf(pnl, ts):.3f} "
              f"wf_test={range_pf(pnl, ts, 2024, 2026):.3f} years={int((years['sum'] > 0).sum())}/{len(years)}")
        print(f"wrote: {out_dir}")


if __name__ == "__main__":
    main()

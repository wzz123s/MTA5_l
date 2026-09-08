# -*- coding: utf-8 -*-
"""Standalone 2H strategy validation (own data, no higher-TF gate).

Triggers on 2H: cross / pre_cross (post_n rejected by prior data).
Optional factor: 2-bar confirmation min(way_s_way, vol_way_s_way) in
direction >= 0.5 (entry delayed to bar+3 open).
Stop: 2H structure (prev-seg SMA13 extreme) 0.1-1.0%; single-position exit.

Lookahead warning (2026-08-17):
  The non-causal confirm variants (cross_pre_confirm, cross_confirm) compute
  way/vol_way over the FULL series; filter_short_segments(min_len=8) then uses
  FUTURE crosses to retroactively merge short segments, i.e. lookahead. That
  inflated PF (2.19 vs 1.50 causal). The EA implements the causal version
  (confirm values as of bar i+2); use cross_confirm_causal as the live baseline.
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
from usoil_4h6h8h_strategies_20260815 import markdown_table  # noqa: E402


STRATEGY_DIR = ROOT / "原油" / "原油2H策略"
OUT_DIR = STRATEGY_DIR / "data" / "validation" / "experiments_20260815"
PCT_LO, PCT_HI = 0.1, 1.0
COSTS = [0.0, 0.02, 0.05, 0.10]
PRE_GAP = 0.003
CONFIRM_THR = 0.5


def load_2h() -> pd.DataFrame:
    manifest = read_json(STRATEGY_DIR / "data" / "raw" / "raw_source_manifest.json")
    frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H2"), "2H", closed_time=True))
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    return add_way_grade(filter_short_segments(mark_direction(frame), min_len=8)).reset_index(drop=True)


def causal_confirm_values(frame: pd.DataFrame, i: int, min_len: int = 8) -> tuple:
    """Way/vol_way at confirm bars i+1/i+2 computed AS OF bar i+2 (window [0..i+2]).

    Matches the EA's live (causal) behavior: the current segment has not ended yet,
    so short-segment merging is NOT yet known. The full-series columns (load_2h)
    retroactively merge short segments using future crosses (lookahead) and can
    reject trades the EA would legitimately take at confirm time.
    """
    j2 = min(i + 2, len(frame) - 1)
    win = frame.iloc[: j2 + 1].copy().reset_index(drop=True)
    w = add_way_grade(filter_short_segments(mark_direction(win), min_len=min_len))
    return (
        float(w.iloc[-2]["way_s_way"]),
        float(w.iloc[-1]["way_s_way"]),
        float(w.iloc[-2]["vol_way_s_way"]),
        float(w.iloc[-1]["vol_way_s_way"]),
    )


def signals(tf: pd.DataFrame, use_pre: bool):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    sma5 = pd.to_numeric(tf["SMA_5"], errors="coerce").to_numpy()
    sma13 = pd.to_numeric(tf["SMA_13"], errors="coerce").to_numpy()
    close = pd.to_numeric(tf["close"], errors="coerce").to_numpy()
    rows = []
    for i in range(1, len(tf) - 1):
        side = None
        if direction[i] in ("good", "bad"):
            side = "L" if direction[i] == "good" else "S"
        elif use_pre and np.isfinite(sma5[i]) and np.isfinite(sma13[i]) and np.isfinite(sma13[i - 1]) and np.isfinite(close[i]) and np.isfinite(close[i - 1]):
            gap = abs(sma5[i] - sma13[i]) / sma13[i]
            long_setup = close[i - 1] <= sma13[i - 1] and close[i] > sma13[i] and sma5[i] < sma13[i]
            short_setup = close[i - 1] >= sma13[i - 1] and close[i] < sma13[i] and sma5[i] > sma13[i]
            if gap <= PRE_GAP and (long_setup or short_setup):
                side = "L" if long_setup else "S"
        if side is None:
            continue
        k = -1
        for c in cross_idx:
            if c < i:
                k = c
            else:
                break
        if k < 0:
            continue
        seg = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").dropna()
        if seg.empty:
            continue
        sl = float(seg.min()) if side == "L" else float(seg.max())
        rows.append({"i": i, "dir": side, "sl": sl, "signal_time": tf.iloc[i]["bar_close_time"]})
    return pd.DataFrame(rows)


def replay(tf: pd.DataFrame, sig: pd.DataFrame, use_confirm: bool, causal: bool = False):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    out = []
    for _, s in sig.iterrows():
        i = int(s["i"])
        side = str(s["dir"])
        sl = float(s["sl"])
        if use_confirm:
            j1, j2 = i + 1, i + 2
            if j2 + 1 >= len(tf):
                continue
            if causal:
                w1, w2, v1, v2 = causal_confirm_values(tf, i)
            else:
                w1 = float(tf.iloc[j1]["way_s_way"]); w2 = float(tf.iloc[j2]["way_s_way"])
                v1 = float(tf.iloc[j1]["vol_way_s_way"]); v2 = float(tf.iloc[j2]["vol_way_s_way"])
            # BUG-1 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1], 方向由触发决定, 去掉 sign
            if not (min(w1, w2) >= CONFIRM_THR and min(v1, v2) >= CONFIRM_THR):
                continue
            entry_idx = j2 + 1
        else:
            entry_idx = i + 1
        if entry_idx >= len(tf):
            continue
        entry = float(tf.iloc[entry_idx]["open"])
        pct = abs(entry - sl) / entry * 100.0
        if not (PCT_LO <= pct <= PCT_HI):
            continue
        if (side == "L" and sl >= entry) or (side == "S" and sl <= entry):
            continue
        opp = "bad" if side == "L" else "good"
        nxt = next((x for x in cross_idx if x > entry_idx and direction[x] == opp), None)
        if nxt is None:
            continue
        exit_idx = nxt + 1
        if exit_idx >= len(tf):
            exit_idx = nxt
        result = None
        sl_idx = None
        for j in range(entry_idx, exit_idx):
            b = tf.iloc[j]
            open_px = float(b["open"]); h = float(b["high"]); lo = float(b["low"])
            if side == "L":
                if open_px <= sl:
                    exit_px = open_px
                elif lo <= sl:
                    exit_px = sl
                else:
                    continue
                pnl = exit_px - entry
            else:
                if open_px >= sl:
                    exit_px = open_px
                elif h >= sl:
                    exit_px = sl
                else:
                    continue
                pnl = entry - exit_px
            result = (exit_px, pnl)
            sl_idx = j
            break
        if result is None:
            exit_bar = tf.iloc[exit_idx]
            exit_px = float(exit_bar["open"]) if exit_idx != nxt else float(exit_bar["close"])
            pnl = (exit_px - entry) if side == "L" else (entry - exit_px)
            reason = "opposite cross"
            exit_row = exit_idx
        else:
            _, pnl = result
            reason = "SL hit"
            exit_row = sl_idx
        out.append({
            "signal_time": s["signal_time"],
            "dir": side,
            "pnl_points": pnl,
            "entry": entry,
            "stop": sl,
            "exit_time": tf.iloc[exit_row]["date"],
            "exit_price": exit_px,
            "reason": reason,
        })
    return pd.DataFrame(out)


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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tf = load_2h()
    sig_all = signals(tf, use_pre=True)
    sig_cross = signals(tf, use_pre=False)
    print("2H signals: cross+pre_cross =", len(sig_all), "| cross only =", len(sig_cross))
    variants = [
        ("cross_pre", sig_all, False),
        ("cross_pre_confirm", sig_all, True),
        ("cross_confirm", sig_cross, True),
        ("cross", sig_cross, False),
        ("cross_confirm_causal", sig_cross, True),
    ]
    LOOKAHEAD_VARIANTS = {"cross_pre_confirm", "cross_confirm"}
    rows = []
    for name, sig, use_confirm in variants:
        causal = name.endswith("_causal")
        trades = replay(tf, sig, use_confirm, causal=causal)
        if trades.empty or len(trades) < 15:
            print(f"  {name}: too few ({len(trades)})")
            continue
        pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
        ts = pd.to_datetime(trades["signal_time"])
        m = metrics(pnl)
        years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].agg(["count", "sum"])
        row = {
            "variant": name, "n": m["n"], "wr": m["wr"], "pf0": m["pf"], "ev0": m["ev"],
            "lookahead": name in LOOKAHEAD_VARIANTS,
            "test_pf0": test_pf(pnl, ts),
            "wf_test_24_26": range_pf(pnl, ts, 2024, 2026),
            "wf_train_20_23": range_pf(pnl, ts, 2020, 2023),
            "pos_years": f"{int((years['sum'] > 0).sum())}/{len(years)}",
        }
        for cost in COSTS[1:]:
            row[f"pf_{cost:g}"] = metrics(pnl - cost)["pf"]
        rows.append(row)
        trades.to_csv(OUT_DIR / f"{name}_trades.csv", index=False, encoding="utf-8-sig")
        print(
            f"  {name}: n={m['n']} pf0={m['pf']:.3f} ev0={m['ev']:+.2f} test0={row['test_pf0']:.3f} "
            f"lookahead={row['lookahead']} "
            f"wf_train={row['wf_train_20_23']:.3f} wf_test={row['wf_test_24_26']:.3f} "
            f"pf0.10={row['pf_0.1']:.3f} years={row['pos_years']}"
        )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "summary.csv", index=False, encoding="utf-8-sig")
    cols = ["variant", "lookahead", "n", "wr", "pf0", "ev0", "test_pf0", "wf_train_20_23", "wf_test_24_26",
            "pf_0.02", "pf_0.05", "pf_0.1", "pos_years"]
    lines = [
        "# 原油单独 2H 策略（独立全流程验证）",
        "",
        "> 2H cross/pre_cross 触发；可选 2-bar way/vol_way 确认因子；2H 结构止损 0.1-1.0%；单段退出。",
        "",
        "## lookahead 风险说明（2026-08-17）",
        "",
        "- `cross_pre_confirm` / `cross_confirm`（lookahead=True）：确认值在全序列上计算，"
        "`filter_short_segments(min_len=8)` 会用**未来交叉**回溯合并短段，属 lookahead，PF 被高估。",
        "- `cross_confirm_causal`（lookahead=False）：确认值按 [0..确认bar] 窗口因果计算，"
        "与实盘 EA 行为一致，**作为正式（可交易）口径**。",
        "- 实盘 EA `USOIL2H_CrossConfirm_EA`（v5）即因果口径；2021–2026 Tester 冒烟 "
        "53/53 与因果期望一致（0 missing / 0 extra / PnL 零误差）。",
        "",
        markdown_table(df[cols], cols),
    ]
    (OUT_DIR / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'validation_report.md'}")


if __name__ == "__main__":
    main()

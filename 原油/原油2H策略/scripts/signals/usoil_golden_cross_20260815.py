# -*- coding: utf-8 -*-

"""USOIL golden-cross experiment: 1H/2H/4H/6H SMA5/13 crosses + way/vol_way filter.

No bias gates. Per higher timeframe:
  - cross bar i (SMA5/13 golden/death cross) closes;
  - confirmation bar i+1 closes; require way_s_way / vol_way_s_way in the
    trade direction (>= thr; on the first segment bar these are 0/1 so the
    filter means "first bar holds cleanly above/below SMA13 with volume <= ma");
  - enter at bar i+2 open;
  - SL = previous-segment SMA13 extreme; exit = stop-first else opposite cross
    next-open (single position).
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
    manifest_timeframe,
    markdown_table,
    read_json,
    standardize_mt5_csv,
)
from replay_1h_way_momentum_filter_scan import (  # noqa: E402
    add_way_grade,
    filter_short_segments,
    mark_direction,
)


OUT_DIR = ROOT / "原油" / "原油金叉实验_20260815"
COSTS = [0.0, 0.02, 0.05, 0.10, 0.20]  # USOILm 真实口径: spread $0.02, 往返含滑点 ~$0.05-0.10

# timeframe -> (strategy dir, manifest timeframe, label for standardize)
TF_SOURCES = {
    "1H": (ROOT / "原油" / "USOIL_1H_M30_4H策略", "H1", "1H"),
    "2H": (ROOT / "原油" / "USOIL_30m2H策略", "H2", "2H"),
    "4H": (ROOT / "原油" / "USOIL_1H_M30_4H策略", "H4", "4H"),
    "6H": (ROOT / "原油" / "USOIL_2H_M30_6H策略", "H6", "6H"),
}
FILTERS = [
    ("none", -1.0),
    ("way>=0", 0.0),
    ("way>=0.3", 0.3),
    ("way>=0.5", 0.5),
]


def load_tf(tf_name: str) -> pd.DataFrame:
    strategy_dir, mt5_tf, label = TF_SOURCES[tf_name]
    manifest = read_json(strategy_dir / "data" / "raw" / "raw_source_manifest.json")
    frame = add_indicators(standardize_mt5_csv(manifest_file(manifest, mt5_tf), label, closed_time=True))
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    frame = add_way_grade(filter_short_segments(mark_direction(frame), min_len=8))
    return frame.reset_index(drop=True)


def cross_trades(tf: pd.DataFrame, thr: float, start_year: int = 2020):
    direction = tf["方向"].values
    cross_idx = [i for i in range(len(tf)) if direction[i] in ("good", "bad")]
    rows = []
    for pos, i in enumerate(cross_idx):
        side = "L" if direction[i] == "good" else "S"
        j = i + 1
        if j + 1 >= len(tf):
            continue
        wsw = float(tf.iloc[j]["way_s_way"])
        vwsw = float(tf.iloc[j]["vol_way_s_way"])
        if side == "L":
            ok = wsw >= thr and vwsw >= thr
        else:
            ok = wsw >= thr and vwsw >= thr  # BUG修复(2026-09-04): way_s_way无符号[0,1], 不能判负值
        if not ok:
            continue
        entry_idx = j + 1
        if pd.to_datetime(tf.iloc[entry_idx]["bar_open_time"]).year < start_year:
            continue
        entry = float(tf.iloc[entry_idx]["open"])
        k = cross_idx[pos - 1] if pos > 0 else 0
        seg = pd.to_numeric(tf.iloc[k:i]["SMA_13"], errors="coerce").dropna()
        if seg.empty:
            continue
        sl = float(seg.min()) if side == "L" else float(seg.max())
        if not np.isfinite(sl):
            continue
        if (side == "L" and sl >= entry) or (side == "S" and sl <= entry):
            continue
        opp = "bad" if side == "L" else "good"
        nxt = next((x for x in cross_idx[pos + 1:] if direction[x] == opp), None)
        if nxt is None:
            continue
        exit_idx = nxt + 1
        if exit_idx >= len(tf):
            exit_idx = nxt
        # replay stop-first
        result = None
        for idx in range(entry_idx, exit_idx):
            bar = tf.iloc[idx]
            open_px = float(bar["open"]); high = float(bar["high"]); low = float(bar["low"])
            if side == "L":
                if open_px <= sl:
                    exit_px, reason = open_px, "stop_gap"
                elif low <= sl:
                    exit_px, reason = sl, "stop"
                else:
                    continue
                pnl = exit_px - entry
            else:
                if open_px >= sl:
                    exit_px, reason = open_px, "stop_gap"
                elif high >= sl:
                    exit_px, reason = sl, "stop"
                else:
                    continue
                pnl = entry - exit_px
            result = (exit_px, reason, pnl)
            break
        if result is None:
            exit_bar = tf.iloc[exit_idx]
            exit_px = float(exit_bar["open"]) if exit_idx != nxt else float(exit_bar["close"])
            pnl = (exit_px - entry) if side == "L" else (entry - exit_px)
        else:
            exit_px, _, pnl = result
        rows.append(
            {
                "signal_time": tf.iloc[i]["bar_close_time"],
                "entry_time": tf.iloc[entry_idx]["bar_open_time"],
                "dir": side,
                "entry": entry,
                "stop": sl,
                "stop_distance": abs(entry - sl),
                "pnl_points": pnl,
            }
        )
    return pd.DataFrame(rows)


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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for tf_name in ["1H", "2H", "4H", "6H"]:
        tf = load_tf(tf_name)
        print(f"==== {tf_name} (bars={len(tf)}) ====")
        for fname, thr in FILTERS:
            trades = cross_trades(tf, thr)
            if trades.empty:
                print(f"  {fname}: no trades")
                continue
            pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
            ts = pd.to_datetime(trades["signal_time"])
            base = metrics(pnl)
            years = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            row = {
                "tf": tf_name,
                "filter": fname,
                "n": base["n"],
                "wr": base["wr"],
                "pf0": base["pf"],
                "ev0": base["ev"],
                "test_pf0": test_pf(pnl, ts),
                "avg_stop": float(pd.to_numeric(trades["stop_distance"], errors="coerce").mean()),
                "pos_years": f"{int((years > 0).sum())}/{len(years)}",
            }
            for cost in COSTS[1:]:
                m = metrics(pnl - cost)
                row[f"pf_{cost:g}"] = m["pf"]
                row[f"test_pf_{cost:g}"] = test_pf(pnl - cost, ts)
            all_rows.append(row)
            print(
                f"  {fname}: n={base['n']} pf0={base['pf']:.3f} ev0={base['ev']:+.2f} "
                f"test0={row['test_pf0']:.3f} pf0.05={row['pf_0.05']:.3f} pf0.10={row['pf_0.1']:.3f} "
                f"years={row['pos_years']}"
            )
    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_DIR / "golden_cross_matrix.csv", index=False, encoding="utf-8-sig")
    cols = ["tf", "filter", "n", "wr", "pf0", "ev0", "test_pf0", "pf_0.02", "pf_0.05", "pf_0.1",
            "test_pf_0.02", "test_pf_0.05", "test_pf_0.1", "avg_stop", "pos_years"]
    lines = [
        "# 原油金叉实验：1H/2H/4H/6H SMA5/13 金叉 + way/vol_way 过滤（2020-2026 USOILm）",
        "",
        "> 无 bias 门；金叉收盘 → 下一根确认 bar（way_s_way/vol_way_s_way 同向）→ 再下一根开盘入场；",
        "> 成本为 USOILm 真实口径（spread $0.02；往返含滑点 $0.05-0.10）。",
        "> 止损=上一段 SMA13 极值；出场=止损优先，否则反向穿越下一根开盘（单段，1 倍成本）。",
        "",
        markdown_table(df[cols], cols),
    ]
    (OUT_DIR / "golden_cross_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote: {OUT_DIR / 'golden_cross_report.md'}")


if __name__ == "__main__":
    main()

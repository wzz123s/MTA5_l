# -*- coding: utf-8 -*-
"""V反策略 P2：候选信号生成（无 lookahead）

信号定义（规格书 v0.1）：
- S1 做空V反：高周期 bias55 >= 阈值（超涨急速段）+ 本周期 bad 穿越 + 结构止损距离合规
- S2 做多V反：高周期 bias55 <= -阈值 + good 穿越
- 黄金：信号 M30，门 H4（bias55 扫描 2.5/3.0/3.5/4.0/4.5）+ 2H rise 结构（>=3%）
- 原油：信号 H2，门 H4（bias55 扫描 2.0/2.5/3.0/3.5/4.0）+ H4 段长>=8

入场：信号 bar 后下一根本周期 bar 开盘价
止损：结构止损（空=prev_seg_high_sma13；多=prev_seg_low_sma13），距离合规区间
输出：data/signals/candidates_<symbol>.csv
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
OUT = Path(__file__).resolve().parents[1] / "data" / "signals"

def load(symbol: str, tf: str) -> pd.DataFrame:
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

TF_MIN = {"M15": 15, "M30": 30, "H1": 60, "H2": 120, "H4": 240, "H6": 360, "H8": 480, "D1": 1440, "W1": 10080}

def last_closed_higher(df_hi: pd.DataFrame, t: pd.Timestamp, tf_hi: str, tf_sig: str) -> pd.Series:
    """返回时间 t 之前最新已收盘的高周期 bar（因果：门 bar 收盘 <= 信号 bar 收盘）"""
    cutoff = t + pd.Timedelta(minutes=TF_MIN[tf_sig])
    mask = (df_hi["dt"] + pd.Timedelta(minutes=TF_MIN[tf_hi])) <= cutoff
    if not mask.any():
        return None
    return df_hi.loc[mask].iloc[-1]

def gen_signals(symbol: str, sig_tf: str, gate_tf: str, struct_tf: str | None,
                short_thresholds: list[float], long_thresholds: list[float],
                stop_lo: float, stop_hi: float, use_structure: bool, seg_min: int) -> pd.DataFrame:
    df = load(symbol, sig_tf)
    df_hi = load(symbol, gate_tf)
    df_struct = load(symbol, struct_tf) if struct_tf else None

    rows = []
    cross_rows = df[df["dir"].isin(["bad", "good"])]
    for i, row in cross_rows.iterrows():
        t = row["dt"]
        # 下一根 bar 开盘 = 信号后的第一个 bar（直接取原始序列中该行后的下一行）
        idx = df.index.get_loc(i)
        if idx + 1 >= len(df):
            continue
        next_bar = df.iloc[idx + 1]
        entry = next_bar["open"]

        hi = last_closed_higher(df_hi, t, gate_tf, sig_tf)
        if hi is None:
            continue
        # 结构条件（可选）：struct_tf 的 rise 或 段长
        struct_ok = True
        if use_structure and df_struct is not None:
            st = last_closed_higher(df_struct, t, struct_tf, sig_tf)
            if st is None or pd.isna(st["rise"]):
                struct_ok = False
            else:
                struct_ok = st["rise"] >= 0.03
        if use_structure and seg_min > 0:
            if hi["seg_len"] < seg_min:
                struct_ok = False

        direction = row["dir"]
        if direction == "bad":
            for thr in short_thresholds:
                if hi["bias55_pct"] >= thr and struct_ok:
                    stop = row["prev_seg_high_sma13"]
                    if pd.isna(stop):
                        continue
                    dist = stop - entry
                    if dist <= 0 or dist / entry < stop_lo or dist / entry > stop_hi:
                        continue
                    rows.append({
                        "symbol": symbol, "signal": "S1", "dir": "short",
                        "signal_dt": t, "signal_tf": sig_tf,
                        "entry_dt": next_bar["dt"], "entry": entry,
                        "stop": stop, "stop_dist_pct": dist / entry * 100,
                        "gate_tf": gate_tf, "gate_bias55_pct": hi["bias55_pct"],
                        "gate_seg_len": hi["seg_len"],
                        "target1": next_bar["close"],  # 占位，P3 用 SMA55 回归
                        "threshold": thr,
                    })
                    break  # 首个满足阈值即可
        elif direction == "good":
            for thr in long_thresholds:
                if hi["bias55_pct"] <= -thr and struct_ok:
                    stop = row["prev_seg_low_sma13"]
                    if pd.isna(stop):
                        continue
                    dist = entry - stop
                    if dist <= 0 or dist / entry < stop_lo or dist / entry > stop_hi:
                        continue
                    rows.append({
                        "symbol": symbol, "signal": "S2", "dir": "long",
                        "signal_dt": t, "signal_tf": sig_tf,
                        "entry_dt": next_bar["dt"], "entry": entry,
                        "stop": stop, "stop_dist_pct": dist / entry * 100,
                        "gate_tf": gate_tf, "gate_bias55_pct": hi["bias55_pct"],
                        "gate_seg_len": hi["seg_len"],
                        "target1": next_bar["close"],
                        "threshold": thr,
                    })
                    break
    return pd.DataFrame(rows)

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 黄金：信号 M30，门 H4，结构 2H rise>=3%（可选）
    gold = gen_signals(
        "XAUUSDm", "M30", "H4", "H2",
        short_thresholds=[2.5, 3.0, 3.5, 4.0, 4.5],
        long_thresholds=[2.5, 3.0, 3.5, 4.0, 4.5],
        stop_lo=0.0011, stop_hi=0.008,   # 5~35 价格单位 ≈ 0.11%~0.8%（4400价位）
        use_structure=True, seg_min=0,
    )
    gold.to_csv(OUT / "candidates_XAUUSDm.csv", index=False)
    print(f"[XAUUSDm] 候选信号: {len(gold)}（S1空={len(gold[gold['dir']=='short'])} S2多={len(gold[gold['dir']=='long'])}）")

    # 原油：信号 H2，门 H4 段长>=8
    oil = gen_signals(
        "USOILm", "H2", "H4", None,
        short_thresholds=[2.0, 2.5, 3.0, 3.5, 4.0],
        long_thresholds=[2.0, 2.5, 3.0, 3.5, 4.0],
        stop_lo=0.001, stop_hi=0.01,   # 0.1%~1.0%
        use_structure=False, seg_min=8,
    )
    oil.to_csv(OUT / "candidates_USOILm.csv", index=False)
    print(f"[USOILm] 候选信号: {len(oil)}（S1空={len(oil[oil['dir']=='short'])} S2多={len(oil[oil['dir']=='long'])}）")

if __name__ == "__main__":
    main()

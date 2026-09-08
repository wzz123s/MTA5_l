# -*- coding: utf-8 -*-
"""M2.1 基线回测：黄金（6H门+M30三机会+Bias_5 top34%+三段退出）与 原油（4H门+H2 cross+H1 confirm+三段退出）。
口径对照 01_策略设计说明.md。输出 trades CSV + 基线统计。
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
COST = 0.0005  # 双边总成本 0.05%/笔（按金额比例）
STOP_SPEC_LO = None  # StopSpec 下限（价格单位）；None=不过滤
STOP_SPEC_HI = None  # StopSpec 上限（价格单位）

# ---------------- 信号生成 ----------------

def gen_signals_gold(df: pd.DataFrame) -> pd.DataFrame:
    """黄金：6H 门 + M30 三机会（pre_cross/cross/post_n）"""
    df = df.copy()
    # 6H 顺势门（做多：bias5/13/55 signed > 0；做空：全部 < 0）
    df["gate_long"] = (df["H6_bias5_signed_pct"] > 0) & (df["H6_bias13_signed_pct"] > 0) & (df["H6_bias55_signed_pct"] > 0)
    df["gate_short"] = (df["H6_bias5_signed_pct"] < 0) & (df["H6_bias13_signed_pct"] < 0) & (df["H6_bias55_signed_pct"] < 0)
    df["gap_pct"] = (df["SMA_5"] - df["SMA_13"]).abs() / df["SMA_13"] * 100
    # 方向状态辅助列
    prev_dir = df["方向"].shift(1)
    df["is_pre_cross_l"] = (df["方向"] == "good") & (df["close"].shift(1) <= df["SMA_13"].shift(1)) & (df["close"] > df["SMA_13"]) & (df["SMA_5"] < df["SMA_13"]) & (df["gap_pct"] <= 0.300)
    df["is_pre_cross_s"] = (df["方向"] == "bad") & (df["close"].shift(1) >= df["SMA_13"].shift(1)) & (df["close"] < df["SMA_13"]) & (df["SMA_5"] > df["SMA_13"]) & (df["gap_pct"] <= 0.300)
    # cross：good 行即为 5SMA 上穿 13SMA 时刻（mark_direction 定义）
    df["is_cross_l"] = (df["方向"] == "good") & ~df["is_pre_cross_l"]
    df["is_cross_s"] = (df["方向"] == "bad") & ~df["is_pre_cross_s"]
    # post_n：穿越后第 2-6 根（沿用 MTA5_l 口径：cross 后第 N 根，N=2..6）
    df["bar_since_cross"] = 0
    cnt_l = cnt_s = 0
    vals_l, vals_s = [], []
    for i in range(len(df)):
        d = df["方向"].iloc[i]
        if d == "good":
            cnt_l = 0
        elif d in ("up",):
            cnt_l += 1
        else:
            cnt_l = -1
        if d == "bad":
            cnt_s = 0
        elif d in ("down",):
            cnt_s += 1
        else:
            cnt_s = -1
        vals_l.append(cnt_l)
        vals_s.append(cnt_s)
    df["bar_since_cross_l"] = vals_l
    df["bar_since_cross_s"] = vals_s
    df["is_post_l"] = df["bar_since_cross_l"].isin([2, 3, 4, 5, 6])
    df["is_post_s"] = df["bar_since_cross_s"].isin([2, 3, 4, 5, 6])
    # 合并信号（去重优先级 pre_cross > cross > post_n），仅当门成立
    df["sig"] = ""
    df.loc[df["is_pre_cross_l"] & df["gate_long"], "sig"] = "long_pre_cross"
    df.loc[df["is_cross_l"] & df["gate_long"] & (df["sig"] == ""), "sig"] = "long_cross"
    df.loc[df["is_post_l"] & df["gate_long"] & (df["sig"] == ""), "sig"] = "long_post_n"
    df.loc[df["is_pre_cross_s"] & df["gate_short"], "sig"] = "short_pre_cross"
    df.loc[df["is_cross_s"] & df["gate_short"] & (df["sig"] == ""), "sig"] = "short_cross"
    df.loc[df["is_post_s"] & df["gate_short"] & (df["sig"] == ""), "sig"] = "short_post_n"
    return df


def gen_signals_oil(df: pd.DataFrame) -> pd.DataFrame:
    """原油：4H 门（bias55 ±2% 反向机会池）+ H2 cross + H1 confirm"""
    df = df.copy()
    df["gate_long"] = (df["H4_bias55_signed_pct"] <= -2.0)   # 超跌 → 只做多
    df["gate_short"] = (df["H4_bias55_signed_pct"] >= 2.0)  # 超涨 → 只做空
    # H1 confirm：bias5/13 同向（策略生成规则：1H bias5&bias13 同向）
    df["h1_confirm_l"] = (df["H1_bias5_signed_pct"] > 0) & (df["H1_bias13_signed_pct"] > 0)
    df["h1_confirm_s"] = (df["H1_bias5_signed_pct"] < 0) & (df["H1_bias13_signed_pct"] < 0)
    df["sig"] = ""
    df.loc[(df["方向"] == "good") & df["gate_long"] & df["h1_confirm_l"], "sig"] = "long_cross"
    df.loc[(df["方向"] == "bad") & df["gate_short"] & df["h1_confirm_s"], "sig"] = "short_cross"
    return df


# ---------------- EA 同口径信号（M4 对齐修正 v1） ----------------

def build_merged_codes(raw: np.ndarray, min_len: int = 8) -> np.ndarray:
    """复刻 EA BuildRawCodes + BuildMergedCodes（min_len=8 链吸收）。
    raw: 2=good(bad→? ) 约定 2=上穿/-2=下穿/1=上/-1=下（与 EA 一致）。"""
    merged = raw.copy()
    crossings = np.where(np.abs(raw) == 2)[0]
    cross_types = raw[crossings]
    n_cross = len(crossings)
    if n_cross < 2:
        return merged
    state = -1 if cross_types[0] == 2 else 1
    i = 0
    while i < n_cross - 1:
        pos = int(crossings[i])
        next_pos = int(crossings[i + 1])
        type_ = int(cross_types[i])
        region_count = 0
        for k in range(pos + 1, next_pos):
            if type_ == 2 and raw[k] == 1:
                region_count += 1
            if type_ == -2 and raw[k] == -1:
                region_count += 1
        if region_count < min_len:
            merged[pos] = state
            for k in range(pos + 1, next_pos):
                merged[k] = state
            merged[next_pos] = state
            crossings = np.delete(crossings, [i, i + 1])
            cross_types = np.delete(cross_types, [i, i + 1])
            n_cross -= 2
            if n_cross < 2:
                break
            continue
        state = 1 if type_ == 2 else -1
        i += 1
    return merged


def merged_post_count(merged: np.ndarray) -> np.ndarray:
    """复刻 EA MergedPostNValue：自上次 merged 穿越后的延续根数（带方向）"""
    n = len(merged)
    out = np.zeros(n, dtype=int)
    counter = 0
    last_cross = 0
    for i in range(n):
        code = int(merged[i])
        if code == 2:
            counter = 1
            last_cross = 1
        elif code == -2:
            counter = -1
            last_cross = -1
        elif code == 1 and last_cross == 1:
            counter += 1
        elif code == -1 and last_cross == -1:
            counter -= 1
        else:
            counter = 0
            last_cross = 0
        out[i] = counter
    return out


def gen_signals_gold_ea(df: pd.DataFrame, min_len: int = 8,
                        pre_gap_pct: float = 0.300) -> pd.DataFrame:
    """黄金信号生成（EA DetectSignal 同口径，M4 对齐 v1）：
    - merged 方向（链吸收 min_len=8）；
    - pre_cross：merged 非穿越 && close 穿 SMA13 && SMA5<SMA13（gap<=0.300）；
    - cross：merged 穿越（good/bad）；
    - post_n：merged 延续计数 2..6；
    - 止损：cross/pre_cross=prev-seg SMA13 极值（long_stop/short_stop ffill）；post_n=当前 SMA13；
    - 6H 门：bias5>0 && bias55>0（EA Pass6HGate 同口径）。
    """
    df = df.copy()
    raw = df["方向"].map({"good": 2, "bad": -2, "up": 1, "down": -1}).fillna(0).to_numpy().astype(int)
    merged = build_merged_codes(raw, min_len)
    m = pd.Series(merged, index=df.index)
    df["方向_m"] = m.map({2: "good", -2: "bad", 1: "up", -1: "down"}).fillna("down")
    # 6H 门（EA Pass6HGate：bias5>0 && bias55>0，trade-direction）
    df["gate_long"] = (df["H6_bias5_signed_pct"] > 0) & (df["H6_bias55_signed_pct"] > 0)
    df["gate_short"] = (df["H6_bias5_signed_pct"] < 0) & (df["H6_bias55_signed_pct"] < 0)
    gap_pct = (df["SMA_5"] - df["SMA_13"]).abs() / df["SMA_13"] * 100
    prev_close = df["close"].shift(1)
    prev_s13 = df["SMA_13"].shift(1)
    not_cross = (m != 2) & (m != -2)
    pre_l = not_cross & (prev_close <= prev_s13) & (df["close"] > df["SMA_13"]) & (df["SMA_5"] < df["SMA_13"]) & (gap_pct <= pre_gap_pct)
    pre_s = not_cross & (prev_close >= prev_s13) & (df["close"] < df["SMA_13"]) & (df["SMA_5"] > df["SMA_13"]) & (gap_pct <= pre_gap_pct)
    cross_l = m == 2
    cross_s = m == -2
    cnt = merged_post_count(merged)
    post_l = (cnt >= 2) & (cnt <= 6)
    post_s = (cnt <= -2) & (cnt >= -6)
    # 止损列（EA FindStopSma 同源：prev-seg SMA13 极值；post_n=当前 SMA13）
    df["long_stop"] = df["long_stop"].ffill()
    df["short_stop"] = df["short_stop"].ffill()
    df.loc[post_l, "long_stop"] = df["SMA_13"]
    df.loc[post_s, "short_stop"] = df["SMA_13"]
    # 合并信号（优先级 pre_cross > cross > post_n）
    df["sig"] = ""
    df.loc[pre_l & df["gate_long"], "sig"] = "long_pre_cross"
    df.loc[cross_l & df["gate_long"] & (df["sig"] == ""), "sig"] = "long_cross"
    df.loc[post_l & df["gate_long"] & (df["sig"] == ""), "sig"] = "long_post_n"
    df.loc[pre_s & df["gate_short"], "sig"] = "short_pre_cross"
    df.loc[cross_s & df["gate_short"] & (df["sig"] == ""), "sig"] = "short_cross"
    df.loc[post_s & df["gate_short"] & (df["sig"] == ""), "sig"] = "short_post_n"
    return df


# ---------------- 三段退出模拟 ----------------

def simulate(df: pd.DataFrame, sig_col: str = "sig") -> list[dict]:
    """在信号 bar 下一根开盘入场；三段退出：
    Stage1 2.0R 止盈；Stage2 1.5R trail(13SMA)/4.0R force；Stage3 反向穿越。
    返回逐笔交易记录。
    """
    trades = []
    i = 0
    n = len(df)
    while i < n:
        sig = df[sig_col].iloc[i]
        if not sig or i + 1 >= n:
            i += 1
            continue
        is_long = sig.startswith("long")
        entry_bar = i + 1
        entry = df["open"].iloc[entry_bar]
        if is_long:
            stop = df["long_stop"].iloc[i]
        else:
            stop = df["short_stop"].iloc[i]
        if not np.isfinite(stop) or not np.isfinite(entry):
            i += 1
            continue
        r = abs(entry - stop)
        if r <= 0 or r > entry * 0.05:  # 止损距离异常过滤（>5% 视为数据异常）
            i += 1
            continue
        if STOP_SPEC_LO is not None and not (STOP_SPEC_LO <= r <= STOP_SPEC_HI):
            i += 1
            continue
        # 三段仓位独立模拟
        exits = {"s1": None, "s2": None, "s3": None}
        trail_s2 = None
        exit_prices: list[float] = []
        j = entry_bar
        while j < n:
            row = df.iloc[j]
            hi, lo, cl = row["high"], row["low"], row["close"]
            s13 = row["SMA_13"]
            d = row["方向"]
            if is_long:
                # 统一止损
                if lo <= stop:
                    exit_prices.append(min(stop, entry))
                    if exits["s1"] is None: exits["s1"] = ("sl", min(stop, entry))
                    if exits["s2"] is None: exits["s2"] = ("sl", min(stop, entry))
                    if exits["s3"] is None: exits["s3"] = ("sl", min(stop, entry))
                    break
                # Stage1: 2.0R
                tp1 = entry + 2.0 * r
                if exits["s1"] is None and hi >= tp1:
                    exits["s1"] = ("tp1", tp1)
                    exit_prices.append(tp1)
                # Stage2: 1.5R 激活 trail，4.0R force
                act2 = entry + 1.5 * r
                force2 = entry + 4.0 * r
                if exits["s2"] is None:
                    if trail_s2 is None and hi >= act2:
                        trail_s2 = s13
                    if trail_s2 is not None:
                        trail_s2 = max(trail_s2, s13)
                        if lo <= trail_s2:
                            exits["s2"] = ("trail", trail_s2)
                            exit_prices.append(trail_s2)
                    if hi >= force2:
                        exits["s2"] = ("force", force2)
                        exit_prices.append(force2)
                # Stage3: 反向穿越（方向变 bad/down 时退出，按该 bar 开盘）
                if exits["s3"] is None and d in ("bad", "down") and j > entry_bar:
                    exits["s3"] = ("rev", row["open"])
                    exit_prices.append(row["open"])
            else:
                if hi >= stop:
                    exit_prices.append(max(stop, entry))
                    if exits["s1"] is None: exits["s1"] = ("sl", max(stop, entry))
                    if exits["s2"] is None: exits["s2"] = ("sl", max(stop, entry))
                    if exits["s3"] is None: exits["s3"] = ("sl", max(stop, entry))
                    break
                tp1 = entry - 2.0 * r
                if exits["s1"] is None and lo <= tp1:
                    exits["s1"] = ("tp1", tp1)
                    exit_prices.append(tp1)
                act2 = entry - 1.5 * r
                force2 = entry - 4.0 * r
                if exits["s2"] is None:
                    if trail_s2 is None and lo <= act2:
                        trail_s2 = s13
                    if trail_s2 is not None:
                        trail_s2 = min(trail_s2, s13)
                        if hi >= trail_s2:
                            exits["s2"] = ("trail", trail_s2)
                            exit_prices.append(trail_s2)
                    if lo <= force2:
                        exits["s2"] = ("force", force2)
                        exit_prices.append(force2)
                if exits["s3"] is None and d in ("good", "up") and j > entry_bar:
                    exits["s3"] = ("rev", row["open"])
                    exit_prices.append(row["open"])
            if exits["s1"] and exits["s2"] and exits["s3"]:
                break
            j += 1
        # 未出场部分按最后 bar 收盘
        if j >= n:
            last_close = df["close"].iloc[-1]
            for k in ("s1", "s2", "s3"):
                if exits[k] is None:
                    exits[k] = ("eod", last_close)
                    exit_prices.append(last_close)
        pnl_pts = 0.0
        for k in ("s1", "s2", "s3"):
            _, px = exits[k]
            if is_long:
                pnl_pts += (px - entry) / r * 33.3333  # 每段 1/3
            else:
                pnl_pts += (entry - px) / r * 33.3333
        pnl_pts -= COST * 100.0 * 3  # 成本按点数近似（r 单位）
        trades.append({
            "entry_time": df["time"].iloc[entry_bar],
            "dir": "L" if is_long else "S",
            "sig": sig,
            "entry": round(entry, 3),
            "stop": round(stop, 3),
            "stop_dist": round(r, 3),
            "exit_s1": f"{exits['s1'][0]}@{round(exits['s1'][1],3)}" if exits["s1"] else "",
            "exit_s2": f"{exits['s2'][0]}@{round(exits['s2'][1],3)}" if exits["s2"] else "",
            "exit_s3": f"{exits['s3'][0]}@{round(exits['s3'][1],3)}" if exits["s3"] else "",
            "pnl_r_units": round(pnl_pts, 2),
            "exit_time": df["time"].iloc[j] if j < n else df["time"].iloc[-1],
        })
        i = j + 1  # 跳过已占用的 bar
    return trades


# ---------------- 统计 ----------------

def stats(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0}
    pnls = np.array([t["pnl_r_units"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gross_win = wins.sum() if len(wins) else 0.0
    gross_loss = -losses.sum() if len(losses) else 0.0
    return {
        "n": len(trades),
        "wr": round(len(wins) / len(trades), 4),
        "avg": round(pnls.mean(), 3),
        "ev": round(pnls.sum(), 2),
        "pf": round(gross_win / gross_loss, 3) if gross_loss > 0 else float("inf"),
        "maxcl": 0,
    }


def max_consecutive_losses(pnls: np.ndarray) -> int:
    m = cur = 0
    for p in pnls:
        if p <= 0:
            cur += 1
            m = max(m, cur)
        else:
            cur = 0
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True, choices=["gold", "oil"])
    args = ap.parse_args()
    if args.strategy == "gold":
        STOP_SPEC_LO, STOP_SPEC_HI = 5.0, 35.0  # 5-35美元（EA InpStopLoPt/HiPt=5/35 价格单位=美元，1点=0.01美元）
        ctx = pd.read_csv(ROOT / "data" / "processed" / "gold_context.csv", parse_dates=["time"])
        df = gen_signals_gold(ctx)
        out_csv = ROOT / "data" / "validation" / "baseline_gold_trades.csv"
    else:
        ctx = pd.read_csv(ROOT / "data" / "processed" / "oil_context_h2.csv", parse_dates=["time"])
        df = gen_signals_oil(ctx)
        out_csv = ROOT / "data" / "validation" / "baseline_oil_trades.csv"
    trades = simulate(df)
    tdf = pd.DataFrame(trades)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    tdf.to_csv(out_csv, index=False, encoding="utf-8-sig")
    st = stats(trades)
    pnls = np.array([t["pnl_r_units"] for t in trades]) if trades else np.array([])
    if len(pnls):
        st["maxcl"] = max_consecutive_losses(pnls)
    print(f"[{args.strategy}] n={st['n']} wr={st['wr']} avg={st['avg']} ev={st['ev']} pf={st['pf']} maxcl={st['maxcl']}")
    if trades:
        tdf["year"] = pd.to_datetime(tdf["entry_time"]).dt.year
        print(tdf.groupby("year").agg(n=("pnl_r_units", "size"), sum=("pnl_r_units", "sum")).to_string())

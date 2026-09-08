# -*- coding: utf-8 -*-
"""乖离反转策略 (Bias Reversal) 回测
超涨做空 / 超跌做多：
  H4 结构：close 站上 SMMA5+SMMA55 且 bias55 >= thr  -> 超涨（只等做空）
           close 站下 SMMA5+SMMA55 且 bias55 <= -thr -> 超跌（只等做多）
  M30 反转确认：死叉(做空) / 金叉(做多)，下一根 M30 bar 开盘入场
  退出：固定%止损(SL) / 2R止盈 / 反向M30交叉平仓（下一bar开盘）
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "validation"
OUT.mkdir(parents=True, exist_ok=True)


def smma(series, n):
    out = np.full(len(series), np.nan)
    if len(series) < n:
        return out
    out[n - 1] = series[:n].mean()
    for i in range(n, len(series)):
        out[i] = (out[i - 1] * (n - 1) + series[i]) / n
    return out


def load():
    m30 = pd.read_csv(RAW / "XAUUSDm_M30.csv", parse_dates=["date"])
    h4 = pd.read_csv(RAW / "XAUUSDm_H4.csv", parse_dates=["date"])
    m30["date"] = m30["date"].dt.tz_localize(None)
    h4["date"] = h4["date"].dt.tz_localize(None)
    return m30, h4


def run(threshold, stop_pct, tp_r, cost_pct=0.05):
    m30, h4 = load()
    # H4 indicators
    c4 = h4["close"].to_numpy(dtype=float)
    h4["s5"] = smma(c4, 5)
    h4["s55"] = smma(c4, 55)
    h4 = h4.dropna(subset=["s55"]).reset_index(drop=True)
    # H4 state per closed bar: +1 超涨(空头准备), -1 超跌(多头准备), 0 无
    h4["bias55"] = (h4["close"] - h4["s55"]) / h4["s55"] * 100.0
    h4["state"] = 0
    h4.loc[(h4["close"] > h4["s5"]) & (h4["close"] > h4["s55"]) & (h4["bias55"] >= threshold), "state"] = 1
    h4.loc[(h4["close"] < h4["s5"]) & (h4["close"] < h4["s55"]) & (h4["bias55"] <= -threshold), "state"] = -1
    h4_close_times = h4["date"].to_numpy()

    # M30 indicators
    c30 = m30["close"].to_numpy(dtype=float)
    m30["s5"] = smma(c30, 5)
    m30["s13"] = smma(c30, 13)
    m30 = m30.dropna(subset=["s13"]).reset_index(drop=True)
    # cross at bar close: 1=金叉, -1=死叉, 0=无
    prev5 = m30["s5"].shift(1)
    prev13 = m30["s13"].shift(1)
    m30["cross"] = np.where((m30["s5"] > m30["s13"]) & (prev5 <= prev13), 1,
                    np.where((m30["s5"] < m30["s13"]) & (prev5 >= prev13), -1, 0))

    n = len(m30)
    closes = m30["close"].to_numpy(dtype=float)
    highs = m30["high"].to_numpy(dtype=float)
    lows = m30["low"].to_numpy(dtype=float)
    opens = m30["open"].to_numpy(dtype=float)
    times = m30["date"].to_numpy()
    crosses = m30["cross"].to_numpy()

    import bisect
    trades = []
    pos = None  # dict(dir, entry, stop, tp, entry_i, entry_price)
    for i in range(1, n):
        t = times[i]
        # current H4 state: latest closed H4 bar <= t
        idx = bisect.bisect_right(h4_close_times.astype("datetime64[ns]"), t) - 1
        state = int(h4["state"].iloc[idx]) if idx >= 0 else 0

        if pos is None:
            # signal on previous bar close -> enter at this bar open
            sig = crosses[i - 1]
            if sig == 1 and state == -1:      # 超跌 + 金叉 -> 做多
                entry = opens[i]
                stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop,
                       "tp": entry + (entry - stop) * tp_r, "entry_i": i}
            elif sig == -1 and state == 1:    # 超涨 + 死叉 -> 做空
                entry = opens[i]
                stop = entry * (1.0 + stop_pct / 100.0)
                pos = {"dir": -1, "entry": entry, "stop": stop,
                       "tp": entry - (stop - entry) * tp_r, "entry_i": i}
        else:
            d = pos["dir"]
            exit_px = None
            reason = None
            # SL/TP on this bar (intrabar: conservative SL first)
            if d == 1:
                if lows[i] <= pos["stop"]:
                    exit_px, reason = pos["stop"], "SL hit"
                elif highs[i] >= pos["tp"]:
                    exit_px, reason = pos["tp"], "TP hit"
            else:
                if highs[i] >= pos["stop"]:
                    exit_px, reason = pos["stop"], "SL hit"
                elif lows[i] <= pos["tp"]:
                    exit_px, reason = pos["tp"], "TP hit"
            # reverse cross exit at this bar open (before SL/TP? after SL/TP check)
            if exit_px is None:
                rc = crosses[i]
                if rc == 1 and d == -1:
                    exit_px, reason = opens[i], "reverse cross"
                elif rc == -1 and d == 1:
                    exit_px, reason = opens[i], "reverse cross"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) * d
                pnl -= pos["entry"] * cost_pct / 100.0 * 2.0  # round-trip cost
                trades.append({
                    "signal_time": times[pos["entry_i"] - 1],
                    "entry_time": times[pos["entry_i"]],
                    "dir": d,
                    "entry": pos["entry"],
                    "stop": pos["stop"],
                    "exit_time": t,
                    "exit": exit_px,
                    "exit_reason": reason,
                    "pnl_points": pnl,
                    "holding_bars": i - pos["entry_i"],
                })
                pos = None

    tr = pd.DataFrame(trades)
    return tr


def metrics(tr, split=0.7):
    if tr is None or len(tr) == 0:
        return None
    pnl = tr["pnl_points"].to_numpy(dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gw, gl = wins.sum(), abs(losses.sum())
    n = len(tr)
    ts = pd.to_datetime(tr["signal_time"])
    cutoff = ts.min() + (ts.max() - ts.min()) * split
    test = tr[ts >= cutoff]
    tp = test["pnl_points"].to_numpy(dtype=float)
    tw, tl = tp[tp > 0].sum(), abs(tp[tp < 0].sum())
    return {
        "n": n,
        "wr": float((pnl > 0).mean() * 100.0),
        "pf": float(gw / gl if gl > 0 else 999.0),
        "ev": float(pnl.mean()),
        "pnl": float(pnl.sum()),
        "test_pf": float(tw / tl if tl > 0 else 999.0),
        "long_n": int((tr["dir"] == 1).sum()),
        "short_n": int((tr["dir"] == -1).sum()),
        "avg_hold": float(tr["holding_bars"].mean()),
        "max_dd": float(max_drawdown(pnl)),
        "sl_hits": int((tr["exit_reason"] == "SL hit").sum()),
        "tp_hits": int((tr["exit_reason"] == "TP hit").sum()),
        "rev_hits": int((tr["exit_reason"] == "reverse cross").sum()),
    }


def max_drawdown(pnl):
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def yearly(tr):
    if tr is None or len(tr) == 0:
        return pd.DataFrame()
    df = tr.copy()
    df["year"] = pd.to_datetime(df["signal_time"]).dt.year
    return df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum"),
                                  wr=("pnl_points", lambda x: (x > 0).mean() * 100)).round(2)


def main():
    rows = []
    best = None
    for thr in [1.5, 2.0, 2.5, 3.0]:
        for sp in [0.5, 0.8, 1.2]:
            for trp in [1.5, 2.0, 3.0]:
                tr = run(thr, sp, trp)
                m = metrics(tr)
                if m is None:
                    continue
                row = {"thr": thr, "stop%": sp, "tpR": trp, **m}
                rows.append(row)
                if best is None or (m["n"] >= 20 and m["pf"] > best["pf"]):
                    best = row
    df = pd.DataFrame(rows)
    df = df.sort_values("pf", ascending=False)
    pd.set_option("display.width", 200)
    print("=== 参数扫描（按 PF 排序）===")
    print(df[["thr", "stop%", "tpR", "n", "wr", "pf", "ev", "pnl", "test_pf", "long_n", "short_n", "avg_hold", "max_dd", "sl_hits", "tp_hits", "rev_hits"]].to_string(index=False))
    df.to_csv(OUT / "bias_reversal_scan.csv", index=False, encoding="utf-8-sig")

    # recommended: best with n>=20
    if best is not None:
        print()
        print("=== 推荐组合 ===")
        print(best)
        tr = run(best["thr"], best["stop%"], best["tpR"])
        tr.to_csv(OUT / "bias_reversal_trades.csv", index=False, encoding="utf-8-sig")
        print()
        print("=== 逐年 ===")
        print(yearly(tr).to_string())


if __name__ == "__main__":
    main()

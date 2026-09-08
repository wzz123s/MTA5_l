# -*- coding: utf-8 -*-
"""冷却过滤 vs 消息面过滤 对比模拟（同一交易清单、因果口径）。

冷却语义（与已部署 EA 一致）：
- cd_post: post_n 信号与上一笔同向已接受信号间隔 < N 根 M30 bar(30min) 时跳过
  (1H_M30_4H=6, 30m2H=3, 2H_M30_6H=3；原油/乖离反转无此机制)
- loss_cd: 连续 N 个亏损信号组(加权盈亏<0)后，暂停开仓 M 小时（从亏损组平仓时刻起）
  (ABC=2连亏->120h；乖离反转=做空侧 2 连 SL->120h，仅 SL 计亏、其他平仓清空；原油无)
消息面过滤: 距下一个高影响事件 < T 小时不开仓（V1，T=1/2/4/8 取总收益最优）
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
RESEARCH = ROOT / "宏观日历研究"
sys.path.insert(0, str(RESEARCH / "scripts"))
from classify_events import classify  # noqa: E402

REPORT_DIR = RESEARCH / "报告"
BAR_MIN = 30  # M30

STRATEGIES = {
    "1H_M30_4H": dict(cd_post=[3, 6], loss_thr=2, loss_hours=120),
    "30m2H":     dict(cd_post=[3], loss_thr=2, loss_hours=120),
    "2H_M30_6H": dict(cd_post=[3], loss_thr=2, loss_hours=120),
    "BiasReversal": dict(cd_post=[], loss_thr=2, loss_hours=120, loss_short_only=True, loss_sl_only=True),
    "USOIL2H":   dict(cd_post=[], loss_thr=None),
    "USOIL4H":   dict(cd_post=[], loss_thr=None),
}
NEWS_TS = [1, 2, 4, 8]


def load_events(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|", dtype={"event_id": "int64", "time": "int64"})
    df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["is_high"] = df["importance"] >= 3
    return df


def load_trades(strat: str) -> pd.DataFrame:
    path = ROOT / "observation_dashboard" / strat / "trades_snapshot.csv"
    df = pd.read_csv(path, parse_dates=["signal_time", "stage3_exit_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
    df["stage3_exit_time"] = pd.to_datetime(df["stage3_exit_time"], utc=True)
    df["dir"] = df["dir"].astype(str).str.upper()
    df["mode"] = df["mode"].astype(str)
    df["reason"] = df["stage3_reason"].astype(str)
    return df.sort_values("signal_time").reset_index(drop=True)


def stats(pts) -> dict:
    p = np.asarray(pts, dtype=float)
    if len(p) == 0:
        return {"n": 0, "win_rate": np.nan, "avg_pts": np.nan, "total_pts": 0.0, "pf": np.nan, "max_dd_pts": 0.0, "sl_total": 0.0}
    eq = np.cumsum(p)
    dd = (np.maximum.accumulate(eq) - eq).max()
    wins = p[p > 0].sum()
    losses = -p[p < 0].sum()
    return {
        "n": len(p), "win_rate": (p > 0).mean(), "avg_pts": p.mean(), "total_pts": p.sum(),
        "pf": wins / losses if losses > 0 else np.inf, "max_dd_pts": dd, "sl_total": losses,
    }


def apply_cd_post(df: pd.DataFrame, bars: int) -> pd.DataFrame:
    """post_n 同向冷却：跳过与最近已接受同向信号间隔 < bars 根 M30 bar 的 post_n 信号。"""
    if bars <= 0:
        return df
    last_time: dict[str, pd.Timestamp] = {}
    keep = []
    for _, r in df.iterrows():
        d = r["dir"]
        if r["mode"].startswith("post_n") and d in last_time:
            gap = (r["signal_time"] - last_time[d]).total_seconds() / 60.0
            if gap < bars * BAR_MIN:
                keep.append(False)
                continue
        keep.append(True)
        last_time[d] = r["signal_time"]
    return df.loc[keep].reset_index(drop=True)


def apply_loss_cd(df: pd.DataFrame, thr: int, hours: int, short_only=False, sl_only=False) -> pd.DataFrame:
    """损失冷却：连续 thr 个亏损信号组后暂停开仓 hours 小时（从亏损组平仓时刻起）。"""
    if thr is None or thr <= 0:
        return df
    streak = 0
    cd_until = None
    keep = []
    for _, r in df.iterrows():
        d = r["dir"]
        relevant = (not short_only) or (d == "S")
        if relevant and cd_until is not None and r["signal_time"] < cd_until:
            keep.append(False)
            continue
        keep.append(True)
        if relevant:
            is_loss = r["weighted_pts"] < 0 if not sl_only else (r["reason"] == "SL hit")
            if is_loss:
                streak += 1
                if streak >= thr:
                    cd_until = r["stage3_exit_time"] + pd.Timedelta(hours=hours)
            else:
                streak = 0
    return df.loc[keep].reset_index(drop=True)


def apply_news_v1(df: pd.DataFrame, high, T: float) -> pd.DataFrame:
    """消息面过滤：距下一个高影响事件 < T 小时不开仓。"""
    eh = high["time_utc"].to_numpy(dtype="datetime64[ns]")
    st = df["signal_time"].to_numpy(dtype="datetime64[ns]")
    idx = np.searchsorted(eh, st)
    gap_after = np.array([float((eh[j] - st[i]) / np.timedelta64(1, "h")) if j < len(eh) else np.nan
                          for i, j in enumerate(idx)])
    keep = gap_after >= T
    return df.loc[keep].reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(RESEARCH / "data" / "calendar_export.csv"))
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(Path(args.events))
    high = events[events["is_high"]].sort_values("time_utc").reset_index(drop=True)

    rows = []
    print(f"{'策略':<12} {'方案':<26} {'n':>4} {'WR%':>6} {'平均':>9} {'合计':>10} {'PF':>6} {'MaxDD':>9} {'SL损失':>9}")
    for strat, cfg in STRATEGIES.items():
        df = load_trades(strat)
        base = stats(df["weighted_pts"])
        rows.append({"strategy": strat, "family": "基线", "variant": "baseline", **base})
        print(f"{strat:<12} {'baseline':<26} {base['n']:>4} {base['win_rate']*100:>5.1f}% {base['avg_pts']:>9.1f} {base['total_pts']:>10.1f} {base['pf']:>6.2f} {base['max_dd_pts']:>9.1f} {base['sl_total']:>9.1f}")

        # 消息面过滤：V1 各T取总收益最优
        news_best = None
        for T in NEWS_TS:
            ndf = apply_news_v1(df, high, T)
            s = stats(ndf["weighted_pts"])
            rows.append({"strategy": strat, "family": "消息面", "variant": f"news_V1_T{T}h", **s})
            if news_best is None or s["total_pts"] > news_best[1]["total_pts"]:
                news_best = (T, s)
        Tb, nb = news_best
        print(f"{strat:<12} {'news_V1_T' + str(Tb) + 'h (最优)':<26} {nb['n']:>4} {nb['win_rate']*100:>5.1f}% {nb['avg_pts']:>9.1f} {nb['total_pts']:>10.1f} {nb['pf']:>6.2f} {nb['max_dd_pts']:>9.1f} {nb['sl_total']:>9.1f}")

        # 冷却过滤
        cur = df
        if cfg["cd_post"]:
            for bars in cfg["cd_post"]:
                cdf = apply_cd_post(cur, bars)
                s = stats(cdf["weighted_pts"])
                v = f"cd_post={bars}bar"
                rows.append({"strategy": strat, "family": "冷却", "variant": v, **s})
                print(f"{strat:<12} {v:<26} {s['n']:>4} {s['win_rate']*100:>5.1f}% {s['avg_pts']:>9.1f} {s['total_pts']:>10.1f} {s['pf']:>6.2f} {s['max_dd_pts']:>9.1f} {s['sl_total']:>9.1f}")
        if cfg["loss_thr"]:
            ldf = apply_loss_cd(cur, cfg["loss_thr"], cfg["loss_hours"],
                                short_only=cfg.get("loss_short_only", False),
                                sl_only=cfg.get("loss_sl_only", False))
            s = stats(ldf["weighted_pts"])
            v = "loss_cd 2连亏→120h"
            rows.append({"strategy": strat, "family": "冷却", "variant": v, **s})
            print(f"{strat:<12} {v:<26} {s['n']:>4} {s['win_rate']*100:>5.1f}% {s['avg_pts']:>9.1f} {s['total_pts']:>10.1f} {s['pf']:>6.2f} {s['max_dd_pts']:>9.1f} {s['sl_total']:>9.1f}")
        # cd_post(最小bar) + loss_cd 组合（已部署口径）
        if cfg["cd_post"] and cfg["loss_thr"]:
            cdf = apply_cd_post(cur, min(cfg["cd_post"]))
            cdf = apply_loss_cd(cdf, cfg["loss_thr"], cfg["loss_hours"])
            s = stats(cdf["weighted_pts"])
            v = f"cd_post{min(cfg['cd_post'])}bar+loss_cd"
            rows.append({"strategy": strat, "family": "冷却", "variant": v, **s})
            print(f"{strat:<12} {v:<26} {s['n']:>4} {s['win_rate']*100:>5.1f}% {s['avg_pts']:>9.1f} {s['total_pts']:>10.1f} {s['pf']:>6.2f} {s['max_dd_pts']:>9.1f} {s['sl_total']:>9.1f}")

        # 消息面(最优T) + 冷却组合
        ndf = apply_news_v1(df, high, Tb)
        combo = ndf
        if cfg["cd_post"]:
            combo = apply_cd_post(combo, min(cfg["cd_post"]))
        if cfg["loss_thr"]:
            combo = apply_loss_cd(combo, cfg["loss_thr"], cfg["loss_hours"],
                                  short_only=cfg.get("loss_short_only", False),
                                  sl_only=cfg.get("loss_sl_only", False))
        s = stats(combo["weighted_pts"])
        v = f"news_T{Tb}h+cd+loss_cd"
        rows.append({"strategy": strat, "family": "组合", "variant": v, **s})
        print(f"{strat:<12} {v:<26} {s['n']:>4} {s['win_rate']*100:>5.1f}% {s['avg_pts']:>9.1f} {s['total_pts']:>10.1f} {s['pf']:>6.2f} {s['max_dd_pts']:>9.1f} {s['sl_total']:>9.1f}")
        print()

    out = pd.DataFrame(rows)
    out_path = REPORT_DIR / "消息面vs冷却_对比.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print("[已输出]", out_path)


if __name__ == "__main__":
    main()

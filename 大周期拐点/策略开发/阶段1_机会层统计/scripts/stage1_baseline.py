# -*- coding: utf-8 -*-
"""
stage1_baseline.py —— 1.1 J1 历史基线表（段长/段幅 P50/P75/P90）+ 1.2 13x55 穿越统计

输出:
  data/processed/J1_历史基线表.csv    段长/段幅/持续天数 分位表（按品种+方向）
  data/processed/J2_穿越点清单_13x55.csv  黄金+原油 13x55 穿越点
  data/processed/1.2_穿越统计汇总.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage1_common as C


def segment_table(df, min_len=8):
    """从段分析结果提取段表：方向/长度(K线)/幅度%/持续天数。"""
    seg_len = df.attrs.get("seg_len")
    starts = df.attrs.get("seg_starts")
    ends = df.attrs.get("seg_ends")
    direction = df["方向_合并后"].values
    rows = []
    for s, e in zip(starts, ends):
        d = direction[s]
        # 段方向取段内主要方向（首段可能混合）
        up_cnt = int(np.sum(direction[s:e+1] == "up"))
        dn_cnt = int(np.sum(direction[s:e+1] == "down"))
        seg_dir = "up" if up_cnt >= dn_cnt else "down"
        o = df["close"].iloc[s]
        c = df["close"].iloc[e]
        amp_pct = (c / o - 1) * 100 if o else np.nan
        days = (df["time"].iloc[e] - df["time"].iloc[s]).total_seconds() / 86400
        rows.append({"seg_dir": seg_dir, "seg_len": up_cnt + dn_cnt,
                     "amp_pct": round(float(amp_pct), 3), "days": round(float(days), 1),
                     "start": str(df["time"].iloc[s]), "end": str(df["time"].iloc[e])})
    return pd.DataFrame(rows)


def baseline_table(seg: pd.DataFrame, symbol: str) -> pd.DataFrame:
    rows = []
    for d in ("up", "down"):
        sub = seg[seg["seg_dir"] == d]
        if len(sub) == 0:
            continue
        for col, label in [("seg_len", "段长K线"), ("amp_pct", "段幅%"), ("days", "持续天数")]:
            v = sub[col].dropna()
            rows.append({
                "symbol": symbol, "seg_dir": d, "metric": label,
                "n": len(v),
                "P50": round(float(v.quantile(0.50)), 2),
                "P75": round(float(v.quantile(0.75)), 2),
                "P90": round(float(v.quantile(0.90)), 2),
                "mean": round(float(v.mean()), 2),
                "max": round(float(v.max()), 2),
            })
    return pd.DataFrame(rows)


def main():
    print("== 1.1 J1 历史基线表 ==")
    all_baseline = []
    all_seg = {}
    for sym in ["XAUUSDm", "USOILm"]:
        df = C.analyze_tf(sym, "D1")
        seg = segment_table(df)
        all_seg[sym] = seg
        bt = baseline_table(seg, sym)
        all_baseline.append(bt)
        print(f"  {sym}: {len(seg)} 段 (up={len(seg[seg.seg_dir=='up'])}, "
              f"down={len(seg[seg.seg_dir=='down'])})")
        print(bt.to_string(index=False))
    bt_all = pd.concat(all_baseline, ignore_index=True)
    bt_all.to_csv(C.PROC / "J1_历史基线表.csv", index=False, encoding="utf-8-sig")
    print("  已保存 J1_历史基线表.csv")

    print()
    print("== 1.2 日线 13x55 穿越统计 ==")
    all_cross = []
    for sym in ["XAUUSDm", "USOILm"]:
        df = C.analyze_tf(sym, "D1")
        cr = C.find_cross13_55(df)
        cr.insert(0, "symbol", sym)
        all_cross.append(cr)
        # 与 5x13 段状态交叉校验：穿越后 5 根内方向状态是否与穿越方向一致
        direction = df["方向_合并后"].values
        agree = []
        for _, row in cr.iterrows():
            i = int(row["idx"])
            win = direction[i:i+6]
            if row["dir"] == 1:
                ok = any(x in ("good", "up") for x in win)
            else:
                ok = any(x in ("bad", "down") for x in win)
            agree.append(ok)
        cr["与5x13方向一致(5bar内)"] = agree
        print(f"  {sym}: {len(cr)} 次 13x55 穿越 "
              f"(上穿={int((cr['dir']==1).sum())}, 下穿={int((cr['dir']==-1).sum())})")
        print(f"    粘合临界占比={float(cr['glue'].mean())*100:.1f}%  "
              f"5x13方向一致率={float(np.mean(agree))*100:.1f}%")
    cross_all = pd.concat(all_cross, ignore_index=True)
    cross_all.to_csv(C.PROC / "J2_穿越点清单_13x55.csv", index=False, encoding="utf-8-sig")
    print("  已保存 J2_穿越点清单_13x55.csv")

    # 汇总 md
    lines = ["# 1.2 日线 13×55 穿越统计（阶段1）", ""]
    lines.append("| 品种 | 穿越次数 | 上穿 | 下穿 | 粘合占比 | 5x13方向一致率 |")
    lines.append("|---|---|---|---|---|---|")
    for sym in ["XAUUSDm", "USOILm"]:
        cr = cross_all[cross_all.symbol == sym]
        agree = cr["与5x13方向一致(5bar内)"]
        lines.append(f"| {sym} | {len(cr)} | {int((cr['dir']==1).sum())} | "
                     f"{int((cr['dir']==-1).sum())} | {float(cr['glue'].mean())*100:.1f}% | "
                     f"{float(agree.mean())*100:.1f}% |")
    lines.append("")
    lines.append("> 说明：粘合临界 = |SMA13−SMA55|/SMA55 < 0.3%；方向一致率 = 穿越后 5 根内")
    lines.append("> 5×13 段状态与穿越方向一致（上穿→good/up，下穿→bad/down）。")
    (C.PROC / "1.2_穿越统计汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 1.2_穿越统计汇总.md")


if __name__ == "__main__":
    main()

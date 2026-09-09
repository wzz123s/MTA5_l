# -*- coding: utf-8 -*-
"""Win/loss group similarity & feature-divergence review (matched 64 groups)."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")

grp = pd.read_csv(os.path.join(DST, "T1_EA匹配64笔_逐笔计算_20260910.csv"), encoding="utf-8-sig")
grp["anchor"] = pd.to_datetime(grp["anchor"])
grp["label"] = np.where(grp["net_usd"] > 0, "WIN", "LOSS")

sig = pd.read_csv(os.path.join(DST, "30m2H_strategy_signals_export_t1export4_20260910.csv"), encoding="utf-8-sig")
sig["bar_time"] = pd.to_datetime(sig["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
sig["anchor"] = sig["bar_time"] - pd.Timedelta(minutes=30)
feat = sig[["anchor", "h2_comp_bias55", "h2_comp_bias5", "h2_dir", "m30_merged_dir",
            "q2_early_pass", "h2_comp_l3_threshold"]].merge(grp, on="anchor", how="inner").drop_duplicates("anchor")
dur = (pd.to_datetime(grp["close_time"]) - pd.to_datetime(grp["anchor"])).dt.total_seconds() / 60
feat["dur_min"] = feat["anchor"].map(dict(zip(grp["anchor"], dur)))
feat["post_n"] = feat["mode"].str.extract(r"post_n(\d)").astype(float).fillna(0)
feat["is_pre"] = (feat["mode"] == "pre_cross").astype(int)
feat["is_cross"] = (feat["mode"] == "cross").astype(int)
feat["same_h2"] = ((feat["dir"] == "L") & (feat["h2_dir"] == "BULL") | (feat["dir"] == "S") & (feat["h2_dir"] == "BEAR")).astype(int)
feat["merged_same"] = ((feat["dir"] == "L") & (feat["m30_merged_dir"] == "BULL") | (feat["dir"] == "S") & (feat["m30_merged_dir"] == "BEAR")).astype(int)

num = ["h2_comp_bias55", "h2_comp_bias5", "h2_comp_l3_threshold", "post_n", "dur_min", "q2_early_pass", "same_h2", "merged_same"]
print("rows", len(feat), "WIN", int((feat.label == "WIN").sum()), "LOSS", int((feat.label == "LOSS").sum()))
for c in num:
    a = feat.loc[feat.label == "WIN", c].astype(float); b = feat.loc[feat.label == "LOSS", c].astype(float)
    pooled = np.sqrt((a.std() ** 2 + b.std() ** 2) / 2)
    d = (a.mean() - b.mean()) / pooled if pooled else np.nan
    print(f"{c}: WIN mean {a.mean():.3f} vs LOSS {b.mean():.3f} | cohen d {d:+.3f}")
for c in ["mode", "dir", "h2_dir"]:
    print("\n", c, "WIN:", feat.loc[feat.label == "WIN", c].value_counts().to_dict())
    print("  LOSS:", feat.loc[feat.label == "LOSS", c].value_counts().to_dict())

# intra-group average pairwise similarity (standardized)
Z = feat[num].astype(float)
Z = (Z - Z.mean()) / Z.std()
for lab in ("WIN", "LOSS"):
    sub = Z[feat.label == lab].values
    if len(sub) > 1:
        # sample pairs
        idx = np.arange(len(sub)); rng = np.random.default_rng(0); pairs = rng.choice(idx, size=(5000, 2), replace=True)
        dist = np.linalg.norm(sub[pairs[:, 0]] - sub[pairs[:, 1]], axis=1)
        print(lab, "mean pairwise std-dist", round(float(dist.mean()), 3), "p50", round(float(np.median(dist)), 3))

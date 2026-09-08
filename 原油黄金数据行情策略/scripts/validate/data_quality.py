# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
root = Path(r"F:\use_code\MTA5_l\原油黄金数据行情策略")
for name in ["gold_context.csv", "oil_context.csv"]:
    df = pd.read_csv(root / "data" / "processed" / name, parse_dates=["time"])
    print(f"== {name}: rows={len(df)} cols={df.shape[1]}")
    vc = df["方向"].value_counts()
    print("  方向分布:", dict(vc))
    n_good = int((df["方向"] == "good").sum()); n_bad = int((df["方向"] == "bad").sum())
    print(f"  good={n_good} bad={n_bad}")
    up = df[df["方向"] == "up"]
    if len(up) and "up_high_price" in df.columns:
        mono = bool((up["up_high_price"].dropna().diff().dropna() >= -1e-9).all())
        print("  up_high_price 单调不减:", mono)
    dn = df[df["方向"] == "down"]
    if len(dn) and "down_low_price" in df.columns:
        mono = bool((dn["down_low_price"].dropna().diff().dropna() <= 1e-9).all())
        print("  down_low_price 单调不增:", mono)
    le = df.dropna(subset=["long_entry"]); se = df.dropna(subset=["short_entry"])
    if len(le):
        print(f"  long_stop<entry 比例: {(le['long_stop'] < le['long_entry']).mean():.3f} (n={len(le)})")
    if len(se):
        print(f"  short_stop>entry 比例: {(se['short_stop'] > se['short_entry']).mean():.3f} (n={len(se)})")
    miss = df.isna().mean()
    keys = [c for c in ["SMA_5","SMA_13","SMA_55","bias55_signed_pct"] if c in miss.index]
    keys += [c for c in df.columns if c.endswith("_bias55_signed_pct")][:3]
    print("  缺失率:", {c: round(float(miss[c]),4) for c in keys})
for mf in ["raw_source_manifest_gold.json","raw_source_manifest_oil.json"]:
    m = json.load(open(root / "data" / "raw" / mf, encoding="utf-8-sig"))
    exist = all(Path(f["path"]).exists() for f in m["files"])
    print(f"{mf}: strategy={m['strategy']} symbol={m['symbol']} files={len(m['files'])} all_exist={exist}")
print("QUALITY_CHECK_DONE")

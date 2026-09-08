
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\宏观日历研究\scripts")
import pandas as pd
from cooldown_vs_news import load_trades, apply_loss_cd, apply_cd_post

for strat, short_only, sl_only in [("1H_M30_4H", False, False), ("2H_M30_6H", False, False), ("BiasReversal", True, True)]:
    df = load_trades(strat)
    out = apply_loss_cd(df, 2, 120, short_only=short_only, sl_only=sl_only)
    print(f"== {strat}: n={len(df)} -> {len(out)} (skip {len(df)-len(out)})")
    # 抽查: 计算触发次数
    streak = 0; cd_until = None; triggers = 0; first_skips = []
    for _, r in df.iterrows():
        relevant = (not short_only) or (r["dir"] == "S")
        skipped = relevant and cd_until is not None and r["signal_time"] < cd_until
        if skipped:
            if len(first_skips) < 3:
                first_skips.append((str(r["signal_time"]), r["dir"], round(r["weighted_pts"],1)))
            continue
        if relevant:
            is_loss = r["weighted_pts"] < 0 if not sl_only else (r["reason"] == "SL hit")
            if is_loss:
                streak += 1
                if streak >= 2:
                    triggers += 1
                    cd_until = r["stage3_exit_time"] + pd.Timedelta(hours=120)
            else:
                streak = 0
    print(f"   触发次数={triggers}, 首批跳过: {first_skips}")
    # 验证跳过交易合计
    skip_mask = df["signal_time"].isin(out["signal_time"]) == False
    print(f"   被跳过交易合计={df.loc[skip_mask, 'weighted_pts'].sum():.1f}, 保留合计={out['weighted_pts'].sum():.1f}")

# cd_post抽查
df = load_trades("1H_M30_4H")
out6 = apply_cd_post(df, 6)
print("\n== 1H_M30_4H cd_post=6:", len(df), "->", len(out6))
# 检查是否还有违反（同向post_n 3h内）
last = {}
viol = 0
for _, r in out6.iterrows():
    d = r["dir"]
    if r["mode"].startswith("post_n") and d in last:
        gap = (r["signal_time"] - last[d]).total_seconds()/3600
        if gap < 3.0: viol += 1
    last[d] = r["signal_time"]
print("   残留违反:", viol)

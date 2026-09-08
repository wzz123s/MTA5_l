# -*- coding: utf-8 -*-
"""1H_M30_4H_ABC_EA 变体细化测试 v2

新增维度：
  - cd 灵敏度: 2/3/4/6 根（1h/1.5h/2h/3h）
  - cd_post: 只对 post_n 信号做同向冷却（cross/pre_cross 不限制）
  - per_dir cap: 按方向限制并发（多/空互不阻塞）
  - defer: 容量满时排队等待（最多等 W 根 bar，到期未释放则放弃）——EA 原意"后续信号等待"
诊断：
  - 被跳过信号的事后盈亏（跳过的是赢家还是输家）
  - 基线按信号模式（pre_cross/cross/post_n）的盈亏构成
  - 推荐配置的年度分解
"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\research")
import heapq
import numpy as np
import pandas as pd
from replay_1h_bias55_h1_stop_optimization import load_frames
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum
from experiment_1h_m30_4h_variants_20260813 import add_m30_state
from experiment_1h_m30_4h_combined_20260813 import build_combined_trades

manifest, m30, h1, contexts = load_frames()
h4 = contexts["4H"]
h1_way = add_h1_way_and_momentum(h1)
m30_state = add_m30_state(m30)
trades = build_combined_trades(m30, h1_way, h4, 5.0, 35.0, 0.6)
trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
keep = []
for _, tr in trades.iterrows():
    m = str(tr["mode"])
    if m.startswith("post_n"):
        v = int(m[len("post_n"):])
        if v < 2 or v > 4:
            keep.append(False); continue
    keep.append(True)
trades = trades.loc[keep].reset_index(drop=True)

STAGE1_R = 1.5; TRAIL_R = 1.5; FORCE_R = 4.0
UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
direction_merged = m30_state["方向_合并后"].values.astype(object)
opens_arr = m30_state["open"].to_numpy(dtype=float)

def first_opposite_idx(i, is_long):
    opp = "bad" if is_long else "good"
    for j in range(i + 1, len(direction_merged)):
        if direction_merged[j] == opp:
            return j
    return len(direction_merged) - 1

def stage_exits(entry_idx, is_long, entry, stop):
    r = abs(entry - stop)
    rows = []
    tgt = entry + STAGE1_R * r if is_long else entry - STAGE1_R * r
    out = None
    for j in range(entry_idx, len(m30_state)):
        row = m30_state.iloc[j]
        if is_long:
            if row["low"] <= stop: out = (-r, "SL hit", j); break
            if row["high"] >= tgt: out = (STAGE1_R * r, "1.5R TP", j); break
        else:
            if row["high"] >= stop: out = (-r, "SL hit", j); break
            if row["low"] <= tgt: out = (STAGE1_R * r, "1.5R TP", j); break
    if out is None: out = (0.0, "data end", len(m30_state) - 1)
    rows.append(out)
    trail_start = entry + TRAIL_R * r if is_long else entry - TRAIL_R * r
    force = entry + FORCE_R * r if is_long else entry - FORCE_R * r
    trail_sl = stop
    m30_end = first_opposite_idx(entry_idx, is_long)
    out = None
    for j in range(entry_idx, m30_end + 1):
        row = m30_state.iloc[j]
        if is_long:
            if row["high"] >= force: out = (FORCE_R * r, "4R forced", j); break
            if row["low"] <= trail_sl: out = (trail_sl - entry, "trail/SL", j); break
            if row["high"] >= trail_start and row["SMA_13"] > trail_sl: trail_sl = row["SMA_13"]
        else:
            if row["low"] <= force: out = (FORCE_R * r, "4R forced", j); break
            if row["high"] >= trail_sl: out = (entry - trail_sl, "trail/SL", j); break
            if row["low"] <= trail_start and (row["SMA_13"] < trail_sl or trail_sl == stop): trail_sl = row["SMA_13"]
    if out is None:
        exit_price = float(m30_state.iloc[m30_end]["close"])
        out = ((exit_price - entry) if is_long else (entry - exit_price), "merged cross", m30_end)
    rows.append(out)
    out = None
    for j in range(entry_idx, m30_end + 1):
        row = m30_state.iloc[j]
        if is_long and row["low"] <= stop: out = (-r, "SL hit", j); break
        if (not is_long) and row["high"] >= stop: out = (-r, "SL hit", j); break
    if out is None:
        exit_price = float(m30_state.iloc[m30_end]["close"])
        out = ((exit_price - entry) if is_long else (entry - exit_price), "merged cross", m30_end)
    rows.append(out)
    return rows

SIG = []
for _, tr in trades.iterrows():
    SIG.append({
        "i": len(SIG),
        "signal_bar_idx": int(tr["signal_bar_idx"]),
        "entry_bar_idx": int(tr["entry_bar_idx"]),
        "signal_time": pd.Timestamp(tr["signal_time"]),
        "dir": str(tr["dir"]).upper(),
        "mode": str(tr["mode"]),
        "entry0": float(tr["entry"]), "stop": float(tr["stop"]),
        "stages0": stage_exits(int(tr["entry_bar_idx"]), str(tr["dir"]).upper() == "L",
                               float(tr["entry"]), float(tr["stop"])),
        "exit0_idx": max(s[2] for s in stage_exits(int(tr["entry_bar_idx"]), str(tr["dir"]).upper() == "L",
                            float(tr["entry"]), float(tr["stop"]))),
    })

def run_variant(cap=None, cd=None, cd_post=False, per_dir=False, defer=False, defer_w=6,
                post_weight=1.0, loss_cd_bars=None, loss_cd_thr=2):
    open_list = []   # (exit_idx, dir)
    last_cd = {}
    accepted, skipped, deferred = [], 0, 0
    max_conc = 0
    queue = []       # deferred signal indices
    close_heap = []  # (exit_idx, group_pnl) 损失冷却用
    loss_streak = 0
    cd_until = -1
    cd_blocks = 0

    def process_closes(up_to_bar):
        nonlocal loss_streak, cd_until, cd_blocks
        while close_heap and close_heap[0][0] <= up_to_bar:
            _, gpnl = heapq.heappop(close_heap)
            if gpnl < 0:
                loss_streak += 1
                if loss_cd_bars and loss_streak >= loss_cd_thr:
                    cd_until = up_to_bar + loss_cd_bars
                    cd_blocks += 1
            else:
                loss_streak = 0

    for r in SIG:
        process_closes(r["signal_bar_idx"])
        if loss_cd_bars and r["signal_bar_idx"] < cd_until:
            skipped += 1
            continue
        open_list = [o for o in open_list if o[0] >= r["signal_bar_idx"]]
        # process queue first: try to admit queued signals (FIFO)
        if defer and queue:
            newq = []
            for qi in queue:
                if cap is not None and len(open_list) >= cap:
                    newq.append(qi); continue
                q = SIG[qi]
                if r["signal_bar_idx"] - q["entry_bar_idx"] > defer_w:
                    skipped += 1; continue   # waited too long -> drop
                entry = opens_arr[r["signal_bar_idx"]]
                stop = q["stop"]
                sd = abs(entry - stop)
                if sd < 5.0 or sd > 35.0:
                    skipped += 1; continue
                st = stage_exits(r["signal_bar_idx"], q["dir"] == "L", entry, stop)
                open_list.append((max(s[2] for s in st), q["dir"]))
                accepted.append(("DEFER", q, r["signal_bar_idx"], entry, stop, st, post_weight))
                last_cd[q["dir"]] = r["signal_bar_idx"]
                gp = sum(pnl * UNITS[sti] for sti, (pnl, _, _) in enumerate(st, start=1))
                heapq.heappush(close_heap, (max(s[2] for s in st), gp))
            queue = newq
        # same-direction cooldown
        cd_ok = True
        if cd is not None:
            prev = last_cd.get(r["dir"])
            if prev is not None and r["signal_bar_idx"] - prev < cd:
                if not (cd_post and not r["mode"].startswith("post_n")):
                    cd_ok = False
        if not cd_ok:
            skipped += 1
            continue
        # capacity check
        cnt = sum(1 for o in open_list if o[1] == r["dir"]) if per_dir else len(open_list)
        if cap is not None and cnt >= cap:
            if defer:
                queue.append(r["i"]); deferred += 1
            else:
                skipped += 1
            continue
        open_list.append((r["exit0_idx"], r["dir"]))
        accepted.append(("LIVE", r, r["entry_bar_idx"], r["entry0"], r["stop"], r["stages0"], post_weight))
        last_cd[r["dir"]] = r["signal_bar_idx"]
        max_conc = max(max_conc, len(open_list))
        gp = sum(pnl * UNITS[sti] for sti, (pnl, _, _) in enumerate(r["stages0"], start=1))
        heapq.heappush(close_heap, (r["exit0_idx"], gp))
    return accepted, skipped, deferred, max_conc, cd_blocks

def metrics(acc):
    rows = []
    for kind, r, eidx, entry, stop, st, pw in acc:
        for sti, (pnl, reason, idx) in enumerate(st, start=1):
            wmult = pw if r["mode"].startswith("post_n") else 1.0
            rows.append({"signal_time": r["signal_time"], "dir": r["dir"], "mode": r["mode"],
                         "w": pnl * UNITS[sti] * wmult})
    if not rows:
        return None
    df = pd.DataFrame(rows)
    per = df.groupby("signal_time").agg(w=("w", "sum"), mode=("mode", "first")).reset_index()
    w = per["w"].to_numpy(dtype=float)
    wins, losses = w[w > 0], w[w < 0]
    gw, gl = wins.sum(), abs(losses.sum())
    ts = pd.to_datetime(per["signal_time"])
    cutoff = ts.min() + (ts.max() - ts.min()) * 0.7
    test = per.loc[ts >= cutoff, "w"].to_numpy(dtype=float)
    tw, tl = test[test > 0].sum(), abs(test[test < 0].sum())
    return {"n": len(per), "wr": (w > 0).mean() * 100, "pf": gw / gl if gl > 0 else 999,
            "ev": w.mean(), "pnl": w.sum(), "test_pf": tw / tl if tl > 0 else 999,
            "yearly": per.assign(y=ts.dt.year).groupby("y")["w"].sum(),
            "mode_pnl": per.groupby("mode")["w"].sum().to_dict()}

def cluster_max(acc, window=6):
    ts = sorted(r["signal_bar_idx"] for _, r, *_ in acc)  # noqa
    mx = 0
    for t in ts:
        mx = max(mx, sum(1 for t2 in ts if 0 <= t2 - t <= window))
    return mx

CONFIGS = [
    ("基线", dict()),
    ("cd_post=3（已部署）", dict(cd=3, cd_post=True)),
    ("cd_post=3 + cap=1", dict(cd=3, cd_post=True, cap=1)),
    ("cd_post=3 + 损失冷却24h", dict(cd=3, cd_post=True, loss_cd_bars=48, loss_cd_thr=2)),
    ("cd_post=3 + 损失冷却60h", dict(cd=3, cd_post=True, loss_cd_bars=120, loss_cd_thr=2)),
    ("cd_post=3 + 损失冷却5天", dict(cd=3, cd_post=True, loss_cd_bars=240, loss_cd_thr=2)),
    ("cd_post=3 + 损失冷却5天×3连", dict(cd=3, cd_post=True, loss_cd_bars=240, loss_cd_thr=3)),
    ("cap=1（硬顶）", dict(cap=1)),
    ("cap=2（硬顶）", dict(cap=2)),
    ("损失冷却5天（单独）", dict(loss_cd_bars=240, loss_cd_thr=2)),
]
base_m = None
print()
print("%-24s %4s %6s %6s %7s %8s %5s %7s %4s %4s %4s %5s %4s" % (
    "配置", "n", "WR%", "PF", "EV", "总加权", "保留%", "SL损失", "SL数", "跳过", "并发", "3h聚集", "冷却次数"))
rows_out = []
for name, kw in CONFIGS:
    acc, skipped, deferred, mc, cd_blocks = run_variant(**kw)
    m = metrics(acc)
    max_pos = max((sum(1 for _, rr, *_ in acc if rr["signal_bar_idx"] <= t <= rr["exit0_idx"])) for t in [r["signal_bar_idx"] for _, r, *_ in acc]) if acc else 0
    # 止损损失合计（负收益信号组的加权盈亏和）
    sl_loss = 0.0
    sl_cnt = 0
    for _, rr, _, _, _, st, pw in acc:
        gp = sum(pnl * UNITS[sti] * (pw if rr["mode"].startswith("post_n") else 1.0) for sti, (pnl, _, _) in enumerate(st, start=1))
        if gp < 0:
            sl_loss += gp
            sl_cnt += 1
    if name == "基线":
        base_m = m
    pct = m["pnl"] / base_m["pnl"] * 100 if base_m and base_m["pnl"] else 0
    print("%-24s %4d %6.1f %6.3f %7.2f %8.0f %5.0f %7.0f %4d %4d %4d %5d %4d" % (
        name, m["n"], m["wr"], m["pf"], m["ev"], m["pnl"], pct, sl_loss, sl_cnt, skipped, mc, cluster_max(acc), cd_blocks))
    rows_out.append((name, m, skipped, deferred, mc, acc))

# 诊断1: 基线按模式
print()
print("=== 基线信号模式构成 ===")
tot = 0
for mode, pnl in sorted(base_m["mode_pnl"].items()):
    print("  %-10s %10.0f" % (mode, pnl))
    tot += pnl
print("  合计 %10.0f" % tot)

# 诊断2: cd=6 被跳过的信号事后盈亏（若未被跳过会怎样）
print()
print("=== 被跳过信号的'事后盈亏'（若基线允许进入）===")
for name, kw in [("cd_post=3", dict(cd=3, cd_post=True)), ("cd_post=6", dict(cd=6, cd_post=True)), ("cd=3", dict(cd=3))]:
    acc, skipped, deferred, mc, cd_blocks = run_variant(**kw)
    acc_ts = {str(r["signal_time"]) for _, r, *_ in acc}
    sk_ts = [r for r in SIG if str(r["signal_time"]) not in acc_ts]
    wp = 0.0; wn = 0; wl = 0
    for r in sk_ts:
        st = r["stages0"]
        w = sum(pnl * UNITS[sti] for sti, (pnl, _, _) in enumerate(st, start=1))
        wp += w; wn += 1 if w > 0 else 0; wl += 1 if w < 0 else 0
    print("  %-14s 跳过=%d  事后盈亏=%+.0f  (赢%d/输%d)" % (name, len(sk_ts), wp, wn, wl))

# 诊断3: 推荐配置年度
print()
print("=== 年度对比（基线 vs cd=3 vs defer cap=3）===")
for name, kw in [("基线", dict()), ("cd_post=3", dict(cd=3, cd_post=True)), ("损失冷却5天", dict(loss_cd_bars=240, loss_cd_thr=2))]:
    acc, *_ = run_variant(**kw)
    m = metrics(acc)
    y = m["yearly"]
    print("  %-14s %s" % (name, " ".join("%d:%+.0f" % (yr, v) for yr, v in y.items())))

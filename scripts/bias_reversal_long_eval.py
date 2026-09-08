# -*- coding: utf-8 -*-
"""乖离反转：超跌做多镜像评估（用户逻辑：上一段下跌极值 wsw/vwsw>=0.5 + 下跌K线根数 + 下跌幅度）

做多镜像（与 EA 做空 Check2HShortSetup 完全对称）：
  门(H4 超跌): close < SMMA5 且 close < SMMA55 且 bias55 <= -3.5%（最新已收盘 H4 bar）
  2H 段结构（600 根窗口，S5/S13 交叉分段）:
    1. 当前段必须为 down 段（S5<S13），上一段必须为 up 段
    2. 下跌幅度 fall = (上一段 SMA13 最高 - 当前段 SMA13 最低) / 上一段最高 x 100 >= 3.0%
    3. 段极值（最低 low bar）的 way_s_way / vol_way_s_way >= 0.5
    4. 当前 down 段 K 线根数 y >= 3
  开仓: 信号 2H bar 收盘后下一根 2H bar 开盘价做多
  止损: 信号 bar 收盘价 x 0.988（固定 1.2%）；止盈 3R；退出: SL/TP/2H 死叉
"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
import json
import bisect
from pathlib import Path
import numpy as np
import pandas as pd
from bias_reversal_replay import pipeline, _smma

ROOT = Path(r"F:\use_code\MTA5_l")
manifest = json.loads((ROOT / "黄金" / "乖离反转策略" / "data" / "raw" / "raw_source_manifest.json").read_text(encoding="utf-8-sig"))
B = Path(manifest["bundle_dir"])
h4 = pipeline(str(B / "XAUUSDm_H4.csv"), "4H")
h2 = pipeline(str(B / "XAUUSDm_H2.csv"), "2H")


def down_setup(frame, i, s5, s13, fall_thr=3.0, w_thr=0.5, len_min=3, vol_win=600, detail=False):
    """做空 Check2HShortSetup 的镜像：返回 (fall, wsw, vwsw, y, ok, detail_dict)。"""
    n = frame.shape[0]
    vol = frame["volume"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    win0 = max(0, i - vol_win + 1)
    vsum = 0.0; cnt = 0
    vol_ma = np.full(n, np.nan)
    for j in range(win0, i + 1):
        vsum += vol[j]; cnt += 1
        vol_ma[j] = vsum / cnt
    seg_start = win0
    seg_up = s5[win0] > s13[win0]
    for j in range(win0 + 1, i + 1):
        up = s5[j] > s13[j]
        if up != seg_up:
            seg_up = up; seg_start = j
    if seg_up:
        return (None, None, None, None, False, None)  # 当前段必须 down
    prev_end = seg_start - 1
    if prev_end < win0:
        return (None, None, None, None, False, None)
    prev_up = s5[prev_end] > s13[prev_end]
    prev_start = win0
    for j in range(prev_end - 1, win0 - 1, -1):
        up = s5[j] > s13[j]
        if up != prev_up:
            prev_start = j + 1; break
    if not prev_up:
        return (None, None, None, None, False, None)  # 上一段必须 up
    seg = s13[prev_start:prev_end + 1]
    if not (seg > 0).any():
        return (None, None, None, None, False, None)
    prev_max = float(seg.max())
    y = x = z = 0
    cur_min = np.inf
    ext_idx = -1; ext_low = np.inf
    ext_wsw = 0.0; ext_vwsw = 0.0
    for j in range(seg_start, i + 1):
        y += 1
        if highs[j] <= s13[j] and lows[j] <= lows[j - 1]:
            x += 1
        if vol[j] <= vol_ma[j]:
            z += 1
        if s13[j] < cur_min:
            cur_min = s13[j]
        if lows[j] < ext_low:
            ext_low = lows[j]; ext_idx = j
        if ext_idx == j:
            ext_wsw = x / y if y > 0 else 0.0
            ext_vwsw = z / y if y > 0 else 0.0
    if y < len_min or not np.isfinite(cur_min) or cur_min >= np.inf:
        return (None, None, None, None, False, None)
    fall = (prev_max - cur_min) / prev_max * 100.0
    ok = fall >= fall_thr and ext_wsw >= w_thr and ext_vwsw >= w_thr
    det = None
    if detail:
        det = {
            "bar": pd.Timestamp(frame["bar_close_time"].iloc[i]),
            "seg_start": seg_start, "i": i, "y": y, "x": x, "z": z,
            "wsw": ext_wsw, "vwsw": ext_vwsw, "fall": fall,
            "prev_start": prev_start, "prev_end": prev_end, "prev_max": prev_max,
            "cur_min": cur_min, "ext_low": ext_low, "ext_idx": ext_idx,
            "gate_bias55": None,
        }
    return (fall, ext_wsw, ext_vwsw, y, ok, det)


def h4_gate_state(t):
    b55 = (h4["close"] - pd.to_numeric(h4["SMA_55"], errors="coerce")) / pd.to_numeric(h4["SMA_55"], errors="coerce") * 100.0
    s5 = pd.to_numeric(h4["SMA_5"], errors="coerce")
    s55 = pd.to_numeric(h4["SMA_55"], errors="coerce")
    gt = h4["bar_close_time"].to_numpy()
    gi = bisect.bisect_right(gt, t) - 1
    if gi < 0:
        return False, None
    return bool(h4["close"].iloc[gi] < s5.iloc[gi] and h4["close"].iloc[gi] < s55.iloc[gi] and b55.iloc[gi] <= -3.5), float(b55.iloc[gi])


def replay_long_mirror(fall_thr=3.0, w_thr=0.5, len_min=3, gate_thr=3.5, stop_pct=1.2, tp_r=3.0):
    closes = h2["close"].to_numpy(dtype=float)
    opens = h2["open"].to_numpy(dtype=float)
    highs = h2["high"].to_numpy(dtype=float)
    lows = h2["low"].to_numpy(dtype=float)
    times = h2["bar_close_time"].to_numpy()
    n = len(h2)
    s5 = _smma(closes, 5)
    s13 = _smma(closes, 13)
    trades = []
    pos = None
    last_detail = None
    for i in range(1, n - 1):
        t = times[i]
        if pos is None:
            gok, gb = h4_gate_state(t)
            if gok:
                r = down_setup(h2, i, s5, s13, fall_thr, w_thr, len_min, detail=True)
                if r[4]:
                    entry = opens[i + 1]
                    stop = closes[i] * (1.0 - stop_pct / 100.0)
                    pos = {"entry": entry, "stop": stop,
                           "tp": entry + (entry - stop) * tp_r,
                           "signal_time": times[i], "entry_i": i + 1}
                    r[5]["gate_bias55"] = gb
                    last_detail = r[5]
        else:
            exit_px = None; reason = None
            if lows[i] <= pos["stop"]:
                exit_px, reason = pos["stop"], "SL hit"
            elif highs[i] >= pos["tp"]:
                exit_px, reason = pos["tp"], "TP hit"
            elif s5[i] < s13[i] and s5[i - 1] >= s13[i - 1]:
                exit_px, reason = opens[i + 1], "dead cross"
            if exit_px is not None:
                trades.append({"signal_time": pos["signal_time"], "dir": "L",
                               "entry": pos["entry"], "stop": pos["stop"],
                               "pnl_points": exit_px - pos["entry"],
                               "exit_time": times[i] if reason in ("SL hit", "TP hit") else times[i + 1],
                               "exit_price": exit_px, "exit_reason": reason})
                pos = None
    if pos is not None:
        trades.append({"signal_time": pos["signal_time"], "dir": "L",
                       "entry": pos["entry"], "stop": pos["stop"],
                       "pnl_points": closes[n - 2] - pos["entry"],
                       "exit_time": times[n - 2], "exit_price": closes[n - 2], "exit_reason": "open"})
    return pd.DataFrame(trades), last_detail


def stats(tr):
    if tr is None or len(tr) == 0:
        return None
    pnl = tr["pnl_points"].to_numpy(dtype=float)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    gw, gl = wins.sum(), abs(losses.sum())
    ts = pd.to_datetime(tr["signal_time"])
    cutoff = ts.min() + (ts.max() - ts.min()) * 0.7
    test = tr[ts >= cutoff]["pnl_points"].to_numpy(dtype=float)
    tw, tl = test[test > 0].sum(), abs(test[test < 0].sum())
    return {"n": len(tr), "wr": float((pnl > 0).mean() * 100), "pf": float(gw / gl if gl > 0 else 999),
            "ev": float(pnl.mean()), "pnl": float(pnl.sum()),
            "test_pf": float(tw / tl if tl > 0 else 999),
            "long_n": int((tr["dir"].astype(str).str.upper() == "L").sum()),
            "short_n": int((tr["dir"].astype(str).str.upper() == "S").sum()),
            "exit": tr["exit_reason"].value_counts().to_dict()}


tr, det = replay_long_mirror()
m = stats(tr)
print("=== 超跌做多镜像（H4 bias55<=-3.5% + 2H down段 fall>=3% + 极值wsw/vwsw>=0.5 + y>=3）===")
print("n=%s wr=%.1f%% pf=%.3f ev=%.2f pnl=%.1f test_pf=%.3f" % (
    m["n"], m["wr"], m["pf"], m["ev"], m["pnl"], m["test_pf"]))
print("exit:", m["exit"])
if det:
    print("最近信号指标明细:", {k: (str(v) if not isinstance(v, (int, float)) else round(v, 3)) for k, v in det.items()})

# 灵敏度网格: len_min x fall_thr
print()
print("=== 灵敏度（len_min x fall_thr，w=0.5，门-3.5%）===")
for lm in [3, 5, 8]:
    row = []
    for ft in [2.0, 3.0, 4.0]:
        t2, _ = replay_long_mirror(fall_thr=ft, len_min=lm)
        m2 = stats(t2)
        if m2:
            row.append("fall%s: n=%d pf=%.3f pnl=%.0f" % (ft, m2["n"], m2["pf"], m2["pnl"]))
        else:
            row.append("fall%s: -" % ft)
    print("len>=%d | %s" % (lm, " | ".join(row)))

print()
print("=== 门阈值灵敏度（bias55 <= -thr，fall=3%，len>=3）===")
for gthr in [2.5, 3.0, 3.5]:
    t2, _ = replay_long_mirror(gate_thr=gthr)
    m2 = stats(t2)
    if m2:
        print("gate -%s%%: n=%d wr=%.1f%% pf=%.3f ev=%.2f pnl=%.0f test_pf=%.3f" % (gthr, m2["n"], m2["wr"], m2["pf"], m2["ev"], m2["pnl"], m2["test_pf"]))

# 年度分解（主配置）
print()
print("=== 年度（主配置）===")
if len(tr):
    df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
    y = df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum"),
                               wr=("pnl_points", lambda x: (x > 0).mean() * 100)).round(2)
    print(y.to_string())
    tr.to_csv(ROOT / "黄金" / "乖离反转策略" / "data" / "validation" / "bias_reversal_long_mirror_trades.csv",
              index=False, encoding="utf-8-sig")

# 对照：当前 EA 做空（H4超涨门+2H up段）与当前做多（6H门+H1金叉），同一数据窗口
print()
print("=== 对照（同一 2018+ 数据窗口）===")
from bias_reversal_replay import replay_short, replay_long
st_s = replay_short(pipeline(str(B / "XAUUSDm_H4.csv"), "4H"), h2)
m_s = stats(st_s.rename(columns={"stage_pnl": "pnl_points", "stage_exit_time": "exit_time", "stage_exit_price": "exit_price", "stage_reason": "exit_reason"}))
h1 = pipeline(str(B / "XAUUSDm_H1.csv"), "1H")
h6 = pipeline(str(B / "XAUUSDm_H6.csv"), "6H")
st_l = replay_long(h6, h1)
m_l = stats(st_l.rename(columns={"stage_pnl": "pnl_points", "stage_exit_time": "exit_time", "stage_exit_price": "exit_price", "stage_reason": "exit_reason"}))
print("当前做空(H4超涨+2H up段): n=%d wr=%.1f%% pf=%.3f pnl=%.1f test_pf=%.3f" % (m_s["n"], m_s["wr"], m_s["pf"], m_s["pnl"], m_s["test_pf"]))
print("当前做多(6H门+H1金叉):     n=%d wr=%.1f%% pf=%.3f pnl=%.1f test_pf=%.3f" % (m_l["n"], m_l["wr"], m_l["pf"], m_l["pnl"], m_l["test_pf"]))
print("新做多镜像(超跌+2H down段): n=%d wr=%.1f%% pf=%.3f pnl=%.1f test_pf=%.3f" % (m["n"], m["wr"], m["pf"], m["pnl"], m["test_pf"]))

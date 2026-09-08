# -*- coding: utf-8 -*-
"""空单方向过滤因子扫描：在修复 BUG-1 后的空单上，扫描能否把 PF 抬到 1 以上。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRAT = ROOT / "原油" / "原油2H策略"
MANIFEST = json.loads((STRAT / "data" / "raw" / "raw_source_manifest.json").read_text(encoding="utf-8-sig"))

def manifest_file(tf):
    for it in MANIFEST["files"]:
        if it["timeframe"].upper() == tf.upper():
            return Path(it["path"])
    raise KeyError(tf)

# ---------- 指标 ----------
def calc_smma(s, n, m=1):
    sma = pd.Series(np.nan, index=s.index, dtype=float)
    if len(s) >= n:
        sma.iloc[n-1] = s.iloc[:n].mean()
        for i in range(n, len(s)):
            sma.iloc[i] = (m*s.iloc[i] + (n-m)*sma.iloc[i-1])/n
    return sma

def mark_direction(df):
    out = df.copy()
    valid = out["SMA_13"].notna() & out["SMA_5"].notna()
    out["方向"] = None
    scoped = out.loc[valid].copy()
    gt = scoped["SMA_5"] > scoped["SMA_13"]
    prev = gt.shift(1, fill_value=False)
    scoped["方向"] = np.select([gt & ~prev, ~gt & prev, gt & prev, ~gt & ~prev], ["good","bad","up","down"], default=None)
    scoped.loc[scoped.index[0], "方向"] = "up" if bool(gt.loc[scoped.index[0]]) else "down"
    out.loc[scoped.index, "方向"] = scoped["方向"]
    return out

def filter_short_segments(df, min_len=8):
    out = df.copy()
    direction = out["方向"].values.astype(object)
    n = len(out)
    good_pos = np.where(direction == "good")[0]
    bad_pos = np.where(direction == "bad")[0]
    crossings = sorted([(int(p),"good") for p in good_pos] + [(int(p),"bad") for p in bad_pos])
    if not crossings:
        out["方向_合并后"] = direction
        return out
    _, first_type = crossings[0]
    state = "down" if first_type == "good" else "up"
    i = 0
    while i < len(crossings):
        pos, typ = crossings[i]
        if i+1 >= len(crossings):
            break
        nxt, _ = crossings[i+1]
        region = direction[pos+1:nxt] if pos+1 < nxt else np.array([], dtype=object)
        rc = int(np.sum(region == ("up" if typ=="good" else "down")))
        if rc < min_len:
            direction[pos] = state
            for k in range(pos+1, nxt): direction[k] = state
            direction[nxt] = state
            crossings.pop(i+1); crossings.pop(i)
        else:
            state = "up" if typ=="good" else "down"
            i += 1
    out["方向_合并后"] = direction
    return out

def add_way_grade(df):
    out = df.copy()
    direction = out["方向_合并后"].values if "方向_合并后" in out.columns else out["方向"].values
    sma13 = pd.to_numeric(out["SMA_13"], errors="coerce").to_numpy()
    low = pd.to_numeric(out["low"], errors="coerce").to_numpy()
    high = pd.to_numeric(out["high"], errors="coerce").to_numpy()
    vol = pd.to_numeric(out["volume"], errors="coerce").fillna(0).to_numpy()
    vol_ma = pd.to_numeric(out["vol_ma_120"], errors="coerce").fillna(0).to_numpy()
    way=np.zeros(len(out)); way_s=np.zeros(len(out)); way_s_way=np.zeros(len(out))
    vol_way=np.zeros(len(out)); vol_way_s_way=np.zeros(len(out))
    y=x=z=0; prev_d=None
    for i,d in enumerate(direction):
        if d in ("good","bad"): y=x=z=0; wsw=0.0; vwsw=0.0
        elif d=="up":
            if prev_d=="up":
                y+=1
                if low[i]>=sma13[i] and high[i]>=high[i-1]: x+=1
                if vol[i]<=vol_ma[i]: z+=1
            else: y=1; x=1; z=1 if vol[i]<=vol_ma[i] else 0
            wsw=round(x/y,2) if y else 0.0; vwsw=round(z/y,2) if y else 0.0
        elif d=="down":
            if prev_d=="down":
                y-=1
                if high[i]<=sma13[i] and low[i]<=low[i-1]: x-=1
                if vol[i]<=vol_ma[i]: z-=1
            else: y=-1; x=-1; z=-1 if vol[i]<=vol_ma[i] else 0
            wsw=round(x/y,2) if y else 0.0; vwsw=round(z/y,2) if y else 0.0
        else: wsw=0.0; vwsw=0.0
        way[i]=y; way_s[i]=x; way_s_way[i]=wsw; vol_way[i]=z; vol_way_s_way[i]=vwsw
        prev_d=d
    out["way"]=way; out["way_s"]=way_s; out["way_s_way"]=way_s_way
    out["vol_way"]=vol_way; out["vol_way_s_way"]=vol_way_s_way
    return out

# ---------- 数据加载 ----------
def load_h2():
    p = manifest_file("H2")
    raw = pd.read_csv(p)
    d = pd.to_datetime(raw["date_utc"], utc=True).dt.tz_convert(None) + pd.to_timedelta(2, unit="h")
    out = pd.DataFrame({
        "date": d, "open": pd.to_numeric(raw["open"], errors="coerce"),
        "high": pd.to_numeric(raw["high"], errors="coerce"),
        "low": pd.to_numeric(raw["low"], errors="coerce"),
        "close": pd.to_numeric(raw["close"], errors="coerce"),
        "volume": pd.to_numeric(raw["tick_volume"], errors="coerce").fillna(0),
    }).dropna(subset=["date","open","high","low","close"]).sort_values("date").reset_index(drop=True)
    out["SMA_5"] = calc_smma(out["close"], 5)
    out["SMA_13"] = calc_smma(out["close"], 13)
    out["vol_ma_120"] = out["volume"].rolling(120, min_periods=1).mean()
    return out

def causal_confirm(frame, i, min_len=8):
    j2 = min(i+2, len(frame)-1)
    win = frame.iloc[:j2+1].copy().reset_index(drop=True)
    w = add_way_grade(filter_short_segments(mark_direction(win), min_len=min_len))
    return (float(w.iloc[-2]["way_s_way"]), float(w.iloc[-1]["way_s_way"]),
            float(w.iloc[-2]["vol_way_s_way"]), float(w.iloc[-1]["vol_way_s_way"]))

CONFIRM_THR = 0.5
PCT_LO, PCT_HI = 0.1, 1.0

tf = load_h2()
tf = add_way_grade(filter_short_segments(mark_direction(tf), min_len=8)).reset_index(drop=True)
direction = tf["方向"].values
cross_idx = [i for i in range(len(tf)) if direction[i] in ("good","bad")]
sma13 = tf["SMA_13"].to_numpy()
close = tf["close"].to_numpy(); open_ = tf["open"].to_numpy()
high = tf["high"].to_numpy(); low = tf["low"].to_numpy()

# ---------- 生成空单清单(带因子) ----------
rows = []
for pos, i in enumerate(cross_idx):
    side = "L" if direction[i]=="good" else "S"
    if side != "S":  # 只做空单
        continue
    j1, j2 = i+1, i+2
    if j2+1 >= len(tf): continue
    # 结构止损: 上一段 SMA13 极值(空单取 max)
    k = cross_idx[pos-1] if pos>0 else 0
    seg = pd.to_numeric(pd.Series(sma13[k:i]), errors="coerce").dropna()
    if seg.empty: continue
    sl = float(seg.max())
    # causal 确认
    w1,w2,v1,v2 = causal_confirm(tf, i)
    if not (min(w1,w2) >= CONFIRM_THR and min(v1,v2) >= CONFIRM_THR):  # 修复后
        continue
    entry_idx = j2 + 1
    if entry_idx >= len(tf): continue
    entry = float(tf.iloc[entry_idx]["open"])
    pct = abs(entry - sl) / entry * 100.0
    if not (PCT_LO <= pct <= PCT_HI): continue
    if sl <= entry: continue  # side_ok: 空单止损须在入场价上方
    opp = "good"
    nxt = next((x for x in cross_idx if x > entry_idx and direction[x]==opp), None)
    if nxt is None: continue
    exit_idx = nxt + 1
    if exit_idx >= len(tf): exit_idx = nxt
    # 止损/退出 replay
    result = None; sl_idx = None
    for j in range(entry_idx, exit_idx):
        b = tf.iloc[j]
        op = float(b["open"]); h = float(b["high"]); lo = float(b["low"])
        if op >= sl: exit_px = op; reason = "SL gap"
        elif h >= sl: exit_px = sl; reason = "SL"
        else: continue
        pnl = entry - exit_px
        result = (exit_px, pnl); sl_idx = j
        break
    if result is None:
        exit_bar = tf.iloc[exit_idx]
        exit_px = float(exit_bar["open"]) if exit_idx != nxt else float(exit_bar["close"])
        pnl = entry - exit_px; reason = "opposite cross"; exit_row = exit_idx
    else:
        _, pnl = result; reason = "SL hit"; exit_row = sl_idx
    # 因子
    prev_up_len = i - k - 1  # 死叉前 up 段长度(原始方向, good~bad 之间根数)
    ret2 = close[j2]/close[i] - 1 if close[i] else np.nan  # 信号后2根收益
    body_i = (close[i]-open_[i])/(high[i]-low[i]) if high[i]>low[i] else 0.0  # 死叉bar实体
    rows.append({
        "signal_time": tf.iloc[i]["date"], "dir":"S", "pnl_points": pnl,
        "entry": entry, "stop": sl, "stop_pct": pct, "reason": reason,
        "w1": w1, "w2": w2, "v1": v1, "v2": v2,
        "min_w": min(w1,w2), "min_v": min(v1,v2),
        "prev_up_len": prev_up_len, "ret2": round(ret2,5), "body_i": round(body_i,4),
        "year": pd.to_datetime(tf.iloc[i]["date"]).year,
    })

tr = pd.DataFrame(rows)
print("空单基线(修复后, 确认>=0.5): n =", len(tr))

def pf(pnl):
    w = pnl[pnl>0].sum(); l = abs(pnl[pnl<0].sum())
    return w/l if l>0 else (999.0 if w>0 else 0.0)

def summ(sub):
    if len(sub)==0: return None
    p = sub["pnl_points"].astype(float)
    return {"n": int(len(sub)), "pf": round(pf(p),3), "wr": round((p>0).mean()*100,1),
            "ev": round(p.mean(),3), "pnl": round(p.sum(),2)}

def yearly(sub):
    if len(sub)==0: return ""
    g = sub.groupby("year")["pnl_points"].sum()
    return " ".join(f"{y}:{v:+.1f}" for y,v in g.items())

base = summ(tr)
print(f"  基线: n={base['n']} PF={base['pf']} WR={base['wr']}% EV={base['ev']} PnL={base['pnl']}")
print(f"  分年: {yearly(tr)}")
print()

# ---------- 保存带因子的空单清单 ----------
OUT = STRAT / "data" / "validation" / "experiments_20260815"
tr.to_csv(OUT / "short_trades_with_factors.csv", index=False, encoding="utf-8-sig")

# ---------- 因子扫描 ----------
print("="*80)
print("【单因子扫描】(空单, 基线 PF=%s n=%d)" % (base['pf'], base['n']))
print("="*80)

def scan_col(col, thresholds, label, direction="ge"):
    print(f"--- {label} ---")
    for t in thresholds:
        if direction == "ge": sub = tr[tr[col] >= t]
        elif direction == "le": sub = tr[tr[col] <= t]
        elif direction == "between": sub = tr[(tr[col] >= t[0]) & (tr[col] <= t[1])]
        s = summ(sub)
        if s is None: print(f"  {label} {t}: n=0"); continue
        flag = "  <<< PF>=1" if s["pf"] >= 1.0 else ""
        print(f"  {label} {t}: n={s['n']:3d} PF={s['pf']:.3f} WR={s['wr']:.1f}% EV={s['ev']:+.3f}{flag}")

print()
print("### 1) 确认强度 min_w = min(w1,w2) (way_s_way)")
scan_col("min_w", [0.6, 0.7, 0.8, 0.9, 1.0], "min_w>=")

print()
print("### 2) 确认缩量 min_v = min(v1,v2) (vol_way_s_way)")
scan_col("min_v", [0.6, 0.7, 0.8, 0.9, 1.0], "min_v>=")

print()
print("### 3) 死叉前 up 段长度 prev_up_len")
scan_col("prev_up_len", [13, 21, 34, 55, 89], "prev_up_len>=")
scan_col("prev_up_len", [8, 12], "prev_up_len<=", direction="le")

print()
print("### 4) 止损距离 stop_pct")
scan_col("stop_pct", [(0.1,0.3),(0.3,0.5),(0.5,0.7),(0.7,1.0)], "stop_pct", direction="between")

print()
print("### 5) 信号后2根收益 ret2 (空单希望为负)")
scan_col("ret2", [0.0], "ret2<=", direction="le")
scan_col("ret2", [-0.005, -0.01, -0.02], "ret2<=", direction="le")

print()
print("### 6) 死叉bar实体 body_i (空单希望阴线<0)")
scan_col("body_i", [0.0], "body_i<=", direction="le")
scan_col("body_i", [-0.2, -0.4], "body_i<=", direction="le")

# ---------- 组合扫描 ----------
print()
print("="*80)
print("【组合扫描】min_w 阈值 × 段长")
print("="*80)
for mw in [0.5, 0.7, 0.9]:
    for pl in [8, 21, 34]:
        sub = tr[(tr["min_w"]>=mw) & (tr["prev_up_len"]>=pl)]
        s = summ(sub)
        if s is None or s["n"] < 3: continue
        flag = "  <<< PF>=1" if s["pf"]>=1.0 else ""
        print(f"  min_w>={mw} & up_len>={pl}: n={s['n']:3d} PF={s['pf']:.3f} WR={s['wr']:.1f}% EV={s['ev']:+.3f} 分年[{yearly(sub)}]{flag}")

print()
print("="*80)
print("【组合扫描】min_w 阈值 × min_v 阈值")
print("="*80)
for mw in [0.5, 0.7]:
    for mv in [0.5, 0.7, 0.9]:
        sub = tr[(tr["min_w"]>=mw) & (tr["min_v"]>=mv)]
        s = summ(sub)
        if s is None or s["n"] < 3: continue
        flag = "  <<< PF>=1" if s["pf"]>=1.0 else ""
        print(f"  min_w>={mw} & min_v>={mv}: n={s['n']:3d} PF={s['pf']:.3f} WR={s['wr']:.1f}% EV={s['ev']:+.3f}{flag}")

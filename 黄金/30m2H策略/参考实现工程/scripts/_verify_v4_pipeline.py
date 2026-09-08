# -*- coding: utf-8 -*-
"""_verify_v4_pipeline.py - v3 终版三层串联验收

最终配置 (Plan B, 2026-06-26 用户确认):
  Layer 1: |Bias_55| > 3.0% 硬门 (H2 SMMA55 偏离)
  Layer 2: cross + post_n (N=2-6) 联合, spec [5, 35]
  Layer 3: Bias_5 top 30% (H2 close 偏离 SMMA5)

实测 8.5 年回测: 68 笔, WR 67.6%, PF 7.41, EV +27.38pt, MaxCL 5
"""
import sys, io, numpy as np, pandas as pd

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.prepare import prepare
from _h2_context import load_h2_context


# ============================================================
# v3.0 配置 (Plan B 最终版)
# ============================================================
SPEC_LO = 5
SPEC_HI = 35              # ← 用户 2026-06-26 修订: 上限 35
POST_N_MIN = 2
POST_N_MAX = 6
BIAS_55_THRESHOLD = 3.0   # ← Layer 1 硬门
BIAS_5_TOP_PCT = 30       # ← Layer 3 top 30%
LAYER1_APPLY_TO_ALL_MODES = True  # ← gate 应用到所有模式


def precompute_layer1_pass_set(h2_df, m30_times):
    """Layer 1 v3 — |Bias_55| > 3.0% 硬门,返回通过的 M30 bar 索引集合"""
    h2_times = pd.to_datetime(h2_df['date']).values.astype('datetime64[ns]')
    h2_close = h2_df['close'].values
    sma55 = h2_df['SMA_55'].values
    bias_55 = np.where(~np.isnan(sma55) & (sma55 != 0),
                       (h2_close - sma55) / sma55 * 100, np.nan)

    # 算 5 因子 (Layer 3 用)
    sma5 = h2_df['SMA_5'].values
    sma13 = h2_df['SMA_13'].values
    bias_5 = np.where(~np.isnan(sma5) & (sma5 != 0),
                      (h2_close - sma5) / sma5 * 100, np.nan)
    bias_13 = np.where(~np.isnan(sma13) & (sma13 != 0),
                       (h2_close - sma13) / sma13 * 100, np.nan)
    way = h2_df['way'].values
    way_s_way = h2_df['way_s_way'].values
    vol_way_s_way = h2_df['vol_way_s_way'].values

    import bisect
    m30_t = pd.to_datetime(m30_times).values.astype('datetime64[ns]')
    pass_set = set()
    factor_map = {}
    for i, t in enumerate(m30_t):
        idx = bisect.bisect_right(h2_times, t) - 1
        if idx < 0: continue
        if pd.isna(sma55[idx]): continue
        # Layer 1: |Bias_55| > 3.0%
        if abs(bias_55[idx]) > BIAS_55_THRESHOLD:
            pass_set.add(i)
        # H2 因子 (无论 gate 是否通过都算,Layer 3 用)
        factor_map[i] = {
            'Bias_5': abs(bias_5[idx]),
            'Bias_13': abs(bias_13[idx]),
            'Bias_55': abs(bias_55[idx]),
            'way': abs(way[idx]),
            'way_s_way': way_s_way[idx],
            'vol_way_s_way': vol_way_s_way[idx],
        }
    return pass_set, factor_map


def build_cross_trades(df, direction, sma13, high, low, close,
                       spec_lo, spec_hi, layer1_pass_set):
    """cross 模式: M30 SMA5/13 实际穿越, SL = 上一段 SMA13 极值"""
    n = len(df)
    trades = []
    for i in range(n):
        if layer1_pass_set is not None and i not in layer1_pass_set: continue
        d = direction[i]
        if d not in ('good', 'bad'): continue
        if pd.isna(sma13[i]): continue
        is_long = (d == 'good')
        entry = (high[i] + low[i] + close[i]) / 3.0
        k = i - 1
        while k >= 0 and direction[k] not in ('good', 'bad'): k -= 1
        if k < 0: continue
        seg = sma13[k:i]; seg_clean = seg[~np.isnan(seg)]
        if len(seg_clean) == 0: continue
        if is_long: sl = np.nanmin(seg_clean)
        else: sl = np.nanmax(seg_clean)
        if is_long and sl >= entry: continue
        if not is_long and sl <= entry: continue
        sd = abs(entry - sl)
        if sd < spec_lo or sd > spec_hi: continue
        opp = 'bad' if is_long else 'good'
        j = i + 1
        while j < n and direction[j] != opp: j += 1
        if j >= n: continue
        seg_hl = low[i+1:j+1] if is_long else high[i+1:j+1]
        hit = (seg_hl <= sl).any() if is_long else (seg_hl >= sl).any()
        exit_px = df.iloc[j]['close']
        if pd.isna(exit_px): continue
        pnl = (exit_px - entry) if is_long else (entry - exit_px)
        pnl = -sd if hit else pnl
        trades.append({'i': i, 'date': df.iloc[i]['date'], 'mode': 'cross',
                       'dir': 'L' if is_long else 'S',
                       'entry': entry, 'stop': sl, 'sd': sd,
                       'pnl': pnl, 'won': pnl > 0})
    return trades


def build_post_cross_trades(df, direction_merged, sma13, close,
                            n_min, n_max, spec_lo, spec_hi,
                            layer1_pass_set):
    """post_cross_n 模式: 穿越后第 N 根, SL = 当前 K 线 SMA13 (动态)"""
    n = len(df)
    post_n_arr = df['merged_post_cross_n'].values
    trades = []
    for i in range(n):
        if layer1_pass_set is not None and i not in layer1_pass_set: continue
        pn = post_n_arr[i]
        if pn == 0: continue
        if abs(pn) < n_min or abs(pn) > n_max: continue
        is_long = (pn > 0)
        entry = close[i]
        sl = sma13[i]
        if pd.isna(sl) or pd.isna(entry): continue
        if is_long:
            if sl >= entry: continue
        else:
            if sl <= entry: continue
        sd = abs(entry - sl)
        if sd < spec_lo or sd > spec_hi: continue
        opp = 'bad' if is_long else 'good'
        j = i + 1
        while j < n and direction_merged[j] != opp: j += 1
        if j >= n: continue
        seg_hl = low_ = df['low'].values[j] if False else df['low'].values[i+1:j+1] if is_long else df['high'].values[i+1:j+1]
        hit = (seg_hl <= sl).any() if is_long else (seg_hl >= sl).any()
        exit_px = df.iloc[j]['close']
        if pd.isna(exit_px): continue
        pnl = (exit_px - entry) if is_long else (entry - exit_px)
        pnl = -sd if hit else pnl
        trades.append({'i': i, 'date': df.iloc[i]['date'], 'mode': f'post_n{abs(pn)}',
                       'dir': 'L' if is_long else 'S',
                       'entry': entry, 'stop': sl, 'sd': sd,
                       'pnl': pnl, 'won': pnl > 0})
    return trades


def stats(tdf, label=''):
    if len(tdf) == 0:
        print(f'  {label:<55} 0 trades'); return None
    n = len(tdf); won = int(tdf['won'].sum())
    tp = tdf[tdf['won']]['pnl'].sum()
    tl = abs(tdf[~tdf['won']]['pnl'].sum())
    pf = tp/tl if tl > 0 else 0
    cl = 0; ml = 0
    for w in tdf['won']:
        if w: cl = 0
        else: cl += 1; ml = max(ml, cl)
    aw = tp/won if won else 0
    al = tl/(n-won) if n > won else 0
    print(f'  {label:<55} {n:>5} 笔  WR {won/n*100:>5.1f}%  PF {pf:>5.2f}  '
          f'EV {(tp-tl)/n:+6.2f}pt  PnL ${tp-tl:>6.0f}  MaxCL {ml}  R:R {aw/al if al else 0:.2f}')
    return {'n': n, 'wr': won/n*100, 'pf': pf, 'ev': (tp-tl)/n, 'pnl': tp-tl, 'ml': ml}


def main():
    print('=' * 100)
    print('v3.0 三层串联终版验收 (Plan B, 用户 2026-06-26 确认)')
    print('=' * 100)
    print()
    print(f'配置:')
    print(f'  Layer 1: |Bias_55| > {BIAS_55_THRESHOLD}% 硬门 (应用到所有模式: {LAYER1_APPLY_TO_ALL_MODES})')
    print(f'  Layer 2: cross + post_n (N={POST_N_MIN}-{POST_N_MAX}), spec [{SPEC_LO}, {SPEC_HI}]')
    print(f'  Layer 3: Bias_5 top {BIAS_5_TOP_PCT}%')
    print()

    print('[1/3] 加载数据...')
    df, meta = prepare('base_data/XAUUSDm30.csv', min_len=8)
    h2_df = load_h2_context()
    print(f'  M30: {len(df)} 行, H2: {len(h2_df)} 行')

    layer1_pass_set, factor_map = precompute_layer1_pass_set(h2_df, df['date'].values)
    print(f'  Layer 1 v3 硬门 |Bias_55|>{BIAS_55_THRESHOLD}%: {len(layer1_pass_set)} M30 bars 通过')
    print()

    # ============ Step 2: Baseline ============
    print('[2/3] Baseline (cross 模式,spec [3, 35], 不应用 Layer 1 gate) ...')
    direction_raw = df['方向'].values
    n = len(df)
    sma13 = df['SMA_13'].values
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    # 旧 baseline (spec 3-35, 不应用 gate)
    baseline_trades = build_cross_trades(df, direction_raw, sma13, high, low, close,
                                       spec_lo=3, spec_hi=35, layer1_pass_set=None)
    tdf_base = pd.DataFrame(baseline_trades)
    bn, bwr, bpf, bev, bp, _ = stats(tdf_base, 'baseline (cross 3-35pt)').values() if False else (stats(tdf_base, 'baseline (cross 3-35pt)') or [0,0,0,0,0,0])
    bs = stats(tdf_base, 'baseline (cross 3-35pt)')
    bn, bwr, bpf, bev, bp = bs['n'], bs['wr'], bs['pf'], bs['ev'], bs['pnl']

    # ============ Step 3: v3.0 三层联合 ============
    print()
    print('[3/3] v3.0 三层串联 (Plan B 配置) ...')
    print()

    direction_merged = df['方向_合并后'].values
    l1_set = layer1_pass_set if LAYER1_APPLY_TO_ALL_MODES else None

    # Layer 2: cross + post_n 联合
    cross_t = build_cross_trades(df, direction_raw, sma13, high, low, close,
                                 spec_lo=SPEC_LO, spec_hi=SPEC_HI, layer1_pass_set=l1_set)
    post_t = build_post_cross_trades(df, direction_merged, sma13, close,
                                     n_min=POST_N_MIN, n_max=POST_N_MAX,
                                     spec_lo=SPEC_LO, spec_hi=SPEC_HI,
                                     layer1_pass_set=l1_set)
    all_t = cross_t + post_t

    # 加 H2 因子,去重 (同一天同方向)
    for t in all_t:
        if t['i'] in factor_map:
            t.update(factor_map[t['i']])
    tdf_all = pd.DataFrame(all_t)
    tdf_all = tdf_all.drop_duplicates(subset=['date', 'dir'], keep='first').reset_index(drop=True)
    n2 = stats(tdf_all, 'Layer 1+2 (cross + post_n 联合)')

    # Layer 3: Bias_5 top 30%
    if len(tdf_all) > 30:
        # 单 Bias_5 top X% (前 X% 分位数)
        thr = tdf_all['Bias_5'].quantile(1 - BIAS_5_TOP_PCT / 100)
        tdf_top = tdf_all[tdf_all['Bias_5'] >= thr]
        n3 = stats(tdf_top, 'Layer 1+2+3 (Bias_5 top 30%)')

    # ============ 综合对比 ============
    print()
    print('=' * 100)
    print('最终对比表 (8.5 年, XAUUSDm M30)')
    print('=' * 100)
    print(f'{"方案":<45} {"笔数":>6} {"WR%":>6} {"PF":>6} {"EV":>8} {"PnL":>8} {"MaxCL":>5}')
    print('-' * 100)
    print(f'{"baseline (v3.10 cross 3-35pt, 8.5 年)":<45} {bn:>6} {bwr:>6.1f} {bpf:>6.2f} {bev:>+8.1f} {bp:>8.0f}')
    print(f'{"v3.0 Plan B (Layer1+2 cross+post_n 联合)":<45} {n2["n"]:>6} {n2["wr"]:>6.1f} {n2["pf"]:>6.2f} {n2["ev"]:>+8.1f} {n2["pnl"]:>8.0f} {n2["ml"]:>5}')
    if len(tdf_all) > 30:
        print(f'{"v3.0 Plan B (Layer1+2+3 Bias_5 top 30%)":<45} {n3["n"]:>6} {n3["wr"]:>6.1f} {n3["pf"]:>6.2f} {n3["ev"]:>+8.1f} {n3["pnl"]:>8.0f} {n3["ml"]:>5}')
    print()
    print('对比 baseline:')
    print(f'  PF:  {bpf:.2f} → {n3["pf"]:.2f}  (×{n3["pf"]/bpf:.1f})')
    print(f'  WR:  {bwr:.1f}% → {n3["wr"]:.1f}%  (+{n3["wr"]-bwr:.1f}pp)')
    print(f'  EV/笔: {bev:+.2f}pt → {n3["ev"]:+.2f}pt  (×{n3["ev"]/bev if bev else 0:.1f})')
    print(f'  MaxCL: {bs["ml"]} → {n3["ml"]} 笔 ({(n3["ml"]-bs["ml"])/bs["ml"]*100:+.0f}%)')
    print(f'  PnL:  ${bp:.0f} → ${n3["pnl"]:.0f}  ({n3["pnl"]/bp*100-100:+.0f}%)')
    print()

    # ============ 信号量与频率 ============
    n_per_year = n3['n'] / 8.5
    print('=' * 100)
    print('信号量与频率 (Plan B 终版)')
    print('=' * 100)
    print(f'  8.5 年总笔数: {n3["n"]}')
    print(f'  年均笔数: {n_per_year:.1f}')
    print(f'  月均笔数: {n_per_year/12:.1f}')
    print(f'  0.06 手 × {n_per_year:.1f} 笔/年 × +{n3["ev"]:.1f}pt/笔 = ${n_per_year * n3["ev"] * 0.6:.0f}/年 (0.06 手)')
    print(f'  假设按 0.1 手算: ${n_per_year * n3["ev"] * 1.0:.0f}/年')
    print(f'  MaxCL {n3["ml"]} 笔 × 平均亏损 ~15pt × 0.1 手 = ${n3["ml"]*15:.0f} (回撤峰值)')

    # ============ 实际触发条件 ============
    print()
    print('=' * 100)
    print('实际触发条件 (Plan B 终版)')
    print('=' * 100)
    print()
    print('  Layer 1: |Bias_55| > 3.0%')
    print(f'    当 H2 close 偏离 SMMA55 超过 3% 时,Layer 1 硬门通过')
    print(f'    8.5 年内 {len(layer1_pass_set)} 根 M30 bar 通过 ({(len(layer1_pass_set)/len(df)*100):.1f}%)')
    print()
    print(f'  Layer 2: cross + post_n (N={POST_N_MIN}-{POST_N_MAX}) 联合')
    print('    cross:  M30 SMA5/13 实际穿越 (good/bad)')
    print(f'    post_n: 穿越后第 {POST_N_MIN}-{POST_N_MAX} 根 K 线')
    print('    去重: 同一天同方向只保留一个')
    print(f'    SL: cross → 上一段 SMA13 极值;post_n → 当前 K 线 SMA13')
    print(f'    spec: [{SPEC_LO}, {SPEC_HI}] pt')
    print()
    print(f'  Layer 3: Bias_5 top {BIAS_5_TOP_PCT}%')
    print('    Bias_5 = |H2 close - H2 SMMA5| / H2 SMMA5 × 100')
    print('    取 Bias_5 排名前 30% 的入场')
    print()
    print('=' * 100)
    print('Layer 3 过滤后,模式分布:')
    if len(tdf_all) > 30:
        for mode in tdf_top['mode'].value_counts().index:
            sub = tdf_top[tdf_top['mode'] == mode]
            n = len(sub)
            wr = sub['won'].mean() * 100
            tp = sub[sub['won']]['pnl'].sum()
            tl = abs(sub[~sub['won']]['pnl'].sum())
            pf = tp/tl if tl > 0 else 0
            print(f'  {mode:<12} {n:>4} 笔  WR {wr:>5.1f}%  PF {pf:>5.2f}')

    print()
    print('=' * 100)
    print('下一步: 部署到 MT5 EA')
    print('=' * 100)
    print('MT5 EA 端需实现 (v3.0 EA):')
    print('  1. H2 5 SMA 句柄 + Bias_55 计算 (Layer 1)')
    print('  2. H2 SMMA5 句柄 + Bias_5 top 30% 阈值 (Layer 3)')
    print('  3. M30 SMA5/13 穿越检测 (Layer 2 cross)')
    print('  4. M30 穿越后 N 根计数器 (Layer 2 post_n)')
    print('  5. SL 计算: cross → FindStopSMA; post_n → 当前 SMA13')
    print('  6. 3 段 TP (0.06 手 = 0.02 × 3): 1.2R / 2R SMA13 / 2H 翻转')


if __name__ == '__main__':
    main()

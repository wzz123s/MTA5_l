# -*- coding: utf-8 -*-
"""
validate_segments.py —— 段分析断言验证（MCT 阶段0 · 验收标准）

对齐 MTA5 规则 v3.1 验证用例：
  1. mark_direction 状态机用例（内置 6 行用例）
  2. 极值追踪断言：up_high_price 段内单调不减 / down_low_price 段内单调不增
  3. 穿越点断言：long_entry/stop 仅在 good 行；short_entry/stop 仅在 bad 行
  4. 数量守恒：幸存 good/bad 数量差 ≤ 1（v4 链式吸收核心性质）
  5. 开仓价在 K 线范围内：low ≤ entry ≤ high
  6. 真实数据段统计报告（段数/段长分布/穿越次数）

用法：
  python validate_segments.py                      # 内置用例 + data/raw 下全部 CSV
  python validate_segments.py --csv <文件路径>      # 指定文件
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segment_analysis import analyze, mark_direction

BASE = Path(__file__).resolve().parent.parent


def test_mark_direction_unit():
    """内置状态机用例（段的定义与方向标记.md 第七节）"""
    df_test = pd.DataFrame({
        'open': [11, 12, 11, 10, 11, 12],
        'high': [13, 14, 12, 11, 13, 14],
        'low': [10, 11, 9, 9, 10, 11],
        'close': [12, 13, 10, 9, 12, 13],
        'tick_volume': [100, 100, 100, 100, 100, 100],
    })
    df_test['SMA_5'] = [12, 13, 10, 9, 12, 13]
    df_test['SMA_13'] = [11, 11, 11, 11, 11, 11]
    got = mark_direction(df_test)['方向'].tolist()
    expect = ['up', 'up', 'bad', 'down', 'good', 'up']
    assert got == expect, f"FAIL: {got} != {expect}"
    print("  [PASS] mark_direction 状态机用例:", got)
    return True


def test_extremes_monotonic(df):
    """极值单调性：up_high_price 段内不减；down_low_price 段内不增"""
    dirs = df['方向_合并后'].values
    up_hp = df['up_high_price'].values
    dn_lp = df['down_low_price'].values
    # 段内检查
    in_up = False
    prev_up = -np.inf
    in_dn = False
    prev_dn = np.inf
    for d, u, l in zip(dirs, up_hp, dn_lp):
        if d == 'up':
            in_up, in_dn = True, False
            if not np.isnan(u):
                assert u >= prev_up - 1e-9, "up_high_price 单调性破坏"
                prev_up = u
        elif d == 'down':
            in_dn, in_up = True, False
            if not np.isnan(l):
                assert l <= prev_dn + 1e-9, "down_low_price 单调性破坏"
                prev_dn = l
        else:
            in_up = in_dn = False
            prev_up = -np.inf
            prev_dn = np.inf
    print("  [PASS] 极值单调性（up_high_price 不减 / down_low_price 不增）")
    return True


def test_crossing_rows(df):
    """穿越点断言：entry/stop 仅出现在对应穿越行；开仓价在 K 线范围内"""
    dirs = df['方向_合并后'].values
    good_pos = np.where(dirs == 'good')[0]
    bad_pos = np.where(dirs == 'bad')[0]

    le = df['long_entry'].values
    ls = df['long_stop'].values
    se = df['short_entry'].values
    ss = df['short_stop'].values

    assert np.all(np.isnan(le[np.arange(len(df))[~np.isin(np.arange(len(df)), good_pos)]])), "long_entry 出现在非 good 行"
    assert np.all(np.isnan(ls[np.arange(len(df))[~np.isin(np.arange(len(df)), good_pos)]])), "long_stop 出现在非 good 行"
    assert np.all(np.isnan(se[np.arange(len(df))[~np.isin(np.arange(len(df)), bad_pos)]])), "short_entry 出现在非 bad 行"
    assert np.all(np.isnan(ss[np.arange(len(df))[~np.isin(np.arange(len(df)), bad_pos)]])), "short_stop 出现在非 bad 行"

    # 开仓价范围
    lo, hi = df['low'].values, df['high'].values
    for pos in good_pos:
        assert lo[pos] <= le[pos] <= hi[pos] + 1e-9, f"long_entry 越界 @{pos}"
    for pos in bad_pos:
        assert lo[pos] <= se[pos] <= hi[pos] + 1e-9, f"short_entry 越界 @{pos}"
    # 止损方向合理：long_stop 低于开仓价；short_stop 高于开仓价
    for pos in good_pos:
        assert ls[pos] <= le[pos], f"long_stop 应 <= long_entry @{pos}"
    for pos in bad_pos:
        assert ss[pos] >= se[pos], f"short_stop 应 >= short_entry @{pos}"
    print(f"  [PASS] 穿越点断言（good={len(good_pos)}, bad={len(bad_pos)}；entry/stop 定位正确、止损方向合理）")
    return True


def test_count_conservation(df):
    """幸存 good/bad 数量差 ≤ 1（v4 链式吸收核心性质）"""
    dirs = df['方向_合并后'].values
    ng = int(np.sum(dirs == 'good'))
    nb = int(np.sum(dirs == 'bad'))
    assert abs(ng - nb) <= 1, f"FAIL: |good-bad| = {abs(ng-nb)} > 1"
    print(f"  [PASS] 数量守恒（good={ng}, bad={nb}, |diff|={abs(ng-nb)} ≤ 1）")
    return True


def report_segments(df, name):
    """段统计报告"""
    attrs = df.attrs
    n_seg = attrs.get('n_seg', 0)
    seg_len = attrs.get('seg_len', np.array([]))
    n_real_good = int(np.sum(attrs.get('is_real_good', [])))
    n_real_bad = int(np.sum(attrs.get('is_real_bad', [])))
    print(f"  [{name}] 行数={len(df)} 段数={n_seg} 幸存穿越点 good={n_real_good} bad={n_real_bad}")
    if len(seg_len):
        print(f"     段长(up+down K线数): min={seg_len.min()} P50={np.median(seg_len):.0f} "
              f"max={seg_len.max()} 均值={seg_len.mean():.1f}")
    return n_seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="指定 CSV；缺省扫描 data/raw 全部 _D1.csv")
    args = ap.parse_args()

    print("== 1/2 内置用例 ==")
    test_mark_direction_unit()

    print("\n== 2/2 真实数据验证 ==")
    if args.csv:
        files = [Path(args.csv)]
    else:
        raw = BASE / "data" / "raw"
        files = sorted(raw.rglob("*_D1.csv"))
        if not files:
            print("未找到数据，请先运行 fetch_mt5_data.py")
            sys.exit(1)

    all_ok = True
    for f in files:
        print(f"\n--- {f.name} ---")
        df = pd.read_csv(f, parse_dates=['time'])
        # 列名兼容（MT5 导出 tick_volume）
        out = analyze(df, min_len=8)
        try:
            test_extremes_monotonic(out)
            test_crossing_rows(out)
            test_count_conservation(out)
            report_segments(out, f.name)
        except AssertionError as e:
            all_ok = False
            print("  [FAIL]", e)

    print("\n========================")
    print("验证结果:", "全部通过 OK" if all_ok else "存在失败 FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

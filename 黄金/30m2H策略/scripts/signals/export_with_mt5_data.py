# -*- coding: utf-8 -*-

"""基于 MT5 原生 SMMA 数据导出信号 — 替代原 export_strategy_signals.py

使用 build_from_mt5.py 生成的 MT5 原生 H2 SMA + M30 SMA 数据，
而非 Python 自算的 SMMA，使两端信号完全对齐。

用法:
    cd F:/use_code/MTA5_l
    python 黄金/30m2H策略/scripts/signals/export_with_mt5_data.py

前置条件:
    python 黄金/30m2H策略/scripts/data_source/build_from_mt5.py
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
from processing.mt5_data_source import load_mt5_smma, generate_h2_from_mt5

# ─── 1. 数据源 ─────────────────────────────────────────────────
EA_CSV = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_strategy_signals_export.csv"
H2_MT5_CSV = os.path.join(ROOT, "30m2H策略", "data", "raw", "H2_XAUUSDm_mt5.csv")
M30_RAW_CSV = os.path.join(ROOT, "base_data", "XAUUSDm30.csv")
SIGNALS_DIR = os.path.join(ROOT, "30m2H策略", "data", "signals_mt5")
os.makedirs(SIGNALS_DIR, exist_ok=True)

# ─── 2. 管道参数 ───────────────────────────────────────────────
TOP_PCT = 34
BIAS55_THRESHOLD = 3.0
SPEC_LO = 5
SPEC_HI = 35
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0

# ─── 3. 加载 MT5 原生 H2 ─────────────────────────────────────

def load_h2_mt5():
    from _h2_context import H2_SOURCE_TO_CLIENT_HOURS, H2_BUCKET_TO_DECISION_HOURS
    h2 = pd.read_csv(H2_MT5_CSV, encoding="utf-8-sig")
    source_time = pd.to_datetime(h2["date"])
    client_bucket_time = source_time + pd.Timedelta(hours=H2_SOURCE_TO_CLIENT_HOURS)
    decision_time = client_bucket_time + pd.Timedelta(hours=H2_BUCKET_TO_DECISION_HOURS)
    h2["source_time"] = source_time
    h2["client_bucket_time"] = client_bucket_time
    h2["decision_time"] = decision_time
    h2["date"] = decision_time
    return h2

# ─── 4. 构建 MT5 数据 ─────────────────────────────────────────

if not os.path.exists(H2_MT5_CSV):
    print("[DATA] 构建 MT5 原生数据...")
    mt5_all = load_mt5_smma(EA_CSV)
    generate_h2_from_mt5(mt5_all, H2_MT5_CSV)

# ─── 5. 使用 Python 原生 SMMA 计算 (不 patch) ──────────────────

import _current_baseline as cb
import _h2_context
import _stage12_combo_test as s12

print("=" * 60)
print("  Python 原生 SMMA 信号导出")
print("=" * 60)
print("[DATA] M30 SMMA → Python calc_smma()")
print("[DATA] H2 数据   → Python gen_h2_36col_v2.py")

# ─── 6. 运行管道 ───────────────────────────────────────────────

print("\n[PIPE] 构建候选信号 (Layer1+Layer2 + M15 replace/rescue + H2 q2)...")
# ea_executable_diag=True: M15 slot1 replace + rescue (完整组合策略)
df, final_acc = cb.build_final_accepted(
    spec_lo=SPEC_LO,
    spec_hi=SPEC_HI,
    bias55_threshold=BIAS55_THRESHOLD,
    ea_executable_diag=True,
)
print(f"  Layer1+Layer2+Combo 通过: {len(final_acc)} 个候选")

print("\n[PIPE] Layer3 过滤...")
threshold, picked = cb.apply_layer3(final_acc, top_pct=TOP_PCT)
print(f"  Layer3 阈值: {threshold:.4f}% (top {TOP_PCT}%)")
print(f"  Layer3 入选: {len(picked)} 个信号")

# 新增: MAX_POS=3 并发限制 (对齐EA)
picked_sorted = picked.sort_values('date')
picked_filtered = []
active = []  # (close_time, anchor_time)
for _, row in picked_sorted.iterrows():
    anchor = row['date']
    # 移除已结束的持仓
    active = [a for a in active if a[0] > anchor]
    if len(active) < 3:
        picked_filtered.append(row)
        # 假设持仓持有到下一个信号(近似)
        active.append((anchor + pd.Timedelta(hours=24), anchor))

picked = pd.DataFrame(picked_filtered).reset_index(drop=True)
print(f"  MAX_POS=3 限制后: {len(picked)} 个信号")

print("\n[PIPE] Stage 执行...")
trades = s12.summarize_variant(df, picked, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R,)
print(f"  最终交易: {len(trades)} 个 stage")

# ─── 7. 导出 + 汇总 ───────────────────────────────────────────

final_acc.to_csv(os.path.join(SIGNALS_DIR, "候选信号_Layer1_Layer2通过.csv"),
                 index=False, encoding="utf-8-sig")
picked.to_csv(os.path.join(SIGNALS_DIR, "最终信号_Layer3入选.csv"),
              index=False, encoding="utf-8-sig")
trades.to_csv(os.path.join(SIGNALS_DIR, "执行交易_Stage结果.csv"),
              index=False, encoding="utf-8-sig")

unique_signals = trades.drop_duplicates(subset=["date", "mode", "dir"]).copy()
unique_modes = {}
for _, r in unique_signals.iterrows():
    m = str(r["mode"])
    if "post_n" in m:
        m = "post_n"
    unique_modes[m] = unique_modes.get(m, 0) + 1

yearly = {}
for _, r in unique_signals.iterrows():
    y = str(r["date"])[:4]
    yearly[y] = yearly.get(y, 0) + 1

print("\n" + "=" * 60)
print("  导出完成")
print("=" * 60)
print(f"\n信号分布: {dict(sorted(unique_modes.items()))}")
print(f"总独有信号: {len(unique_signals)}")

print("\n分年统计 (vs 旧 Python):")
py_exp = {"2019": 1, "2020": 24, "2021": 5, "2022": 14, "2023": 2, "2024": 6, "2025": 22, "2026": 44}
print(f"  {'年':<6} {'MT5_Py':>6} {'旧Py':>6} {'差距':>6}")
t_all = 0
t_py = 0
for y in sorted(set(list(yearly.keys()) + list(py_exp.keys()))):
    a = yearly.get(y, 0)
    b = py_exp.get(y, 0)
    t_all += a
    t_py += b
    print(f"  {y:<6} {a:>6} {b:>6} {a - b:+6d}")
print(f"  {'TOT':<6} {t_all:>6} {t_py:>6} {t_all - t_py:+6d}")

print(f"\n输出目录: {SIGNALS_DIR}")
print(f"文件:")
for fn in os.listdir(SIGNALS_DIR):
    print(f"  - {fn}")

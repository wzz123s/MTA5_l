# -*- coding: utf-8 -*-

"""
build_from_mt5.py — 从 MT5 EA CSV 导出构建 Python 策略所需全部数据

用法:
    python 黄金/30m2H策略/scripts/data_source/build_from_mt5.py

输出:
    - data/raw/H2_XAUUSDm_mt5.csv  (MT5原生H2 SMA)
    - data/processed/m30_mt5.csv    (M30标准化数据 + MT5 SMA)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pandas as pd
from processing.mt5_data_source import load_mt5_smma, generate_h2_from_mt5, DEFAULT_MT5_CSV
from processing.prepare import prepare
from pathlib import Path

ROOT = Path(r"F:\use_code\MTA5_l")
DATA_RAW = ROOT / "黄金" / "30m2H策略" / "data" / "raw"
DATA_PROC = ROOT / "黄金" / "30m2H策略" / "data" / "processed"
M30_CSV = ROOT / "base_data" / "XAUUSDm30.csv"

def main():
    print("=" * 60)
    print("  从 MT5 EA CSV 构建 Python 策略数据")
    print("=" * 60)
    
    # 1) 加载 MT5 SMMA 数据
    print(f"\n[1/3] 加载 MT5 CSV: {DEFAULT_MT5_CSV}")
    mt5 = load_mt5_smma(DEFAULT_MT5_CSV)
    print(f"  MT5 bars: {len(mt5)}")
    
    # 2) 生成 H2 数据 (使用 MT5 原生 H2 SMA)
    print(f"\n[2/3] 生成 H2 数据 (MT5 原生 SMA)")
    h2_path = str(DATA_RAW / "H2_XAUUSDm_mt5.csv")
    h2 = generate_h2_from_mt5(mt5, h2_path)
    
    # 3) 运行 prepare 使用 MT5 SMMA
    print(f"\n[3/3] 运行 prepare() 使用 MT5 M30 SMA")
    df, meta = prepare(str(M30_CSV), min_len=8, mt5_smma=mt5)
    
    # 保存标准化数据
    m30_path = str(DATA_PROC / "m30_mt5.csv")
    df.to_csv(m30_path, encoding='utf-8-sig')
    print(f"  Wrote {len(df)} rows to {m30_path}")
    
    print(f"\n{'=' * 60}")
    print(f"  DONE! 数据文件:")
    print(f"    H2: {h2_path}")
    print(f"    M30: {m30_path}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()

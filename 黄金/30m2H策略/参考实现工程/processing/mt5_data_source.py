# -*- coding: utf-8 -*-
"""
processing.mt5_data_source — 从 MT5 EA CSV 导出读取原生 SMMA 数据
替代 Python calc_smma()，让 Python 和 EA 使用完全相同的 SMMA 值
"""
import pandas as pd
import numpy as np
from pathlib import Path

# EA CSV 默认路径 (MT5 Strategy Tester 输出)
DEFAULT_MT5_CSV = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_strategy_signals_export.csv"


def load_mt5_smma(csv_path=None):
    """加载 MT5 EA 导出的 CSV，提取 M30 和 H2 的原生 SMMA 值。
    
    返回:
        m30_smma: DataFrame, index=datetime, columns=[m30_sma5, m30_sma13,
                  h2_sma5, h2_sma13, h2_sma55, h2_dir, h2_cross]
    """
    if csv_path is None:
        csv_path = DEFAULT_MT5_CSV
    
    df = pd.read_csv(csv_path)
    
    # 解析时间: "2018.01.15 06:00" -> datetime
    df['date'] = pd.to_datetime(df['bar_time'], format='%Y.%m.%d %H:%M')
    
    # MT5 数据是服务器时间 (GMT+2)，Python 管道需要 +2h → 客户端时间
    df['date'] = df['date'] + pd.Timedelta(hours=2)
    df = df.set_index('date')
    
    # 提取需要的列
    result = pd.DataFrame(index=df.index)
    result['m30_sma5'] = pd.to_numeric(df['m30_sma5'], errors='coerce')
    result['m30_sma13'] = pd.to_numeric(df['m30_sma13'], errors='coerce')
    result['h2_sma5'] = pd.to_numeric(df['h2_sma5'], errors='coerce')
    result['h2_sma13'] = pd.to_numeric(df['h2_sma13'], errors='coerce')
    result['h2_sma55'] = pd.to_numeric(df['h2_sma55'], errors='coerce')
    result['h2_dir'] = df['h2_dir']
    result['h2_cross'] = df['h2_cross']
    result['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    return result


def generate_h2_from_mt5(mt5_smma, output_path=None):
    """从 MT5 原生 H2 SMA 数据生成 H2 上下文文件 (替代 gen_h2_36col_v2.py)。
    
    只在整点 2h 倍数 (0,2,4,...,22) 提取 H2 bar。
    """
    df = mt5_smma.copy().reset_index()
    
    # 只取整点(2h倍数)的 bar: hour % 2 == 0, minute == 0
    mask = (df['date'].dt.hour % 2 == 0) & (df['date'].dt.minute == 0)
    h2_bars = df[mask].copy()
    
    # 构建 H2 DataFrame
    h2 = pd.DataFrame()
    h2['date'] = h2_bars['date']
    h2['open'] = h2_bars['close']   # 从 M30 close 近似
    h2['high'] = h2_bars['close']
    h2['low'] = h2_bars['close']
    h2['close'] = h2_bars['close']
    h2['volume'] = 0
    h2['SMA_5'] = h2_bars['h2_sma5']
    h2['SMA_13'] = h2_bars['h2_sma13']
    h2['SMA_55'] = h2_bars['h2_sma55']
    h2['SMA_144'] = 0.0
    h2['SMA_233'] = 0.0
    
    # 去除无效值
    h2 = h2.dropna(subset=['SMA_55'])
    h2 = h2[h2['SMA_5'] > 0]
    h2 = h2.reset_index(drop=True)
    
    if output_path:
        h2.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"Wrote {len(h2)} H2 bars to {output_path}")
    
    return h2


print("MT5 data source module loaded.")
print(f"Default CSV: {DEFAULT_MT5_CSV}")

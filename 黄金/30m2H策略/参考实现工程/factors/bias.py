# -*- coding: utf-8 -*-
"""factors.bias - SMA BIAS (signed percentage deviation from SMA)

v4.0 三层分级策略 Layer 1 主要判断因子。
与 SMADistance 关键差异:保留符号,反映"价格在 SMA 之上/之下",
用于 Layer 1 判定 H2 大势的超跌/超涨。

公式:
    BIAS(n) = (close - SMA_n) / SMA_n × 100

符号语义:
    +  = close 在 SMA 之上 (上涨远离均线 → 可能超涨)
    -  = close 在 SMA 之下 (下跌远离均线 → 可能超跌)

数据源优先级:
    1. 优先读 df['SMA_n'] 列 (H2 CSV 已有 SMMA 预计算列,与 close 对齐)
    2. fallback 到 rolling_mean(close, n) (M30 或其他未预计算的场景)
"""
from factors.base import BaseFactor, rolling_mean
import numpy as np


class Bias(BaseFactor):
    """SMA BIAS: (close - SMA_n) / SMA_n × 100, 保留符号"""

    def signal(self, df, n, factor_name):
        close = df['close'].values
        sma_col = f'SMA_{n}'

        # 优先用预计算 SMMA 列 (H2 CSV 已有),保证 close 与 SMA 数值口径一致
        if sma_col in df.columns:
            sma = df[sma_col].values
        else:
            sma = rolling_mean(close, n)

        # +0.01 防 0 除 (对齐 SMADistance 处理)
        df[factor_name] = (close - sma) / (sma + 0.01) * 100
        return df

    @classmethod
    def get_parameter(cls):
        """对应 H2 SMMA 配置的 5 个周期"""
        return [5, 13, 55, 144, 233]

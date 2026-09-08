---
title: SMMA均线参数配置
date: 2026-06-14
author: 难者
category: 交易规则
tags: [SMMA, 均线, MT5, 参数配置, 段分析, 极值追踪, 穿越点]
description: 难论SMMA均线MT5模板参数配置 + 段分析极值追踪与穿越点交易规则
source: 难论SMA均线MT5模板优化版.tpl
knowledge_base:
  version: "3.0"
  language: zh-CN
  market_type: [股票, 期货, 外汇]
---

# SMMA均线参数配置

## 一、模板来源

文件：`难论SMA均线MT5模板优化版.tpl`

## 二、均线参数表

| 均线周期 | MT5参数 | 颜色代码 | 颜色 | 级别 |
|---------|--------|---------|------|------|
| **5** SMMA | InpMAPeriod=5 | 1677215 | 蓝色 |  |
| **13** SMMA | InpMAPeriod=13 | 65535 | 黄色 |  |
| **55** SMMA | InpMAPeriod=55 | 16776960 | 青色 |  |
| **144** SMMA | InpMAPeriod=144 | 16748574 | 绿色 |  |
| **233** SMMA | InpMAPeriod=233 | 16724894 | 橙色 |  |

## 三、均线方法

> **实际配置为 SMMA（平滑移动平均）**

MT5 中 Method 参数含义：

| 值 | 方法 | 说明 |
|----|------|------|
| **1** | **SMMA** | **平滑移动平均（实际配置）** |

## 四、颜色说明

| 颜色 | 用途 |
|------|------|
| 蓝色 (5 SMMA) |  |
| 黄色 (13 SMMA) |  |
| 青色 (55 SMMA) |  |
| 绿色 (144 SMMA) |  |
| 橙色 (233 SMMA) |  |

## 五、级别周期对应

| 本级别 | 次级别 (÷4) | 高级别 (×4) |
|--------|------------|------------|
| 15分钟 | 5分钟 | 1小时 |
| 30分钟 | 15分钟 | 2小时 |
| 1小时 | 15分钟/30分钟 | 4小时 |
| 4小时 | 1小时 | 日线 |
| 日线 | 4小时 | 周线 |

## 六、SMMA 计算公式

### 1. 核心函数

```python
def calc_sma(series, n, m=1):
    """计算加权移动平均 SMA(X, N, M)，前n-1行返回空值"""
    sma = pd.Series(index=series.index, dtype=float)
    sma.iloc[:n-1] = pd.NA
    if len(series) >= n:
        sma.iloc[n-1] = series.iloc[:n].mean()
        for i in range(n, len(series)):
            sma.iloc[i] = (m * series.iloc[i] + (n - m) * sma.iloc[i - 1]) / n
    return sma
```

### 2. 公式说明

**第一步（初始化）**：前 N 个周期的算术平均

```
SMA(N) = (CLOSE(1) + CLOSE(2) + ... + CLOSE(N)) / N
```

**第二步（递推）**：从第 N+1 个开始

```
SMA(i) = (M × CLOSE(i) + (N - M) × SMA(i - 1)) / N
```

| 参数 | 含义 |
|------|------|
| **N** | 周期数（5、13、55、144、233） |
| **M** | 当前价格权重（默认 1） |
| **CLOSE(i)** | 第 i 个周期的收盘价 |
| **SMA(i-1)** | 第 i-1 个周期的 SMA 值 |

### 3. M=1 时的简化公式

```
SMA(i) = CLOSE(i) / N + ((N - 1) / N) × SMA(i - 1)
```

| 周期 N | 当前权重 | 历史权重 |
|--------|---------|---------|
| 5 | 1/5 = 20% | 4/5 = 80% |
| 13 | 1/13 ≈ 7.7% | 12/13 ≈ 92.3% |
| 55 | 1/55 ≈ 1.8% | 54/55 ≈ 98.2% |
| 144 | 1/144 ≈ 0.7% | 143/144 ≈ 99.3% |
| 233 | 1/233 ≈ 0.4% | 232/233 ≈ 99.6% |

### 4. 举例（N=5, M=1）

价格序列：`10, 12, 11, 13, 9, 14, 13, 12, 15, 11`

**初始化**（前 5 个的算术平均）：

```
SMA(5) = (10 + 12 + 11 + 13 + 9) / 5 = 55 / 5 = 11.00
```

**递推计算**：

```
SMA(6) = (1×14 + 4×11.00) / 5 = 58.00 / 5 = 11.60
SMA(7) = (1×13 + 4×11.60) / 5 = 59.40 / 5 = 11.88
SMA(8) = (1×12 + 4×11.88) / 5 = 59.52 / 5 = 11.90
SMA(9) = (1×15 + 4×11.90) / 5 = 62.60 / 5 = 12.52
SMA(10) = (1×11 + 4×12.52) / 5 = 61.08 / 5 = 12.22
```

### 5. 完整调用示例

```python
import pandas as pd

# 假设 close 是收盘价 Series
close = pd.Series([10, 12, 11, 13, 9, 14, 13, 12, 15, 11])

# 计算 5 条 SMMA
sma5  = calc_sma(close, n=5,   m=1)
sma13 = calc_sma(close, n=13,  m=1)
sma55 = calc_sma(close, n=55,  m=1)
sma144 = calc_sma(close, n=144, m=1)
sma233 = calc_sma(close, n=233, m=1)
```

### 6. SMMA 特点

| 特点 | 说明 |
|------|------|
| **比 SMA 平滑** | 每一项都包含前一个 SMMA 的影响 |
| **比 EMA 更平滑** | 权重衰减更缓慢 |
| **无价格跳跃** | 新数据逐渐融入，不会突变 |
| **历史依赖强** | N 越大，历史值权重越高（233 时达 99.6%） |

---

# 段分析与极值追踪

## 七、段定义

| 段类型 | 触发条件 | 状态机转移 |
|--------|---------|-----------|
| **good** | 5 SMA 上穿 13 SMA | down → good → up |
| **up** | 持续 5 SMA > 13 SMA | good → up → up ... |
| **bad** | 5 SMA 下穿 13 SMA | up → bad → down |
| **down** | 持续 5 SMA < 13 SMA | bad → down → down ... |

> **段内包含起始 good/bad 行**：good 行是该 up 段的第一根，bad 行是该 down 段的第一根。

## 八、段内极值追踪

### 1. up 段内最高价追踪

| 列名 | 含义 |
|------|------|
| `up_high_price` | up 段内运行最高价（high 最大值） |
| `up_high_sma13` | 最高价对应 K 线的 SMA_13 |
| `up_high_way_s_way` | 最高价对应 K 线的 way_s_way |
| `up_high_vol_way_s_way` | 最高价对应 K 线的 vol_way_s_way |

**算法**：

```python
if d == 'up':
    if high[i] > c_up_hp:           # 创新高
        c_up_hp  = high[i]
        c_up_hs  = sma13[i]
        c_up_hw  = wsw[i]
        c_up_hvw = vwsw[i]
up_high_price[i] = c_up_hp
```

### 2. down 段内最低价追踪

| 列名 | 含义 |
|------|------|
| `down_low_price` | down 段内运行最低价（low 最小值） |
| `down_low_sma13` | 最低价对应 K 线的 SMA_13 |
| `down_low_way_s_way` | 最低价对应 K 线的 way_s_way |
| `down_low_vol_way_s_way` | 最低价对应 K 线的 vol_way_s_way |

**算法**：

```python
if d == 'down':
    if low[i] < c_dn_lp:            # 创新低
        c_dn_lp  = low[i]
        c_dn_ls  = sma13[i]
        c_dn_lw  = wsw[i]
        c_dn_lvw = vwsw[i]
down_low_price[i] = c_dn_lp
```

### 3. 极值追踪性质

| 性质 | 验证 |
|------|------|
| `up_high_price` 在 up 段内单调不减 | 147 个 up 段全部通过 |
| `down_low_price` 在 down 段内单调不增 | 147 个 down 段全部通过 |
| `up_high_*` 严格匹配段内最高 K 线 | 0 不一致 |
| `down_low_*` 严格匹配段内最低 K 线 | 0 不一致 |

## 九、穿越点（good/bad）的前段极值标记

### 1. 规则

| 穿越点 | 标记内容 | 用途 |
|--------|---------|------|
| **good 行** | 上一 down 段的最低价 K 线四元组 | 做多开仓 + 止损 |
| **bad 行** | 上一 up 段的最高价 K 线四元组 | 做空开仓 + 止损 |

### 2. 列定义

| 列名 | 出现行 | 取值 |
|------|--------|------|
| `prev_seg_low_price` | good | 上一 down 段最低 K 线的 high |
| `prev_seg_low_sma13` | good | 上一 down 段最低 K 线的 SMA_13 |
| `prev_seg_low_way_s_way` | good | 上一 down 段最低 K 线的 way_s_way |
| `prev_seg_low_vol_way_s_way` | good | 上一 down 段最低 K 线的 vol_way_s_way |
| `prev_seg_high_price` | bad | 上一 up 段最高 K 线的 high |
| `prev_seg_high_sma13` | bad | 上一 up 段最高 K 线的 SMA_13 |
| `prev_seg_high_way_s_way` | bad | 上一 up 段最高 K 线的 way_s_way |
| `prev_seg_high_vol_way_s_way` | bad | 上一 up 段最高 K 线的 vol_way_s_way |

## 十、穿越点均价计算与开仓止损

### 1. 均价计算（典型价格）

使用 **(H+L+C)/3** 作为穿越点 K 线的理论开仓价：

```
开仓价 = (high + low + close) / 3
```

**为何用 (H+L+C)/3 而非 close**：

- 充分利用一根 K 线的全部价格信息（high/low/close）
- 技术分析最常用（CCI 等默认参数）
- 比 OHLC 均价（O+H+L+C）/4 少一个无关价格点（open 易跳空）

### 2. 开仓与止损规则

| 方向 | 触发点 | 开仓价 | 止损价 |
|------|--------|--------|--------|
| **做多** | good 行 | `(H+L+C)/3` | `prev_seg_low_sma13` |
| **做空** | bad 行 | `(H+L+C)/3` | `prev_seg_high_sma13` |

### 3. 列定义

| 列名 | 出现行 | 公式 |
| ---- | ---- | ---- |
| `long_entry` | good | `(H+L+C)/3` |
| `long_stop` | good | `prev_seg_low_sma13` |
| `short_entry` | bad | `(H+L+C)/3` |
| `short_stop` | bad | `prev_seg_high_sma13` |

### 4. 验证断言

| 断言 | 结果 |
|------|------|
| `long_entry` 仅在 good 行有值 | 147 行 ✓ |
| `long_stop` 仅在 good 行有值 | 147 行 ✓ |
| `short_entry` 仅在 bad 行有值 | 147 行 ✓ |
| `short_stop` 仅在 bad 行有值 | 147 行 ✓ |
| `long_stop == prev_seg_low_sma13` | good 行 0 不一致 ✓ |
| `short_stop == prev_seg_high_sma13` | bad 行 0 不一致 ✓ |
| `low ≤ long_entry ≤ high` | good 行 0 越界 ✓ |
| `low ≤ short_entry ≤ high` | bad 行 0 越界 ✓ |

## 十一、way_grade 重置规则

在 **good/bad 穿越点**，`way / way_s / way_s_way / vol_way / vol_way_s_way` 全部重置为 0：

```python
if d in ('good', 'bad'):
    y = x = z = 0
    way_s_way = 0.0
    vol_way_s_way = 0.0
```

**这是 by design**，因为穿越点意味着趋势方向切换，way 等级需要重新累计。

## 十二、输出文件结构

### 1. 文件清单

| 文件名 | 编码 | 行数 | 列数 | 用途 |
| ---- | ---- | ---- | ---- | ---- |
| `段分析检查表.csv` | GBK | 14,302 | 16 | 基础段分析 |
| `段分析检查表_utf8.csv` | UTF-8 BOM | 14,302 | 16 | 同上（编码兼容） |
| `段分析_极值追踪.csv` | GBK | 14,302 | 36 | 含极值 + 均价 + 止损 |
| `段分析_极值追踪_utf8.csv` | UTF-8 BOM | 14,302 | 36 | 同上（编码兼容） |

> **编码双版本原则**：GBK 与 `段分析检查表.csv` 一致；UTF-8 BOM 兼容 Excel/macOS。

### 2. 36 列布局

| # | 列名 | 填充规则 |
| -- | ---- | ---- |
| 1-10 | date, open, high, low, close, volume, SMA_5, SMA_13, 方向, 方向_合并后 | 全行 |
| 11-16 | vol_ma_120, way, way_s, way_s_way, vol_way, vol_way_s_way | 全行 |
| 17-20 | up_high_price/sma13/way_s_way/vol_way_s_way | 仅 up 行 |
| 21-24 | down_low_price/sma13/way_s_way/vol_way_s_way | 仅 down 行 |
| 25-28 | prev_seg_high_price/sma13/way_s_way/vol_way_s_way | 仅 bad 行 |
| 29-32 | prev_seg_low_price/sma13/way_s_way/vol_way_s_way | 仅 good 行 |
| 33 | long_entry = (H+L+C)/3 | 仅 good 行 |
| 34 | long_stop = prev_seg_low_sma13 | 仅 good 行 |
| 35 | short_entry = (H+L+C)/3 | 仅 bad 行 |
| 36 | short_stop = prev_seg_high_sma13 | 仅 bad 行 |

### 3. 16 列基础布局

| # | 列名 | 说明 |
| -- | ---- | ---- |
| 1 | date | K 线时间（YYYY/MM/DD HH:MM:SS） |
| 2 | open | 开盘价 |
| 3 | high | 最高价 |
| 4 | low | 最低价 |
| 5 | close | 收盘价 |
| 6 | volume | 成交量 |
| 7 | SMA_5 | 5 周期 SMMA |
| 8 | SMA_13 | 13 周期 SMMA |
| 9 | 方向 | good / up / bad / down |
| 10 | 方向_合并后 | v4 严格链吸收后的方向 |
| 11 | vol_ma_120 | 120 周期成交量均线 |
| 12 | way | way_grade 主值 |
| 13 | way_s | way_grade 短期值 |
| 14 | way_s_way | way_s × way |
| 15 | vol_way | 成交量 way |
| 16 | vol_way_s_way | vol_way × way_s_way |

## 十三、生成脚本

| 脚本 | 输出 | 调用关系 |
| ---- | ---- | ---- |
| `gen_csv.py` | 段分析检查表.csv (+ _utf8) | 16 列基础 |
| `segment_extrema.py` | 段分析_极值追踪.csv (+_utf8) | 36 列 = 16 + 16 极值 + 4 均价止损 |

```bash
# 生成顺序
python F:/use_code/MTA5/gen_csv.py            # 输出 16 列
python F:/use_code/MTA5/segment_extrema.py    # 输出 36 列
```

---

**来源：** MT5模板文件 `难论SMA均线MT5模板优化版.tpl`
**整理时间：** 2026-06-14
**更新内容：**

- v3.0 新增段分析与极值追踪、穿越点均价、止损规则、输出文件结构
- v2.0 原始 SMMA 参数配置

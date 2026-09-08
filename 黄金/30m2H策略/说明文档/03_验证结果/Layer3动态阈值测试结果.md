# Layer 3 动态阈值测试结果

> 当前入口/退出固定为主线版本：`H2 q2 + M15 replace_any_rescue` + `Stage1 2.0R / Stage2 1.5R trail / 4.0R force / Stage3 m30_merged_cross`。
> 这一轮只比较 Layer 3：全样本固定阈值 vs 前一年分位阈值。

## 对照结果

| Variant | Trades | WR | PF | EV | PnL | MaxCL | 2024 | 2024 WR | 2024 PF | 2024 EV | Test PF | Test EV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| global_top35 | 103 | 79.6% | 10.13 | +92.60pt | $1908 | 4 | 6 | 100.0% | 0.00 | +64.84pt | 17.47 | +126.32pt |
| global_top40 | 121 | 78.5% | 9.35 | +80.36pt | $1945 | 5 | 9 | 100.0% | 0.00 | +51.71pt | 16.27 | +110.97pt |
| global_top30 | 89 | 78.7% | 9.33 | +94.17pt | $1676 | 4 | 0 | - | - | - | 15.16 | +130.73pt |
| prior_year_top40 | 128 | 75.0% | 7.68 | +75.43pt | $1931 | 6 | 0 | - | - | - | 17.51 | +132.82pt |
| prior_year_top35 | 113 | 73.5% | 7.18 | +75.78pt | $1713 | 6 | 0 | - | - | - | 16.86 | +146.38pt |
| prior_year_top30 | 111 | 73.0% | 7.14 | +76.55pt | $1699 | 6 | 0 | - | - | - | 16.71 | +151.20pt |

## 分年交易数

| Year | global_top30 | global_top35 | global_top40 | prior_year_top30 | prior_year_top35 | prior_year_top40 |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 24 | 25 | 29 | 53 | 53 | 53 |
| 2021 | 1 | 3 | 7 | 1 | 1 | 3 |
| 2022 | 10 | 10 | 10 | 10 | 10 | 10 |
| 2023 | 7 | 7 | 7 | 0 | 0 | 0 |
| 2024 | 0 | 6 | 9 | 0 | 0 | 0 |
| 2025 | 26 | 31 | 31 | 28 | 28 | 31 |
| 2026 | 21 | 21 | 28 | 19 | 21 | 31 |

## 2024 年阈值来源

| Variant | Threshold | Source | Source Year | Source N |
| --- | --- | --- | --- | --- |
| global_top30 | 0.750654 | global | global | 295 |
| global_top35 | 0.631417 | global | global | 295 |
| global_top40 | 0.603543 | global | global | 295 |
| prior_year_top30 | 0.781817 | prior_year | 2023 | 12 |
| prior_year_top35 | 0.781817 | prior_year | 2023 | 12 |
| prior_year_top40 | 0.781817 | prior_year | 2023 | 12 |

## 当前判断

- 当前扫描里，PF 最高的是 `global_top35`：103 笔，PF 10.13，EV +92.60pt，2024 年 6 笔。
- `global_top35` 的特点是简单、稳定，而且已经能把 2024 年带回 6 笔。
- `prior_year_top30/35/40` 的特点是会顺着年度分布自适应；如果前一年 `Bias_5` 偏弱，下一年门槛会自动放松。
- 需要额外注意：前一年法对样本很少的早期年份更敏感，后续若采用，最好再加 `source_n` 下限或 warm-up 规则。

## 文件

- `data\results\layer3_adaptive_20260627\layer3_adaptive_summary.csv`
- `data\results\layer3_adaptive_20260627\layer3_adaptive_yearly_counts.csv`
- `data\results\layer3_adaptive_20260627\layer3_adaptive_thresholds.csv`
- `data\results\layer3_adaptive_20260627\layer3_adaptive_equity_curve.png`

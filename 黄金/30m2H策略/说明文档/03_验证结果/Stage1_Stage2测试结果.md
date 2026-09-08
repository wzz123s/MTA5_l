# Stage 1 / Stage 2 测试结果

> 基于当前主线组合候选：`combo_h2_q2_plus_replace_any_rescue`。
> Stage 3 固定为当前推荐：`m30_merged_cross`。

## 测试范围

- Stage 1 R: `1.0 / 1.2 / 1.5 / 2.0`
- Stage 2 trail start: `1.5R / 2.0R / 2.5R`
- Stage 2 force close: `2.5R / 3.0R / 4.0R`
- Stage 3: 固定 `m30_merged_cross`

## 最优结果

- 当前扫描最优：Stage 1 `2.0R`，Stage 2 `1.5R trail / 4.0R force`。
- 结果：89 笔，WR 78.7%，PF 9.33，EV +94.17pt，PnL $1676，MaxCL 4。

## 与当前基线对比

- 当前基线：Stage 1 `1.2R`，Stage 2 `2.0R trail / 3.0R force`。
  - PF 8.51，EV +82.03pt，PnL $1460。
- 扫描最优：Stage 1 `2.0R`，Stage 2 `1.5R trail / 4.0R force`。
  - PF 9.33，EV +94.17pt，PnL $1676。

## Top 8

| Stage 1 | Trail | Force | 笔数 | WR | PF | EV | PnL | MaxCL | 验证PF | 验证EV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0R | 1.5R | 4.0R | 89 | 78.7% | 9.33 | +94.17pt | $1676 | 4 | 15.16 | +130.73pt |
| 2.0R | 2.5R | 4.0R | 89 | 76.4% | 9.27 | +94.26pt | $1678 | 5 | 14.97 | +130.70pt |
| 2.0R | 2.0R | 4.0R | 89 | 78.7% | 9.25 | +94.11pt | $1675 | 4 | 14.95 | +130.55pt |
| 1.5R | 1.5R | 4.0R | 89 | 77.5% | 9.21 | +88.66pt | $1578 | 5 | 15.67 | +124.85pt |
| 1.5R | 2.0R | 4.0R | 89 | 77.5% | 9.14 | +88.59pt | $1577 | 5 | 15.44 | +124.67pt |
| 1.5R | 2.5R | 4.0R | 89 | 76.4% | 9.09 | +88.74pt | $1580 | 5 | 15.46 | +124.82pt |
| 2.0R | 1.5R | 3.0R | 89 | 78.7% | 9.07 | +91.32pt | $1626 | 4 | 14.61 | +125.70pt |
| 2.0R | 2.5R | 3.0R | 89 | 76.4% | 9.04 | +91.67pt | $1632 | 5 | 14.40 | +125.34pt |

## 结果文件

- `data\results\stage12_combo_20260627\stage12_combo_summary.csv`
- `data\results\stage12_combo_20260627\stage12_combo_trade_detail.csv`
- `data\results\stage12_combo_20260627\stage12_combo_equity_curve.png`

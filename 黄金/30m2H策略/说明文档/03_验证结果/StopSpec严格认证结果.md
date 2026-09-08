# Stop Spec 严格认证结果

> 当前基线固定为：`Layer1 3.0%` + `pre_cross + cross + post_n(2-6)` + `M15 replace_any + rescue` + `H2 q2 early-gate` + `Layer3 top34%`。
> 本轮只验证 stop spec 下限，`spec_hi` 固定为 `35pt`，退出固定为当前主线三段退出。

## [3,35] - [8,35] 细扫

| Spec | Accepted | L3 threshold | Trades | WR | PF | EV | PnL | MaxCL | MaxDD | MaxDD% | 2024 | Test PF | Test EV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [3, 35] | 372 | 0.609423 | 127 | 81.1% | 10.28 | +78.49pt | $1994 | 4 | $-59 | -0.59% | 9 | 17.04 | +108.16pt |
| [4, 35] | 330 | 0.615698 | 113 | 81.4% | 10.22 | +85.22pt | $1926 | 4 | $-59 | -0.59% | 9 | 17.47 | +115.66pt |
| [5, 35] | 295 | 0.652164 | 102 | 80.4% | 10.37 | +93.75pt | $1912 | 4 | $-59 | -0.59% | 6 | 17.47 | +126.32pt |
| [6, 35] | 269 | 0.669073 | 92 | 81.5% | 10.06 | +95.88pt | $1764 | 4 | $-59 | -0.59% | 6 | 16.53 | +126.86pt |
| [7, 35] | 244 | 0.734796 | 83 | 79.5% | 9.47 | +99.35pt | $1649 | 4 | $-59 | -0.59% | 1 | 15.57 | +135.07pt |
| [8, 35] | 227 | 0.769189 | 77 | 81.8% | 10.32 | +106.28pt | $1637 | 4 | $-59 | -0.59% | 0 | 16.81 | +142.14pt |

## 分年交易数

| Year | lo3 | lo4 | lo5 | lo6 | lo7 | lo8 |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 33 | 27 | 24 | 22 | 21 | 18 |
| 2021 | 4 | 4 | 3 | 1 | 1 | 1 |
| 2022 | 13 | 11 | 10 | 10 | 9 | 9 |
| 2023 | 7 | 7 | 7 | 7 | 7 | 7 |
| 2024 | 9 | 9 | 6 | 6 | 1 | 0 |
| 2025 | 32 | 31 | 31 | 25 | 23 | 23 |
| 2026 | 29 | 24 | 21 | 21 | 21 | 19 |

## [4,35] 相比 [5,35] 新增交易

- 数量：`11`，WR `90.9%`，PF `8.78`，EV `+17.20pt`，MaxCL `1`
- 年份分布：`{2020: 3, 2021: 1, 2022: 1, 2024: 3, 2026: 3}`

| Date | Mode | Dir | Total pt | Stage1 | Stage2 | Stage3 |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-03-17 00:30 | cross | L | +2.60 | 2.0R TP | trail/SL hit | SL hit |
| 2020-03-17 04:00 | cross | S | -24.32 | SL hit | trail/SL hit | SL hit |
| 2020-04-16 10:30 | post_n5 | L | +5.15 | 2.0R TP | trail/SL hit | SL hit |
| 2021-03-01 16:00 | post_n6 | S | +38.46 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2022-11-08 16:00 | post_n2 | L | +53.87 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2024-04-03 16:30 | cross | L | +38.60 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2024-04-03 17:00 | post_n2 | L | +35.16 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2024-04-03 17:30 | post_n3 | L | +2.56 | SL hit | trail/SL hit | M30 merged cross |
| 2026-03-24 04:30 | post_n4 | S | +14.48 | 2.0R TP | trail/SL hit | SL hit |
| 2026-03-24 05:00 | post_n5 | S | +12.78 | 2.0R TP | trail/SL hit | SL hit |
| 2026-03-24 05:30 | post_n6 | S | +9.85 | 2.0R TP | trail/SL hit | SL hit |

## [5,35] 相比 [6,35] 被保留下来的交易

- 数量：`10`，WR `70.0%`，PF `16.88`，EV `+74.65pt`，MaxCL `2`
- 年份分布：`{2020: 2, 2021: 2, 2025: 6}`

| Date | Mode | Dir | Total pt | Stage1 | Stage2 | Stage3 |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-03-06 18:00 | post_n3 | S | +1.96 | 2.0R TP | trail/SL hit | SL hit |
| 2020-03-06 19:00 | post_n5 | S | -16.67 | SL hit | trail/SL hit | SL hit |
| 2021-03-04 19:00 | cross | S | +43.59 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2021-03-04 19:30 | post_n2 | S | -13.77 | SL hit | M30 merged cross | M30 merged cross |
| 2025-04-22 12:30 | pre_cross | S | -16.58 | SL hit | trail/SL hit | SL hit |
| 2025-04-22 14:30 | cross | S | +184.51 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-04-22 15:00 | post_n2 | S | +227.28 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-04-22 15:30 | post_n3 | S | +150.87 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-09-02 15:30 | post_n2 | L | +89.76 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-10-17 15:30 | post_n5 | S | +95.56 | 2.0R TP | 4.0R forced | M30 merged cross |

## 当前判断

- 单看 PF 峰值，`[5, 35]` 最强：PF `10.37`，EV `+93.75pt`，2024 年 `6` 笔。
- 若按“恢复 2024 + 不显著牺牲 EV/PF + 不把样本拉得过松”的标准，`[5,35]` 仍是最平衡主线：`102` 笔，PF `10.37`，EV `+93.75pt`，2024 年 `6` 笔。
- `[4,35]` 会把 2024 交易从 `6` 提到 `9`，但总体 PF 从 `10.37` 降到 `10.22`，EV 从 `+93.75pt` 降到 `+85.22pt`。
- `[6,35]` 虽然 EV 升到 `+95.88pt`，但交易数从 `102` 掉到 `92`，而且 2024 仍只有 `6` 笔；这更像偏保守的备选，不像主线。
- 结论：当前不建议把 stop 下限从 `5pt` 放宽到 `3pt/4pt`，也不建议收紧到 `6pt+` 作为主线。

## 文件

- `data\results\stop_spec_strict_certify_20260627\stop_spec_strict_sweep.csv`
- `data\results\stop_spec_strict_certify_20260627\stop_spec_strict_yearly.csv`
- `data\results\stop_spec_strict_certify_20260627\stop_spec_lo4_added_vs_lo5.csv`
- `data\results\stop_spec_strict_certify_20260627\stop_spec_lo6_removed_vs_lo5.csv`
- `data\results\stop_spec_strict_certify_20260627\stop_spec_strict_equity_curve.png`

# Layer 1 严格认证结果

> 当前固定主线为：`pre_cross + cross + post_n(2-6)` + `M15 replace_any + rescue` + `H2 q2 early-gate` + `Layer3 top34%` + `stop spec [5,35] pt`。
> 本轮只验证 Layer 1 `|Bias_55|` threshold，不再混入 stop / Layer 3 / 退出参数改动。

## 2.0% - 5.0% 细扫

| Threshold | Accepted | Trades | WR | PF | EV | PnL | MaxCL | MaxDD | MaxDD% | 2024 | Test PF | Test EV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0% | 842 | 288 | 69.4% | 6.55 | +56.91pt | $3278 | 6 | $-59 | -0.58% | 23 | 9.25 | +77.05pt |
| 2.5% | 498 | 169 | 75.7% | 9.14 | +73.39pt | $2481 | 6 | $-59 | -0.59% | 14 | 17.34 | +102.54pt |
| 3.0% | 295 | 102 | 80.4% | 10.37 | +93.75pt | $1912 | 4 | $-59 | -0.59% | 6 | 17.47 | +126.32pt |
| 3.2% | 249 | 85 | 81.2% | 9.95 | +98.56pt | $1676 | 4 | $-59 | -0.59% | 2 | 15.11 | +127.94pt |
| 3.4% | 194 | 67 | 79.1% | 10.41 | +113.58pt | $1522 | 3 | $-46 | -0.43% | 0 | 15.39 | +158.70pt |
| 3.6% | 173 | 61 | 82.0% | 13.86 | +125.28pt | $1528 | 3 | $-46 | -0.41% | 0 | 15.39 | +158.70pt |
| 4.0% | 115 | 39 | 82.1% | 12.91 | +122.98pt | $959 | 3 | $-48 | -0.44% | 0 | 12.04 | +171.68pt |
| 5.0% | 53 | 19 | 84.2% | 20.98 | +171.80pt | $653 | 1 | $-14 | -0.14% | 0 | 28.82 | +262.63pt |

## 分年交易数

| Year | thr2.0 | thr2.5 | thr3.0 | thr3.2 | thr3.4 | thr3.6 | thr4.0 | thr5.0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2020 | 56 | 33 | 24 | 20 | 18 | 15 | 13 | 9 |
| 2021 | 27 | 18 | 3 | 1 | 0 | 0 | 0 | 0 |
| 2022 | 17 | 14 | 10 | 9 | 8 | 5 | 5 | 0 |
| 2023 | 21 | 13 | 7 | 7 | 0 | 0 | 0 | 0 |
| 2024 | 23 | 14 | 6 | 2 | 0 | 0 | 0 | 0 |
| 2025 | 78 | 43 | 31 | 25 | 21 | 21 | 9 | 5 |
| 2026 | 61 | 34 | 21 | 21 | 20 | 20 | 12 | 5 |

## 3.4% 相比 3.0% 被删掉的交易

- 数量：`35`，WR `82.9%`，PF `10.21`，EV `+55.79pt`，MaxCL `3`
- 年份分布：`{2020: 6, 2021: 3, 2022: 2, 2023: 7, 2024: 6, 2025: 10, 2026: 1}`

| Date | Mode | Dir | Total pt | Stage1 | Stage2 | Stage3 |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-03-06 18:00 | post_n3 | S | +1.96 | 2.0R TP | trail/SL hit | SL hit |
| 2020-03-06 18:30 | post_n4 | S | -32.07 | SL hit | trail/SL hit | SL hit |
| 2020-03-06 19:00 | post_n5 | S | -16.67 | SL hit | trail/SL hit | SL hit |
| 2020-03-06 19:30 | post_n6 | S | -21.88 | SL hit | trail/SL hit | SL hit |
| 2020-03-17 16:00 | cross | L | +61.01 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2020-03-17 17:30 | post_n4 | L | -81.19 | SL hit | M30 merged cross | M30 merged cross |
| 2021-03-04 19:00 | cross | S | +43.59 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2021-03-04 19:30 | post_n2 | S | -13.77 | SL hit | M30 merged cross | M30 merged cross |
| 2021-06-16 20:00 | cross | S | +140.98 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2022-03-09 11:00 | cross | S | +117.56 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2022-11-08 18:00 | post_n6 | L | +49.41 | 2.0R TP | M30 merged cross | M30 merged cross |
| 2023-03-15 12:00 | pre_cross | L | +44.48 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2023-03-15 13:00 | cross | L | +30.71 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2023-03-15 13:30 | post_n2 | L | +23.57 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2023-03-15 14:00 | post_n3 | L | +14.73 | 2.0R TP | M30 merged cross | M30 merged cross |
| 2023-03-15 14:30 | post_n4 | L | +11.02 | 2.0R TP | M30 merged cross | M30 merged cross |
| 2023-03-15 15:00 | post_n5 | L | +8.20 | 2.0R TP | M30 merged cross | M30 merged cross |
| 2023-03-15 15:30 | post_n6 | L | -46.33 | SL hit | trail/SL hit | SL hit |
| 2024-11-13 16:30 | pre_cross | S | +69.95 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2024-11-13 17:00 | cross | S | +69.95 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2024-11-13 18:00 | post_n3 | S | +88.48 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2024-11-13 18:30 | post_n4 | S | +79.09 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2024-11-13 19:00 | post_n5 | S | +76.44 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2024-11-13 19:30 | post_n6 | S | +5.12 | SL hit | trail/SL hit | M30 merged cross |
| 2025-09-02 15:30 | post_n2 | L | +89.76 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-09-02 16:00 | post_n3 | L | +103.50 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2025-09-02 16:30 | post_n4 | L | +99.52 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2025-09-02 17:00 | post_n5 | L | +126.04 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2025-09-02 17:30 | post_n6 | L | +121.25 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2025-10-17 14:00 | post_n2 | S | +135.58 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-10-17 14:30 | post_n3 | S | +136.81 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2025-10-29 20:00 | cross | S | +62.81 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-10-29 20:30 | post_n2 | S | +93.16 | 2.0R TP | 4.0R forced | M30 merged cross |
| 2025-10-29 21:00 | post_n3 | S | +53.19 | 2.0R TP | trail/SL hit | M30 merged cross |
| 2026-06-05 14:30 | cross | S | +206.68 | 2.0R TP | 4.0R forced | M30 merged cross |

## 当前判断

- 单看 PF / EV 峰值，更严格阈值会继续上升；本轮最高是 `5.0%`，PF `20.98`，EV `+171.80pt`。
- 但如果把“保留有效样本 + 保留 2024 恢复能力 + 不让主线风格过窄”一起考虑，`3.0%` 仍是最平衡主线：`102` 笔，PF `10.37`，EV `+93.75pt`，2024 年 `6` 笔。
- `3.4%` 虽然把 EV 提到 `+113.58pt`，PF 提到 `10.41`，但交易数会从 `102` 缩到 `67`，而且 2024 会再次变成 `0`。
- 结论：`Bias_55 threshold` 不是越大越好；当前不建议把主线从 `3.0%` 收紧到 `3.4%`。

## 文件

- `data\results\layer1_strict_certify_20260628\layer1_strict_sweep.csv`
- `data\results\layer1_strict_certify_20260628\layer1_strict_yearly.csv`
- `data\results\layer1_strict_certify_20260628\layer1_3p4_removed_vs_3p0.csv`
- `data\results\layer1_strict_certify_20260628\layer1_strict_equity_curve.png`

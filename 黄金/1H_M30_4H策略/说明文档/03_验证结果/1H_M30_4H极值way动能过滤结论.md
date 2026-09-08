# 1H_M30_4H 极值 way_s_way / 动能过滤结论

日期：2026-07-25

## 测试目的

本轮验证两个新指标：

1. 做空机会取最近 4 根已收盘 H1 中“最高价对应 K 线”的 `way_s_way`。
2. 做多机会取最近 4 根已收盘 H1 中“最低价对应 K 线”的 `way_s_way`。
3. 额外测试动能指标，包括：
   - `side_extreme_body_momentum_signed`：极值 K 线实体动能，按交易方向取正。
   - `side_extreme_close_momentum_signed_pct`：极值 K 线收盘相对上一根的动能，按交易方向取正。
   - `side_extreme_sma13_gap_momentum_signed_pct`：极值 K 线相对 SMA13 位置变化动能，按交易方向取正。

`way_s_way` 重新用 `1H_M30_4H` 自己的 MT5 H1 原始数据计算，没有复用旧 `30m2H` 的 H2 CSV。

## 重要口径变化

之前的机会池对多空都使用 `H1roll4 high vs H4 SMA55`。  
本轮新增 side-extreme 机会池：

- 做空：最近 4 根已收盘 H1 的最高价相对 H4 SMA55 `>= 2%`。
- 做多：最近 4 根已收盘 H1 的最低价相对 H4 SMA55 `<= -2%`。

这个修正本身带来了明显改善，因为多单不再用“最高价低于 SMA55”这种过严口径，而是用“最低价低于 SMA55”定义机会。

## 基线对比

| 候选 | 机会池 | n | PF | test PF | 0.01 lot净收益 | 正收益年份 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| fd1_h1last6_8_28 | side_extreme_pool | 112 | 2.2954 | 1.8391 | $561.37 | 4/4 |
| fd1_h1last6_8_28 | legacy_high_pool | 90 | 2.3045 | 1.8937 | $481.25 | 2/4 |
| fd1_h1last6_6_28 | side_extreme_pool | 144 | 1.9439 | 1.3945 | $508.99 | 4/4 |
| fd1_h1last6_6_28 | legacy_high_pool | 118 | 1.9512 | 1.5206 | $440.56 | 3/4 |
| fd3_m30sma13_6_28 | side_extreme_pool | 67 | 2.8759 | 2.6092 | $439.74 | 4/4 |
| fd3_m30sma13_6_28 | legacy_high_pool | 50 | 3.1162 | 2.4490 | $404.75 | 3/4 |

结论：`side_extreme_pool` 是本轮最大增益点，优先级高于单独的 `way_s_way` 阈值过滤。

## 最强实际收益候选

```text
fixed_delay_1
+ h1_last6_hilo
+ stop_distance 8-28pt
+ 1H bias5&bias13 同向
+ side_extreme_pool
+ side_extreme_close_momentum_signed_pct >= -0.4
```

结果：

```text
n=108
PF=2.4334
test PF=1.9237
0.01 lot净收益=$585.95
正收益年份=4/4
```

年度拆分：

| year | trades | pnl_points |
| --- | ---: | ---: |
| 2020 | 23 | 404.908 |
| 2021 | 25 | 50.964 |
| 2022 | 32 | 8.245 |
| 2023 | 28 | 121.832 |

说明：4 年均为正，但收益明显集中在 2020，2021/2022 较薄，不能直接跳过滚动窗口验证。

## 稳定性候选

```text
fixed_delay_1
+ h1_last6_hilo
+ stop_distance 6-28pt
+ 1H bias5&bias13 同向
+ side_extreme_pool
+ side_extreme_close_momentum_signed_pct >= -0.4
```

结果：

```text
n=140
PF=2.0367
test PF=1.5030
0.01 lot净收益=$533.56
正收益年份=4/4
```

年度拆分：

| year | trades | pnl_points |
| --- | ---: | ---: |
| 2020 | 26 | 425.538 |
| 2021 | 36 | 10.839 |
| 2022 | 38 | 18.701 |
| 2023 | 40 | 78.487 |

说明：样本更多，年度全正，但 2021/2022 边际仍薄。

## way_s_way 的实际作用

单独使用 `way_s_way` 阈值，没有比 side-extreme 机会池本身带来更大的提升。

较好的观察项：

| 条件 | n | PF | test PF | 0.01 lot净收益 | 正收益年份 |
| --- | ---: | ---: | ---: | ---: | ---: |
| fd1_h1last6_8_28 + way_le_0.9 | 111 | 2.3306 | 1.8365 | $567.91 | 4/4 |
| fd1_h1last6_8_28 + way_le_0.6 | 101 | 2.3408 | 2.0110 | $544.29 | 4/4 |
| fd1_h1last6_8_28 + way_ge_0.3 | 97 | 2.3994 | 1.9387 | $484.50 | 4/4 |

判断：`way_s_way` 有过滤价值，但不是主导增益。当前更适合作为质量确认或风控扰动指标，不建议单独当主过滤条件。

## 动能指标的实际作用

最佳动能过滤是：

```text
side_extreme_close_momentum_signed_pct >= -0.4
```

含义：极值 K 线不能在交易反方向上过度发力。这个过滤只剔除少量样本，但能把 `fd1_h1last6_8_28 + side_extreme_pool` 从 `$561.37` 提到 `$585.95`，同时保持 4/4 年正收益。

## 当前结论

本轮建议把第一层机会池正式改成 side-extreme 口径：

```text
做空：最近 4 根已收盘 H1 的最高价 vs H4 SMA55 >= 2%
做多：最近 4 根已收盘 H1 的最低价 vs H4 SMA55 <= -2%
```

当前最强候选：

```text
fixed_delay_1
+ h1_last6_hilo
+ stop_distance 8-28pt
+ 1H bias5&bias13 同向
+ side_extreme_pool
+ close_momentum_signed_pct >= -0.4
```

当前稳定候选：

```text
fixed_delay_1
+ h1_last6_hilo
+ stop_distance 6-28pt
+ 1H bias5&bias13 同向
+ side_extreme_pool
+ close_momentum_signed_pct >= -0.4
```

`way_s_way` 保留为第三层对照过滤，优先观察 `way_le_0.9`、`way_le_0.6` 和 `way_ge_0.3`，暂不作为主策略硬条件。

## 下一步

1. 对最强候选和稳定候选做月度拆分。
2. 做 BUY/SELL 拆分，确认 side-extreme 是否主要改善多单。
3. 做成本敏感性：点差、滑点、手续费。
4. 做滚动窗口验证，重点检查 2021/2022 的薄收益是否能承受成本。
5. 如果通过，再把 side-extreme 机会池写入正式规则和 EA 参数包。


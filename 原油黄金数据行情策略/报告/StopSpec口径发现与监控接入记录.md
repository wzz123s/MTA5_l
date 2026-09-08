# 重要发现：回测口径与 EA 的一致性核对（StopSpec 单位）

> 记录：2026-08-30 ｜ 背景：监控接入时发现点数换算异常，追溯出 StopSpec 单位问题。

## 一、发现过程

1. 接入 monitor_all_strategies.py 后，Gold total_weighted_pts 异常大（600 万+）；
2. 排查发现：本工程回测的止损距离（prev_seg SMA13 极值）中位数 4.04 美元，远大于最初假设的 "5-35 点"（0.05-0.35 美元）；
3. 对照 MTA5_l 参考（1H_M30_4H）：stop_distance 中位数 12.53 **美元**（不是点）；
4. 确认 EA 母版 InpStopLoPt=5/InpStopHiPt=35 是 **价格单位=美元**（除以 _Point=0.01 得 500-3500 点）。

## 二、结论

- **本工程黄金止损（5-35 美元区间过滤后 n=405 笔，PF 1.62）与 EA 口径一致**，无需改 EA；
- 之前 M2/M3 的 1018 笔基线是**未施加 StopSpec 过滤**的宽口径，需以 405 笔（5-35 美元）为基准口径；
- 405 笔口径：8/8 年正收益、PF 1.62，策略结论稳健（与 1.64 接近）。

## 三、监控接入结果

| 策略 | 交易数 | total_weighted_pts | equity_0.5% | 说明 |
|---|---|---|---|---|
| Gold_DataEvent | 405 | 195,699 | $66,814 | 5-35 美元 StopSpec 口径 |
| Oil_DataEvent | 58 | 8.7 | $554 | way门口径（空单为主） |

- 接入方式：STRATEGY_CONFIGS 添加 2 条 + build_strategy 分支 + adapter 模块（monitor_data_event_adapter.py）；
- 监控输出：observation_dashboard/dashboard_report.md（含新策略行）；
- 备份：monitor_all_strategies.py.bak_dataevent（可回滚）。

## 四、遗留

- ~~M3 变体报告（V1_T2h PF 1.753 等）基于 1018 笔口径，需用 405 笔口径重跑确认~~ **已完成（M3.6）**：405 笔口径 V1_T2h PF 1.647（vs 基线 1.621）、8/8 年正收益，决策不变；V5_widen3.0x_4h PF 1.685、EV 全表最高；结果见《M3_变体回测与稳健性报告》第八节；
- ~~expected_ledger_gold.csv 也需按 405 笔口径重新生成~~ **已完成**：expected_ledger_gold.csv=1,020 行（340 信号×3 段，V1_T2h+StopSpec 5-35）；expected_ledger_oil.csv=56 行（way门 V1_T1h，PF 1.488 复核一致）；格式与 EA 账本对齐（真实价格/逐段行/EA reason 文案）。

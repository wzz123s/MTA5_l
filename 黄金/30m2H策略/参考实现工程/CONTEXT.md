# 项目上下文

> 作用：只保留接手时必须知道的固定背景。  
> 不写：日常进展、动态待办、长篇研究结论。

## 一、工作区

- 工作区：`F:\use_code\MTA5`
- 当前主策略文档：`30m2H策略/策略说明.md`
- 当前已模板化的多周期策略：`H1_M30_H4策略`

## 二、核心文档入口

- [30m2H策略/策略说明.md](/F:/use_code/MTA5/30m2H策略/策略说明.md)
  - 主线 30m x 2H 当前方案、当前参数、主待办
- [H1_M30_H4策略/策略说明.md](/F:/use_code/MTA5/H1_M30_H4策略/策略说明.md)
  - 多周期策略模板示例
- [findings.md](/F:/use_code/MTA5/findings.md)
  - 研究结论
- [progress.md](/F:/use_code/MTA5/progress.md)
  - 时间日志
- [task_plan.md](/F:/use_code/MTA5/task_plan.md)
  - 当前待办

## 三、当前固定规则

- Markdown 文档默认使用 `utf-8-sig`。
- 结果类 CSV 主版本优先使用 `utf-8-sig`。
- 各策略的止损、门参数、Stage 参数必须按各自周期独立计算，不能直接复用主线结果。
- 多周期策略目录标准结构：
  - `data/raw`
  - `data/processed`
  - `data/validation`
  - `scripts/data_source`
  - `scripts/prepare`
  - `scripts/signals`
  - `scripts/validate`
  - `scripts/bundle`

## 四、当前主线状态

- 30m x 2H 主线已经完成 Python 侧主要严格认证。
- 当前最高优先级是主线 `30m2H策略` 与 `auto_trade/30m2H_Strategy_EA.mq5` 的最终对齐和回测收口。
- Python 侧现在已经有 `EA 可执行口径` 诊断模式，可用于复核 `M30 CLOSE` 的 Layer 3 边界补偿和 `M15 slot1` 的 runtime-style StopSpec rescue。
- 多周期矩阵当前只按 `H1_M30_H4策略` 模板向其他策略铺工作区骨架，不作为当前主线任务。
- EA / MT5 最终对齐尚未收口，仍属于未完成事项。

## 五、四个协作文档边界

- `findings.md`：只写结论
- `progress.md`：只写过程
- `task_plan.md`：只写待办
- `CONTEXT.md`：只写固定背景

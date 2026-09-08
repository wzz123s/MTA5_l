# 黄金乖离反转策略

- 正式口径：BiasReversal_Combo_EA v8（默认多头 6H门+H1金叉；做空分支门禁关闭 EnableShort=false）
- 审查状态：✅ 已审（2026-09-06 修 vol_ma 尾随）；BUG 报告见 data\validation
- 对齐状态：✅ Tester 回放 351/351=100%（默认多头路径全窗）
- 观察期：模拟盘实时中（observation_dashboard\BiasReversal），警戒：连续3月后2月负
- 当前待办：做空侧 PF1.01 门禁待决策；台账列改造已闭环（见说明文档）

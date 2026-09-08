# 原油单独 2H 策略（独立全流程验证）

> 2H cross/pre_cross 触发；可选 2-bar way/vol_way 确认因子；2H 结构止损 0.1-1.0%；单段退出。

## lookahead 风险说明（2026-08-17）

- `cross_pre_confirm` / `cross_confirm`（lookahead=True）：确认值在全序列上计算，`filter_short_segments(min_len=8)` 会用**未来交叉**回溯合并短段，属 lookahead，PF 被高估。
- `cross_confirm_causal`（lookahead=False）：确认值按 [0..确认bar] 窗口因果计算，与实盘 EA 行为一致，**作为正式（可交易）口径**。
- 实盘 EA `USOIL2H_CrossConfirm_EA`（v5）即因果口径；2021–2026 Tester 冒烟 53/53 与因果期望一致（0 missing / 0 extra / PnL 零误差）。

| variant | lookahead | n | wr | pf0 | ev0 | test_pf0 | wf_train_20_23 | wf_test_24_26 | pf_0.02 | pf_0.05 | pf_0.1 | pos_years |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cross_pre | False | 718 | 14.9025 | 1.0465 | 0.0136 | 0.8221 | 0.9922 | 1.1036 | 0.9793 | 0.8912 | 0.7711 | 3/7 |
| cross_pre_confirm | True | 79 | 29.1139 | 1.6114 | 0.2092 | 1.3378 | 1.4170 | 1.7948 | 1.5309 | 1.4216 | 1.2640 | 5/7 |
| cross_confirm | True | 68 | 32.3529 | 1.8021 | 0.2768 | 1.5731 | 1.5465 | 2.0356 | 1.7161 | 1.5986 | 1.4277 | 5/7 |
| cross | False | 302 | 18.8742 | 1.1379 | 0.0476 | 1.1380 | 0.8489 | 1.4212 | 1.0763 | 0.9937 | 0.8771 | 5/6 |
| cross_confirm_causal | False | 99 | 22.2222 | 1.0995 | 0.0386 | 0.6199 | 1.0271 | 1.1560 | 1.0461 | 0.9734 | 0.8685 | 4/7 |

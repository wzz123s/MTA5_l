# 时间语义与原始数据诊断（2026-07-12）

## 结论摘要
- base/raw 文件同步：`3/4` 个核心文件的前 12 位 SHA256 一致；不一致项需要看是否只是 BOM/编码/截断差异。
- MT5 bar export 与 Python M30 processed 的 close 最佳时间偏移：`MT5 bar_time + 90.0 min`，匹配 `95435.0` 行，close mean abs diff `0.000062`。
- SMA 最佳偏移并不自动证明语义已对齐：SMA5 最佳 `90.0 min`，mean abs diff `0.067395`；SMA13 最佳 `90.0 min`，mean abs diff `0.134612`。
- M15/M30 覆盖关系最佳映射：`m30_date_plus_0_min_in_m15`，覆盖 `99.99%`。
- H2 context 当前保留三种时间：`source_time -> decision_time` 中位偏移 `240 min`，这确认 H2 不是单一 date 口径。
- M30 映射到最近 H2 decision 后仍有 `1082` 行超过常规 `0/30/60/90 min` 桶，需要作为数据缺口/休市窗口处理。
- 当前仍不能把 MT5-only bar export 直接当成完整信号源：它只覆盖 bar 级 M30 导出，M15 SLOT1 仍要依赖 tester log 或后续 trade ledger。

## 输出文件
- `time_semantics_dataset_summary_20260712.csv`：核心输入文件的行数、时间范围、重复时间、close 摘要。
- `raw_sync_consistency_20260712.csv`：base_data 与策略 raw 的同步对比。
- `timeframe_alignment_20260712.csv`：M15/M30 与 H2 decision bucket 映射检查。
- `mt5_export_shift_quality_20260712.csv`：不同时间偏移下 MT5 export 与 Python M30 processed 的 close/SMA 匹配质量。
- `mt5_export_best_shift_sample_20260712.csv`：close 最佳偏移下的前 200 行样本。

## 后续动作
1. 先解释 raw/full_data 不一致项是编码/BOM 还是真实数据差异。
2. 用当前最佳偏移结果复核 `bar_time` 是否代表 MT5 completed bar、EA aligned anchor，还是 tester 新 bar 时间。
3. 在重建 Python-MT5 数据版前，先固定 H2 的 `source_time/client_bucket_time/decision_time` 使用规则。
4. MT5 侧下一步必须补 `trade ledger` 或更完整的 M15 SLOT1 bar-level export，否则胜率、止损次数和资金曲线仍不能可靠并表。

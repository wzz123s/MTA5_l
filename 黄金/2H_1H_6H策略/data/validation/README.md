# 2H_1H_6H 验证数据

## 目标文件

- `strategy_summary.csv`
- `yearly_performance.csv`
- `ea_parameter_pack.json`
- `ea_alignment_readiness.csv`
- `ea_alignment/python_expected_trade_ledger.csv`
- `ea_alignment/python_vs_ea_alignment_summary.csv`
- `ea_alignment/python_vs_ea_alignment_detail.csv`

## 通过标准

最终通过标准必须和 `1H_M30_4H` 一致：

```text
expected_rows = actual_rows
matched_rows = expected_rows
missing_in_actual = 0
extra_in_actual = 0
max_abs_entry_diff = 0
max_abs_stop_diff = 0
max_abs_exit_diff = 0
max_abs_pnl_points_diff = 0
```

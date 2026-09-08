# 2H_M30_6H EA 对齐说明

> 更新时间：2026-07-26

## 当前状态

- Python 研究参数包：已生成。
- EA 源文件：已存在。
- 策略目录内 `.ex5`：未确认存在。
- Python vs EA 逐笔对齐：未通过。
- 当前状态码：`python_research_rebuilt__ea_pending`

## 参数摘要

| 项目 | 当前值 |
| --- | --- |
| Variant | `2H_M30_6H__6h_bias5_13_55_signed_pos` |
| Stage | `2.0 / 2.5 / 4.0` |
| Units | `0.5 / 0.5 / 2.0` |
| Lots | `0.01 / 0.01 / 0.04` |
| Primary StopSpec | `2-10pt` |
| StopSpec source | `stop_distance` |
| Research set | `2H_M30_6H_Strategy_EA.mt5_raw_research_20260725.set` |

## 当前对齐结果

`data/validation/ea_alignment/alignment_summary.csv` 记录的现有结果为：

| status | expected_rows | ea_rows | matched | python_only | ea_only | pnl_sign_mismatch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mismatch | 453 | 54 | 9 | 444 | 45 | 4 |

这说明当前 EA 输出与 Python 预期并不一致，不能用于部署。

## 部署前必须补齐

1. 编译专用 EA，并确认 `.ex5` 位于策略目录或 MT5 Experts 目录。
2. 用研究 set 文件运行 MT5 Strategy Tester。
3. 导出完整 EA trade ledger。
4. 重新跑 `compare_python_vs_ea.py`。
5. 对齐结果必须达到：
   - expected_rows = ea_rows
   - missing = 0
   - extra = 0
   - entry / stop / exit / pnl 差异为 0 或在预先定义容差内
6. 对齐通过后，再生成部署前参数评审。

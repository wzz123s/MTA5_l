# Dynamic Risk Alignment

## Summary
| source      |   trade_count |   final_balance |   dynamic_total_profit |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |   avg_total_lot |
|:------------|--------------:|----------------:|-----------------------:|------------:|---------------:|---------------------:|---------------------:|--------------------:|----------------:|
| python_only |           118 |         9585.57 |                9085.57 |          51 |        43.2203 |                   95 |                   44 |             15.6285 |        0.503475 |
| python_mt5  |           101 |        15767.1  |               15267.1  |          51 |        50.495  |                   81 |                   30 |             15.0598 |        0.842772 |
| mt5_ledger  |            66 |        -1127.15 |               -1627.15 |          14 |        21.2121 |                   66 |                   66 |             15.5093 |                 |

## Key Overlap
| source      |   shared |   python_only |   mt5_only |
|:------------|---------:|--------------:|-----------:|
| python_only |        0 |           118 |         66 |
| python_mt5  |        0 |           101 |         66 |

## Interpretation
- `python_only` / `python_mt5` 动态风险版目前仍沿用 Python 信号集合，只是把固定 `total_$ * 5` 改成了按 EA 风格的动态手数近似。
- `mt5_ledger` 侧统计的是已成交并完成 close 的唯一信号，不等于 EA 日志里的全部信号触发。
- 因此这里的主键 overlap 更适合作为“可比成交集合”的第一轮诊断，而不是最终对齐结论。

## Output Files
- `python_only_dynamic_risk_trades.csv`
- `python_mt5_dynamic_risk_trades.csv`
- `mt5_ledger_unique_signals.csv`
- `dynamic_risk_compare_summary.csv`
- `dynamic_risk_key_overlap_summary.csv`

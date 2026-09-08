# Dynamic Risk Alignment - shift90

## Summary

| source      |   trade_count |   final_balance |   dynamic_total_profit |   win_count |   win_rate_pct |   any_stage_sl_count |   all_stage_sl_count |   avg_stop_pts_spec |   avg_total_lot | source_variant                    |
|:------------|--------------:|----------------:|-----------------------:|------------:|---------------:|---------------------:|---------------------:|--------------------:|----------------:|:----------------------------------|
| python_only |           118 |         9585.57 |                9085.57 |          51 |        43.2203 |                   95 |                   44 |             15.6285 |        0.503475 | baseline                          |
| python_mt5  |            98 |         1969.91 |                1469.91 |          46 |        46.9388 |                   80 |                   33 |             15.1367 |        0.227551 | shift90_python_h2_context_q2early |
| mt5_ledger  |            78 |         3940.37 |                3440.37 |          33 |        42.3077 |                   72 |                   36 |             15.9843 |                 | ledger_deinitfix_full_20260713_v1 |

## Exact Key Overlap

| source      |   shared |   python_only |   mt5_only |
|:------------|---------:|--------------:|-----------:|
| python_only |        0 |           118 |         78 |
| python_mt5  |        0 |            98 |         78 |

## Notes
- Python-MT5 uses `dynamic_risk_inputs_shift90_20260713`.
- Exact key overlap is kept as a coarse diagnostic; mapped trade alignment is the authoritative next step.
- This output intentionally does not overwrite `dynamic_risk_alignment_magic0fix_20260713`.

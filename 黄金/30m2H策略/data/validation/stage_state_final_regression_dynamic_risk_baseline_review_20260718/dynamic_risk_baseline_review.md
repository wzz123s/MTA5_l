# Final Regression: Dynamic-risk Baseline Review

- Decision date: 2026-07-18
- Check id: `python_mt5_dynamic_risk_baseline_review`
- Status: `pass`
- Pass: `True`
- Reason: `detail_files_recompute_match_dynamic_summary_and_freeze_snapshot`

## Recomputed Metrics

| source | trades | final balance | profit | win rate | any SL | all SL | avg stop |
|---|---:|---:|---:|---:|---:|---:|---:|
| python_only | 118 | 23366.397104 | 22866.397098 | 45.762712 | 95 | 44 | 15.62845 |
| python_mt5 | 98 | 4039.57227 | 3539.57227 | 48.979592 | 80 | 33 | 15.136681 |
| mt5_ledger | 82 | 1649.84 | 1149.84 | 40.243902 | 75 | 40 | 16.170248 |

## Comparison Result

- Failed comparisons: `0`
- Dynamic summary and final-freeze baseline snapshot are both consistent with the detail files.

## Boundary

This review only validates dynamic-risk baseline accounting. It does not modify signals, mapper policy, EA behavior, or run-package files.

# Three-version Unified Report Refresh

- Decision date: 2026-07-18
- Check id: `three_version_unified_report_refresh`
- Status: `pass`
- Pass: `True`
- Reason: `three_version_report_refreshed_from_frozen_inputs`

## Unified Metrics

| version | initial | leverage | lot model | trades | final | net profit | wins | win rate | any SL | all SL |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| Python-only 基础版 | 500.0 | 100 | Python dynamic-risk approximation with MT5 value/stage-lot parity | 118 | 23366.397104 | 22866.397098 | 54 | 45.762712 | 95 | 44 |
| Python-MT5 数据版 | 500.0 | 100 | Python dynamic-risk approximation with MT5 value/stage-lot parity | 98 | 4039.57227 | 3539.57227 | 48 | 48.979592 | 80 | 33 |
| MT5-only EA 单独版 | 500.0 | 100 | EA real dynamic lots in MT5 tester | 82 | 1649.84 | 1149.84 | 33 | 40.243902 | 75 | 40 |

## Direct Gap Vs MT5

| version | trade gap | final gap | net profit gap | win-rate gap pp | any SL gap | all SL gap |
|---|---:|---:|---:|---:|---:|---:|
| Python-only 基础版 | 36 | 21716.557104 | 21716.557098 | 5.51881 | 20 | 4 |
| Python-MT5 数据版 | 16 | 2389.73227 | 2389.73227 | 8.73569 | 5 | -7 |

## Alignment Snapshot

| source | matched | reliable | relaxed | python unmatched | mt5 unmatched | matched profit diff |
|---|---:|---:|---:|---:|---:|---:|
| Python-only 基础版 | 61 | 43 | 18 | 57 | 21 | 4502.497765 |
| Python-MT5 数据版 | 60 | 29 | 31 | 38 | 22 | 654.894778 |

## Scope Boundary

- `Python-only 基础版`: Useful for signal/data pipeline diagnostics, not a direct replacement for MT5 tester equity.
- `Python-MT5 数据版`: Closer to MT5 data than Python-only, but final balance remains affected by Python execution assumptions.
- `MT5-only EA 单独版`: Primary frozen run baseline for run-package readiness.

## Conclusion

- The three-version report is refreshed from frozen final-regression inputs.
- The large final-balance spread is explained by different signal sets plus different execution models, not by a ledger closure failure.
- MT5-only remains the frozen run baseline; Python-only and Python-MT5 remain diagnostic/parity references.

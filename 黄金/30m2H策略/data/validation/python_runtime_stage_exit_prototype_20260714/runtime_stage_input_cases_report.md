# Python Runtime-Style Stage Exit Prototype Inputs

## Scope

- Source: `stage_exit_rule_alignment_shift90_close_retry_20260714/stage_exit_rule_alignment_stage_rows.csv`.
- MT5 ledger enrichment: `mt5_full_close_retry_fix_20260714/30m2H_strategy_trade_ledger.csv`.
- Rows: one case per matched trade stage.

## Summary

|   runtime_priority | runtime_priority_reason                               |   stage | exit_relation                      |   rows |
|-------------------:|:------------------------------------------------------|--------:|:-----------------------------------|-------:|
|                  1 | Python Stage1 TP but MT5 broker SL                    |       1 | py_tp_mt5_sl                       |      7 |
|                  1 | Python Stage2 forced exit but MT5 broker SL           |       2 | py_forced_mt5_sl                   |      5 |
|                  1 | Python merged cross exit but MT5 broker SL            |       2 | py_cross_mt5_sl                    |      4 |
|                  1 | Python win becomes MT5 loss                           |       2 | both_stop_or_trail                 |      3 |
|                  1 | Python merged cross exit but MT5 broker SL            |       3 | py_cross_mt5_sl                    |      5 |
|                  1 | Python win becomes MT5 loss                           |       3 | both_cross_but_price_time_may_diff |      1 |
|                  2 | MT5 expert close where Python did not model same exit |       1 | mt5_expert_close_other             |      3 |
|                  2 | MT5 expert close where Python did not model same exit |       2 | mt5_expert_close_other             |      3 |
|                  2 | Both cross-like but price/time may differ             |       3 | both_cross_but_price_time_may_diff |     11 |
|                  2 | MT5 expert close where Python did not model same exit |       3 | mt5_expert_close_other             |      1 |
|                  3 | lower priority control case                           |       1 | py_tp_mt5_expert_close             |     13 |
|                  3 | lower priority control case                           |       1 | both_initial_sl                    |      5 |
|                  3 | lower priority control case                           |       1 | other                              |      1 |
|                  3 | lower priority control case                           |       2 | both_stop_or_trail                 |     12 |
|                  3 | lower priority control case                           |       2 | py_forced_mt5_expert_close         |      2 |
|                  3 | lower priority control case                           |       3 | both_initial_sl                    |     11 |

## Priority Rules

- Priority 1: Python win/TP/forced/cross becomes MT5 broker SL, or sign changes from win to loss.
- Priority 2: MT5 expert close or both cross-like exits with possible price/time mismatch.
- Priority 3: lower-risk control cases.

## Output Files

- `runtime_stage_input_cases.csv`
- `runtime_stage_input_case_summary.csv`

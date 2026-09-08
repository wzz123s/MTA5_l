# Runtime-Style Stage Exit Priority 1 M15 Refine

## Scope

- Input: `runtime_stage_priority1_replay.csv` cases with `needs_tick_for_order = True`, plus `runtime_stage_case_004` and `runtime_stage_case_007`.
- Market data: `data/processed/m15_context_bars.csv`.
- This is still OHLC bar-level replay, not tick replay.

## Key Counts

- Refined cases: `22`.
- M15-covered cases: `15`.
- No M15 coverage: `7`.
- Still tick/log-needed after M15 refine: `17`.
- Resolved by M15 bar ordering: `5`.
- MT5 SL before Python-style M15 event: `6`.
- MT5 SL before any selected Python-style M15 event: `3`.
- MT5 SL before Stage2 trail-on threshold: `2`.
- Stage3 M15 SL seen but M30 cross not refined: `3`.
- Same M15 bar order still unknown: `0`.

## Overall Summary

| m15_refine_class                     | still_needs_tick   | m15_has_coverage   |   rows |
|:-------------------------------------|:-------------------|:-------------------|-------:|
| no_m15_coverage                      | True               | False              |      7 |
| mt5_sl_before_python_event           | True               | True               |      4 |
| stage3_m15_sl_seen_cross_not_refined | True               | True               |      3 |
| mt5_sl_before_no_python_event        | False              | True               |      2 |
| mt5_sl_before_stage2_trail_on        | True               | True               |      2 |
| mt5_sl_before_python_event           | False              | True               |      2 |
| mt5_sl_before_no_python_event        | True               | True               |      1 |
| python_event_before_mt5_sl           | False              | True               |      1 |

## Stage Summary

|   stage | exit_relation                      | m15_refine_class                     | still_needs_tick   |   rows |
|--------:|:-----------------------------------|:-------------------------------------|:-------------------|-------:|
|       1 | py_tp_mt5_sl                       | mt5_sl_before_python_event           | True               |      3 |
|       1 | py_tp_mt5_sl                       | mt5_sl_before_python_event           | False              |      1 |
|       1 | py_tp_mt5_sl                       | no_m15_coverage                      | True               |      1 |
|       1 | py_tp_mt5_sl                       | python_event_before_mt5_sl           | False              |      1 |
|       2 | both_stop_or_trail                 | mt5_sl_before_stage2_trail_on        | True               |      2 |
|       2 | both_stop_or_trail                 | no_m15_coverage                      | True               |      1 |
|       2 | py_cross_mt5_sl                    | no_m15_coverage                      | True               |      2 |
|       2 | py_cross_mt5_sl                    | mt5_sl_before_no_python_event        | True               |      1 |
|       2 | py_forced_mt5_sl                   | mt5_sl_before_no_python_event        | False              |      2 |
|       2 | py_forced_mt5_sl                   | mt5_sl_before_python_event           | False              |      1 |
|       2 | py_forced_mt5_sl                   | mt5_sl_before_python_event           | True               |      1 |
|       2 | py_forced_mt5_sl                   | no_m15_coverage                      | True               |      1 |
|       3 | both_cross_but_price_time_may_diff | no_m15_coverage                      | True               |      1 |
|       3 | py_cross_mt5_sl                    | stage3_m15_sl_seen_cross_not_refined | True               |      3 |
|       3 | py_cross_mt5_sl                    | no_m15_coverage                      | True               |      1 |

## Notes

- 2020/2021 and early 2022 cases are outside current M15 processed coverage and remain tick/log-needed.
- A same-M15-bar result means M15 narrowed the uncertainty but cannot determine tick order.
- Stage3 M30 cross chronology is not recomputed from M15; M15 only refines broker SL timing around the case.

## Output Files

- `runtime_stage_priority1_m15_refine.csv`
- `runtime_stage_priority1_m15_refine_summary.csv`
- `runtime_stage_priority1_m15_refine_by_stage.csv`

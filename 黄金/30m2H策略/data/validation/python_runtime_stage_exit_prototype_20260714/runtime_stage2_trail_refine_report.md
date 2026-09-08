# Runtime Stage2 Trail Refine

## Scope

- Input: Priority 1 Stage2 cases from `runtime_stage_input_cases.csv`.
- Market data: `data/processed/m30_mt5.csv`.
- Trail model: after 1.5R, SELL trail SL ratchets down to M30 SMA13; BUY trail SL ratchets up to M30 SMA13.
- This is M30 bar-level diagnostic logic, not tick/order-log equivalent.

## Key Counts

- Stage2 cases: `12`.
- Initial SL before force: `11`.
- Trail SL touch before/at MT5 SL bar: `1`.
- Force before MT5 SL, session/log needed: `0`.
- First event in partial opening M30 bar: `10`.
- Need log/tick after refine: `10`.

## Summary

| stage2_trail_refine_class          | needs_log_or_tick   |   rows |
|:-----------------------------------|:--------------------|-------:|
| initial_sl_before_force            | True                |     10 |
| initial_sl_before_force            | False               |      1 |
| trail_sl_touch_before_or_at_mt5_sl | False               |      1 |

## Relation Summary

| exit_relation      | stage2_trail_refine_class          | needs_log_or_tick   |   rows |
|:-------------------|:-----------------------------------|:--------------------|-------:|
| both_stop_or_trail | initial_sl_before_force            | True                |      3 |
| py_cross_mt5_sl    | initial_sl_before_force            | True                |      3 |
| py_cross_mt5_sl    | trail_sl_touch_before_or_at_mt5_sl | False               |      1 |
| py_forced_mt5_sl   | initial_sl_before_force            | True                |      4 |
| py_forced_mt5_sl   | initial_sl_before_force            | False               |      1 |

## Output Files

- `runtime_stage2_trail_refine.csv`
- `runtime_stage2_trail_refine_summary.csv`
- `runtime_stage2_trail_refine_by_relation.csv`

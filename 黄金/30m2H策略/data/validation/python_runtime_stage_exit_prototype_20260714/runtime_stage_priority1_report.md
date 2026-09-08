# Runtime-Style Stage Exit Priority 1 Replay

## Scope

- Input: `runtime_stage_input_cases.csv`, filtered to `runtime_priority = 1`.
- Market data: `data/processed/m30_mt5.csv`.
- This is an M30 OHLC approximation, not a tick-equivalent replay.

## Overall Summary

| predicted_runtime_class           | explains_mt5_sl   | contradicts_mt5_sl   | needs_tick_for_order   |   rows |
|:----------------------------------|:------------------|:---------------------|:-----------------------|-------:|
| broker_sl_first                   | True              | False                | True                   |     19 |
| broker_sl_first                   | True              | False                | False                  |      2 |
| broker_sl_first                   | False             | False                | True                   |      1 |
| ambiguous_same_bar_with_broker_sl | True              | False                | True                   |      1 |
| stage2_trail_on_first             | False             | False                | False                  |      1 |
| stage3_cross_first                | False             | True                 | False                  |      1 |

## Key Counts

- Priority 1 cases: `25`.
- MT5 SL cases: `24`.
- MT5 SL explained by M30 approximation: `22`.
- Non-SL MT5 cases in Priority 1: `1`.
- Cases requiring tick/order detail for exact ordering: `21`.

## Stage Summary

|   stage | exit_relation                      | predicted_runtime_class           | explains_mt5_sl   | contradicts_mt5_sl   | needs_tick_for_order   |   rows |
|--------:|:-----------------------------------|:----------------------------------|:------------------|:---------------------|:-----------------------|-------:|
|       1 | py_tp_mt5_sl                       | broker_sl_first                   | True              | False                | True                   |      6 |
|       1 | py_tp_mt5_sl                       | broker_sl_first                   | True              | False                | False                  |      1 |
|       2 | both_stop_or_trail                 | broker_sl_first                   | True              | False                | True                   |      3 |
|       2 | py_cross_mt5_sl                    | broker_sl_first                   | True              | False                | True                   |      3 |
|       2 | py_cross_mt5_sl                    | stage2_trail_on_first             | False             | False                | False                  |      1 |
|       2 | py_forced_mt5_sl                   | broker_sl_first                   | True              | False                | True                   |      3 |
|       2 | py_forced_mt5_sl                   | ambiguous_same_bar_with_broker_sl | True              | False                | True                   |      1 |
|       2 | py_forced_mt5_sl                   | broker_sl_first                   | True              | False                | False                  |      1 |
|       3 | both_cross_but_price_time_may_diff | broker_sl_first                   | False             | False                | True                   |      1 |
|       3 | py_cross_mt5_sl                    | broker_sl_first                   | True              | False                | True                   |      4 |
|       3 | py_cross_mt5_sl                    | stage3_cross_first                | False             | True                 | False                  |      1 |

## Interpretation Rules

- `broker_sl_first` means the M30 bar sequence can explain the MT5 broker SL before Python's modeled exit.
- `ambiguous_same_bar_with_broker_sl` means broker SL and a Python-style event occur in the same M30 bar; tick order is required.
- `stage*_first` classes contradict an MT5 SL if no broker SL appears in the same first bar.
- `partial_open_bar=True` marks cases where the first scanned M30 bar already started before the EA open time.

## Output Files

- `runtime_stage_priority1_replay.csv`
- `runtime_stage_priority1_summary.csv`
- `runtime_stage_priority1_overall_summary.csv`

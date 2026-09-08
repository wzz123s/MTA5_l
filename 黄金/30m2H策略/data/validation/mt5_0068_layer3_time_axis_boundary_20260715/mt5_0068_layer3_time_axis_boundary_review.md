# mt5_0068 Layer3/time-axis boundary audit

## Scope

- Target: `mt5_0068`.
- Purpose: separate true Layer3 rejection from mixed +90/+120 data-axis effects.
- This is read-only and does not modify signal, Stage, dynamic-risk, or EA files.

## Decision

- Current +90 M15 SLOT1 Layer3 pass: `False` (`Bias_5=0.71206`, threshold `0.91684`).
- +120/M30-aligned Layer3 pass: `True` (`Bias_5=1.05559`, threshold `0.91684`).
- `mt5_0068` must not be injected into the current +90 full-chain prototype.
- Passing under +120 is evidence of a time-axis semantics issue, not permission to loosen Layer3.

## Target Signal

| mt5_trade_id   | raw_anchor          | aligned_plus90      | log_time            | log_plus90          |   entry |    stop |      sd |
|:---------------|:--------------------|:--------------------|:--------------------|:--------------------|--------:|--------:|--------:|
| mt5_0068       | 2026-02-02 23:30:00 | 2026-02-03 01:00:00 | 2026-02-02 23:15:00 | 2026-02-03 00:45:00 | 4718.61 | 4683.85 | 34.7657 |

## Time-Axis Summary

| item         | raw_time            | plus90              | plus120             | current_bridge_uses   |
|:-------------|:--------------------|:--------------------|:--------------------|:----------------------|
| raw_anchor   | 2026-02-02 23:30:00 | 2026-02-03 01:00:00 | 2026-02-03 01:30:00 | plus90                |
| m15_log_time | 2026-02-02 23:15:00 | 2026-02-03 00:45:00 | 2026-02-03 01:15:00 | plus90                |

## Presence Matrix

| check              | source        | time_target         | time_exact_exists   | time_nearest_before   | time_nearest_after   |   time_nearest_before_delta_min |   time_nearest_after_delta_min |
|:-------------------|:--------------|:--------------------|:--------------------|:----------------------|:---------------------|--------------------------------:|-------------------------------:|
| m15_log_raw        | raw_m15       | 2026-02-02 23:15:00 | True                | 2026-02-02 23:15:00   | 2026-02-02 23:15:00  |                               0 |                              0 |
| m15_log_plus90     | processed_m15 | 2026-02-03 00:45:00 | False               | 2026-02-02 23:45:00   | 2026-02-03 01:15:00  |                              60 |                             30 |
| m15_log_plus120    | processed_m15 | 2026-02-03 01:15:00 | True                | 2026-02-03 01:15:00   | 2026-02-03 01:15:00  |                               0 |                              0 |
| m30_anchor_raw     | raw_m30       | 2026-02-02 23:30:00 | True                | 2026-02-02 23:30:00   | 2026-02-02 23:30:00  |                               0 |                              0 |
| m30_anchor_plus90  | shift_m30     | 2026-02-03 01:00:00 | False               | 2026-02-02 23:30:00   | 2026-02-03 01:30:00  |                              90 |                             30 |
| m30_anchor_plus120 | shift_m30     | 2026-02-03 01:30:00 | True                | 2026-02-03 01:30:00   | 2026-02-03 01:30:00  |                               0 |                              0 |
| h2_eval_plus90     | h2_context    | 2026-02-03 01:00:00 | True                | 2026-02-03 01:00:00   | 2026-02-03 01:00:00  |                               0 |                              0 |
| h2_eval_plus120    | h2_context    | 2026-02-03 01:30:00 | True                | 2026-02-03 01:30:00   | 2026-02-03 01:30:00  |                               0 |                              0 |

## Layer3 Eval Matrix

| variant                              | eval_time           | h2_lookup_time      | h2_source_bar_time   |   Bias_5 |   layer3_threshold |   threshold_margin | layer3_pass   | note                                                            |
|:-------------------------------------|:--------------------|:--------------------|:---------------------|---------:|-------------------:|-------------------:|:--------------|:----------------------------------------------------------------|
| current_m15_slot1_aligned_plus90     | 2026-02-03 01:00:00 | 2026-02-03 01:00:00 | 2026-02-02 23:30:00  | 0.712056 |           0.916843 |          -0.204787 | False         | Current bridge date/eval_time; this is the P0 prototype result. |
| m15_entry_log_plus90_lookup          | 2026-02-03 00:45:00 | 2026-02-03 00:30:00 | 2026-02-02 23:00:00  | 0.763255 |           0.922095 |          -0.15884  | False         | Entry-bar +90 boundary; H2 lookup falls to latest <= 00:45.     |
| m15_entry_log_plus120_lookup         | 2026-02-03 01:15:00 | 2026-02-03 01:00:00 | 2026-02-02 23:30:00  | 0.712056 |           0.916843 |          -0.204787 | False         | Processed M15 +2h boundary; still evaluates at H2 01:00.        |
| m30_anchor_plus120                   | 2026-02-03 01:30:00 | 2026-02-03 01:30:00 | 2026-02-03 00:00:00  | 1.05559  |           0.916843 |           0.13875  | True          | Consistent raw +2h M30 processed boundary.                      |
| m30_close_rule_on_plus90_date_plus30 | 2026-02-03 01:30:00 | 2026-02-03 01:30:00 | 2026-02-03 00:00:00  | 1.05559  |           0.916843 |           0.13875  | True          | If the +90 date were treated like M30 CLOSE Layer3 shift.       |
| raw_anchor_no_shift                  | 2026-02-02 23:30:00 | 2026-02-02 23:00:00 | 2026-02-02 21:30:00  | 0.418879 |           0.925664 |          -0.506785 | False         | Server-time raw anchor only, diagnostic control.                |

## Raw/Processed Window Evidence

| source                       | date_dt             |    open |    high |     low |   close |   volume |   spread |   SMA_5 |   SMA_13 | ledger_entry_inside_hilo   | ledger_stop_inside_hilo   |
|:-----------------------------|:--------------------|--------:|--------:|--------:|--------:|---------:|---------:|--------:|---------:|:---------------------------|:--------------------------|
| raw_m15_server_time          | 2026-02-02 23:15:00 | 4718.37 | 4763.46 | 4715.87 | 4738.09 |     6594 |      240 |  nan    |   nan    | True                       | False                     |
| raw_m15_server_time          | 2026-02-02 23:30:00 | 4738.17 | 4750.49 | 4716.92 | 4731.69 |     5890 |      240 |  nan    |   nan    | True                       | False                     |
| processed_m15_plus120_window | 2026-02-03 01:15:00 | 4718.37 | 4763.46 | 4715.87 | 4738.09 |     6594 |      240 | 4683.06 |  4679.4  | True                       | False                     |
| processed_m15_plus120_window | 2026-02-03 01:30:00 | 4738.17 | 4750.49 | 4716.92 | 4731.69 |     5890 |      240 | 4692.78 |  4683.42 | True                       | False                     |
| raw_m30_server_time          | 2026-02-02 23:30:00 | 4738.17 | 4775.1  | 4716.92 | 4774.15 |     9726 |      240 |  nan    |   nan    | True                       | False                     |
| raw_m30_server_time          | 2026-02-03 00:00:00 | 4774.23 | 4829.28 | 4766.24 | 4819.8  |    17092 |      160 |  nan    |   nan    | False                      | False                     |
| raw_m30_server_time          | 2026-02-03 00:30:00 | 4819.87 | 4830.95 | 4773.88 | 4780.42 |    17663 |      160 |  nan    |   nan    | False                      | False                     |
| shift_m30_window             | 2026-02-03 01:30:00 | 4738.17 | 4775.1  | 4716.92 | 4774.15 |     9726 |      240 | 4699.39 |  4692.96 | True                       | False                     |
| shift_m30_window             | 2026-02-03 02:00:00 | 4774.23 | 4829.28 | 4766.24 | 4819.8  |    17092 |      160 | 4723.47 |  4702.72 | False                      | False                     |

## Output Files

- `mt5_0068_time_axis_summary.csv`
- `mt5_0068_presence_matrix.csv`
- `mt5_0068_layer3_eval_matrix.csv`
- `mt5_0068_raw_processed_windows.csv`
- `mt5_0068_current_raw_window.csv`
- `mt5_0068_boundary_decision.csv`

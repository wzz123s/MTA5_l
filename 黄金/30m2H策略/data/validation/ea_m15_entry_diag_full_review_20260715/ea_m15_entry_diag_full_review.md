# EA M15 early-entry full diagnostic review

## 结论

- 本报告使用 full-history tester 导出的 `30m2H_strategy_m15_entry_diag.csv`，不是短窗口 smoke。
- 两个重点 Python-unmatched 样本均已定位到 EA `TryM15EarlyEntry()` 的逐 bar 诊断行。
- 若 `stage_count < max_pos` 且结果不是 `SKIP_MAX_POS`，则不能再把原因归为纯持仓占用或 max position。
- 后续修复应按下表的 `classification` 和 `recommended_next_check` 分支推进。

## Target summary

| stable_case                          | original_trade_id   | filtered_trade_id   | python_target_time   | mt5_raw_anchor_time   | expected_trigger_family   | expected_mode   | expected_dir   |   anchor_diag_rows |   slot1_diag_rows | primary_diag_time   | primary_result   | primary_detail   |   stage_count |   max_pos |   signal_dir | signal_src        |   stop_pts_spec |   active_ledger_rows_at_primary_time | result_sequence   | classification                         | recommended_next_check                                                              |
|:-------------------------------------|:--------------------|:--------------------|:---------------------|:----------------------|:--------------------------|:----------------|:---------------|-------------------:|------------------:|:--------------------|:-----------------|:-----------------|--------------:|----------:|-------------:|:------------------|----------------:|-------------------------------------:|:------------------|:---------------------------------------|:------------------------------------------------------------------------------------|
| far_runtime_rescue_20251021_postn6   | python_mt5_0079     | python_mt5_0078     | 2025-10-21 10:00:00  | 2025-10-21 08:30:00   | M15 SLOT1                 | post_n6         | SELL           |                  1 |                 1 | 2025-10-21 08:15:00 | SPEC_FAIL        | SPEC_FAIL_PROXY  |             2 |         3 |           -1 | post_n5_m15_slot1 |          84.189 |                                    2 | SPEC_FAIL:1       | stop_or_symbol_spec_gate/not_max_pos   | diff EA stop_pts_spec and Python stop/spec gate for the raw anchor                  |
| far_runtime_rescue_20251017_precross | python_mt5_0073     | python_mt5_0073     | 2025-10-17 11:00:00  | 2025-10-17 09:30:00   | M15 SLOT1                 | pre_cross       | SELL           |                  1 |                 1 | 2025-10-17 09:15:00 | NO_SIGNAL_DIR    | nan              |             2 |         3 |            0 | nan               |         nan     |                                    2 | NO_SIGNAL_DIR:1   | m15_signal_mode_divergence/not_max_pos | diff M15 pre_cross/is_cross/post_n counter between Python and EA for the raw anchor |

## Ledger baseline

| source       |   rows |   unique_signal_anchors |   net_profit |   final_balance_from_net |
|:-------------|-------:|------------------------:|-------------:|-------------------------:|
| trade_ledger |    234 |                      78 |      3311.35 |                  3811.35 |
| deal_history |    468 |                         |      3311.35 |                  3811.35 |

## Target exact diagnostic rows

| stable_case                          | diag_time           | completed_m15_open   | anchor_time      |   slot_in_m30 |   stage_count |   max_pos | pre_cross   | is_cross   |   merged_post_n_counter |   signal_dir | signal_src        | layer1_pass   | layer3_pass   |   stop_pts_spec | result        | detail          |
|:-------------------------------------|:--------------------|:---------------------|:-----------------|--------------:|--------------:|----------:|:------------|:-----------|------------------------:|-------------:|:------------------|:--------------|:--------------|----------------:|:--------------|:----------------|
| far_runtime_rescue_20251021_postn6   | 2025-10-21 08:15:00 | 2025.10.21 08:00     | 2025.10.21 08:30 |             1 |             2 |         3 | false       | false      |                      -5 |           -1 | post_n5_m15_slot1 | true          | true          |          84.189 | SPEC_FAIL     | SPEC_FAIL_PROXY |
| far_runtime_rescue_20251017_precross | 2025-10-17 09:15:00 | 2025.10.17 09:00     | 2025.10.17 09:30 |             1 |             2 |         3 | false       | false      |                     121 |            0 | nan               | false         | false         |         nan     | NO_SIGNAL_DIR | nan             |

## Overall M15 diagnostic result counts

| result         |   rows |     pct |
|:---------------|-------:|--------:|
| SLOT2_DISABLED |  98795 | 49.2257 |
| NO_SIGNAL_DIR  |  74650 | 37.1952 |
| LAYER1_FAIL    |  23553 | 11.7355 |
| SKIP_MAX_POS   |   2913 |  1.4514 |
| LAYER3_FAIL    |    427 |  0.2128 |
| NO_SLOT        |    208 |  0.1036 |
| SPEC_FAIL      |    104 |  0.0518 |
| EXECUTED       |     29 |  0.0144 |
| STOP_FAIL      |     19 |  0.0095 |

## Signals export rows around targets

| stable_case                          | bar_time         | bar_dt              | decision   | skip_reason        |
|:-------------------------------------|:-----------------|:--------------------|:-----------|:-------------------|
| far_runtime_rescue_20251021_postn6   | 2025.10.21 06:30 | 2025-10-21 06:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 07:00 | 2025-10-21 07:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 07:30 | 2025-10-21 07:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 08:00 | 2025-10-21 08:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 08:30 | 2025-10-21 08:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 09:00 | 2025-10-21 09:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 09:30 | 2025-10-21 09:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 10:00 | 2025-10-21 10:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251021_postn6   | 2025.10.21 10:30 | 2025-10-21 10:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 07:30 | 2025-10-17 07:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 08:00 | 2025-10-17 08:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 08:30 | 2025-10-17 08:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 09:00 | 2025-10-17 09:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 09:30 | 2025-10-17 09:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 10:00 | 2025-10-17 10:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 10:30 | 2025-10-17 10:30:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 11:00 | 2025-10-17 11:00:00 | SKIP       | no_cross_m30_or_h2 |
| far_runtime_rescue_20251017_precross | 2025.10.17 11:30 | 2025-10-17 11:30:00 | SKIP       | no_cross_m30_or_h2 |

## Output files

- `target_m15_entry_diag_rows.csv`: exact `anchor_time == raw_anchor` rows.
- `target_m15_entry_diag_windows.csv`: target +/-120 minute diagnostic windows.
- `target_active_positions_at_diag_time.csv`: ledger positions active at each primary diag time.
- `target_signals_export_windows.csv`: coarse M30 signals export around target anchors.
- `m15_entry_diag_result_counts.csv`: global result counts for the full run.
- `ledger_baseline_summary.csv`: full-run ledger/deal net check.

## Window note

- `target_m15_entry_diag_windows.csv` contains 39 rows; use it for detailed row-by-row inspection.

# P0 data-axis bridge prototype review

## Scope

- Candidates: `mt5_0068`, `mt5_0005`, `mt5_0019`.
- This prototype uses MT5 ledger signal entry/stop and time-axis metadata only.
- It does not use MT5 ledger net profit to create Python PnL.
- Layer3 uses the current EA-executable H2 rolling threshold: top 34%, lookback 500 H2 rows.

## Summary

- Raw bridge candidates: `3`.
- Accepted bridge pass: `3/3`.
- Picked bridge pass: `2/3`.
- Full-chain ready now: `0/3`.
- Missing M15 entry window rows: `3`.
- Missing M30 aligned rows: `1`.

## Decision

- At least one P0 row fails accepted/Layer3 reconstruction; do not enter full-chain replay before resolving the failed boundary.
- Next mergeable step must be data backfill or explicit data-axis bridge generation, followed by a real Stage/dynamic-risk replay.

## Acceptance Matrix

| mt5_trade_id   | date                | mode      | dir   |      sd | spec_pass   |   Bias_55 | layer1_pass   | raw_bridge_pass   | accepted_bridge_pass   | picked_bridge_pass   |
|:---------------|:--------------------|:----------|:------|--------:|:------------|----------:|:--------------|:------------------|:-----------------------|:---------------------|
| mt5_0068       | 2026-02-03 01:00:00 | pre_cross | L     | 34.7657 | True        |   4.73011 | True          | True              | True                   | False                |
| mt5_0005       | 2020-03-13 17:30:00 | post_n3   | S     | 33.4915 | True        |   5.82241 | True          | True              | True                   | True                 |
| mt5_0019       | 2020-08-04 19:00:00 | post_n6   | L     | 19.5663 | True        |   3.25733 | True          | True              | True                   | True                 |

## Layer3 Matrix

| mt5_trade_id   | date                | trigger   | layer3_eval_time    | h2_lookup_time      | h2_source_bar_time   |   Bias_5 |   layer3_threshold_ea |   layer3_hist_count | layer3_pass_ea   | accepted_bridge_pass   | picked_bridge_pass   |
|:---------------|:--------------------|:----------|:--------------------|:--------------------|:---------------------|---------:|----------------------:|--------------------:|:-----------------|:-----------------------|:---------------------|
| mt5_0068       | 2026-02-03 01:00:00 | M15 SLOT1 | 2026-02-03 01:00:00 | 2026-02-03 01:00:00 | 2026-02-02 23:30:00  | 0.712056 |              0.916843 |                 500 | False            | True                   | False                |
| mt5_0005       | 2020-03-13 17:30:00 | M15 SLOT1 | 2020-03-13 17:30:00 | 2020-03-13 17:30:00 | 2020-03-13 16:00:00  | 1.91755  |              0.428532 |                 500 | True             | True                   | True                 |
| mt5_0019       | 2020-08-04 19:00:00 | M15 SLOT1 | 2020-08-04 19:00:00 | 2020-08-04 19:00:00 | 2020-08-04 17:30:00  | 0.95291  |              0.337316 |                 500 | True             | True                   | True                 |

## Missing Data Requirements

| mt5_trade_id   | date                | entry_time          | entry_bar_minute    | m30_has_aligned_time   | m15_has_entry_bar_exact   | m15_has_entry_bar_minute   | required_m30_time   | required_m15_window_start   | required_m15_window_end   | stage_replay_min_ready_current   | full_chain_ready_now   | required_rule_change                                                      | data_source_requirement                                 |
|:---------------|:--------------------|:--------------------|:--------------------|:-----------------------|:--------------------------|:---------------------------|:--------------------|:----------------------------|:--------------------------|:---------------------------------|:-----------------------|:--------------------------------------------------------------------------|:--------------------------------------------------------|
| mt5_0068       | 2026-02-03 01:00:00 | 2026-02-03 00:45:00 | 2026-02-03 00:45:00 | False                  | False                     | False                      | 2026-02-03 01:00:00 | 2026-02-03 00:30:00         | 2026-02-03 01:00:00       | False                            | False                  | backfill_m30_shift90_and_m15_entry_window                                 | export_or_backfill_MT5_M15_bars_for_required_m15_window |
| mt5_0005       | 2020-03-13 17:30:00 | 2020-03-13 17:15:06 | 2020-03-13 17:15:00 | True                   | False                     | False                      | 2020-03-13 17:30:00 | 2020-03-13 17:00:00         | 2020-03-13 17:30:00       | True                             | False                  | backfill_m15_entry_window_then_rebuild_m15_slot1_over_existing_m30_parent | export_or_backfill_MT5_M15_bars_for_required_m15_window |
| mt5_0019       | 2020-08-04 19:00:00 | 2020-08-04 18:45:09 | 2020-08-04 18:45:00 | True                   | False                     | False                      | 2020-08-04 19:00:00 | 2020-08-04 18:30:00         | 2020-08-04 19:00:00       | True                             | False                  | backfill_m15_entry_window_then_add_m15_slot1_bridge_parent                | export_or_backfill_MT5_M15_bars_for_required_m15_window |

## Output Files

- `p0_bridge_raw_candidates.csv`
- `p0_bridge_acceptance_matrix.csv`
- `p0_bridge_layer3_matrix.csv`
- `p0_bridge_missing_data_requirements.csv`

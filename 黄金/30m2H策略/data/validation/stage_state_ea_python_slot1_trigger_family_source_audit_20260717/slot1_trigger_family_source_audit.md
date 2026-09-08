# Stage-State EA vs Python SLOT1 Trigger-Family Source Audit

## Final Decision

- Target count: `5`.
- Python relabel gap count: `4`.
- Base sequence reset gap count: `1`.
- StopSpec rescue path gap count: `0`.
- Insufficient code evidence count: `0`.
- EA label drift secondary count: `5`.
- All targets have EA source hit: `True`.
- All targets have Python source hit: `True`.
- All targets have timeline evidence: `True`.
- Diagnostic source rule found: `True`.
- Prototype gate: `False`.
- Main signal gate: `False`.
- EA behavior gate: `False`.
- Mapping gate: `False`.
- Merge gate: `False`.

## Classification Summary

| source_primary_classification   |   count |   mt5_net_profit_sum |   reliable_mapped_count | mt5_ids                             |
|:--------------------------------|--------:|---------------------:|------------------------:|:------------------------------------|
| python_relabel_gap              |       4 |               209.71 |                       1 | mt5_0052;mt5_0054;mt5_0068;mt5_0069 |
| base_sequence_reset_gap         |       1 |               -88.35 |                       0 | mt5_0067                            |

## Case Review

| mt5_trade_id   | signal_anchor_time   | dir_norm   | mt5_signal_src                      |   mt5_net_profit | source_primary_classification   | source_secondary_classifications       | ea_exact_event_kinds     | layer12_nearest_near_nonpostn_time   | layer12_nearest_near_nonpostn_mode   | raw_nearest_day_postn_time   | raw_nearest_day_postn_mode   | timeline_python_modes   |
|:---------------|:---------------------|:-----------|:------------------------------------|-----------------:|:--------------------------------|:---------------------------------------|:-------------------------|:-------------------------------------|:-------------------------------------|:-----------------------------|:-----------------------------|:------------------------|
| mt5_0052       | 2025-10-07 14:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           -11.97 | python_relabel_gap              | ea_label_drift;python_relabel_gap      | Candidate;Execute;SIGNAL | 2025-10-07 13:30:00                  | cross                                | nan                          | nan                          | cross                   |
| mt5_0054       | 2025-10-14 18:30:00  | BUY        | post_n5_m15_slot1_replace_or_rescue |           201.68 | python_relabel_gap              | ea_label_drift;python_relabel_gap      | Candidate;Execute;SIGNAL | 2025-10-14 17:30:00                  | cross                                | nan                          | nan                          | cross                   |
| mt5_0067       | 2026-02-02 15:00:00  | BUY        | post_n4_m15_slot1_replace_or_rescue |           -88.35 | base_sequence_reset_gap         | ea_label_drift;base_sequence_reset_gap | Candidate;Execute;SIGNAL | nan                                  | nan                                  | 2026-02-03 02:00:00          | post_n2                      | cross;pre_cross         |
| mt5_0068       | 2026-02-02 16:30:00  | SELL       | post_n2_m15_slot1_replace_or_rescue |             2.03 | python_relabel_gap              | ea_label_drift;python_relabel_gap      | Candidate;Execute;SIGNAL | 2026-02-02 17:00:00                  | cross                                | nan                          | nan                          | cross;pre_cross         |
| mt5_0069       | 2026-02-02 18:00:00  | SELL       | post_n5_m15_slot1_replace_or_rescue |            17.97 | python_relabel_gap              | ea_label_drift;python_relabel_gap      | Candidate;Execute;SIGNAL | 2026-02-02 17:00:00                  | cross                                | nan                          | nan                          | cross                   |

## Case Code Map

| mt5_trade_id   | source_primary_classification   | side   | component                                 | file                                                    |   start_line |   end_line |
|:---------------|:--------------------------------|:-------|:------------------------------------------|:--------------------------------------------------------|-------------:|-----------:|
| mt5_0052       | python_relabel_gap              | EA     | TryM15EarlyEntry classification           | auto_trade\30m2H_Strategy_EA.mq5                        |         2903 |       2933 |
| mt5_0052       | python_relabel_gap              | EA     | TryM15EarlyEntry candidate logging        | auto_trade\30m2H_Strategy_EA.mq5                        |         2944 |       2951 |
| mt5_0052       | python_relabel_gap              | EA     | TryM15EarlyEntry stop/spec/tag            | auto_trade\30m2H_Strategy_EA.mq5                        |         2976 |       3047 |
| mt5_0052       | python_relabel_gap              | Python | build_candidate_frames                    | scripts\_m15_h2_combo_test.py                           |           77 |         85 |
| mt5_0052       | python_relabel_gap              | Python | collect_cross_candidates                  | scripts\_m15_early_entry_test.py                        |          162 |        194 |
| mt5_0052       | python_relabel_gap              | Python | collect_pre_cross_candidates              | scripts\_m15_early_entry_test.py                        |          118 |        159 |
| mt5_0052       | python_relabel_gap              | Python | apply_replace_variant                     | scripts\_m15_early_entry_test.py                        |          380 |        410 |
| mt5_0052       | python_relabel_gap              | Python | build_rescued_trades                      | scripts\_m15_early_entry_test.py                        |          413 |        434 |
| mt5_0052       | python_relabel_gap              | Python | rebuild_python_mt5_shift90 SLOT1 pipeline | 黄金/30m2H策略\scripts\signals\rebuild_python_mt5_shift90.py |          222 |        249 |
| mt5_0054       | python_relabel_gap              | EA     | TryM15EarlyEntry classification           | auto_trade\30m2H_Strategy_EA.mq5                        |         2903 |       2933 |
| mt5_0054       | python_relabel_gap              | EA     | TryM15EarlyEntry candidate logging        | auto_trade\30m2H_Strategy_EA.mq5                        |         2944 |       2951 |
| mt5_0054       | python_relabel_gap              | EA     | TryM15EarlyEntry stop/spec/tag            | auto_trade\30m2H_Strategy_EA.mq5                        |         2976 |       3047 |
| mt5_0054       | python_relabel_gap              | Python | build_candidate_frames                    | scripts\_m15_h2_combo_test.py                           |           77 |         85 |
| mt5_0054       | python_relabel_gap              | Python | collect_cross_candidates                  | scripts\_m15_early_entry_test.py                        |          162 |        194 |
| mt5_0054       | python_relabel_gap              | Python | collect_pre_cross_candidates              | scripts\_m15_early_entry_test.py                        |          118 |        159 |
| mt5_0054       | python_relabel_gap              | Python | apply_replace_variant                     | scripts\_m15_early_entry_test.py                        |          380 |        410 |
| mt5_0054       | python_relabel_gap              | Python | build_rescued_trades                      | scripts\_m15_early_entry_test.py                        |          413 |        434 |
| mt5_0054       | python_relabel_gap              | Python | rebuild_python_mt5_shift90 SLOT1 pipeline | 黄金/30m2H策略\scripts\signals\rebuild_python_mt5_shift90.py |          222 |        249 |
| mt5_0067       | base_sequence_reset_gap         | EA     | UpdateMergedPostNState                    | auto_trade\30m2H_Strategy_EA.mq5                        |         2396 |       2453 |
| mt5_0067       | base_sequence_reset_gap         | EA     | TryM15EarlyEntry classification           | auto_trade\30m2H_Strategy_EA.mq5                        |         2903 |       2933 |
| mt5_0067       | base_sequence_reset_gap         | EA     | TryM15EarlyEntry candidate logging        | auto_trade\30m2H_Strategy_EA.mq5                        |         2944 |       2951 |
| mt5_0067       | base_sequence_reset_gap         | Python | collect_cross_candidates                  | scripts\_m15_early_entry_test.py                        |          162 |        194 |
| mt5_0067       | base_sequence_reset_gap         | Python | collect_post_candidates                   | scripts\_m15_early_entry_test.py                        |          197 |        228 |
| mt5_0067       | base_sequence_reset_gap         | Python | add_pre_cross_and_counter                 | processing\direction.py                                 |          110 |        148 |
| mt5_0068       | python_relabel_gap              | EA     | TryM15EarlyEntry classification           | auto_trade\30m2H_Strategy_EA.mq5                        |         2903 |       2933 |
| mt5_0068       | python_relabel_gap              | EA     | TryM15EarlyEntry candidate logging        | auto_trade\30m2H_Strategy_EA.mq5                        |         2944 |       2951 |
| mt5_0068       | python_relabel_gap              | EA     | TryM15EarlyEntry stop/spec/tag            | auto_trade\30m2H_Strategy_EA.mq5                        |         2976 |       3047 |
| mt5_0068       | python_relabel_gap              | Python | build_candidate_frames                    | scripts\_m15_h2_combo_test.py                           |           77 |         85 |
| mt5_0068       | python_relabel_gap              | Python | collect_cross_candidates                  | scripts\_m15_early_entry_test.py                        |          162 |        194 |
| mt5_0068       | python_relabel_gap              | Python | collect_pre_cross_candidates              | scripts\_m15_early_entry_test.py                        |          118 |        159 |
| mt5_0068       | python_relabel_gap              | Python | apply_replace_variant                     | scripts\_m15_early_entry_test.py                        |          380 |        410 |
| mt5_0068       | python_relabel_gap              | Python | build_rescued_trades                      | scripts\_m15_early_entry_test.py                        |          413 |        434 |
| mt5_0068       | python_relabel_gap              | Python | rebuild_python_mt5_shift90 SLOT1 pipeline | 黄金/30m2H策略\scripts\signals\rebuild_python_mt5_shift90.py |          222 |        249 |
| mt5_0069       | python_relabel_gap              | EA     | TryM15EarlyEntry classification           | auto_trade\30m2H_Strategy_EA.mq5                        |         2903 |       2933 |
| mt5_0069       | python_relabel_gap              | EA     | TryM15EarlyEntry candidate logging        | auto_trade\30m2H_Strategy_EA.mq5                        |         2944 |       2951 |
| mt5_0069       | python_relabel_gap              | EA     | TryM15EarlyEntry stop/spec/tag            | auto_trade\30m2H_Strategy_EA.mq5                        |         2976 |       3047 |
| mt5_0069       | python_relabel_gap              | Python | build_candidate_frames                    | scripts\_m15_h2_combo_test.py                           |           77 |         85 |
| mt5_0069       | python_relabel_gap              | Python | collect_cross_candidates                  | scripts\_m15_early_entry_test.py                        |          162 |        194 |
| mt5_0069       | python_relabel_gap              | Python | collect_pre_cross_candidates              | scripts\_m15_early_entry_test.py                        |          118 |        159 |
| mt5_0069       | python_relabel_gap              | Python | apply_replace_variant                     | scripts\_m15_early_entry_test.py                        |          380 |        410 |
| mt5_0069       | python_relabel_gap              | Python | build_rescued_trades                      | scripts\_m15_early_entry_test.py                        |          413 |        434 |
| mt5_0069       | python_relabel_gap              | Python | rebuild_python_mt5_shift90 SLOT1 pipeline | 黄金/30m2H策略\scripts\signals\rebuild_python_mt5_shift90.py |          222 |        249 |

## Interpretation

- The 4-row cluster is best treated as `python_relabel_gap`: EA determines the SLOT1 trigger family at runtime from the current M30 context and merged counter, while Python SLOT1 replacement/rescue keeps the raw M30 `cross/pre_cross` mode.
- `mt5_0067` remains a separate `base_sequence_reset_gap`: Python raw has a same-direction `cross` near the EA anchor and only reaches same-mode `post_n` later.
- StopSpec/rescue tagging is not supported as the post_n creator. EA appends `_replace_or_rescue` after selecting the mode, and Python rescue/replacement preserves the existing mode.
- This audit is diagnostic-only. It opens no EA, Python main-signal, mapping, dynamic-risk, or merge gate.

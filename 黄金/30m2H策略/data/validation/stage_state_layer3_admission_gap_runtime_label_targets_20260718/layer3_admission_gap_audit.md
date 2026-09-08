# Stage-State Layer3 Admission Gap Audit For Runtime-Label Targets

## Final Decision

- Missing Layer3 target count: `2`.
- Missing target failure reasons: `layer3_threshold_fail`.
- Missing all threshold fail: `True`.
- Controls admitted after maxpos: `True`.
- Low-blast admission rule supported: `False`.
- Layer3 admission prototype gate: `False`.
- Main signal gate: `False`.
- EA behavior gate: `False`.
- Mapping gate: `False`.
- Merge gate: `False`.

## Target Candidate Specs

| mt5_trade_id   | mt5_signal_src                      | signal_anchor_time   | dir_norm   | candidate_time      | candidate_mode   | candidate_variant   | candidate_source                    | ea_runtime_mode   | retained_after_exclusion   | post_exclusion_tier   | is_missing_layer3_target   | is_control_target   | source_primary_classification   | source_secondary_classifications   |
|:---------------|:------------------------------------|:---------------------|:-----------|:--------------------|:-----------------|:--------------------|:------------------------------------|:------------------|:---------------------------|:----------------------|:---------------------------|:--------------------|:--------------------------------|:-----------------------------------|
| mt5_0052       | post_n5_m15_slot1_replace_or_rescue | 2025-10-07 14:30:00  | BUY        | 2025-10-07 13:30:00 | cross            | ea_slot1_replace    | runtime_target_review_py_evidence   | post_n5           | False                      | nan                   | True                       | False               | python_relabel_gap              | ea_label_drift;python_relabel_gap  |
| mt5_0054       | post_n5_m15_slot1_replace_or_rescue | 2025-10-14 18:30:00  | BUY        | 2025-10-14 17:30:00 | cross            | ea_slot1_replace    | runtime_target_review_py_evidence   | post_n5           | True                       | nearby_7d_all         | True                       | False               | python_relabel_gap              | ea_label_drift;python_relabel_gap  |
| mt5_0068       | post_n2_m15_slot1_replace_or_rescue | 2026-02-02 16:30:00  | SELL       | 2026-02-02 15:30:00 | pre_cross        | ea_slot1_replace    | runtime_assignment_dynamic_original | post_n2           | True                       | nearby_180_all        | False                      | True                | python_relabel_gap              | ea_label_drift;python_relabel_gap  |
| mt5_0069       | post_n5_m15_slot1_replace_or_rescue | 2026-02-02 18:00:00  | SELL       | 2026-02-02 17:00:00 | cross            | ea_slot1_replace    | runtime_assignment_dynamic_original | post_n5           | True                       | nearby_180_all        | False                      | True                | python_relabel_gap              | ea_label_drift;python_relabel_gap  |

## Stage Presence

| mt5_trade_id   | layer   | present   |   row_count | date                | dir   | mode      | variant          | entry_time          |      pnl |   total_$ |   dynamic_total_$ |      Bias_5 |   Bias_5_ea |   layer3_threshold_ea |   layer3_pass_ea |   spec_pass | spec_reason   |
|:---------------|:--------|:----------|------------:|:--------------------|:------|:----------|:-----------------|:--------------------|---------:|----------:|------------------:|------------:|------------:|----------------------:|-----------------:|------------:|:--------------|
| mt5_0052       | raw     | True      |           1 | 2025-10-07 13:30:00 | L     | cross     | m30_base         | 2025-10-07 13:30:00 |  57.244  |           |                   |   0.014518  |             |                       |                  |           1 | ok            |
| mt5_0052       | layer12 | True      |           1 | 2025-10-07 13:30:00 | L     | cross     | ea_slot1_replace | 2025-10-07 13:30:00 |  57.244  |           |                   |   0.014518  |             |                       |                  |           1 | ok            |
| mt5_0052       | layer3  | False     |           0 | nan                 | nan   | nan       | nan              | nan                 | nan      |  nan      |           nan     | nan         |  nan        |            nan        |              nan |         nan | nan           |
| mt5_0052       | stage   | False     |           0 | nan                 | nan   | nan       | nan              | nan                 | nan      |  nan      |           nan     | nan         |  nan        |            nan        |              nan |         nan | nan           |
| mt5_0052       | dynamic | False     |           0 | nan                 | nan   | nan       | nan              | nan                 | nan      |  nan      |           nan     | nan         |  nan        |            nan        |              nan |         nan | nan           |
| mt5_0054       | raw     | True      |           1 | 2025-10-14 17:30:00 | L     | cross     | m30_base         | 2025-10-14 17:30:00 | 149.634  |           |                   |   0.0276321 |             |                       |                  |           1 | ok            |
| mt5_0054       | layer12 | True      |           1 | 2025-10-14 17:30:00 | L     | cross     | ea_slot1_replace | 2025-10-14 17:15:00 | 149.207  |           |                   |   0.0276321 |             |                       |                  |           1 | ok            |
| mt5_0054       | layer3  | False     |           0 | nan                 | nan   | nan       | nan              | nan                 | nan      |  nan      |           nan     | nan         |  nan        |            nan        |              nan |         nan | nan           |
| mt5_0054       | stage   | False     |           0 | nan                 | nan   | nan       | nan              | nan                 | nan      |  nan      |           nan     | nan         |  nan        |            nan        |              nan |         nan | nan           |
| mt5_0054       | dynamic | False     |           0 | nan                 | nan   | nan       | nan              | nan                 | nan      |  nan      |           nan     | nan         |  nan        |            nan        |              nan |         nan | nan           |
| mt5_0068       | raw     | True      |           1 | 2026-02-02 15:30:00 | S     | pre_cross | m30_base         | 2026-02-02 15:30:00 | -17.8149 |           |                   |   0.241863  |             |                       |                  |           1 | ok            |
| mt5_0068       | layer12 | True      |           1 | 2026-02-02 15:30:00 | S     | pre_cross | ea_slot1_replace | 2026-02-02 15:30:00 | -17.8149 |           |                   |   0.241863  |             |                       |                  |           1 | ok            |
| mt5_0068       | layer3  | True      |           1 | 2026-02-02 15:30:00 | S     | pre_cross | ea_slot1_replace | 2026-02-02 15:30:00 | -17.8149 |           |                   |   0.241863  |    0.818697 |              0.469037 |                1 |           1 | ok            |
| mt5_0068       | stage   | True      |           1 | 2026-02-02 15:30:00 | S     | pre_cross |                  |                     |          |  -10.689  |                   |             |             |                       |                  |             |               |
| mt5_0068       | dynamic | True      |           1 | 2026-02-02 15:30:00 | S     | pre_cross | ea_slot1_replace |                     |          |           |          -106.89  |             |             |                       |                  |             |               |
| mt5_0069       | raw     | True      |           1 | 2026-02-02 17:00:00 | S     | cross     | m30_base         | 2026-02-02 17:00:00 | -23.8673 |           |                   |   0.818697  |             |                       |                  |           1 | ok            |
| mt5_0069       | layer12 | True      |           1 | 2026-02-02 17:00:00 | S     | cross     | ea_slot1_replace | 2026-02-02 17:00:00 | -23.8673 |           |                   |   0.818697  |             |                       |                  |           1 | ok            |
| mt5_0069       | layer3  | True      |           1 | 2026-02-02 17:00:00 | S     | cross     | ea_slot1_replace | 2026-02-02 17:00:00 | -23.8673 |           |                   |   0.818697  |    0.818697 |              0.469037 |                1 |           1 | ok            |
| mt5_0069       | stage   | True      |           1 | 2026-02-02 17:00:00 | S     | cross     |                  |                     |          |  -22.5045 |                   |             |             |                       |                  |             |               |
| mt5_0069       | dynamic | True      |           1 | 2026-02-02 17:00:00 | S     | cross     | ea_slot1_replace |                     |          |           |          -112.523 |             |             |                       |                  |             |               |

## Admission Review

| mt5_trade_id   | candidate_time      | candidate_mode   | ea_runtime_mode   | layer12_present   |   Bias_5_ea |   layer3_threshold_ea |   layer3_bias_gap | layer3_pass_ea   |   maxpos_active_count_before | maxpos_pass   | layer3_after_maxpos   | admission_failure_reason        | low_blast_admission_rule_supported   |
|:---------------|:--------------------|:-----------------|:------------------|:------------------|------------:|----------------------:|------------------:|:-----------------|-----------------------------:|:--------------|:----------------------|:--------------------------------|:-------------------------------------|
| mt5_0052       | 2025-10-07 13:30:00 | cross            | post_n5           | True              |   0.227808  |              0.296599 |        -0.0687907 | False            |                              | False         | False                 | layer3_threshold_fail           | False                                |
| mt5_0054       | 2025-10-14 17:30:00 | cross            | post_n5           | True              |   0.0276321 |              0.344232 |        -0.3166    | False            |                              | False         | False                 | layer3_threshold_fail           | False                                |
| mt5_0068       | 2026-02-02 15:30:00 | pre_cross        | post_n2           | True              |   0.818697  |              0.469037 |         0.34966   | True             |                            0 | True          | True                  | admitted_to_layer3_dynamic_path | True                                 |
| mt5_0069       | 2026-02-02 17:00:00 | cross            | post_n5           | True              |   0.818697  |              0.469037 |         0.34966   | True             |                            1 | True          | True                  | admitted_to_layer3_dynamic_path | True                                 |

## Admission Summary

| admission_failure_reason        |   count | mt5_ids           |   missing_layer3_targets |   control_targets |   avg_layer3_bias_gap |
|:--------------------------------|--------:|:------------------|-------------------------:|------------------:|----------------------:|
| admitted_to_layer3_dynamic_path |       2 | mt5_0068;mt5_0069 |                        0 |                 2 |              0.34966  |
| layer3_threshold_fail           |       2 | mt5_0052;mt5_0054 |                        2 |                 0 |             -0.192695 |

## Interpretation

- `mt5_0052` and `mt5_0054` are present in raw and Layer1/2, but fail the EA-style Layer3 H2 top_pct threshold before max-position is relevant.
- `mt5_0068` and `mt5_0069` have control rows that pass Layer3 and survive max-position, which explains why they reach Stage/dynamic.
- Letting `mt5_0052/0054` in would require bypassing the global Layer3 threshold, not a narrow max-position or displacement correction.
- No main signal, EA behavior, mapping, dynamic-risk, or merge gate is opened here.

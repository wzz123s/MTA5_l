# MT5独有 M15 SLOT1 all-low 复核

## 汇总

|   总样本数 |   当前too_tight/too_wide样本数 |   all_low可救回样本数 |   完全无候选样本数 |
|-----------:|-------------------------------:|----------------------:|-------------------:|
|          7 |                              7 |                     0 |                  0 |

## 逐笔结果

| anchor_time         | dir   | mode_raw                              |   mt5_stop_dist | candidate_source   | candidate_time      |   candidate_sd |   candidate_spec_pass | candidate_spec_reason   |   slot1_low_sd |   slot1_low_pass |   slot1_low_error |   current_error | all_low_can_rescue   | result_note    |
|:--------------------|:------|:--------------------------------------|----------------:|:-------------------|:--------------------|---------------:|----------------------:|:------------------------|---------------:|-----------------:|------------------:|----------------:|:---------------------|:---------------|
| 2023-03-15 20:30:00 | S     | pre_cross_m15_slot1_replace_or_rescue |             7.7 | exact              | 2023-03-15 20:30:00 |       1.94886  |                     0 | too_tight               |       1.14586  |                0 |           6.55414 |         5.75114 | False                | 仍不通过       |
| 2023-03-20 12:30:00 | S     | pre_cross_m15_slot1_replace_or_rescue |             6.5 | exact              | 2023-03-20 12:30:00 |       1.95532  |                     0 | too_tight               |       0.130678 |                0 |           6.36932 |         4.54468 | False                | 仍不通过       |
| 2024-03-07 16:30:00 | S     | pre_cross_m15_slot1_replace_or_rescue |             6.1 | exact              | 2024-03-07 16:30:00 |       0.695832 |                     0 | too_tight               |       0.511832 |                0 |           5.58817 |         5.40417 | False                | 仍不通过       |
| 2025-04-14 00:00:00 | S     | pre_cross_m15_slot1_replace_or_rescue |             5.3 | nearest_after      | 2025-04-14 00:30:00 |       5.17256  |                   nan | ok                      |     nan        |              nan |         nan       |       nan       | False                | 缺少 slot1 K线 |
| 2026-02-03 01:00:00 | L     | pre_cross_m15_slot1_replace_or_rescue |            34.8 | nearest_after      | 2026-02-03 01:30:00 |      91.7544   |                   nan | too_wide                |     nan        |              nan |         nan       |       nan       | False                | 缺少 slot1 K线 |
| 2026-02-24 03:00:00 | S     | pre_cross_m15_slot1_replace_or_rescue |            17.4 | exact              | 2026-02-24 03:00:00 |      36.6428   |                     0 | too_wide                |      19.3202   |                0 |           1.92018 |        19.2428  | False                | 仍不通过       |
| 2026-06-11 07:30:00 | L     | pre_cross_m15_slot1_replace_or_rescue |             7.9 | exact              | 2026-06-11 07:30:00 |       1.82315  |                     0 | too_tight               |      20.0139   |                0 |          12.1138  |         6.07685 | False                | 仍不通过       |

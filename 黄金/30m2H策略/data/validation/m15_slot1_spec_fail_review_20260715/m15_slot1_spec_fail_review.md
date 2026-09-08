# M15 SLOT1 SPEC_FAIL review - 2025-10-21

## 结论

- Python-MT5 当前接受的是 `date=2025-10-21 10:00:00`、`entry_time=2025-10-21 09:45:00`、`sd=32.32603` 的 `ea_slot1_runtime_rescue`。
- EA full-history diag 对应 raw anchor `2025-10-21 08:30:00` 的 M15 slot1 使用 `completed_m15_open=2025.10.21 08:00`，`m15_close=4244.872`，`stop_pts_spec=84.189`，结果 `SPEC_FAIL_PROXY`。
- 在当前 Python shifted M15 数据中，EA 对应的 completed bar 是 `date=2025-10-21 10:00:00`；当前 Python `choose_slot1_by_distance()` 取的是窗口内第一根 `09:45`，不是 EA 对应的 latest completed bar `10:00`。
- 因此该 SPEC_FAIL 的主要原因是 Python-MT5 M15 SLOT1 选 bar 语义与 EA 不一致；不应改 EA spec gate。
- 后续应先做版本化 prototype：把 `ea_slot1_replace` 和 `ea_slot1_runtime_rescue` 的 slot1 chooser 从 `seg.iloc[0]` 改为 EA-equivalent latest completed bar，再重跑 dynamic risk / mapping / remaining diff。

## Python signal chain

| layer            | date                | entry_time          | mode      | dir   | variant                 | trigger   |   entry |    stop |        sd |   spec_pass | spec_reason   | layer3_eval_time    |   layer3_pass_ea |   total_$ |
|:-----------------|:--------------------|:--------------------|:----------|:------|:------------------------|:----------|--------:|--------:|----------:|------------:|:--------------|:--------------------|-----------------:|----------:|
| raw_candidates   | 2025-10-21 06:00:00 | 2025-10-21 06:00:00 | pre_cross | S     | m30_base                | nan       | 4342.89 | 4344.09 |   1.19577 |           0 | too_tight     | nan                 |              nan |   nan     |
| raw_candidates   | 2025-10-21 08:30:00 | 2025-10-21 08:30:00 | pre_cross | L     | m30_base                | nan       | 4343.2  | 4340.16 |   3.04203 |           0 | too_tight     | nan                 |              nan |   nan     |
| raw_candidates   | 2025-10-21 07:30:00 | 2025-10-21 07:30:00 | cross     | S     | m30_base                | nan       | 4324.57 | 4344.09 |  19.5218  |           1 | ok            | nan                 |              nan |   nan     |
| raw_candidates   | 2025-10-21 08:00:00 | 2025-10-21 08:00:00 | post_n2   | S     | m30_base                | nan       | 4324.11 | 4340.16 |  16.055   |           1 | ok            | nan                 |              nan |   nan     |
| raw_candidates   | 2025-10-21 09:00:00 | 2025-10-21 09:00:00 | post_n4   | S     | m30_base                | nan       | 4324.91 | 4339.2  |  14.2901  |           1 | ok            | nan                 |              nan |   nan     |
| raw_candidates   | 2025-10-21 09:30:00 | 2025-10-21 09:30:00 | post_n5   | S     | m30_base                | nan       | 4298.45 | 4336.07 |  37.6201  |           0 | too_wide      | nan                 |              nan |   nan     |
| raw_candidates   | 2025-10-21 10:00:00 | 2025-10-21 10:00:00 | post_n6   | S     | m30_base                | nan       | 4267.25 | 4330.78 |  63.529   |           0 | too_wide      | nan                 |              nan |   nan     |
| layer12_accepted | 2025-10-21 07:30:00 | 2025-10-21 07:15:00 | cross     | S     | ea_slot1_replace        | nan       | 4333.13 | 4344.09 |  10.9558  |           1 | ok            | nan                 |              nan |   nan     |
| layer12_accepted | 2025-10-21 08:00:00 | 2025-10-21 07:45:00 | post_n2   | S     | ea_slot1_replace        | nan       | 4323.31 | 4340.16 |  16.846   |           1 | ok            | nan                 |              nan |   nan     |
| layer12_accepted | 2025-10-21 09:00:00 | 2025-10-21 09:00:00 | post_n4   | S     | ea_slot1_replace        | nan       | 4324.91 | 4339.2  |  14.2901  |           1 | ok            | nan                 |              nan |   nan     |
| layer12_accepted | 2025-10-21 09:30:00 | 2025-10-21 09:15:00 | post_n5   | S     | ea_slot1_runtime_rescue | nan       | 4324.91 | 4336.07 |  11.1551  |           1 | ok            | nan                 |              nan |   nan     |
| layer12_accepted | 2025-10-21 10:00:00 | 2025-10-21 09:45:00 | post_n6   | S     | ea_slot1_runtime_rescue | nan       | 4298.45 | 4330.78 |  32.326   |           1 | ok            | nan                 |              nan |   nan     |
| layer3_picked    | 2025-10-21 10:00:00 | 2025-10-21 09:45:00 | post_n6   | S     | ea_slot1_runtime_rescue | M15 SLOT1 | 4298.45 | 4330.78 |  32.326   |           1 | ok            | 2025-10-21 10:00:00 |                1 |   nan     |
| stage_results    | 2025-10-21 10:00:00 | nan                 | post_n6   | S     | nan                     | nan       |  nan    |  nan    | nan       |         nan | nan           | nan                 |              nan |    77.991 |
| dynamic_inputs   | 2025-10-21 10:00:00 | 2025-10-21 09:45:00 | post_n6   | S     | ea_slot1_runtime_rescue | M15 SLOT1 | 4298.45 | 4330.78 |  32.326   |           1 | ok            | 2025-10-21 10:00:00 |                1 |    77.991 |

## EA target diagnostic row

| diag_time           | completed_m15_open   | anchor_time      | signal_src        |   m15_close |   m15_sma13 |   stop_price |   stop_pts_spec | result    | detail          |
|:--------------------|:---------------------|:-----------------|:------------------|------------:|------------:|-------------:|----------------:|:----------|:----------------|
| 2025-10-21 08:15:00 | 2025.10.21 08:00     | 2025.10.21 08:30 | post_n5_m15_slot1 |     4244.87 |     4326.14 |      4329.06 |          84.189 | SPEC_FAIL | SPEC_FAIL_PROXY |

## Slot candidate comparison

| source                         | axis_time           | raw_time_inferred   |   entry_close |   stop_used |   sd_to_python_stop | spec_reason_to_python_stop   |   sma13 |   ea_stop_pts_spec | ea_result   | ea_detail       |
|:-------------------------------|:--------------------|:--------------------|--------------:|------------:|--------------------:|:-----------------------------|--------:|-------------------:|:------------|:----------------|
| python_current_selected_first  | 2025-10-21 09:45:00 | 2025-10-21 07:45:00 |       4298.45 |     4330.78 |              32.326 | ok                           | 4332.87 |            nan     | nan         | nan             |
| ea_equivalent_latest_completed | 2025-10-21 10:00:00 | 2025-10-21 08:00:00 |       4244.87 |     4330.78 |              85.903 | too_wide                     | 4326.1  |            nan     | nan         | nan             |
| raw_m15_reference              |                     | 2025-10-21 07:45:00 |       4298.45 |     4330.78 |              32.326 | ok                           |         |            nan     | nan         | nan             |
| raw_m15_reference              |                     | 2025-10-21 08:00:00 |       4244.87 |     4330.78 |              85.903 | too_wide                     |         |            nan     | nan         | nan             |
| ea_diag_actual                 |                     | 2025.10.21 08:00    |       4244.87 |     4329.06 |                     |                              | 4326.14 |             84.189 | SPEC_FAIL   | SPEC_FAIL_PROXY |

## Code evidence

| file                             | line                  | evidence                                                                                          |
|:---------------------------------|:----------------------|:--------------------------------------------------------------------------------------------------|
| scripts/_m15_early_entry_test.py | 256-259               | m15_window returns rows in (anchor_time-30m, anchor_time] sorted ascending.                       |
| scripts/_m15_early_entry_test.py | 304-314               | choose_slot1_by_distance uses seg.iloc[0], the earliest row in that 30-minute window.             |
| auto_trade/30m2H_Strategy_EA.mq5 | 2655, 2699-2711, 2731 | EA uses iTime(M15,1), maps it to slot_in_m30, and sets anchor_time=slot_m30_open+M30.             |
| auto_trade/30m2H_Strategy_EA.mq5 | 2742-2763, 2935-2975  | EA stop/spec uses completed M15 close and M30 ctx SMA13, then blocks outside InpStopLo/InpStopHi. |

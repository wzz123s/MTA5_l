# Stage2 Remaining Tick/Trail Ledger Evidence

## Scope

- Input review: `python_runtime_stage_exit_prototype_20260714\runtime_stage2_partial_open_ticklog_review.csv`
- Enhanced full ledger: `ea_stage2_trail_ledger_full_20260714\30m2H_strategy_trade_ledger.csv`
- Pending cases reviewed: `8`

## Summary

| evidence_class                                 | remaining_alignment_blocker | needs_raw_tick_for_first_touch_order | rows |
| ---------------------------------------------- | --------------------------- | ------------------------------------ | ---- |
| resolved_as_trail_sl_by_ea_ledger              | False                       | False                                | 2    |
| confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 | 6    |

## Case Evidence

| case_id                | signal_anchor_time | stage2_sl_kind | ledger_exit_time    | stage2_trail_modify_count | stage2_last_modify_to_sl | ledger_deal_sl_price | evidence_class                                 | remaining_alignment_blocker | needs_raw_tick_for_first_touch_order |
| ---------------------- | ------------------ | -------------- | ------------------- | ------------------------- | ------------------------ | -------------------- | ---------------------------------------------- | --------------------------- | ------------------------------------ |
| runtime_stage_case_001 | 2020.03.17 16:00   | initial_sl     | 2020.03.18 07:43:02 | 0                         |                          | 1498.22900           | confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 |
| runtime_stage_case_005 | 2021.03.04 19:00   | initial_sl     | 2021.03.07 23:18:16 | 0                         |                          | 1711.54700           | confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 |
| runtime_stage_case_008 | 2022.03.08 01:30   | initial_sl     | 2022.03.08 04:59:12 | 0                         |                          | 1990.97100           | confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 |
| runtime_stage_case_010 | 2023.03.15 13:00   | trail_sl       | 2023.03.20 10:00:36 | 553                       | 1983.42200               | 1983.42200           | resolved_as_trail_sl_by_ea_ledger              | False                       | False                                |
| runtime_stage_case_012 | 2023.03.20 11:00   | initial_sl     | 2023.03.20 11:04:37 | 0                         |                          | 1982.83500           | confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 |
| runtime_stage_case_016 | 2025.04.22 09:00   | initial_sl     | 2025.04.22 09:16:39 | 0                         |                          | 3458.18300           | confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 |
| runtime_stage_case_019 | 2025.10.16 06:00   | initial_sl     | 2025.10.16 06:05:38 | 0                         |                          | 4217.98000           | confirmed_initial_sl_after_open_by_deal_ledger | False                       | True                                 |
| runtime_stage_case_023 | 2026.02.02 18:00   | trail_sl       | 2026.02.02 19:41:37 | 32                        | 4684.45400               | 4684.45400           | resolved_as_trail_sl_by_ea_ledger              | False                       | False                                |

## Interpretation

- `remaining_alignment_blocker = False` means the case no longer blocks current Stage2 exit/PnL classification alignment.
- `needs_raw_tick_for_first_touch_order = True` is retained for strict intra-bar tick replay, not for current ledger-level classification.
- `case_019` is resolved by the new Stage2 trail ledger because it records trail activation and repeated successful SL modify attempts.
- The initial-SL cases are resolved for ledger-level classification because broker deal history confirms the SL close after open; raw ticks would only refine the first-touch sequence inside the bar.

## Output Files

- `runtime_stage2_remaining_ticklog_evidence.csv`
- `runtime_stage2_remaining_ticklog_evidence_summary.csv`

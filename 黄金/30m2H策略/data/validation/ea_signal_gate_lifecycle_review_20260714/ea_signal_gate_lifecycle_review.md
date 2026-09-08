# EA Signal Gate Lifecycle Review 20260714

## Summary

| stable_case                          | python_target_time   | mt5_raw_anchor_time   | m15_slot1_eval_time   | mode      |   filtered_trade_profit | signals_export_decision_at_raw_anchor   | signals_export_skip_reason_at_raw_anchor   |   active_stage_rows_at_m15_eval | ledger_proxy_supports_max_pos_gate   | classification                                 |
|:-------------------------------------|:---------------------|:----------------------|:----------------------|:----------|------------------------:|:----------------------------------------|:-------------------------------------------|--------------------------------:|:-------------------------------------|:-----------------------------------------------|
| far_runtime_rescue_20251021_postn6   | 2025-10-21 10:00:00  | 2025-10-21 08:30:00   | 2025-10-21 08:15:00   | post_n6   |                 201.851 | SKIP                                    | no_cross_m30_or_h2                         |                               2 | False                                | m15_candidate_absent_or_silent_gate_unresolved |
| far_runtime_rescue_20251017_precross | 2025-10-17 11:00:00  | 2025-10-17 09:30:00   | 2025-10-17 09:15:00   | pre_cross |                 189.621 | SKIP                                    | no_cross_m30_or_h2                         |                               2 | False                                | m15_candidate_absent_or_silent_gate_unresolved |

## Code Evidence

| evidence                      | lines     | meaning                                                                                               |
|:------------------------------|:----------|:------------------------------------------------------------------------------------------------------|
| InpMaxPos                     | 39        | EA input max concurrent stage positions is 3 in current source.                                       |
| OurStageCount                 | 1386-1396 | Counts real open stage positions with magic InpMagic+1..InpMagic+3.                                   |
| HasPosDir                     | 1788      | Checks only InpMagic base positions and is not the M15/M30 signal gate used here.                     |
| M15 max-pos gate              | 2521      | TryM15EarlyEntry returns SKIP_MAX_POS only when OurStageCount() >= InpMaxPos.                         |
| M15 same-anchor silent return | 2550      | A repeated anchor returns false without CSV evidence.                                                 |
| M15 no-signal silent return   | 2636      | If M15 pre/cross/post_n mode is absent, the function returns false before Candidate diag.             |
| M15 Candidate diag            | 2637      | Candidate diagnostics start only after signal_dir is non-zero.                                        |
| M30 signals_export            | 2814-2825 | Per-bar CSV records coarse M30 decision and max_pos only, not all M15 early-entry silent returns.     |
| M30 max-pos gate              | 3001      | M30 close also skips when OurStageCount() >= InpMaxPos, after M15 early-entry has already been tried. |
| DiagLog target                | 813       | Verbose gate diagnostics are printed to tester/journal, not exported to the current CSV set.          |

## Active Positions At Probe Times

| stable_case                          | probe_kind     | probe_time          | signal_anchor_time   |   stage | dir   | trigger_tag   | signal_src                          | open_time           | exit_time           |   net_profit |
|:-------------------------------------|:---------------|:--------------------|:---------------------|--------:|:------|:--------------|:------------------------------------|:--------------------|:--------------------|-------------:|
| far_runtime_rescue_20251021_postn6   | raw_anchor     | 2025-10-21 08:30:00 | 2025.10.14 18:30     |       3 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2025.10.14 18:15:00 | 2025.10.21 14:29:38 |       -17.7  |
| far_runtime_rescue_20251021_postn6   | raw_anchor     | 2025-10-21 08:30:00 | 2022.11.08 16:30     |       1 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 |      1802.36 |
| far_runtime_rescue_20251021_postn6   | m15_slot1_eval | 2025-10-21 08:15:00 | 2025.10.14 18:30     |       3 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2025.10.14 18:15:00 | 2025.10.21 14:29:38 |       -17.7  |
| far_runtime_rescue_20251021_postn6   | m15_slot1_eval | 2025-10-21 08:15:00 | 2022.11.08 16:30     |       1 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 |      1802.36 |
| far_runtime_rescue_20251017_precross | raw_anchor     | 2025-10-17 09:30:00 | 2025.10.14 18:30     |       3 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2025.10.14 18:15:00 | 2025.10.21 14:29:38 |       -17.7  |
| far_runtime_rescue_20251017_precross | raw_anchor     | 2025-10-17 09:30:00 | 2022.11.08 16:30     |       1 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 |      1802.36 |
| far_runtime_rescue_20251017_precross | m15_slot1_eval | 2025-10-17 09:15:00 | 2025.10.14 18:30     |       3 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2025.10.14 18:15:00 | 2025.10.21 14:29:38 |       -17.7  |
| far_runtime_rescue_20251017_precross | m15_slot1_eval | 2025-10-17 09:15:00 | 2022.11.08 16:30     |       1 | BUY   | [M15 SLOT1]   | post_n5_m15_slot1_replace_or_rescue | 2022.11.08 16:15:06 | 2026.07.06 23:59:59 |      1802.36 |

## Decision

- Current evidence weakens the previous pure position-occupancy explanation: both target M15 evaluation times have 2 active stage rows, below InpMaxPos=3.
- The M30 signals_export rows at the raw anchors are SKIP/no_cross_m30_or_h2, so they only prove no successful signal was registered for that anchor; they do not explain the M15 early-entry path.
- Because TryM15EarlyEntry has silent returns before Candidate diagnostics, current exports cannot distinguish absent M15 mode from same-anchor, slot, Layer, stop/spec, or quote gates.
- Next repair step should add a non-trading M15 early-entry diagnostic export around every new_m15_bar before changing trading behavior.

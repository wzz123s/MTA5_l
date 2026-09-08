# Python Runtime Stage Exit Prototype 20260714

## Scope

- Input source: `stage_exit_rule_alignment_shift90_close_retry_20260714`.
- Case file: `runtime_stage_input_cases.csv`.
- First replay: M30 OHLC approximation, not tick-equivalent.
- Refine replay: M15 OHLC approximation for cases that remained order-uncertain.
- Stage2 trail refine: M30 SMA13 trail SL approximation, not tick-equivalent.
- Stage2 partial-open review: available ledger/M15/diag evidence, not exported tick replay.
- Integrated alignment: M30/M15/Stage2 trail/enhanced ledger evidence merged into runtime residual status.
- Remaining blocker journal review: tester journal evidence for current integrated Priority 1 blockers.

## Outputs

- `runtime_stage_input_cases.csv`
- `runtime_stage_input_case_summary.csv`
- `runtime_stage_input_cases_report.md`
- `runtime_stage_priority1_replay.csv`
- `runtime_stage_priority1_summary.csv`
- `runtime_stage_priority1_overall_summary.csv`
- `runtime_stage_priority1_report.md`
- `runtime_stage_priority1_m15_refine.csv`
- `runtime_stage_priority1_m15_refine_summary.csv`
- `runtime_stage_priority1_m15_refine_by_stage.csv`
- `runtime_stage_priority1_m15_refine_report.md`
- `runtime_stage2_trail_refine.csv`
- `runtime_stage2_trail_refine_summary.csv`
- `runtime_stage2_trail_refine_by_relation.csv`
- `runtime_stage2_trail_refine_report.md`
- `runtime_stage2_partial_open_ticklog_review.csv`
- `runtime_stage2_partial_open_ticklog_summary.csv`
- `runtime_stage2_partial_open_ticklog_sl_summary.csv`
- `runtime_stage2_partial_open_ticklog_review.md`
- `runtime_stage2_remaining_ticklog_evidence.csv`
- `runtime_stage2_remaining_ticklog_evidence_summary.csv`
- `runtime_stage2_remaining_ticklog_evidence.md`
- `runtime_stage_exit_integrated_alignment.csv`
- `runtime_stage_exit_integrated_stage_summary.csv`
- `runtime_stage_exit_integrated_trade_summary.csv`
- `runtime_stage_exit_integrated_alignment.md`
- `runtime_stage_exit_remaining_blockers.csv`
- `runtime_stage_exit_remaining_blockers_summary.csv`
- `runtime_stage_exit_remaining_blockers_journal_snippets.txt`
- `runtime_stage_exit_remaining_blockers.md`

## Current Result

- Stage cases: `87`.
- Priority 1 cases: `25`.
- M30 replay:
  - Priority 1 rows: `25`.
  - M30 broker-SL first or same-bar broker-SL explains MT5 SL for most SL cases.
- M15 refine:
  - refined cases: `21`.
  - no M15 coverage: `7`.
  - still tick/log-needed rows remain for strict first-touch audit.
- Stage2 trail refine:
  - Stage2 cases: `12`.
  - initial SL before force: `11`.
  - trail SL touch before/at MT5 SL bar: `1`.
  - force before MT5 SL: `0`.
  - most unresolved Stage2 rows are still opening-bar/tick-order questions before enhanced ledger evidence.
- Stage2 partial-open review:
  - reviewed partial-open cases: `10`.
  - resolved without new tick/log export: `2`.
  - remaining rows were passed to enhanced ledger evidence review.
- Stage2 remaining evidence:
  - remaining Stage2 partial-open blockers: `0`.
  - `2` rows resolved as `trail_sl` by enhanced EA ledger.
  - `6` rows confirmed as broker initial SL after open by deal ledger.
- Integrated alignment:
  - stage exit detail trades before runtime integration: `29`.
  - Priority 1 stage rows before runtime integration: `25`.
  - remaining Priority 1 blockers after integration: `3`.
  - Priority 1 rows still requiring strict tick/journal replay: `16`.
  - trade status: `priority1_resolved=4`, `priority1_explained_but_strict_replay_pending=6`, `has_priority1_blocker=3`, `no_priority1_stage=16`.
- Remaining blocker journal review:
  - `2` rows resolved by tester journal.
  - current Priority 1 blockers after journal review: `1`.
  - remaining blocker: `python_mt5_0061 / mt5_0045`, BUY Stage3, Python cross profit vs MT5 broker SL.

## Decision

- Do not change EA price-side behavior from this evidence.
- Python runtime-style dynamic risk / funds curve diagnostic has been refreshed in `../runtime_style_dynamic_risk_alignment_20260714`.
- Continue with `python_mt5_0061 / mt5_0045` blocker and `mt5_0068` layer3 reject review.

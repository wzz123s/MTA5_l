# EA Gate Precheck Report

## Scope
- Target rule family: `M15 SLOT1 / post_n` raw-parent gate.
- Source evidence:
  - `m15_raw_parent_gate_policy_summary.csv`
  - `m15_raw_parent_gate_policy_details.csv`
  - `auto_trade/30m2H_Strategy_EA.mq5`

## Prototype Result
- `strict_parent` is not safe for direct EA migration.
  - In the Python-MT5 view, every tested window `0/30/60/90/120/180min` rejects `3` reliable matched MT5 `M15 SLOT1 / post_n` trades.
- `conservative_cause` is safe in the offline prototype.
  - `reliable_matched_rejected = 0`
  - `relaxed_matched_rejected = 0`
  - Python-MT5 rejects `3~4` unmatched rows.
  - Python-only rejects `5~7` unmatched rows.

## EA-Expressible Conditions
- The EA can identify current M15 slot context:
  - `is_slot1`
  - `is_slot2`
  - `slot_m30_open`
  - `anchor_time`
- The EA can identify current signal family before execution:
  - `signal_src`
  - `post_nN_m15_slot1`
  - `trigger_tag = [M15 SLOT1]`
  - `g_merged_post_n_counter`
- The EA can apply local gates:
  - `PassLayer1Gate()`
  - `PassLayer3Gate()`
  - stop validity
  - spec range
  - max-position gate
- The EA can log additional local diagnostics before `ExecuteSignalByMarket()`.

## Offline-Only Conditions
- The EA cannot know whether a signal is `reliable_matched` or `relaxed_matched`; that is produced by offline Python/MT5 mapping.
- The EA cannot know `cause_bucket` values such as:
  - `mapping_conflict_or_profit_diff`
  - `stage_execution_diff_or_family_drift`
  - `layer3_reject`
  - `trigger_family_drift`
  - `missing_raw_parent`
- The EA cannot know Python-side accepted/picked/executed nearest-neighbor status without adding new persistent diagnostic state.
- The EA cannot directly protect `mapping_conflict_or_profit_diff` or `layer3_reject` samples, because those labels are computed after comparing Python and MT5 outputs.

## Decision
- Do not implement `strict_parent` in EA.
- Do not directly implement `conservative_cause` in EA, because its protection conditions are offline-only.
- The safe next EA step, if any, is diagnostic-only:
  - Add logging for M15 SLOT1 post_n parent context.
  - Do not block trades yet.
  - Re-run smoke/full tester and rebuild the same mapped reports.

## Recommended Next Step
- Continue with `M30 CLOSE / post_n` alignment before changing EA behavior.
- If EA M15 gate is still needed later, first add diagnostic fields:
  - parent M30 candidate time
  - parent M30 mode family
  - parent time distance
  - merged post_n counter
  - strict merged post_n counter
  - Layer1/Layer3 pass values
  - Stop/spec pass values


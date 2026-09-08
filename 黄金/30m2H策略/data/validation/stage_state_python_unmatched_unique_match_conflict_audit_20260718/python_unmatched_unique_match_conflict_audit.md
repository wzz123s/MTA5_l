# Stage-state Python-unmatched unique-match conflict audit

## Decision

- Reviewed unique-conflict rows: `32`
- P1 rows: `5`
- P1 abs gap sum: `1448.52909`
- Behavior evidence rows: `0`
- Unique-match behavior blocker closed: `True`
- Recommended next task: `Stage-state independent MT5 signal gap audit`
- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.

## P1 Shape

- Far candidate accounting-only rows: `2`
- Duplicate continuation diagnostic-only rows: `1`
- Relaxed mapping-policy rows: `2`

## Top P1 Cases

- `python_mt5_0079` `2025-10-21 10:00:00` `python_unmatched` `M15 SLOT1/post_n`: abs gap `389.95518`, class `far_candidate_accounting_only`, best candidate `mt5_0057` tier `nearby_7d_all`, interpretation `candidate is outside reliable behavior window; keep as accounting/window evidence`
- `python_mt5_0073` `2025-10-17 11:00:00` `python_unmatched` `M15 SLOT1/pre_cross`: abs gap `379.2422`, class `far_candidate_accounting_only`, best candidate `mt5_0056` tier `nearby_7d_all`, interpretation `candidate is outside reliable behavior window; keep as accounting/window evidence`
- `python_mt5_0075` `2025-10-17 15:00:00` `python_unmatched` `M15 SLOT1/post_n`: abs gap `301.8339`, class `duplicate_continuation_diagnostic_only`, best candidate `mt5_0057` tier `nearby_60_all`, interpretation `nearby duplicate continuation was already tested by filtered dynamic/mapping rerun; merge gate stayed closed`
- `python_mt5_0065` `2025-04-22 16:30:00` `python_unmatched` `M15 SLOT1/post_n`: abs gap `191.76934`, class `relaxed_mapping_policy_review`, best candidate `mt5_0048` tier `nearby_60_trigger_relaxed`, interpretation `conflict depends on relaxed trigger/mode policy; not stage-exit or EA price-side evidence`
- `python_mt5_0062` `2025-04-21 02:30:00` `python_unmatched` `M15 SLOT1/post_n`: abs gap `185.72847`, class `relaxed_mapping_policy_review`, best candidate `mt5_0046` tier `nearby_60_trigger_relaxed`, interpretation `conflict depends on relaxed trigger/mode policy; not stage-exit or EA price-side evidence`

## Prior Prototype Status

- Duplicate full-chain improved gap: `True`
- Duplicate full-chain merge gate pass: `False`
- Targeted signal downstream decision: `run_selected_layer3_prototype_next`

## Bucket Summary

- P1 `True` `python_unmatched` `far_candidate_accounting_only`: rows `2`, abs `769.19738`
- P1 `True` `python_unmatched` `relaxed_mapping_policy_review`: rows `2`, abs `377.49781`
- P1 `True` `python_unmatched` `duplicate_continuation_diagnostic_only`: rows `1`, abs `301.8339`
- P1 `False` `python_unmatched` `far_candidate_accounting_only`: rows `8`, abs `461.976456`
- P1 `False` `python_unmatched` `relaxed_mapping_policy_review`: rows `8`, abs `386.56525`
- P1 `False` `mt5_unmatched` `relaxed_mapping_policy_review`: rows `2`, abs `234.83`
- P1 `False` `python_unmatched` `duplicate_continuation_diagnostic_only`: rows `7`, abs `195.39756`
- P1 `False` `mt5_unmatched` `far_candidate_accounting_only`: rows `2`, abs `73.87`

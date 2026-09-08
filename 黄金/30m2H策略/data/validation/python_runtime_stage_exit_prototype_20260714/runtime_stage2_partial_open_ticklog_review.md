# Runtime Stage2 Partial-Open Tick/Log Review

## Scope

- Input: `runtime_stage2_trail_refine.csv` rows with `needs_log_or_tick = True`.
- Evidence used: close-retry MT5 ledger/deal comment, M15 refine output, and available EA stage price smoke diagnostics.
- This is still not an exported tick replay or full tester journal parser.

## Key Counts

- Reviewed partial-open Stage2 cases: `10`.
- Resolved without new tick/log export: `2`.
- Still needs exported tick/tester log: `8`.
- Cases with matching stage-price diag rows: `3`.
- Close-retry ledger rows checked: `234`.

## Review Summary

| partial_open_review_class                           | still_needs_tick_or_log   |   rows |
|:----------------------------------------------------|:--------------------------|-------:|
| resolved_as_initial_sl_after_open_with_m15          | False                     |      1 |
| resolved_as_trail_or_modified_sl_with_diag          | False                     |      1 |
| broker_initial_sl_confirmed_but_no_tick_source      | True                      |      5 |
| modified_sl_price_needs_trail_ledger_or_tick        | True                      |      2 |
| broker_initial_sl_confirmed_but_sequence_needs_tick | True                      |      1 |

## SL Price Summary

| deal_sl_kind               | partial_open_review_class                           |   rows |
|:---------------------------|:----------------------------------------------------|-------:|
| initial_sl_price           | broker_initial_sl_confirmed_but_no_tick_source      |      5 |
| initial_sl_price           | broker_initial_sl_confirmed_but_sequence_needs_tick |      1 |
| initial_sl_price           | resolved_as_initial_sl_after_open_with_m15          |      1 |
| trail_or_modified_sl_price | modified_sl_price_needs_trail_ledger_or_tick        |      2 |
| trail_or_modified_sl_price | resolved_as_trail_or_modified_sl_with_diag          |      1 |

## Notes

- `broker_initial_sl_confirmed_*` means the MT5 deal itself confirms a broker SL after open, but current data still cannot prove the exact first-touch order inside the opening bar.
- `resolved_as_trail_or_modified_sl_*` means the deal SL price is closer to the simulated/modified SL than to the initial SL; this removes it from the initial-SL partial-open bucket.
- Remaining `still_needs_tick_or_log = True` rows require exported MT5 ticks or tester journal around the open/exit window.

## Output Files

- `runtime_stage2_partial_open_ticklog_review.csv`
- `runtime_stage2_partial_open_ticklog_summary.csv`
- `runtime_stage2_partial_open_ticklog_sl_summary.csv`

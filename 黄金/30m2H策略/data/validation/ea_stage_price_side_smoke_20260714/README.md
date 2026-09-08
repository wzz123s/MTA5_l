# EA Stage Price-Side Smoke 20260714

## Scope

- EA file: `auto_trade/30m2H_Strategy_EA.mq5`
- Smoke config: `auto_trade/30m2H_Strategy_EA.stage_price_diag_smoke_20260126.ini`
- Window: `2026.01.25` to `2026.01.28`
- Target sample: SELL signal around `2026.01.26 20:30`

## Outputs

- `20260126`: first Stage1/2 price-side diagnostic smoke.
- `20260126_close_retry_fix`: same window after ClosePos retry/state-retention fix.
- `20250422_close_retry_fix`: SELL Stage3/deinit smoke after ClosePos fix.
- `20260324_close_retry_fix`: SELL Stage1/Stage3 EXPERT smoke after ClosePos fix.

Each snapshot contains:

- `30m2H_strategy_stage_price_diag.csv`
- `30m2H_strategy_trade_ledger.csv`
- `30m2H_strategy_deal_history.csv`
- `30m2H_strategy_signals_export.csv`

## Result

- The `2026.01.26 20:30` SELL sample did not prove a false TP caused by BID/ASK price-side.
- First Stage1 TP trigger:
  - time: `2026.01.26 21:31:50`
  - `legacy_abs_rr=2.010334`
  - `close_profit_rr=2.002203`
  - `legacy_action_text=stage1_tp`
  - `profit_side_action_text=stage1_tp`
- No SELL diagnostic rows matched `legacy_abs_rr>=1.5` and `close_profit_rr<0`.

## Confirmed Bug

- When `PositionClose` failed during market closed, the old EA cleared stage state anyway.
- The failed `stage1_tp` intent remained pending, so a later real SL could be reported as `stage1_tp + SL`.
- The fix makes `ClosePos` return `bool`, clears stage state only after successful close, and clears failed pending exit intent while keeping the stage position for retry.

## Next

- Review outputs:
  - `ea_stage_price_side_smoke_review.md`
  - `ea_stage_price_side_smoke_summary.csv`
  - `ea_stage_price_side_reason_summary.csv`
  - `ea_stage_price_side_trail_on_events.csv`
  - `ea_stage_price_side_action_mismatch.csv`
- Then run a full tester regression with the ClosePos fix.

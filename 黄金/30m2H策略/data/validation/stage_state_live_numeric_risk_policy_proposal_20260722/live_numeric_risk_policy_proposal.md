# Live Numeric Risk Policy Proposal

## Decision

- status: `live_numeric_risk_policy_proposal_pending_user_confirmation`
- live_gap_006_closed: `False`
- requires_user_confirmation: `True`
- requires_ea_guard_implementation_or_external_monitor: `True`
- ready_to_live_trade: `False`

## Proposed Values

- `max_daily_loss_usd`: `120.0`
- `max_drawdown_usd`: `200.0`
- `max_open_positions`: `3`
- `max_new_positions_per_day`: `9`
- `max_spread_points`: `300`
- `margin_guard_pct`: `500`
- `min_lot`: `0.01`
- `max_lot`: `0.1`

## Implementation Reality

- Current EA supports dynamic risk sizing, max concurrent positions, min lot, max lot, and partial margin checks.
- Current EA does not expose live max daily loss, max drawdown, or max spread guards.
- Current EA margin estimate uses a hardcoded 1:500 assumption, while the demo parameter is 1:2000.

## Support Matrix

- `per_trade_strategy_risk_pct`: supported_by_InpRiskPct_dynamic_lots; gap: none_for_strategy_lot_calculation
- `max_open_positions`: supported_by_InpMaxPos; gap: none_for_concurrent_position_count
- `min_lot`: supported_by_InpMinLots; gap: none
- `max_lot`: supported_by_InpMaxLots_but_current_set_is_broader; gap: live set should lower InpMaxLots or external monitor must enforce cap
- `max_daily_loss`: not_found; gap: requires EA guard or external account monitor
- `max_drawdown`: not_found; gap: requires EA guard or external account monitor
- `max_spread_points`: not_found; gap: requires EA spread check before entries or external monitor
- `margin_guard_pct`: partial_pre_trade_margin_check; gap: EA should use ACCOUNT_LEVERAGE or explicit InpLeverage before live

## Checks

- `demo_balance_cap_2000`: `True` - actual `2000.0`, expected `2000`
- `rehearsal_passed`: `True` - actual `nonprod_mt5_rehearsal_passed`, expected `nonprod_mt5_rehearsal_passed`
- `symbol_xauusdm`: `True` - actual `XAUUSDm`, expected `XAUUSDm`
- `strategy_risk_pct_present`: `True` - actual `3.0`, expected `> 0`
- `max_daily_loss_positive`: `True` - actual `120.0`, expected `> 0`
- `max_drawdown_positive`: `True` - actual `200.0`, expected `> 0`
- `max_spread_at_or_above_current`: `True` - actual `300`, expected `>= current 240`
- `max_lot_not_above_set_cap`: `True` - actual `0.1`, expected `<= 10.0`
- `ea_has_inp_risk_pct`: `True` - actual `present`, expected `present`
- `ea_has_inp_max_pos`: `True` - actual `present`, expected `present`
- `ea_lacks_daily_loss_guard_expected`: `True` - actual `not found`, expected `not found`
- `ea_lacks_drawdown_guard_expected`: `True` - actual `not found`, expected `not found`
- `ea_lacks_spread_guard_expected`: `True` - actual `not found`, expected `not found`
- `margin_estimate_hardcoded_500_detected`: `True` - actual `detected`, expected `detected`
- `proposal_not_live_approval`: `True` - actual `ready=false confirmation=true`, expected `ready=false confirmation=true`

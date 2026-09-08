# Non-production MT5 Rehearsal Package

## Decision

- status: `ready_to_execute_nonprod_mt5_rehearsal`
- tester_ini: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.nonprod_demo_rehearsal_20260601_20260707_20260721.ini`
- terminal_exe: `F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe`
- symbol: `XAUUSDm`
- period: `M30`
- window: `2026.06.01 -> 2026.07.07`
- deposit: `2000`
- leverage: `1:2000`
- InpSimMode: `false`
- risk_pct: `3.0`
- use_dynamic_lots: `true`
- baseline_window_rows: `15`
- ready_to_execute_nonprod_rehearsal: `True`
- ready_to_live_trade: `False`

## Boundary

- This package is for MT5 Strategy Tester or demo non-production order lifecycle rehearsal only.
- It does not approve real-money live trading.
- The Python runner remains blocked.
- `InpSimMode=false` is confined to this non-production tester config.

## Sample Metrics

- `baseline_rehearsal_window_rows`: `15`
- `sl_or_deal_exit_rows`: `10`
- `expert_exit_rows`: `5`
- `min_lot`: `0.01`
- `max_lot`: `0.04`
- `exit_reason_deal_exit`: `10`
- `exit_reason_stage1_tp`: `2`
- `exit_reason_stage2_forced`: `1`
- `exit_reason_stage3_cross_exit`: `2`
- `stage_1`: `5`
- `stage_2`: `5`
- `stage_3`: `5`

## Checks

- `demo_confirmation_ready`: `True` - actual `True`, expected `True`
- `demo_confirmation_not_live`: `True` - actual `False`, expected `False`
- `terminal_exe_exists`: `True` - actual `F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe`, expected `exists`
- `ex5_exists`: `True` - actual `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.ex5`, expected `exists`
- `frozen_set_exists`: `True` - actual `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_frozen_20260718.set`, expected `exists`
- `symbol_matches`: `True` - actual `XAUUSDm`, expected `XAUUSDm`
- `risk_pct_present`: `True` - actual `3.0`, expected `present`
- `dynamic_lots_enabled`: `True` - actual `true`, expected `true`
- `inp_sim_mode_false_for_tester_only`: `True` - actual `false`, expected `false`
- `deposit_2000`: `True` - actual `2000`, expected `2000`
- `leverage_2000`: `True` - actual `2000`, expected `2000`
- `baseline_window_has_rows`: `True` - actual `15`, expected `>= 6`
- `baseline_window_has_sl`: `True` - actual `10`, expected `> 0`
- `baseline_window_has_expert_exit`: `True` - actual `5`, expected `> 0`
- `tester_ini_written`: `True` - actual `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.nonprod_demo_rehearsal_20260601_20260707_20260721.ini`, expected `exists`
- `terminal_data_path_known`: `True` - actual `C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16; probe=permission_denied`, expected `exists or permission_denied`

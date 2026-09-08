# Demo MT5 EA Execution Approval Record

- approval_id: `DEMO-MT5-EA-20260721-001`
- approval_date: `2026-07-21T18:08:14`
- approver: `user_confirmed_in_chat`
- account_alias: `MT5_DEMO_***085`
- account_id_storage: `redacted_full_id_not_written; last3=085`
- account_type: `demo_nonproduction`
- symbol: `XAUUSDm`
- starting_balance_cap: `2000`
- leverage: `1:2000`
- max_risk: `strategy_defined; strategy_InpRiskPct=3.0`
- max_lots: `strategy_defined; strategy_InpMaxLots=10.0`
- allowed_runner: `MT5_EA_ONLY`
- order_source_count: `1`
- rollback_owner: `user`
- emergency_stop: `disable_mt5_auto_trading`
- position_close_rule: `strategy_defined`
- approval_scope: `nonprod_demo_rehearsal_only`
- ready_to_nonprod_rehearsal: `true`
- ready_to_live_trade: `false`

## Boundary

- This approval is for MT5 demo/non-production rehearsal only.
- It is not a real-money live trading approval.
- The full account id is intentionally not written into repo artifacts.
- The next evidence must come from an actual MT5 tester/demo rehearsal report and ledger.

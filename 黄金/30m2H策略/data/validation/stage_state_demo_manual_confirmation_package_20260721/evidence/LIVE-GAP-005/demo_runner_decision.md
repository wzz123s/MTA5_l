# Demo Production Runner Decision

- runner_mode: `MT5_EA_ONLY`
- order_source_count: `1`
- blocked_runner_files: `auto_trade/auto_trader.py`
- approver: `user_confirmed_in_chat`
- scope: `demo_nonproduction_rehearsal_only`
- ready_to_nonprod_rehearsal: `true`
- ready_to_live_trade: `false`

Only the MT5 EA may place demo/tester orders during the rehearsal.
The Python runner remains blocked for order placement.

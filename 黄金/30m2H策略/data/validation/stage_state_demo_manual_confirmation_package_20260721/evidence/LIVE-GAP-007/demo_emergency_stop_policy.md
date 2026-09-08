# Demo Emergency Stop Policy

- emergency_stop: `disable_mt5_auto_trading`
- disable_auto_trading_steps: `turn off MT5 Algo Trading / AutoTrading`
- close_position_steps: `strategy_defined; validate in demo rehearsal`
- rollback_steps: `remove EA from chart or stop tester/demo run`
- owner: `user`
- backup_owner: `not_assigned_for_live`
- ready_to_nonprod_rehearsal: `true`
- ready_to_live_trade: `false`

This is sufficient to rehearse emergency behavior in non-production.
It is not sufficient by itself for real-money positions.

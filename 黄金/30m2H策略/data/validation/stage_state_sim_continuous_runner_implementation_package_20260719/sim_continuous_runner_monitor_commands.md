# Sim Continuous Runner Monitor Commands

Preflight command:

```powershell
python "F:\use_code\MTA5_l\黄金\30m2H策略\scripts\validate\sim_continuous_runner_monitor_20260719.py" --config "F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_continuous_runner_implementation_package_20260719\sim_continuous_runner_config_20260719.json" --out-dir "F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_continuous_runner_implementation_package_20260719\monitor_preflight" --mode preflight
```

Forward-review command after manual MT5 chart trial:

```powershell
python "F:\use_code\MTA5_l\黄金\30m2H策略\scripts\validate\sim_continuous_runner_monitor_20260719.py" --config "F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_continuous_runner_implementation_package_20260719\sim_continuous_runner_config_20260719.json" --out-dir "F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_continuous_runner_implementation_package_20260719\monitor_forward_review" --mode forward-review
```

Execution boundary:

- These commands do not run `auto_trade/auto_trader.py`.
- The config has `live_trade_enabled=false` and `sim_only_lock=true`.
- Forward-review does not approve live trading.
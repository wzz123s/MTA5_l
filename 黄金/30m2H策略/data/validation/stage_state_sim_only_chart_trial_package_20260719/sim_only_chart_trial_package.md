# SIM_ONLY Chart Trial Package Review

## Decision

- status: `pass`
- ready_to_manual_chart_trial_with_sim_only: `True`
- ready_to_startup_attach_trial: `True`
- ready_to_sim_continuous_runner_execution: `False`
- ready_to_live_trade: `False`
- blocker_failure_count: `0`
- warning_failure_count: `0`

## Package

- source: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA_SIM_ONLY.mq5`
- local ex5: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA_SIM_ONLY.ex5`
- deployed ex5: `C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\Advisors\30m2H_Strategy_EA_SIM_ONLY.ex5`
- local set: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set`
- deployed set: `C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Presets\30m2H_Strategy_EA_SIM_ONLY.stage_state_sim_dryrun_20260719.set`
- compile log: `F:\use_code\MTA5_l\auto_trade\compile_sim_only_20260719.log`

## Summary

- The frozen main EA source remains unchanged and still defaults `InpSimMode=false`.
- The SIM_ONLY wrapper defaults `InpSimMode=true` and aborts initialization if it is changed to false.
- Strategy signal, stop, exit and sizing logic are copied from the frozen EA; this package is only a chart-trial safety wrapper.
- The package does not open the continuous runner gate and does not approve live trading.

## Failed Checks

- None.

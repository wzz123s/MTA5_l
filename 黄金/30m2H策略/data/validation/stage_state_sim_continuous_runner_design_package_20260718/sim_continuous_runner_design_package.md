# Sim Continuous Runner Design Package

- Decision date: 2026-07-18
- Status: `pass`
- Ready to implementation package: `True`
- Ready to execution: `False`
- Ready to live trade: `False`
- Blocker failure count: `0`

## Boundary

- This package designs a local MT5 signal-only forward dry-run runner.
- It does not start continuous running.
- It does not approve live trading.
- It does not use `auto_trade/auto_trader.py`.
- `InpSimMode=true` is a hard requirement.

## Package Files

- `sim_continuous_runner_config_template.json`
- `sim_continuous_runner_scope.csv`
- `sim_continuous_runner_risk_controls.csv`
- `sim_continuous_runner_monitoring_spec.csv`
- `sim_continuous_runner_forward_dryrun_test_plan.csv`
- `sim_continuous_runner_implementation_tasks.csv`
- `sim_continuous_runner_runbook.md`

## Next Gate

- Build the implementation package: safe config file, monitor/preflight script, manual MT5 chart runbook trial, and forward dry-run review.
- Execution remains blocked until that implementation gate passes.
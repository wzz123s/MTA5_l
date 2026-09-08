# Sim Continuous Runner Runbook

## Start Preconditions

- Use `XAUUSDm` / `M30` only.
- Load `auto_trade/30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set`.
- Confirm `InpSimMode=true` before enabling the EA.
- Do not run `auto_trade/auto_trader.py`.
- Keep live trading approval closed.

## Manual Forward Dry-run Flow

1. Open MT5 terminal with the account already configured in MT5.
2. Open an `XAUUSDm` `M30` chart.
3. Attach `Advisors\30m2H_Strategy_EA.ex5`.
4. Load the sim dry-run set and verify `InpSimMode=true`.
5. Watch the Experts/Journal log for `SIMULATION` mode.
6. Let at least one new M30 bar close.
7. Check signal CSV freshness and confirm trade ledger remains header-only.
8. Run the future forward dry-run review script before opening any execution gate.

## Stop Flow

1. Disable Algo Trading or remove the EA from the chart.
2. Create `auto_trade/RUNNER_STOP.flag` once monitor implementation exists.
3. Save/copy no credentials into project files.
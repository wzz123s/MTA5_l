# Sim Dry-run Smoke Package

- Decision date: 2026-07-18
- Status: `pass`
- Ready to execute tester smoke: `True`
- Ready to live trade: `False`
- Blocker failure count: `0`

## Scope

- Generates a short-window MT5 Strategy Tester `.ini` from the frozen full tester config.
- Forces `InpSimMode=true`, `InpExportCSV=true`, and `InpExportTradeLedger=true`.
- Keeps live trading blocked; this package is only for signal-only dry-run smoke.

## Generated Files

- `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_sim_dryrun_smoke_20260601_20260707.ini`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_dryrun_smoke_package_20260718\30m2H_Strategy_EA.stage_state_sim_dryrun_smoke_20260601_20260707.ini`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_dryrun_smoke_package_20260718\sim_dryrun_smoke_run_command.md`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_dryrun_smoke_package_20260718\sim_dryrun_smoke_tester_fields.csv`
- `F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\stage_state_sim_dryrun_smoke_package_20260718\sim_dryrun_smoke_input_fields.csv`

## Expected Smoke Result

- EA loads in Strategy Tester for `XAUUSDm` / `M30` / `2026.06.01` to `2026.07.07`.
- Tester deposit/leverage remain `$500` and `1:100`.
- Because `InpSimMode=true`, the run should not be treated as a profit regression; use it to validate initialization, signal scanning, CSV/log export, and absence of live-run escalation.

## Next Gate

- Execute the generated tester command only if the external MT5 terminal launch is approved.
- After execution, parse the report/log/export files before considering any live/sim continuous runner work.
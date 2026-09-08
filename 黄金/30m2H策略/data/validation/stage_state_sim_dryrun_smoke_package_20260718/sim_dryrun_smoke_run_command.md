# Sim Dry-run Smoke Tester Command

Run from PowerShell:

```powershell
& "F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe" /config:"F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_sim_dryrun_smoke_20260601_20260707.ini"
```

Safety posture:

- `InpSimMode=true` is forced in the generated tester `.ini`.
- Do not run `auto_trade/auto_trader.py` for this smoke.
- Expected tester balance stays near the initial `$500` because sim mode does not place real tester orders.
- Use the generated signal CSV/log output to verify the EA can initialize, scan, and export signals in the MT5 runtime.

After the run, collect:

- tester report: `auto_trade/stage_state_sim_dryrun_smoke_20260601_20260707_report.xml`
- latest MT5 tester log
- latest `30m2H_strategy_signals_export.csv` if exported
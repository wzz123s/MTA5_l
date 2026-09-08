# Live / Sim Run Gate

- Decision date: 2026-07-18
- Status: `pass`
- Ready to sim dry-run: `True`
- Ready to live trade: `False`
- Sim blocker count: `0`
- Live blocker count: `5`

## Summary

| key | value |
|---|---|
| `frozen_set` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_frozen_20260718.set |
| `sim_dryrun_set` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set |
| `tester_ini` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_full_2018_20260707.ini |
| `local_ex5` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.ex5 |
| `frozen_expected_trades` | 82 |
| `frozen_expected_final_balance` | 1649.84 |
| `sim_mode` | true |
| `export_csv` | true |
| `export_trade_ledger` | true |
| `hardcoded_credential_file_count` | 3 |
| `python_auto_trader_current_runner` | False |

## Decision

- The frozen MT5 tester package is ready for replay.
- A signal-only sim dry-run parameter set has been generated with `InpSimMode=true`.
- Live trading is not approved in this gate. Live needs separate credential handling, risk limits, monitoring, and operational controls.
- Existing Python `auto_trader.py` is not the current frozen EA strategy runner and must not be treated as the production runner.

## Dry-run Use

- Use `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set` for manual MT5 chart/UI signal-only dry run.
- Use the existing frozen tester `.ini` only for full Strategy Tester replay.

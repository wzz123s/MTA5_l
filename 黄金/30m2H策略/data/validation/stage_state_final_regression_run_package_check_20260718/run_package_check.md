# Final Regression: EA EX5 / SET Run Package Check

- Decision date: 2026-07-18
- Check id: `ea_ex5_set_run_package_check`
- Status: `pass`
- Pass: `True`
- Ready to frozen tester run: `True`
- Reason: `ea_binary_config_set_snapshot_and_archive_outputs_are_ready_for_frozen_tester_run`

## Package Summary

| key | value |
|---|---|
| `mq5_source` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.mq5 |
| `local_ex5` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.ex5 |
| `deployed_ex5` | C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\Advisors\30m2H_Strategy_EA.ex5 |
| `terminal_exe` | F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe |
| `tester_ini` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_full_2018_20260707.ini |
| `generated_set` | F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_frozen_20260718.set |
| `local_ex5_sha256` | 5F3D2771F43815E6A405CE8DFBDE31B8ECF35400E5C433992A8D158D95AA1B8C |
| `deployed_ex5_sha256` | 5F3D2771F43815E6A405CE8DFBDE31B8ECF35400E5C433992A8D158D95AA1B8C |
| `tester_symbol` | XAUUSDm |
| `tester_period` | M30 |
| `date_range` | 2018.01.01 to 2026.07.07 |
| `deposit` | 500 |
| `leverage` | 100 |
| `risk_pct` | 3.0 |
| `dynamic_lots` | true |
| `stage_lots` | 0.01/0.02/0.03 |
| `expected_frozen_final_balance` | 1649.84 |
| `expected_frozen_trades` | 82 |

## Check Result

- Blocker failures: `0`
- Local EX5 and deployed EX5 SHA256 hashes match.
- Current frozen `.set` snapshot was generated from the full tester `.ini`.
- Older v3.21/v3.22 `.set` files are historical and should not be treated as the frozen run package.

## Boundary

This check validates run-package readiness for the frozen MT5 tester baseline. It does not approve live trading and does not modify EA/Python strategy logic.

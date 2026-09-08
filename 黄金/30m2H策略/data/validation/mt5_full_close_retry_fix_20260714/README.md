# MT5 Full Close Retry Fix 20260714

## Scope

- EA: `auto_trade/30m2H_Strategy_EA.mq5`
- Config: `auto_trade/30m2H_Strategy_EA.close_retry_full_2018_20260707.ini`
- Window: `2018.01.01` to `2026.07.07`
- Deposit: `500`
- Leverage: `100`
- `InpExportTradeLedger=true`
- `InpExportStagePriceDiag=false`

## Outputs

- `30m2H_strategy_trade_ledger.csv`
- `30m2H_strategy_deal_history.csv`
- `30m2H_strategy_signals_export.csv`
- `close_retry_full_regression_report.md`
- `close_retry_full_regression_summary.csv`
- `close_retry_full_regression_changed_rows.csv`
- `close_retry_full_regression_reason_diff.csv`

## Result

- Ledger rows: `234`
- Unique signal anchors: `78`
- Ledger net profit: `3311.35`
- Raw deal OUT rows: `234`
- Raw deal OUT net profit: `3311.35`
- Implied final balance: `3811.35`

## Main Difference Versus Previous Full Ledger

- Previous closed snapshot net profit: `3440.37`
- New net profit: `3311.35`
- Delta: `-129.02`
- Main changed row:
  - `2020.03.20 02:00` BUY Stage3
  - old exit: `2020.03.25 10:00:05`, net `138.59`
  - new exit: `2020.03.22 22:05:00`, net `20.37`
- Tester log confirms the first Stage3 close attempt failed at `2020.03.22 00:00:00` due to market closed; the fixed EA retained state and retried successfully at `2020.03.22 22:05:00`.

## Decision

- Use this snapshot as the MT5 full-run baseline for subsequent mapping and Stage exit alignment.

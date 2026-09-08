# MT5 Direct Data Tools

This folder contains direct MetaTrader 5 Python API data tools.

## Files

- `mt5_connection.py`: MT5 initialize/shutdown, symbol visibility, timeframe mapping, public snapshots.
- `mt5_history.py`: historical bars export and `raw_source_manifest.json` generation.
- `mt5_live.py`: live tick and latest-bar capture for deployment smoke tests.

## Dry Run

```powershell
python scripts/mt5/mt5_history.py `
  --strategy 1H_M30_4H `
  --strategy-dir 1H_M30_4H策略 `
  --symbol XAUUSDm `
  --timeframes M30,H1,H4 `
  --from 2020-01-01 `
  --to 2024-01-01 `
  --source-id dry_run `
  --dry-run
```

Dry run does not connect to MT5 and only prints planned output paths.

## Safety

Do not write MT5 passwords into markdown files or committed scripts. Pass them through command line only for local execution, or keep the terminal logged in and omit `--password`.

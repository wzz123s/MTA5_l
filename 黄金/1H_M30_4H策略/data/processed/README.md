# 1H_M30_4H processed data

## Files

- `raw_m30_standardized.csv`
- `30m_bars.csv`
- `1h_bars.csv`
- `4h_bars.csv`
- `mt5_basic_cross_signals.csv`
- `1h_m30_4h_context_trades.csv`

## Notes

- Raw data is read from this strategy's MT5 manifest, not from the reference strategy raw folder.
- `mt5_basic_cross_signals.csv` is a baseline research candidate set using SMA5/SMA13 crosses.
- StopSpec filtering is deferred to validation and must use `stop_distance`, not `focus_sd`.
- Final Stage, StopSpec, position sizing, EA parameters and Python-vs-EA alignment still require dedicated validation.

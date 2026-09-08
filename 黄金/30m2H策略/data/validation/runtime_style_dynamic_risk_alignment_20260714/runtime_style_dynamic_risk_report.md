# Runtime Style Dynamic Risk Alignment 20260714

## Method

- Base source: `dynamic_risk_alignment_shift90_close_retry_20260714/python_mt5_dynamic_risk_trades.csv`.
- Adjustment source: matched `stage_exit_detail_diff` trades from `matched_profit_exit_diff_shift90_close_retry_20260714`.
- Runtime evidence source: integrated Stage exit evidence plus remaining-blocker journal review.
- This is a diagnostic funds-curve replay: it keeps the Python-MT5 signal set and existing dynamic lots, then substitutes MT5 net PnL only for resolved runtime Stage-exit trades.
- It does not re-generate signals, re-open orders, or re-lot downstream trades from the adjusted balance.

## Overall Funds Curve

| source                                 | trade_count | final_balance | dynamic_total_profit | win_count | win_rate_pct | any_stage_sl_count | all_stage_sl_count | adjusted_trade_count | strict_replay_pending_adjusted_trades |
| -------------------------------------- | ----------- | ------------- | -------------------- | --------- | ------------ | ------------------ | ------------------ | -------------------- | ------------------------------------- |
| python_mt5_close_retry_original        | 98          | 1969.914099   | 1469.914099          | 46        | 46.9388      | 80                 | 33                 | 0                    | 0                                     |
| python_mt5_runtime_stage_exit_adjusted | 98          | 4288.503976   | 3788.503976          | 45        | 45.9184      | 80                 | 33                 | 28                   | 7                                     |
| mt5_ledger_reference_close_retry       | 78          | 3811.35       | 3311.35              | 33        | 42.3077      | 72                 | 36                 |                      |                                       |

## Matched Residual

| scope                       | rows | adjusted_rows | original_residual_sum | runtime_residual_sum | original_abs_residual_sum | runtime_abs_residual_sum | original_abs_residual_mean | runtime_abs_residual_mean |
| --------------------------- | ---- | ------------- | --------------------- | -------------------- | ------------------------- | ------------------------ | -------------------------- | ------------------------- |
| all_matched_trades          | 57   | 28            | -2275.85182           | 42.738057            | 4799.436818               | 269.514877               | 84.200646                  | 4.728331                  |
| stage_exit_detail_diff_only | 29   | 28            | -2374.399677          | -55.8098             | 4585.731741               | 55.8098                  | 158.128681                 | 1.924476                  |

## Primary Diff Class Residual

| primary_diff_class     | rows | adjusted_rows | original_residual_sum | runtime_residual_sum | original_abs_residual_sum | runtime_abs_residual_sum |
| ---------------------- | ---- | ------------- | --------------------- | -------------------- | ------------------------- | ------------------------ |
| exit_reason_diff       | 5    | 0             | -26.890608            | -26.890608           | 35.273736                 | 35.273736                |
| minor_or_mixed_diff    | 12   | 0             | 103.665597            | 103.665597           | 117.002675                | 117.002675               |
| pnl_aligned            | 6    | 0             | 9.672263              | 9.672263             | 11.158377                 | 11.158377                |
| stage_exit_detail_diff | 29   | 28            | -2374.399677          | -55.8098             | 4585.731741               | 55.8098                  |
| stop_distance_diff     | 5    | 0             | 12.100605             | 12.100605            | 50.270289                 | 50.270289                |

## Runtime Evidence Gate

- Final Priority 1 stage blockers used by this adjustment: `1`.
- Stage rows still marked as strict replay audit items: `15`.
- Stage rows adjusted to MT5 stage PnL for the trade-level runtime replay: `84`.

## Interpretation

- The matched Stage-exit PnL residual should collapse only for the adjusted `stage_exit_detail_diff` class.
- The all-trade final balance is still not expected to match MT5 ledger, because Python-MT5 has 98 trades while the MT5 ledger has 78 trades and unmatched signal-set drift is outside this replay.
- A full production runtime model would need to replay order lifecycle and re-lot subsequent trades from adjusted balances; this output is the safer diagnostic step before that larger rewrite.

# Dynamic Risk Input Preparation

## Summary
### python_only
- Layer3 rows: `118`
- Stage rows: `118`
- Matched rows: `118`
- Signal-only rows: `0`
- Stage-only rows: `0`
- Layer3 duplicate keys: `0`
- Stage duplicate keys: `0`
- Stop range (spec pts): `5.041794 ~ 34.959134`

### python_mt5
- Layer3 rows: `101`
- Stage rows: `101`
- Matched rows: `101`
- Signal-only rows: `0`
- Stage-only rows: `0`
- Layer3 duplicate keys: `0`
- Stage duplicate keys: `0`
- Stop range (spec pts): `5.07649 ~ 35.214713`

## Notes
- `stop_pts_spec = abs(entry - stop)`.
- `stop_pts_mql5 = stop_pts_spec * 1000` aligns with the EA comment `1 spec 点 = 1000 MQL5 points`.
- `signal_stage_pnl_gap = Layer3 pnl - Stage total_$` is kept only as a diagnostic helper; it is not yet the final dynamic-risk formula.

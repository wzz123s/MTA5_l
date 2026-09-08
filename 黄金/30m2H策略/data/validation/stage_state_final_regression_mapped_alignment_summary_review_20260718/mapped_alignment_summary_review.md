# Final Regression: Mapped Alignment Summary Review

- Decision date: 2026-07-18
- Check id: `mapped_alignment_summary_review`
- Status: `pass`
- Pass: `True`
- Reason: `unique_match_summary_and_freeze_mapping_snapshot_match_detail_files`

## Recomputed Summary

| source | python trades | mt5 trades | matched | reliable | relaxed | python unmatched | mt5 unmatched | profit diff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| python_only | 118 | 82 | 61 | 43 | 18 | 57 | 21 | 4502.497765 |
| python_mt5 | 98 | 82 | 60 | 29 | 31 | 38 | 22 | 654.894778 |

## Comparison Result

- Failed summary comparisons: `0`
- Failed tier comparisons: `0`
- Unique-match summary and final-freeze mapping snapshot are consistent with detail files.
- Tier counts are consistent with `unique_match_tier_counts.csv`.

## Boundary

This review only validates mapped alignment accounting. It does not change canonical mapper policy or rematch any trade.

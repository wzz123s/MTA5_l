# Stage-state M30 CLOSE post_n true no-candidate source audit

## Decision

- Target count: `2`
- Target ids: `mt5_0026;mt5_0061`
- All targets raw absent broad window: `False`
- Primary classification count: `2`
- Low-blast signal prototype gate open: `False`
- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.

## Case Summary

- `mt5_0026` `2021-11-10 16:30:00` `M30 CLOSE/post_n3`: raw exact `0`, raw 60m `0`, raw 7d same-family `0`, Layer3 exact same-mode `0`, classification `python_raw_generation_absent_broad_window`
- `mt5_0061` `2026-01-13 17:30:00` `M30 CLOSE/post_n6`: raw exact `1`, raw 60m `1`, raw 7d same-family `1`, Layer3 exact same-mode `0`, classification `python_raw_parent_transformed_then_layer3_filtered`

## Classification Buckets

- `python_raw_generation_absent_broad_window`: rows `1`, ids `mt5_0026`
- `python_raw_parent_transformed_then_layer3_filtered`: rows `1`, ids `mt5_0061`

## Interpretation

- The two targets split into different loss points: `mt5_0026` is broad-window Python raw absent, while `mt5_0061` has exact Python raw evidence but is transformed/filtered before Layer3/dynamic.
- Because the cohort has mixed loss points and only two samples, it does not support a low-blast signal or EA change.
- EA source shows M30 CLOSE/post_n is driven by `g_merged_post_n_counter` with strict-veto guard, while Python raw generation uses `merged_post_cross_n` produced by `add_pre_cross_and_counter()` over `方向_合并后`.

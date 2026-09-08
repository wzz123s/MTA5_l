# Stage-state duplicate continuation suppression prototype

## Scope

- Input: `duplicate_continuation_suppression_candidate` rows from the stage-state unique-conflict review.
- This is a first-order estimate only; it does not rerun dynamic risk, mapping, Stage exits, or EA.

## Decision

- Suppression rows: `8`.
- Removed duplicate profit sum: `371.07646`.
- First-order direct gap improvement: `371.07646`.
- First-order direct gap after: `2018.65581`.
- Merge gate pass: `False`.
- Decision: `diagnostic_improvement_not_mergeable`.

## Before/After Estimate

| scenario                                   |   python_trade_count |   python_final_balance |   mt5_final_balance |   direct_gap_py_minus_mt5 |   matched_profit_diff_py_minus_mt5 |   signal_set_gap_py_minus_mt5 |   removed_duplicate_rows |   removed_duplicate_profit_sum | first_order_only   |   direct_gap_from_components |   direct_gap_improvement |   signal_set_gap_improvement |
|:-------------------------------------------|---------------------:|-----------------------:|--------------------:|--------------------------:|-----------------------------------:|------------------------------:|-------------------------:|-------------------------------:|:-------------------|-----------------------------:|-------------------------:|-----------------------------:|
| current_stage_state_metadatafix            |                   98 |                4039.57 |             1649.84 |                   2389.73 |                            654.895 |                       1734.84 |                        0 |                          0     | False              |                       nan    |                  nan     |                      nan     |
| first_order_duplicate_suppression_estimate |                   90 |                3668.5  |             1649.84 |                   2018.66 |                            654.895 |                       1363.76 |                        8 |                        371.076 | True               |                      2018.66 |                  371.076 |                      371.076 |

## Suppression Candidates

| trade_id        | target_time         | dir_norm   |   dynamic_total_$ | cluster_key   | best_candidate_mt5_trade_id   |   best_candidate_abs_minutes | selected_owner_trade_id   | selected_owner_match_tier   |
|:----------------|:--------------------|:-----------|------------------:|:--------------|:------------------------------|-----------------------------:|:--------------------------|:----------------------------|
| python_mt5_0075 | 2025-10-17 15:00:00 | SELL       |         301.834   | mt5:mt5_0057  | mt5_0057                      |                           30 | python_mt5_0074           | exact_align90_all           |
| python_mt5_0038 | 2022-03-09 12:30:00 | SELL       |          89.2193  | mt5:mt5_0030  | mt5_0030                      |                           60 | python_mt5_0036           | exact_align90_all           |
| python_mt5_0021 | 2020-03-26 14:30:00 | BUY        |         -25.5358  | mt5:mt5_0014  | mt5_0014                      |                           60 | python_mt5_0019           | exact_align90_all           |
| python_mt5_0020 | 2020-03-26 14:00:00 | BUY        |          25.5163  | mt5:mt5_0014  | mt5_0014                      |                           30 | python_mt5_0019           | exact_align90_all           |
| python_mt5_0034 | 2022-03-07 22:00:00 | BUY        |         -18.0741  | mt5:mt5_0027  | mt5_0027                      |                           30 | python_mt5_0033           | exact_align90_all           |
| python_mt5_0031 | 2021-06-18 16:30:00 | SELL       |          17.5845  | mt5:mt5_0024  | mt5_0024                      |                           60 | python_mt5_0029           | exact_align90_all           |
| python_mt5_0028 | 2021-03-04 21:30:00 | SELL       |         -12.9986  | mt5:mt5_0022  | mt5_0022                      |                           60 | python_mt5_0027           | nearby_60_all               |
| python_mt5_0089 | 2026-03-24 05:00:00 | SELL       |          -6.46907 | mt5:mt5_0074  | mt5_0074                      |                           30 | python_mt5_0088           | exact_align90_all           |

## Cluster Impact

| cluster_key   |   rows | trade_ids                       |   removed_profit_sum |   abs_removed_profit_sum |   max_abs_removed_profit | best_candidate_mt5_ids   | selected_owner_ids   |   min_best_candidate_abs_minutes |
|:--------------|-------:|:--------------------------------|---------------------:|-------------------------:|-------------------------:|:-------------------------|:---------------------|---------------------------------:|
| mt5:mt5_0057  |      1 | python_mt5_0075                 |            301.834   |                301.834   |                301.834   | mt5_0057                 | python_mt5_0074      |                               30 |
| mt5:mt5_0030  |      1 | python_mt5_0038                 |             89.2193  |                 89.2193  |                 89.2193  | mt5_0030                 | python_mt5_0036      |                               60 |
| mt5:mt5_0014  |      2 | python_mt5_0021;python_mt5_0020 |             -0.01949 |                 51.052   |                 25.5358  | mt5_0014                 | python_mt5_0019      |                               30 |
| mt5:mt5_0027  |      1 | python_mt5_0034                 |            -18.0741  |                 18.0741  |                 18.0741  | mt5_0027                 | python_mt5_0033      |                               30 |
| mt5:mt5_0024  |      1 | python_mt5_0031                 |             17.5845  |                 17.5845  |                 17.5845  | mt5_0024                 | python_mt5_0029      |                               60 |
| mt5:mt5_0022  |      1 | python_mt5_0028                 |            -12.9986  |                 12.9986  |                 12.9986  | mt5_0022                 | python_mt5_0027      |                               60 |
| mt5:mt5_0074  |      1 | python_mt5_0089                 |             -6.46907 |                  6.46907 |                  6.46907 | mt5_0074                 | python_mt5_0088      |                               30 |

## Interpretation

- The first-order estimate improves the current stage-state direct gap by the sum of removed duplicate Python profit.
- Because later dynamic-risk lot sizing depends on balance path, this is not a mergeable result.
- The remaining direct gap is still much larger than the merge threshold, so the result is useful as a diagnostic/prototype direction only.

## Output Files

- `duplicate_suppression_candidates.csv`
- `duplicate_suppression_cluster_impact.csv`
- `duplicate_suppression_before_after_summary.csv`
- `duplicate_suppression_decision.csv`

# EA merged_post_n Approximation Diagnosis

## Summary

| metric                  |   value |
|:------------------------|--------:|
| rows                    |   97628 |
| band_mismatch_rows      |    6205 |
| python_signal_band_rows |   10610 |
| ea_signal_band_rows     |   16815 |
| max_abs_counter_diff    |     219 |

## Hot Windows

### 2023-03-15 14:30:00

| date                | 方向   | 方向_合并后   |   merged_post_cross_n |   ea_approx_merged_sign |   ea_approx_merged_post_n |   counter_diff |   abs_counter_diff | python_is_signal_band   | ea_is_signal_band   | band_mismatch   |
|:--------------------|:-------|:--------------|----------------------:|------------------------:|--------------------------:|---------------:|-------------------:|:------------------------|:--------------------|:----------------|
| 2023-03-15 12:30:00 | down   | down          |                   -28 |                      -1 |                       -28 |              0 |                  0 | False                   | False               | False           |
| 2023-03-15 13:00:00 | good   | good          |                     1 |                       1 |                         1 |              0 |                  0 | False                   | False               | False           |
| 2023-03-15 13:30:00 | up     | up            |                     2 |                       1 |                         2 |              0 |                  0 | True                    | True                | False           |
| 2023-03-15 14:00:00 | up     | up            |                     3 |                       1 |                         3 |              0 |                  0 | True                    | True                | False           |
| 2023-03-15 14:30:00 | up     | up            |                     4 |                       1 |                         4 |              0 |                  0 | True                    | True                | False           |
| 2023-03-15 15:00:00 | up     | up            |                     5 |                       1 |                         5 |              0 |                  0 | True                    | True                | False           |
| 2023-03-15 15:30:00 | up     | up            |                     6 |                       1 |                         6 |              0 |                  0 | True                    | True                | False           |
| 2023-03-15 16:00:00 | up     | up            |                     7 |                       1 |                         7 |              0 |                  0 | False                   | False               | False           |
| 2023-03-15 16:30:00 | up     | up            |                     8 |                       1 |                         8 |              0 |                  0 | False                   | False               | False           |

### 2025-10-09 02:30:00

| date                | 方向   | 方向_合并后   |   merged_post_cross_n |   ea_approx_merged_sign |   ea_approx_merged_post_n |   counter_diff |   abs_counter_diff | python_is_signal_band   | ea_is_signal_band   | band_mismatch   |
|:--------------------|:-------|:--------------|----------------------:|------------------------:|--------------------------:|---------------:|-------------------:|:------------------------|:--------------------|:----------------|
| 2025-10-09 00:30:00 | up     | up            |                   164 |                       1 |                        65 |            -99 |                 99 | False                   | False               | False           |
| 2025-10-09 01:00:00 | bad    | bad           |                    -1 |                      -1 |                        -1 |              0 |                  0 | False                   | False               | False           |
| 2025-10-09 01:30:00 | down   | down          |                    -2 |                      -1 |                        -2 |              0 |                  0 | True                    | True                | False           |
| 2025-10-09 02:00:00 | down   | down          |                    -3 |                      -1 |                        -3 |              0 |                  0 | True                    | True                | False           |
| 2025-10-09 02:30:00 | down   | down          |                    -4 |                      -1 |                        -4 |              0 |                  0 | True                    | True                | False           |
| 2025-10-09 03:00:00 | down   | down          |                    -5 |                      -1 |                        -5 |              0 |                  0 | True                    | True                | False           |
| 2025-10-09 03:30:00 | down   | down          |                    -6 |                      -1 |                        -6 |              0 |                  0 | True                    | True                | False           |
| 2025-10-09 04:00:00 | down   | down          |                    -7 |                      -1 |                        -7 |              0 |                  0 | False                   | False               | False           |
| 2025-10-09 04:30:00 | down   | down          |                    -8 |                      -1 |                        -8 |              0 |                  0 | False                   | False               | False           |

### 2026-02-02 17:00:00

| date                | 方向   | 方向_合并后   |   merged_post_cross_n |   ea_approx_merged_sign |   ea_approx_merged_post_n |   counter_diff |   abs_counter_diff | python_is_signal_band   | ea_is_signal_band   | band_mismatch   |
|:--------------------|:-------|:--------------|----------------------:|------------------------:|--------------------------:|---------------:|-------------------:|:------------------------|:--------------------|:----------------|
| 2026-02-02 15:00:00 | up     | down          |                   -87 |                       1 |                         2 |             89 |                 89 | False                   | True                | True            |
| 2026-02-02 15:30:00 | up     | down          |                   -88 |                       1 |                         3 |             91 |                 91 | False                   | True                | True            |
| 2026-02-02 16:00:00 | up     | down          |                   -89 |                       1 |                         4 |             93 |                 93 | False                   | True                | True            |
| 2026-02-02 16:30:00 | up     | down          |                   -90 |                       1 |                         5 |             95 |                 95 | False                   | True                | True            |
| 2026-02-02 17:00:00 | bad    | down          |                   -91 |                      -1 |                        -1 |             90 |                 90 | False                   | False               | False           |
| 2026-02-02 17:30:00 | down   | down          |                   -92 |                      -1 |                        -2 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 18:00:00 | down   | down          |                   -93 |                      -1 |                        -3 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 18:30:00 | down   | down          |                   -94 |                      -1 |                        -4 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 19:00:00 | down   | down          |                   -95 |                      -1 |                        -5 |             90 |                 90 | False                   | True                | True            |

### 2026-02-02 18:00:00

| date                | 方向   | 方向_合并后   |   merged_post_cross_n |   ea_approx_merged_sign |   ea_approx_merged_post_n |   counter_diff |   abs_counter_diff | python_is_signal_band   | ea_is_signal_band   | band_mismatch   |
|:--------------------|:-------|:--------------|----------------------:|------------------------:|--------------------------:|---------------:|-------------------:|:------------------------|:--------------------|:----------------|
| 2026-02-02 16:00:00 | up     | down          |                   -89 |                       1 |                         4 |             93 |                 93 | False                   | True                | True            |
| 2026-02-02 16:30:00 | up     | down          |                   -90 |                       1 |                         5 |             95 |                 95 | False                   | True                | True            |
| 2026-02-02 17:00:00 | bad    | down          |                   -91 |                      -1 |                        -1 |             90 |                 90 | False                   | False               | False           |
| 2026-02-02 17:30:00 | down   | down          |                   -92 |                      -1 |                        -2 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 18:00:00 | down   | down          |                   -93 |                      -1 |                        -3 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 18:30:00 | down   | down          |                   -94 |                      -1 |                        -4 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 19:00:00 | down   | down          |                   -95 |                      -1 |                        -5 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 19:30:00 | down   | down          |                   -96 |                      -1 |                        -6 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 20:00:00 | down   | down          |                   -97 |                      -1 |                        -7 |             90 |                 90 | False                   | False               | False           |

### 2026-02-02 19:00:00

| date                | 方向   | 方向_合并后   |   merged_post_cross_n |   ea_approx_merged_sign |   ea_approx_merged_post_n |   counter_diff |   abs_counter_diff | python_is_signal_band   | ea_is_signal_band   | band_mismatch   |
|:--------------------|:-------|:--------------|----------------------:|------------------------:|--------------------------:|---------------:|-------------------:|:------------------------|:--------------------|:----------------|
| 2026-02-02 17:00:00 | bad    | down          |                   -91 |                      -1 |                        -1 |             90 |                 90 | False                   | False               | False           |
| 2026-02-02 17:30:00 | down   | down          |                   -92 |                      -1 |                        -2 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 18:00:00 | down   | down          |                   -93 |                      -1 |                        -3 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 18:30:00 | down   | down          |                   -94 |                      -1 |                        -4 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 19:00:00 | down   | down          |                   -95 |                      -1 |                        -5 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 19:30:00 | down   | down          |                   -96 |                      -1 |                        -6 |             90 |                 90 | False                   | True                | True            |
| 2026-02-02 20:00:00 | down   | down          |                   -97 |                      -1 |                        -7 |             90 |                 90 | False                   | False               | False           |
| 2026-02-02 20:30:00 | down   | down          |                   -98 |                      -1 |                        -8 |             90 |                 90 | False                   | False               | False           |
| 2026-02-02 21:00:00 | down   | down          |                   -99 |                      -1 |                        -9 |             90 |                 90 | False                   | False               | False           |

## Largest Band Mismatches

| date                | 方向   | 方向_合并后   |   merged_post_cross_n |   ea_approx_merged_sign |   ea_approx_merged_post_n |   counter_diff |   abs_counter_diff | python_is_signal_band   | ea_is_signal_band   | band_mismatch   |
|:--------------------|:-------|:--------------|----------------------:|------------------------:|--------------------------:|---------------:|-------------------:|:------------------------|:--------------------|:----------------|
| 2024-09-26 02:30:00 | down   | up            |                   216 |                      -1 |                        -3 |           -219 |                219 | False                   | True                | True            |
| 2024-09-26 02:00:00 | down   | up            |                   215 |                      -1 |                        -2 |           -217 |                217 | False                   | True                | True            |
| 2024-09-26 03:30:00 | up     | up            |                   218 |                       1 |                         2 |           -216 |                216 | False                   | True                | True            |
| 2024-09-26 04:00:00 | up     | up            |                   219 |                       1 |                         3 |           -216 |                216 | False                   | True                | True            |
| 2024-09-26 04:30:00 | up     | up            |                   220 |                       1 |                         4 |           -216 |                216 | False                   | True                | True            |
| 2024-09-26 05:00:00 | up     | up            |                   221 |                       1 |                         5 |           -216 |                216 | False                   | True                | True            |
| 2024-09-26 05:30:00 | up     | up            |                   222 |                       1 |                         6 |           -216 |                216 | False                   | True                | True            |
| 2024-09-25 19:30:00 | up     | up            |                   205 |                       1 |                         2 |           -203 |                203 | False                   | True                | True            |
| 2024-09-25 20:00:00 | up     | up            |                   206 |                       1 |                         3 |           -203 |                203 | False                   | True                | True            |
| 2024-09-25 20:30:00 | up     | up            |                   207 |                       1 |                         4 |           -203 |                203 | False                   | True                | True            |
| 2024-09-25 21:00:00 | up     | up            |                   208 |                       1 |                         5 |           -203 |                203 | False                   | True                | True            |
| 2024-09-25 21:30:00 | up     | up            |                   209 |                       1 |                         6 |           -203 |                203 | False                   | True                | True            |
| 2018-11-13 20:00:00 | up     | down          |                  -188 |                       1 |                         5 |            193 |                193 | False                   | True                | True            |
| 2018-11-13 19:30:00 | up     | down          |                  -187 |                       1 |                         4 |            191 |                191 | False                   | True                | True            |
| 2018-11-13 19:00:00 | up     | down          |                  -186 |                       1 |                         3 |            189 |                189 | False                   | True                | True            |
| 2018-11-13 21:00:00 | down   | down          |                  -190 |                      -1 |                        -2 |            188 |                188 | False                   | True                | True            |
| 2018-11-13 21:30:00 | down   | down          |                  -191 |                      -1 |                        -3 |            188 |                188 | False                   | True                | True            |
| 2018-11-13 22:00:00 | down   | down          |                  -192 |                      -1 |                        -4 |            188 |                188 | False                   | True                | True            |
| 2018-11-13 22:30:00 | down   | down          |                  -193 |                      -1 |                        -5 |            188 |                188 | False                   | True                | True            |
| 2018-11-13 23:00:00 | down   | down          |                  -194 |                      -1 |                        -6 |            188 |                188 | False                   | True                | True            |
| 2025-01-13 08:00:00 | up     | up            |                   190 |                       1 |                         2 |           -188 |                188 | False                   | True                | True            |
| 2025-01-13 08:30:00 | up     | up            |                   191 |                       1 |                         3 |           -188 |                188 | False                   | True                | True            |
| 2025-01-13 09:00:00 | up     | up            |                   192 |                       1 |                         4 |           -188 |                188 | False                   | True                | True            |
| 2025-01-13 09:30:00 | up     | up            |                   193 |                       1 |                         5 |           -188 |                188 | False                   | True                | True            |
| 2025-01-13 10:00:00 | up     | up            |                   194 |                       1 |                         6 |           -188 |                188 | False                   | True                | True            |
| 2018-11-13 18:30:00 | up     | down          |                  -185 |                       1 |                         2 |            187 |                187 | False                   | True                | True            |
| 2023-01-04 22:30:00 | down   | up            |                   176 |                      -1 |                        -4 |           -180 |                180 | False                   | True                | True            |
| 2023-01-04 22:00:00 | down   | up            |                   175 |                      -1 |                        -3 |           -178 |                178 | False                   | True                | True            |
| 2024-08-14 02:30:00 | down   | up            |                   174 |                      -1 |                        -4 |           -178 |                178 | False                   | True                | True            |
| 2023-01-04 21:30:00 | down   | up            |                   174 |                      -1 |                        -2 |           -176 |                176 | False                   | True                | True            |
| 2023-01-04 23:30:00 | up     | up            |                   178 |                       1 |                         2 |           -176 |                176 | False                   | True                | True            |
| 2023-01-05 01:30:00 | up     | up            |                   179 |                       1 |                         3 |           -176 |                176 | False                   | True                | True            |
| 2023-01-05 02:00:00 | up     | up            |                   180 |                       1 |                         4 |           -176 |                176 | False                   | True                | True            |
| 2023-01-05 02:30:00 | up     | up            |                   181 |                       1 |                         5 |           -176 |                176 | False                   | True                | True            |
| 2023-01-05 03:00:00 | up     | up            |                   182 |                       1 |                         6 |           -176 |                176 | False                   | True                | True            |
| 2024-08-14 02:00:00 | down   | up            |                   173 |                      -1 |                        -3 |           -176 |                176 | False                   | True                | True            |
| 2020-12-04 16:30:00 | up     | up            |                   177 |                       1 |                         2 |           -175 |                175 | False                   | True                | True            |
| 2024-08-14 01:30:00 | down   | up            |                   172 |                      -1 |                        -2 |           -174 |                174 | False                   | True                | True            |
| 2024-08-14 03:30:00 | up     | up            |                   176 |                       1 |                         2 |           -174 |                174 | False                   | True                | True            |
| 2025-03-14 22:00:00 | down   | up            |                   168 |                      -1 |                        -6 |           -174 |                174 | False                   | True                | True            |

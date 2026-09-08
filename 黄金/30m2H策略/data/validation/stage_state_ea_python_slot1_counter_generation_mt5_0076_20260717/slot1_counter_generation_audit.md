# Stage-State EA/Python SLOT1 Counter Generation Audit for mt5_0076

## Final Decision

- Target: `mt5_0076`.
- Primary classification: `merged_postn_counter_offset`.
- Full classifications: `merged_postn_counter_offset;python_slot1_relabel_gap`.
- EA counter source: `g_merged_post_n_counter`.
- Python counter source: `raw M30 merged_post_cross_n label preserved through SLOT1 replace/rescue`.
- Main signal gate: `False`.
- EA behavior gate: `False`.
- Mapping gate: `False`.
- Low-blast prototype gate: `True`.
- Merge gate: `False`.

## Evidence

- EA `TryM15EarlyEntry()` assigns `merged_post_n = g_merged_post_n_counter`, then formats `post_nN_m15_slot1`; `_replace_or_rescue` is appended after the label is already created.
- No independent M15 SLOT1 post_n counter is visible in the current EA source; the M15 path borrows the legacy merged counter.
- Python builds `post_nN` from the M30 row's `merged_post_cross_n`; `ea_slot1_replace` / `ea_slot1_runtime_rescue` only changes `entry_time`, `entry`, stop handling and `variant`, not the `mode` label.
- At the MT5 real anchor, Python Layer1/2 rows: `1`; modes: `post_n3`.
- Python same-label `post_n5` occurs at: `2026-03-24 11:30:00`.
- Python +90 aligned rows: `1`; modes: `post_n6`.
- Target-window log `post_n5_m15_slot1_replace_or_rescue` hits: `2`.
- Target-window log `post_n_counter=5` hits: `2`.
- Target-window log `merged_post_n_counter=5` hits: `2`.
- Target-window log both counters equal 5 hits: `2`.
- Full-log same signal-src hits: `18`.

## Interpretation

- `post_n5_m15_slot1_replace_or_rescue` is not created by replace/rescue recalculating a SLOT1-local counter.
- It is best explained as the EA M15 branch inheriting the EA legacy `g_merged_post_n_counter` value at runtime.
- Python's `post_n3` at `2026-03-24 10:30` is the raw M30 `post_n3` candidate whose entry is moved to `10:15` by SLOT1 replace.
- Therefore, the mismatch is a counter-source gap first, and a replace/rescue relabeling gap second.

## Risk

- A direct change to `g_merged_post_n_counter` is not safe: earlier global and M15 strict-counter expansions were rejected by full tester.
- The next step should quantify all M15 SLOT1 post_n cases where EA's legacy merged counter disagrees with Python `merged_post_cross_n`, then design a low-blast prototype only if the cohort is coherent.

## Outputs

- `slot1_counter_generation_final_decision.csv`
- `slot1_counter_generation_code_hits.csv`
- `slot1_counter_generation_log_hits.csv`
- `slot1_counter_generation_candidate_alignment.csv`
- `slot1_counter_generation_legacy_m15_diag_window.csv`

## Counts

- Code evidence rows: `25`.
- Current log evidence rows: `96`.

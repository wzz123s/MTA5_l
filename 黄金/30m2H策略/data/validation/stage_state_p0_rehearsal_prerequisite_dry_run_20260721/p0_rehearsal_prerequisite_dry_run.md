# P0 Rehearsal Prerequisite Dry Run

## Decision

- status: `p0_rehearsal_dry_run_planned_live_blocked`
- p0_rehearsal_items: `1`
- planned_steps: `6`
- ready_to_live_trade: `False`

## Boundary

- This is a prerequisite dry-run plan only.
- No MT5 query, runner execution, order placement, live chart attachment, or live set switching is performed.
- Only demo, strategy tester, or SIM_ONLY-only environments are allowed for later rehearsal.
- Real-money accounts, positions, and credentials are prohibited.

## Items

- `LIVE-GAP-007` `emergency_rehearsal_report.csv` -> `黄金/30m2H策略\data\validation\stage_state_p0_rehearsal_prerequisite_dry_run_20260721\expected_evidence_samples\LIVE-GAP-007\emergency_rehearsal_report.csv`

## Planned Steps

- `LIVE-GAP-007` `PRECHECK-001`: Confirm rehearsal environment is demo, tester, or SIM_ONLY-only.
- `LIVE-GAP-007` `PRECHECK-002`: Confirm no real-money positions or orders will be touched.
- `LIVE-GAP-007` `PRECHECK-003`: Confirm runner files are not executed during this dry run.
- `LIVE-GAP-007` `DRYRUN-001`: Walk through emergency disable and rollback procedure as a document-only scenario.
- `LIVE-GAP-007` `DRYRUN-002`: Define expected redacted evidence files and reviewer fields.
- `LIVE-GAP-007` `REVIEW-001`: Review that gate remains open and ready_to_live_trade remains false.

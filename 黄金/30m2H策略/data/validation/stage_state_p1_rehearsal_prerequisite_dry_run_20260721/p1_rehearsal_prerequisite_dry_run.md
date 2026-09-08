# P1 Rehearsal Prerequisite Dry Run

## Decision

- status: `p1_rehearsal_dry_run_planned_live_blocked`
- p1_rehearsal_items: `3`
- planned_steps: `18`
- expected_evidence_samples: `3`
- ready_to_live_trade: `False`

## Boundary

- This is a prerequisite dry-run plan only.
- No MT5 query, runner execution, order placement, live chart attachment, or live set switching is performed.
- Later rehearsal is allowed only on demo, strategy tester, or SIM_ONLY-only environments.
- Real-money accounts, positions, orders, and credentials are prohibited.

## Items

- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` -> `黄金/30m2H策略\data\validation\stage_state_p1_rehearsal_prerequisite_dry_run_20260721\expected_evidence_samples\LIVE-GAP-010\nonprod_order_rehearsal_report.md`
- `LIVE-GAP-010` `rehearsal_ledger.csv` -> `黄金/30m2H策略\data\validation\stage_state_p1_rehearsal_prerequisite_dry_run_20260721\expected_evidence_samples\LIVE-GAP-010\rehearsal_ledger.csv`
- `LIVE-GAP-010` `rehearsal_alert_log.csv` -> `黄金/30m2H策略\data\validation\stage_state_p1_rehearsal_prerequisite_dry_run_20260721\expected_evidence_samples\LIVE-GAP-010\rehearsal_alert_log.csv`

## Planned Steps

- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` `PRECHECK-001`: Confirm rehearsal environment is demo, tester, or SIM_ONLY-only.
- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` `PRECHECK-002`: Confirm no real-money positions, orders, or live chart will be touched.
- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` `PRECHECK-003`: Confirm runner files are not executed during this dry-run plan.
- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` `DRYRUN-001`: Define the non-production open/close order rehearsal scenario.
- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` `DRYRUN-002`: Define expected ledger and alert rows with placeholder values.
- `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` `REVIEW-001`: Review that gate remains open and ready_to_live_trade remains false.
- `LIVE-GAP-010` `rehearsal_ledger.csv` `PRECHECK-001`: Confirm rehearsal environment is demo, tester, or SIM_ONLY-only.
- `LIVE-GAP-010` `rehearsal_ledger.csv` `PRECHECK-002`: Confirm no real-money positions, orders, or live chart will be touched.
- `LIVE-GAP-010` `rehearsal_ledger.csv` `PRECHECK-003`: Confirm runner files are not executed during this dry-run plan.
- `LIVE-GAP-010` `rehearsal_ledger.csv` `DRYRUN-001`: Define the non-production open/close order rehearsal scenario.
- `LIVE-GAP-010` `rehearsal_ledger.csv` `DRYRUN-002`: Define expected ledger and alert rows with placeholder values.
- `LIVE-GAP-010` `rehearsal_ledger.csv` `REVIEW-001`: Review that gate remains open and ready_to_live_trade remains false.
- `LIVE-GAP-010` `rehearsal_alert_log.csv` `PRECHECK-001`: Confirm rehearsal environment is demo, tester, or SIM_ONLY-only.
- `LIVE-GAP-010` `rehearsal_alert_log.csv` `PRECHECK-002`: Confirm no real-money positions, orders, or live chart will be touched.
- `LIVE-GAP-010` `rehearsal_alert_log.csv` `PRECHECK-003`: Confirm runner files are not executed during this dry-run plan.
- `LIVE-GAP-010` `rehearsal_alert_log.csv` `DRYRUN-001`: Define the non-production open/close order rehearsal scenario.
- `LIVE-GAP-010` `rehearsal_alert_log.csv` `DRYRUN-002`: Define expected ledger and alert rows with placeholder values.
- `LIVE-GAP-010` `rehearsal_alert_log.csv` `REVIEW-001`: Review that gate remains open and ready_to_live_trade remains false.

# Manual Evidence Prerequisite Plan

## Decision

- status: `manual_prerequisites_drafted_live_blocked`
- remaining_prerequisite_items: `20`
- pending_auto_items: `3`
- manual_items: `13`
- rehearsal_items: `4`
- p0_items: `13`
- p1_items: `7`
- ready_to_live_trade: `False`

## Boundary

- This plan defines prerequisites only; it does not fill production evidence.
- Real credentials, passwords, tokens, and account secret values remain forbidden.
- Live chart attachment, real-money orders, and live set switching remain forbidden.
- All gates remain open and live trading remains blocked.

## Execution Order

1. `P0` `LIVE-GAP-001` `live_trade_approval_record.md` - manual_confirmation; confirmer: user plus approver; next: fill the template with redacted/manual confirmation data only.
2. `P0` `LIVE-GAP-002` `live_package_manifest.json` - manual_live_action_approval; confirmer: user plus release reviewer; next: fill the template with redacted/manual confirmation data only.
3. `P0` `LIVE-GAP-002` `live_package_hashes.csv` - deferred_auto_after_manual_approval; confirmer: release reviewer; next: hash only the user-approved package manifest paths.
4. `P0` `LIVE-GAP-002` `live_package_deployment_proof.md` - manual_live_action_approval; confirmer: user plus release reviewer; next: fill the template with redacted/manual confirmation data only.
5. `P0` `LIVE-GAP-003` `sim_mode_transition_approval.md` - manual_live_action_approval; confirmer: user plus approver; next: fill the template with redacted/manual confirmation data only.
6. `P0` `LIVE-GAP-003` `parsed_live_set_template.json` - deferred_auto_after_manual_approval; confirmer: release reviewer; next: parse only a reviewed set template after transition approval exists.
7. `P0` `LIVE-GAP-004` `secret_policy.md` - manual_secret_safe_document; confirmer: user plus operator; next: fill the template with redacted/manual confirmation data only.
8. `P0` `LIVE-GAP-004` `env_example_review.md` - manual_secret_safe_document; confirmer: operator; next: fill the template with redacted/manual confirmation data only.
9. `P0` `LIVE-GAP-005` `production_runner_decision.md` - manual_live_action_approval; confirmer: user plus reviewer; next: fill the template with redacted/manual confirmation data only.
10. `P0` `LIVE-GAP-006` `live_risk_policy.json` - manual_confirmation; confirmer: user plus operator; next: fill the template with redacted/manual confirmation data only.
11. `P0` `LIVE-GAP-006` `risk_policy_manual_confirmation.md` - manual_confirmation; confirmer: user plus operator; next: fill the template with redacted/manual confirmation data only.
12. `P0` `LIVE-GAP-007` `emergency_runbook.md` - manual_live_action_approval; confirmer: user plus operator; next: fill the template with redacted/manual confirmation data only.
13. `P0` `LIVE-GAP-007` `emergency_rehearsal_report.csv` - nonprod_rehearsal; confirmer: user plus operator; next: prepare demo/tester rehearsal steps and expected evidence files.
14. `P1` `LIVE-GAP-008` `live_monitoring_policy.json` - manual_confirmation; confirmer: user or delegated operator; next: fill the template with redacted/manual confirmation data only.
15. `P1` `LIVE-GAP-008` `reconciliation_checklist.csv` - manual_confirmation; confirmer: user or delegated operator; next: fill the template with redacted/manual confirmation data only.
16. `P1` `LIVE-GAP-009` `live_account_spec_snapshot.json` - manual_secret_safe_document; confirmer: user or delegated operator; next: fill the template with redacted/manual confirmation data only.
17. `P1` `LIVE-GAP-009` `broker_symbol_spec.csv` - deferred_auto_after_manual_approval; confirmer: user or delegated operator; next: request explicit read-only MT5 approval, then collect symbol spec without orders.
18. `P1` `LIVE-GAP-010` `nonprod_order_rehearsal_report.md` - nonprod_rehearsal; confirmer: user or delegated reviewer; next: prepare demo/tester rehearsal steps and expected evidence files.
19. `P1` `LIVE-GAP-010` `rehearsal_ledger.csv` - nonprod_rehearsal; confirmer: reviewer; next: prepare demo/tester rehearsal steps and expected evidence files.
20. `P1` `LIVE-GAP-010` `rehearsal_alert_log.csv` - nonprod_rehearsal; confirmer: reviewer; next: prepare demo/tester rehearsal steps and expected evidence files.

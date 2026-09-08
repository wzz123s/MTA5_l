# Post-smoke Decision Gate

- Decision date: 2026-07-18
- Status: `pass`
- Ready to sim continuous runner design: `True`
- Ready to sim continuous runner execution: `False`
- Ready to live trade: `False`
- Blocker failure count: `0`

## Decision

- The frozen tester package, live/sim gate, smoke package, and smoke execution all passed their blocker checks.
- The project may move into sim continuous runner design.
- Continuous runner execution is not opened yet because credentials, runtime risk controls, monitoring, and forward dry-run verification are not designed.
- Live trading remains blocked.

## Required Next Tasks

| step_id | deliverable | acceptance |
|---|---|---|
| `runner_scope` | Define local sim runner scope: MT5 chart/EA signal-only runtime, not Python auto_trader.py and not live trade. | Runner doc states InpSimMode=true, symbol/timeframe, startup/stop path, and evidence outputs. |
| `credential_isolation` | Externalize or quarantine hardcoded MT5 credentials from Python helper scripts before any continuous runner. | No account/password literal is required by the runner path; secrets are not committed into strategy code. |
| `runtime_risk_controls` | Define sim/live independent guard rails: max daily loss, max session loss, max positions, kill switch, allowed symbol/timeframe. | Config exists and defaults keep live trade disabled. |
| `monitoring_restart_alerts` | Define heartbeat, log rotation, restart rule, and alert/report files for local MT5 runner. | A failed heartbeat or missing export is detectable without manual log browsing. |
| `forward_dryrun_verification` | Run a short live-market forward dry-run with InpSimMode=true and verify logs/exports. | Post-run review shows terminal active, CSV updates, no real order/deal rows, and no critical errors. |

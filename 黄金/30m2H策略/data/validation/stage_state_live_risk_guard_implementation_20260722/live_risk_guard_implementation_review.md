# LIVE-GAP-006 EA Live Risk Guard Implementation Review

Generated: 2026-07-22T23:32:21

## Decision

- Status: `live_risk_guard_implemented_compile_passed_guard_rehearsal_pending`
- Compile: `PASS`
- LIVE-GAP-006 code implemented: `True`
- LIVE-GAP-006 closed: `false`
- Ready to live trade: `false`

## What changed

- Added explicit live/pre-live guard switch with default `InpEnableLiveRiskGuards=false`.
- Added numeric guard inputs for balance cap, daily loss, drawdown, daily entries, spread, margin level, per-stage lot cap, and leverage override.
- Connected guard checks to the `ExecuteSignal` path before the split-stage orders are sent.
- Replaced the old hardcoded 1:500 margin estimate with `OrderCalcMargin`, while retaining a fallback estimate for diagnostics.
- Guard-enabled mode blocks new entries fail-closed and writes `LIVE_RISK_BLOCK` diagnostics.

## Current Evidence

- MQ5: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.mq5`
- EX5: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.ex5`
- Compile log: `F:\use_code\MTA5_l\auto_trade\compile_live_risk_guard_20260722.log`
- Compile log result: `0 errors, 0 warnings`
- Prior non-production rehearsal: `nonprod_mt5_rehearsal_passed`
- Prior rehearsal max lot: `0.05`
- Proposed live max lot cap: `0.10`

## Why LIVE-GAP-006 Is Not Closed Yet

1. The code now supports the numeric risk policy, but the final policy values still need explicit confirmation after implementation.
2. The prior MT5 rehearsal did not run with `InpEnableLiveRiskGuards=true`, so it proves baseline order lifecycle, not guard behavior.
3. The broader live gate still requires alert evidence and emergency stop handling evidence.

## Next Action

Prepare and run a non-production MT5 Strategy Tester rehearsal using the compiled EX5 with `InpEnableLiveRiskGuards=true`, then update the live gate from that evidence.

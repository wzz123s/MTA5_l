# LIVE-GAP-006 Guard-enabled Non-production Rehearsal Package

Generated: 2026-07-22T23:47:44

## Decision

- Status: `live_risk_guard_rehearsal_package_ready`
- Ready to execute nonprod guard rehearsal: `True`
- Ready to live trade: `false`

## Tester Config

- INI: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.ini`
- SET: `F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.set`
- Report: `F:\use_code\MTA5_l\auto_trade\live_risk_guard_rehearsal_20260601_20260707_20260722_report.xml`
- Terminal: `F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe`
- Expert: `Advisors\30m2H_Strategy_EA.ex5`
- Symbol/period: `XAUUSDm` / `M30`
- Window: `2026.06.01` to `2026.07.07`
- Deposit/leverage: `2000` / `1:2000`

## Guard Inputs

- `InpEnableLiveRiskGuards=true`
- `InpLiveBalanceCap=2000.0`
- `InpMaxDailyLossUSD=120.0`
- `InpMaxDrawdownUSD=200.0`
- `InpMaxNewPositionsPerDay=9`
- `InpMaxSpreadPoints=300`
- `InpMarginGuardPct=500.0`
- `InpLiveMaxLotCap=0.1`
- `InpLeverageOverride=0`
- `InpSimMode=false`

## Boundary

This package is for MT5 Strategy Tester / demo-context rehearsal only. It does not approve real-money live trading.

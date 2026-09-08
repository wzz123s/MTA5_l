# Manual MT5 EA Load Steps

Generated: 2026-07-24

## Target

- Account alias: `MT5_ACCOUNT_***085`
- Server: `Exness-MT5Trial5`
- Symbol/timeframe: `XAUUSDm / M30`
- EA: `30m2H_Strategy_EA.ex5`
- Approved set: `30m2H_Strategy_EA.live_loading_owner_local_20260723.set`
- Operator: `owner_local`

## Steps

1. In MT5, open or switch to chart `XAUUSDm`.
2. Set chart timeframe to `M30`.
3. In Navigator, find `Expert Advisors > Advisors > 30m2H_Strategy_EA`.
4. Drag the EA onto the `XAUUSDm / M30` chart.
5. In the EA input window, click `Load`.
6. Load the approved set from one of these MT5 preset locations:
   - `C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Presets\30m2H_Strategy_EA.live_loading_owner_local_20260723.set`
   - `C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Profiles\Tester\30m2H_Strategy_EA.live_loading_owner_local_20260723.set`
7. Confirm critical inputs:
   - `InpSymbol=XAUUSDm`
   - `InpSimMode=false`
   - `InpEnableLiveRiskGuards=true`
   - `InpLiveBalanceCap=2000.0`
   - `InpLiveMaxLotCap=0.1`
8. Confirm common settings allow algorithmic trading for the EA.
9. Enable MT5 toolbar AutoTrading only after the EA is attached with the approved inputs.
10. Keep `owner_local` monitoring alerts, Experts/Journal logs, and account exposure.

## After Loading

Tell Codex: `已在 MT5 GUI 加载 EA 并开启 AutoTrading，采集 post-load evidence。`

Do not include the full account number, password, investor password, API token, or secret key.

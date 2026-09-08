# Frozen MT5 Tester Run Command

Run from PowerShell:

```powershell
& "F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe" /config:"F:\use_code\MTA5_l\auto_trade\30m2H_Strategy_EA.stage_state_full_2018_20260707.ini"
```

Expected frozen reference after full tester:

- Symbol: XAUUSDm
- Period: M30
- Date range: 2018.01.01 to 2026.07.07
- Deposit: 500 USD
- Leverage: 1:100
- Expected final balance from frozen archive: 1649.84 USD

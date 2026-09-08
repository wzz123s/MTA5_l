# -*- coding: utf-8 -*-
import MetaTrader5 as mt5
if not mt5.initialize():
    raise SystemExit(1)
t = mt5.symbol_info_tick("XAUUSDm")
print("XAUUSDm 现价 bid=", t.bid, "ask=", t.ask, " time=", t.time)
info = mt5.symbol_info("XAUUSDm")
print("digits=", info.digits, " point=", info.point, " swap_short=", info.swap_short)
mt5.shutdown()

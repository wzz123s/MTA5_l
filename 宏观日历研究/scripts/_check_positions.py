# -*- coding: utf-8 -*-
import MetaTrader5 as mt5
from datetime import datetime

if not mt5.initialize():
    print("MT5 initialize failed:", mt5.last_error())
    raise SystemExit(1)
pos = mt5.positions_get()
print("持仓数:", len(pos) if pos else 0)
if pos:
    for p in pos:
        line = ("ticket=" + str(p.ticket) + " magic=" + str(p.magic) + " " + p.symbol +
                (" BUY " if p.type == 0 else " SELL ") + "vol=" + str(p.volume) +
                " 开仓价=" + format(p.price_open, ".3f") +
                " SL=" + format(p.sl, ".3f") + " TP=" + format(p.tp, ".3f") +
                " 浮盈=$" + format(p.profit, ".2f") +
                " 开仓时间=" + datetime.utcfromtimestamp(p.time).strftime("%Y-%m-%d %H:%M UTC"))
        print(line)
mt5.shutdown()

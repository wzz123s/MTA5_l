# -*- coding: utf-8 -*-
"""给 BiasReversal 遗留空单补挂服务器 TP（3R），价格已低于限价将立即成交。"""
import MetaTrader5 as mt5

if not mt5.initialize():
    print("init failed:", mt5.last_error())
    raise SystemExit(1)

ticket = 2371628249
pos = mt5.positions_get(ticket=ticket)
if not pos:
    print("ticket not found (可能已被EA平仓)")
    mt5.shutdown()
    raise SystemExit(0)
p = pos[0]
entry = p.price_open
stop = p.sl
r = abs(entry - stop)
tp = entry - 3.0 * r   # 空单 3R TP
print("持仓:", p.ticket, "entry=", entry, "sl=", stop, "r=", r, "TP目标=", round(tp, 3))

request = {
    "action": mt5.TRADE_ACTION_SLTP,
    "symbol": p.symbol,
    "position": ticket,
    "sl": stop,
    "tp": round(tp, 3),
}
res = mt5.order_send(request)
print("order_send retcode:", res.retcode, res.comment)
mt5.shutdown()

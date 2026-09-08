# -*- coding: utf-8 -*-
"""市价平仓 BiasReversal 遗留空单（TP早已跌破，等价于TP执行，锁盈）。"""
import MetaTrader5 as mt5

if not mt5.initialize():
    raise SystemExit(1)
ticket = 2371628249
pos = mt5.positions_get(ticket=ticket)
if not pos:
    print("ticket not found（已被平仓）")
    mt5.shutdown()
    raise SystemExit(0)
p = pos[0]
print("平仓前: ticket=", p.ticket, "entry=", p.price_open, "浮盈=$", format(p.profit, ".2f"))
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": p.symbol,
    "position": ticket,
    "volume": p.volume,
    "type": mt5.ORDER_TYPE_BUY,  # 空单平仓 = 买入
    "price": mt5.symbol_info_tick(p.symbol).ask,
    "deviation": 30,
    "magic": p.magic,
    "comment": "manual close (TP overdue)",
    "type_filling": mt5.ORDER_FILLING_IOC,
}
res = mt5.order_send(request)
print("retcode:", res.retcode, res.comment)
if res.retcode == mt5.TRADE_RETCODE_DONE:
    # 验证
    left = mt5.positions_get(ticket=ticket)
    print("剩余持仓:", len(left) if left else 0)
    # 查历史成交确认
    deals = mt5.history_deals_get(position=ticket) or []
    print("该仓位成交笔数:", len(deals))
    for d in deals[-3:]:
        print("  deal:", d.ticket, d.type, d.price, d.volume, d.profit, d.time)
mt5.shutdown()

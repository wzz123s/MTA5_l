# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import MetaTrader5 as mt5
paths = sys.argv[1:]
for p in paths:
    ok = mt5.initialize(p)
    print("--- init", p, "->", ok, mt5.last_error() if not ok else "ok")
    if not ok:
        continue
    acc = mt5.account_info()
    if acc is None:
        print("  account_info: None", mt5.last_error()); mt5.shutdown(); continue
    print("  account:", acc.login, acc.server, "| cur:", acc.currency,
          "| balance:", acc.balance, "| equity:", round(acc.equity, 2),
          "| margin_free:", round(acc.margin_free, 2), "| profit:", round(acc.profit, 2))
    pos = mt5.positions_get()
    print("  open positions:", 0 if pos is None else len(pos))
    if pos:
        for d in pos:
            side = "BUY" if d.type == 0 else "SELL"
            print("    ", d.ticket, d.symbol, side, "vol", d.volume,
                  "| open", round(d.price_open, 2), "| sl", round(d.sl, 2),
                  "| tp", round(d.tp, 2), "| cur", round(d.price_current, 2),
                  "| profit", round(d.profit, 2), "| magic", d.magic,
                  "| comment", (d.comment or "")[:24])
    mt5.shutdown()

# -*- coding: utf-8 -*-
p = r"F:\use_code\MTA5_l\黄金\乖离反转策略\auto_trade\BiasReversal_Combo_EA.mq5"
s = open(p, encoding="utf-8-sig").read()
NL = "\n"
fixes = [
    ("input bool    InpVerboseDiag = true;",
     "input bool    InpVerboseDiag = true;" + NL + "input int     InpHistoryBars = 600;      // 2H 结构计算窗口"),
    ("   double stop = PositionGetDouble(POSITION_SL);" + NL + "   double entry = PositionGetDouble(POSITION_PRICE_OPEN);" + NL + "   MqlRates bar0;" + NL + "   if(!CopyRates(InpSymbol, PERIOD_M30, 0, 1, bar0)) return;" + NL + "   // SL 由服务器执行；检查 TP(3R) 与死叉" + NL + "   double tp = entry + (entry - stop) * InpTpR;" + NL + "   if(bar0.high >= tp)",
     "   double stop = PositionGetDouble(POSITION_SL);" + NL + "   double entry = PositionGetDouble(POSITION_PRICE_OPEN);" + NL + "   MqlRates bar0[];" + NL + "   if(CopyRates(InpSymbol, PERIOD_M30, 0, 1, bar0) < 1) return;" + NL + "   // SL 由服务器执行；检查 TP(3R) 与死叉" + NL + "   double tp = entry + (entry - stop) * InpTpR;" + NL + "   if(bar0[0].high >= tp)"),
    ("   double stop = PositionGetDouble(POSITION_SL);" + NL + "   double entry = PositionGetDouble(POSITION_PRICE_OPEN);" + NL + "   MqlRates bar0;" + NL + "   if(!CopyRates(InpSymbol, PERIOD_H2, 0, 1, bar0)) return;" + NL + "   double tp = entry - (stop - entry) * InpTpR;" + NL + "   if(bar0.low <= tp)",
     "   double stop = PositionGetDouble(POSITION_SL);" + NL + "   double entry = PositionGetDouble(POSITION_PRICE_OPEN);" + NL + "   MqlRates bar0[];" + NL + "   if(CopyRates(InpSymbol, PERIOD_H2, 0, 1, bar0) < 1) return;" + NL + "   double tp = entry - (stop - entry) * InpTpR;" + NL + "   if(bar0[0].low <= tp)"),
]
for old, new in fixes:
    assert old in s, "missing: " + old[:60]
    s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8-sig").write(s)
print("fixed")

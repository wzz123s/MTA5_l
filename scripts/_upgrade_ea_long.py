# -*- coding: utf-8 -*-
p = r"F:\use_code\MTA5_l\黄金\乖离反转策略\auto_trade\BiasReversal_Combo_EA.mq5"
s = open(p, encoding="utf-8-sig").read()
NL = "\n"

def rep(old, new):
    global s
    assert old in s, "missing: " + old[:70]
    s = s.replace(old, new, 1)

rep('datetime g_last_m30 = 0;' + NL + 'datetime g_last_h2 = 0;',
    'datetime g_last_m30 = 0;' + NL + 'datetime g_last_h1 = 0;' + NL + 'datetime g_last_h2 = 0;')
rep('   datetime t_m30 = iTime(InpSymbol, PERIOD_M30, 0);' + NL + '   datetime t_h2 = iTime(InpSymbol, PERIOD_H2, 0);',
    '   datetime t_m30 = iTime(InpSymbol, PERIOD_M30, 0);' + NL + '   datetime t_h1 = iTime(InpSymbol, PERIOD_H1, 0);' + NL + '   datetime t_h2 = iTime(InpSymbol, PERIOD_H2, 0);')

old_tick = '''      MqlRates r[];
      int n = CopyRates(InpSymbol, PERIOD_M30, 0, 100, r);
      if(n >= 14)
      {
         double s5[], s13[];
         if(CalcSmmaArray(r, n, 5, s5) && CalcSmmaArray(r, n, 13, s13))
         {
            int i = n - 2;
            bool gold_cross = (i >= 1 && s5[i] > s13[i] && s5[i - 1] <= s13[i - 1]);
            bool dead_cross = (i >= 1 && s5[i] < s13[i] && s5[i - 1] >= s13[i - 1]);
            if(gold_cross && g_long_gate_ok && !PositionSelectByMagic(InpMagicLong))
            {
               double stop = r[i].close * (1.0 - InpStopPct / 100.0);
               OpenPosition(1, InpMagicLong, stop, "long_gold_cross");
            }
            if(dead_cross)
               CloseByMagic(InpMagicLong, "dead cross");
         }
      }
      ManageLong();'''
new_tick = '''      // 做多信号改用 H1 金叉（回测 PF 2.19 vs M30 1.57）
      if(t_h1 != g_last_h1)
      {
         g_last_h1 = t_h1;
         MqlRates r1[];
         int n1 = CopyRates(InpSymbol, PERIOD_H1, 0, 100, r1);
         if(n1 >= 14)
         {
            double s5b[], s13b[];
            if(CalcSmmaArray(r1, n1, 5, s5b) && CalcSmmaArray(r1, n1, 13, s13b))
            {
               int i = n1 - 2;
               bool gold_cross = (i >= 1 && s5b[i] > s13b[i] && s5b[i - 1] <= s13b[i - 1]);
               bool dead_cross = (i >= 1 && s5b[i] < s13b[i] && s5b[i - 1] >= s13b[i - 1]);
               if(gold_cross && g_long_gate_ok && !PositionSelectByMagic(InpMagicLong))
               {
                  double stop = r1[i].close * (1.0 - InpStopPct / 100.0);
                  OpenPosition(1, InpMagicLong, stop, "long_h1_gold_cross");
               }
               if(dead_cross)
                  CloseByMagic(InpMagicLong, "dead cross");
            }
         }
      }
      ManageLongH1();'''
rep(old_tick, new_tick)

old_ml = '''void ManageLong()
{
   if(!PositionSelectByMagic(InpMagicLong)) return;
   double stop = PositionGetDouble(POSITION_SL);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   MqlRates bar0[];
   if(CopyRates(InpSymbol, PERIOD_M30, 0, 1, bar0) < 1) return;
   // SL 由服务器执行；检查 TP(3R) 与死叉
   double tp = entry + (entry - stop) * InpTpR;
   if(bar0[0].high >= tp)
   {
      CloseByMagic(InpMagicLong, "TP hit");
      return;
   }
   // M30 死叉（最新已收盘 bar）
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_M30, 0, 100, r);
   if(n < 14) return;
   double s5[], s13[];
   if(!CalcSmmaArray(r, n, 5, s5) || !CalcSmmaArray(r, n, 13, s13)) return;
   int i = n - 2;
   if(i >= 1 && s5[i] < s13[i] && s5[i - 1] >= s13[i - 1])
      CloseByMagic(InpMagicLong, "dead cross");
}'''
new_ml = '''void ManageLongH1()
{
   if(!PositionSelectByMagic(InpMagicLong)) return;
   double stop = PositionGetDouble(POSITION_SL);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   MqlRates bar0[];
   if(CopyRates(InpSymbol, PERIOD_H1, 0, 1, bar0) < 1) return;
   // SL 由服务器执行；检查 TP(3R) 与死叉
   double tp = entry + (entry - stop) * InpTpR;
   if(bar0[0].high >= tp)
   {
      CloseByMagic(InpMagicLong, "TP hit");
      return;
   }
   // H1 死叉（最新已收盘 bar）
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_H1, 0, 100, r);
   if(n < 14) return;
   double s5[], s13[];
   if(!CalcSmmaArray(r, n, 5, s5) || !CalcSmmaArray(r, n, 13, s13)) return;
   int i = n - 2;
   if(i >= 1 && s5[i] < s13[i] && s5[i - 1] >= s13[i - 1])
      CloseByMagic(InpMagicLong, "dead cross");
}'''
rep(old_ml, new_ml)
open(p, "w", encoding="utf-8-sig").write(s)
print("EA long side upgraded to H1")

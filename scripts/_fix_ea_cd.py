# -*- coding: utf-8 -*-
p = r"F:\use_code\MTA5_l\黄金\乖离反转策略\auto_trade\BiasReversal_Combo_EA.mq5"
s = open(p, encoding="utf-8-sig").read()
NL = "\n"

def rep(old, new):
    global s
    assert old in s, "missing: " + old[:70]
    s = s.replace(old, new, 1)

rep('input double  InpWThr         = 0.5;      // way_s_way / vol_way_s_way 阈值',
    'input double  InpWThr         = 0.5;      // way_s_way / vol_way_s_way 阈值' + NL +
    'input int     InpShortCdLoss  = 2;        // 连续止损达到该次数后冷却' + NL +
    'input int     InpShortCdHours = 120;      // 冷却时长（小时）')
rep('bool     g_short_pending = false;' + NL + 'datetime g_short_pending_time = 0;',
    'bool     g_short_pending = false;' + NL + 'datetime g_short_pending_time = 0;' + NL +
    'int      g_short_loss_streak = 0;    // 做空连续止损计数' + NL +
    'datetime g_short_cd_until = 0;       // 做空冷却截止时间' + NL +
    'bool     g_short_had_pos = false;    // 上一 2H bar 是否有做空仓')
rep('      if(!PositionSelectByMagic(InpMagicShort))' + NL + '      {' + NL + '         double rise = 0.0;',
    '      if(!PositionSelectByMagic(InpMagicShort) && TimeCurrent() >= g_short_cd_until)' + NL + '      {' + NL + '         double rise = 0.0;')
rep('               OpenPosition(-1, InpMagicShort, stop, "short_bias_reversal");',
    '               if(OpenPosition(-1, InpMagicShort, stop, "short_bias_reversal"))' + NL +
    '                  g_short_loss_streak = 0;')
rep('      ManageShort();' + NL + '   }' + NL + '}',
    '      ManageShort();' + NL + '   }' + NL + '}' + NL + NL +
    '//+------------------------------------------------------------------+' + NL +
    '//| 做空平仓后的冷却状态更新                                          |' + NL +
    '//+------------------------------------------------------------------+' + NL +
    'void UpdateShortCooldown(string reason)' + NL + '{' + NL +
    '   if(reason == "SL hit")' + NL + '   {' + NL +
    '      g_short_loss_streak++;' + NL +
    '      if(g_short_loss_streak >= InpShortCdLoss)' + NL +
    '      {' + NL +
    '         g_short_cd_until = TimeCurrent() + InpShortCdHours * 3600;' + NL +
    '         if(InpVerboseDiag)' + NL +
    '            Print("[CD] short cooldown ", InpShortCdHours, "h after ", g_short_loss_streak, " consecutive SL");' + NL +
    '      }' + NL +
    '   }' + NL +
    '   else' + NL +
    '      g_short_loss_streak = 0;' + NL +
    '}' + NL)
rep('   if(bar0[0].low <= tp)' + NL + '   {' + NL + '      CloseByMagic(InpMagicShort, "TP hit");' + NL + '      return;' + NL + '   }',
    '   if(bar0[0].low <= tp)' + NL + '   {' + NL + '      CloseByMagic(InpMagicShort, "TP hit");' + NL + '      UpdateShortCooldown("TP hit");' + NL + '      return;' + NL + '   }')
rep('   if(i >= 1 && s5[i] > s13[i] && s5[i - 1] <= s13[i - 1])' + NL + '      CloseByMagic(InpMagicShort, "gold cross");',
    '   if(i >= 1 && s5[i] > s13[i] && s5[i - 1] <= s13[i - 1])' + NL + '   {' + NL + '      CloseByMagic(InpMagicShort, "gold cross");' + NL + '      UpdateShortCooldown("gold cross");' + NL + '   }')
rep('void ManageShort()' + NL + '{',
    'void ManageShort()' + NL + '{' + NL +
    '   bool had = g_short_had_pos;' + NL +
    '   bool has = PositionSelectByMagic(InpMagicShort);' + NL +
    '   if(had && !has)' + NL +
    '      UpdateShortCooldown("SL hit");  // 仓位消失（服务器SL/手动平）按 SL 计' + NL +
    '   g_short_had_pos = has;' + NL +
    '   if(!has) return;')
open(p, "w", encoding="utf-8-sig").write(s)
print("EA patched")

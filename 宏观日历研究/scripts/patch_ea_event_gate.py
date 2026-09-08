# -*- coding: utf-8 -*-
"""给 30m2H(T=2h)/2H_M30_6H(T=1h)/USOIL4H(T=8h) 三个 EA 注入"高影响事件前N小时不开仓"可选门（默认关）。"""
from pathlib import Path

FILES = [
    (Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5"), 2, "datetime g_loss_cd_until = 0;     // 损失冷却截止时间"),
    (Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.mq5"), 1, "datetime g_loss_cd_until = 0;     // 损失冷却截止时间"),
    (Path(r"F:\use_code\MTA5_l\原油\原油4H门策略\auto_trade\USOIL4H_Gate_On2H_EA.mq5"), 8, "bool   g_gate_ok_s = false;   // gate passes for SHORT (4H up extreme quality)"),
]

INPUTS = '''
input group "=== Macro Calendar Filter (research, default OFF) ==="
input bool   InpEventFilterOn   = false;  // 事件过滤总开关（默认关，先模拟盘）
input int    InpEventFilterHrs  = {hrs};  // 高影响事件前 N 小时内不开新仓
input int    InpEventCheckEvery = 300;    // 日历查询缓存（秒）
'''

GLOBALS = '''
bool     g_ev_blackout   = false;   // 未来 N 小时内有高影响事件（日历门）
datetime g_ev_next_check = 0;       // 下次日历查询时刻
'''

FUNCS = '''
//| Macro Calendar Event Gate (research, default OFF)                 |
bool EventBlackout()
{
   if(!InpEventFilterOn) return false;
   return g_ev_blackout;
}

void RefreshCalendarGate()
{
   if(!InpEventFilterOn) return;
   datetime now = TimeCurrent();
   if(now < g_ev_next_check) return;
   g_ev_next_check = now + InpEventCheckEvery;
   MqlCalendarValue vals[];
   if(CalendarValueHistory(vals, now, now + InpEventFilterHrs * 3600) < 0)
   {
      Print("[CAL] CalendarValueHistory error=", GetLastError(), " (gate keeps state)");
      return;
   }
   g_ev_blackout = false;
   for(int i = 0; i < ArraySize(vals); i++)
   {
      MqlCalendarEvent ev;
      if(CalendarEventById(vals[i].event_id, ev) && ev.importance >= 3)
      {
         g_ev_blackout = true;
         if(InpVerboseDiag)
            Print("[CAL] event blackout: ", ev.name, " @ ", TimeToString(vals[i].time));
         break;
      }
   }
}

void OnTimer()
{
   RefreshCalendarGate();
}
'''


def patch(path: Path, hrs: int, globals_anchor: str):
    text = path.read_text(encoding="utf-8")
    orig = text
    n_checks = 0

    def rep(old, new, count=1):
        nonlocal text, n_checks
        assert text.count(old) == count, f"[{path.name}] anchor x{text.count(old)} != {count}: {old[:60]!r}"
        text = text.replace(old, new)
        n_checks += 1

    # 1) inputs after InpVerboseDiag
    rep("input bool    InpVerboseDiag = true;       // verbose per-bar diagnostics",
        "input bool    InpVerboseDiag = true;       // verbose per-bar diagnostics" + INPUTS.format(hrs=hrs))
    # 2) globals
    rep(globals_anchor, globals_anchor + GLOBALS)
    # 3) functions before OnInit
    rep("int OnInit()", FUNCS + "\nint OnInit()")
    # 4) timer in OnInit
    rep("   RestoreRealPositions();\n   return INIT_SUCCEEDED;",
        "   RestoreRealPositions();\n   EventSetTimer(60);\n   return INIT_SUCCEEDED;")
    # 5) kill timer in OnDeinit
    rep("void OnDeinit(const int reason)\n{\n}",
        "void OnDeinit(const int reason)\n{\n   EventKillTimer();\n}")
    # 6) signal acceptance gate (ABC family only: cd_ok line)
    if "USOIL4H" not in path.name:
        rep("      if(stop_pts >= spec_lo && stop_pts <= spec_hi && cd_ok)",
            "      if(EventBlackout() && InpVerboseDiag)\n"
            "         Print(\"[CAL] signal blocked by event gate (next high-impact event within \", InpEventFilterHrs, \"h)\");\n"
            "      if(stop_pts >= spec_lo && stop_pts <= spec_hi && cd_ok && !EventBlackout())")
    # 7) USOIL4H ok condition
    if "USOIL4H" in path.name:
        rep("      bool ok = (stop != 0.0 && gate_ok && pct >= InpStopLoPct && pct <= InpStopHiPct && side_ok &&\n"
            "                 ArraySize(g_trades) < InpMaxOpenVirtual);",
            "      if(EventBlackout() && InpVerboseDiag)\n"
            "         Print(\"[CAL] signal blocked by event gate (next high-impact event within \", InpEventFilterHrs, \"h)\");\n"
            "      bool ok = (stop != 0.0 && gate_ok && pct >= InpStopLoPct && pct <= InpStopHiPct && side_ok &&\n"
            "                 ArraySize(g_trades) < InpMaxOpenVirtual && !EventBlackout());")

    assert text != orig
    path.write_text(text, encoding="utf-8")
    print(f"[OK] {path.name}: {n_checks} anchors replaced (hrs={hrs})")


for path, hrs, anchor in FILES:
    patch(path, hrs, anchor)
print("ALL PATCHED")

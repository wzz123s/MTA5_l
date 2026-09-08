# -*- coding: utf-8 -*-
"""币种白名单 USD/EUR/GBP/CAD 硬编码进三个 EA 的事件门（策略定义的一部分）。"""
from pathlib import Path

FILES = [
    Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5"),
    Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.mq5"),
    Path(r"F:\use_code\MTA5_l\原油\原油4H门策略\auto_trade\USOIL4H_Gate_On2H_EA.mq5"),
]

NEW_FUNC = """
//| 币种白名单（策略定义）：USD=直接计价 / EUR+GBP=USDX权重70% / CAD=油价货币 |
bool IsWhitelistedCurrency(const long country_id)
{
   MqlCalendarCountry ctry;
   if(!CalendarCountryById(country_id, ctry)) return false;
   return (ctry.currency == "USD" || ctry.currency == "EUR" ||
           ctry.currency == "GBP" || ctry.currency == "CAD");
}
"""

OLD_LINE = "      if(CalendarEventById(vals[i].event_id, ev) && ev.importance >= 3)"
NEW_LINE = "      if(CalendarEventById(vals[i].event_id, ev) && ev.importance >= 3\n         && IsWhitelistedCurrency(ev.country_id))"
OLD_ANCHOR = "bool EventBlackout()"
NEW_ANCHOR = NEW_FUNC + "\nbool EventBlackout()"

for p in FILES:
    t = p.read_text(encoding="utf-8")
    assert t.count(OLD_LINE) == 1, f"{p.name}: filter line x{t.count(OLD_LINE)}"
    assert t.count(OLD_ANCHOR) == 1, f"{p.name}: anchor x{t.count(OLD_ANCHOR)}"
    t = t.replace(OLD_LINE, NEW_LINE).replace(OLD_ANCHOR, NEW_ANCHOR)
    p.write_text(t, encoding="utf-8")
    print(f"[OK] {p.name}: 币种白名单已注入")
print("ALL DONE")

//+------------------------------------------------------------------+
//| ProbeCalendar2_EA.mq5                                              |
//+------------------------------------------------------------------+
#property strict

int OnInit()
  {
   MqlCalendarEvent e;
   MqlCalendarCountry c;
   int r1 = (int)e.id;             // CAND e.id
   string s1 = e.name;             // CAND e.name
   int r2 = (int)CalendarCountryById(0, c);   // CAND CalendarCountryById
   int r3 = (int)c.id;             // CAND c.id
   string s2 = c.name;             // CAND c.name
   string s3 = c.currency;         // CAND c.currency
   string s4 = c.url_name;         // CAND c.url_name
   string s5 = c.iso_code;         // CAND c.iso_code
   PrintFormat("probe2 %d %s %d %d %s %s %s %s", r1, s1, r2, r3, s2, s3, s4, s5);
   return INIT_FAILED;
  }
void OnTick() { }

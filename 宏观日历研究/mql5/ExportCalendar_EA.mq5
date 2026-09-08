//+------------------------------------------------------------------+
//| ExportCalendar_EA.mq5  v2 (OnTimer-driven, init-safe)            |
//| One-shot export of MT5 economic calendar values to MQL5\Files   |
//+------------------------------------------------------------------+
#property copyright "MTA5_l macro research"
#property version   "2.00"
#property strict

input datetime InpDateFrom = D'2019.01.01';
input datetime InpDateTo   = D'2027.01.01';
input int      InpChunkDays = 7;

string   g_out_file  = "calendar_export.csv";
string   g_done_file = "calendar_export_done.txt";
string   g_prog_file = "calendar_export_progress.txt";

int      g_handle    = INVALID_HANDLE;
long     g_rows      = 0;
datetime g_t         = 0;
datetime g_t_end     = 0;
int      g_state     = 0;   // 0=wait auth, 1=exporting, 2=finished
int      g_ticks     = 0;

string Safe(const string s)
  {
   string out = s;
   StringReplace(out, "|", "_");
   StringReplace(out, "\r", " ");
   StringReplace(out, "\n", " ");
   StringReplace(out, ";", "_");
   return out;
  }

bool WriteLine(const string line)
  {
   string full = line + "\r\n";
   uchar bytes[];
   int n = StringToCharArray(full, bytes, 0, WHOLE_ARRAY, CP_UTF8);
   if(n > 0 && bytes[n-1] == 0) n--;
   return (FileWriteArray(g_handle, bytes, 0, n) == n);
  }

bool WriteProgress(const string msg)
  {
   int h = FileOpen(g_prog_file, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return false;
   FileWrite(h, msg);
   FileClose(h);
   return true;
  }

void Finish()
  {
   if(g_handle != INVALID_HANDLE)
     {
      FileClose(g_handle);
      g_handle = INVALID_HANDLE;
     }
   int dh = FileOpen(g_done_file, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(dh != INVALID_HANDLE)
     {
      FileWrite(dh, "rows=" + IntegerToString(g_rows),
                "from=" + TimeToString(g_t_start()),
                "to=" + TimeToString(g_t_end));
      FileClose(dh);
     }
   EventKillTimer();
   g_state = 2;
   PrintFormat("ExportCalendar DONE rows=%I64d", g_rows);
  }

datetime g_start = 0;
datetime g_t_start()
  {
   if(g_start == 0) g_start = InpDateFrom;
   return g_start;
  }

void ProcessChunk()
  {
   datetime t2 = g_t + InpChunkDays * 86400;
   if(t2 > g_t_end) t2 = g_t_end;
   MqlCalendarValue vals[];
   int n = CalendarValueHistory(vals, g_t, t2);
   if(n < 0)
     {
      int err = GetLastError();
      PrintFormat("ExportCalendar chunk %s -> %s error %d", TimeToString(g_t), TimeToString(t2), err);
      WriteProgress(StringFormat("chunk %s..%s ERROR %d rows=%I64d", TimeToString(g_t), TimeToString(t2), err, g_rows));
     }
   else
     {
      for(int i = 0; i < n; i++)
        {
         MqlCalendarEvent ev;
         string evname = "";
         int evimp = 0, evsector = 0, evfreq = 0, evtmode = 0, evunit = 0;
         long evcountry = 0;
         if(CalendarEventById(vals[i].event_id, ev))
           {
            evname = ev.name;
            evimp = ev.importance;
            evsector = (int)ev.sector;
            evfreq = (int)ev.frequency;
            evtmode = (int)ev.time_mode;
            evunit = (int)ev.unit;
            evcountry = (long)ev.country_id;
           }
         string cname = "", ccur = "";
         if(evcountry > 0)
           {
            MqlCalendarCountry ctry;
            if(CalendarCountryById(evcountry, ctry))
              {
               cname = ctry.name;
               ccur = ctry.currency;
              }
           }
         string line = StringFormat("%I64d|%s|%d|%d|%I64d|%d|%d|%I64d|%I64d|%I64d|%I64d|%I64d|%d|%d|%d|%I64d|%d|%s|%s",
                                    (long)vals[i].event_id, Safe(evname), evimp,
                                    (int)vals[i].impact_type, (long)vals[i].time,
                                    vals[i].period, vals[i].revision,
                                    (long)vals[i].actual_value, (long)vals[i].forecast_value,
                                    (long)vals[i].prev_value, (long)vals[i].revised_prev_value,
                                    (long)vals[i].id, evsector, evfreq, evtmode,
                                    evcountry, evunit, Safe(cname), Safe(ccur));
         if(WriteLine(line)) g_rows++;
        }
      PrintFormat("ExportCalendar chunk %s -> %s : %d rows(total=%I64d)", TimeToString(g_t), TimeToString(t2), n, g_rows);
      WriteProgress(StringFormat("chunk %s..%s n=%d rows=%I64d", TimeToString(g_t), TimeToString(t2), n, g_rows));
     }
   g_t = t2;
   if(g_t >= g_t_end) Finish();
  }

int OnInit()
  {
   g_handle = FileOpen(g_out_file, FILE_WRITE | FILE_BIN);
   if(g_handle == INVALID_HANDLE)
     {
      PrintFormat("ExportCalendar: cannot open output, error=%d", GetLastError());
      return INIT_FAILED;
     }
   uchar bom[] = {0xEF, 0xBB, 0xBF};
   FileWriteArray(g_handle, bom, 0, 3);
   WriteLine("event_id|event_name|importance|impact_type|time|period|revision|actual|forecast|prev|revised_prev|value_id|sector|frequency|time_mode|country_id|unit|country|currency");
   g_t = InpDateFrom;
   g_t_end = InpDateTo;
   g_state = 0;
   EventSetTimer(2);
   PrintFormat("ExportCalendar v2 started %s -> %s", TimeToString(InpDateFrom), TimeToString(InpDateTo));
   return INIT_SUCCEEDED;
  }

void OnTimer()
  {
   if(g_state == 2) return;
   if(g_state == 0)
     {
      if(TerminalInfoInteger(TERMINAL_CONNECTED) == 0) return;
      if(AccountInfoInteger(ACCOUNT_LOGIN) == 0) return;
      g_state = 1;
      WriteProgress("authorized, starting export");
      PrintFormat("ExportCalendar authorized, start export");
      return;
     }
   g_ticks++;
   if(g_ticks % 2 == 0) ProcessChunk();   // 4s cadence between chunks
  }

void OnTick() { }
void OnDeinit(const int reason) { }

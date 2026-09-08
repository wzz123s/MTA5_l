//+------------------------------------------------------------------+
//| DownloadUSOILHistory_EA.mq5                                      |
//|  Temporary EA: force MT5 to download full USOILm history         |
//|  (M1 / M30 / H2) into the terminal cache.                        |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "1.00"
#property strict

input string InpSymbol = "USOILm";   // Symbol
input int    InpChunkDays = 30;      // M1 chunk size in days

datetime g_last = 0;
bool     g_done = false;

int OnInit()
{
   g_last = 0;
   g_done = false;
   EventSetTimer(5);
   Print("[DL] DownloadUSOILHistory_EA started, symbol=", InpSymbol);
   return INIT_SUCCEEDED;
}

void OnTimer()
{
   datetime now = TimeCurrent();
   if(g_done) return;

   MqlRates rates[];
   int n = 0;

   // H2: request up to 100k bars (full history)
   n = CopyRates(InpSymbol, PERIOD_H2, 0, 100000, rates);
   Print("[DL] H2 bars=", n,
         (n > 0 ? " oldest=" + TimeToString(rates[ArraySize(rates) - 1].time) : ""));

   // M30: full
   n = CopyRates(InpSymbol, PERIOD_M30, 0, 100000, rates);
   Print("[DL] M30 bars=", n,
         (n > 0 ? " oldest=" + TimeToString(rates[ArraySize(rates) - 1].time) : ""));

   // M1: chunked walk from 2019.01.01 to now
   datetime from = D'2019.01.01';
   datetime to   = now;
   int total = 0, chunks = 0;
   while(from < to && chunks < 200)
   {
      datetime seg_from = from;
      datetime seg_to   = (from + InpChunkDays * 86400 > to) ? to : from + InpChunkDays * 86400;
      int c = CopyRates(InpSymbol, PERIOD_M1, seg_from, seg_to, rates);
      if(c <= 0)
      {
         Print("[DL] M1 chunk failed at ", TimeToString(seg_from));
         break;
      }
      total += c;
      chunks++;
      datetime oldest = rates[0].time;
      datetime newest = rates[ArraySize(rates) - 1].time;
      if(chunks <= 3 || chunks % 20 == 0)
         Print("[DL] M1 chunk ", chunks, ": ", c, " bars [", TimeToString(oldest),
               " .. ", TimeToString(newest), "] total=", total);
      if(oldest <= from) break;
      from = oldest;
   }
   Print("[DL] M1 chunks=", chunks, " total bars=", total);

   g_done = true;
   EventKillTimer();
   Print("[DL] download pass finished");
}

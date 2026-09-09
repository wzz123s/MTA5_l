//+------------------------------------------------------------------+
//|                                     2H_M30_6H_CurrentCandidate_EA.mq5 |
//|                         2H_M30_6H Current Candidate EA           |
//|                    Python-aligned: basic M30 cross + 6H bias gates|
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "1.19"
#property strict

#include <Trade/Trade.mqh>

input group "=== Account ==="
input ulong   InpMagic      = 322026;
input string  InpSymbol     = "XAUUSDm";

input group "=== Candidate Parameters ==="
input double  InpLots                    = 0.01;       // Base lot size
input double  InpStopLoPt                = 2.0;        // Min stop distance (points)
input double  InpStopHiPt                = 10.0;       // Max stop distance (points)
input double  InpBias5MinPct             = 0.0;        // 6H bias5 signed > this (default 0)
input double  InpBias13MinPct            = 0.0;        // 6 H bias13 signed > this (default 0)
input double  InpBias55MinPct            = 0.0;        // 6H bias55 signed > this (default 0)

input group "=== Timeframes ==="
input ENUM_TIMEFRAMES InpM30Period = PERIOD_M30;      // Signal timeframe
input ENUM_TIMEFRAMES InpH2Period  = PERIOD_H2;       // Medium timeframe (for future use)
input ENUM_TIMEFRAMES InpH6Period  = PERIOD_H6;       // Bias gate timeframe

input group "=== Runtime ==="
input bool    InpSimMode       = true;                // true=virtual ledger only
input bool    InpAllowRealTrading = false;            // Safety switch for live trading
input bool    InpExportLedger  = true;
input string  InpLedgerFile    = "2H_M30_6H_current_candidate_trade_ledger.csv";
input int     InpHistoryBarsM30 = 2500;
input int     InpHistoryBarsH2  = 1500;
input int     InpHistoryBarsH6  = 800;
input string  InpHistoryStartUtc = "2024.01.01 23:00";  // research raw window start (UTC wall time)
input int     InpCheckSec       = 1;
input ulong   InpSlippage       = 30;

input group "=== Live Guards ==="
input int     InpMaxOpenPositions     = 1;
input double  InpMaxSpreadPricePt     = 0.80;
input double  InpMaxRiskUsd           = 30.0;
input double  InpMinFreeMarginAfterTradeUsd = 100.0;

const int DIR_BUY  = 1;
const int DIR_SELL = -1;

//--- Indicator handles (created in OnInit)
struct VirtualTrade
{
   bool     active;
   int      dir;
   datetime signal_time;
   datetime entry_time;
   double   entry;
   double   stop;
   double   stop_distance;
   int      holding_bars;
   double   h6_bias5_signed_pct;
   double   h6_bias13_signed_pct;
   double   h6_bias55_signed_pct;
};

CTrade g_trade;
datetime g_last_m30_open = 0;
datetime g_last_check = 0;
int g_ledger_handle = INVALID_HANDLE;
int g_trade_seq = 0;
VirtualTrade g_vt;

//+------------------------------------------------------------------+
//| Helper: get MA value at shift                                    |
//+------------------------------------------------------------------+
double GetMAVal(int handle, int shift)
{
   if(handle == INVALID_HANDLE)
      return 0.0;
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(handle, 0, shift, 1, buf) <= 0)
      return 0.0;
   return buf[0];
}

string Dt(datetime value)
{
   return TimeToString(value, TIME_DATE | TIME_SECONDS);
}

int TfSeconds(ENUM_TIMEFRAMES tf)
{
   return (int)PeriodSeconds(tf);
}

double BiasSigned(double price, double sma, int dir)
{
   if(dir == DIR_BUY)
      return (price - sma) / sma * 100.0;
   else
      return (sma - price) / sma * 100.0;
}

double SMMAClose(const double &closes[], int count, int period)
{
   if(count < period)
      return EMPTY_VALUE;
   double sum = 0.0;
   for(int i = 0; i < period; i++)
      sum += closes[i];
   double sma = sum / period;
   for(int i = period; i < count; i++)
      sma = (closes[i] + (period - 1) * sma) / period;
   return sma;
}

void CalcSMMAArray(const double &closes[], int n, int period, double &out[])
{
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = EMPTY_VALUE;
   if(n < period)
      return;
   double sum = 0.0;
   for(int i = 0; i < period; i++)
      sum += closes[i];
   out[period - 1] = sum / period;
   for(int i = period; i < n; i++)
      out[i] = (closes[i] + (period - 1) * out[i - 1]) / period;
}

bool CheckSpreadOK()
{
   double spread = SymbolInfoInteger(InpSymbol, SYMBOL_SPREAD) * _Point;
   double maxSpread = InpMaxSpreadPricePt;
   return (spread <= maxSpread);
}

int InitLedger()
{
   if(!InpExportLedger)
      return INVALID_HANDLE;

   string fileName = InpLedgerFile;
   g_ledger_handle = FileOpen(fileName, FILE_CSV | FILE_WRITE | FILE_ANSI | FILE_SHARE_READ, ',');
   if(g_ledger_handle == INVALID_HANDLE)
   {
      Print("Failed to open ledger file: ", fileName);
      return INVALID_HANDLE;
   }

   FileWrite(g_ledger_handle,
      "seq",
      "signal_time",
      "dir",
      "entry_time",
      "entry",
      "stop",
      "stop_distance_pt",
      "exit_time",
      "exit",
      "exit_reason",
      "pnl_points",
      "pnl_usd_001",
      "holding_bars",
      "h6_bias5_pct",
      "h6_bias13_pct",
      "h6_bias55_pct"
   );

   return g_ledger_handle;
}

void CloseLedger()
{
   if(g_ledger_handle != INVALID_HANDLE)
   {
      FileClose(g_ledger_handle);
      g_ledger_handle = INVALID_HANDLE;
   }
}

void WriteLedgerEntry(VirtualTrade &vt, string exitReason, double exitPrice, datetime exitTime)
{
   if(g_ledger_handle == INVALID_HANDLE)
      return;

   double pnlPoints = 0;
   if(vt.dir == DIR_BUY)
      pnlPoints = exitPrice - vt.entry;
   else
      pnlPoints = vt.entry - exitPrice;

   double pnlUsd = pnlPoints * 100.0 * 0.01;

   g_trade_seq++;

   FileWrite(g_ledger_handle,
      IntegerToString(g_trade_seq),
      Dt(vt.signal_time),
      vt.dir == DIR_BUY ? "BUY" : "SELL",
      Dt(vt.entry_time),
      DoubleToString(vt.entry, 3),
      DoubleToString(vt.stop, 3),
      DoubleToString(vt.stop_distance, 3),
      Dt(exitTime),
      DoubleToString(exitPrice, 3),
      exitReason,
      DoubleToString(pnlPoints, 3),
      DoubleToString(pnlUsd, 3),
      IntegerToString(vt.holding_bars),
      DoubleToString(vt.h6_bias5_signed_pct, 4),
      DoubleToString(vt.h6_bias13_signed_pct, 4),
      DoubleToString(vt.h6_bias55_signed_pct, 4)
   );

   FileFlush(g_ledger_handle);
}

double FindStructuralStop(int dir, const double &sma5[], const double &sma13[], int signalIdx)
{
   // Python research: stop = min/max of SMA13 over the segment between the
   // previous cross bar (inclusive) and the signal bar (exclusive).
   int prevCrossShift = -1;
   for(int i = signalIdx - 1; i >= 1; i--)
   {
      double s5o = sma5[i - 1];
      double s13o = sma13[i - 1];
      double s5n = sma5[i];
      double s13n = sma13[i];
      if(s5o <= 0 || s13o <= 0 || s5n <= 0 || s13n <= 0)
         continue;
      if((s5o > s13o && s5n <= s13n) || (s5o < s13o && s5n >= s13n))
      {
         prevCrossShift = i;
         break;
      }
   }
   if(prevCrossShift < 0)
      return 0.0;

   double extreme = 0.0;
   bool first = true;
   for(int i = prevCrossShift; i < signalIdx; i++)
   {
      double value = sma13[i];
      if(value <= 0)
         continue;
      if(first)
      {
         extreme = value;
         first = false;
      }
      else if(dir == DIR_BUY)
         extreme = MathMin(extreme, value);
      else
         extreme = MathMax(extreme, value);
   }
   if(first)
      return 0.0;
   return extreme;
}

bool CheckBiasGates(int dir, double &out_bias5, double &out_bias13, double &out_bias55, double &out_close6, datetime entryTime)
{
   MqlRates m30[];
   ArrayFree(m30);
   ArraySetAsSeries(m30, false);
   long utcOffset = (long)(TimeCurrent() - TimeGMT());
   datetime startServer = StringToTime(InpHistoryStartUtc) + (datetime)utcOffset;
   int n = CopyRates(InpSymbol, InpM30Period, startServer, entryTime + 1, m30);
   ArraySetAsSeries(m30, false);
   if(n < 12)
      return false;

   // Python research resamples M30 with label="right", closed="right" in UTC:
   // the H6 bar labeled L includes the M30 bar at time L (UTC), and is used
   // for any signal bar with open time in [L, L+6h).
   long h6Secs = 21600;
   long firstUtc = (long)m30[0].time - utcOffset;
   long entryUtc = (long)entryTime - utcOffset;
   long firstBoundary = (long)((double)firstUtc / (double)h6Secs) * h6Secs;
   if(firstBoundary < firstUtc)
      firstBoundary += h6Secs;

   double closes[];
   int count = 0;
   for(long L = firstBoundary; L <= entryUtc; L += h6Secs)
   {
      datetime boundaryServer = (datetime)(L + utcOffset);
      int idxLast = -1;
      for(int i = 0; i < n; i++)
      {
         if((long)m30[i].time <= (long)boundaryServer)
            idxLast = i;
         else
            break;
      }
      if(idxLast < 0)
         continue;
      long bucketStart = L - h6Secs;
      if((long)m30[idxLast].time <= bucketStart)
         continue;  // empty 6h bucket; pandas resample drops it
      ArrayResize(closes, count + 1);
      closes[count] = m30[idxLast].close;
      count++;
   }
   if(count < 55)
      return false;

   double sma5 = SMMAClose(closes, count, 5);
   double sma13 = SMMAClose(closes, count, 13);
   double sma55 = SMMAClose(closes, count, 55);
   if(sma5 <= 0 || sma13 <= 0 || sma55 <= 0)
      return false;

   out_close6 = closes[count - 1];
   out_bias5 = BiasSigned(out_close6, sma5, dir);
   out_bias13 = BiasSigned(out_close6, sma13, dir);
   out_bias55 = BiasSigned(out_close6, sma55, dir);

   if(out_bias5 < InpBias5MinPct || out_bias13 < InpBias13MinPct || out_bias55 < InpBias55MinPct)
      return false;
   return true;
}

void CheckForSignal()
{
   if(g_vt.active)
      return;

   MqlRates m30[];
   ArrayFree(m30);
   ArraySetAsSeries(m30, false);
   int n = CopyRates(InpSymbol, InpM30Period, 0, InpHistoryBarsM30, m30);
   ArraySetAsSeries(m30, false);
   if(n < 120)
      return;

   double closes[];
   ArrayResize(closes, n);
   for(int i = 0; i < n; i++)
      closes[i] = m30[i].close;
   double sma5[], sma13[];
   CalcSMMAArray(closes, n, 5, sma5);
   CalcSMMAArray(closes, n, 13, sma13);

   int signalIdx = n - 2;
   if(signalIdx < 3)
      return;

   int crossDir = 0;
   if(sma5[signalIdx - 1] > sma13[signalIdx - 1] && sma5[signalIdx] <= sma13[signalIdx])
      crossDir = DIR_SELL;
   else if(sma5[signalIdx - 1] < sma13[signalIdx - 1] && sma5[signalIdx] >= sma13[signalIdx])
      crossDir = DIR_BUY;

   if(crossDir == 0)
      return;

   datetime signalBarTime = m30[signalIdx].time;
   double entryPrice = (m30[signalIdx].high + m30[signalIdx].low + m30[signalIdx].close) / 3.0;
   double stopPrice = FindStructuralStop(crossDir, sma5, sma13, signalIdx);
   if(stopPrice <= 0)
      return;
   double stopDistance = MathAbs(entryPrice - stopPrice);
   if(stopDistance < InpStopLoPt || stopDistance > InpStopHiPt)
      return;

   double bias5 = 0, bias13 = 0, bias55 = 0;
   double close6 = 0.0;
   bool biasPass = CheckBiasGates(crossDir, bias5, bias13, bias55, close6, signalBarTime);
   if(!biasPass)
      return;

   if(!CheckSpreadOK())
      return;

   g_vt.active = true;
   g_vt.dir = crossDir;
   g_vt.signal_time = signalBarTime;
   g_vt.entry_time = signalBarTime;
   g_vt.entry = entryPrice;
   g_vt.stop = stopPrice;
   g_vt.stop_distance = stopDistance;
   g_vt.holding_bars = 0;
   g_vt.h6_bias5_signed_pct = bias5;
   g_vt.h6_bias13_signed_pct = bias13;
   g_vt.h6_bias55_signed_pct = bias55;

   Print("Virtual trade opened: ", crossDir == DIR_BUY ? "BUY" : "SELL",
         " @ ", DoubleToString(entryPrice, 2),
         " SL @ ", DoubleToString(stopPrice, 2),
         " Dist=", DoubleToString(g_vt.stop_distance, 1), "pt",
         " B5=", DoubleToString(bias5, 2),
         " B13=", DoubleToString(bias13, 2),
         " B55=", DoubleToString(bias55, 2));
}

void CheckForExit()
{
   if(!g_vt.active)
      return;

   MqlRates m30[];
   ArrayFree(m30);
   ArraySetAsSeries(m30, false);
   int n = CopyRates(InpSymbol, InpM30Period, 0, InpHistoryBarsM30, m30);
   ArraySetAsSeries(m30, false);
   if(n < 120)
      return;

   double closes[];
   ArrayResize(closes, n);
   for(int i = 0; i < n; i++)
      closes[i] = m30[i].close;
   double sma5[], sma13[];
   CalcSMMAArray(closes, n, 5, sma5);
   CalcSMMAArray(closes, n, 13, sma13);

   int signalIdx = n - 2;
   if(signalIdx < 3)
      return;

   bool oppositeCross = false;
   if(g_vt.dir == DIR_BUY && sma5[signalIdx - 1] > sma13[signalIdx - 1] && sma5[signalIdx] <= sma13[signalIdx])
      oppositeCross = true;
   else if(g_vt.dir == DIR_SELL && sma5[signalIdx - 1] < sma13[signalIdx - 1] && sma5[signalIdx] >= sma13[signalIdx])
      oppositeCross = true;

   if(oppositeCross)
   {
      double closePrice = m30[signalIdx].close;
      datetime exitBarTime = m30[signalIdx].time;
      WriteLedgerEntry(g_vt, "OPPOSITE_CROSS", closePrice, exitBarTime);
      g_vt.active = false;
      return;
   }

   g_vt.holding_bars++;
}

int OnInit()
{
   Print("2H_M30_6H Current Candidate EA v1.19 initialized (SMMA from bars)");

   Print("Mode: SimMode=", InpSimMode, " AllowRealTrading=", InpAllowRealTrading);
   Print("Parameters: StopRange=[", InpStopLoPt, "-", InpStopHiPt, "]pt",
         " Bias5>=", InpBias5MinPct,
         " Bias13>=", InpBias13MinPct,
         " Bias55>=", InpBias55MinPct);

   InitLedger();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   Print("2H_M30_6H EA deinitialized. Reason: ", reason);

   CloseLedger();
}

void OnTick()
{
   datetime now = TimeCurrent();
   if(now - g_last_check < InpCheckSec)
      return;

   g_last_check = now;

   datetime current_open = iTime(InpSymbol, InpM30Period, 0);
   if(current_open == 0 || current_open == g_last_m30_open)
      return;
   g_last_m30_open = current_open;

   CheckForExit();
   CheckForSignal();
}

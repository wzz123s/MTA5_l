//+------------------------------------------------------------------+
//|                         1H_M30_4H_CurrentCandidate_EA.mq5        |
//|                         Current candidate alignment/sim EA       |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "=== Account ==="
input ulong   InpMagic      = 312026;
input string  InpSymbol     = "XAUUSDm";

input group "=== Candidate ==="
input double  InpLots                    = 0.01;
input double  InpStopLoPt                = 8.0;
input double  InpStopHiPt                = 28.0;
input double  InpSideExtremeThresholdPct = 2.0;
input double  InpCloseMomentumMinPct     = -0.4;
input double  InpShortVolWayMax          = 0.7;
input int     InpH1StopLookback          = 6;
input int     InpWayMergeMinLen          = 8;

input group "=== Timeframes ==="
input ENUM_TIMEFRAMES InpM30Period = PERIOD_M30;
input ENUM_TIMEFRAMES InpH1Period  = PERIOD_H1;
input ENUM_TIMEFRAMES InpH4Period  = PERIOD_H4;

input group "=== Runtime ==="
input bool    InpSimMode       = true;   // true=virtual ledger only; false=also place/close one live/tester position
input bool    InpAllowRealTrading = false; // second confirmation for placing live/tester orders
input bool    InpExportLedger  = true;
input string  InpLedgerFile    = "1H_M30_4H_current_candidate_trade_ledger.csv";
input int     InpHistoryBarsM30 = 2500;
input int     InpHistoryBarsH1  = 2500;
input int     InpHistoryBarsH4  = 900;
input int     InpCheckSec       = 1;
input ulong   InpSlippage       = 30;

input group "=== Live Guards ==="
input int     InpMaxOpenPositions             = 1;
input double  InpMaxSpreadPricePt             = 0.80;
input double  InpMaxRiskUsd                   = 30.0;
input double  InpMinFreeMarginAfterTradeUsd   = 100.0;

const int DIR_BUY  = 1;
const int DIR_SELL = -1;
const int WAY_UP   = 1;
const int WAY_DOWN = -1;
const int WAY_GOOD = 2;
const int WAY_BAD  = -2;

struct FeaturePack
{
   string   side_extreme_kind;
   datetime side_extreme_time;
   double   side_extreme_price;
   double   side_extreme_bias55_h4sma_pct;
   double   side_extreme_way_s_way;
   double   side_extreme_vol_way_s_way;
   double   side_extreme_close_momentum_signed_pct;
   double   side_extreme_body_momentum_signed;
   double   h1_bias5_signed_pct;
   double   h1_bias13_signed_pct;
   double   structural_stop;
   double   stop_distance;
};

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
   string   side_extreme_kind;
   datetime side_extreme_time;
   double   side_extreme_bias55_h4sma_pct;
   double   side_extreme_way_s_way;
   double   side_extreme_vol_way_s_way;
   double   side_extreme_close_momentum_signed_pct;
   double   side_extreme_body_momentum_signed;
};

CTrade g_trade;
datetime g_last_m30_open = 0;
datetime g_last_check = 0;
int g_ledger_handle = INVALID_HANDLE;
int g_trade_seq = 0;
VirtualTrade g_vt;

string Dt(datetime value)
{
   return TimeToString(value, TIME_DATE | TIME_SECONDS);
}

string DirText(int dir)
{
   return (dir == DIR_BUY ? "BUY" : "SELL");
}

double Round3(double value)
{
   return NormalizeDouble(value, 3);
}

bool IsValid(double value)
{
   return value != EMPTY_VALUE && MathIsValidNumber(value);
}

int TfSeconds(ENUM_TIMEFRAMES tf)
{
   return (int)PeriodSeconds(tf);
}

int CopyTfRates(ENUM_TIMEFRAMES tf, int count, MqlRates &rates[])
{
   ArrayFree(rates);
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(InpSymbol, tf, 0, count, rates);
   ArraySetAsSeries(rates, false);
   return copied;
}

int LastClosedIndex(MqlRates &rates[], int n, ENUM_TIMEFRAMES tf, datetime at_time)
{
   int secs = TfSeconds(tf);
   int best = -1;
   for(int i = 0; i < n; i++)
   {
      if(rates[i].time + secs <= at_time)
         best = i;
      else
         break;
   }
   return best;
}

bool CalcSMMA(MqlRates &rates[], int n, int period, double &out[])
{
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = EMPTY_VALUE;
   if(n < period)
      return false;

   double sum = 0.0;
   for(int i = 0; i < period; i++)
      sum += rates[i].close;
   out[period - 1] = sum / period;
   for(int i = period; i < n; i++)
      out[i] = (rates[i].close + (period - 1) * out[i - 1]) / period;
   return true;
}

double BiasPct(double price, double smma)
{
   if(!IsValid(smma) || MathAbs(smma) < 1e-12)
      return EMPTY_VALUE;
   return (price - smma) / smma * 100.0;
}

void RemoveCrossing(int &pos[], int &typ[], int &count, int index)
{
   if(index < 0 || index >= count)
      return;
   for(int i = index; i < count - 1; i++)
   {
      pos[i] = pos[i + 1];
      typ[i] = typ[i + 1];
   }
   count--;
}

void CalcWayFeatures(
   MqlRates &h1[],
   int n,
   double &sma5[],
   double &sma13[],
   int min_len,
   double &way_s_way[],
   double &vol_way_s_way[],
   double &body_momentum[],
   double &close_momentum_pct[],
   double &sma13_gap_momentum_pct[]
)
{
   ArrayResize(way_s_way, n);
   ArrayResize(vol_way_s_way, n);
   ArrayResize(body_momentum, n);
   ArrayResize(close_momentum_pct, n);
   ArrayResize(sma13_gap_momentum_pct, n);
   int direction[];
   int merged[];
   ArrayResize(direction, n);
   ArrayResize(merged, n);

   for(int i = 0; i < n; i++)
   {
      way_s_way[i] = 0.0;
      vol_way_s_way[i] = 0.0;
      body_momentum[i] = EMPTY_VALUE;
      close_momentum_pct[i] = EMPTY_VALUE;
      sma13_gap_momentum_pct[i] = EMPTY_VALUE;
      direction[i] = 0;
      merged[i] = 0;

      double range = h1[i].high - h1[i].low;
      if(range > 0)
         body_momentum[i] = (h1[i].close - h1[i].open) / range;
      if(i > 0 && MathAbs(h1[i - 1].close) > 1e-12)
         close_momentum_pct[i] = (h1[i].close / h1[i - 1].close - 1.0) * 100.0;
      if(i > 0 && IsValid(sma13[i]) && MathAbs(sma13[i]) > 1e-12 && IsValid(sma13[i - 1]))
      {
         double gap_now = h1[i].close - sma13[i];
         double gap_prev = h1[i - 1].close - sma13[i - 1];
         sma13_gap_momentum_pct[i] = (gap_now - gap_prev) / sma13[i] * 100.0;
      }
   }

   bool have_prev = false;
   bool prev_gt = false;
   for(int i = 0; i < n; i++)
   {
      if(!IsValid(sma5[i]) || !IsValid(sma13[i]))
         continue;
      bool gt = sma5[i] > sma13[i];
      if(!have_prev)
      {
         direction[i] = (gt ? WAY_UP : WAY_DOWN);
         have_prev = true;
         prev_gt = gt;
         continue;
      }
      if(gt && !prev_gt)
         direction[i] = WAY_GOOD;
      else if(!gt && prev_gt)
         direction[i] = WAY_BAD;
      else if(gt && prev_gt)
         direction[i] = WAY_UP;
      else
         direction[i] = WAY_DOWN;
      prev_gt = gt;
   }

   for(int i = 0; i < n; i++)
      merged[i] = direction[i];

   int cross_pos[];
   int cross_typ[];
   ArrayResize(cross_pos, n);
   ArrayResize(cross_typ, n);
   int cross_count = 0;
   for(int i = 0; i < n; i++)
   {
      if(merged[i] == WAY_GOOD || merged[i] == WAY_BAD)
      {
         cross_pos[cross_count] = i;
         cross_typ[cross_count] = merged[i];
         cross_count++;
      }
   }

   if(cross_count > 0)
   {
      int state = (cross_typ[0] == WAY_GOOD ? WAY_DOWN : WAY_UP);
      int i = 0;
      while(i < cross_count)
      {
         int pos = cross_pos[i];
         int typ = cross_typ[i];
         if(i + 1 >= cross_count)
            break;
         int next_pos = cross_pos[i + 1];
         int target = (typ == WAY_GOOD ? WAY_UP : WAY_DOWN);
         int region_count = 0;
         for(int k = pos + 1; k < next_pos; k++)
            if(merged[k] == target)
               region_count++;
         if(region_count < min_len)
         {
            merged[pos] = state;
            for(int k = pos + 1; k < next_pos; k++)
               merged[k] = state;
            merged[next_pos] = state;
            RemoveCrossing(cross_pos, cross_typ, cross_count, i + 1);
            RemoveCrossing(cross_pos, cross_typ, cross_count, i);
         }
         else
         {
            state = (typ == WAY_GOOD ? WAY_UP : WAY_DOWN);
            i++;
         }
      }
   }

   double vol_ma[];
   ArrayResize(vol_ma, n);
   for(int i = 0; i < n; i++)
   {
      int start = MathMax(0, i - 119);
      double sum = 0.0;
      int cnt = 0;
      for(int k = start; k <= i; k++)
      {
         sum += (double)h1[k].tick_volume;
         cnt++;
      }
      vol_ma[i] = (cnt > 0 ? sum / cnt : 0.0);
   }

   int y = 0;
   int x = 0;
   int z = 0;
   int prev_d = 0;
   for(int i = 0; i < n; i++)
   {
      int d = merged[i];
      double wsw = 0.0;
      double vwsw = 0.0;
      if(d == WAY_GOOD || d == WAY_BAD)
      {
         y = 0;
         x = 0;
         z = 0;
      }
      else if(d == WAY_UP)
      {
         if(prev_d == WAY_UP)
         {
            y++;
            if(IsValid(sma13[i]) && i > 0 && h1[i].low >= sma13[i] && h1[i].high >= h1[i - 1].high)
               x++;
            if((double)h1[i].tick_volume <= vol_ma[i])
               z++;
         }
         else
         {
            y = 1;
            x = 1;
            z = ((double)h1[i].tick_volume <= vol_ma[i] ? 1 : 0);
         }
         if(y != 0)
         {
            wsw = (double)x / (double)y;
            vwsw = (double)z / (double)y;
         }
      }
      else if(d == WAY_DOWN)
      {
         if(prev_d == WAY_DOWN)
         {
            y--;
            if(IsValid(sma13[i]) && i > 0 && h1[i].high <= sma13[i] && h1[i].low <= h1[i - 1].low)
               x--;
            if((double)h1[i].tick_volume <= vol_ma[i])
               z--;
         }
         else
         {
            y = -1;
            x = -1;
            z = ((double)h1[i].tick_volume <= vol_ma[i] ? -1 : 0);
         }
         if(y != 0)
         {
            wsw = (double)x / (double)y;
            vwsw = (double)z / (double)y;
         }
      }
      way_s_way[i] = NormalizeDouble(wsw, 2);
      vol_way_s_way[i] = NormalizeDouble(vwsw, 2);
      prev_d = d;
   }
}

int CrossSide(MqlRates &m30[], int n, int signal_idx, double &sma5[], double &sma13[])
{
   if(signal_idx <= 0 || signal_idx >= n)
      return 0;
   if(!IsValid(sma5[signal_idx]) || !IsValid(sma13[signal_idx]) ||
      !IsValid(sma5[signal_idx - 1]) || !IsValid(sma13[signal_idx - 1]))
      return 0;
   int prev_dir = (sma5[signal_idx - 1] > sma13[signal_idx - 1] ? DIR_BUY : DIR_SELL);
   int cur_dir = (sma5[signal_idx] > sma13[signal_idx] ? DIR_BUY : DIR_SELL);
   if(cur_dir > 0 && prev_dir <= 0)
      return DIR_BUY;
   if(cur_dir < 0 && prev_dir >= 0)
      return DIR_SELL;
   return 0;
}

bool BuildFeatures(int side, datetime entry_time, double entry, FeaturePack &fp)
{
   MqlRates h1[];
   MqlRates h4[];
   int n1 = CopyTfRates(InpH1Period, InpHistoryBarsH1, h1);
   int n4 = CopyTfRates(InpH4Period, InpHistoryBarsH4, h4);
   if(n1 < 60 || n4 < 60)
      return false;

   int h1_idx = LastClosedIndex(h1, n1, InpH1Period, entry_time);
   int h4_idx = LastClosedIndex(h4, n4, InpH4Period, entry_time);
   if(h1_idx < 54 || h4_idx < 54)
      return false;

   double h1_sma5[], h1_sma13[], h1_sma55[];
   double h4_sma55[];
   CalcSMMA(h1, n1, 5, h1_sma5);
   CalcSMMA(h1, n1, 13, h1_sma13);
   CalcSMMA(h1, n1, 55, h1_sma55);
   CalcSMMA(h4, n4, 55, h4_sma55);
   if(!IsValid(h1_sma5[h1_idx]) || !IsValid(h1_sma13[h1_idx]) || !IsValid(h4_sma55[h4_idx]))
      return false;

   double sign = (side == DIR_BUY ? 1.0 : -1.0);
   fp.h1_bias5_signed_pct = BiasPct(h1[h1_idx].close, h1_sma5[h1_idx]) * sign;
   fp.h1_bias13_signed_pct = BiasPct(h1[h1_idx].close, h1_sma13[h1_idx]) * sign;
   if(!(fp.h1_bias5_signed_pct > 0.0 && fp.h1_bias13_signed_pct > 0.0))
      return false;

   int stop_start = MathMax(0, h1_idx - InpH1StopLookback + 1);
   if(side == DIR_BUY)
   {
      fp.structural_stop = h1[stop_start].low;
      for(int i = stop_start + 1; i <= h1_idx; i++)
         fp.structural_stop = MathMin(fp.structural_stop, h1[i].low);
      fp.stop_distance = entry - fp.structural_stop;
   }
   else
   {
      fp.structural_stop = h1[stop_start].high;
      for(int i = stop_start + 1; i <= h1_idx; i++)
         fp.structural_stop = MathMax(fp.structural_stop, h1[i].high);
      fp.stop_distance = fp.structural_stop - entry;
   }
   if(!(fp.stop_distance >= InpStopLoPt && fp.stop_distance <= InpStopHiPt))
      return false;

   double way_s_way[], vol_way_s_way[], body_momentum[], close_mom[], gap_mom[];
   CalcWayFeatures(h1, n1, h1_sma5, h1_sma13, InpWayMergeMinLen, way_s_way, vol_way_s_way, body_momentum, close_mom, gap_mom);

   int extreme_start = MathMax(0, h1_idx - 3);
   int extreme_idx = extreme_start;
   if(side == DIR_SELL)
   {
      for(int i = extreme_start + 1; i <= h1_idx; i++)
         if(h1[i].high > h1[extreme_idx].high)
            extreme_idx = i;
      fp.side_extreme_kind = "high";
      fp.side_extreme_price = h1[extreme_idx].high;
   }
   else
   {
      for(int i = extreme_start + 1; i <= h1_idx; i++)
         if(h1[i].low < h1[extreme_idx].low)
            extreme_idx = i;
      fp.side_extreme_kind = "low";
      fp.side_extreme_price = h1[extreme_idx].low;
   }

   fp.side_extreme_time = h1[extreme_idx].time + TfSeconds(InpH1Period);
   fp.side_extreme_bias55_h4sma_pct = BiasPct(fp.side_extreme_price, h4_sma55[h4_idx]);
   if(side == DIR_SELL)
   {
      if(!(fp.side_extreme_bias55_h4sma_pct >= InpSideExtremeThresholdPct))
         return false;
   }
   else
   {
      if(!(fp.side_extreme_bias55_h4sma_pct <= -InpSideExtremeThresholdPct))
         return false;
   }

   fp.side_extreme_way_s_way = way_s_way[extreme_idx];
   fp.side_extreme_vol_way_s_way = vol_way_s_way[extreme_idx];
   fp.side_extreme_close_momentum_signed_pct = close_mom[extreme_idx] * sign;
   fp.side_extreme_body_momentum_signed = body_momentum[extreme_idx] * sign;
   if(!(fp.side_extreme_close_momentum_signed_pct >= InpCloseMomentumMinPct))
      return false;
   if(side == DIR_SELL && !(fp.side_extreme_vol_way_s_way <= InpShortVolWayMax))
      return false;
   return true;
}

bool OpenLedger()
{
   if(!InpExportLedger)
      return true;
   g_ledger_handle = FileOpen(InpLedgerFile, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
   if(g_ledger_handle == INVALID_HANDLE)
   {
      Print("Cannot open ledger file: ", InpLedgerFile, " err=", GetLastError());
      return false;
   }
   FileWrite(g_ledger_handle,
      "trade_seq", "trade_key", "candidate_name", "signal_time", "entry_time", "dir",
      "entry", "stop", "exit_time", "exit", "exit_reason", "pnl_points",
      "entry_rule", "entry_delay_bars", "stop_variant", "stop_distance",
      "side_extreme_kind", "side_extreme_time", "side_extreme_bias55_h4sma_pct",
      "side_extreme_way_s_way", "side_extreme_vol_way_s_way",
      "side_extreme_close_momentum_signed_pct", "side_extreme_body_momentum_signed");
   FileFlush(g_ledger_handle);
   return true;
}

void WriteLedger(double exit_price, datetime exit_time, string reason)
{
   if(!g_vt.active)
      return;
   g_trade_seq++;
   double pnl = (g_vt.dir == DIR_BUY ? exit_price - g_vt.entry : g_vt.entry - exit_price);
   string dir_text = DirText(g_vt.dir);
   string trade_key = Dt(g_vt.entry_time) + "|" + dir_text;
   if(InpExportLedger && g_ledger_handle != INVALID_HANDLE)
   {
      FileWrite(g_ledger_handle,
         g_trade_seq,
         trade_key,
         "fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7",
         Dt(g_vt.signal_time),
         Dt(g_vt.entry_time),
         dir_text,
         DoubleToString(Round3(g_vt.entry), 3),
         DoubleToString(Round3(g_vt.stop), 3),
         Dt(exit_time),
         DoubleToString(Round3(exit_price), 3),
         reason,
         DoubleToString(Round3(pnl), 3),
         "fixed_delay_1",
         1,
         "h1_last6_hilo",
         DoubleToString(Round3(g_vt.stop_distance), 3),
         g_vt.side_extreme_kind,
         Dt(g_vt.side_extreme_time),
         DoubleToString(g_vt.side_extreme_bias55_h4sma_pct, 6),
         DoubleToString(g_vt.side_extreme_way_s_way, 6),
         DoubleToString(g_vt.side_extreme_vol_way_s_way, 6),
         DoubleToString(g_vt.side_extreme_close_momentum_signed_pct, 6),
         DoubleToString(g_vt.side_extreme_body_momentum_signed, 6));
      FileFlush(g_ledger_handle);
   }
   g_vt.active = false;
}

int CountMagicPositions()
{
   int count = 0;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      count++;
   }
   return count;
}

bool CurrentBidAsk(double &bid, double &ask)
{
   bid = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   ask = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   return IsValid(bid) && IsValid(ask) && bid > 0.0 && ask > 0.0 && ask >= bid;
}

bool EstimateRiskUsd(double &risk_usd)
{
   risk_usd = 0.0;
   ENUM_ORDER_TYPE order_type = (g_vt.dir == DIR_BUY ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double profit = 0.0;
   if(!OrderCalcProfit(order_type, InpSymbol, InpLots, g_vt.entry, g_vt.stop, profit))
   {
      Print("Order skipped: OrderCalcProfit failed. error=", GetLastError());
      return false;
   }
   risk_usd = MathAbs(profit);
   return true;
}

bool LiveGuardsPass()
{
   double bid = 0.0;
   double ask = 0.0;
   if(!CurrentBidAsk(bid, ask))
   {
      Print("Order skipped: invalid bid/ask for ", InpSymbol);
      return false;
   }

   double spread = ask - bid;
   if(InpMaxSpreadPricePt > 0.0 && spread > InpMaxSpreadPricePt)
   {
      Print("Order skipped: spread=", DoubleToString(spread, 3),
            " > max=", DoubleToString(InpMaxSpreadPricePt, 3));
      return false;
   }

   double risk_usd = 0.0;
   if(!EstimateRiskUsd(risk_usd))
      return false;
   if(InpMaxRiskUsd > 0.0 && risk_usd > InpMaxRiskUsd)
   {
      Print("Order skipped: estimated risk $", DoubleToString(risk_usd, 2),
            " > max $", DoubleToString(InpMaxRiskUsd, 2));
      return false;
   }

   ENUM_ORDER_TYPE order_type = (g_vt.dir == DIR_BUY ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double order_price = (g_vt.dir == DIR_BUY ? ask : bid);
   double margin = 0.0;
   if(!OrderCalcMargin(order_type, InpSymbol, InpLots, order_price, margin))
   {
      Print("Order skipped: OrderCalcMargin failed. error=", GetLastError());
      return false;
   }
   double free_after = AccountInfoDouble(ACCOUNT_MARGIN_FREE) - margin;
   if(InpMinFreeMarginAfterTradeUsd > 0.0 && free_after < InpMinFreeMarginAfterTradeUsd)
   {
      Print("Order skipped: free margin after trade $", DoubleToString(free_after, 2),
            " < min $", DoubleToString(InpMinFreeMarginAfterTradeUsd, 2));
      return false;
   }

   return true;
}

void TryPlaceTrade()
{
   if(InpSimMode || g_vt.active == false)
      return;
   if(!InpAllowRealTrading)
   {
      Print("Order skipped: InpAllowRealTrading=false. Virtual ledger remains active.");
      return;
   }
   if(CountMagicPositions() >= InpMaxOpenPositions)
   {
      Print("Order skipped: max open positions reached for magic ", InpMagic);
      return;
   }
   if(!LiveGuardsPass())
      return;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpSlippage);
   string comment = "1H_M30_4H_CURRENT";
   bool sent = false;
   if(g_vt.dir == DIR_BUY)
      sent = g_trade.Buy(InpLots, InpSymbol, 0.0, g_vt.stop, 0.0, comment);
   else
      sent = g_trade.Sell(InpLots, InpSymbol, 0.0, g_vt.stop, 0.0, comment);
   if(!sent)
      Print("Order send failed. retcode=", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
   else
      Print("Order sent. ticket=", g_trade.ResultOrder(), " dir=", DirText(g_vt.dir), " lots=", InpLots, " stop=", DoubleToString(g_vt.stop, 3));
}

void TryCloseTrade()
{
   if(InpSimMode)
      return;
   g_trade.SetDeviationInPoints(InpSlippage);
   if(PositionSelect(InpSymbol))
   {
      ulong magic = (ulong)PositionGetInteger(POSITION_MAGIC);
      if(magic == InpMagic)
         g_trade.PositionClose(InpSymbol);
   }
}

void ProcessNewM30Bar()
{
   MqlRates m30[];
   int n30 = CopyTfRates(InpM30Period, InpHistoryBarsM30, m30);
   if(n30 < 80)
      return;
   datetime current_open = m30[n30 - 1].time;
   int signal_idx = n30 - 2;
   int prev_idx = n30 - 3;
   if(signal_idx <= 0 || prev_idx <= 0)
      return;

   double m30_sma5[], m30_sma13[];
   CalcSMMA(m30, n30, 5, m30_sma5);
   CalcSMMA(m30, n30, 13, m30_sma13);
   int cross = CrossSide(m30, n30, signal_idx, m30_sma5, m30_sma13);

   if(g_vt.active)
   {
      bool closed = false;
      double exit_price = 0.0;
      string reason = "";
      MqlRates bar = m30[signal_idx];
      if(g_vt.dir == DIR_BUY)
      {
         if(bar.open <= g_vt.stop)
         {
            exit_price = bar.open;
            reason = "stop_gap";
            closed = true;
         }
         else if(bar.low <= g_vt.stop)
         {
            exit_price = g_vt.stop;
            reason = "stop";
            closed = true;
         }
      }
      else
      {
         if(bar.open >= g_vt.stop)
         {
            exit_price = bar.open;
            reason = "stop_gap";
            closed = true;
         }
         else if(bar.high >= g_vt.stop)
         {
            exit_price = g_vt.stop;
            reason = "stop";
            closed = true;
         }
      }
      if(closed)
      {
         TryCloseTrade();
         WriteLedger(exit_price, bar.time, reason);
      }
      else if(cross == -g_vt.dir)
      {
         TryCloseTrade();
         WriteLedger(m30[n30 - 1].open, current_open, "opposite_cross_next_open");
      }
      else
      {
         g_vt.holding_bars++;
      }
   }

   if(g_vt.active || cross == 0)
      return;

   double entry = m30[n30 - 1].open;
   datetime entry_time = current_open;
   FeaturePack fp;
   if(!BuildFeatures(cross, entry_time, entry, fp))
      return;

   g_vt.active = true;
   g_vt.dir = cross;
   g_vt.signal_time = m30[signal_idx].time + TfSeconds(InpM30Period);
   g_vt.entry_time = entry_time;
   g_vt.entry = entry;
   g_vt.stop = fp.structural_stop;
   g_vt.stop_distance = fp.stop_distance;
   g_vt.holding_bars = 0;
   g_vt.side_extreme_kind = fp.side_extreme_kind;
   g_vt.side_extreme_time = fp.side_extreme_time;
   g_vt.side_extreme_bias55_h4sma_pct = fp.side_extreme_bias55_h4sma_pct;
   g_vt.side_extreme_way_s_way = fp.side_extreme_way_s_way;
   g_vt.side_extreme_vol_way_s_way = fp.side_extreme_vol_way_s_way;
   g_vt.side_extreme_close_momentum_signed_pct = fp.side_extreme_close_momentum_signed_pct;
   g_vt.side_extreme_body_momentum_signed = fp.side_extreme_body_momentum_signed;
   TryPlaceTrade();
}


//+------------------------------------------------------------------+
//| Restore real position after EA reload (chart period switch etc.) |
//+------------------------------------------------------------------+
void RestoreRealPositions()
{
   if(InpSimMode) return;
   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      g_vt.active = true;
      g_vt.dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? DIR_BUY : DIR_SELL;
      g_vt.entry_time = (datetime)PositionGetInteger(POSITION_TIME);
      g_vt.signal_time = g_vt.entry_time;
      g_vt.entry = PositionGetDouble(POSITION_PRICE_OPEN);
      g_vt.stop = PositionGetDouble(POSITION_SL);
      g_vt.stop_distance = MathAbs(g_vt.entry - g_vt.stop);
      g_vt.holding_bars = 0;
      Print("[REAL] RESTORED ticket=", ticket, " dir=", DirText(g_vt.dir),
            " entry=", DoubleToString(g_vt.entry, 5), " stop=", DoubleToString(g_vt.stop, 5));
      break;
   }
}

int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagic);
   g_vt.active = false;
   if(!OpenLedger())
      return INIT_FAILED;
   RestoreRealPositions();
   Print("1H_M30_4H current candidate EA initialized. SimMode=", InpSimMode,
         " Ledger=", InpLedgerFile);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_ledger_handle != INVALID_HANDLE)
   {
      FileFlush(g_ledger_handle);
      FileClose(g_ledger_handle);
      g_ledger_handle = INVALID_HANDLE;
   }
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
   ProcessNewM30Bar();
}

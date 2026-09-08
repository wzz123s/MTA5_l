//+------------------------------------------------------------------+
//|                                         30m2H_Strategy_EA.mq5    |
//|                                                          Codex    |
//|                                        30m x 2H SMA5/13 Strategy |
//|                                        v3.0: 三层分级最终版 (Plan B, 2026-06-26)                        |
//|                                          Layer 1: |H2 Bias_55| > 3.0% 硬门 (应用到所有模式)           |
//|                                          Layer 2: pre_cross + cross + post_n(N=2-6), spec [5, 35]            |
//|                                          Layer 3: H2 Bias_5 top 30%                                    |
//|                                        v3.17: FindStopSMA rollback to v3.15 — only MIN_BARS=30 guard |
//|                                        v3.16: REVERTED — 4-guard MAX_DIST_PTS=100 was wrong |
//|                                        v3.15: iBarShift->iTime, CSV before signal return |
//|                                        v3.13: H2 filter = SMA5 vs SMA13 |
//|                                        v3.12: CSV signal export   |
//|                                        v3.11: InpH2Thresh 0.5->0.0     |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "3.00"
#property strict
#include <Trade\Trade.mqh>

//--- Input parameters
input group "=== Account ==="
input ulong   InpMagic      = 302025;      // Magic Number
input string  InpSymbol     = "XAUUSDm";   // Symbol

input group "=== Risk & Position ==="
input double  InpRiskPct    = 3.0;         // Risk % per trade
input double  InpStopLo     = 5000.0;         // Min stop distance (MQL5 points = spec 5 pt x 1000) — v3.0 修订
input double  InpStopHi     = 35000.0;         // Max stop distance (MQL5 points = spec 35 pt x 1000) — v3.0 修订
input int     InpMaxPos     = 3;            // Max concurrent positions
input double  InpMinLots    = 0.01;         // Min lot
input double  InpMaxLots    = 10.0;         // Max lot

input group "=== v3.0 Layer Config ==="
input double  InpBias55Threshold = 3.0;     // Layer 1 硬门: |H2 Bias_55| > X% (默认 3.0%)
input double  InpPreCrossGapPct  = 0.300;      // Layer 2 pre_cross: abs(SMMA5-SMMA13)/SMMA13 <= X%
input int     InpPostNMin        = 2;          // Layer 2 post_n 起始 (含), N ∈ [Min, Max]
input int     InpPostNMax        = 6;          // Layer 2 post_n 终止 (含), 默认 6
input bool    InpUseLayer1       = true;        // 启用 Layer 1 硬门
input bool    InpUseLayer3       = true;        // 启用 Layer 3 Bias_5 top X%
input double  InpBias5TopPct     = 30.0;        // Layer 3: Bias_5 top X% (默认 30%)
input int     InpBias5Lookback   = 500;         // Layer 3 Bias_5 历史滚动计算窗口 (H2 bars)

input group "=== Split TP (v3.10) ==="
input int     InpStageCount   = 3;          // Number of sub-orders per signal (1-3)
input double  InpLotsPerStage = 0.02;       // Lots per sub-order
input double  InpStage1R      = 1.2;        // Stage 1: TP in R multiples (e.g., 1.2 = 1.2R profit)
input double  InpStage2TrailR = 2.0;        // Stage 2: start 30m SMA13 trailing after N R
input double  InpStage2ForceR = 3.0;        // Stage 2: forced close at N R
input int     InpH2CrossBars  = 3;          // Bars used to confirm 2H SMA5/13 cross
input bool    InpStage3On     = true;       // Enable Stage 3 passive (exit on M30 opposite cross)
input bool    InpDebugStages  = true;       // Verbose per-stage logs
input bool    InpExportCSV    = true;       // Export per-bar signals to CSV (signals_export.csv)

input group "=== Strategy ==="
input int     InpFastMA     = 5;            // Fast MA period
input int     InpSlowMA     = 13;           // Slow MA period
input int     InpStopLookback = 200;        // M30 bars to load for stop search
input double  InpH2Thresh   = 0.0;          // H2 distance threshold (%) — LEGACY, unused by H2Filter v3.13+. Kept so old .set files load.
input ENUM_TIMEFRAMES InpH2Period   = PERIOD_H2;    // Higher timeframe (2H)
input ENUM_TIMEFRAMES InpM30Period  = PERIOD_M30;    // Signal timeframe (30m)

input group "=== H2 SMMA (5 periods for v3.0) ==="
input int     InpH2SMA5    = 5;             // H2 SMA5 (Layer 3 Bias_5)
input int     InpH2SMA13   = 13;            // H2 SMA13
input int     InpH2SMA55   = 55;            // H2 SMA55 (Layer 1 Bias_55 锚)
input int     InpH2SMA144  = 144;           // H2 SMA144
input int     InpH2SMA233  = 233;           // H2 SMA233

input group "=== Execution ==="
input ulong   InpSlippage   = 30;           // Slippage (points)
input int     InpCheckSec   = 10;           // Check interval (seconds)
input bool    InpSimMode    = false;         // true=signal only, false=LIVE trading

//--- Global handles
int g_ma_fast_m30, g_ma_slow_m30;
int g_ma_fast_h2,  g_ma_slow_h2;
int g_h2_sma5, g_h2_sma13, g_h2_sma55, g_h2_sma144, g_h2_sma233;  // v3.0: H2 5 SMA
CTrade g_trade;

//--- Bar tracking
datetime g_last_m30_bar = 0;
datetime g_last_h2_bar  = 0;
bool     g_signal_fired = false;

//--- v3.0 post_n 状态机 (M30 SMA5/13 穿越后第 N 根)
int      g_post_n_counter = 0;          // 当前 M30 bar 在段内的位置 (0=穿越/无段, +N=up, -N=down)
double   g_last_cross_dir = 0;          // 最近穿越方向 (+1=good, -1=bad, 0=无)

//--- v3.0 Layer 3 状态 (Bias_5 top X% 阈值缓存)
double   g_bias5_top_threshold = 0;     // Bias_5 滚动 top X% 阈值 (H2 close 偏离 SMMA5)
bool     g_bias5_history_ready = false; // 是否已计算过阈值

//--- 3-stage split TP state (v3.10)
// Magic-number stage offsets from InpMagic (must be ulong to match InpMagic type)
const ulong MAGIC_STAGE1 = 1;   // InpMagic+1 = stage 1 (1.2R close)
const ulong MAGIC_STAGE2 = 2;   // InpMagic+2 = stage 2 (SMA13 trail + 3R force)
const ulong MAGIC_STAGE3 = 3;   // InpMagic+3 = stage 3 (let profits run, M30 opposite-cross exit)

// Per-stage state, indexed 1..3 (index 0 unused)
ulong  g_stage_tickets[4];     // position ticket for this stage (0 = no position)
double g_stage_entry[4];       // fill price for R calc
double g_stage_orig_sl[4];     // original SL at fill (used for R, NOT ratchet SL)
bool   g_stage2_trail_on[4];   // true once stage 2 reaches InpStage2TrailR

//--- CSV export (v3.11)
int g_csv_handle = INVALID_HANDLE;   // signals_export.csv file handle
string g_csv_path = "signals_export.csv";

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("========================================");
   Print("  30m x 2H EA v3.00 - Initializing (Plan B, 2026-06-26)");
   Print("========================================");
   Print("  [Layer 1] InpBias55Threshold = ", DoubleToString(InpBias55Threshold, 1),
         "% (|H2 Bias_55| 硬门, 默认 3.0%)");
   Print("  [Layer 1] InpUseLayer1 = ", InpUseLayer1 ? "TRUE" : "FALSE (Layer 1 禁用)");
   Print("  [Layer 2] pre_cross gap <= ", DoubleToString(InpPreCrossGapPct, 3), "% (close crosses SMMA13)");
   Print("  [Layer 2] post_n range = [", InpPostNMin, ", ", InpPostNMax, "]");
   Print("  [Layer 2] spec range = [", DoubleToString(InpStopLo/1000, 1), ", ", DoubleToString(InpStopHi/1000, 1), "] pt");
   Print("  [Layer 3] InpBias5TopPct = ", DoubleToString(InpBias5TopPct, 1),
         "% (Bias_5 top X%, 默认 30%)");
   Print("  [Layer 3] InpUseLayer3 = ", InpUseLayer3 ? "TRUE" : "FALSE");
   Print("  [Spec 换算] 1 spec 点 = 1000 MQL5 points");

   // Create MA handles (M30)
   g_ma_fast_m30 = iMA(InpSymbol, InpM30Period, InpFastMA, 0, MODE_SMMA, PRICE_CLOSE);
   g_ma_slow_m30 = iMA(InpSymbol, InpM30Period, InpSlowMA, 0, MODE_SMMA, PRICE_CLOSE);

   // Create H2 2 SMA handles (兼容旧逻辑)
   g_ma_fast_h2  = iMA(InpSymbol, InpH2Period,  InpFastMA, 0, MODE_SMMA, PRICE_CLOSE);
   g_ma_slow_h2  = iMA(InpSymbol, InpH2Period,  InpSlowMA, 0, MODE_SMMA, PRICE_CLOSE);

   // v3.0: H2 5 SMA 句柄 (Layer 1 Bias_55 + Layer 3 Bias_5)
   g_h2_sma5    = iMA(InpSymbol, InpH2Period, InpH2SMA5,   0, MODE_SMMA, PRICE_CLOSE);
   g_h2_sma13   = iMA(InpSymbol, InpH2Period, InpH2SMA13,  0, MODE_SMMA, PRICE_CLOSE);
   g_h2_sma55   = iMA(InpSymbol, InpH2Period, InpH2SMA55,  0, MODE_SMMA, PRICE_CLOSE);
   g_h2_sma144  = iMA(InpSymbol, InpH2Period, InpH2SMA144, 0, MODE_SMMA, PRICE_CLOSE);
   g_h2_sma233  = iMA(InpSymbol, InpH2Period, InpH2SMA233, 0, MODE_SMMA, PRICE_CLOSE);

   if(g_ma_fast_m30 == INVALID_HANDLE || g_ma_slow_m30 == INVALID_HANDLE ||
      g_ma_fast_h2  == INVALID_HANDLE || g_ma_slow_h2  == INVALID_HANDLE ||
      g_h2_sma5 == INVALID_HANDLE || g_h2_sma13 == INVALID_HANDLE ||
      g_h2_sma55 == INVALID_HANDLE || g_h2_sma144 == INVALID_HANDLE ||
      g_h2_sma233 == INVALID_HANDLE)
   {
     Print("Failed to create MA handles!");
     return INIT_FAILED;
   }

   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("  Account:  ", AccountInfoInteger(ACCOUNT_LOGIN));
   Print("  Balance:  $", DoubleToString(bal, 2));
   Print("  Equity:   $", DoubleToString(eq, 2));
   Print("  Mode:     ", InpSimMode ? "SIMULATION" : "LIVE TRADING");

   // v3.10: initialize 3-stage split TP state
   for(int i = 1; i <= 3; i++)
   {
      g_stage_tickets[i]   = 0;
      g_stage_entry[i]     = 0;
      g_stage_orig_sl[i]   = 0;
      g_stage2_trail_on[i] = false;
   }
   Print("  Split TP: ", InpStageCount, " stage(s) x ",
         DoubleToString(InpLotsPerStage, 2), " lots");
   Print("    Stage 1: ", DoubleToString(InpStage1R, 2), "R close");
   Print("    Stage 2: trail after ", DoubleToString(InpStage2TrailR, 2),
         "R, force close at ", DoubleToString(InpStage2ForceR, 2), "R");
   Print("    Stage 3: ", InpStage3On ? "ON (M30 opposite cross exit)" : "OFF");

   // v3.11: open CSV export file (if enabled)
   if(InpExportCSV)
   {
      g_csv_handle = FileOpen(g_csv_path, FILE_WRITE|FILE_CSV|FILE_SHARE_READ|FILE_ANSI, ",");
      if(g_csv_handle == INVALID_HANDLE)
         Print("[WARN] Could not open CSV file: ", GetLastError());
      else
      {
         // Header (v3.14: added h2_cross column)
         FileWrite(g_csv_handle,
            "bar_time", "close", "m30_sma5", "m30_sma13",
            "m30_cross", "h2_close", "h2_sma5", "h2_dist_pct", "h2_dir",
            "h2_cross", "stop_sma", "stop_pts", "decision", "skip_reason");
         Print("  CSV export: ", g_csv_path, " (per-bar rows, v3.14+ includes h2_cross)");
         FileFlush(g_csv_handle);
      }
   }

   Print("========================================");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_ma_fast_m30 != INVALID_HANDLE) IndicatorRelease(g_ma_fast_m30);
   if(g_ma_slow_m30 != INVALID_HANDLE) IndicatorRelease(g_ma_slow_m30);
   if(g_ma_fast_h2  != INVALID_HANDLE) IndicatorRelease(g_ma_fast_h2);
   if(g_ma_slow_h2  != INVALID_HANDLE) IndicatorRelease(g_ma_slow_h2);
   // v3.0: H2 5 SMA 句柄释放
   if(g_h2_sma5   != INVALID_HANDLE) IndicatorRelease(g_h2_sma5);
   if(g_h2_sma13  != INVALID_HANDLE) IndicatorRelease(g_h2_sma13);
   if(g_h2_sma55  != INVALID_HANDLE) IndicatorRelease(g_h2_sma55);
   if(g_h2_sma144 != INVALID_HANDLE) IndicatorRelease(g_h2_sma144);
   if(g_h2_sma233 != INVALID_HANDLE) IndicatorRelease(g_h2_sma233);

   // v3.11: close CSV file
   if(g_csv_handle != INVALID_HANDLE)
   {
      FileClose(g_csv_handle);
      g_csv_handle = INVALID_HANDLE;
      Print("CSV export closed");
   }
   Print("EA Deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Copy MA buffer (shift 0 = oldest, 1 = prev, N-1 = current)        |
//+------------------------------------------------------------------+
bool GetMABars(int handle, int count, double &out[])
{
   double buf[];
   ArraySetAsSeries(buf, false);  // oldest first
   int copied = CopyBuffer(handle, 0, 0, count, buf);
   if(copied <= 0) { Print("CopyBuffer error: ", GetLastError()); return false; }
   ArrayResize(out, copied);
   ArrayCopy(out, buf);
   return true;
}

//+------------------------------------------------------------------+
//| Get last N values of MA buffer (newest first, index 0 = newest)   |
//+------------------------------------------------------------------+
bool GetMALastN(int handle, int count, double &out[])
{
   double buf[];
   ArraySetAsSeries(buf, true);  // newest first
   int copied = CopyBuffer(handle, 0, 0, count, buf);
   if(copied <= 0) return false;
   ArrayResize(out, copied);
   ArrayCopy(out, buf);
   return true;
}

//+------------------------------------------------------------------+
//| H2 segment direction: +1=up (close>SMA13), -1=down, 0=neutral    |
//+------------------------------------------------------------------+
int H2SegmentDir()
{
   double ma_buf[];
   if(!GetMALastN(g_ma_slow_h2, 1, ma_buf)) return 0;
   if(!GetMALastN(g_ma_fast_h2, 1, ma_buf)) return 0; // NOTE: overwrites slow H2 result; H2SegmentDir is not called from main flow

   // Get last H2 close
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int n = CopyRates(InpSymbol, InpH2Period, 0, 1, rates);
   if(n <= 0) return 0;

   double close0 = rates[0].close;
   double ma13 = ma_buf[0];
   if(ma13 == 0) return 0;
   return (close0 > ma13) ? 1 : -1;
}

//+------------------------------------------------------------------+
//| H2 distance filter: return +1=bull, -1=bear, 0=reject            |
//+------------------------------------------------------------------+
int H2Filter()
{
   // v3.13: Python-parity H2 direction — check SMA5 vs SMA13 (segment direction),
   // not close vs SMA5. Matches Python Strategy30m2H.mark_direction:
   //   'up'/'good' (SMA5 > SMA13) -> bull, 'down'/'bad' (SMA5 < SMA13) -> bear.
   // InpH2Thresh is now unused (kept for backward compat with old .set files).
   double slow_buf[];
   double fast_buf[];
   if(!GetMALastN(g_ma_slow_h2, 1, slow_buf)) return 0;
   if(!GetMALastN(g_ma_fast_h2, 1, fast_buf)) return 0;
   if(ArraySize(slow_buf) == 0 || ArraySize(fast_buf) == 0) return 0;

   double ma5  = fast_buf[0];
   double ma13 = slow_buf[0];
   if(ma13 == 0) return 0;

   if(ma5 > ma13) return +1;   // H2 bull (SMA5 above SMA13, up trend)
   if(ma5 < ma13) return -1;   // H2 bear (SMA5 below SMA13, down trend)
   return 0;                    // exactly equal — neutral (rare)
}

//+------------------------------------------------------------------+
//| Detect M30 cross on completed bar (index 0 = bar[1] = prev comp)   |
//| bars[0]=oldest, bars[1]=prev, bars[2]=prev2 ... we check bar[1]   |
//| Returns: +1=golden cross, -1=dead cross, 0=none                  |
//+------------------------------------------------------------------+
int M30Cross()
{
   // Need 3 bars minimum for cross detection: prev, prev2, prev3
   // We check if SMA5 crosses SMA13 on the most recently completed bar
   // bars index: 0=bar[-3], 1=bar[-2], 2=bar[-1] = most recent completed
   const int BARS = 3;
   double fast_buf[], slow_buf[];
   if(!GetMALastN(g_ma_fast_m30, BARS, fast_buf)) return 0;
   if(!GetMALastN(g_ma_slow_m30, BARS, slow_buf)) return 0;

   // fast_buf[0]=current forming, [1]=last completed, [2]=prev completed
   // Check cross on most recently completed bar = index 1
   if(fast_buf[1] == 0 || slow_buf[1] == 0 || fast_buf[2] == 0 || slow_buf[2] == 0) return 0;

   bool curr_above = fast_buf[1] > slow_buf[1];
   bool prev_above = fast_buf[2] > slow_buf[2];

   if(!prev_above && curr_above) return +1;  // golden cross
   if(prev_above && !curr_above) return -1;  // dead cross
   return 0;
}

//+------------------------------------------------------------------+
//| Get M30 SMA values for stop calculation                           |
//| Returns: n=number of values, arrays oldest->newest                |
//+------------------------------------------------------------------+
int GetM30SMAArrays(double &fast[], double &slow[], int max_bars)
{
   if(!GetMABars(g_ma_fast_m30, max_bars, fast)) return 0;
   if(!GetMABars(g_ma_slow_m30, max_bars, slow)) return 0;
   int sz_fast = ArraySize(fast);
   int sz_slow = ArraySize(slow);
   if(sz_fast == 0 || sz_slow == 0) return 0;
   return MathMin(sz_fast, sz_slow);
}

//+------------------------------------------------------------------+
//| Get M30 rates (oldest first)                                      |
//+------------------------------------------------------------------+
int GetM30Rates(MqlRates &rates[], int count)
{
   ArraySetAsSeries(rates, false);
   int copied = CopyRates(InpSymbol, InpM30Period, 0, count, rates);
   return copied;
}

//+------------------------------------------------------------------+
//| Find last segment extreme for stop                                |
//| seg_dir = +1 means SMA5 above SMA13 (bull segment)                |
//| seg_dir = -1 means SMA5 below SMA13 (bear segment)               |
//| Returns stop SMA13 extreme, 0 on failure                          |
//+------------------------------------------------------------------+
double FindStopSMA(double &sma_f[], double &sma_s[], int n, int seg_dir)
{
   // v3.17: ROLLBACK from v3.16 4-guard to v3.15-style minimal logic.
   // Only MIN_BARS=30 guard remains (defends against array OOB).
   // Spec check (3000-35000 MQL5 pts = 3-35 spec 点) is done by caller.
   //
   // v3.16 was broken: 4th guard MAX_DIST_PTS=100 wrongly rejected 91,178
   // valid stops (100 MQL5 pts = $0.10, but spec is 3000-35000 MQL5 pts).
   // Result: 0% FindStopSMA success rate, 0 signals, $500 final.
   const int MIN_BARS = 30;

   // Defence: array too small
   if(n < MIN_BARS)
   {
      Print("[FindStopSMA] array too small (n=", n, " < ", MIN_BARS, "), returning 0");
      return 0;
   }

   // Search entire history for the most recent M30 cross
   int seg_start = -1;
   for(int i = n - 2; i >= 1; i--)
   {
      bool curr_above = sma_f[i] > sma_s[i];
      bool prev_above = sma_f[i+1] > sma_s[i+1];
      if(curr_above != prev_above)
      {
         seg_start = i;
         break;
      }
   }
   if(seg_start < 0)
   {
      Print("[FindStopSMA] no cross in entire history (n=", n, "), returning 0");
      return 0;
   }

   int seg_len = (n - 2) - seg_start;
   Print("[FindStopSMA] seg_dir=", seg_dir, " seg_start=", seg_start,
         " seg_len=", seg_len, " n=", n);

   // Print SMA13 range in segment (debug aid)
   double sma_min = 0, sma_max = 0;
   for(int i = seg_start; i < n - 2; i++)
   {
      if(sma_s[i] == 0 || MathIsValidNumber(sma_s[i]) == false) continue;
      if(sma_min == 0 || sma_s[i] < sma_min) sma_min = sma_s[i];
      if(sma_max == 0 || sma_s[i] > sma_max) sma_max = sma_s[i];
   }
   Print("[FindStopSMA] SMA13 segment range: [", DoubleToString(sma_min, 5),
         " to ", DoubleToString(sma_max, 5), "]");

   // Find SMA13 extreme in segment (MathMax for UP, MathMin for DOWN)
   double extreme = 0;
   for(int i = seg_start; i < n - 2; i++)  // n-2 = most recent completed bar
   {
      if(sma_s[i] == 0 || MathIsValidNumber(sma_s[i]) == false) continue;
      if(seg_dir > 0)   // UP segment (caller is SHORT): find HIGHEST SMA13 as stop
         extreme = (extreme == 0) ? sma_s[i] : MathMax(extreme, sma_s[i]);
      else              // DOWN segment (caller is LONG): find LOWEST SMA13 as stop
         extreme = (extreme == 0) ? sma_s[i] : MathMin(extreme, sma_s[i]);
   }

   // v3.17: spec check removed. Caller validates stop distance in [InpStopLo, InpStopHi].
   Print("[FindStopSMA] RETURN extreme=", DoubleToString(extreme, 5));
   return extreme;
}

//+------------------------------------------------------------------+
//| Count our open positions                                          |
//+------------------------------------------------------------------+
int OurPositionCount()
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == InpSymbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         cnt++;
   }
   return cnt;
}

//+------------------------------------------------------------------+
//| Count our 3-stage split positions (magic in [InpMagic+1..+3])    |
//+------------------------------------------------------------------+
int OurStageCount()
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != InpSymbol) continue;
      ulong m = (ulong)PositionGetInteger(POSITION_MAGIC);
      if(m >= InpMagic + MAGIC_STAGE1 && m <= InpMagic + MAGIC_STAGE3)
         cnt++;
   }
   return cnt;
}

//+------------------------------------------------------------------+
//| Count positions of a specific stage (magic == InpMagic + stage)   |
//+------------------------------------------------------------------+
int OurStagePosCount(int stage)
{
   if(stage < 1 || stage > 3) return 0;
   int cnt = 0;
   ulong target_magic = InpMagic + (ulong)stage;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == InpSymbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == target_magic)
         cnt++;
   }
   return cnt;
}

//+------------------------------------------------------------------+
//| Find first position matching stage, fill ticket/entry/sl/volume   |
//| Returns false if no position found for this stage                |
//+------------------------------------------------------------------+
bool FindOurStagePos(int stage, ulong &ticket, double &entry,
                     double &sl, double &vol)
{
   ticket = 0; entry = 0; sl = 0; vol = 0;
   if(stage < 1 || stage > 3) return false;
   ulong target_magic = InpMagic + (ulong)stage;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != target_magic) continue;
      ticket = PositionGetTicket(i);
      entry  = PositionGetDouble(POSITION_PRICE_OPEN);
      sl     = PositionGetDouble(POSITION_SL);
      vol    = PositionGetDouble(POSITION_VOLUME);
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| 2H SMA5/13 cross detector (last completed bar)                    |
//| Returns +1=golden, -1=dead, 0=no cross                            |
//+------------------------------------------------------------------+
int H2CrossDetector()
{
   // Need at least InpH2CrossBars + 2 bars
   int need = InpH2CrossBars + 2;
   double fast[], slow[];
   if(!GetMABars(g_ma_fast_h2, need, fast)) return 0;
   if(!GetMABars(g_ma_slow_h2, need, slow)) return 0;

   // fast[0]=oldest, fast[need-1]=newest (newest is bar 0 = current forming)
   // Last completed bar = index need-2
   int last_comp = need - 2;
   int prev_comp = need - 3;
   if(prev_comp < 0 || last_comp >= ArraySize(fast)) return 0;

   bool curr_above = fast[last_comp] > slow[last_comp];
   bool prev_above = fast[prev_comp] > slow[prev_comp];

   if(!prev_above && curr_above) return +1;  // golden cross
   if(prev_above && !curr_above) return -1;  // dead cross
   return 0;
}

//+------------------------------------------------------------------+
//| Partial-close helper (wraps CTrade::PositionClosePartial)         |
//+------------------------------------------------------------------+
bool PartialClose(ulong ticket, double lots)
{
   if(InpSimMode)
   {
      Print("=== SIM PARTIAL CLOSE ticket=", ticket, " lots=", DoubleToString(lots, 2), " ===");
      return true;
   }
   if(!g_trade.PositionClosePartial(ticket, lots))
   {
      Print("PartialClose failed: ticket=", ticket, " lots=", lots, " err=", GetLastError());
      return false;
   }
   Print("Partial close OK: ticket=", ticket, " lots=", lots);
   return true;
}

//+------------------------------------------------------------------+
//| Stage 2 trailing SL: only ratchet UP (longs) / DOWN (shorts)      |
//| Returns true if SL was modified                                   |
//+------------------------------------------------------------------+
bool TrailStage2SL(ulong ticket, double current_sl, double sma13_now,
                   ENUM_POSITION_TYPE ptype)
{
   if(ticket == 0 || sma13_now <= 0) return false;

   double new_sl = current_sl;
   if(ptype == POSITION_TYPE_BUY)
   {
      // Long: only ratchet SL UP (never lower it)
      if(sma13_now > current_sl)
         new_sl = NormalizeDouble(sma13_now, (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS));
   }
   else if(ptype == POSITION_TYPE_SELL)
   {
      // Short: only ratchet SL DOWN (never raise it)
      if(sma13_now < current_sl)
         new_sl = NormalizeDouble(sma13_now, (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS));
   }
   else
      return false;

   // No improvement (SL on the wrong side)
   if(MathAbs(new_sl - current_sl) < SymbolInfoDouble(InpSymbol, SYMBOL_POINT))
   {
      if(InpDebugStages)
         Print("[STAGE2 TRAIL] ticket=", ticket, " no ratchet (SMA13=",
               DoubleToString(sma13_now, 5), " SL=", DoubleToString(current_sl, 5), ")");
      return false;
   }

   if(InpSimMode)
   {
      Print("=== SIM TRAIL ticket=", ticket, " new_sl=", DoubleToString(new_sl, 5), " ===");
      return true;
   }

   MqlTradeRequest mod = {};
   MqlTradeResult  modres = {};
   mod.action   = TRADE_ACTION_SLTP;
   mod.position = ticket;
   mod.symbol   = InpSymbol;
   mod.sl       = new_sl;
   mod.tp       = 0;
   if(!g_trade.OrderSend(mod, modres))
   {
      Print("  [WARN] Stage2 trail SL modify failed: ticket=", ticket,
            " retcode=", modres.retcode, " comment=", modres.comment);
      return false;
   }
   if(InpDebugStages)
      Print("[STAGE2 TRAIL] ticket=", ticket, " SL: ",
            DoubleToString(current_sl, 5), " -> ", DoubleToString(new_sl, 5));
   return true;
}

//+------------------------------------------------------------------+
//| Per-stage TP / trail / cross-exit logic                           |
//| Returns: 0 = hold, 1 = full close this stage                     |
//| Uses g_stage_orig_sl[stage] for R (not current ratcheted SL)     |
//+------------------------------------------------------------------+
int CheckStageExit(int stage, ulong ticket, double entry, double orig_sl,
                   double current_price, int h2_cross)
{
   if(stage < 1 || stage > 3) return 0;
   if(entry <= 0 || orig_sl <= 0) return 0;

   double R = MathAbs(entry - orig_sl);   // R is the original stop distance
   if(R <= 0) return 0;
   double dist = MathAbs(current_price - entry);
   double rr   = dist / R;                // current profit in R multiples

   ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   if(stage == 1)
   {
      // Stage 1: 1.2R profit -> full close
      if(rr >= InpStage1R)
      {
         if(InpDebugStages)
            Print("[STAGE1 TP] ticket=", ticket, " rr=", DoubleToString(rr, 2),
                  " >= ", DoubleToString(InpStage1R, 2), " -> close");
         return 1;
      }
      // Also exit if M30 opposite cross (use existing ShouldExit semantics)
      if(ShouldExit(ptype))
      {
         if(InpDebugStages)
            Print("[STAGE1 M30-X] ticket=", ticket, " -> close");
         return 1;
      }
   }
   else if(stage == 2)
   {
      // Stage 2: 3R forced close
      if(rr >= InpStage2ForceR)
      {
         if(InpDebugStages)
            Print("[STAGE2 FORCED] ticket=", ticket, " rr=", DoubleToString(rr, 2),
                  " >= ", DoubleToString(InpStage2ForceR, 2), " -> close");
         return 1;
      }
      // After 2R: start trailing 30m SMA13 (one-shot set g_stage2_trail_on)
      if(rr >= InpStage2TrailR && !g_stage2_trail_on[stage])
      {
         g_stage2_trail_on[stage] = true;
         if(InpDebugStages)
            Print("[STAGE2 TRAIL ON] ticket=", ticket, " rr=",
                  DoubleToString(rr, 2), " >= ", DoubleToString(InpStage2TrailR, 2));
      }
      if(g_stage2_trail_on[stage])
      {
         // Get 30m SMA13 current value
         double sma13_now[];
         if(GetMALastN(g_ma_slow_m30, 1, sma13_now) && ArraySize(sma13_now) > 0)
            TrailStage2SL(ticket, PositionGetDouble(POSITION_SL), sma13_now[0], ptype);
      }
      // Exit if M30 opposite cross
      if(ShouldExit(ptype))
      {
         if(InpDebugStages)
            Print("[STAGE2 M30-X] ticket=", ticket, " -> close");
         return 1;
      }
   }
   else if(stage == 3)
   {
      // Stage 3 always returns 0 (managed separately by M30 opposite cross in OnTick)
      return 0;
   }
   return 0;
}

//+------------------------------------------------------------------+
//| Check if we have a position in given direction                    |
//+------------------------------------------------------------------+
bool HasPosDir(ENUM_POSITION_TYPE ptype)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == InpSymbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         PositionGetInteger(POSITION_TYPE) == ptype)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Calculate lot size based on equity risk                            |
//+------------------------------------------------------------------+
double CalcLot(double stop_pts)
{
   if(stop_pts <= 0) return InpMinLots;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk    = balance * InpRiskPct / 100.0;

   // XAUUSD: contract = 100 oz, point = 0.001 (3-digit), tick = 0.001
   double tick_val = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz  = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   double point    = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);

   if(point == 0) point = 0.001;
   if(tick_sz == 0) tick_sz = 0.001;
   if(tick_val == 0) tick_val = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE) * tick_sz;

   double pts_val = tick_val * stop_pts;
   if(pts_val <= 0) return InpMinLots;

   double lot = risk / pts_val;
   lot = NormalizeDouble(lot, 2);
   lot = MathMax(InpMinLots, MathMin(InpMaxLots, lot));
   lot = MathFloor(lot / SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP)) *
         SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   return MathMax(InpMinLots, lot);
}

//+------------------------------------------------------------------+
//| Should exit position based on M30 opposite cross?                  |
//++------------------------------------------------------------------+
bool ShouldExit(ENUM_POSITION_TYPE ptype)
{
   // Get last 4 M30 bars (oldest to newest)
   MqlRates rates[];
   int n = GetM30Rates(rates, 4);
   if(n < 4) return false;

   double fast[], slow[];
   if(!GetMABars(g_ma_fast_m30, n, fast)) return false;
   if(!GetMABars(g_ma_slow_m30, n, slow)) return false;
   // fast[0]=oldest, fast[n-1]=newest

   // Check cross on rates[1] (second newest = last completed)
   int prev_idx = n - 2;   // last completed bar index in SMA arrays
   if(prev_idx < 1 || prev_idx >= ArraySize(fast)) return false;

   bool curr_above = fast[prev_idx] > slow[prev_idx];
   bool prev_above = fast[prev_idx+1] > slow[prev_idx+1];

   int cross = 0;
   if(!prev_above && curr_above) cross = +1;
   else if(prev_above && !curr_above) cross = -1;

   if(ptype == POSITION_TYPE_BUY  && cross == -1) return true;  // exit long on dead cross
   if(ptype == POSITION_TYPE_SELL && cross == +1) return true;  // exit short on golden cross
   return false;
}

//+------------------------------------------------------------------+
//| Execute order (real or simulated) — v3.10 split-aware             |
//| Returns: ticket (>0) on success, 0 on failure                     |
//| stage: 0 = legacy single order, 1/2/3 = split TP stage          |
//+------------------------------------------------------------------+
ulong Execute(string direction, double entry, double stop, double lot, int stage = 0)
{
   double intended_dist = MathAbs(entry - stop);   // distance in price units
   double tick_val = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz  = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_val == 0 || tick_sz == 0)
   {
      Print("  [ERROR] tick_val/tick_sz not available — aborting");
      return 0;
   }
   if(intended_dist <= 0)
   {
      Print("  [ERROR] intended stop distance is 0 — aborting");
      return 0;
   }
   double intended_risk = lot * (intended_dist / tick_sz) * tick_val;

   // Magic + comment encode the split stage (v3.10)
   ulong  this_magic = (stage >= 1 && stage <= 3) ? (InpMagic + stage) : InpMagic;
   string this_comm  = (stage >= 1 && stage <= 3)
                       ? ("30m2H_v3_S" + IntegerToString(stage))
                       : "30m2H_v3";

   Print("=== ", direction, (stage > 0 ? " (stage " + IntegerToString(stage) + ")" : ""), " ===");
   Print("  Magic:         ", this_magic, "  Comment: ", this_comm);
   Print("  Entry(signal): ", DoubleToString(entry, 5));
   Print("  Stop(target):  ", DoubleToString(stop, 5));
   Print("  Lots:          ", lot);
   Print("  Intended risk: $", DoubleToString(intended_risk, 2));

   if(InpSimMode)
   {
      Print("  [SIM MODE - no order placed, synthetic ticket assigned]");
      // Still populate stage globals so CheckStageExit can run in backtest
      if(stage >= 1 && stage <= 3)
      {
         ulong synth_ticket = 1000 + stage;   // synthetic, never collides with real
         g_stage_tickets[stage] = synth_ticket;
         g_stage_entry[stage]   = entry;
         double synth_sl = (direction == "BUY")
                           ? NormalizeDouble(entry - intended_dist, 5)
                           : NormalizeDouble(entry + intended_dist, 5);
         g_stage_orig_sl[stage] = synth_sl;
         g_stage2_trail_on[stage] = false;
         Print("  [SIM] stage ", stage, " synth_ticket=", synth_ticket,
               " SL=", DoubleToString(synth_sl, 5));
         return synth_ticket;
      }
      return 0;
   }

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action      = TRADE_ACTION_DEAL;
   req.symbol      = InpSymbol;
   req.magic       = this_magic;
   req.comment     = this_comm;
   req.deviation   = InpSlippage;
   req.type_filling = ORDER_FILLING_FOK;
   req.volume      = lot;
   req.sl          = 0;     // SL set AFTER fill to anchor on actual price
   req.tp          = 0;

   if(direction == "BUY")
   {
      req.price = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
      req.type  = ORDER_TYPE_BUY;
   }
   else
   {
      req.price = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
      req.type  = ORDER_TYPE_SELL;
   }

   if(!g_trade.OrderSend(req, res))
   {
      Print("OrderSend failed: retcode=", res.retcode, " comment=", res.comment);
      return 0;
   }
   if(res.retcode != TRADE_RETCODE_DONE)
   {
      Print("Order failed: retcode=", res.retcode, " comment=", res.comment);
      return 0;
   }

   // === Anchor stop to ACTUAL fill price, not typical price ===
   double fill_price = res.price;
   double actual_stop;
   if(direction == "BUY")
      actual_stop = NormalizeDouble(fill_price - intended_dist, 5);
   else
      actual_stop = NormalizeDouble(fill_price + intended_dist, 5);

   // Apply SL to open position
   MqlTradeRequest mod = {};
   MqlTradeResult  modres = {};
   mod.action   = TRADE_ACTION_SLTP;
   mod.position = res.order;
   mod.symbol   = InpSymbol;
   mod.sl       = actual_stop;
   mod.tp       = 0;
   if(!g_trade.OrderSend(mod, modres))
      Print("  [WARN] PositionModify SL failed: retcode=", modres.retcode,
            " comment=", modres.comment);
   else
      Print("  SL set: ", DoubleToString(actual_stop, 5));

   // === Print ACTUAL values using real fill price ===
   double actual_risk = lot * (MathAbs(fill_price - actual_stop) / tick_sz) * tick_val;
   double slippage    = MathAbs(fill_price - entry);

   Print("  FILLED! ticket=", res.order, " vol=", res.volume);
   Print("  Fill:           ", DoubleToString(fill_price, 5));
   Print("  Stop (actual):  ", DoubleToString(actual_stop, 5));
   Print("  Slippage:       ", DoubleToString(slippage / tick_sz, 1), " ticks (",
         DoubleToString(slippage, 5), " price)");
   Print("  Actual risk $:  ", DoubleToString(actual_risk, 2));

   // Populate stage globals for the new 3-stage TP system
   if(stage >= 1 && stage <= 3)
   {
      g_stage_tickets[stage] = res.order;
      g_stage_entry[stage]   = fill_price;
      g_stage_orig_sl[stage] = actual_stop;
      g_stage2_trail_on[stage] = false;
   }
   return res.order;
}

//+------------------------------------------------------------------+
//| Close position                                                    |
//+------------------------------------------------------------------+
void ClosePos(ulong ticket)
{
   if(InpSimMode)
   {
      Print("=== SIM CLOSE ticket=", ticket, " ===");
      return;
   }
   if(!g_trade.PositionClose(ticket))
   {
      Print("Close failed: ticket=", ticket, " err=", GetLastError());
      return;
   }
   Print("Closed ticket=", ticket);
}

//+------------------------------------------------------------------+
//| v3.0 Layer 1: H2 Bias_55 计算                                       |
//| 返回: |Bias_55| = |(close - SMA55) / SMA55| × 100              |
//+------------------------------------------------------------------+
double CalcBias55()
{
   double close_arr[], sma55_arr[];
   if(CopyClose(InpSymbol, InpH2Period, 0, 1, close_arr) <= 0) return 0;
   if(CopyBuffer(g_h2_sma55, 0, 0, 1, sma55_arr) <= 0) return 0;
   double close = close_arr[0];
   double sma55 = sma55_arr[0];
   if(sma55 == 0 || sma55 == EMPTY_VALUE) return 0;
   return MathAbs((close - sma55) / sma55) * 100.0;
}

//+------------------------------------------------------------------+
//| v3.0 Layer 3: H2 Bias_5 计算                                      |
//| 返回: |Bias_5| = |(close - SMA5) / SMA5| × 100                |
//+------------------------------------------------------------------+
double CalcBias5()
{
   double close_arr[], sma5_arr[];
   if(CopyClose(InpSymbol, InpH2Period, 0, 1, close_arr) <= 0) return 0;
   if(CopyBuffer(g_h2_sma5, 0, 0, 1, sma5_arr) <= 0) return 0;
   double close = close_arr[0];
   double sma5 = sma5_arr[0];
   if(sma5 == 0 || sma5 == EMPTY_VALUE) return 0;
   return MathAbs((close - sma5) / sma5) * 100.0;
}

//+------------------------------------------------------------------+
//| v3.0 Layer 3: Bias_5 历史滚动 top X% 阈值计算                    |
//| 计算最近 N 根 H2 bar 的 Bias_5,取第 (1 - X%) 分位作为阈值        |
//| 返回: true = 通过 top X% (Bias_5 >= 阈值)                        |
//+------------------------------------------------------------------+
bool IsBias5TopPct(double current_bias5)
{
   if(!InpUseLayer3) return true;  // Layer 3 关闭时直接通过

   int n = InpBias5Lookback;
   double close_arr[], sma5_arr[];
   ArraySetAsSeries(close_arr, true);
   ArraySetAsSeries(sma5_arr, true);
   if(CopyClose(InpSymbol, InpH2Period, 0, n, close_arr) <= 0) return false;
   if(CopyBuffer(g_h2_sma5, 0, 0, n, sma5_arr) <= 0) return false;

   // 计算 Bias_5 数组
   double biases[];
   ArrayResize(biases, n);
   int valid = 0;
   for(int i = 0; i < n; i++)
   {
      if(sma5_arr[i] == 0 || sma5_arr[i] == EMPTY_VALUE) continue;
      biases[valid] = MathAbs((close_arr[i] - sma5_arr[i]) / sma5_arr[i]) * 100.0;
      valid++;
   }
   if(valid < 10) return true;  // 数据不足,放行

   ArrayResize(biases, valid);
   ArraySort(biases);
   // 取第 (1 - X%) 分位
   int idx = (int)MathFloor(valid * (1.0 - InpBias5TopPct / 100.0));
   if(idx < 0) idx = 0;
   if(idx >= valid) idx = valid - 1;
   g_bias5_top_threshold = biases[idx];

   return (current_bias5 >= g_bias5_top_threshold);
}

//+------------------------------------------------------------------+
//| v3.0 Layer 2: pre_cross detector                              |
//| Python parity: previous close on old side, current close crosses |
//| SMMA13, while SMMA5 remains on the original side.                |
//+------------------------------------------------------------------+
int DetectPreCross(double prev_close2, double prev_close1,
                   double ma5_prev1, double ma13_prev1, double ma13_prev2)
{
   if(ma13_prev1 == 0 || ma13_prev2 == 0) return 0;

   double gap_pct = MathAbs(ma5_prev1 - ma13_prev1) / ma13_prev1 * 100.0;
   if(gap_pct > InpPreCrossGapPct) return 0;

   bool long_setup = (prev_close2 <= ma13_prev2 && prev_close1 > ma13_prev1 && ma5_prev1 < ma13_prev1);
   bool short_setup = (prev_close2 >= ma13_prev2 && prev_close1 < ma13_prev1 && ma5_prev1 > ma13_prev1);

   if(long_setup) return +1;
   if(short_setup) return -1;
   return 0;
}

//+------------------------------------------------------------------+
//| v3.0 Layer 2: post_n 计数器更新 (每根 M30 bar 调用)              |
//| 根据 M30 SMA5/13 穿越状态,更新全局 g_post_n_counter              |
//+------------------------------------------------------------------+
void UpdatePostNState()
{
   // 检测当前 M30 bar 是否穿越 (good/bad)
   double fast_buf[], slow_buf[];
   if(!GetMALastN(g_ma_fast_m30, 2, fast_buf)) { g_post_n_counter = 0; g_last_cross_dir = 0; return; }
   if(!GetMALastN(g_ma_slow_m30, 2, slow_buf)) { g_post_n_counter = 0; g_last_cross_dir = 0; return; }

   bool curr_above = fast_buf[0] > slow_buf[0];
   bool prev_above = fast_buf[1] > slow_buf[1];
   bool is_good = !prev_above && curr_above;  // 金叉
   bool is_bad  = prev_above && !curr_above;  // 死叉

   if(is_good)
   {
      g_post_n_counter = 1;
      g_last_cross_dir = +1;
      return;
   }
   if(is_bad)
   {
      g_post_n_counter = -1;
      g_last_cross_dir = -1;
      return;
   }

   // 无新穿越: 延续当前方向
   if(curr_above && g_last_cross_dir > 0)
   {
      g_post_n_counter = (g_post_n_counter > 0) ? g_post_n_counter + 1 : 1;
   }
   else if(!curr_above && g_last_cross_dir < 0)
   {
      g_post_n_counter = (g_post_n_counter < 0) ? g_post_n_counter - 1 : -1;
   }
   else
   {
      // SMA 关系反转但无穿越 (跨过又回来): 重置
      g_post_n_counter = 0;
      g_last_cross_dir = 0;
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   static datetime last_check = 0;
   datetime now = TimeCurrent();
   if(now - last_check < InpCheckSec) return;
   last_check = now;

   // Check for new M30 bar — v3.15: use iTime() directly. iBarShift(..., exact=true)
   // returns -1 on most ticks in tester (TimeCurrent() rarely equals a bar open), so
   // the old code exited at line 844 on every tick, never setting new_m30_bar.
   datetime cur_bar = iTime(InpSymbol, InpM30Period, 0);
   if(cur_bar == 0) return;

   bool new_m30_bar = false;

   if(cur_bar != g_last_m30_bar)
   {
      new_m30_bar = true;
      g_last_m30_bar = cur_bar;
      g_signal_fired = false;
      Print("--- New M30 bar: ", cur_bar, " ---");
   }

   // Check for new H2 bar — v3.15: same iTime fix
   datetime cur_h2 = iTime(InpSymbol, InpH2Period, 0);
   if(cur_h2 != 0 && cur_h2 != g_last_h2_bar)
   {
      g_last_h2_bar = cur_h2;
      Print("--- New H2 bar:  ", cur_h2, " ---");
   }

   // Get M30 rates (need enough for SMMA warmup + stop calc)
   const int SMA_WARMUP = InpSlowMA + 5;
   MqlRates rates[];
   int n_rates = GetM30Rates(rates, MathMax(SMA_WARMUP + 10, InpStopLookback));
   if(n_rates < SMA_WARMUP) return;

   double fast_ma[], slow_ma[];
   int n_sma = GetM30SMAArrays(fast_ma, slow_ma, n_rates);
   if(n_sma < SMA_WARMUP) return;

   // Most recently completed bar index = n_rates - 2
   int comp_idx = n_rates - 2;

   // Current (forming) bar values
   double ma5_curr  = fast_ma[n_sma - 1];
   double ma13_curr = slow_ma[n_sma - 1];

   // Last completed bar SMA
   double ma5_prev  = fast_ma[n_sma - 2];
   double ma13_prev = slow_ma[n_sma - 2];

   // Prev2 completed bar SMA (for cross detection)
   double ma5_prev2 = fast_ma[n_sma - 3];
   double ma13_prev2 = slow_ma[n_sma - 3];

   // M30 cross on last completed bar
   bool curr_above = ma5_prev  > ma13_prev;
   bool prev_above = ma5_prev2 > ma13_prev2;
   int cross = 0;
   if(!prev_above && curr_above) cross = +1;
   else if(prev_above && !curr_above) cross = -1;

   // H2 filter
   int h2_dir = H2Filter();

   // v3.15: compute 2H cross BEFORE [STATUS]/CSV block (was after, broke compile when
   // CSV block moved up — needed h2_cross column for every new M30 bar).
   int h2_x = H2CrossDetector();

   // Get last completed bar OHLC for entry/stop calculation
   double O = rates[n_rates - 2].open;
   double H = rates[n_rates - 2].high;
   double L = rates[n_rates - 2].low;
   double C = rates[n_rates - 2].close;
   double tp = (H + L + C) / 3.0;   // typical price = entry


   if(new_m30_bar)
   {
      Print("[STATUS] M30: SMA5=", DoubleToString(ma5_prev,3),
            " SMA13=", DoubleToString(ma13_prev,3),
            " Cross=", cross == 1 ? "GOLDEN" : (cross == -1 ? "DEAD" : "none"),
            " EntryTP=", DoubleToString(tp, 3),
            " | H2Dir=", h2_dir == 1 ? "BULL" : (h2_dir == -1 ? "BEAR" : "NEUTRAL"),
            " | Stages=", OurStageCount(), "/", InpMaxPos);

      // v3.15: CSV write moved here (was after early-returns, so rows were
      // silently skipped on bars where a signal fired). Now runs every new M30 bar.
      if(g_csv_handle != INVALID_HANDLE)
      {
         string decision  = "HOLD";
         string skip_rsn  = "";
         if(g_signal_fired)
            decision = "SIGNAL";
         else if(cross == 0 && h2_x == 0)
         { decision = "SKIP"; skip_rsn = "no_cross_m30_or_h2"; }
         else if(h2_dir == 0)
         { decision = "SKIP"; skip_rsn = "h2_neutral"; }
         else if(((cross == +1 && h2_dir != +1) || (cross == -1 && h2_dir != -1)) &&
                 !(h2_x != 0 && h2_x == h2_dir))
         { decision = "SKIP"; skip_rsn = "no_trigger"; }
         else if(OurStageCount() >= InpMaxPos)
         { decision = "SKIP"; skip_rsn = "max_pos"; }
         // (Other skip reasons like stop_invalid / stop_out_of_range
         //  happen inside the signal block below; we only catch the gating cases here.)

         // Pull H2 SMA5 value for the row
         double h2_sma5_buf[];
         string h2_sma5_str = "";
         double h2_dist_pct = 0;
         if(GetMALastN(g_ma_fast_h2, 1, h2_sma5_buf) && ArraySize(h2_sma5_buf) > 0)
         {
            h2_dist_pct = (C - h2_sma5_buf[0]) / h2_sma5_buf[0] * 100.0;
            h2_sma5_str = DoubleToString(h2_sma5_buf[0], 5);
         }

         int written = (int)FileWrite(g_csv_handle,
            TimeToString(cur_bar, TIME_DATE|TIME_MINUTES),
            DoubleToString(C, 5),
            DoubleToString(ma5_prev, 5),
            DoubleToString(ma13_prev, 5),
            (cross == +1 ? "GOLDEN" : (cross == -1 ? "DEAD" : "NONE")),
            DoubleToString(C, 5),                  // h2_close (last completed M30 bar close used as proxy)
            h2_sma5_str,
            DoubleToString(h2_dist_pct, 4),
            (h2_dir == 1 ? "BULL" : (h2_dir == -1 ? "BEAR" : "NEUTRAL")),
            (h2_x == +1 ? "GOLDEN" : (h2_x == -1 ? "DEAD" : "NONE")),
            "",                                    // stop_sma filled inside signal block (not visible here)
            "",                                    // stop_pts
            decision,
            skip_rsn);

         static int csv_row_count = 0;
         csv_row_count++;
         if(written <= 0)
            Print("[CSV] FileWrite FAILED row=", csv_row_count, " err=", GetLastError(),
                  " handle=", g_csv_handle);
         else
         {
            FileFlush(g_csv_handle);
            if(csv_row_count <= 3 || csv_row_count % 1000 == 0)
               Print("[CSV] row #", csv_row_count, " written OK  bar=",
                     TimeToString(cur_bar, TIME_DATE|TIME_MINUTES),
                     " decision=", decision, " skip=", skip_rsn);
         }
      }
   }

   // --- MANAGE EXISTING POSITIONS (v3.10 3-stage) ---
   // Cache current price once per tick
   double cur_price = SymbolInfoDouble(InpSymbol, SYMBOL_BID);

   // Stages 1 & 2: TP + trail + M30 cross-exit
   for(int stage = 1; stage <= 2; stage++)
   {
      if(g_stage_tickets[stage] == 0) continue;
      ulong  ticket = 0;
      double entry  = 0, sl = 0, vol = 0;
      if(!FindOurStagePos(stage, ticket, entry, sl, vol))
      {
         // Position disappeared (SL hit / manual close)
         if(InpDebugStages)
            Print("[STAGE", stage, "] position gone, clearing state");
         g_stage_tickets[stage] = 0;
         g_stage2_trail_on[stage] = false;
         continue;
      }
      int action = CheckStageExit(stage, ticket, entry, g_stage_orig_sl[stage],
                                  cur_price, h2_x);
      if(action == 1)
      {
         Print("[EXIT] stage ", stage, " ticket=", ticket);
         ClosePos(ticket);
         g_stage_tickets[stage] = 0;
         g_stage2_trail_on[stage] = false;
      }
   }

   // Stage 3: passive, exits on M30 opposite cross (matches Python best variant).
   if(InpStage3On && g_stage_tickets[3] != 0)
   {
      ulong  ticket = 0;
      double entry  = 0, sl = 0, vol = 0;
      if(!FindOurStagePos(3, ticket, entry, sl, vol))
      {
         if(InpDebugStages)
            Print("[STAGE3] position gone, clearing state");
         g_stage_tickets[3] = 0;
      }
      else
      {
         ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         bool reverse = (ptype == POSITION_TYPE_BUY  && cross == -1)
                     || (ptype == POSITION_TYPE_SELL && cross == +1);
         if(reverse)
         {
            Print("[STAGE3 M30 EXIT] ticket=", ticket, " M30 cross=", cross,
                  " pos_type=", (ptype == POSITION_TYPE_BUY ? "BUY" : "SELL"));
            ClosePos(ticket);
            g_stage_tickets[3] = 0;
         }
      }
   }

   // --- v3.0 CHECK NEW SIGNAL (Layer 1 + Layer 2 三模式 + Layer 3) ---
   if(g_signal_fired) return;
   if(OurStageCount() >= InpMaxPos) return;

   // v3.0: 更新 post_n 状态 (基于当前 M30 SMA5/13 关系)
   UpdatePostNState();

   int  signal_dir = 0;        // +1=BUY, -1=SELL, 0=no signal
   string signal_src = "";     // "pre_cross" / "cross" / "post_n{N}"
   int pre_cross = DetectPreCross(rates[n_rates - 3].close, rates[n_rates - 2].close,
                                  ma5_prev, ma13_prev, ma13_prev2);
   bool is_pre_cross_mode = (pre_cross != 0);
   bool is_cross_mode = (cross != 0);
   bool is_post_n_mode = (g_post_n_counter >= InpPostNMin && g_post_n_counter <= InpPostNMax);
   bool is_post_n_mode_neg = (g_post_n_counter <= -InpPostNMin && g_post_n_counter >= -InpPostNMax);

   // Mode priority: pre_cross > cross > post_n, matching Python de-dup priority.
   if(is_pre_cross_mode)
   {
      signal_dir = pre_cross;
      signal_src = "pre_cross";
   }
   else if(is_cross_mode)
   {
      signal_dir = cross;
      signal_src = "cross";
   }
   else if(is_post_n_mode)
   {
      signal_dir = +1;
      signal_src = "post_n" + IntegerToString(g_post_n_counter);
   }
   else if(is_post_n_mode_neg)
   {
      signal_dir = -1;
      signal_src = "post_n" + IntegerToString(-g_post_n_counter);
   }

   if(signal_dir != 0)
   {
      // === Layer 1 硬门 (应用到所有模式) ===
      if(InpUseLayer1)
      {
         double bias55 = CalcBias55();
         if(bias55 <= InpBias55Threshold)
         {
            if(InpDebugStages) Print("[V3 SKIP] Layer 1: |Bias_55|=", DoubleToString(bias55, 2),
                                       "% <= threshold ", DoubleToString(InpBias55Threshold, 1), "%");
            return;
         }
         if(InpDebugStages) Print("[V3 LAYER 1 PASS] |Bias_55|=", DoubleToString(bias55, 2), "%");
      }

      // === Layer 3 Bias_5 top X% ===
      if(InpUseLayer3)
      {
         double bias5 = CalcBias5();
         if(!IsBias5TopPct(bias5))
         {
            if(InpDebugStages) Print("[V3 SKIP] Layer 3: Bias_5=", DoubleToString(bias5, 2),
                                       "% < top ", DoubleToString(InpBias5TopPct, 1), "% threshold");
            return;
         }
         if(InpDebugStages) Print("[V3 LAYER 3 PASS] Bias_5=", DoubleToString(bias5, 2),
                                  "% >= top ", DoubleToString(InpBias5TopPct, 1), "% threshold");
      }

      // === SL 计算 ===
      double stop_price = 0;
      double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
      if(point == 0) point = 0.001;
      if(is_pre_cross_mode || is_cross_mode)
      {
         // pre_cross/cross: SL = previous segment SMA13 extreme (FindStopSMA).
         int seg_dir = (signal_dir == +1) ? -1 : +1;
         double stop_sma = FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
         if(stop_sma <= 0)
         {
            Print("[V3 SKIP] ", signal_src, " 模式: 上一段 SMA13 无有效极值");
            return;
         }
         stop_price = NormalizeDouble(stop_sma, 5);
      }
      else
      {
         // post_n: SL = 当前 K 线 SMA13 (动态)
         double sma13_now = ma13_prev;  // 已完成 bar 的 SMA13
         if(signal_dir == +1 && sma13_now >= ma5_prev)
         {
            Print("[V3 SKIP] post_n LONG: SMA13=", DoubleToString(sma13_now, 5),
                  " >= close=", DoubleToString(ma5_prev, 5));
            return;
         }
         if(signal_dir == -1 && sma13_now <= ma5_prev)
         {
            Print("[V3 SKIP] post_n SHORT: SMA13=", DoubleToString(sma13_now, 5),
                  " <= close=", DoubleToString(ma5_prev, 5));
            return;
         }
         stop_price = NormalizeDouble(sma13_now, 5);
      }

      // Real-time entry price
      double real_entry_raw = (signal_dir == +1)
         ? SymbolInfoDouble(InpSymbol, SYMBOL_ASK)
         : SymbolInfoDouble(InpSymbol, SYMBOL_BID);
      if(real_entry_raw <= 0)
      {
         Print("[SKIP] ASK/BID not available at signal time");
         return;
      }
      double real_entry = NormalizeDouble(real_entry_raw, 5);

      double stop_pts = MathAbs(real_entry - stop_price) / point;

      // spec 检查 [InpStopLo, InpStopHi] pt (MQL5 points)
      if(stop_pts < InpStopLo || stop_pts > InpStopHi)
      {
         Print("[V3 SKIP] stop_pts=", DoubleToString(stop_pts, 0),
               " outside spec [", DoubleToString(InpStopLo, 0), "-",
               DoubleToString(InpStopHi, 0), "] MQL5 pts = [",
               DoubleToString(InpStopLo/1000.0, 1), "-",
               DoubleToString(InpStopHi/1000.0, 1), "] spec 点");
         return;
      }

      double entry = real_entry;

      string dir = (signal_dir == +1) ? "BUY" : "SELL";
      Print("[V3 SIGNAL] ", dir, "! mode=", signal_src,
            " post_n=", g_post_n_counter,
            " stop_dist=", DoubleToString(stop_pts/1000.0, 1), " spec点",
            " — opening ", InpStageCount, " stages x ",
            DoubleToString(InpLotsPerStage, 2), " lots");

      for(int stage = 1; stage <= InpStageCount; stage++)
      {
         ulong t = Execute(dir, entry, stop_price, InpLotsPerStage, stage);
         if(t == 0)
            Print("[V3 WARN] stage ", stage, " Execute returned 0");
      }
      g_signal_fired = true;
   }

   // v3.15: CSV write block was moved to right after the [STATUS] print
   // (above) so it runs every new M30 bar, even when a signal fires.
}
//+------------------------------------------------------------------+



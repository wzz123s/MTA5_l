//+------------------------------------------------------------------+
//|                                         30m2H_Strategy_EA.mq5    |
//|                                                          Codex    |
//|                                        30m x 2H SMA5/13 Strategy |
//|                                        v3.24: Python-compatible SMMA (mean-init) for Bias_55/Bias_5   |
//|                                        v3.23: removed legacy M15 close-side filter (CLOSE_SIDE_FAIL) — post_n restored |
//|                                        v3.22: dynamic lot sizing from InpRiskPct + pre-trade margin check |
//|                                        v3.21: strategy package sync + dedicated CSV export filename    |
//|                                        v3.20: real-time M15 slot1 early-entry + H2 q2 early-gate     |
//|                                        NOTE: slot2 falls back to normal M30-close execution           |
//|                                        v3.19: H2 q2 early-gate + merged stage3 exit                  |
//|                                        v3.18: balanced final sizing + current mainline defaults       |
//|                                          Layer 1: |H2 Bias_55| > 3.0% 硬门 (应用到所有模式)           |
//|                                          Layer 2: pre_cross + cross + post_n(N=2-6), spec [5, 35]     |
//|                                          Layer 3: H2 Bias_5 top 34%                                   |
//|                                          Stage lots: 0.01 / 0.02 / 0.03                               |
//|                                        v3.17: FindStopSMA rollback to v3.15 — only MIN_BARS=30 guard |
//|                                        v3.16: REVERTED — 4-guard MAX_DIST_PTS=100 was wrong |
//|                                        v3.15: iBarShift->iTime, CSV before signal return |
//|                                        v3.13: H2 filter = SMA5 vs SMA13 |
//|                                        v3.12: CSV signal export   |
//|                                        v3.11: InpH2Thresh 0.5->0.0     |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "3.23"
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
input bool    InpUseDynamicLots = true;     // true=dynamic lots from InpRiskPct + stop (recommended), false=fixed InpStageXLots

input group "=== v3.0 Layer Config ==="
input double  InpBias55Threshold = 3.0;     // Layer 1 硬门: |H2 Bias_55| > X% (默认 3.0%)
input double  InpPreCrossGapPct  = 0.300;      // Layer 2 pre_cross: abs(SMMA5-SMMA13)/SMMA13 <= X%
input int     InpPostNMin        = 2;          // Layer 2 post_n 起始 (含), N ∈ [Min, Max]
input int     InpPostNMax        = 6;          // Layer 2 post_n 终止 (含), 默认 6
input bool    InpUseLayer1       = true;        // 启用 Layer 1 硬门
input bool    InpUseH2EarlyGateQ2 = true;       // Layer 1 q2 early-gate (当前主线保留)
input int     InpH2EarlyGateQ    = 2;           // H2 走完前 q 根 M30 后允许提前估算 Bias_55
input bool    InpUseLayer3       = true;        // 启用 Layer 3 Bias_5 top X%
input double  InpBias5TopPct     = 34.0;        // Layer 3: Bias_5 top X% (最终主线 34%)
input int     InpBias5Lookback   = 500;         // Layer 3 Bias_5 历史滚动计算窗口 (H2 bars)

input group "=== M15 Early Entry ==="
input bool    InpUseM15EarlyEntry = true;       // 启用实时版 M15 slot1 early-entry
input bool    InpUseM15RescueTag  = true;       // 日志上保留 rescue 语义（执行口径仍是实时版）
input ENUM_TIMEFRAMES InpM15Period = PERIOD_M15; // 小周期确认
input bool    InpVerboseDecisionDiag = true;    // 输出逐层判定诊断日志

input group "=== Split TP (v3.10) ==="
input int     InpStageCount   = 3;          // Number of sub-orders per signal (1-3)
input double  InpStage1Lots  = 0.01;       // Stage 1 lots (final balanced sizing: 0.5 unit)
input double  InpStage2Lots  = 0.02;       // Stage 2 lots (final balanced sizing: 1.0 unit)
input double  InpStage3Lots  = 0.03;       // Stage 3 lots (final balanced sizing: 1.5 units)
input double  InpStage1R      = 2.0;        // Stage 1: TP in R multiples (final mainline 2.0R)
input double  InpStage2TrailR = 1.5;        // Stage 2: start 30m SMA13 trailing after N R
input double  InpStage2ForceR = 4.0;        // Stage 2: forced close at N R
input int     InpH2CrossBars  = 3;          // Bars used to confirm 2H SMA5/13 cross
input bool    InpStage3On     = true;       // Enable Stage 3 passive (exit on M30 merged direction flip)
input bool    InpDebugStages  = true;       // Verbose per-stage logs
input bool    InpExportCSV    = true;       // Export per-bar signals to CSV (30m2H_strategy_signals_export.csv)

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
int g_ma_slow_m15;
CTrade g_trade;

//--- Bar tracking
datetime g_last_m30_bar = 0;
datetime g_last_h2_bar  = 0;
datetime g_last_m15_bar = 0;
bool     g_signal_fired = false;
datetime g_signal_anchor_time = 0;

//--- v3.0 post_n 状态机 (M30 SMA5/13 穿越后第 N 根)
int      g_post_n_counter = 0;          // 原始 方向 post_n
int      g_merged_post_n_counter = 0;   // v3.23: 合并后 方向 post_n (matches Python merged_post_cross_n)
double   g_last_cross_dir = 0;
int      g_merged_last_dir = 0;         // v3.23: 合并后最后方向

//--- v3.0 Layer 3 状态 (Bias_5 top X% 阈值缓存)
double   g_bias5_top_threshold = 0;     // Bias_5 滚动 top X% 阈值 (H2 close 偏离 SMMA5)
bool     g_bias5_history_ready = false; // 是否已计算过阈值

//--- 3-stage split TP state (v3.10)
// Magic-number stage offsets from InpMagic (must be ulong to match InpMagic type)
const ulong MAGIC_STAGE1 = 1;   // InpMagic+1 = stage 1 (2.0R close, 0.01 lot)
const ulong MAGIC_STAGE2 = 2;   // InpMagic+2 = stage 2 (SMA13 trail + 4R force, 0.02 lot)
const ulong MAGIC_STAGE3 = 3;   // InpMagic+3 = stage 3 (let profits run, M30 merged exit, 0.03 lot)

// Per-stage state, indexed 1..3 (index 0 unused)
ulong  g_stage_tickets[4];     // position ticket for this stage (0 = no position)
double g_stage_entry[4];       // fill price for R calc
double g_stage_orig_sl[4];     // original SL at fill (used for R, NOT ratchet SL)
bool   g_stage2_trail_on[4];   // true once stage 2 reaches InpStage2TrailR

//--- merged direction settings (Python prepare(..., min_len=8))
const int M30_MERGED_MIN_LEN = 8;

//--- CSV export (v3.21)
int g_csv_handle = INVALID_HANDLE;   // 30m2H_strategy_signals_export.csv file handle
string g_csv_path = "30m2H_strategy_signals_export.csv";

string DirText(int signal_dir)
{
   if(signal_dir > 0) return "BUY";
   if(signal_dir < 0) return "SELL";
   return "NONE";
}

void DiagLog(string tag, string phase, string detail)
{
   if(!InpVerboseDecisionDiag) return;
   Print(tag, " [DIAG] ", phase, " | ", detail);
}

//+------------------------------------------------------------------+
//| v3.24: Python-compatible SMMA — matches calc_smma() init          |
//| Python: init = mean of first N values, then (1*C + (N-1)*prev)/N  |
//| MT5 built-in: init = first price → different early values         |
//+------------------------------------------------------------------+
double PythonSMMA(string symbol, ENUM_TIMEFRAMES tf, int period, int shift)
{
   static string _last_symbol = "";
   static ENUM_TIMEFRAMES _last_tf = 0;
   static double _buf[];
   static int _buf_size = 0;
   static bool _ready = false;
   static datetime _last_bar = 0;

   datetime cur_bar = iTime(symbol, tf, shift);
   if(cur_bar == 0) return 0;

   // Rebuild buffer if symbol/tf changed or new bar arrived
   if(symbol != _last_symbol || tf != _last_tf || cur_bar != _last_bar || !_ready)
   {
      _last_symbol = symbol; _last_tf = tf; _last_bar = cur_bar;
      int total = Bars(symbol, tf);
      if(total < period + 1) { _ready = false; return 0; }
      if(total > _buf_size)
      {
         ArrayResize(_buf, total);
         _buf_size = total;
         for(int j = 0; j < total; j++) _buf[j] = 0;
      }

      double closes[];
      ArraySetAsSeries(closes, true);
      if(CopyClose(symbol, tf, 0, total, closes) <= 0) { _ready = false; return 0; }

      // Init: average of first N prices (matching Python)
      double sum = 0;
      for(int j = 0; j < period; j++)
         sum += closes[total - 1 - j];  // oldest N bars
      _buf[period - 1] = sum / period;

      // Recurrence: (1*close + (n-1)*prev) / n
      for(int j = period; j < total; j++)
      {
         int idx = total - 1 - j;
         _buf[j] = (closes[idx] + (period - 1) * _buf[j - 1]) / period;
      }
      _ready = true;
   }

   int target = iBarShift(symbol, tf, cur_bar);
   if(target < 0 || target >= _buf_size) return 0;
   return _buf[target];
}

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("========================================");
   Print("  30m x 2H EA v3.23 - Initializing (post_n fixes, 2026-07-09)");
   Print("========================================");
   Print("  [Layer 1] InpBias55Threshold = ", DoubleToString(InpBias55Threshold, 1),
         "% (|H2 Bias_55| 硬门, 默认 3.0%)");
   Print("  [Layer 1] InpUseLayer1 = ", InpUseLayer1 ? "TRUE" : "FALSE (Layer 1 禁用)");
   Print("  [Layer 1] H2 early-gate q", InpH2EarlyGateQ, " = ",
         InpUseH2EarlyGateQ2 ? "TRUE" : "FALSE");
   Print("  [Layer 2] pre_cross gap <= ", DoubleToString(InpPreCrossGapPct, 3), "% (close crosses SMMA13)");
   Print("  [Layer 2] post_n range = [", InpPostNMin, ", ", InpPostNMax, "]");
   Print("  [Layer 2] spec range = [", DoubleToString(InpStopLo/1000, 1), ", ", DoubleToString(InpStopHi/1000, 1), "] pt");
   Print("  [Layer 3] InpBias5TopPct = ", DoubleToString(InpBias5TopPct, 1),
         "% (Bias_5 top X%, 最终主线 34%)");
   Print("  [Layer 3] InpUseLayer3 = ", InpUseLayer3 ? "TRUE" : "FALSE");
   Print("  [M15] real-time slot1 early-entry = ", InpUseM15EarlyEntry ? "TRUE" : "FALSE");
   Print("  [Diag] verbose decision log = ", InpVerboseDecisionDiag ? "TRUE" : "FALSE");
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
   g_ma_slow_m15 = iMA(InpSymbol, InpM15Period, InpSlowMA, 0, MODE_SMMA, PRICE_CLOSE);

   if(g_ma_fast_m30 == INVALID_HANDLE || g_ma_slow_m30 == INVALID_HANDLE ||
       g_ma_fast_h2  == INVALID_HANDLE || g_ma_slow_h2  == INVALID_HANDLE ||
       g_h2_sma5 == INVALID_HANDLE || g_h2_sma13 == INVALID_HANDLE ||
       g_h2_sma55 == INVALID_HANDLE || g_h2_sma144 == INVALID_HANDLE ||
       g_h2_sma233 == INVALID_HANDLE || g_ma_slow_m15 == INVALID_HANDLE)
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
   Print("  Split TP: ", InpStageCount, " stage(s); final balanced lots S1/S2/S3 = ",
         DoubleToString(InpStage1Lots, 2), " / ",
         DoubleToString(InpStage2Lots, 2), " / ",
         DoubleToString(InpStage3Lots, 2));
    Print("    Stage 1: ", DoubleToString(InpStage1R, 2), "R close");
    Print("    Stage 2: trail after ", DoubleToString(InpStage2TrailR, 2),
          "R, force close at ", DoubleToString(InpStage2ForceR, 2), "R");
    Print("    Stage 3: ", InpStage3On ? "ON (M30 merged direction exit)" : "OFF");
    Print("  [NOTE] M15 early-entry now executes on slot1 in real time; slot2 remains the normal M30-close fallback.");
    Print("  [v3.22] Dynamic lots: ", InpUseDynamicLots ? "TRUE (InpRiskPct=" + DoubleToString(InpRiskPct, 1) + "% of balance, balanced ratio 0.5:1.0:1.5)" : "FALSE (fixed InpStageXLots)");
    if(InpUseDynamicLots)
       Print("          Base stage lot ≈ balance × ", DoubleToString(InpRiskPct, 1), "% ÷ stop_distance. Total 3-stage risk = ", DoubleToString(InpRiskPct, 1), "% of equity.");

   // v3.11: open CSV export file (if enabled)
   if(InpExportCSV)
   {
      g_csv_handle = FileOpen(g_csv_path, FILE_WRITE|FILE_CSV|FILE_SHARE_READ|FILE_ANSI, ",");
      if(g_csv_handle == INVALID_HANDLE)
         Print("[WARN] Could not open CSV file: ", GetLastError());
      else
      {
         // Header (v3.23: added h2_sma13, h2_sma55 for Python data alignment)
         FileWrite(g_csv_handle,
            "bar_time", "close", "m30_sma5", "m30_sma13",
            "m30_cross", "h2_close", "h2_sma5", "h2_sma13", "h2_sma55",
            "h2_dist_pct", "h2_dir",
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
   if(g_ma_slow_m15 != INVALID_HANDLE) IndicatorRelease(g_ma_slow_m15);

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
//| Estimate H2 Bias_55 using current partial H2 close after q M30s  |
//| Mirrors Python early_precompute(..., q2, use_early_factor=False) |
//+------------------------------------------------------------------+
bool CalcBias55EarlyQ(double &est_bias55, int &elapsed_q)
{
   est_bias55 = 0.0;
   elapsed_q = 0;

   datetime current_h2_open = iTime(InpSymbol, InpH2Period, 0);
   datetime last_m30_open = iTime(InpSymbol, InpM30Period, 1);
   if(current_h2_open <= 0 || last_m30_open < current_h2_open)
      return false;

   elapsed_q = (int)((last_m30_open - current_h2_open) / 1800) + 1;
   if(elapsed_q < InpH2EarlyGateQ)
      return false;

   double sma55_prev[];
   if(!GetMALastN(g_h2_sma55, 2, sma55_prev) || ArraySize(sma55_prev) < 2)
      return false;

   double prev_sma55 = sma55_prev[1];
   if(prev_sma55 == 0 || prev_sma55 == EMPTY_VALUE)
      return false;

   double partial_close = iClose(InpSymbol, InpM30Period, 1);
   if(partial_close <= 0)
      return false;

   double est_sma55 = prev_sma55 + (partial_close - prev_sma55) / InpH2SMA55;
   if(est_sma55 == 0 || est_sma55 == EMPTY_VALUE)
      return false;

   est_bias55 = MathAbs((partial_close - est_sma55) / est_sma55) * 100.0;
   return true;
}

int RawDirCode(bool curr_above, bool prev_above)
{
   if(curr_above && !prev_above) return 2;   // good
   if(!curr_above && prev_above) return -2;  // bad
   if(curr_above && prev_above) return 1;    // up
   return -1;                                // down
}

int RawDirSign(int code)
{
   return code > 0 ? 1 : -1;
}

//+------------------------------------------------------------------+
//| Compute merged direction sign on the last completed M30 bar       |
//| Approximation-port of processing.segment_filter.filter_short_...  |
//+------------------------------------------------------------------+
int M30MergedDirectionLastCompleted()
{
   int need = 120;
   double fast[], slow[];
   if(!GetMABars(g_ma_fast_m30, need, fast)) return 0;
   if(!GetMABars(g_ma_slow_m30, need, slow)) return 0;
   if(ArraySize(fast) < need || ArraySize(slow) < need) return 0;

   int completed = need - 1; // ignore newest forming bar
   int dir_codes[];
   ArrayResize(dir_codes, completed);
   if(completed <= 0) return 0;

   bool prev_above = fast[0] > slow[0];
   dir_codes[0] = prev_above ? 1 : -1;
   for(int i = 1; i < completed; i++)
   {
      bool curr_above = fast[i] > slow[i];
      dir_codes[i] = RawDirCode(curr_above, prev_above);
      prev_above = curr_above;
   }

   int crossings[];
   int cross_types[];
   int cross_count = 0;
   ArrayResize(crossings, completed);
   ArrayResize(cross_types, completed);
   for(int i = 0; i < completed; i++)
   {
      if(MathAbs(dir_codes[i]) == 2)
      {
         crossings[cross_count] = i;
         cross_types[cross_count] = dir_codes[i];
         cross_count++;
      }
   }
   if(cross_count == 0)
      return RawDirSign(dir_codes[completed - 1]);

   int first_type = cross_types[0];
   int state = (first_type == 2) ? -1 : 1; // good before = down, bad before = up
   int i = 0;
   while(i < cross_count)
   {
      int pos = crossings[i];
      int type_ = cross_types[i];
      if(i + 1 >= cross_count)
         break; // last crossing always survives

      int next_pos = crossings[i + 1];
      int region_count = 0;
      for(int k = pos + 1; k < next_pos; k++)
      {
         if(type_ == 2 && dir_codes[k] == 1) region_count++;
         if(type_ == -2 && dir_codes[k] == -1) region_count++;
      }

      if(region_count < M30_MERGED_MIN_LEN)
      {
         dir_codes[pos] = state;
         for(int k = pos + 1; k < next_pos; k++)
            dir_codes[k] = state;
         dir_codes[next_pos] = state;

         for(int s = i + 2; s < cross_count; s++)
         {
            crossings[s - 2] = crossings[s];
            cross_types[s - 2] = cross_types[s];
         }
         cross_count -= 2;
         if(cross_count <= 0)
            break;
         continue;
      }

      state = (type_ == 2) ? 1 : -1;
      i++;
   }

   return RawDirSign(dir_codes[completed - 1]);
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
      // Stage 1: final mainline R profit -> full close
      if(rr >= InpStage1R)
      {
         if(InpDebugStages)
            Print("[STAGE1 TP] ticket=", ticket, " rr=", DoubleToString(rr, 2),
                  " >= ", DoubleToString(InpStage1R, 2), " -> close");
         return 1;
      }
   }
   else if(stage == 2)
   {
      // Stage 2: final mainline forced close
      if(rr >= InpStage2ForceR)
      {
         if(InpDebugStages)
            Print("[STAGE2 FORCED] ticket=", ticket, " rr=", DoubleToString(rr, 2),
                  " >= ", DoubleToString(InpStage2ForceR, 2), " -> close");
         return 1;
      }
      // After configured R: start trailing 30m SMA13 (one-shot set g_stage2_trail_on)
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
   }
   else if(stage == 3)
   {
      // Stage 3 always returns 0 (managed separately by M30 merged direction exit in OnTick)
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
//| Normalize explicit stage lot to broker volume constraints          |
//+------------------------------------------------------------------+
double NormalizeLots(double lot)
{
   double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;

   lot = MathMax(InpMinLots, MathMin(InpMaxLots, lot));
   lot = MathFloor(lot / step) * step;
   return NormalizeDouble(MathMax(InpMinLots, lot), 2);
}

//+------------------------------------------------------------------+
//| Final balanced lot size per split stage                            |
//| v3.22: InpUseDynamicLots=true → CalcLot by stop & balance,         |
//|        then distribute per 0.5:1.0:1.5 balanced ratio              |
//+------------------------------------------------------------------+
double StageLots(int stage, double stop_pts = 0)
{
   double base_lot = InpMinLots;

   if(InpUseDynamicLots && stop_pts > 0)
   {
      // Dynamic: CalcLot uses InpRiskPct% of balance against stop_pts.
      // It returns the lot for FULL total risk. We distribute per ratio:
      //   S1=0.5unit, S2=1.0unit, S3=1.5unit → total=3.0units.
      double total_lot = CalcLot(stop_pts);
      // base_lot = total_lot / 3.0 (the 0.5-unit base)
      base_lot = total_lot / 3.0;
      if(base_lot < InpMinLots) base_lot = InpMinLots;
   }
   else
   {
      // Fixed: use explicit input stage lots
      if(stage == 1) return NormalizeLots(InpStage1Lots);
      if(stage == 2) return NormalizeLots(InpStage2Lots);
      if(stage == 3) return NormalizeLots(InpStage3Lots);
      return NormalizeLots(InpMinLots);
   }

   // Apply balanced ratio 0.5 : 1.0 : 1.5
   double stage_mult = 0.5;
   if(stage == 1) stage_mult = 0.5;
   else if(stage == 2) stage_mult = 1.0;
   else if(stage == 3) stage_mult = 1.5;

   return NormalizeLots(base_lot * stage_mult);
}

//+------------------------------------------------------------------+
//| Legacy helper: raw M30 opposite cross exit                         |
//++------------------------------------------------------------------+
bool ShouldExit(ENUM_POSITION_TYPE ptype)
{
   // Get last 4 M30 bars (oldest to newest, newest forming bar ignored)
   MqlRates rates[];
   int n = GetM30Rates(rates, 4);
   if(n < 4) return false;

   double fast[], slow[];
   if(!GetMABars(g_ma_fast_m30, n, fast)) return false;
   if(!GetMABars(g_ma_slow_m30, n, slow)) return false;
   // fast[0]=oldest, fast[n-1]=newest

   // Compare previous completed bar vs last completed bar
   int last_completed = n - 2;
   int prev_completed = n - 3;
   if(prev_completed < 0 || last_completed >= ArraySize(fast)) return false;

   bool curr_above = fast[last_completed] > slow[last_completed];
   bool prev_above = fast[prev_completed] > slow[prev_completed];

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
   if(CopyClose(InpSymbol, InpH2Period, 1, 1, close_arr) <= 0) return 0;
   if(CopyBuffer(g_h2_sma55, 0, 1, 1, sma55_arr) <= 0) return 0;
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
   if(CopyClose(InpSymbol, InpH2Period, 1, 1, close_arr) <= 0) return 0;
   if(CopyBuffer(g_h2_sma5, 0, 1, 1, sma5_arr) <= 0) return 0;
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
   // Exclude the forming H2 bar so the percentile threshold matches the completed-bar pipeline.
   if(CopyClose(InpSymbol, InpH2Period, 1, n, close_arr) <= 0) return false;
   if(CopyBuffer(g_h2_sma5, 0, 1, n, sma5_arr) <= 0) return false;

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

   // 无新穿越: 延续当前方向 (v3.23: do NOT reset on SMA flip without cross —
   // this matches Python post_n definition where counter persists until a real cross)
   if(curr_above && g_last_cross_dir > 0)
   {
      g_post_n_counter = (g_post_n_counter > 0) ? g_post_n_counter + 1 : 1;
   }
   else if(!curr_above && g_last_cross_dir < 0)
   {
      g_post_n_counter = (g_post_n_counter < 0) ? g_post_n_counter - 1 : -1;
   }
   // else: SMA5/SMA13 relationship doesn't match last cross direction, but
   // no new cross occurred — keep the counter, don't reset. Python does the same.
}

//+------------------------------------------------------------------+
//| v3.23: merged post_n counter — matches Python merged_post_cross_n |
//| Uses M30MergedDirectionLastCompleted() which absorbs short segments|
//+------------------------------------------------------------------+
void UpdateMergedPostNState()
{
   int merged = M30MergedDirectionLastCompleted();
   if(merged == 0) return;  // can't determine

   if(g_merged_last_dir == 0)
   {
      // First call
      g_merged_post_n_counter = 1;
      g_merged_last_dir = merged;
      return;
   }

   if(merged != g_merged_last_dir)
   {
      // Merged direction flipped → cross
      if(merged > 0)
         g_merged_post_n_counter = 1;    // merged good cross
      else
         g_merged_post_n_counter = -1;   // merged bad cross
      g_merged_last_dir = merged;
   }
   else
   {
      // Same direction → continue
      if(g_merged_post_n_counter > 0)
         g_merged_post_n_counter++;
      else if(g_merged_post_n_counter < 0)
         g_merged_post_n_counter--;
      else
         g_merged_post_n_counter = (merged > 0) ? 1 : -1;
   }
}

//+------------------------------------------------------------------+
//| Shared Layer 1 gate                                               |
//+------------------------------------------------------------------+
bool PassLayer1Gate(string tag)
{
   if(!InpUseLayer1) return true;

   double bias55 = CalcBias55();
   if(bias55 <= InpBias55Threshold)
   {
      bool early_pass = false;
      double early_bias55 = 0.0;
      int elapsed_q = 0;
      if(InpUseH2EarlyGateQ2 && CalcBias55EarlyQ(early_bias55, elapsed_q) && early_bias55 > InpBias55Threshold)
      {
         early_pass = true;
         if(InpDebugStages)
            Print(tag, " [LAYER1 EARLY PASS] q", elapsed_q,
                  " est |Bias_55|=", DoubleToString(early_bias55, 2),
                  "% > threshold ", DoubleToString(InpBias55Threshold, 1), "%");
         DiagLog(tag, "Layer1",
                 "completed_bias55=" + DoubleToString(bias55, 5) +
                 " threshold=" + DoubleToString(InpBias55Threshold, 5) +
                 " early_bias55=" + DoubleToString(early_bias55, 5) +
                 " elapsed_q=" + IntegerToString(elapsed_q) +
                 " result=EARLY_PASS");
      }
      if(!early_pass)
      {
         if(InpDebugStages)
            Print(tag, " [SKIP] Layer 1: |Bias_55|=", DoubleToString(bias55, 2),
                  "% <= threshold ", DoubleToString(InpBias55Threshold, 1), "%");
         DiagLog(tag, "Layer1",
                 "completed_bias55=" + DoubleToString(bias55, 5) +
                 " threshold=" + DoubleToString(InpBias55Threshold, 5) +
                 " early_bias55=" + DoubleToString(early_bias55, 5) +
                 " elapsed_q=" + IntegerToString(elapsed_q) +
                 " result=FAIL");
         return false;
      }
   }
   if(InpDebugStages)
      Print(tag, " [LAYER1 PASS] |Bias_55|=", DoubleToString(bias55, 2), "%");
   DiagLog(tag, "Layer1",
           "completed_bias55=" + DoubleToString(bias55, 5) +
           " threshold=" + DoubleToString(InpBias55Threshold, 5) +
           " result=PASS");
   return true;
}

//+------------------------------------------------------------------+
//| Shared Layer 3 gate                                               |
//+------------------------------------------------------------------+
bool PassLayer3Gate(string tag)
{
   if(!InpUseLayer3) return true;

   double bias5 = CalcBias5();
   bool pass = IsBias5TopPct(bias5);
   if(!pass)
   {
      if(InpDebugStages)
         Print(tag, " [SKIP] Layer 3: Bias_5=", DoubleToString(bias5, 2),
                "% < top ", DoubleToString(InpBias5TopPct, 1), "% threshold");
      DiagLog(tag, "Layer3",
              "bias5=" + DoubleToString(bias5, 5) +
              " threshold=" + DoubleToString(g_bias5_top_threshold, 5) +
              " top_pct=" + DoubleToString(InpBias5TopPct, 2) +
              " result=FAIL");
      return false;
   }
   if(InpDebugStages)
      Print(tag, " [LAYER3 PASS] Bias_5=", DoubleToString(bias5, 2),
            "% >= top ", DoubleToString(InpBias5TopPct, 1), "% threshold");
   DiagLog(tag, "Layer3",
           "bias5=" + DoubleToString(bias5, 5) +
           " threshold=" + DoubleToString(g_bias5_top_threshold, 5) +
           " top_pct=" + DoubleToString(InpBias5TopPct, 2) +
           " result=PASS");
   return true;
}

//+------------------------------------------------------------------+
//| Execute validated signal at market                                |
//+------------------------------------------------------------------+
bool ExecuteSignalByMarket(int signal_dir, string signal_src, double stop_price,
                           datetime anchor_time, string trigger_tag)
{
   double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   if(point == 0) point = 0.001;

   double real_entry_raw = (signal_dir == +1)
      ? SymbolInfoDouble(InpSymbol, SYMBOL_ASK)
      : SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   if(real_entry_raw <= 0)
   {
      Print(trigger_tag, " [SKIP] ASK/BID not available at signal time");
      DiagLog(trigger_tag, "Execute",
              "mode=" + signal_src +
              " dir=" + DirText(signal_dir) +
              " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
              " result=NO_QUOTE");
      return false;
   }

   double real_entry = NormalizeDouble(real_entry_raw, 5);
   double stop_pts = MathAbs(real_entry - stop_price) / point;
   DiagLog(trigger_tag, "Execute",
           "mode=" + signal_src +
           " dir=" + DirText(signal_dir) +
           " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
           " real_entry=" + DoubleToString(real_entry, 5) +
           " stop_price=" + DoubleToString(stop_price, 5) +
           " stop_pts=" + DoubleToString(stop_pts/1000.0, 3) +
           " spec_lo=" + DoubleToString(InpStopLo/1000.0, 3) +
           " spec_hi=" + DoubleToString(InpStopHi/1000.0, 3));
   if(stop_pts < InpStopLo || stop_pts > InpStopHi)
   {
      Print(trigger_tag, " [SKIP] stop_pts=", DoubleToString(stop_pts, 0),
            " outside spec [", DoubleToString(InpStopLo, 0), "-",
            DoubleToString(InpStopHi, 0), "] MQL5 pts = [",
            DoubleToString(InpStopLo/1000.0, 1), "-",
            DoubleToString(InpStopHi/1000.0, 1), "] spec 点");
      DiagLog(trigger_tag, "Execute",
              "mode=" + signal_src +
              " dir=" + DirText(signal_dir) +
              " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
              " result=SPEC_FAIL");
      return false;
   }

   string dir = (signal_dir == +1) ? "BUY" : "SELL";
   Print(trigger_tag, " [SIGNAL] ", dir, "! mode=", signal_src,
         " stop_dist=", DoubleToString(stop_pts/1000.0, 1), " spec点",
         " anchor=", TimeToString(anchor_time, TIME_DATE|TIME_MINUTES),
         " — opening ", InpStageCount, " balanced stages S1/S2/S3=",
         DoubleToString(InpStage1Lots, 2), "/",
         DoubleToString(InpStage2Lots, 2), "/",
         DoubleToString(InpStage3Lots, 2), " lots");

   // --- v3.22: pre-trade margin/free-margin check ---
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin  = AccountInfoDouble(ACCOUNT_MARGIN);
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double tick_val = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz  = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_val == 0 || tick_sz == 0)
   {
      tick_val = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE) * 0.001;
      tick_sz  = 0.001;
   }

   // Calculate total required margin for the entire 3-stage signal
   double total_lots = 0;
   double stage_lots_arr[4];
   for(int stage = 1; stage <= InpStageCount; stage++)
   {
      stage_lots_arr[stage] = StageLots(stage, stop_pts);
      total_lots += stage_lots_arr[stage];
   }
   double ask_price = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   if(ask_price <= 0) ask_price = real_entry;
   double est_margin = (total_lots * ask_price * 100.0) / 500.0;  // leverage 1:500 assumed
   double est_free_after = free_margin - est_margin;

   Print("  current account state: Balance: ", DoubleToString(balance, 2),
         ", Equity: ", DoubleToString(equity, 2),
         ", Margin: ", DoubleToString(margin, 2),
         ", FreeMargin: ", DoubleToString(free_margin, 2));
   Print("  calculated account state: TotalLots: ", DoubleToString(total_lots, 2),
         ", EstMargin: ", DoubleToString(est_margin, 2),
         ", EstFreeAfter: ", DoubleToString(est_free_after, 2));

   if(est_free_after < 0 && !InpSimMode)
   {
      Print(trigger_tag, " [WARN] insufficient free margin for full signal — ",
            "FreeMargin=", DoubleToString(free_margin, 2),
            " needed≈", DoubleToString(est_margin, 2),
            ". Will attempt stages but expect No money errors.");
      DiagLog(trigger_tag, "Execute",
              "mode=" + signal_src +
              " dir=" + DirText(signal_dir) +
              " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
              " result=LOW_MARGIN free=" + DoubleToString(free_margin, 2) +
              " need=" + DoubleToString(est_margin, 2));
   }

   bool any_opened = false;
   for(int stage = 1; stage <= InpStageCount; stage++)
   {
      double stage_lot = stage_lots_arr[stage];
      ulong t = Execute(dir, real_entry, stop_price, stage_lot, stage);
      if(t == 0)
         Print(trigger_tag, " [WARN] stage ", stage, " Execute returned 0");
      else
         any_opened = true;
   }

   if(any_opened)
   {
      g_signal_anchor_time = anchor_time;
      g_signal_fired = (g_signal_anchor_time == iTime(InpSymbol, InpM30Period, 0));
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Real-time M15 slot1 early-entry                                   |
//| slot2 stays merged into the normal M30-close trigger              |
//+------------------------------------------------------------------+
bool TryM15EarlyEntry(MqlRates &rates[], int n_rates,
                      double &fast_ma[], double &slow_ma[], int n_sma,
                      double ma5_curr, double ma13_curr,
                      double ma5_prev, double ma13_prev,
                      datetime cur_bar)
{
   if(!InpUseM15EarlyEntry) return false;
   if(OurStageCount() >= InpMaxPos)
   {
      DiagLog("[M15 SLOT1]", "Candidate",
              "result=SKIP_MAX_POS stages=" + IntegerToString(OurStageCount()) +
              " max_pos=" + IntegerToString(InpMaxPos));
      return false;
   }

   datetime completed_m15_open = iTime(InpSymbol, InpM15Period, 1);
   if(completed_m15_open <= 0) return false;

   int m30_shift = iBarShift(InpSymbol, InpM30Period, completed_m15_open, false);
   if(m30_shift < 0) return false;

   datetime slot_m30_open = iTime(InpSymbol, InpM30Period, m30_shift);
   if(slot_m30_open <= 0) return false;

   int slot_in_m30 = (int)((completed_m15_open - slot_m30_open) / PeriodSeconds(InpM15Period)) + 1;
   if(slot_in_m30 != 1) return false;
   if(slot_m30_open != cur_bar) return false;

   datetime anchor_time = slot_m30_open + PeriodSeconds(InpM30Period);
   if(g_signal_anchor_time == anchor_time) return false;

   double m15_close_arr[], m15_sma13_arr[];
   if(CopyClose(InpSymbol, InpM15Period, 1, 1, m15_close_arr) <= 0) return false;
   if(CopyBuffer(g_ma_slow_m15, 0, 1, 1, m15_sma13_arr) <= 0) return false;
   double m15_close = m15_close_arr[0];
   double m15_sma13 = m15_sma13_arr[0];
   if(m15_sma13 <= 0 || m15_sma13 == EMPTY_VALUE) return false;

   int signal_dir = 0;
   string signal_src = "";
   int pre_cross = DetectPreCross(rates[n_rates - 2].close, rates[n_rates - 1].close,
                                  ma5_curr, ma13_curr, ma13_prev);
   bool is_pre_cross_mode = (pre_cross != 0);

   bool curr_above = ma5_curr > ma13_curr;
   bool prev_above = ma5_prev > ma13_prev;
   bool is_cross_mode = ((!prev_above && curr_above) || (prev_above && !curr_above));
   bool is_post_n_mode = (g_post_n_counter >= InpPostNMin && g_post_n_counter <= InpPostNMax);
   bool is_post_n_mode_neg = (g_post_n_counter <= -InpPostNMin && g_post_n_counter >= -InpPostNMax);

   if(is_pre_cross_mode)
   {
      signal_dir = pre_cross;
      signal_src = "pre_cross_m15_slot1";
   }
   else if(is_cross_mode)
   {
      signal_dir = curr_above ? +1 : -1;
      signal_src = "cross_m15_slot1";
   }
   else if(is_post_n_mode)
   {
      signal_dir = +1;
      signal_src = "post_n" + IntegerToString(g_post_n_counter) + "_m15_slot1";
   }
   else if(is_post_n_mode_neg)
   {
      signal_dir = -1;
      signal_src = "post_n" + IntegerToString(-g_post_n_counter) + "_m15_slot1";
   }

   if(signal_dir == 0) return false;
   DiagLog("[M15 SLOT1]", "Candidate",
           "mode=" + signal_src +
           " dir=" + DirText(signal_dir) +
           " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
           " m15_close=" + DoubleToString(m15_close, 5) +
           " m15_smma13=" + DoubleToString(m15_sma13, 5) +
           " post_n_counter=" + IntegerToString(g_post_n_counter));
   // v3.23: removed legacy M15 close-side filter (CLOSE_SIDE_FAIL) —
   // the main strategy has moved to M15 replace_any+rescue + H2 early-gate.
   // Close-side filtering was explicitly retired per Python strategy baseline.

   if(!PassLayer1Gate("[M15 SLOT1]")) return false;
   if(!PassLayer3Gate("[M15 SLOT1]")) return false;

   double stop_price = 0.0;
   if(is_pre_cross_mode || is_cross_mode)
   {
      int seg_dir = (signal_dir == +1) ? -1 : +1;
      double stop_sma = FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
      if(stop_sma <= 0)
      {
         if(InpDebugStages)
            Print("[M15 SLOT1] [SKIP] ", signal_src, " 模式: 上一段 SMA13 无有效极值");
         DiagLog("[M15 SLOT1]", "Stop",
                 "mode=" + signal_src + " result=NO_STOP_EXTREME");
         return false;
      }
      stop_price = NormalizeDouble(stop_sma, 5);
   }
   else
   {
      double sma13_now = ma13_curr;
      if(signal_dir == +1 && m15_close <= sma13_now)
      {
         DiagLog("[M15 SLOT1]", "Stop",
                 "mode=" + signal_src + " result=POSTN_STOP_INVALID");
         return false;
      }
      if(signal_dir == -1 && m15_close >= sma13_now)
      {
         DiagLog("[M15 SLOT1]", "Stop",
                 "mode=" + signal_src + " result=POSTN_STOP_INVALID");
         return false;
      }
      stop_price = NormalizeDouble(sma13_now, 5);
   }

   double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   if(point == 0) point = 0.001;
   double m15_stop_pts = MathAbs(m15_close - stop_price) / point;
   DiagLog("[M15 SLOT1]", "Stop",
           "mode=" + signal_src +
           " stop_price=" + DoubleToString(stop_price, 5) +
           " entry_proxy=" + DoubleToString(m15_close, 5) +
           " stop_pts=" + DoubleToString(m15_stop_pts/1000.0, 3));
   if(m15_stop_pts < InpStopLo || m15_stop_pts > InpStopHi)
   {
      DiagLog("[M15 SLOT1]", "Stop",
              "mode=" + signal_src + " result=SPEC_FAIL_PROXY");
      return false;
   }

   if(InpUseM15RescueTag)
      signal_src = signal_src + "_replace_or_rescue";

   return ExecuteSignalByMarket(signal_dir, signal_src, stop_price, anchor_time, "[M15 SLOT1]");
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
   g_signal_fired = (g_signal_anchor_time == cur_bar);

   datetime cur_m15 = iTime(InpSymbol, InpM15Period, 0);
   bool new_m15_bar = false;
   if(cur_m15 != 0)
   {
      if(g_last_m15_bar == 0)
         g_last_m15_bar = cur_m15;
      else if(cur_m15 != g_last_m15_bar)
      {
         new_m15_bar = true;
         g_last_m15_bar = cur_m15;
      }
   }

   if(cur_bar != g_last_m30_bar)
   {
      new_m30_bar = true;
      g_last_m30_bar = cur_bar;
      g_signal_fired = (g_signal_anchor_time == cur_bar);
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

         // Pull H2 SMA values for the row (v3.23: included for Python data alignment)
         double h2_sma5_buf[], h2_sma13_buf[], h2_sma55_buf[];
         string h2_sma5_str = "", h2_sma13_str = "", h2_sma55_str = "";
         double h2_dist_pct = 0;
         if(GetMALastN(g_h2_sma5, 1, h2_sma5_buf) && ArraySize(h2_sma5_buf) > 0)
         {
            h2_dist_pct = (C - h2_sma5_buf[0]) / h2_sma5_buf[0] * 100.0;
            h2_sma5_str = DoubleToString(h2_sma5_buf[0], 5);
         }
         if(GetMALastN(g_h2_sma13, 1, h2_sma13_buf) && ArraySize(h2_sma13_buf) > 0)
            h2_sma13_str = DoubleToString(h2_sma13_buf[0], 5);
         if(GetMALastN(g_h2_sma55, 1, h2_sma55_buf) && ArraySize(h2_sma55_buf) > 0)
            h2_sma55_str = DoubleToString(h2_sma55_buf[0], 5);

         int written = (int)FileWrite(g_csv_handle,
            TimeToString(cur_bar, TIME_DATE|TIME_MINUTES),
            DoubleToString(C, 5),
            DoubleToString(ma5_prev, 5),
            DoubleToString(ma13_prev, 5),
            (cross == +1 ? "GOLDEN" : (cross == -1 ? "DEAD" : "NONE")),
            DoubleToString(C, 5),
            h2_sma5_str,
            h2_sma13_str,
            h2_sma55_str,
            DoubleToString(h2_dist_pct, 4),
            (h2_dir == 1 ? "BULL" : (h2_dir == -1 ? "BEAR" : "NEUTRAL")),
            (h2_x == +1 ? "GOLDEN" : (h2_x == -1 ? "DEAD" : "NONE")),
            "",
            "",
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

   // Stages 1 & 2: TP + trail only (no raw M30 cross exit in current mainline)
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

   // Stage 3: passive, exits on M30 merged direction flip (matches Python best variant).
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
         int merged_sign = M30MergedDirectionLastCompleted();
         bool reverse = (ptype == POSITION_TYPE_BUY  && merged_sign < 0)
                     || (ptype == POSITION_TYPE_SELL && merged_sign > 0);
         if(reverse)
         {
            Print("[STAGE3 MERGED EXIT] ticket=", ticket, " merged_sign=", merged_sign,
                  " pos_type=", (ptype == POSITION_TYPE_BUY ? "BUY" : "SELL"));
            ClosePos(ticket);
            g_stage_tickets[3] = 0;
         }
      }
   }

   // v3.0: 更新 post_n 状态 (基于当前 M30 SMA5/13 关系)
   UpdatePostNState();

   // Real-time M15 slot1 early-entry.
   if(new_m15_bar)
   {
      if(TryM15EarlyEntry(rates, n_rates, fast_ma, slow_ma, n_sma,
                          ma5_curr, ma13_curr, ma5_prev, ma13_prev, cur_bar))
         return;
   }

   // --- v3.0 CHECK NEW SIGNAL (Layer 1 + Layer 2 三模式 + Layer 3) ---
   if(g_signal_fired) return;
   if(OurStageCount() >= InpMaxPos)
   {
      DiagLog("[M30 CLOSE]", "Candidate",
              "result=SKIP_MAX_POS stages=" + IntegerToString(OurStageCount()) +
              " max_pos=" + IntegerToString(InpMaxPos));
      return;
   }
   if(!new_m30_bar) return;

   int  signal_dir = 0;        // +1=BUY, -1=SELL, 0=no signal
   string signal_src = "";     // "pre_cross" / "cross" / "post_n{N}"
   int pre_cross = DetectPreCross(rates[n_rates - 3].close, rates[n_rates - 2].close,
                                  ma5_prev, ma13_prev, ma13_prev2);
   bool is_pre_cross_mode = (pre_cross != 0);
   bool is_cross_mode = (cross != 0);
   bool is_post_n_mode = (g_post_n_counter >= InpPostNMin && g_post_n_counter <= InpPostNMax);
   bool is_post_n_mode_neg = (g_post_n_counter <= -InpPostNMin && g_post_n_counter >= -InpPostNMax);

   // Mode priority: pre_cross > cross > post_n, matching Python de-dup priority.
   // v3.23: post_n is evaluated FIRST as an independent opportunity,
   //        then pre_cross/cross override if active. This matches Python
   //        baseline where all three modes are treated as separate chances.
   if(is_post_n_mode)
   {
      signal_dir = +1;
      signal_src = "post_n" + IntegerToString(g_post_n_counter);
   }
   else if(is_post_n_mode_neg)
   {
      signal_dir = -1;
      signal_src = "post_n" + IntegerToString(-g_post_n_counter);
   }

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

   if(signal_dir != 0)
   {
      DiagLog("[M30 CLOSE]", "Candidate",
              "mode=" + signal_src +
              " dir=" + DirText(signal_dir) +
              " anchor=" + TimeToString(cur_bar, TIME_DATE|TIME_MINUTES) +
              " close=" + DoubleToString(C, 5) +
              " smma5=" + DoubleToString(ma5_prev, 5) +
              " smma13=" + DoubleToString(ma13_prev, 5) +
              " post_n_counter=" + IntegerToString(g_post_n_counter));
      // v3.23: post_n inherits Layer1+Layer3 from the original cross
      bool is_postn = (is_post_n_mode || is_post_n_mode_neg);
      if(!is_postn && !PassLayer1Gate("[M30 CLOSE]")) return;
      if(!is_postn && !PassLayer3Gate("[M30 CLOSE]")) return;


      // === SL 计算 ===
      double stop_price = 0;
      if(is_pre_cross_mode || is_cross_mode)
      {
         // pre_cross/cross: SL = previous segment SMA13 extreme (FindStopSMA).
         int seg_dir = (signal_dir == +1) ? -1 : +1;
         double stop_sma = FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
         if(stop_sma <= 0)
         {
            Print("[V3 SKIP] ", signal_src, " 模式: 上一段 SMA13 无有效极值");
            DiagLog("[M30 CLOSE]", "Stop",
                    "mode=" + signal_src + " result=NO_STOP_EXTREME");
            return;
         }
         stop_price = NormalizeDouble(stop_sma, 5);
      }
      else
      {
         // v3.23: post_n stop uses FindStopSMA (prev segment SMA13 extreme)
         // like pre_cross/cross, instead of current SMA13 which is too close.
         // Python's SMMA diff makes SMA13 gap larger, EA's SMMA makes it near-zero.
         int seg_dir = (signal_dir == +1) ? -1 : +1;
         double stop_sma = FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
         if(stop_sma <= 0)
         {
            DiagLog("[M30 CLOSE]", "Stop",
                    "mode=" + signal_src + " result=POSTN_STOP_INVALID");
            return;
         }
         stop_price = NormalizeDouble(stop_sma, 5);
      }

      double exec_point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
      if(exec_point == 0) exec_point = 0.001;
      DiagLog("[M30 CLOSE]", "Stop",
              "mode=" + signal_src +
              " stop_price=" + DoubleToString(stop_price, 5) +
              " entry_proxy=" + DoubleToString(C, 5) +
              " stop_pts=" + DoubleToString(MathAbs(C - stop_price) / exec_point / 1000.0, 3));

      ExecuteSignalByMarket(signal_dir, signal_src, stop_price, cur_bar, "[M30 CLOSE]");
   }

   // v3.15: CSV write block was moved to right after the [STATUS] print
   // (above) so it runs every new M30 bar, even when a signal fires.
}
//+------------------------------------------------------------------+



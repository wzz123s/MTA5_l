//+------------------------------------------------------------------+
//|                                     1H_M30_4H_Strategy_EA.mq5    |
//|                                                          Codex    |
//|                                  1H / M30 / 4H baseline profile  |
//|                                  Dedicated defaults derived from  |
//|                                  1H_M30_4H validation bundle     |
//|                                        v3.24: Python-compatible SMMA (mean-init) for Bias_55/Bias_5   |
//|                                        v3.26: Python batch SMMA + M15 anchor/runtime fixes + optional slot2 gate |
//|                                        v3.25: Python-aligned SMMA + post_n reset fix + M15 slot2 + merged window |
//|                                        v3.22: dynamic lot sizing from InpRiskPct + pre-trade margin check |
//|                                        v3.21: strategy package sync + dedicated CSV export filename    |
//|                                        v3.20: real-time M15 slot1 early-entry + H2 q2 early-gate     |
//|                                        NOTE: slot2 falls back to normal M30-close execution           |
//|                                        v3.19: H2 q2 early-gate + merged stage3 exit                  |
//|                                        v3.18: balanced final sizing + current mainline defaults       |
//|                                          Layer 1: |H2 Bias_55| > 3.0% 硬门 (应用到所有模式)           |
//|                                          Layer 2: pre_cross + cross + post_n(N=2-6), spec [14, 70]    |
//|                                          Layer 3: H2 Bias_5 top 34%                                   |
//|                                          Stage lots: 0.02 / 0.01 / 0.03                               |
//|                                        v3.17: FindStopSMA rollback to v3.15 — only MIN_BARS=30 guard |
//|                                        v3.16: REVERTED — 4-guard MAX_DIST_PTS=100 was wrong |
//|                                        v3.15: iBarShift->iTime, CSV before signal return |
//|                                        v3.13: H2 filter = SMA5 vs SMA13 |
//|                                        v3.12: CSV signal export   |
//|                                        v3.11: InpH2Thresh 0.5->0.0     |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "3.26"
#property strict
#include <Trade\Trade.mqh>

//--- Input parameters
input group "=== Account ==="
input ulong   InpMagic      = 312025;      // Magic Number
input string  InpSymbol     = "XAUUSDm";   // Symbol

input group "=== Risk & Position ==="
input double  InpRiskPct    = 3.0;         // Risk % per trade
input double  InpStopLo     = 14000.0;        // Min stop distance (MQL5 points = spec 14 pt x 1000)
input double  InpStopHi     = 70000.0;        // Max stop distance (MQL5 points = spec 70 pt x 1000)
input int     InpMaxPos     = 3;            // Max concurrent positions
input double  InpMinLots    = 0.01;         // Min lot
input double  InpMaxLots    = 10.0;         // Max lot
input bool    InpUseDynamicLots = false;    // false=fixed lots from validation bundle; true=dynamic lots from InpRiskPct + stop

input group "=== Live Risk Guards ==="
input bool    InpEnableLiveRiskGuards = false; // Explicit live/pre-live guard switch
input double  InpLiveBalanceCap       = 2000.0; // Reference balance cap for drawdown guard
input double  InpMaxDailyLossUSD      = 120.0;  // Block new entries at or below daily net loss
input double  InpMaxDrawdownUSD       = 200.0;  // Block new entries if balance cap - equity exceeds this
input int     InpMaxNewPositionsPerDay = 9;     // Counts split-stage IN deals
input int     InpMaxSpreadPoints      = 300;    // Block new entries above this spread
input double  InpMarginGuardPct       = 500.0;  // Min margin level after estimated signal
input double  InpLiveMaxLotCap        = 0.10;   // Per-stage live lot cap when guard is enabled
input int     InpLeverageOverride     = 0;      // 0=ACCOUNT_LEVERAGE; otherwise explicit fallback

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
input bool    InpUseM15EarlyEntry = true;       // 启用实时版 M15 early-entry
input bool    InpEnableM15Slot2   = false;      // v3.26: slot2 early-entry experiment (default off for baseline-B)
input bool    InpUseM15RescueTag  = true;       // 日志上保留 rescue 语义（执行口径仍是实时版）
input ENUM_TIMEFRAMES InpM15Period = PERIOD_M15; // 小周期确认
input bool    InpVerboseDecisionDiag = true;    // 输出逐层判定诊断日志

input group "=== Split TP (v3.10) ==="
input int     InpStageCount   = 3;          // Number of sub-orders per signal (1-3)
input double  InpStage1Lots  = 0.02;       // Stage 1 lots (validation profile: 1.0 unit)
input double  InpStage2Lots  = 0.01;       // Stage 2 lots (validation profile: 0.5 unit)
input double  InpStage3Lots  = 0.03;       // Stage 3 lots (validation profile: 1.5 units)
input double  InpStage1R      = 1.0;        // Stage 1: TP in R multiples
input double  InpStage2TrailR = 1.5;        // Stage 2: start 30m SMA13 trailing after N R
input double  InpStage2ForceR = 3.0;        // Stage 2: forced close at N R
input int     InpH2CrossBars  = 3;          // Bars used to confirm 2H SMA5/13 cross
input bool    InpStage3On     = true;       // Enable Stage 3 passive (exit on M30 merged direction flip)
input bool    InpDebugStages  = true;       // Verbose per-stage logs
input bool    InpExportCSV    = true;       // Export per-bar signals to CSV (1H_M30_4H_strategy_signals_export.csv)
input bool    InpExportTradeLedger = true;  // Export per-stage trade ledger (1H_M30_4H_strategy_trade_ledger.csv)
input bool    InpExportStagePriceDiag = true; // Export Stage1/2 price-side diagnostics (no behavior change)
input bool    InpExportM15EntryDiag = true; // Export M15 early-entry gate diagnostics (no behavior change)

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
int      g_merged_strict_post_n_counter = 0; // Diagnostic Python-style merged post_n for M30 CLOSE veto only
double   g_last_cross_dir = 0;
int      g_merged_last_dir = 0;         // v3.23: 合并后最后方向
int      g_merged_strict_last_cross = 0;

//--- v3.0 Layer 3 状态 (Bias_5 top X% 阈值缓存)
double   g_bias5_top_threshold = 0;     // Bias_5 滚动 top X% 阈值 (H2 close 偏离 SMMA5)
bool     g_bias5_history_ready = false; // 是否已计算过阈值

//--- 3-stage split TP state (v3.10)
// Magic-number stage offsets from InpMagic (must be ulong to match InpMagic type)
const ulong MAGIC_STAGE1 = 1;   // InpMagic+1 = stage 1 (1.0R close, 0.02 lot)
const ulong MAGIC_STAGE2 = 2;   // InpMagic+2 = stage 2 (SMA13 trail + 3R force, 0.01 lot)
const ulong MAGIC_STAGE3 = 3;   // InpMagic+3 = stage 3 (let profits run, M30 merged exit, 0.03 lot)

// Per-stage state, indexed 1..3 (index 0 unused)
ulong  g_stage_tickets[4];     // latest position ticket for this stage (0 = no position)
ulong  g_stage_pos_ids[4];     // latest POSITION_IDENTIFIER for this stage
double g_stage_entry[4];       // fill price for R calc
double g_stage_orig_sl[4];     // original SL at fill (used for R, NOT ratchet SL)
bool   g_stage2_trail_on[4];   // true once stage 2 reaches InpStage2TrailR

//--- merged direction settings (Python prepare(..., min_len=8))
const int M30_MERGED_MIN_LEN = 8;

//--- CSV export (v3.21)
int g_csv_handle = INVALID_HANDLE;   // 1H_M30_4H_strategy_signals_export.csv file handle
string g_csv_path = "1H_M30_4H_strategy_signals_export.csv";
int g_ledger_handle = INVALID_HANDLE;
string g_ledger_path = "1H_M30_4H_strategy_trade_ledger.csv";
string g_deal_history_path = "1H_M30_4H_strategy_deal_history.csv";
int g_stage_price_diag_handle = INVALID_HANDLE;
string g_stage_price_diag_path = "1H_M30_4H_strategy_stage_price_diag.csv";
int g_m15_entry_diag_handle = INVALID_HANDLE;
string g_m15_entry_diag_path = "1H_M30_4H_strategy_m15_entry_diag.csv";

#define LEDGER_MAX_TRACK 64
bool     g_ledger_active[LEDGER_MAX_TRACK];
int      g_ledger_stage[LEDGER_MAX_TRACK];
ulong    g_ledger_ticket[LEDGER_MAX_TRACK];
ulong    g_ledger_position_id[LEDGER_MAX_TRACK];
ulong    g_ledger_magic[LEDGER_MAX_TRACK];
datetime g_ledger_anchor_time[LEDGER_MAX_TRACK];
datetime g_ledger_open_time[LEDGER_MAX_TRACK];
int      g_ledger_signal_dir[LEDGER_MAX_TRACK];
double   g_ledger_signal_entry[LEDGER_MAX_TRACK];
double   g_ledger_signal_stop[LEDGER_MAX_TRACK];
double   g_ledger_fill_price[LEDGER_MAX_TRACK];
double   g_ledger_actual_stop[LEDGER_MAX_TRACK];
double   g_ledger_lots[LEDGER_MAX_TRACK];
double   g_ledger_stop_pts[LEDGER_MAX_TRACK];
string   g_ledger_signal_src[LEDGER_MAX_TRACK];
string   g_ledger_trigger_tag[LEDGER_MAX_TRACK];
string   g_ledger_pending_exit[LEDGER_MAX_TRACK];
datetime g_ledger_stage2_trail_on_time[LEDGER_MAX_TRACK];
double   g_ledger_stage2_trail_on_rr[LEDGER_MAX_TRACK];
double   g_ledger_stage2_trail_on_price[LEDGER_MAX_TRACK];
double   g_ledger_stage2_trail_on_sl[LEDGER_MAX_TRACK];
int      g_ledger_stage2_trail_no_ratchet_count[LEDGER_MAX_TRACK];
int      g_ledger_stage2_trail_modify_count[LEDGER_MAX_TRACK];
int      g_ledger_stage2_trail_modify_fail_count[LEDGER_MAX_TRACK];
datetime g_ledger_stage2_first_modify_time[LEDGER_MAX_TRACK];
datetime g_ledger_stage2_last_modify_time[LEDGER_MAX_TRACK];
double   g_ledger_stage2_last_modify_from_sl[LEDGER_MAX_TRACK];
double   g_ledger_stage2_last_modify_to_sl[LEDGER_MAX_TRACK];
double   g_ledger_stage2_last_modify_sma13[LEDGER_MAX_TRACK];
long     g_ledger_stage2_last_modify_retcode[LEDGER_MAX_TRACK];
string   g_ledger_stage2_last_modify_comment[LEDGER_MAX_TRACK];
double   g_ledger_stage2_last_known_sl[LEDGER_MAX_TRACK];

void LedgerResetSlot(int slot)
{
   if(slot < 0 || slot >= LEDGER_MAX_TRACK) return;
   g_ledger_active[slot] = false;
   g_ledger_stage[slot] = 0;
   g_ledger_ticket[slot] = 0;
   g_ledger_position_id[slot] = 0;
   g_ledger_magic[slot] = 0;
   g_ledger_anchor_time[slot] = 0;
   g_ledger_open_time[slot] = 0;
   g_ledger_signal_dir[slot] = 0;
   g_ledger_signal_entry[slot] = 0;
   g_ledger_signal_stop[slot] = 0;
   g_ledger_fill_price[slot] = 0;
   g_ledger_actual_stop[slot] = 0;
   g_ledger_lots[slot] = 0;
   g_ledger_stop_pts[slot] = 0;
   g_ledger_signal_src[slot] = "";
   g_ledger_trigger_tag[slot] = "";
   g_ledger_pending_exit[slot] = "";
   g_ledger_stage2_trail_on_time[slot] = 0;
   g_ledger_stage2_trail_on_rr[slot] = 0;
   g_ledger_stage2_trail_on_price[slot] = 0;
   g_ledger_stage2_trail_on_sl[slot] = 0;
   g_ledger_stage2_trail_no_ratchet_count[slot] = 0;
   g_ledger_stage2_trail_modify_count[slot] = 0;
   g_ledger_stage2_trail_modify_fail_count[slot] = 0;
   g_ledger_stage2_first_modify_time[slot] = 0;
   g_ledger_stage2_last_modify_time[slot] = 0;
   g_ledger_stage2_last_modify_from_sl[slot] = 0;
   g_ledger_stage2_last_modify_to_sl[slot] = 0;
   g_ledger_stage2_last_modify_sma13[slot] = 0;
   g_ledger_stage2_last_modify_retcode[slot] = 0;
   g_ledger_stage2_last_modify_comment[slot] = "";
   g_ledger_stage2_last_known_sl[slot] = 0;
}

int LedgerFindFreeSlot()
{
   for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
      if(!g_ledger_active[slot])
         return slot;
   return -1;
}

int LedgerFindSlotByTicket(ulong ticket)
{
   if(ticket == 0) return -1;
   for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
   {
      if(!g_ledger_active[slot]) continue;
      if(g_ledger_ticket[slot] == ticket)
         return slot;
   }
   return -1;
}

int LedgerFindSlotByPositionId(ulong position_id)
{
   if(position_id == 0) return -1;
   for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
   {
      if(!g_ledger_active[slot]) continue;
      if(g_ledger_position_id[slot] == position_id)
         return slot;
   }
   return -1;
}

int LedgerFindLatestActiveSlotByStage(int stage)
{
   if(stage < 1 || stage > 3) return -1;
   int best_slot = -1;
   datetime best_time = 0;
   for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
   {
      if(!g_ledger_active[slot]) continue;
      if(g_ledger_stage[slot] != stage) continue;
      if(best_slot < 0 || g_ledger_open_time[slot] >= best_time)
      {
         best_slot = slot;
         best_time = g_ledger_open_time[slot];
      }
   }
   return best_slot;
}

int StageFromMagic(ulong magic)
{
   if(magic == InpMagic + MAGIC_STAGE1) return 1;
   if(magic == InpMagic + MAGIC_STAGE2) return 2;
   if(magic == InpMagic + MAGIC_STAGE3) return 3;
   return 0;
}

string DealEntryText(long entry)
{
   if(entry == DEAL_ENTRY_IN)     return "IN";
   if(entry == DEAL_ENTRY_OUT)    return "OUT";
   if(entry == DEAL_ENTRY_INOUT)  return "INOUT";
   if(entry == DEAL_ENTRY_OUT_BY) return "OUT_BY";
   return IntegerToString((int)entry);
}

string DealReasonText(long reason)
{
   if(reason == DEAL_REASON_CLIENT)   return "CLIENT";
   if(reason == DEAL_REASON_MOBILE)   return "MOBILE";
   if(reason == DEAL_REASON_WEB)      return "WEB";
   if(reason == DEAL_REASON_EXPERT)   return "EXPERT";
   if(reason == DEAL_REASON_SL)       return "SL";
   if(reason == DEAL_REASON_TP)       return "TP";
   if(reason == DEAL_REASON_SO)       return "SO";
   if(reason == DEAL_REASON_ROLLOVER) return "ROLLOVER";
   if(reason == DEAL_REASON_VMARGIN)  return "VMARGIN";
   if(reason == DEAL_REASON_SPLIT)    return "SPLIT";
   return IntegerToString((int)reason);
}

string DealTypeText(long type)
{
   if(type == DEAL_TYPE_BUY)     return "BUY";
   if(type == DEAL_TYPE_SELL)    return "SELL";
   if(type == DEAL_TYPE_BALANCE) return "BALANCE";
   if(type == DEAL_TYPE_CREDIT)  return "CREDIT";
   if(type == DEAL_TYPE_CHARGE)  return "CHARGE";
   if(type == DEAL_TYPE_CORRECTION) return "CORRECTION";
   if(type == DEAL_TYPE_BONUS)   return "BONUS";
   if(type == DEAL_TYPE_COMMISSION) return "COMMISSION";
   if(type == DEAL_TYPE_COMMISSION_DAILY) return "COMMISSION_DAILY";
   if(type == DEAL_TYPE_COMMISSION_MONTHLY) return "COMMISSION_MONTHLY";
   if(type == DEAL_TYPE_INTEREST) return "INTEREST";
   if(type == DEAL_TYPE_BUY_CANCELED) return "BUY_CANCELED";
   if(type == DEAL_TYPE_SELL_CANCELED) return "SELL_CANCELED";
   return IntegerToString((int)type);
}

void DumpRawDealHistory()
{
   if(!InpExportTradeLedger || InpSimMode) return;

   datetime now = TimeCurrent();
   if(!HistorySelect(0, now + 86400))
   {
      Print("[WARN] Could not select deal history for raw export: ", GetLastError());
      return;
   }

   int handle = FileOpen(g_deal_history_path, FILE_WRITE|FILE_CSV|FILE_SHARE_READ|FILE_ANSI, ",");
   if(handle == INVALID_HANDLE)
   {
      Print("[WARN] Could not open raw deal history CSV: ", GetLastError());
      return;
   }

   FileWrite(handle,
      "deal_ticket", "order_ticket", "position_id", "time", "symbol",
      "magic", "stage", "deal_entry", "deal_type", "deal_reason",
      "volume", "price", "profit", "swap", "commission", "net_profit",
      "comment");

   int written = 0;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0) continue;
      if(!HistoryDealSelect(deal)) continue;
      string symbol = HistoryDealGetString(deal, DEAL_SYMBOL);
      ulong magic = (ulong)HistoryDealGetInteger(deal, DEAL_MAGIC);
      int stage = StageFromMagic(magic);
      if(symbol != InpSymbol && stage == 0) continue;

      double profit = HistoryDealGetDouble(deal, DEAL_PROFIT);
      double swap = HistoryDealGetDouble(deal, DEAL_SWAP);
      double commission = HistoryDealGetDouble(deal, DEAL_COMMISSION);
      double net_profit = profit + swap + commission;

      FileWrite(handle,
         (string)deal,
         (string)HistoryDealGetInteger(deal, DEAL_ORDER),
         (string)HistoryDealGetInteger(deal, DEAL_POSITION_ID),
         TimeToString((datetime)HistoryDealGetInteger(deal, DEAL_TIME), TIME_DATE|TIME_SECONDS),
         symbol,
         (string)magic,
         IntegerToString(stage),
         DealEntryText(HistoryDealGetInteger(deal, DEAL_ENTRY)),
         DealTypeText(HistoryDealGetInteger(deal, DEAL_TYPE)),
         DealReasonText(HistoryDealGetInteger(deal, DEAL_REASON)),
         DoubleToString(HistoryDealGetDouble(deal, DEAL_VOLUME), 2),
         DoubleToString(HistoryDealGetDouble(deal, DEAL_PRICE), 5),
         DoubleToString(profit, 2),
         DoubleToString(swap, 2),
         DoubleToString(commission, 2),
         DoubleToString(net_profit, 2),
         HistoryDealGetString(deal, DEAL_COMMENT));
      written++;
   }

   FileFlush(handle);
   FileClose(handle);
   Print("Raw deal history export closed: ", g_deal_history_path, " rows=", written);
}

void LedgerRegisterOpen(int stage, ulong ticket, ulong position_id,
                        string signal_src, string trigger_tag,
                        datetime anchor_time, int signal_dir, double signal_entry,
                        double signal_stop, double fill_price, double actual_stop,
                        double lots, double stop_pts)
{
   if(!InpExportTradeLedger || InpSimMode) return;
   if(stage < 1 || stage > 3) return;
   int slot = LedgerFindSlotByTicket(ticket);
   if(slot < 0)
      slot = LedgerFindFreeSlot();
   if(slot < 0)
   {
      Print("[WARN] Trade ledger slot exhausted, ticket=", ticket, " stage=", stage);
      return;
   }
   g_ledger_active[slot] = true;
   g_ledger_stage[slot] = stage;
   g_ledger_ticket[slot] = ticket;
   g_ledger_position_id[slot] = position_id;
   g_ledger_magic[slot] = InpMagic + (ulong)stage;
   g_ledger_anchor_time[slot] = anchor_time;
   g_ledger_open_time[slot] = TimeCurrent();
   g_ledger_signal_dir[slot] = signal_dir;
   g_ledger_signal_entry[slot] = signal_entry;
   g_ledger_signal_stop[slot] = signal_stop;
   g_ledger_fill_price[slot] = fill_price;
   g_ledger_actual_stop[slot] = actual_stop;
   g_ledger_lots[slot] = lots;
   g_ledger_stop_pts[slot] = stop_pts;
   g_ledger_signal_src[slot] = signal_src;
   g_ledger_trigger_tag[slot] = trigger_tag;
   g_ledger_pending_exit[slot] = "";
   if(stage == 2)
      g_ledger_stage2_last_known_sl[slot] = actual_stop;
}

void LedgerMarkExitIntentByTicket(ulong ticket, string local_reason)
{
   int slot = LedgerFindSlotByTicket(ticket);
   if(slot < 0 && PositionSelectByTicket(ticket))
   {
      ulong position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      slot = LedgerFindSlotByPositionId(position_id);
   }
   if(slot < 0) return;
   g_ledger_pending_exit[slot] = local_reason;
}

string LedgerTimeText(datetime value)
{
   if(value <= 0) return "";
   return TimeToString(value, TIME_DATE|TIME_SECONDS);
}

string LedgerDoubleText(double value, int digits)
{
   if(value <= 0) return "";
   return DoubleToString(value, digits);
}

double LedgerExtractSLPrice(string comment)
{
   int pos = StringFind(comment, "sl ");
   if(pos < 0)
      pos = StringFind(comment, "SL ");
   if(pos < 0)
      return 0.0;
   string tail = StringSubstr(comment, pos + 3);
   return StringToDouble(tail);
}

string LedgerStage2SLKind(int slot, long deal_reason, double exit_price, string deal_comment)
{
   if(slot < 0 || slot >= LEDGER_MAX_TRACK) return "";
   if(g_ledger_stage[slot] != 2) return "";
   if(deal_reason != DEAL_REASON_SL) return "";

   double deal_sl = LedgerExtractSLPrice(deal_comment);
   if(deal_sl <= 0)
      deal_sl = exit_price;
   if(deal_sl <= 0)
      return "unknown_sl";

   double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   double tol = MathMax(point * 20.0, 0.10);
   double initial_sl = g_ledger_actual_stop[slot];
   double last_sl = g_ledger_stage2_last_known_sl[slot] > 0 ?
                    g_ledger_stage2_last_known_sl[slot] : initial_sl;
   double dist_initial = MathAbs(deal_sl - initial_sl);
   double dist_last = MathAbs(deal_sl - last_sl);

   if(dist_initial <= tol && (g_ledger_stage2_trail_modify_count[slot] == 0 || dist_initial <= dist_last))
      return "initial_sl";
   if(g_ledger_stage2_trail_modify_count[slot] > 0 && dist_last <= tol && dist_last < dist_initial)
      return "trail_sl";
   if(g_ledger_stage2_trail_modify_count[slot] > 0)
      return "modified_sl_unknown";
   return "unknown_sl";
}

void LedgerStage2MarkTrailOn(ulong ticket, double rr, double price, double current_sl)
{
   int slot = LedgerFindSlotByTicket(ticket);
   if(slot < 0 || g_ledger_stage[slot] != 2) return;
   if(g_ledger_stage2_trail_on_time[slot] <= 0)
   {
      g_ledger_stage2_trail_on_time[slot] = TimeCurrent();
      g_ledger_stage2_trail_on_rr[slot] = rr;
      g_ledger_stage2_trail_on_price[slot] = price;
      g_ledger_stage2_trail_on_sl[slot] = current_sl;
   }
   if(current_sl > 0)
      g_ledger_stage2_last_known_sl[slot] = current_sl;
}

void LedgerStage2RecordTrailAttempt(ulong ticket, double from_sl, double to_sl,
                                    double sma13_now, bool changed, bool success,
                                    long retcode, string comment)
{
   int slot = LedgerFindSlotByTicket(ticket);
   if(slot < 0 || g_ledger_stage[slot] != 2) return;

   if(!changed)
   {
      g_ledger_stage2_trail_no_ratchet_count[slot]++;
      if(from_sl > 0)
         g_ledger_stage2_last_known_sl[slot] = from_sl;
      return;
   }

   if(success)
   {
      g_ledger_stage2_trail_modify_count[slot]++;
      if(g_ledger_stage2_first_modify_time[slot] <= 0)
         g_ledger_stage2_first_modify_time[slot] = TimeCurrent();
      g_ledger_stage2_last_known_sl[slot] = to_sl;
   }
   else
   {
      g_ledger_stage2_trail_modify_fail_count[slot]++;
      if(from_sl > 0)
         g_ledger_stage2_last_known_sl[slot] = from_sl;
   }

   g_ledger_stage2_last_modify_time[slot] = TimeCurrent();
   g_ledger_stage2_last_modify_from_sl[slot] = from_sl;
   g_ledger_stage2_last_modify_to_sl[slot] = to_sl;
   g_ledger_stage2_last_modify_sma13[slot] = sma13_now;
   g_ledger_stage2_last_modify_retcode[slot] = retcode;
   g_ledger_stage2_last_modify_comment[slot] = comment;
}

void LedgerWriteCloseFromDealSlot(int slot, ulong deal_ticket, string fallback_reason)
{
   if(!InpExportTradeLedger || InpSimMode) return;
   if(slot < 0 || slot >= LEDGER_MAX_TRACK) return;
   if(!g_ledger_active[slot]) return;
   if(g_ledger_handle == INVALID_HANDLE) return;
   if(deal_ticket == 0) return;
   if(!HistoryDealSelect(deal_ticket)) return;

   string local_reason = g_ledger_pending_exit[slot];
   if(local_reason == "") local_reason = fallback_reason;
   if(local_reason == "") local_reason = "history_exit";

   datetime exit_time = (datetime)HistoryDealGetInteger(deal_ticket, DEAL_TIME);
   double exit_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
   double exit_volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
   double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
   double swap = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);
   double commission = HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
   long deal_entry = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
   long deal_reason = HistoryDealGetInteger(deal_ticket, DEAL_REASON);
   string deal_comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);
   double net_profit = profit + swap + commission;
   double deal_sl_price = LedgerExtractSLPrice(deal_comment);
   string stage2_sl_kind = LedgerStage2SLKind(slot, deal_reason, exit_price, deal_comment);

   FileWrite(g_ledger_handle,
      TimeToString(g_ledger_anchor_time[slot], TIME_DATE|TIME_MINUTES),
      g_ledger_trigger_tag[slot],
      g_ledger_signal_src[slot],
      DirText(g_ledger_signal_dir[slot]),
      IntegerToString(g_ledger_stage[slot]),
      (string)g_ledger_magic[slot],
      (string)g_ledger_ticket[slot],
      (string)g_ledger_position_id[slot],
      TimeToString(g_ledger_open_time[slot], TIME_DATE|TIME_SECONDS),
      DoubleToString(g_ledger_signal_entry[slot], 5),
      DoubleToString(g_ledger_signal_stop[slot], 5),
      DoubleToString(g_ledger_fill_price[slot], 5),
      DoubleToString(g_ledger_actual_stop[slot], 5),
      DoubleToString(g_ledger_lots[slot], 2),
      DoubleToString(g_ledger_stop_pts[slot], 1),
      local_reason,
      DealEntryText(deal_entry),
      DealReasonText(deal_reason),
      TimeToString(exit_time, TIME_DATE|TIME_SECONDS),
      DoubleToString(exit_price, 5),
      DoubleToString(exit_volume, 2),
      DoubleToString(profit, 2),
      DoubleToString(swap, 2),
      DoubleToString(commission, 2),
      DoubleToString(net_profit, 2),
      deal_comment,
      (string)deal_ticket,
      LedgerTimeText(g_ledger_stage2_trail_on_time[slot]),
      LedgerDoubleText(g_ledger_stage2_trail_on_rr[slot], 6),
      LedgerDoubleText(g_ledger_stage2_trail_on_price[slot], 5),
      LedgerDoubleText(g_ledger_stage2_trail_on_sl[slot], 5),
      IntegerToString(g_ledger_stage2_trail_no_ratchet_count[slot]),
      IntegerToString(g_ledger_stage2_trail_modify_count[slot]),
      IntegerToString(g_ledger_stage2_trail_modify_fail_count[slot]),
      LedgerTimeText(g_ledger_stage2_first_modify_time[slot]),
      LedgerTimeText(g_ledger_stage2_last_modify_time[slot]),
      LedgerDoubleText(g_ledger_stage2_last_modify_from_sl[slot], 5),
      LedgerDoubleText(g_ledger_stage2_last_modify_to_sl[slot], 5),
      LedgerDoubleText(g_ledger_stage2_last_modify_sma13[slot], 5),
      (string)g_ledger_stage2_last_modify_retcode[slot],
      g_ledger_stage2_last_modify_comment[slot],
      LedgerDoubleText(g_ledger_stage2_last_known_sl[slot], 5),
      stage2_sl_kind,
      LedgerDoubleText(deal_sl_price, 5));
   FileFlush(g_ledger_handle);
   LedgerResetSlot(slot);
}

bool LedgerFindLatestExitDealBySlot(int slot, ulong &deal_ticket)
{
   deal_ticket = 0;
   if(slot < 0 || slot >= LEDGER_MAX_TRACK) return false;
   if(!g_ledger_active[slot]) return false;

   datetime from_time = g_ledger_open_time[slot] > 0 ? (g_ledger_open_time[slot] - 86400) : (TimeCurrent() - 86400);
   if(!HistorySelect(from_time, TimeCurrent() + 60))
      return false;

   ulong tracked_ticket = g_ledger_ticket[slot];
   ulong tracked_position_id = g_ledger_position_id[slot];
   int total = HistoryDealsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0) continue;
      if(HistoryDealGetString(deal, DEAL_SYMBOL) != InpSymbol) continue;
      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY && entry != DEAL_ENTRY_INOUT) continue;
      ulong position_id = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
      if(tracked_position_id > 0 && position_id > 0 && position_id != tracked_position_id) continue;
      if(tracked_position_id <= 0 && (ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != g_ledger_magic[slot]) continue;
      if(tracked_position_id == 0 && tracked_ticket > 0 && position_id > 0 && position_id != tracked_ticket) continue;
      datetime deal_time = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);
      if(g_ledger_open_time[slot] > 0 && deal_time + 1 < g_ledger_open_time[slot]) continue;
      deal_ticket = deal;
      return true;
   }
   return false;
}

void LedgerTryFinalizeFromHistoryByTicket(ulong ticket, string fallback_reason)
{
   int slot = LedgerFindSlotByTicket(ticket);
   if(slot < 0) return;
   ulong deal_ticket = 0;
   if(LedgerFindLatestExitDealBySlot(slot, deal_ticket))
      LedgerWriteCloseFromDealSlot(slot, deal_ticket, fallback_reason);
}

void LedgerFinalizeAllOpenFromHistory(string fallback_reason)
{
   if(!InpExportTradeLedger || InpSimMode) return;
   for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
   {
      if(!g_ledger_active[slot]) continue;
      ulong deal_ticket = 0;
      if(LedgerFindLatestExitDealBySlot(slot, deal_ticket))
         LedgerWriteCloseFromDealSlot(slot, deal_ticket, fallback_reason);
   }
}

string DirText(int signal_dir)
{
   if(signal_dir > 0) return "BUY";
   if(signal_dir < 0) return "SELL";
   return "NONE";
}

string BoolText(bool value)
{
   return value ? "true" : "false";
}

double SafeR(double entry, double orig_sl)
{
   double r = MathAbs(entry - orig_sl);
   if(r <= 0) return 0.0;
   return r;
}

double AbsRRAtPrice(double entry, double orig_sl, double price)
{
   double r = SafeR(entry, orig_sl);
   if(r <= 0) return 0.0;
   return MathAbs(price - entry) / r;
}

double ProfitRRAtPrice(ENUM_POSITION_TYPE ptype, double entry, double orig_sl, double price)
{
   double r = SafeR(entry, orig_sl);
   if(r <= 0) return 0.0;
   if(ptype == POSITION_TYPE_BUY)
      return (price - entry) / r;
   if(ptype == POSITION_TYPE_SELL)
      return (entry - price) / r;
   return 0.0;
}

string LegacyActionText(int stage, int action, bool trail_before, bool trail_after)
{
   if(action == 1)
   {
      if(stage == 1) return "stage1_tp";
      if(stage == 2) return "stage2_forced";
      return "close";
   }
   if(stage == 2 && !trail_before && trail_after)
      return "stage2_trail_on";
   if(stage == 2 && trail_after)
      return "stage2_trailing";
   return "hold";
}

string ProfitSideActionText(int stage, double profit_rr, bool trail_before)
{
   if(stage == 1)
   {
      if(profit_rr >= InpStage1R) return "stage1_tp";
      return "hold";
   }
   if(stage == 2)
   {
      if(profit_rr >= InpStage2ForceR) return "stage2_forced";
      if(profit_rr >= InpStage2TrailR && !trail_before) return "stage2_trail_on";
      if(trail_before) return "stage2_trailing";
      return "hold";
   }
   return "hold";
}

string DiagTimeText(datetime value)
{
   if(value <= 0) return "";
   return TimeToString(value, TIME_DATE|TIME_MINUTES);
}

string DiagDoubleText(double value, int digits)
{
   if(value == EMPTY_VALUE) return "";
   return DoubleToString(value, digits);
}

void M15EntryDiagWrite(string result, string detail,
                       datetime cur_bar, datetime completed_m15_open,
                       int m15_shift, int m30_shift,
                       datetime slot_m30_open, int slot_in_m30,
                       bool is_slot1, bool is_slot2, datetime anchor_time,
                       int stage_count, int pre_cross, bool is_cross_mode,
                       int merged_post_n, int signal_dir, string signal_src,
                       bool layer1_checked, bool layer1_pass,
                       bool layer3_checked, bool layer3_pass,
                       double m15_close, double m15_sma13,
                       double stop_price, double entry_proxy,
                       double stop_pts_spec)
{
   if(!InpExportM15EntryDiag) return;
   if(g_m15_entry_diag_handle == INVALID_HANDLE) return;

   bool same_anchor = (anchor_time > 0 && g_signal_anchor_time == anchor_time);
   FileWrite(g_m15_entry_diag_handle,
      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
      DiagTimeText(cur_bar),
      DiagTimeText(completed_m15_open),
      IntegerToString(m15_shift),
      IntegerToString(m30_shift),
      DiagTimeText(slot_m30_open),
      IntegerToString(slot_in_m30),
      BoolText(is_slot1),
      BoolText(is_slot2),
      DiagTimeText(anchor_time),
      IntegerToString(stage_count),
      IntegerToString(InpMaxPos),
      DiagTimeText(g_signal_anchor_time),
      BoolText(same_anchor),
      IntegerToString(pre_cross),
      BoolText(is_cross_mode),
      IntegerToString(g_post_n_counter),
      IntegerToString(merged_post_n),
      IntegerToString(signal_dir),
      DirText(signal_dir),
      signal_src,
      BoolText(layer1_checked),
      BoolText(layer1_pass),
      BoolText(layer3_checked),
      BoolText(layer3_pass),
      DiagDoubleText(m15_close, 5),
      DiagDoubleText(m15_sma13, 5),
      DiagDoubleText(stop_price, 5),
      DiagDoubleText(entry_proxy, 5),
      DiagDoubleText(stop_pts_spec, 3),
      result,
      detail);
   FileFlush(g_m15_entry_diag_handle);
}

void StagePriceDiagWrite(int stage, ulong ticket, double entry, double orig_sl,
                         double current_sl, double lots, double legacy_price,
                         double bid, double ask, ENUM_POSITION_TYPE ptype,
                         bool trail_before, bool trail_after, int legacy_action,
                         bool new_m30_bar, bool new_m15_bar)
{
   if(!InpExportStagePriceDiag || InpSimMode) return;
   if(g_stage_price_diag_handle == INVALID_HANDLE) return;
   if(stage < 1 || stage > 2) return;

   int slot = LedgerFindSlotByTicket(ticket);
   string signal_anchor = "";
   string trigger_tag = "";
   string signal_src = "";
   string dir = (ptype == POSITION_TYPE_BUY ? "BUY" : "SELL");
   ulong position_id = 0;
   if(slot >= 0)
   {
      signal_anchor = TimeToString(g_ledger_anchor_time[slot], TIME_DATE|TIME_MINUTES);
      trigger_tag = g_ledger_trigger_tag[slot];
      signal_src = g_ledger_signal_src[slot];
      dir = DirText(g_ledger_signal_dir[slot]);
      position_id = g_ledger_position_id[slot];
   }
   else if(PositionSelectByTicket(ticket))
   {
      position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
   }

   double close_side_price = (ptype == POSITION_TYPE_BUY ? bid : ask);
   double legacy_abs_rr = AbsRRAtPrice(entry, orig_sl, legacy_price);
   double bid_abs_rr = AbsRRAtPrice(entry, orig_sl, bid);
   double ask_abs_rr = AbsRRAtPrice(entry, orig_sl, ask);
   double close_abs_rr = AbsRRAtPrice(entry, orig_sl, close_side_price);
   double close_profit_rr = ProfitRRAtPrice(ptype, entry, orig_sl, close_side_price);
   string legacy_action_text = LegacyActionText(stage, legacy_action, trail_before, trail_after);
   string profit_side_action_text = ProfitSideActionText(stage, close_profit_rr, trail_before);

   FileWrite(g_stage_price_diag_handle,
      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
      signal_anchor,
      trigger_tag,
      signal_src,
      dir,
      IntegerToString(stage),
      (string)ticket,
      (string)position_id,
      DoubleToString(entry, 5),
      DoubleToString(orig_sl, 5),
      DoubleToString(current_sl, 5),
      DoubleToString(lots, 2),
      DoubleToString(bid, 5),
      DoubleToString(ask, 5),
      DoubleToString(legacy_price, 5),
      DoubleToString(close_side_price, 5),
      DoubleToString(legacy_abs_rr, 6),
      DoubleToString(bid_abs_rr, 6),
      DoubleToString(ask_abs_rr, 6),
      DoubleToString(close_abs_rr, 6),
      DoubleToString(close_profit_rr, 6),
      DoubleToString(InpStage1R, 2),
      DoubleToString(InpStage2TrailR, 2),
      DoubleToString(InpStage2ForceR, 2),
      BoolText(trail_before),
      BoolText(trail_after),
      IntegerToString(legacy_action),
      legacy_action_text,
      profit_side_action_text,
      BoolText(new_m30_bar),
      BoolText(new_m15_bar));
   FileFlush(g_stage_price_diag_handle);
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
   static int _last_period = 0;
   static double _buf[];
   static int _buf_size = 0;
   static bool _ready = false;
   static int _last_bars = 0;

   // Cache key: Bars(symbol,tf) changes only when a new bar forms (NOT per shift)
   int total_bars = Bars(symbol, tf);
   if(symbol != _last_symbol || tf != _last_tf || period != _last_period ||
      total_bars != _last_bars || !_ready)
   {
      _last_symbol = symbol; _last_tf = tf; _last_period = period; _last_bars = total_bars;
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

   // Lookup: shift=0=latest, shift=1=prev completed, direct index into _buf
   // _buf is ordered oldest→newest: _buf[0..total_bars-1]
   int target = total_bars - 1 - shift;
   if(target < 0 || target >= _buf_size || target < period - 1) return 0;
   return _buf[target];
}

//+------------------------------------------------------------------+
//| v3.26: Batch Python-style M30 SMMA arrays (oldest -> newest)     |
//| Matches PythonSMMA init/recurrence while keeping array semantics  |
//| compatible with GetM30SMAArrays(): [n-1] = current/forming bar   |
//+------------------------------------------------------------------+
int GetM30SMAArrays_Python(double &out_fast[], double &out_slow[], int max_bars)
{
   static string _cached_sym = "";
   static int    _cached_bars = 0;
   static double _cached_close0 = 0.0;
   static double _full_fast[];
   static double _full_slow[];
   static int    _full_count = 0;

   int total_bars = Bars(InpSymbol, InpM30Period);
   if(total_bars < InpSlowMA + 2 || max_bars <= 0) return 0;

   double close0 = iClose(InpSymbol, InpM30Period, 0);
   bool need_recalc = (_cached_sym != InpSymbol ||
                       _cached_bars != total_bars ||
                       _full_count != total_bars ||
                       _full_count <= 0);

   if(need_recalc)
   {
      double closes[];
      ArraySetAsSeries(closes, true);
      int n_close = CopyClose(InpSymbol, InpM30Period, 0, total_bars, closes);
      if(n_close != total_bars) return 0;

      ArrayResize(_full_fast, total_bars);
      ArrayResize(_full_slow, total_bars);
      ArrayInitialize(_full_fast, 0.0);
      ArrayInitialize(_full_slow, 0.0);

      double sum5 = 0.0;
      for(int j = 0; j < InpFastMA; j++)
         sum5 += closes[total_bars - 1 - j];
      _full_fast[InpFastMA - 1] = sum5 / InpFastMA;
      for(int j = InpFastMA; j < total_bars; j++)
      {
         int ci = total_bars - 1 - j;
         _full_fast[j] = (closes[ci] + (InpFastMA - 1) * _full_fast[j - 1]) / InpFastMA;
      }

      double sum13 = 0.0;
      for(int j = 0; j < InpSlowMA; j++)
         sum13 += closes[total_bars - 1 - j];
      _full_slow[InpSlowMA - 1] = sum13 / InpSlowMA;
      for(int j = InpSlowMA; j < total_bars; j++)
      {
         int ci = total_bars - 1 - j;
         _full_slow[j] = (closes[ci] + (InpSlowMA - 1) * _full_slow[j - 1]) / InpSlowMA;
      }

      _cached_sym = InpSymbol;
      _cached_bars = total_bars;
      _full_count = total_bars;
   }
   else if(close0 != _cached_close0)
   {
      int last = _full_count - 1;
      if(last > InpSlowMA)
      {
         _full_fast[last] = (close0 + (InpFastMA - 1) * _full_fast[last - 1]) / InpFastMA;
         _full_slow[last] = (close0 + (InpSlowMA - 1) * _full_slow[last - 1]) / InpSlowMA;
      }
   }

   _cached_close0 = close0;

   int valid_count = _full_count - InpSlowMA + 1;
   int out_count = MathMin(max_bars, valid_count);
   if(out_count <= 0) return 0;

   int copy_start = _full_count - out_count;
   ArrayResize(out_fast, out_count);
   ArrayResize(out_slow, out_count);
   ArrayCopy(out_fast, _full_fast, 0, copy_start, out_count);
   ArrayCopy(out_slow, _full_slow, 0, copy_start, out_count);
   return out_count;
}

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("========================================");
   Print("  30m x 2H EA v3.26 - Initializing (batch Python SMMA + M15 runtime fixes, 2026-07-10)");
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
   Print("  [M15] real-time early-entry = ", InpUseM15EarlyEntry ? "TRUE" : "FALSE");
   Print("  [M15] slot2 experiment = ", InpEnableM15Slot2 ? "TRUE" : "FALSE");
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
      g_stage_pos_ids[i]   = 0;
      g_stage_entry[i]     = 0;
      g_stage_orig_sl[i]   = 0;
      g_stage2_trail_on[i] = false;
   }
   for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
      LedgerResetSlot(slot);
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

   if(InpExportTradeLedger)
   {
      g_ledger_handle = FileOpen(g_ledger_path, FILE_WRITE|FILE_CSV|FILE_SHARE_READ|FILE_ANSI, ",");
      if(g_ledger_handle == INVALID_HANDLE)
         Print("[WARN] Could not open trade ledger CSV: ", GetLastError());
      else
      {
         FileWrite(g_ledger_handle,
            "signal_anchor_time", "trigger_tag", "signal_src", "dir", "stage",
            "magic", "ticket", "position_id", "open_time", "signal_entry", "signal_stop",
            "fill_price", "actual_stop", "lots", "stop_pts",
            "local_exit_reason", "deal_entry", "deal_reason", "exit_time",
            "exit_price", "exit_volume", "profit", "swap", "commission",
            "net_profit", "deal_comment", "deal_ticket",
            "stage2_trail_on_time", "stage2_trail_on_rr", "stage2_trail_on_price",
            "stage2_trail_on_sl", "stage2_trail_no_ratchet_count",
            "stage2_trail_modify_count", "stage2_trail_modify_fail_count",
            "stage2_first_modify_time", "stage2_last_modify_time",
            "stage2_last_modify_from_sl", "stage2_last_modify_to_sl",
            "stage2_last_modify_sma13", "stage2_last_modify_retcode",
            "stage2_last_modify_comment", "stage2_last_known_sl",
            "stage2_sl_kind", "deal_sl_price");
         FileFlush(g_ledger_handle);
         Print("  Trade ledger export: ", g_ledger_path);
      }
   }

   if(InpExportStagePriceDiag)
   {
      g_stage_price_diag_handle = FileOpen(g_stage_price_diag_path, FILE_WRITE|FILE_CSV|FILE_SHARE_READ|FILE_ANSI, ",");
      if(g_stage_price_diag_handle == INVALID_HANDLE)
         Print("[WARN] Could not open stage price diag CSV: ", GetLastError());
      else
      {
         FileWrite(g_stage_price_diag_handle,
            "time", "signal_anchor_time", "trigger_tag", "signal_src", "dir", "stage",
            "ticket", "position_id", "entry", "orig_sl", "current_sl", "lots",
            "bid", "ask", "legacy_price", "close_side_price",
            "legacy_abs_rr", "bid_abs_rr", "ask_abs_rr", "close_abs_rr", "close_profit_rr",
            "stage1_r", "stage2_trail_r", "stage2_force_r",
            "trail_before", "trail_after", "legacy_action",
            "legacy_action_text", "profit_side_action_text",
            "new_m30_bar", "new_m15_bar");
         FileFlush(g_stage_price_diag_handle);
         Print("  Stage price diag export: ", g_stage_price_diag_path);
      }
   }

   if(InpExportM15EntryDiag)
   {
      g_m15_entry_diag_handle = FileOpen(g_m15_entry_diag_path, FILE_WRITE|FILE_CSV|FILE_SHARE_READ|FILE_ANSI, ",");
      if(g_m15_entry_diag_handle == INVALID_HANDLE)
         Print("[WARN] Could not open M15 entry diag CSV: ", GetLastError());
      else
      {
         FileWrite(g_m15_entry_diag_handle,
            "time", "current_m30_bar", "completed_m15_open",
            "m15_shift", "m30_shift", "slot_m30_open", "slot_in_m30",
            "is_slot1", "is_slot2", "anchor_time",
            "stage_count", "max_pos", "last_signal_anchor", "same_anchor",
            "pre_cross", "is_cross", "post_n_counter", "merged_post_n_counter",
            "signal_dir", "dir", "signal_src",
            "layer1_checked", "layer1_pass", "layer3_checked", "layer3_pass",
            "m15_close", "m15_sma13", "stop_price", "entry_proxy",
            "stop_pts_spec", "result", "detail");
         FileFlush(g_m15_entry_diag_handle);
         Print("  M15 entry diag export: ", g_m15_entry_diag_path);
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
   if(g_ledger_handle != INVALID_HANDLE)
   {
      LedgerFinalizeAllOpenFromHistory("deinit_history");
      FileClose(g_ledger_handle);
      g_ledger_handle = INVALID_HANDLE;
      Print("Trade ledger export closed");
   }
   if(g_stage_price_diag_handle != INVALID_HANDLE)
   {
      FileClose(g_stage_price_diag_handle);
      g_stage_price_diag_handle = INVALID_HANDLE;
      Print("Stage price diag export closed");
   }
   if(g_m15_entry_diag_handle != INVALID_HANDLE)
   {
      FileClose(g_m15_entry_diag_handle);
      g_m15_entry_diag_handle = INVALID_HANDLE;
      Print("M15 entry diag export closed");
   }
   DumpRawDealHistory();
   Print("EA Deinitialized. Reason: ", reason);
}

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(!InpExportTradeLedger || InpSimMode) return;
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(trans.deal == 0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != InpSymbol) return;

   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY || entry == DEAL_ENTRY_INOUT)
   {
      ulong tracked_position_id = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
      int slot = LedgerFindSlotByPositionId(tracked_position_id);
      int stage = StageFromMagic((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC));
      if(slot < 0 && stage >= 1 && stage <= 3)
         slot = LedgerFindLatestActiveSlotByStage(stage);
      if(slot >= 0)
         LedgerWriteCloseFromDealSlot(slot, trans.deal, "deal_exit");
   }
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

bool FindStagePosByTrackedState(int stage, ulong tracked_ticket, ulong tracked_position_id,
                                ulong &ticket, double &entry, double &sl, double &vol)
{
   ticket = 0; entry = 0; sl = 0; vol = 0;
   if(stage < 1 || stage > 3) return false;
   ulong target_magic = InpMagic + (ulong)stage;

   if(tracked_ticket != 0 && PositionSelectByTicket(tracked_ticket))
   {
      if(PositionGetString(POSITION_SYMBOL) == InpSymbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == target_magic)
      {
         ulong cur_position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
         if(tracked_position_id == 0 || cur_position_id == tracked_position_id)
         {
            ticket = tracked_ticket;
            entry  = PositionGetDouble(POSITION_PRICE_OPEN);
            sl     = PositionGetDouble(POSITION_SL);
            vol    = PositionGetDouble(POSITION_VOLUME);
            return true;
         }
      }
   }

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != target_magic) continue;
      ulong cur_ticket = PositionGetTicket(i);
      ulong cur_position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(tracked_position_id != 0 && cur_position_id != tracked_position_id) continue;
      if(tracked_position_id == 0 && tracked_ticket != 0 && cur_ticket != tracked_ticket) continue;

      ticket = cur_ticket;
      entry  = PositionGetDouble(POSITION_PRICE_OPEN);
      sl     = PositionGetDouble(POSITION_SL);
      vol    = PositionGetDouble(POSITION_VOLUME);
      return true;
   }
   return false;
}

void RefreshLatestStageState(int stage)
{
   if(stage < 1 || stage > 3) return;
   int slot = LedgerFindLatestActiveSlotByStage(stage);
   if(slot < 0)
   {
      g_stage_tickets[stage] = 0;
      g_stage_pos_ids[stage] = 0;
      g_stage_entry[stage]   = 0;
      g_stage_orig_sl[stage] = 0;
      g_stage2_trail_on[stage] = false;
      return;
   }

   g_stage_tickets[stage] = g_ledger_ticket[slot];
   g_stage_pos_ids[stage] = g_ledger_position_id[slot];
   g_stage_entry[stage]   = g_ledger_fill_price[slot];
   g_stage_orig_sl[stage] = g_ledger_actual_stop[slot];
   g_stage2_trail_on[stage] = (g_ledger_stage2_trail_on_time[slot] > 0);
}

bool FindLatestStagePositionMeta(int stage, ulong &ticket, ulong &position_id)
{
   ticket = 0;
   position_id = 0;
   if(stage < 1 || stage > 3) return false;
   ulong target_magic = InpMagic + (ulong)stage;
   long best_time_msc = -1;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != target_magic) continue;
      ulong cur_ticket = PositionGetTicket(i);
      long open_time_msc = PositionGetInteger(POSITION_TIME_MSC);
      if(open_time_msc >= best_time_msc)
      {
         best_time_msc = open_time_msc;
         ticket = cur_ticket;
         position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      }
   }
   return (ticket != 0);
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

   // v3.25: Use PythonSMMA instead of GetMALastN(g_h2_sma55)
   double prev_sma55 = PythonSMMA(InpSymbol, InpH2Period, 55, 2);
   if(prev_sma55 == 0)
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
//| Compute merged direction code on the last completed M30 bar       |
//| Returns Python-style code: good=2, bad=-2, up=1, down=-1          |
//| Approximation-port of processing.segment_filter.filter_short_...  |
//+------------------------------------------------------------------+
int M30MergedDirectionCodeLastCompleted()
{
   // v3.25: use full available history (capped at 500 for performance), was 120
   int total_bars = Bars(InpSymbol, InpM30Period);
   int need = total_bars;
   if(need > 500) need = 500;
   if(need < 120) need = 120;
   double fast[], slow[];
   int got = GetM30SMAArrays_Python(fast, slow, need);
   if(got <= 0) return 0;
   if(ArraySize(fast) < got || ArraySize(slow) < got) return 0;

   int completed = got - 1; // ignore newest forming bar
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
      return dir_codes[completed - 1];

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

   return dir_codes[completed - 1];
}

int M30MergedDirectionLastCompleted()
{
   int code = M30MergedDirectionCodeLastCompleted();
   if(code == 0) return 0;
   return RawDirSign(code);
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
      LedgerStage2RecordTrailAttempt(ticket, current_sl, new_sl, sma13_now,
                                     false, false, 0, "no_ratchet");
      if(InpDebugStages)
         Print("[STAGE2 TRAIL] ticket=", ticket, " no ratchet (SMA13=",
               DoubleToString(sma13_now, 5), " SL=", DoubleToString(current_sl, 5), ")");
      return false;
   }

   if(InpSimMode)
   {
      Print("=== SIM TRAIL ticket=", ticket, " new_sl=", DoubleToString(new_sl, 5), " ===");
      LedgerStage2RecordTrailAttempt(ticket, current_sl, new_sl, sma13_now,
                                     true, true, TRADE_RETCODE_DONE, "sim");
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
      LedgerStage2RecordTrailAttempt(ticket, current_sl, new_sl, sma13_now,
                                     true, false, modres.retcode, modres.comment);
      Print("  [WARN] Stage2 trail SL modify failed: ticket=", ticket,
            " retcode=", modres.retcode, " comment=", modres.comment);
      return false;
   }
   bool modify_done = (modres.retcode == TRADE_RETCODE_DONE);
   LedgerStage2RecordTrailAttempt(ticket, current_sl, new_sl, sma13_now,
                                  true, modify_done, modres.retcode, modres.comment);
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
         LedgerStage2MarkTrailOn(ticket, rr, current_price, PositionGetDouble(POSITION_SL));
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
//| Live risk guard helpers                                           |
//+------------------------------------------------------------------+
datetime DayStart(datetime now)
{
   MqlDateTime parts;
   TimeToStruct(now, parts);
   parts.hour = 0;
   parts.min = 0;
   parts.sec = 0;
   return StructToTime(parts);
}

bool IsOurStrategyMagic(ulong magic)
{
   return (magic == InpMagic || StageFromMagic(magic) >= 1);
}

double OurFloatingNetProfit()
{
   double total = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != InpSymbol) continue;
      ulong magic = (ulong)PositionGetInteger(POSITION_MAGIC);
      if(!IsOurStrategyMagic(magic)) continue;
      total += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return total;
}

bool LiveRiskHistoryStats(double &closed_net, int &new_entries)
{
   closed_net = 0.0;
   new_entries = 0;
   datetime now = TimeCurrent();
   if(now <= 0) now = TimeLocal();
   if(!HistorySelect(DayStart(now), now + 60))
   {
      Print("[LIVE_RISK_BLOCK] HistorySelect failed: ", GetLastError());
      return false;
   }

   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0) continue;
      if(!HistoryDealSelect(deal)) continue;
      if(HistoryDealGetString(deal, DEAL_SYMBOL) != InpSymbol) continue;
      ulong magic = (ulong)HistoryDealGetInteger(deal, DEAL_MAGIC);
      if(!IsOurStrategyMagic(magic)) continue;

      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_IN || entry == DEAL_ENTRY_INOUT)
         new_entries++;
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY || entry == DEAL_ENTRY_INOUT)
      {
         closed_net += HistoryDealGetDouble(deal, DEAL_PROFIT);
         closed_net += HistoryDealGetDouble(deal, DEAL_SWAP);
         closed_net += HistoryDealGetDouble(deal, DEAL_COMMISSION);
      }
   }
   return true;
}

int CurrentSpreadPoints()
{
   double ask = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   if(ask > 0 && bid > 0 && point > 0)
      return (int)MathRound((ask - bid) / point);
   return (int)SymbolInfoInteger(InpSymbol, SYMBOL_SPREAD);
}

int EffectiveLeverage()
{
   if(InpLeverageOverride > 0) return InpLeverageOverride;
   long leverage = AccountInfoInteger(ACCOUNT_LEVERAGE);
   if(leverage > 0) return (int)leverage;
   return 500;
}

double FallbackMarginEstimate(double total_lots, double price)
{
   double contract = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract <= 0) contract = 100.0;
   int leverage = EffectiveLeverage();
   if(leverage <= 0) leverage = 500;
   return (total_lots * price * contract) / (double)leverage;
}

void LiveRiskBlockLog(string trigger_tag, string signal_src, int signal_dir,
                      datetime anchor_time, string reason)
{
   Print(trigger_tag, " [LIVE_RISK_BLOCK] ", reason);
   DiagLog(trigger_tag, "Execute",
           "mode=" + signal_src +
           " dir=" + DirText(signal_dir) +
           " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
           " result=LIVE_RISK_BLOCK reason=" + reason);
}

bool LiveRiskAccountGuardPass(string trigger_tag, string signal_src, int signal_dir,
                              datetime anchor_time)
{
   if(!InpEnableLiveRiskGuards || InpSimMode)
      return true;

   int spread_points = CurrentSpreadPoints();
   if(InpMaxSpreadPoints > 0 && spread_points > InpMaxSpreadPoints)
   {
      LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                       "spread " + IntegerToString(spread_points) +
                       " > max " + IntegerToString(InpMaxSpreadPoints));
      return false;
   }

   double closed_net = 0.0;
   int new_entries_today = 0;
   if(!LiveRiskHistoryStats(closed_net, new_entries_today))
   {
      LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                       "history stats unavailable");
      return false;
   }

   double floating_net = OurFloatingNetProfit();
   double daily_net = closed_net + floating_net;
   if(InpMaxDailyLossUSD > 0 && daily_net <= -InpMaxDailyLossUSD)
   {
      LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                       "daily net " + DoubleToString(daily_net, 2) +
                       " <= -" + DoubleToString(InpMaxDailyLossUSD, 2));
      return false;
   }

   if(InpMaxNewPositionsPerDay > 0 && new_entries_today + InpStageCount > InpMaxNewPositionsPerDay)
   {
      LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                       "daily entries " + IntegerToString(new_entries_today) +
                       " + stages " + IntegerToString(InpStageCount) +
                       " > max " + IntegerToString(InpMaxNewPositionsPerDay));
      return false;
   }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpLiveBalanceCap > 0 && InpMaxDrawdownUSD > 0 &&
      InpLiveBalanceCap - equity >= InpMaxDrawdownUSD)
   {
      LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                       "drawdown from cap " + DoubleToString(InpLiveBalanceCap - equity, 2) +
                       " >= " + DoubleToString(InpMaxDrawdownUSD, 2));
      return false;
   }

   double margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   if(InpMarginGuardPct > 0 && margin_level > 0 && margin_level < InpMarginGuardPct)
   {
      LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                       "current margin level " + DoubleToString(margin_level, 2) +
                       "% < " + DoubleToString(InpMarginGuardPct, 2) + "%");
      return false;
   }

   return true;
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
                       ? ("1H_M30_4H_S" + IntegerToString(stage))
                       : "1H_M30_4H";

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
         g_stage_pos_ids[stage] = synth_ticket;
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

   ulong position_ticket = res.order;
   ulong position_id = 0;
   if(res.deal > 0 && HistoryDealSelect(res.deal))
      position_id = (ulong)HistoryDealGetInteger(res.deal, DEAL_POSITION_ID);
   ulong latest_stage_ticket = 0;
   ulong latest_stage_pos_id = 0;
   if(FindLatestStagePositionMeta(stage, latest_stage_ticket, latest_stage_pos_id))
   {
      if(latest_stage_ticket != 0)
         position_ticket = latest_stage_ticket;
      if(latest_stage_pos_id != 0)
         position_id = latest_stage_pos_id;
   }

   // Populate stage globals for the new 3-stage TP system
   if(stage >= 1 && stage <= 3)
   {
      g_stage_tickets[stage] = position_ticket;
      g_stage_pos_ids[stage] = position_id;
      g_stage_entry[stage]   = fill_price;
      g_stage_orig_sl[stage] = actual_stop;
      g_stage2_trail_on[stage] = false;
   }
   return position_ticket;
}

//+------------------------------------------------------------------+
//| Close position                                                    |
//+------------------------------------------------------------------+
bool ClosePos(ulong ticket)
{
   if(InpSimMode)
   {
      Print("=== SIM CLOSE ticket=", ticket, " ===");
      return true;
   }
   if(!g_trade.PositionClose(ticket))
   {
      Print("Close failed: ticket=", ticket, " err=", GetLastError());
      return false;
   }
   Print("Closed ticket=", ticket);
   return true;
}

//+------------------------------------------------------------------+
//| v3.0 Layer 1: H2 Bias_55 计算                                       |
//| 返回: |Bias_55| = |(close - SMA55) / SMA55| × 100              |
//+------------------------------------------------------------------+
//| v3.25: Bias_55 uses PythonSMMA to match Python calc_smma()        |
//+------------------------------------------------------------------+
double CalcBias55()
{
   double close_arr[];
   if(CopyClose(InpSymbol, InpH2Period, 1, 1, close_arr) <= 0) return 0;
   double close = close_arr[0];
   double sma55 = PythonSMMA(InpSymbol, InpH2Period, 55, 1);
   if(sma55 == 0) return 0;
   return MathAbs((close - sma55) / sma55) * 100.0;
}

//+------------------------------------------------------------------+
//| v3.25: Bias_5 uses PythonSMMA to match Python calc_smma()         |
//+------------------------------------------------------------------+
double CalcBias5()
{
   double close_arr[];
   if(CopyClose(InpSymbol, InpH2Period, 1, 1, close_arr) <= 0) return 0;
   double close = close_arr[0];
   double sma5 = PythonSMMA(InpSymbol, InpH2Period, 5, 1);
   if(sma5 == 0) return 0;
   return MathAbs((close - sma5) / sma5) * 100.0;
}

//+------------------------------------------------------------------+
//| v3.0 Layer 3: Bias_5 历史滚动 top X% 阈值计算                    |
//| 计算最近 N 根 H2 bar 的 Bias_5,取第 (1 - X%) 分位作为阈值        |
//| 返回: true = 通过 top X% (Bias_5 >= 阈值)                        |
//+------------------------------------------------------------------+
bool IsBias5TopPct(double current_bias5)
{
   if(!InpUseLayer3) return true;

   int n = InpBias5Lookback;
   double close_arr[], biases[];
   ArraySetAsSeries(close_arr, true);
   ArrayResize(biases, n);
   if(CopyClose(InpSymbol, InpH2Period, 1, n, close_arr) <= 0) return false;

   double s0 = PythonSMMA(InpSymbol, InpH2Period, 5, 0);
   if(s0 == 0) return false;

   int valid = 0;
   for(int i = 0; i < n; i++)
   {
      double s = PythonSMMA(InpSymbol, InpH2Period, 5, i + 1);
      if(s == 0) continue;
      biases[valid] = MathAbs((close_arr[i] - s) / s) * 100.0;
      valid++;
   }
   if(valid < 10) return true;

   ArrayResize(biases, valid);
   ArraySort(biases);
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
                   double ma5_prev2, double ma5_prev1, double ma13_prev1, double ma13_prev2)
{
   if(ma13_prev1 == 0 || ma13_prev2 == 0 || ma5_prev1 == 0 || ma5_prev2 == 0) return 0;

   double gap_pct = MathAbs(ma5_prev1 - ma13_prev1) / ma13_prev1 * 100.0;
   if(gap_pct > InpPreCrossGapPct) return 0;

   // v3.25: Exclude bars where SMA5 also crosses SMA13 (these are 'cross', not 'pre_cross')
   // Python: direction.py line 145 skips direction[i] in ("good", "bad")
   bool sma5_prev_above = (ma5_prev2 > ma13_prev2);
   bool sma5_curr_above = (ma5_prev1 > ma13_prev1);
   if(sma5_prev_above != sma5_curr_above) return 0;

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
   static datetime s_last_completed_bar = 0;
   datetime completed_bar = iTime(InpSymbol, InpM30Period, 1);
   if(completed_bar <= 0) return;
   if(completed_bar == s_last_completed_bar) return;
   s_last_completed_bar = completed_bar;

   // v3.25: Must use PythonSMMA for post_n direction detection to match Python
   // MODE_SMMA produces different cross points → counter diverges and runs away
   double ma5_p1  = PythonSMMA(InpSymbol, InpM30Period, 5, 1);
   double ma5_p2  = PythonSMMA(InpSymbol, InpM30Period, 5, 2);
   double ma13_p1 = PythonSMMA(InpSymbol, InpM30Period, 13, 1);
   double ma13_p2 = PythonSMMA(InpSymbol, InpM30Period, 13, 2);
   if(ma5_p1 == 0 || ma13_p1 == 0) { g_post_n_counter = 0; g_last_cross_dir = 0; return; }

   bool curr_above = ma5_p1 > ma13_p1;
   bool prev_above = ma5_p2 > ma13_p2;
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
   // v3.25: Python DOES reset when current trend doesn't match last cross direction
   // direction.py line 141-146: counter=0, last_cross=None, post_n=0
   else
   {
      g_post_n_counter = 0;
      g_last_cross_dir = 0;
   }
}

//+------------------------------------------------------------------+
//| v3.23: merged post_n counter — matches Python merged_post_cross_n |
//| Uses M30MergedDirectionLastCompleted() which absorbs short segments|
//+------------------------------------------------------------------+
void UpdateMergedPostNState()
{
   int merged_code = M30MergedDirectionCodeLastCompleted();
   if(merged_code == 0) return;  // can't determine
   int merged = RawDirSign(merged_code);

   if(g_merged_last_dir == 0)
   {
      // First call
      g_merged_post_n_counter = 1;
      g_merged_last_dir = merged;
   }
   else if(merged != g_merged_last_dir)
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

   if(merged_code == 2)
   {
      g_merged_strict_post_n_counter = 1;
      g_merged_strict_last_cross = 1;
   }
   else if(merged_code == -2)
   {
      g_merged_strict_post_n_counter = -1;
      g_merged_strict_last_cross = -1;
   }
   else if(merged_code == 1 && g_merged_strict_last_cross > 0)
   {
      g_merged_strict_post_n_counter =
         (g_merged_strict_post_n_counter > 0) ? g_merged_strict_post_n_counter + 1 : 1;
   }
   else if(merged_code == -1 && g_merged_strict_last_cross < 0)
   {
      g_merged_strict_post_n_counter =
         (g_merged_strict_post_n_counter < 0) ? g_merged_strict_post_n_counter - 1 : -1;
   }
   else
   {
      g_merged_strict_post_n_counter = 0;
      g_merged_strict_last_cross = 0;
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

   if(!LiveRiskAccountGuardPass(trigger_tag, signal_src, signal_dir, anchor_time))
      return false;

   // --- v3.27: live guard-aware pre-trade margin/free-margin check ---
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
      if(InpEnableLiveRiskGuards && !InpSimMode && InpLiveMaxLotCap > 0 &&
         stage_lots_arr[stage] > InpLiveMaxLotCap)
      {
         LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                          "stage " + IntegerToString(stage) +
                          " lot " + DoubleToString(stage_lots_arr[stage], 2) +
                          " > live max lot cap " + DoubleToString(InpLiveMaxLotCap, 2));
         return false;
      }
      total_lots += stage_lots_arr[stage];
   }

   double ask_price = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   double bid_price = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   double margin_price = (signal_dir == +1) ? ask_price : bid_price;
   if(margin_price <= 0) margin_price = real_entry;

   double est_margin = 0.0;
   bool margin_calc_ok = true;
   ENUM_ORDER_TYPE margin_order_type = (signal_dir == +1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   for(int stage = 1; stage <= InpStageCount; stage++)
   {
      double stage_margin = 0.0;
      if(!OrderCalcMargin(margin_order_type, InpSymbol, stage_lots_arr[stage],
                          margin_price, stage_margin))
      {
         margin_calc_ok = false;
         break;
      }
      est_margin += stage_margin;
   }
   string margin_calc_status = margin_calc_ok ? "ORDER_CALC" : "FALLBACK";
   if(!margin_calc_ok)
      est_margin = FallbackMarginEstimate(total_lots, margin_price);

   double est_free_after = free_margin - est_margin;
   double est_margin_after = margin + est_margin;
   double est_margin_level_after = (est_margin_after > 0.0) ? equity / est_margin_after * 100.0 : 0.0;

   Print("  current account state: Balance: ", DoubleToString(balance, 2),
         ", Equity: ", DoubleToString(equity, 2),
         ", Margin: ", DoubleToString(margin, 2),
         ", FreeMargin: ", DoubleToString(free_margin, 2));
   Print("  calculated account state: TotalLots: ", DoubleToString(total_lots, 2),
         ", EstMargin: ", DoubleToString(est_margin, 2),
         ", EstFreeAfter: ", DoubleToString(est_free_after, 2),
         ", EstMarginLevelAfter: ", DoubleToString(est_margin_level_after, 2),
         "%, MarginCalc: ", margin_calc_status,
         ", Leverage: 1:", IntegerToString(EffectiveLeverage()));

   if(InpEnableLiveRiskGuards && !InpSimMode)
   {
      if(!margin_calc_ok)
      {
         LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                          "OrderCalcMargin failed; fallback estimate=" +
                          DoubleToString(est_margin, 2));
         return false;
      }
      if(est_free_after < 0)
      {
         LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                          "estimated free margin after signal " +
                          DoubleToString(est_free_after, 2) + " < 0.00");
         return false;
      }
      if(InpMarginGuardPct > 0 && est_margin_level_after > 0 &&
         est_margin_level_after < InpMarginGuardPct)
      {
         LiveRiskBlockLog(trigger_tag, signal_src, signal_dir, anchor_time,
                          "estimated margin level after signal " +
                          DoubleToString(est_margin_level_after, 2) + "% < " +
                          DoubleToString(InpMarginGuardPct, 2) + "%");
         return false;
      }
   }
   else if(est_free_after < 0 && !InpSimMode)
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
      {
         any_opened = true;
         LedgerRegisterOpen(stage, t, g_stage_pos_ids[stage], signal_src, trigger_tag, anchor_time,
                            signal_dir, real_entry, stop_price,
                            g_stage_entry[stage], g_stage_orig_sl[stage],
                            stage_lot, stop_pts);
      }
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

   int stage_count = OurStageCount();
   datetime completed_m15_open = 0;
   int m15_shift = -1;
   int m30_shift = -1;
   datetime slot_m30_open = 0;
   int slot_in_m30 = 0;
   bool is_slot1 = false;
   bool is_slot2 = false;
   datetime anchor_time = 0;
   int pre_cross = 0;
   bool is_cross_mode = false;
   int merged_post_n = 0;
   int signal_dir = 0;
   string signal_src = "";
   bool layer1_checked = false;
   bool layer1_pass = false;
   bool layer3_checked = false;
   bool layer3_pass = false;
   double m15_close = EMPTY_VALUE;
   double m15_sma13 = EMPTY_VALUE;
   double stop_price = EMPTY_VALUE;
   double entry_proxy = EMPTY_VALUE;
   double stop_pts_spec = EMPTY_VALUE;

   if(stage_count >= InpMaxPos)
   {
      DiagLog("[M15]", "Candidate",
              "result=SKIP_MAX_POS stages=" + IntegerToString(stage_count) +
              " max_pos=" + IntegerToString(InpMaxPos));
      M15EntryDiagWrite("SKIP_MAX_POS", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   completed_m15_open = iTime(InpSymbol, InpM15Period, 1);
   if(completed_m15_open <= 0)
   {
      M15EntryDiagWrite("NO_M15_BAR", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   m15_shift = iBarShift(InpSymbol, InpM15Period, completed_m15_open, true);
   if(m15_shift < 0)
   {
      M15EntryDiagWrite("NO_M15_SHIFT", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   m30_shift = iBarShift(InpSymbol, InpM30Period, completed_m15_open, false);
   if(m30_shift < 0)
   {
      M15EntryDiagWrite("NO_M30_SHIFT", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   slot_m30_open = iTime(InpSymbol, InpM30Period, m30_shift);
   if(slot_m30_open <= 0)
   {
      M15EntryDiagWrite("NO_SLOT_M30", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   slot_in_m30 = (int)((completed_m15_open - slot_m30_open) / PeriodSeconds(InpM15Period)) + 1;
   if(slot_in_m30 < 1 || slot_in_m30 > 2)
   {
      M15EntryDiagWrite("NO_SLOT", "slot_in_m30_out_of_range", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   is_slot1 = (m30_shift == 0 && slot_in_m30 == 1 && slot_m30_open == cur_bar);
   is_slot2 = (m30_shift == 1 && slot_in_m30 == 2);
   if(is_slot2 && !InpEnableM15Slot2)
   {
      M15EntryDiagWrite("SLOT2_DISABLED", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }
   if(!is_slot1 && !is_slot2)
   {
      M15EntryDiagWrite("NO_SLOT", "not_runtime_slot", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   anchor_time = slot_m30_open + PeriodSeconds(InpM30Period);
   if(g_signal_anchor_time == anchor_time)
   {
      M15EntryDiagWrite("SAME_ANCHOR", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   double m15_close_arr[];
   if(CopyClose(InpSymbol, InpM15Period, m15_shift, 1, m15_close_arr) <= 0)
   {
      M15EntryDiagWrite("NO_M15_CLOSE", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }
   double m15_sma13_arr[];
   if(CopyBuffer(g_ma_slow_m15, 0, m15_shift, 1, m15_sma13_arr) <= 0)
   {
      M15EntryDiagWrite("NO_M15_SMA13", "copybuffer_failed", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }
   m15_sma13 = m15_sma13_arr[0];
   m15_close = m15_close_arr[0];
   if(m15_sma13 <= 0 || m15_sma13 == EMPTY_VALUE)
   {
      M15EntryDiagWrite("NO_M15_SMA13", "invalid_value", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   double ctx_ma5_curr = 0.0;
   double ctx_ma13_curr = 0.0;
   double ctx_ma5_prev = 0.0;
   double ctx_ma13_prev = 0.0;
   double ctx_close_curr = 0.0;
   double ctx_close_prev = 0.0;
   double ctx_fast[];
   double ctx_slow[];
   int ctx_nsma = 0;
   string slot_suffix = is_slot2 ? "slot2" : "slot1";
   string log_tag = is_slot2 ? "[M15 SLOT2]" : "[M15 SLOT1]";

   if(is_slot2)
   {
      MqlRates slot2_rates[];
      int slot2_nrates = GetM30Rates(slot2_rates, n_rates);
      if(slot2_nrates < InpSlowMA + 5)
      {
         M15EntryDiagWrite("NO_SLOT2_RATES", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                           slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                           stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                           layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                           m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
         return false;
      }

      ctx_nsma = GetM30SMAArrays_Python(ctx_fast, ctx_slow, slot2_nrates);
      if(ctx_nsma < InpSlowMA + 5)
      {
         M15EntryDiagWrite("NO_SLOT2_SMMA", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                           slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                           stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                           layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                           m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
         return false;
      }

      int parent_idx = ctx_nsma - 1 - m30_shift;
      if(parent_idx < 1 || parent_idx >= ctx_nsma - 1)
      {
         M15EntryDiagWrite("NO_SLOT2_PARENT", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                           slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                           stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                           layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                           m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
         return false;
      }

      ctx_ma5_curr = ctx_fast[parent_idx];
      ctx_ma13_curr = ctx_slow[parent_idx];
      ctx_ma5_prev = ctx_fast[parent_idx - 1];
      ctx_ma13_prev = ctx_slow[parent_idx - 1];
      ctx_close_curr = slot2_rates[parent_idx].close;
      ctx_close_prev = slot2_rates[parent_idx - 1].close;
   }
   else
   {
      ctx_ma5_curr = ma5_curr;
      ctx_ma13_curr = ma13_curr;
      ctx_ma5_prev = ma5_prev;
      ctx_ma13_prev = ma13_prev;
      ctx_close_curr = rates[n_rates - 1].close;
      ctx_close_prev = rates[n_rates - 2].close;
      ctx_nsma = n_sma;
   }

   pre_cross = DetectPreCross(ctx_close_prev, ctx_close_curr,
                              ctx_ma5_prev, ctx_ma5_curr, ctx_ma13_curr, ctx_ma13_prev);
   bool is_pre_cross_mode = (pre_cross != 0);

   bool curr_above = ctx_ma5_curr > ctx_ma13_curr;
   bool prev_above = ctx_ma5_prev > ctx_ma13_prev;
   is_cross_mode = ((!prev_above && curr_above) || (prev_above && !curr_above));
   merged_post_n = g_merged_post_n_counter;
   bool is_post_n_mode = (merged_post_n >= InpPostNMin && merged_post_n <= InpPostNMax);
   bool is_post_n_mode_neg = (merged_post_n <= -InpPostNMin && merged_post_n >= -InpPostNMax);

   if(is_pre_cross_mode)
   {
      signal_dir = pre_cross;
      signal_src = "pre_cross_m15_" + slot_suffix;
   }
   else if(is_cross_mode)
   {
      signal_dir = curr_above ? +1 : -1;
      signal_src = "cross_m15_" + slot_suffix;
   }
   else if(is_post_n_mode)
   {
      signal_dir = +1;
      signal_src = "post_n" + IntegerToString(merged_post_n) + "_m15_" + slot_suffix;
   }
   else if(is_post_n_mode_neg)
   {
      signal_dir = -1;
      signal_src = "post_n" + IntegerToString(-merged_post_n) + "_m15_" + slot_suffix;
   }

   if(signal_dir == 0)
   {
      M15EntryDiagWrite("NO_SIGNAL_DIR", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }
   DiagLog(log_tag, "Candidate",
           "mode=" + signal_src +
           " dir=" + DirText(signal_dir) +
           " anchor=" + TimeToString(anchor_time, TIME_DATE|TIME_MINUTES) +
           " m15_close=" + DoubleToString(m15_close, 5) +
           " m15_smma13=" + DoubleToString(m15_sma13, 5) +
           " post_n_counter=" + IntegerToString(g_post_n_counter) +
           " merged_post_n_counter=" + IntegerToString(merged_post_n));

   layer1_checked = true;
   layer1_pass = PassLayer1Gate(log_tag);
   if(!layer1_pass)
   {
      M15EntryDiagWrite("LAYER1_FAIL", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }
   layer3_checked = true;
   layer3_pass = PassLayer3Gate(log_tag);
   if(!layer3_pass)
   {
      M15EntryDiagWrite("LAYER3_FAIL", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   if(is_pre_cross_mode || is_cross_mode)
   {
      int seg_dir = (signal_dir == +1) ? -1 : +1;
      double stop_sma = is_slot2 ? FindStopSMA(ctx_fast, ctx_slow, ctx_nsma, seg_dir)
                                 : FindStopSMA(fast_ma, slow_ma, n_sma, seg_dir);
      if(stop_sma <= 0)
      {
         if(InpDebugStages)
            Print(log_tag, " [SKIP] ", signal_src, " 模式: 上一段 SMA13 无有效极值");
         DiagLog(log_tag, "Stop",
                 "mode=" + signal_src + " result=NO_STOP_EXTREME");
         M15EntryDiagWrite("STOP_FAIL", "NO_STOP_EXTREME", cur_bar, completed_m15_open, m15_shift, m30_shift,
                           slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                           stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                           layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                           m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
         return false;
      }
      stop_price = NormalizeDouble(stop_sma, 5);
   }
   else
   {
      double sma13_now = ctx_ma13_curr;
      if(signal_dir == +1 && m15_close <= sma13_now)
      {
         DiagLog(log_tag, "Stop",
                 "mode=" + signal_src + " result=POSTN_STOP_INVALID");
         M15EntryDiagWrite("STOP_FAIL", "POSTN_STOP_INVALID", cur_bar, completed_m15_open, m15_shift, m30_shift,
                           slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                           stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                           layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                           m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
         return false;
      }
      if(signal_dir == -1 && m15_close >= sma13_now)
      {
         DiagLog(log_tag, "Stop",
                 "mode=" + signal_src + " result=POSTN_STOP_INVALID");
         M15EntryDiagWrite("STOP_FAIL", "POSTN_STOP_INVALID", cur_bar, completed_m15_open, m15_shift, m30_shift,
                           slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                           stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                           layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                           m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
         return false;
      }
      stop_price = NormalizeDouble(sma13_now, 5);
   }

   double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   if(point == 0) point = 0.001;
   entry_proxy = m15_close;
   double m15_stop_pts = MathAbs(m15_close - stop_price) / point;
   stop_pts_spec = m15_stop_pts / 1000.0;
   DiagLog(log_tag, "Stop",
            "mode=" + signal_src +
            " stop_price=" + DoubleToString(stop_price, 5) +
            " entry_proxy=" + DoubleToString(m15_close, 5) +
            " stop_pts=" + DoubleToString(m15_stop_pts/1000.0, 3));
   if(m15_stop_pts < InpStopLo || m15_stop_pts > InpStopHi)
   {
      DiagLog(log_tag, "Stop",
              "mode=" + signal_src + " result=SPEC_FAIL_PROXY");
      M15EntryDiagWrite("SPEC_FAIL", "SPEC_FAIL_PROXY", cur_bar, completed_m15_open, m15_shift, m30_shift,
                        slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                        stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                        layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                        m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
      return false;
   }

   if(InpUseM15RescueTag)
      signal_src = signal_src + "_replace_or_rescue";

   bool executed = ExecuteSignalByMarket(signal_dir, signal_src, stop_price, anchor_time, log_tag);
   M15EntryDiagWrite(executed ? "EXECUTED" : "EXECUTE_FAIL", "", cur_bar, completed_m15_open, m15_shift, m30_shift,
                     slot_m30_open, slot_in_m30, is_slot1, is_slot2, anchor_time,
                     stage_count, pre_cross, is_cross_mode, merged_post_n, signal_dir, signal_src,
                     layer1_checked, layer1_pass, layer3_checked, layer3_pass,
                     m15_close, m15_sma13, stop_price, entry_proxy, stop_pts_spec);
   return executed;
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
   int n_sma = GetM30SMAArrays_Python(fast_ma, slow_ma, n_rates);
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

   if(ma5_prev == 0 || ma13_prev == 0) return;

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

   // --- MANAGE EXISTING POSITIONS (v3.27 multi-slot stage state) ---
   // Cache current prices once per tick. Stage1/2 legacy behavior still uses BID;
   // diagnostics also record ASK and direction-aware close-side R.
   double bid_price = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   double ask_price = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   double cur_price = bid_price;

   if(InpExportTradeLedger && !InpSimMode)
   {
      for(int stage = 1; stage <= 2; stage++)
      {
         for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
         {
            if(!g_ledger_active[slot]) continue;
            if(g_ledger_stage[slot] != stage) continue;

            ulong ticket = 0;
            double entry = 0, sl = 0, vol = 0;
            if(!FindStagePosByTrackedState(stage, g_ledger_ticket[slot], g_ledger_position_id[slot],
                                           ticket, entry, sl, vol))
            {
               if(InpDebugStages)
                  Print("[STAGE", stage, "] tracked position gone, slot=", slot,
                        " ticket=", g_ledger_ticket[slot],
                        " position_id=", g_ledger_position_id[slot]);
               LedgerTryFinalizeFromHistoryByTicket(g_ledger_ticket[slot], "position_gone");
               RefreshLatestStageState(stage);
               continue;
            }

            ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            bool trail_before = (stage == 2 && g_ledger_stage2_trail_on_time[slot] > 0);
            g_stage2_trail_on[stage] = trail_before;
            int action = CheckStageExit(stage, ticket, entry, g_ledger_actual_stop[slot],
                                        cur_price, h2_x);
            bool trail_after = (stage == 2 && g_stage2_trail_on[stage]);
            StagePriceDiagWrite(stage, ticket, entry, g_ledger_actual_stop[slot], sl, vol,
                                cur_price, bid_price, ask_price, ptype,
                                trail_before, trail_after, action, new_m30_bar, new_m15_bar);
            if(action == 1)
            {
               Print("[EXIT] stage ", stage, " slot=", slot, " ticket=", ticket);
               if(stage == 1)
                  LedgerMarkExitIntentByTicket(ticket, "stage1_tp");
               else if(stage == 2)
                  LedgerMarkExitIntentByTicket(ticket, "stage2_forced");
               if(ClosePos(ticket))
                  RefreshLatestStageState(stage);
               else
               {
                  LedgerMarkExitIntentByTicket(ticket, "");
                  if(InpDebugStages)
                     Print("[EXIT RETRY] stage ", stage, " slot=", slot,
                           " ticket=", ticket, " close failed; keeping state");
               }
            }
         }
      }

      if(InpStage3On)
      {
         double stage3_fast[], stage3_slow[];
         bool have_stage3_cross = GetMALastN(g_ma_fast_m30, 2, stage3_fast) &&
                                  GetMALastN(g_ma_slow_m30, 2, stage3_slow);
         for(int slot = 0; slot < LEDGER_MAX_TRACK; slot++)
         {
            if(!g_ledger_active[slot]) continue;
            if(g_ledger_stage[slot] != 3) continue;

            ulong ticket = 0;
            double entry = 0, sl = 0, vol = 0;
            if(!FindStagePosByTrackedState(3, g_ledger_ticket[slot], g_ledger_position_id[slot],
                                           ticket, entry, sl, vol))
            {
               if(InpDebugStages)
                  Print("[STAGE3] tracked position gone, slot=", slot,
                        " ticket=", g_ledger_ticket[slot],
                        " position_id=", g_ledger_position_id[slot]);
               LedgerTryFinalizeFromHistoryByTicket(g_ledger_ticket[slot], "position_gone");
               RefreshLatestStageState(3);
               continue;
            }
            if(!have_stage3_cross) continue;

            ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            bool prev_above = (stage3_fast[1] > stage3_slow[1]);
            bool curr_above = (stage3_fast[0] > stage3_slow[0]);
            bool just_good = (!prev_above && curr_above);
            bool just_bad  = (prev_above && !curr_above);
            bool reverse = (ptype == POSITION_TYPE_BUY  && just_bad)
                        || (ptype == POSITION_TYPE_SELL && just_good);

            if(reverse)
            {
               Print("[STAGE3 CROSS EXIT] slot=", slot, " ticket=", ticket, " cross=",
                     (just_bad ? "DEAD" : "GOLDEN"),
                     " pos_type=", (ptype == POSITION_TYPE_BUY ? "BUY" : "SELL"));
               LedgerMarkExitIntentByTicket(ticket, "stage3_cross_exit");
               if(ClosePos(ticket))
                  RefreshLatestStageState(3);
               else
               {
                  LedgerMarkExitIntentByTicket(ticket, "");
                  if(InpDebugStages)
                     Print("[STAGE3 EXIT RETRY] slot=", slot, " ticket=", ticket,
                           " close failed; keeping state");
               }
            }
         }
      }
   }
   else
   {
      // Legacy fallback for sim mode or when trade-ledger tracking is disabled.
      for(int stage = 1; stage <= 2; stage++)
      {
         if(g_stage_tickets[stage] == 0) continue;
         ulong ticket = 0;
         double entry = 0, sl = 0, vol = 0;
         if(!FindOurStagePos(stage, ticket, entry, sl, vol))
         {
            ulong old_ticket = g_stage_tickets[stage];
            if(InpDebugStages)
               Print("[STAGE", stage, "] position gone, clearing state");
            LedgerTryFinalizeFromHistoryByTicket(old_ticket, "position_gone");
            g_stage_tickets[stage] = 0;
            g_stage_pos_ids[stage] = 0;
            g_stage2_trail_on[stage] = false;
            continue;
         }
         ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         bool trail_before = g_stage2_trail_on[stage];
         int action = CheckStageExit(stage, ticket, entry, g_stage_orig_sl[stage],
                                     cur_price, h2_x);
         bool trail_after = g_stage2_trail_on[stage];
         StagePriceDiagWrite(stage, ticket, entry, g_stage_orig_sl[stage], sl, vol,
                             cur_price, bid_price, ask_price, ptype,
                             trail_before, trail_after, action, new_m30_bar, new_m15_bar);
         if(action == 1)
         {
            Print("[EXIT] stage ", stage, " ticket=", ticket);
            if(stage == 1)
               LedgerMarkExitIntentByTicket(ticket, "stage1_tp");
            else if(stage == 2)
               LedgerMarkExitIntentByTicket(ticket, "stage2_forced");
            if(ClosePos(ticket))
            {
               g_stage_tickets[stage] = 0;
               g_stage_pos_ids[stage] = 0;
               g_stage2_trail_on[stage] = false;
            }
            else
            {
               LedgerMarkExitIntentByTicket(ticket, "");
               if(InpDebugStages)
                  Print("[EXIT RETRY] stage ", stage, " ticket=", ticket, " close failed; keeping state");
            }
         }
      }

      if(InpStage3On && g_stage_tickets[3] != 0)
      {
         ulong ticket = 0;
         double entry = 0, sl = 0, vol = 0;
         if(!FindOurStagePos(3, ticket, entry, sl, vol))
         {
            ulong old_ticket = g_stage_tickets[3];
            if(InpDebugStages)
               Print("[STAGE3] position gone, clearing state");
            LedgerTryFinalizeFromHistoryByTicket(old_ticket, "position_gone");
            g_stage_tickets[3] = 0;
            g_stage_pos_ids[3] = 0;
         }
         else
         {
            ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            double stage3_fast[], stage3_slow[];
            if(GetMALastN(g_ma_fast_m30, 2, stage3_fast) && GetMALastN(g_ma_slow_m30, 2, stage3_slow))
            {
               bool prev_above = (stage3_fast[1] > stage3_slow[1]);
               bool curr_above = (stage3_fast[0] > stage3_slow[0]);
               bool just_good = (!prev_above && curr_above);
               bool just_bad  = (prev_above && !curr_above);
               bool reverse = (ptype == POSITION_TYPE_BUY  && just_bad)
                           || (ptype == POSITION_TYPE_SELL && just_good);
               if(reverse)
               {
                  Print("[STAGE3 CROSS EXIT] ticket=", ticket, " cross=",
                        (just_bad ? "DEAD" : "GOLDEN"),
                        " pos_type=", (ptype == POSITION_TYPE_BUY ? "BUY" : "SELL"));
                  LedgerMarkExitIntentByTicket(ticket, "stage3_cross_exit");
                  if(ClosePos(ticket))
                  {
                     g_stage_tickets[3] = 0;
                     g_stage_pos_ids[3] = 0;
                  }
                  else
                  {
                     LedgerMarkExitIntentByTicket(ticket, "");
                     if(InpDebugStages)
                        Print("[STAGE3 EXIT RETRY] ticket=", ticket, " close failed; keeping state");
                  }
               }
            }
         }
      }
   }

   // v3.26: post_n state must advance once per completed M30 bar, not every tick
   if(new_m30_bar)
   {
      UpdatePostNState();
      UpdateMergedPostNState();
   }

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
                                  ma5_prev2, ma5_prev, ma13_prev, ma13_prev2);
   bool is_pre_cross_mode = (pre_cross != 0);
   bool is_cross_mode = (cross != 0);
   int merged_post_n = g_merged_post_n_counter;
   bool is_post_n_mode = (merged_post_n >= InpPostNMin && merged_post_n <= InpPostNMax);
   bool is_post_n_mode_neg = (merged_post_n <= -InpPostNMin && merged_post_n >= -InpPostNMax);

   // Mode priority: pre_cross > cross > post_n, matching Python de-dup priority.
   // v3.23: post_n is evaluated FIRST as an independent opportunity,
   //        then pre_cross/cross override if active. This matches Python
   //        baseline where all three modes are treated as separate chances.
   if(is_post_n_mode)
   {
      signal_dir = +1;
      signal_src = "post_n" + IntegerToString(merged_post_n);
   }
   else if(is_post_n_mode_neg)
   {
      signal_dir = -1;
      signal_src = "post_n" + IntegerToString(-merged_post_n);
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
              " post_n_counter=" + IntegerToString(g_post_n_counter) +
              " merged_post_n_counter=" + IntegerToString(merged_post_n) +
              " strict_merged_post_n_counter=" + IntegerToString(g_merged_strict_post_n_counter));
      if(StringFind(signal_src, "post_n") == 0)
      {
         bool strict_post_n_ok =
            (signal_dir == +1 &&
             g_merged_strict_post_n_counter >= InpPostNMin &&
             g_merged_strict_post_n_counter <= InpPostNMax) ||
            (signal_dir == -1 &&
             g_merged_strict_post_n_counter <= -InpPostNMin &&
             g_merged_strict_post_n_counter >= -InpPostNMax);
         if(!strict_post_n_ok)
         {
            DiagLog("[M30 CLOSE]", "Candidate",
                    "mode=" + signal_src +
                    " result=SKIP_STRICT_MERGED_POSTN" +
                    " merged_post_n_counter=" + IntegerToString(merged_post_n) +
                    " strict_merged_post_n_counter=" + IntegerToString(g_merged_strict_post_n_counter));
            return;
         }
      }
      // v3.26: post_n must pass the same Layer1/Layer3 gates as
      // pre_cross/cross unless we later add a persisted "qualified cross"
      // state machine. Bypassing the gates overfires badly in full backtests.
      if(!PassLayer1Gate("[M30 CLOSE]")) return;
      if(!PassLayer3Gate("[M30 CLOSE]")) return;


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
         // v3.26: post_n SL must use Python-style SMA13, not MODE_SMMA
         double sma13_py = PythonSMMA(InpSymbol, InpM30Period, InpSlowMA, 1);
         if(sma13_py > 0)
         {
            stop_price = NormalizeDouble(sma13_py, 5);
         }
         else
         {
            DiagLog("[M30 CLOSE]", "Stop",
                    "mode=" + signal_src + " result=POSTN_STOP_INVALID");
            return;
         }
      }

      double exec_point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
      if(exec_point == 0) exec_point = 0.001;

      // v3.25: M15 rescue — if M30 entry stop_pts is too_wide, try M15 closer entry
      // Python: build_rescued_trades() rescues too_wide signals via M15 closer entry
      double m30_sd = MathAbs(C - stop_price) / exec_point;
      if(m30_sd > InpStopHi && InpUseM15EarlyEntry)
      {
         // Try M15 slot1 close as closer entry (Python choose_any: scan M15 bars)
         double m15_close_arr[1];
         if(CopyClose(InpSymbol, InpM15Period, 1, 1, m15_close_arr) > 0)
         {
            double m15_close = m15_close_arr[0];
            double m15_sd = MathAbs(m15_close - stop_price) / exec_point;
            if(m15_sd >= InpStopLo && m15_sd <= InpStopHi)
            {
               // Check M15 same side (LONG: close > sma13, SHORT: close < sma13)
               double m15_sma13_arr[1];
               double m15_sma13 = 0;
               if(CopyBuffer(g_ma_slow_m15, 0, 1, 1, m15_sma13_arr) > 0)
                  m15_sma13 = m15_sma13_arr[0];
               bool same_side = (signal_dir == +1 && m15_close > m15_sma13) ||
                                (signal_dir == -1 && m15_close < m15_sma13);
               if(same_side && m15_sma13 > 0)
               {
                  DiagLog("[M30 CLOSE]", "Rescue",
                          "mode=" + signal_src +
                          " m30_sd=" + DoubleToString(m30_sd/1000.0, 3) +
                          " m15_sd=" + DoubleToString(m15_sd/1000.0, 3) +
                          " m15_close=" + DoubleToString(m15_close, 5) +
                          " result=RESCUED");
                  ExecuteSignalByMarket(signal_dir, signal_src + "_rescue",
                                        stop_price, cur_bar, "[M15 RESCUE]");
                  return;
               }
            }
         }
         DiagLog("[M30 CLOSE]", "Rescue",
                 "mode=" + signal_src +
                 " m30_sd=" + DoubleToString(m30_sd/1000.0, 3) +
                 " result=RESCUE_FAIL");
      }

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

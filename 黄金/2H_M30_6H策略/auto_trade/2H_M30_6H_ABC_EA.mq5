//+------------------------------------------------------------------+
//|                                  2H_M30_6H_ABC_EA.mq5           |
//|                                                         Codex    |
//|        2H_M30_6H A+B+C combined candidate (2026-08-15)           |
//|  Entry : pre_cross / cross / post_n(2-6), previous-segment SMA13 |
//|          extreme stops (post_n: current-bar SMA13), next-bar open|
//|  Gate  : 6H SMMA5 >0 AND 6H SMMA55 >0 (trade-direction signed)   |
//|  Exit  : 3-stage 2.0R / 1.5R trail + 4.0R / M30 merged cross     |
//|  Risk  : 1% balance, stage units 0.5/1.0/1.5, SimMode only       |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "=== Account ==="
input ulong   InpMagic      = 342036;      // Magic Number
input string  InpSymbol     = "XAUUSDm";   // Symbol

input group "=== Risk & Virtual Position ==="
input double  InpRiskPct    = 1.0;         // Risk % per trade (recommended 0.5-1.0)
input double  InpStopLoPt   = 5.0;         // Min stop distance (price units, spec 5pt)
input double  InpStopHiPt   = 35.0;        // Max stop distance (price units, spec 35pt)
input int     InpMaxOpenVirtual = 100;     // Max concurrent signals（按信号计，1信号=3笔仓；临时100=对齐Python无并发限制回测口径）
input double  InpMinLots    = 0.01;        // Min lot
input double  InpMaxLots    = 10.0;        // Max lot
input double  InpSimStartBalance = 500.0;  // Virtual start balance for SimMode

input group "=== Layer 2 (three opportunities) ==="
input double  InpPreCrossGapPct = 0.300;   // pre_cross: |SMMA5-SMMA13|/SMMA13 <= X%
input int     InpPostNMin    = 2;          // post_n start (inclusive)
input int     InpPostNMax    = 6;          // post_n end (inclusive)
input int     InpSameDirCdBars = 0;        // post_n 同向冷却（0=关闭，P1-2 默认关闭对齐回测口径）
input int     InpLossCdLoss   = 0;        // 损失冷却（0=关闭，P1-2 默认关闭对齐回测口径）
input int     InpLossCdHours  = 120;      // 损失冷却时长（小时）
input int     InpMergedMinLen = 8;         // merged segment min length (Python min_len)

input group "=== 6H Gate (bias5>0 AND bias55>0, trade-direction) ==="
input int     InpH6SMA5     = 5;           // 6H SMMA5
input int     InpH6SMA13    = 13;          // 6H SMMA13 (r13_55 结构带通用)
input int     InpH6SMA55    = 55;          // 6H SMMA55
input double  InpR13BandMinPct = 3.0;      // 结构带通下限: |H6 SMA13-SMA55|/SMA55*100 >= X%
input double  InpR13BandMaxPct = 5.0;      // 结构带通上限: <= X%
input int     InpM30SMA5    = 5;           // M30 SMMA5
input int     InpM30SMA13   = 13;          // M30 SMMA13
input int     InpM30SMA55   = 55;          // M30 SMMA55 (Nan-lun regression gate)
input bool    InpNanRegOn   = false;       // Nan-lun 55SMA regression gate (default OFF = baseline)
input double  InpNanRegPct  = 0.5;         // regression threshold % (close within X% of M30 55SMA)

input group "=== Split TP (three stages) ==="
input double  InpStage1R      = 2.0;       // Stage 1 TP in R
input double  InpStage2TrailR = 1.5;       // Stage 2 trail start in R
input double  InpStage2ForceR = 4.0;       // Stage 2 force close in R
input double  InpStage1Units  = 0.5;       // Stage 1 lot units
input double  InpStage2Units  = 1.0;       // Stage 2 lot units
input double  InpStage3Units  = 1.5;       // Stage 3 lot units

input group "=== Runtime ==="
input int     InpHistoryBars = 600;        // M30 bars to load
input bool    InpSimMode     = true;       // true=virtual only (SAFE)
input bool    InpAllowRealTrading = false; // must be true for real orders (guard)
input bool    InpExportCSV   = true;       // signals CSV
input bool    InpExportLedger = true;      // stage ledger CSV
input bool    InpVerboseDiag = true;       // verbose per-bar diagnostics
input group "=== Macro Calendar Filter (research, default OFF) ==="
input bool   InpEventFilterOn   = false;  // 事件过滤总开关（默认关，先模拟盘）
input int    InpEventFilterHrs  = 1;  // 高影响事件前 N 小时内不开新仓
input int    InpEventCheckEvery = 300;    // 日历查询缓存（秒）


//--- globals
string g_signals_csv  = "2H_M30_6H_abc_signals_export.csv";
string g_ledger_csv   = "2H_M30_6H_abc_trade_ledger.csv";
datetime g_last_bar   = 0;
int      g_bar_seq    = 0;
double   g_virtual_balance = 0.0;
CTrade   g_trade;
int      g_ledger_handle = INVALID_HANDLE;  // BUG-12: 台账句柄保持打开, 避免频繁 open/close 丢失写入

enum ENUM_SIGNAL { SIG_NONE = 0, SIG_PRE = 1, SIG_CROSS = 2, SIG_POST = 3 };

//--- pending signal (detected at last closed bar; opens at next bar open)
bool      g_pending = false;
datetime g_pending_signal_time = 0;
int      g_pending_dir = 0;
int      g_pending_mode = 0;
double   g_pending_stop = 0.0;
int      g_last_signal_dir = 0;   // 同向冷却：最近接受信号的方向
int      g_last_signal_seq = 0;   // 同向冷却：最近接受信号的 bar_seq
int      g_loss_streak = 0;       // 损失冷却：连续亏损信号组计数
datetime g_loss_cd_until = 0;     // 损失冷却截止时间
bool     g_ev_blackout   = false;   // 未来 N 小时内有高影响事件（日历门）
datetime g_ev_next_check = 0;       // 下次日历查询时刻


//--- virtual trade struct
struct VirtualTrade
{
   datetime signal_time;
   datetime entry_time;
   int      dir;             // +1 LONG, -1 SHORT
   int      mode;            // ENUM_SIGNAL
   int      open_seq;        // bar seq at entry (new bar when opened)
   double   entry;
   double   stop;
   double   r;               // stop distance in price
   bool     stage1_done;
   bool     stage2_done;
   bool     stage3_done;
   double   stage2_trail_sl;
   double   stage1_pnl;
   double   stage2_pnl;
   double   stage3_pnl;
   ulong    ticket_s1;     // real position ticket stage 1
   ulong    ticket_s2;     // real position ticket stage 2
   ulong    ticket_s3;     // real position ticket stage 3
};
VirtualTrade g_trades[];

//+------------------------------------------------------------------+
//| CSV helpers                                                      |
//+------------------------------------------------------------------+
int CsvHandle(string fname)
{
   return FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
}

void CsvSignalsHeader()
{
   int h = CsvHandle(g_signals_csv);
   if(h != INVALID_HANDLE)
   {
      FileWrite(h, "bar_time", "dir", "mode", "entry", "stop", "stop_distance", "gate_pass", "decision");
      FileClose(h);
   }
}

void CsvLedgerHeader()
{
   // BUG-05 修复: 实盘追加；BUG-11b: SimMode 下 FILE_WRITE 截断（每次回测清空，避免旧台账混合）
   int flags = InpSimMode ? (FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ)
                          : (FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ);
   g_ledger_handle = FileOpen(g_ledger_csv, flags, ',');
   if(g_ledger_handle != INVALID_HANDLE)
   {
      if(InpSimMode || FileSize(g_ledger_handle) == 0)
         FileWrite(g_ledger_handle, "signal_time", "entry_time", "dir", "mode", "stage", "open_time",
                   "entry", "stop", "exit_time", "exit_price", "reason", "pnl_points", "pnl_usd", "virtual_balance");
      else
         FileSeek(g_ledger_handle, 0, SEEK_END);
      FileFlush(g_ledger_handle);
      // 不关闭, 保持句柄供 RecordStageExit 复用 (BUG-12)
   }
}

//+------------------------------------------------------------------+
//| SMMA (mean-init), matches processing.smma.calc_smma               |
//+------------------------------------------------------------------+
bool CalcSmmaArray(const MqlRates &r[], int n, int period, double &out[])
{
   ArrayResize(out, n);
   for(int i = 0; i < n; i++) out[i] = 0.0;
   if(n < period) return false;
   double sum = 0.0;
   for(int i = 0; i < period; i++) sum += r[i].close;
   out[period - 1] = sum / period;
   for(int i = period; i < n; i++)
      out[i] = (r[i].close + (period - 1) * out[i - 1]) / period;
   return true;
}

//+------------------------------------------------------------------+
//| Raw direction codes: good=2, bad=-2, up=1, down=-1                |
//+------------------------------------------------------------------+
void BuildRawCodes(const double &fast[], const double &slow[], int n, int &codes[])
{
   ArrayResize(codes, n);
   if(n <= 0) return;
   bool prev_above = fast[0] > slow[0];
   codes[0] = prev_above ? 1 : -1;
   for(int i = 1; i < n; i++)
   {
      bool curr_above = fast[i] > slow[i];
      if(curr_above && !prev_above) codes[i] = 2;
      else if(!curr_above && prev_above) codes[i] = -2;
      else if(curr_above) codes[i] = 1;
      else codes[i] = -1;
      prev_above = curr_above;
   }
}

//+------------------------------------------------------------------+
//| Merged direction codes (chain absorption, min_len=InpMergedMinLen)|
//+------------------------------------------------------------------+
void BuildMergedCodes(const int &raw[], int n, int &merged[])
{
   // BUG-13: 对齐 Python filter_short_segments_causal(逐bar+stack, 吸收短段时只改当前穿越点, 不改 prev/段内)
   ArrayResize(merged, n);
   for(int i = 0; i < n; i++) merged[i] = raw[i];

   int stack[];
   ArrayResize(stack, n);
   int sc = 0;         // stack count
   int state = 0;      // 0 = None, +1 = up, -1 = down

   for(int i = 0; i < n; i++)
   {
      int d = raw[i];
      if(MathAbs(d) != 2) continue;
      if(state == 0)
         state = (d == 2) ? -1 : 1;
      if(sc > 0)
      {
         int prev = stack[sc - 1];
         int typ = raw[prev];
         int rc = 0;
         for(int k = prev + 1; k < i; k++)
         {
            if((typ == 2 && raw[k] == 1) || (typ == -2 && raw[k] == -1))
               rc++;
         }
         if(rc < InpMergedMinLen)
         {
            merged[i] = state;   // 只改当前穿越点
            sc--;                // pop prev
         }
         else
         {
            merged[i] = raw[i];
            state = (typ == 2) ? 1 : -1;
            sc--;                // pop prev
            stack[sc] = i;       // push i
            sc++;
         }
      }
      else
      {
         merged[i] = raw[i];
         stack[sc] = i;          // push i
         sc++;
      }
   }
}

//+------------------------------------------------------------------+
//| post_n counter from merged direction (matches Python)             |
//+------------------------------------------------------------------+
int MergedPostNValue(const int &merged[], int idx)
{
   int counter = 0;
   int last_cross = 0;
   for(int i = 0; i <= idx; i++)
   {
      int code = merged[i];
      if(code == 2) { counter = 1; last_cross = 1; }
      else if(code == -2) { counter = -1; last_cross = -1; }
      else if(code == 1 && last_cross == 1) counter++;
      else if(code == -1 && last_cross == -1) counter--;
      else { counter = 0; last_cross = 0; }
   }
   return counter;
}

//+------------------------------------------------------------------+
//| FindStopSMA: previous-segment SMA13 extreme (Python prior_segment)|
//+------------------------------------------------------------------+
double FindStopSma(const double &sma_f[], const double &sma_s[], int sig_idx, bool is_long)
{
   int k = -1;
   for(int i = sig_idx - 1; i >= 1; i--)
   {
      bool curr_above = sma_f[i] > sma_s[i];
      bool prev_above = sma_f[i - 1] > sma_s[i - 1];
      if(curr_above != prev_above) { k = i; break; }
   }
   if(k < 0) return 0.0;
   double extreme = 0.0;
   for(int i = k; i < sig_idx; i++)
   {
      if(sma_s[i] == 0.0 || !MathIsValidNumber(sma_s[i])) continue;
      if(is_long) extreme = (extreme == 0.0) ? sma_s[i] : MathMin(extreme, sma_s[i]);
      else        extreme = (extreme == 0.0) ? sma_s[i] : MathMax(extreme, sma_s[i]);
   }
   return extreme;
}

//+------------------------------------------------------------------+
//| 6H bias (signed in trade direction), last closed 6H bar           |
//+------------------------------------------------------------------+
double H6BiasPct(int period, int dir_sign)
{
   MqlRates h6[];
   int n = CopyRates(InpSymbol, PERIOD_H6, 0, 300, h6);
   if(n < period + 2) return EMPTY_VALUE;
   double sma[];
   if(!CalcSmmaArray(h6, n, period, sma)) return EMPTY_VALUE;
   int last_closed = n - 2;
   double close = h6[last_closed].close;
   double s = sma[last_closed];
   if(s == 0.0 || !MathIsValidNumber(s)) return EMPTY_VALUE;
   return (close - s) / s * 100.0 * dir_sign;
}

//+------------------------------------------------------------------+
//| 6H (SMA13-SMA55)/SMA55*100, signed in trade direction              |
//| (r13_55 结构带通, 2026-09-06 变体: LONG 3..5% / SHORT -5..-3%)      |
//+------------------------------------------------------------------+
double H6R13SMA55Pct(int dir_sign)
{
   MqlRates h6[];
   int n = CopyRates(InpSymbol, PERIOD_H6, 0, 300, h6);
   if(n < InpH6SMA55 + 2) return EMPTY_VALUE;
   double s13[], s55[];
   if(!CalcSmmaArray(h6, n, InpH6SMA13, s13)) return EMPTY_VALUE;
   if(!CalcSmmaArray(h6, n, InpH6SMA55, s55)) return EMPTY_VALUE;
   int last_closed = n - 2;
   double a = s13[last_closed];
   double b = s55[last_closed];
   if(b == 0.0 || !MathIsValidNumber(a) || !MathIsValidNumber(b)) return EMPTY_VALUE;
   return (a - b) / b * 100.0 * dir_sign;
}

//+------------------------------------------------------------------+
//| Gate: 6H bias5>0 AND bias55>0 (trade-direction)                   |
//|  + r13_55 结构带通: InpR13BandMinPct <= dir_sign*(SMA13-SMA55)/SMA55% <= Max |
//+------------------------------------------------------------------+
bool Pass6HGate(int dir_sign)
{
   double b5 = H6BiasPct(InpH6SMA5, dir_sign);
   double b55 = H6BiasPct(InpH6SMA55, dir_sign);
   if(!MathIsValidNumber(b5) || !MathIsValidNumber(b55)) return false;
   if(!(b5 > 0.0 && b55 > 0.0)) return false;
   double r13 = H6R13SMA55Pct(dir_sign);
   if(!MathIsValidNumber(r13)) return false;
   return (r13 >= InpR13BandMinPct && r13 <= InpR13BandMaxPct);
}

//+------------------------------------------------------------------+
//| Stage PnL recording (virtual)                                     |
//+------------------------------------------------------------------+
double ContractSize()
{
   return SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE);
}

double CalcUnitLot(double stop_price)
{
   double risk = g_virtual_balance * InpRiskPct / 100.0;
   double unit = risk / (3.0 * stop_price * ContractSize());
   if(unit < InpMinLots) unit = InpMinLots;
   if(unit > InpMaxLots) unit = InpMaxLots;
   return unit;
}

double CalcUnitLotReal(double stop_price)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = balance * InpRiskPct / 100.0;
   double unit = risk / (3.0 * stop_price * ContractSize());
   if(unit < InpMinLots) unit = InpMinLots;
   if(unit > InpMaxLots) unit = InpMaxLots;
   double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;
   unit = MathFloor(unit / step) * step;
   return MathMax(InpMinLots, unit);
}

double StageLot(double unit_lot, double units)
{
   return unit_lot * units;
}

string ModeText(int mode)
{
   if(mode == SIG_PRE) return "pre_cross";
   if(mode == SIG_CROSS) return "cross";
   if(mode == SIG_POST) return "post_n";
   return "none";
}

void RecordStageExit(int slot, int stage, datetime exit_time, double exit_price,
                     string reason, double pnl_points)
{
   if(!InpSimMode)
   {
      ulong t = (stage == 1 ? g_trades[slot].ticket_s1 :
                 (stage == 2 ? g_trades[slot].ticket_s2 : g_trades[slot].ticket_s3));
      if(t > 0)
      {
         if(PositionSelectByTicket(t))
         {
            if(!g_trade.PositionClose(t))
               Print("[REAL] stage ", stage, " CLOSE FAILED ticket=", t,
                     " retcode=", g_trade.ResultRetcode(), " comment=", g_trade.ResultRetcodeDescription());
            else
               Print("[REAL] stage ", stage, " CLOSE ticket=", t, " reason=", reason,
                     " px=", DoubleToString(exit_price, 5));
         }
         if(stage == 1) g_trades[slot].ticket_s1 = 0;
         else if(stage == 2) g_trades[slot].ticket_s2 = 0;
         else g_trades[slot].ticket_s3 = 0;
      }
   }
   double unit_lot = CalcUnitLot(g_trades[slot].r);
   double units = (stage == 1 ? InpStage1Units : (stage == 2 ? InpStage2Units : InpStage3Units));
   double lot = StageLot(unit_lot, units);
   double pnl_usd = lot * pnl_points * ContractSize();
   g_virtual_balance += pnl_usd;

   if(InpExportLedger)
   {
      if(g_ledger_handle != INVALID_HANDLE)
      {
         FileWrite(g_ledger_handle, TimeToString(g_trades[slot].signal_time), TimeToString(g_trades[slot].entry_time),
                   (g_trades[slot].dir > 0 ? "BUY" : "SELL"), ModeText(g_trades[slot].mode), stage,
                   TimeToString(g_trades[slot].entry_time), DoubleToString(g_trades[slot].entry, 5),
                   DoubleToString(g_trades[slot].stop, 5), TimeToString(exit_time),
                   DoubleToString(exit_price, 5), reason, DoubleToString(pnl_points, 5),
                   DoubleToString(pnl_usd, 5), DoubleToString(g_virtual_balance, 5));
         FileFlush(g_ledger_handle);
      }
   }

   if(InpVerboseDiag)
   {
      Print("[SIM] stage ", stage, " ", (g_trades[slot].dir > 0 ? "BUY" : "SELL"), " ",
            ModeText(g_trades[slot].mode), " exit=", TimeToString(exit_time), " px=",
            DoubleToString(exit_price, 5), " reason=", reason, " pnl_usd=",
            DoubleToString(pnl_usd, 5), " balance=", DoubleToString(g_virtual_balance, 5));
   }
}

//+------------------------------------------------------------------+
//| Process one closed bar for all open virtual trades                |
//+------------------------------------------------------------------+
void ProcessOpenTrades(const MqlRates &rates[], int n, const double &sma13[], const int &merged[])
{
   int closed_idx = n - 2;
   for(int s = 0; s < ArraySize(g_trades); s++)
   {
      if(g_trades[s].stage3_done) continue;
      // 修复(2026-09-04): 出场逐 bar 推进到最新已收盘 bar。
      // 原 idx=closed_idx-(age-1) 因 age 与 closed_idx 每 bar 同步 +1, idx 恒=开仓 bar,
      // 导致三段出场(SL/TP/trail/force/bound)永远只读开仓 bar、出场逻辑失效。
      int idx = closed_idx;
      if(idx < 0) { g_trades[s].stage3_done = true; continue; }
      MqlRates bar = rates[idx];
      bool is_long = g_trades[s].dir > 0;

      int merged_code = merged[idx];
      bool bound = false;
      if(is_long && merged_code < 0) bound = true;
      if(!is_long && merged_code > 0) bound = true;

      // ---- stage 1 (TP/SL only, no bound) ----
      if(!g_trades[s].stage1_done)
      {
         double target = g_trades[s].entry + (is_long ? InpStage1R * g_trades[s].r : -InpStage1R * g_trades[s].r);
         bool exit_now = false;
         double exit_px = 0.0; string reason = "";
         if(is_long)
         {
            if(bar.low <= g_trades[s].stop) { exit_px = g_trades[s].stop; reason = "SL hit"; g_trades[s].stage1_pnl = -g_trades[s].r; exit_now = true; }
            else if(bar.high >= target) { exit_px = target; reason = "2.0R TP"; g_trades[s].stage1_pnl = InpStage1R * g_trades[s].r; exit_now = true; }
         }
         else
         {
            if(bar.high >= g_trades[s].stop) { exit_px = g_trades[s].stop; reason = "SL hit"; g_trades[s].stage1_pnl = -g_trades[s].r; exit_now = true; }
            else if(bar.low <= target) { exit_px = target; reason = "2.0R TP"; g_trades[s].stage1_pnl = InpStage1R * g_trades[s].r; exit_now = true; }
         }
         if(exit_now)
         {
            RecordStageExit(s, 1, bar.time, exit_px, reason, g_trades[s].stage1_pnl);
            g_trades[s].stage1_done = true;
         }
      }

      // ---- stage 2 ----
      if(!g_trades[s].stage2_done)
      {
         double force = g_trades[s].entry + (is_long ? InpStage2ForceR * g_trades[s].r : -InpStage2ForceR * g_trades[s].r);
         double trail_start = g_trades[s].entry + (is_long ? InpStage2TrailR * g_trades[s].r : -InpStage2TrailR * g_trades[s].r);
         bool exit_now = false; double exit_px = 0.0; string reason = "";
         if(is_long)
         {
            if(bar.high >= force) { exit_px = force; reason = "4.0R forced"; g_trades[s].stage2_pnl = InpStage2ForceR * g_trades[s].r; exit_now = true; }
            else if(bar.low <= g_trades[s].stage2_trail_sl) { exit_px = g_trades[s].stage2_trail_sl; reason = "trail/SL hit"; g_trades[s].stage2_pnl = g_trades[s].stage2_trail_sl - g_trades[s].entry; exit_now = true; }
            else if(bar.high >= trail_start && sma13[idx] > g_trades[s].stage2_trail_sl) g_trades[s].stage2_trail_sl = sma13[idx];
         }
         else
         {
            if(bar.low <= force) { exit_px = force; reason = "4.0R forced"; g_trades[s].stage2_pnl = InpStage2ForceR * g_trades[s].r; exit_now = true; }
            else if(bar.high >= g_trades[s].stage2_trail_sl) { exit_px = g_trades[s].stage2_trail_sl; reason = "trail/SL hit"; g_trades[s].stage2_pnl = g_trades[s].entry - g_trades[s].stage2_trail_sl; exit_now = true; }
            else if(bar.low <= trail_start && (sma13[idx] < g_trades[s].stage2_trail_sl || g_trades[s].stage2_trail_sl == g_trades[s].stop))
               g_trades[s].stage2_trail_sl = sma13[idx];
         }
         if(bound && !exit_now)
         {
            exit_px = bar.close; reason = "M30 merged cross"; g_trades[s].stage2_pnl = (is_long ? exit_px - g_trades[s].entry : g_trades[s].entry - exit_px); exit_now = true;
         }
         if(exit_now)
         {
            RecordStageExit(s, 2, bar.time, exit_px, reason, g_trades[s].stage2_pnl);
            g_trades[s].stage2_done = true;
         }
      }

      // ---- stage 3 ----
      if(!g_trades[s].stage3_done)
      {
         bool exit_now = false; double exit_px = 0.0; string reason = "";
         if(is_long && bar.low <= g_trades[s].stop) { exit_px = g_trades[s].stop; reason = "SL hit"; g_trades[s].stage3_pnl = -g_trades[s].r; exit_now = true; }
         if(!is_long && bar.high >= g_trades[s].stop) { exit_px = g_trades[s].stop; reason = "SL hit"; g_trades[s].stage3_pnl = -g_trades[s].r; exit_now = true; }
         if(bound && !exit_now)
         {
            exit_px = bar.close; reason = "M30 merged cross"; g_trades[s].stage3_pnl = (is_long ? exit_px - g_trades[s].entry : g_trades[s].entry - exit_px); exit_now = true;
         }
         if(exit_now)
         {
            RecordStageExit(s, 3, bar.time, exit_px, reason, g_trades[s].stage3_pnl);
            g_trades[s].stage3_done = true;
         }
      }
   }

   // remove closed trades + 损失冷却组计数（组=1信号×3段，加权盈亏<0 计一次亏损）
   int w = 0;
   for(int s = 0; s < ArraySize(g_trades); s++)
   {
      if(!g_trades[s].stage3_done)
      {
         if(w != s) g_trades[w] = g_trades[s];
         w++;
      }
      else
      {
         double gp = g_trades[s].stage1_pnl * InpStage1Units
                   + g_trades[s].stage2_pnl * InpStage2Units
                   + g_trades[s].stage3_pnl * InpStage3Units;
         if(gp < 0.0)
         {
            g_loss_streak++;
            if(InpLossCdLoss > 0 && g_loss_streak >= InpLossCdLoss)
            {
               g_loss_cd_until = TimeCurrent() + InpLossCdHours * 3600;
               if(InpVerboseDiag)
                  Print("[CD] loss cooldown ", InpLossCdHours, "h after ", g_loss_streak,
                        " consecutive losing groups gp=", DoubleToString(gp, 2));
            }
         }
         else
            g_loss_streak = 0;
      }
   }
   ArrayResize(g_trades, w);
}

//+------------------------------------------------------------------+
//| Detect signal on bar idx (closed)                                 |
//+------------------------------------------------------------------+
bool DetectSignal(const MqlRates &rates[], int n, const double &sma5[], const double &sma13[],
                  const int &raw[], const int &merged[], int idx, int &dir, int &mode, double &stop)
{
   int pn = MergedPostNValue(merged, idx);
   // cross first (BUG-15: Python cross 检测用 raw 方向, 非 merged)
   if(MathAbs(raw[idx]) == 2)
   {
      bool is_long = raw[idx] == 2;
      double sl = FindStopSma(sma5, sma13, idx, is_long);
      if(sl != 0.0)
      {
         dir = is_long ? 1 : -1; mode = SIG_CROSS; stop = sl; return true;
      }
   }
   // pre_cross (raw != cross 后检测, 对齐 Python)
   if(MathAbs(raw[idx]) != 2 && idx >= 1)
   {
      double gap = MathAbs(sma5[idx] - sma13[idx]) / sma13[idx];
      bool long_setup = (rates[idx - 1].close <= sma13[idx - 1]) && (rates[idx].close > sma13[idx]) && (sma5[idx] < sma13[idx]);
      bool short_setup = (rates[idx - 1].close >= sma13[idx - 1]) && (rates[idx].close < sma13[idx]) && (sma5[idx] > sma13[idx]);
      if(gap <= InpPreCrossGapPct / 100.0 && (long_setup || short_setup))
      {
         bool is_long = long_setup;
         double sl = FindStopSma(sma5, sma13, idx, is_long);
         if(sl != 0.0)
         {
            dir = is_long ? 1 : -1; mode = SIG_PRE; stop = sl; return true;
         }
      }
   }
   // post_n
   if(MathAbs(pn) >= InpPostNMin && MathAbs(pn) <= InpPostNMax)
   {
      bool is_long = pn > 0;
      double sl = sma13[idx];
      if(sl != 0.0)
      {
         dir = is_long ? 1 : -1; mode = SIG_POST; stop = sl; return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Restore real positions after EA reload (chart period switch etc.)|
//| Remaining N stage positions map to stages (4-N)..3 by open time.  |
//+------------------------------------------------------------------+
void RestoreRealPositions()
{
   if(InpSimMode) return;
   int total = PositionsTotal();
   int n = 0;
   for(int i = total - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(!PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      n++;
   }
   if(n == 0) return;
   if(n > 3) n = 3;
   ulong tickets[3] = {0, 0, 0};
   double entries[3] = {0, 0, 0};
   double stops[3] = {0, 0, 0};
   int    dirs[3] = {0, 0, 0};
   datetime times[3] = {0, 0, 0};
   for(int pick = 0; pick < n; pick++)
   {
      datetime best = 0;
      ulong best_t = 0;
      for(int i = total - 1; i >= 0; i--)
      {
         ulong t = PositionGetTicket(i);
         if(t == 0) continue;
         if(!PositionSelectByTicket(t)) continue;
         if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
         if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
         bool used = false;
         for(int k = 0; k < pick; k++) if(tickets[k] == t) { used = true; break; }
         if(used) continue;
         datetime tm = (datetime)PositionGetInteger(POSITION_TIME);
         if(best_t == 0 || tm < best) { best = tm; best_t = t; }
      }
      if(best_t == 0) break;
      PositionSelectByTicket(best_t);
      tickets[pick] = best_t;
      times[pick] = (datetime)PositionGetInteger(POSITION_TIME);
      entries[pick] = PositionGetDouble(POSITION_PRICE_OPEN);
      stops[pick] = PositionGetDouble(POSITION_SL);
      dirs[pick] = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
   }
   int first_stage = 4 - n;
   for(int j = 0; j < n; j++)
   {
      int stage = first_stage + j;
      int s = ArraySize(g_trades);
      ArrayResize(g_trades, s + 1);
      g_trades[s].signal_time = times[j];
      g_trades[s].entry_time = times[j];
      g_trades[s].dir = dirs[j];
      g_trades[s].mode = SIG_CROSS;
      g_trades[s].open_seq = 0;
      g_trades[s].entry = entries[j];
      g_trades[s].stop = stops[j];
      g_trades[s].r = MathAbs(entries[j] - stops[j]);
      g_trades[s].stage1_done = (stage > 1);
      g_trades[s].stage2_done = (stage > 2);
      g_trades[s].stage3_done = (stage > 3);
      g_trades[s].stage2_trail_sl = stops[j];
      g_trades[s].stage1_pnl = 0.0; g_trades[s].stage2_pnl = 0.0; g_trades[s].stage3_pnl = 0.0;
      g_trades[s].ticket_s1 = (stage == 1 ? tickets[j] : 0);
      g_trades[s].ticket_s2 = (stage == 2 ? tickets[j] : 0);
      g_trades[s].ticket_s3 = (stage == 3 ? tickets[j] : 0);
      Print("[REAL] RESTORED stage=", stage, " ticket=", tickets[j],
            " dir=", (dirs[j] > 0 ? "BUY" : "SELL"),
            " entry=", DoubleToString(entries[j], 5),
            " stop=", DoubleToString(stops[j], 5));
   }
}

//+------------------------------------------------------------------+
//| 损失冷却判定（连续 InpLossCdLoss 个亏损信号组后暂停开仓）          |
//+------------------------------------------------------------------+
bool InLossCooldown()
{
   if(InpLossCdLoss <= 0 || g_loss_cd_until == 0) return false;
   return TimeCurrent() < g_loss_cd_until;
}

//| OnInit / OnDeinit / OnTick                                        |
//+------------------------------------------------------------------+

//| Macro Calendar Event Gate (research, default OFF)                 |

//| 币种白名单（策略定义）：USD=直接计价 / EUR+GBP=USDX权重70% / CAD=油价货币 |
bool IsWhitelistedCurrency(const long country_id)
{
   MqlCalendarCountry ctry;
   if(!CalendarCountryById(country_id, ctry)) return false;
   return (ctry.currency == "USD" || ctry.currency == "EUR" ||
           ctry.currency == "GBP" || ctry.currency == "CAD");
}

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
      if(CalendarEventById(vals[i].event_id, ev) && ev.importance >= 3
         && IsWhitelistedCurrency(ev.country_id))
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

int OnInit()
{
   g_virtual_balance = InpSimStartBalance;
   g_last_bar = 0;
   g_bar_seq = 0;
   g_pending = false;
   g_last_signal_dir = 0;
   g_last_signal_seq = 0;
   g_loss_streak = 0;
   g_loss_cd_until = 0;
   ArrayResize(g_trades, 0);
   // BUGFIX(2026-09-09): CTrade had no expert magic, so PositionClose() sent magic=0
   // -> close deals unattributable. 实测（问题记录 §二十三③④，position_id 血缘还原）：
   // 本 EA 有 3 笔平仓 deal magic 落 0（08-21 21:46 +71.39 / 08-24 22:14 +150.67 /
   // 08-25 19:53 +125.73），致按 deal.magic 统计本策略为 -279.62，而血缘还原后为 +68.17。
   // Same fix as 1H_M30_4H_ABC_EA(2026-09-02) / 30m2H_Strategy_EA v3.35 Fix 3.
   // Opens set req.magic explicitly; this makes ALL orders carry InpMagic.
   g_trade.SetExpertMagicNumber(InpMagic);
   if(InpExportCSV) CsvSignalsHeader();
   if(InpExportLedger) CsvLedgerHeader();
   Print("2H_M30_6H ABC EA initialized. SimMode=", InpSimMode,
         " AllowRealTrading=", InpAllowRealTrading,
         " Magic=", InpMagic, " VirtualBalance=", DoubleToString(g_virtual_balance, 5));
   RestoreRealPositions();
   EventSetTimer(60);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_ledger_handle != INVALID_HANDLE)
   {
      FileFlush(g_ledger_handle);
      FileClose(g_ledger_handle);
      g_ledger_handle = INVALID_HANDLE;
   }
}

void OnTick()
{
   if(!InpSimMode && !InpAllowRealTrading) return; // double guard: sim-only

   datetime bar0_time = iTime(InpSymbol, PERIOD_M30, 0);
   if(bar0_time <= 0) return;
   if(bar0_time == g_last_bar) return;
   g_last_bar = bar0_time;
   g_bar_seq++;

   MqlRates rates[];
   int n = CopyRates(InpSymbol, PERIOD_M30, 0, InpHistoryBars, rates);
   if(n < 80) return;

   double sma5[], sma13[];
   if(!CalcSmmaArray(rates, n, InpM30SMA5, sma5)) return;
   if(!CalcSmmaArray(rates, n, InpM30SMA13, sma13)) return;
   double sma55[];
   if(InpNanRegOn && !CalcSmmaArray(rates, n, InpM30SMA55, sma55)) return;
   int raw_codes[], merged[];
   int completed = n - 1;  // P2-2 (2026-09-06 复测): 排除 forming bar, 对齐 30m2H/1H 因果口径
   BuildRawCodes(sma5, sma13, completed, raw_codes);
   BuildMergedCodes(raw_codes, completed, merged);


   // 1) process open trades on the just-closed bar
   ProcessOpenTrades(rates, n, sma13, merged);

   // 2) detect signal on the just-closed bar
   int sig_idx = n - 2;
   int dir = 0, mode = 0; double stop = 0.0;
   bool hit = DetectSignal(rates, n, sma5, sma13, raw_codes, merged, sig_idx, dir, mode, stop);
   bool gate_pass = false;
   bool reg_ok = true;
   if(hit && InpNanRegOn)
   {
      // Nan-lun: 盘整第三段起点在 55SMA 附近 — 信号 bar 收盘价回归 M30 55SMA ±InpNanRegPct% 以内
      double s55 = sma55[sig_idx];
      if(s55 == 0.0 || !MathIsValidNumber(s55))
         reg_ok = false;   // 55SMA 预热期无值 -> 拒绝 (与 Python attach_reg55 的 NaN 过滤一致)
      else
      {
         double reg_pct = MathAbs(rates[sig_idx].close - s55) / s55 * 100.0;
         reg_ok = reg_pct < InpNanRegPct;
      }
   }
   if(hit && Pass6HGate(dir) && reg_ok)
   {
      gate_pass = true;
      double entry_next = iOpen(InpSymbol, PERIOD_M30, 0);
      double r = MathAbs(entry_next - stop);
      double stop_pts = r / _Point;
      double spec_lo = InpStopLoPt / _Point;
      double spec_hi = InpStopHiPt / _Point;
      bool cd_ok = true;
      if(InpSameDirCdBars > 0 && mode == SIG_POST && dir == g_last_signal_dir &&
         g_bar_seq - g_last_signal_seq < InpSameDirCdBars)
         cd_ok = false;
      if(EventBlackout() && InpVerboseDiag)
         Print("[CAL] signal blocked by event gate (next high-impact event within ", InpEventFilterHrs, "h)");
      // BUG-13 调试: 输出每个 gate PASS 信号的 stop_pts/spec/cd_ok/ev, 定位 223 个"CSV spec通过但无SIGNAL"差异
      if(InpVerboseDiag)
         Print("[GATEDBG] ", (dir > 0 ? "BUY" : "SELL"), " ", ModeText(mode),
               " sig=", TimeToString(rates[sig_idx].time),
               " entry_next=", DoubleToString(entry_next, 5),
               " stop=", DoubleToString(stop, 5),
               " stop_pts=", DoubleToString(stop_pts, 2),
               " spec=", DoubleToString(spec_lo, 2), "..", DoubleToString(spec_hi, 2),
               " cd_ok=", cd_ok, " ev=", EventBlackout());
      if(stop_pts >= spec_lo && stop_pts <= spec_hi && cd_ok && !EventBlackout())
      {
         g_pending = true;
         g_pending_signal_time = rates[sig_idx].time;
         g_pending_dir = dir;
         g_pending_mode = mode;
         g_pending_stop = stop;
         g_last_signal_dir = dir;
         g_last_signal_seq = g_bar_seq;
         if(InpVerboseDiag)
            Print("[SIGNAL] ", (dir > 0 ? "BUY" : "SELL"), " ", ModeText(mode),
                  " signal_time=", TimeToString(rates[sig_idx].time),
                  " stop=", DoubleToString(stop, 5), " stop_pts=", DoubleToString(stop_pts, 2),
                  " -> open at current bar open");  // P2-5 修正文案
      }
   }

   // 3) open pending signal at current bar open (P2-5: 移到信号检测后, 当前bar开盘立即入场, 不晚1bar)
   if(g_pending)
   {
      double entry = iOpen(InpSymbol, PERIOD_M30, 0);
      double r = MathAbs(entry - g_pending_stop);
      double stop_pts = r / _Point;
      double spec_lo = InpStopLoPt / _Point;
      double spec_hi = InpStopHiPt / _Point;
      if(stop_pts >= spec_lo && stop_pts <= spec_hi && ArraySize(g_trades) < InpMaxOpenVirtual
         && !InLossCooldown())
      {
         int s = ArraySize(g_trades);
         ArrayResize(g_trades, s + 1);
         g_trades[s].signal_time = g_pending_signal_time;
         g_trades[s].entry_time = bar0_time;
         g_trades[s].dir = g_pending_dir;
         g_trades[s].mode = g_pending_mode;
         g_trades[s].open_seq = g_bar_seq;
         g_trades[s].entry = entry;
         g_trades[s].stop = g_pending_stop;
         g_trades[s].r = r;
         g_trades[s].stage1_done = false;
         g_trades[s].stage2_done = false;
         g_trades[s].stage3_done = false;
         g_trades[s].stage2_trail_sl = g_trades[s].stop;
         g_trades[s].stage1_pnl = 0.0; g_trades[s].stage2_pnl = 0.0; g_trades[s].stage3_pnl = 0.0;
         g_trades[s].ticket_s1 = 0; g_trades[s].ticket_s2 = 0; g_trades[s].ticket_s3 = 0;
         if(!InpSimMode)
         {
            double unit_lot = CalcUnitLotReal(r);
            MqlTradeRequest req = {};
            MqlTradeResult  res = {};
            req.action       = TRADE_ACTION_DEAL;
            req.symbol       = InpSymbol;
            req.magic        = InpMagic;
            req.deviation    = 30;
            req.type_filling = ORDER_FILLING_FOK;
            req.sl           = g_pending_stop;
            req.tp           = 0;
            req.price        = (g_pending_dir > 0) ? SymbolInfoDouble(InpSymbol, SYMBOL_ASK)
                                                   : SymbolInfoDouble(InpSymbol, SYMBOL_BID);
            req.type         = (g_pending_dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
            double unit_lots[3] = {InpStage1Units, InpStage2Units, InpStage3Units};
            ulong tickets[3] = {0, 0, 0};
            for(int st = 0; st < 3; st++)
            {
               double stage_lot = unit_lot * unit_lots[st];
               double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
               if(step <= 0.0) step = 0.01;
               stage_lot = MathFloor(stage_lot / step) * step;
               if(stage_lot < InpMinLots) stage_lot = InpMinLots;
               if(stage_lot > InpMaxLots) stage_lot = InpMaxLots;
               req.volume = stage_lot;
               // 开仓即挂服务器止盈: stage1=InpStage1R, stage2=InpStage2ForceR, stage3 无 TP
               double r_abs = MathAbs(req.price - req.sl);
               if(st == 0)
                  req.tp = (g_pending_dir > 0) ? req.price + r_abs * InpStage1R
                                               : req.price - r_abs * InpStage1R;
               else if(st == 1)
                  req.tp = (g_pending_dir > 0) ? req.price + r_abs * InpStage2ForceR
                                               : req.price - r_abs * InpStage2ForceR;
               else
                  req.tp = 0.0;
               if(g_trade.OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
                  tickets[st] = res.order;
               else
                  Print("[REAL] stage ", st + 1, " OPEN FAILED retcode=", res.retcode,
                        " comment=", res.comment);
            }
            g_trades[s].ticket_s1 = tickets[0];
            g_trades[s].ticket_s2 = tickets[1];
            g_trades[s].ticket_s3 = tickets[2];
            if(tickets[0] || tickets[1] || tickets[2])
               Print("[REAL] OPEN ", (g_pending_dir > 0 ? "BUY" : "SELL"), " ",
                     ModeText(g_pending_mode), " tickets=", tickets[0], "/", tickets[1], "/", tickets[2],
                     " unit_lot=", DoubleToString(unit_lot, 2));
         }
         if(InpVerboseDiag)
            Print("[SIM] OPEN ", (g_trades[s].dir > 0 ? "BUY" : "SELL"), " ", ModeText(g_trades[s].mode),
                  " entry=", DoubleToString(entry, 5), " stop=", DoubleToString(g_trades[s].stop, 5),
                  " stop_pts=", DoubleToString(r / _Point, 2));
      }
      g_pending = false;
   }
   if(InpExportCSV)
   {
      int h = FileOpen(g_signals_csv, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
      if(h != INVALID_HANDLE)
      {
         FileSeek(h, 0, SEEK_END);
         double next_open = iOpen(InpSymbol, PERIOD_M30, 0);
         FileWrite(h, TimeToString(rates[sig_idx].time),
                   (dir > 0 ? "BUY" : (dir < 0 ? "SELL" : "NONE")),
                   ModeText(mode), DoubleToString(next_open, 5),
                   DoubleToString(stop, 5), DoubleToString(MathAbs(next_open - stop) / _Point, 2),
                   (gate_pass ? "PASS" : "FAIL"), (g_pending ? "ENTRY_PENDING" : "SKIP"));
         FileClose(h);
      }
   }
}
//+------------------------------------------------------------------+

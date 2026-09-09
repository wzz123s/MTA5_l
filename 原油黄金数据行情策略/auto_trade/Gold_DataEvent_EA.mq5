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
input ulong   InpMagic      = 411101;      // Magic Number (gold data-event)
input string  InpSymbol     = "XAUUSDm";   // Symbol

input group "=== Risk & Virtual Position ==="
input double  InpRiskPct    = 1.0;         // Risk % per trade (recommended 0.5-1.0)
input double  InpStopLoPt   = 5.0;         // Min stop distance (price units, spec 5pt)
input double  InpStopHiPt   = 35.0;        // Max stop distance (price units, spec 35pt)
input int     InpMaxOpenVirtual = 3;       // Max concurrent signals（按信号计，1信号=3笔仓；设1=同时最多1个信号）
input double  InpMinLots    = 0.01;        // Min lot
input double  InpMaxLots    = 10.0;        // Max lot
input double  InpSimStartBalance = 500.0;  // Virtual start balance for SimMode

input group "=== Layer 2 (three opportunities) ==="
input double  InpPreCrossGapPct = 0.300;   // pre_cross: |SMMA5-SMMA13|/SMMA13 <= X%
input int     InpPostNMin    = 2;          // post_n start (inclusive)
input int     InpPostNMax    = 6;          // post_n end (inclusive)
input int     InpSameDirCdBars = 3;        // post_n 同向冷却（M30 bar，0=关闭）防追势连开
input int     InpLossCdLoss   = 2;        // 损失冷却：连续亏损信号组达到该次数后暂停开仓（0=关闭）
input int     InpLossCdHours  = 120;      // 损失冷却时长（小时）
input int     InpMergedMinLen = 8;         // merged segment min length (Python min_len)

input group "=== 6H Gate (bias5>0 AND bias55>0, trade-direction) ==="
input int     InpH6SMA5     = 5;           // 6H SMMA5
input int     InpH6SMA55    = 55;          // 6H SMMA55
input int     InpM30SMA5    = 5;           // M30 SMMA5
input int     InpM30SMA13   = 13;          // M30 SMMA13

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
input bool   InpEventFilterOn   = true;   // 事件过滤总开关（M3 验证：V1_T2h PF 1.753）
input int    InpEventFilterHrs  = 2;  // 高影响事件前 N 小时内不开新仓（M3: V1_T2h）
input int    InpEventCheckEvery = 300;    // 日历查询缓存（秒）


//--- globals
string g_signals_csv  = "Gold_DataEvent_signals_export.csv";
string g_ledger_csv   = "Gold_DataEvent_trade_ledger.csv";
string g_gate_csv    = "Gold_DataEvent_gate_state.csv";
datetime g_last_bar   = 0;
int      g_bar_seq    = 0;
double   g_virtual_balance = 0.0;
CTrade   g_trade;

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
   // BUG-05 修复: 追加模式（FILE_READ|FILE_WRITE 不截断），仅空文件写表头
   int h = FileOpen(g_ledger_csv, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
   if(h != INVALID_HANDLE)
   {
      if(FileSize(h) == 0)
         FileWrite(h, "signal_time", "entry_time", "dir", "mode", "stage", "open_time",
                   "entry", "stop", "exit_time", "exit_price", "reason", "pnl_points", "pnl_usd", "virtual_balance");
      else
         FileSeek(h, 0, SEEK_END);
      FileClose(h);
   }
}

void CsvGateHeader()
{
   int h = CsvHandle(g_gate_csv);
   if(h != INVALID_HANDLE)
   {
      FileWrite(h, "check_time", "blackout", "event_name", "event_time", "importance", "currency");
      FileClose(h);
   }
}

void CsvGateState(const datetime now, const int blackout, const string ev_name,
                  const datetime ev_time, const int imp, const string cur)
{
   int h = FileOpen(g_gate_csv, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
   if(h != INVALID_HANDLE)
   {
      FileSeek(h, 0, SEEK_END);
      FileWrite(h, TimeToString(now), blackout,
                (ev_name == "" ? "-" : ev_name), TimeToString(ev_time), imp, cur);
      FileClose(h);
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
   ArrayResize(merged, n);
   for(int i = 0; i < n; i++) merged[i] = raw[i];

   int crossings[];
   int cross_types[];
   int cross_count = 0;
   ArrayResize(crossings, n);
   ArrayResize(cross_types, n);
   for(int i = 0; i < n; i++)
   {
      if(MathAbs(raw[i]) == 2)
      {
         crossings[cross_count] = i;
         cross_types[cross_count] = raw[i];
         cross_count++;
      }
   }
   if(cross_count == 0) return;

   int state = (cross_types[0] == 2) ? -1 : 1;
   int i = 0;
   while(i < cross_count)
   {
      int pos = crossings[i];
      int type_ = cross_types[i];
      if(i + 1 >= cross_count) break;
      int next_pos = crossings[i + 1];
      int region_count = 0;
      for(int k = pos + 1; k < next_pos; k++)
      {
         if(type_ == 2 && raw[k] == 1) region_count++;
         if(type_ == -2 && raw[k] == -1) region_count++;
      }
      if(region_count < InpMergedMinLen)
      {
         merged[pos] = state;
         for(int k = pos + 1; k < next_pos; k++) merged[k] = state;
         merged[next_pos] = state;
         for(int s = i + 2; s < cross_count; s++)
         {
            crossings[s - 2] = crossings[s];
            cross_types[s - 2] = cross_types[s];
         }
         cross_count -= 2;
         if(cross_count <= 0) break;
         continue;
      }
      state = (type_ == 2) ? 1 : -1;
      i++;
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
//| Gate: 6H bias5>0 AND bias55>0 (trade-direction)                   |
//+------------------------------------------------------------------+
bool Pass6HGate(int dir_sign)
{
   double b5 = H6BiasPct(InpH6SMA5, dir_sign);
   double b55 = H6BiasPct(InpH6SMA55, dir_sign);
   if(!MathIsValidNumber(b5) || !MathIsValidNumber(b55)) return false;
   return b5 > 0.0 && b55 > 0.0;
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
      int h = FileOpen(g_ledger_csv, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
      if(h != INVALID_HANDLE)
      {
         FileSeek(h, 0, SEEK_END);
         FileWrite(h, TimeToString(g_trades[slot].signal_time), TimeToString(g_trades[slot].entry_time),
                   (g_trades[slot].dir > 0 ? "BUY" : "SELL"), ModeText(g_trades[slot].mode), stage,
                   TimeToString(g_trades[slot].entry_time), DoubleToString(g_trades[slot].entry, 5),
                   DoubleToString(g_trades[slot].stop, 5), TimeToString(exit_time),
                   DoubleToString(exit_price, 5), reason, DoubleToString(pnl_points, 5),
                   DoubleToString(pnl_usd, 5), DoubleToString(g_virtual_balance, 5));
         FileClose(h);
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
      int age = g_bar_seq - g_trades[s].open_seq;
      int idx = closed_idx - (age - 1);
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
                  const int &merged[], int idx, int &dir, int &mode, double &stop)
{
   int pn = MergedPostNValue(merged, idx);
   // pre_cross first (priority over post_n; cross is disjoint)
   if(MathAbs(merged[idx]) != 2 && idx >= 1)
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
   // cross
   if(MathAbs(merged[idx]) == 2)
   {
      bool is_long = merged[idx] == 2;
      double sl = FindStopSma(sma5, sma13, idx, is_long);
      if(sl != 0.0)
      {
         dir = is_long ? 1 : -1; mode = SIG_CROSS; stop = sl; return true;
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
      CsvGateState(now, -1, "CalendarValueHistory error", 0, GetLastError(), "-");
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
         MqlCalendarCountry ctry2;
         string cur = "-";
         if(CalendarCountryById(ev.country_id, ctry2)) cur = ctry2.currency;
         if(InpVerboseDiag)
            Print("[CAL] event blackout: ", ev.name, " @ ", TimeToString(vals[i].time));
         CsvGateState(now, 1, ev.name, vals[i].time, ev.importance, cur);
         break;
      }
   }
   if(!g_ev_blackout)
      CsvGateState(now, 0, "-", 0, 0, "-");
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
   if(InpExportCSV) CsvSignalsHeader();
   if(InpExportLedger) CsvLedgerHeader();
   if(InpEventFilterOn) CsvGateHeader();
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
   int raw_codes[], merged[];
   BuildRawCodes(sma5, sma13, n, raw_codes);
   BuildMergedCodes(raw_codes, n, merged);

   // 1) open pending signal at current bar open
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

   // 2) process open trades on the just-closed bar
   ProcessOpenTrades(rates, n, sma13, merged);

   // 3) detect signal on the just-closed bar
   int sig_idx = n - 2;
   int dir = 0, mode = 0; double stop = 0.0;
   bool hit = DetectSignal(rates, n, sma5, sma13, merged, sig_idx, dir, mode, stop);
   bool gate_pass = false;
   if(hit && Pass6HGate(dir))
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
                  " -> pending next bar open");
      }
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

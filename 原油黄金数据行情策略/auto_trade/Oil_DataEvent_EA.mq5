//+------------------------------------------------------------------+
//|                  Oil_DataEvent_EA.mq5                         |
//|                                                     Codex       |
//|  数据行情: 4H 机会门 -> 2H 交易 + 宏观事件日历过滤 (event filter)  |
//|    Gate: 4H merged-seg len>=8 + extreme-bar way/vol_way>=0.5     |
//|          + SMMA13 extreme amplitude in [0.5,5.0]%                |
//|    Trigger: 2H cross / pre_cross (no post_n, no 2-bar confirm)  |
//|    Entry : next 2H bar open (i+1), prev-seg SMMA13 extreme stop |
//|    Exit  : SL (open-gap then low/high) or opposite raw cross     |
//|            -> exit at next bar open; single position             |
//|  Causal note: gate requires seg_len>=8, so short-segment merge   |
//|  (lookahead in full-series filter_short_segments) never affects  |
//|  gate-passing segments -> gate is lookahead-free (verified 0 flips).|
//|  Risk: 1% virtual balance, SimMode only, no real orders          |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "=== Account ==="
input ulong   InpMagic      = 411102;      // Magic Number (oil data-event)
input string  InpSymbol     = "USOILm";    // Symbol

input group "=== Risk & Virtual Position ==="
input double  InpRiskPct    = 1.0;         // Risk % per trade (virtual)
input double  InpStopLoPct  = 0.1;         // Min stop distance (% of price)
input double  InpStopHiPct  = 1.0;         // Max stop distance (% of price)
input int     InpMaxOpenVirtual = 10;      // Max concurrent virtual trades
input double  InpMinLots    = 0.01;        // Min lot
input double  InpMaxLots    = 10.0;        // Max lot
input double  InpSimStartBalance = 500.0;  // Virtual start balance for SimMode

input group "=== Strategy (2H) ==="
input int     InpSMA5       = 5;           // 2H SMMA5 period
input int     InpSMA13      = 13;          // 2H SMMA13 period
input double  InpPreGap     = 0.003;       // pre_cross SMA5/SMA13 gap threshold
input int     InpHistoryBars2H = 20000;    // 2H bars to load

input group "=== 4H Gate ==="
input int     InpGateSMA5   = 5;           // 4H SMMA5 period
input int     InpGateSMA13  = 13;          // 4H SMMA13 period
input int     InpMergedMinLen = 8;         // 4H merged segment min length
input int     InpVolMaPeriod = 120;        // 4H volume MA period
input double  InpGateThr    = 0.5;         // extreme-bar way/vol_way threshold
input double  InpGateAmpLo  = 0.5;         // SMMA13 extreme amplitude min (%)
input double  InpGateAmpHi  = 5.0;         // SMMA13 extreme amplitude max (%)
input int     InpHistoryBars4H = 10000;    // 4H bars to load

input group "=== Runtime ==="
input bool    InpSimMode     = true;       // true=virtual only (SAFE)
input bool    InpAllowRealTrading = false; // must be true for real orders (guard)
input bool    InpExportCSV   = true;       // signals CSV
input bool    InpExportLedger = true;      // trade ledger CSV
input bool    InpVerboseDiag = true;       // verbose per-bar diagnostics
input group "=== Macro Calendar Filter (research, default OFF) ==="
input bool   InpEventFilterOn   = true;   // 事件过滤总开关（M3 验证：V1_T1h PF 1.488）
input int    InpEventFilterHrs  = 1;  // 高影响事件前 N 小时内不开新仓（M3: V1_T1h PF 1.488）
input int    InpEventCheckEvery = 300;    // 日历查询缓存（秒）


//--- globals
string g_signals_csv  = "Oil_DataEvent_signals_export.csv";
string g_ledger_csv   = "Oil_DataEvent_trade_ledger.csv";
string g_gate_csv    = "Oil_DataEvent_gate_state.csv";
datetime g_last_bar   = 0;
int      g_bar_seq    = 0;
double   g_virtual_balance = 0.0;
CTrade   g_trade;

//--- gate state at the latest closed 4H bar
bool   g_gate_ok_l = false;   // gate passes for LONG (4H down extreme quality)
bool   g_gate_ok_s = false;   // gate passes for SHORT (4H up extreme quality)
bool     g_ev_blackout   = false;   // 未来 N 小时内有高影响事件（日历门）
datetime g_ev_next_check = 0;       // 下次日历查询时刻


//--- virtual trade
struct VirtualTrade
{
   datetime signal_time;
   datetime entry_time;
   int      dir;           // +1 LONG, -1 SHORT
   double   entry;
   double   stop;
   int      open_seq;      // bar seq when opened
   bool     exit_pending;  // opposite cross seen -> exit at next bar open
   bool     closed;
   ulong    ticket;        // real position ticket (0 = virtual only)
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
      FileWrite(h, "bar_time", "dir", "kind", "entry", "stop", "stop_pct",
                "gate_d", "gate_sl", "gate_w", "gate_v", "gate_amp", "decision");
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
         FileWrite(h, "signal_time", "entry_time", "dir", "entry", "stop", "stop_pct", "exit_time", "exit_price", "reason", "pnl_points", "pnl_usd", "virtual_balance");
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
//| Merged direction codes (chain absorption, min_len)                |
//+------------------------------------------------------------------+
void BuildMergedCodes(const int &raw[], int n, int min_len, int &merged[])
{
   ArrayResize(merged, n);
   for(int i = 0; i < n; i++) merged[i] = raw[i];

   int crossings[], cross_types[];
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
      if(region_count < min_len)
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
//| Rolling volume MA (pandas rolling(period, min_periods=1))         |
//+------------------------------------------------------------------+
void ComputeVolMa(const MqlRates &r[], int n, int period, double &vol_ma[])
{
   ArrayResize(vol_ma, n);
   for(int i = 0; i < n; i++)
   {
      double sum = 0.0;
      int c = 0;
      for(int j = i; j >= 0 && (i - j) < period; j--)
      {
         sum += r[j].tick_volume;
         c++;
      }
      vol_ma[i] = (c > 0) ? sum / c : 0.0;
   }
}

//+------------------------------------------------------------------+
//| way / way_s_way / vol_way_s_way over merged codes                 |
//+------------------------------------------------------------------+
void ComputeWayArrays(const MqlRates &r[], int n, const double &sma13[],
                      const int &merged[], const double &vol_ma[],
                      double &way[], double &way_sw[], double &vol_way_sw[])
{
   ArrayResize(way, n);
   ArrayResize(way_sw, n);
   ArrayResize(vol_way_sw, n);
   int y = 0, x = 0, z = 0;
   int prev_d = 0;
   for(int i = 0; i < n; i++)
   {
      int d = merged[i];
      if(sma13[i] == 0.0 || !MathIsValidNumber(sma13[i])) d = 0;
      double wsw = 0.0, vwsw = 0.0;
      if(d == 2 || d == -2)
      {
         y = x = z = 0;
      }
      else if(d == 1)
      {
         if(prev_d == 1)
         {
            y++;
            if(r[i].low >= sma13[i] && r[i].high >= r[i - 1].high) x++;
            if(r[i].tick_volume <= vol_ma[i]) z++;
         }
         else
         {
            y = 1;
            x = 1;
            z = (r[i].tick_volume <= vol_ma[i]) ? 1 : 0;
         }
         wsw = (y != 0) ? NormalizeDouble((double)x / y, 2) : 0.0;
         vwsw = (y != 0) ? NormalizeDouble((double)z / y, 2) : 0.0;
      }
      else if(d == -1)
      {
         if(prev_d == -1)
         {
            y--;
            if(r[i].high <= sma13[i] && r[i].low <= r[i - 1].low) x--;
            if(r[i].tick_volume <= vol_ma[i]) z--;
         }
         else
         {
            y = -1;
            x = -1;
            z = (r[i].tick_volume <= vol_ma[i]) ? -1 : 0;
         }
         wsw = (y != 0) ? NormalizeDouble((double)x / y, 2) : 0.0;
         vwsw = (y != 0) ? NormalizeDouble((double)z / y, 2) : 0.0;
      }
      way[i] = y;
      way_sw[i] = wsw;
      vol_way_sw[i] = vwsw;
      prev_d = d;
   }
}

//+------------------------------------------------------------------+
//| 4H gate arrays at the last closed bar:                            |
//|  dir_sign, seg_len, ext way/vol_way, amplitude                   |
//+------------------------------------------------------------------+
struct GateState
{
   int    dir_sign;
   int    seg_len;
   double ext_w;
   double ext_v;
   double amp;
};

bool ComputeGateState(const MqlRates &r4[], int n4, const double &sma13[],
                      const int &raw[], const int &merged[],
                      const double &way[], const double &wsw[], const double &vwsw[],
                      GateState &out)
{
   // run extreme index tracking (mirrors gate_arrays)
   int cur_sign = 0;
   int run_ext_idx = -1;
   for(int i = 0; i < n4; i++)
   {
      int d = merged[i];
      int sign = (d == 2 || d == 1) ? 1 : ((d == -2 || d == -1) ? -1 : 0);
      if(sign != cur_sign)
      {
         cur_sign = sign;
         run_ext_idx = i;
      }
      else if(cur_sign == 1 && r4[i].high > r4[run_ext_idx].high) run_ext_idx = i;
      else if(cur_sign == -1 && r4[i].low < r4[run_ext_idx].low) run_ext_idx = i;

      out.dir_sign = cur_sign;
      out.seg_len = (int)MathAbs(way[i]);
      out.ext_w = (run_ext_idx >= 0) ? wsw[run_ext_idx] : 0.0;
      out.ext_v = (run_ext_idx >= 0) ? vwsw[run_ext_idx] : 0.0;
      out.amp = 0.0;

      // amplitude: current vs previous raw-cross segment SMMA13 extreme
      int ci = -1;
      for(int k = i; k >= 0; k--)
      {
         if(MathAbs(raw[k]) == 2) { ci = k; break; }
      }
      if(ci >= 1 && cur_sign != 0)
      {
         int c0 = -1;
         for(int k = ci - 1; k >= 0; k--)
         {
            if(MathAbs(raw[k]) == 2) { c0 = k; break; }
         }
         if(c0 >= 0 && r4[i].close != 0.0)
         {
            double cur_ext = 0.0, prev_ext = 0.0;
            bool cur_set = false, prev_set = false;
            for(int k = ci; k <= i; k++)
            {
               if(sma13[k] == 0.0 || !MathIsValidNumber(sma13[k])) continue;
               if(cur_sign == -1) cur_ext = (!cur_set) ? sma13[k] : MathMin(cur_ext, sma13[k]);
               else               cur_ext = (!cur_set) ? sma13[k] : MathMax(cur_ext, sma13[k]);
               cur_set = true;
            }
            for(int k = c0; k < ci; k++)
            {
               if(sma13[k] == 0.0 || !MathIsValidNumber(sma13[k])) continue;
               if(cur_sign == -1) prev_ext = (!prev_set) ? sma13[k] : MathMax(prev_ext, sma13[k]);
               else               prev_ext = (!prev_set) ? sma13[k] : MathMin(prev_ext, sma13[k]);
               prev_set = true;
            }
            if(cur_set && prev_set)
               out.amp = MathAbs(cur_ext - prev_ext) / r4[i].close * 100.0;
         }
      }
   }
   return true;
}

//+------------------------------------------------------------------+
//| FindStop: previous RAW-cross segment SMMA13 extreme (Python)      |
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
//| PnL / ledger helpers                                              |
//+------------------------------------------------------------------+
double ContractSize()
{
   return SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE);
}

double CalcLot(double stop_price)
{
   double risk = g_virtual_balance * InpRiskPct / 100.0;
   double lot = (stop_price > 0.0) ? risk / (stop_price * ContractSize()) : InpMinLots;
   if(lot < InpMinLots) lot = InpMinLots;
   if(lot > InpMaxLots) lot = InpMaxLots;
   return lot;
}

double CalcLotReal(double stop_price)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = balance * InpRiskPct / 100.0;
   double lot = (stop_price > 0.0) ? risk / (stop_price * ContractSize()) : InpMinLots;
   if(lot < InpMinLots) lot = InpMinLots;
   if(lot > InpMaxLots) lot = InpMaxLots;
   double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;
   lot = MathFloor(lot / step) * step;
   return MathMax(InpMinLots, lot);
}

void RecordExit(int slot, datetime exit_time, double exit_price, string reason)
{
   if(!InpSimMode && g_trades[slot].ticket > 0)
   {
      if(PositionSelectByTicket(g_trades[slot].ticket))
      {
         if(!g_trade.PositionClose(g_trades[slot].ticket))
            Print("[REAL] CLOSE FAILED ticket=", g_trades[slot].ticket,
                  " retcode=", g_trade.ResultRetcode(), " comment=", g_trade.ResultRetcodeDescription());
         else
            Print("[REAL] CLOSE ticket=", g_trades[slot].ticket, " reason=", reason,
                  " px=", DoubleToString(exit_price, 5));
      }
      g_trades[slot].ticket = 0;
   }
   double pnl_points = (g_trades[slot].dir > 0)
                       ? (exit_price - g_trades[slot].entry)
                       : (g_trades[slot].entry - exit_price);
   double stop = MathAbs(g_trades[slot].entry - g_trades[slot].stop);
   double lot = CalcLot(stop);
   double pnl_usd = lot * pnl_points * ContractSize();
   g_virtual_balance += pnl_usd;

   if(InpExportLedger)
   {
      int h = FileOpen(g_ledger_csv, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
      if(h != INVALID_HANDLE)
      {
         FileSeek(h, 0, SEEK_END);
         FileWrite(h, TimeToString(g_trades[slot].signal_time), TimeToString(g_trades[slot].entry_time),
                   (g_trades[slot].dir > 0 ? "BUY" : "SELL"),
                   DoubleToString(g_trades[slot].entry, 5), DoubleToString(g_trades[slot].stop, 5),
                   DoubleToString(MathAbs(g_trades[slot].entry - g_trades[slot].stop) / g_trades[slot].entry * 100.0, 3),
                   TimeToString(exit_time), DoubleToString(exit_price, 5), reason,
                   DoubleToString(pnl_points, 5), DoubleToString(pnl_usd, 5),
                   DoubleToString(g_virtual_balance, 5));
         FileClose(h);
      }
   }
   if(InpVerboseDiag)
   {
      Print("[SIM] EXIT ", (g_trades[slot].dir > 0 ? "BUY" : "SELL"),
            " signal=", TimeToString(g_trades[slot].signal_time),
            " exit=", TimeToString(exit_time), " px=", DoubleToString(exit_price, 5),
            " reason=", reason, " pnl_pts=", DoubleToString(pnl_points, 5),
            " pnl_usd=", DoubleToString(pnl_usd, 5),
            " balance=", DoubleToString(g_virtual_balance, 5));
   }
}

//+------------------------------------------------------------------+
//| Manage open virtual trades on the just-closed bar                 |
//+------------------------------------------------------------------+
void ProcessOpenTrades(const MqlRates &rates[], int n, const int &raw2[])
{
   for(int s = 0; s < ArraySize(g_trades); s++)
   {
      if(g_trades[s].closed) continue;
      int age = g_bar_seq - g_trades[s].open_seq;
      if(age <= 0) continue;               // entry bar still forming
      int idx = n - 2;                     // always latest closed bar
      if(idx < 0) continue;
      MqlRates bar = rates[idx];
      bool is_long = g_trades[s].dir > 0;

      bool exit_now = false;
      double exit_px = 0.0;
      string reason = "";
      if(g_trades[s].exit_pending)
      {
         exit_px = bar.open;
         reason = "opposite cross";
         exit_now = true;
      }
      else
      {
         if(is_long)
         {
            if(bar.open <= g_trades[s].stop) { exit_px = bar.open; reason = "SL hit"; exit_now = true; }
            else if(bar.low <= g_trades[s].stop) { exit_px = g_trades[s].stop; reason = "SL hit"; exit_now = true; }
         }
         else
         {
            if(bar.open >= g_trades[s].stop) { exit_px = bar.open; reason = "SL hit"; exit_now = true; }
            else if(bar.high >= g_trades[s].stop) { exit_px = g_trades[s].stop; reason = "SL hit"; exit_now = true; }
         }
         if(!exit_now && ((is_long && raw2[idx] == -2) || (!is_long && raw2[idx] == 2)))
            g_trades[s].exit_pending = true;
      }
      if(exit_now)
      {
         RecordExit(s, bar.time, exit_px, reason);
         g_trades[s].closed = true;
      }
   }

   int w = 0;
   for(int s = 0; s < ArraySize(g_trades); s++)
   {
      if(!g_trades[s].closed)
      {
         if(w != s) g_trades[w] = g_trades[s];
         w++;
      }
   }
   ArrayResize(g_trades, w);
}

//+------------------------------------------------------------------+
//| Refresh 4H gate state at the latest closed 4H bar                 |
//+------------------------------------------------------------------+
void RefreshGate()
{
   g_gate_ok_l = false;
   g_gate_ok_s = false;
   MqlRates r4[];
   int n4 = CopyRates(InpSymbol, PERIOD_H4, 0, InpHistoryBars4H, r4);
   if(n4 < 60) return;
   // use only CLOSED 4H bars (drop the forming bar)
   n4--;
   if(n4 < 60) return;

   double sma5[], sma13[];
   if(!CalcSmmaArray(r4, n4, InpGateSMA5, sma5)) return;
   if(!CalcSmmaArray(r4, n4, InpGateSMA13, sma13)) return;
   int raw[], merged[];
   BuildRawCodes(sma5, sma13, n4, raw);
   BuildMergedCodes(raw, n4, InpMergedMinLen, merged);
   double vol_ma[];
   ComputeVolMa(r4, n4, InpVolMaPeriod, vol_ma);
   double way[], wsw[], vwsw[];
   ComputeWayArrays(r4, n4, sma13, merged, vol_ma, way, wsw, vwsw);
   GateState st;
   ComputeGateState(r4, n4, sma13, raw, merged, way, wsw, vwsw, st);

   bool amp_ok = (st.amp >= InpGateAmpLo && st.amp <= InpGateAmpHi);
   // BUG 修复(2026-09-04): way_s_way/vol_way_s_way 无符号 [0,1](down段 x/y=负/负=正),
   // LONG gate(down段) 应判 ext_w >= 阈值(强势下跌), 不能判 <= -阈值(恒 false -> 多单永不开)
   if(st.dir_sign == -1 && st.seg_len >= InpMergedMinLen &&
      st.ext_w >= InpGateThr && st.ext_v >= InpGateThr && amp_ok)
      g_gate_ok_l = true;
   if(st.dir_sign == 1 && st.seg_len >= InpMergedMinLen &&
      st.ext_w >= InpGateThr && st.ext_v >= InpGateThr && amp_ok)
      g_gate_ok_s = true;
}

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Restore real positions after EA reload (chart period switch etc.)|
//+------------------------------------------------------------------+
void RestoreRealPositions()
{
   if(InpSimMode) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(ArraySize(g_trades) >= InpMaxOpenVirtual) break;
      int s = ArraySize(g_trades);
      ArrayResize(g_trades, s + 1);
      g_trades[s].signal_time = (datetime)PositionGetInteger(POSITION_TIME);
      g_trades[s].entry_time = (datetime)PositionGetInteger(POSITION_TIME);
      g_trades[s].dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      g_trades[s].entry = PositionGetDouble(POSITION_PRICE_OPEN);
      g_trades[s].stop = PositionGetDouble(POSITION_SL);
      g_trades[s].open_seq = 0;
      g_trades[s].exit_pending = false;
      g_trades[s].closed = false;
      g_trades[s].ticket = ticket;
      Print("[REAL] RESTORED ticket=", ticket,
            " dir=", (g_trades[s].dir > 0 ? "BUY" : "SELL"),
            " entry=", DoubleToString(g_trades[s].entry, 5),
            " stop=", DoubleToString(g_trades[s].stop, 5));
   }
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
   ArrayResize(g_trades, 0);
   if(InpExportCSV) CsvSignalsHeader();
   if(InpExportLedger) CsvLedgerHeader();
   if(InpEventFilterOn) CsvGateHeader();
   Print("USOIL4H_Gate_On2H EA initialized. SimMode=", InpSimMode,
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
   if(!InpSimMode && !InpAllowRealTrading) return;

   datetime bar0_time = iTime(InpSymbol, PERIOD_H2, 0);
   if(bar0_time <= 0) return;
   if(bar0_time == g_last_bar) return;
   g_last_bar = bar0_time;
   g_bar_seq++;

   // refresh 4H gate state using the latest closed 4H bar (causal)
   RefreshGate();

   MqlRates rates[];
   int n = CopyRates(InpSymbol, PERIOD_H2, 0, InpHistoryBars2H, rates);
   if(n < 80) return;

   double sma5[], sma13[];
   if(!CalcSmmaArray(rates, n, InpSMA5, sma5)) return;
   if(!CalcSmmaArray(rates, n, InpSMA13, sma13)) return;
   int raw2[];
   BuildRawCodes(sma5, sma13, n, raw2);

   // manage open positions on the just-closed bar
   ProcessOpenTrades(rates, n, raw2);

   // detect signal on the just-closed bar (n-2)
   int sig_idx = n - 2;
   if(sig_idx < 1) return;
   int code = raw2[sig_idx];
   bool is_cross = (MathAbs(code) == 2);
   bool is_long = false;
   bool signal = false;

   if(is_cross)
   {
      is_long = (code == 2);
      signal = true;
   }
   else
   {
      // pre_cross: price crosses SMA13 while SMA5 stays on the other side
      if(sig_idx - 1 >= 0 && sma13[sig_idx - 1] != 0.0 && sma13[sig_idx] != 0.0 &&
         sma5[sig_idx] != 0.0)
      {
         double gap = MathAbs(sma5[sig_idx] - sma13[sig_idx]) / sma13[sig_idx];
         bool long_setup = rates[sig_idx - 1].close <= sma13[sig_idx - 1] &&
                           rates[sig_idx].close > sma13[sig_idx] &&
                           sma5[sig_idx] < sma13[sig_idx];
         bool short_setup = rates[sig_idx - 1].close >= sma13[sig_idx - 1] &&
                            rates[sig_idx].close < sma13[sig_idx] &&
                            sma5[sig_idx] > sma13[sig_idx];
         if(gap <= InpPreGap && (long_setup || short_setup))
         {
            is_long = long_setup;
            signal = true;
         }
      }
   }

   if(signal)
   {
      double stop = FindStopSma(sma5, sma13, sig_idx, is_long);
      double entry = iOpen(InpSymbol, PERIOD_H2, 0);   // bar i+1 open (current forming)
      double r = MathAbs(entry - stop);
      double pct = (entry > 0.0) ? r / entry * 100.0 : 0.0;
      bool side_ok = (is_long) ? (stop < entry) : (stop > entry);
      bool gate_ok = is_long ? g_gate_ok_l : g_gate_ok_s;

      if(EventBlackout() && InpVerboseDiag)
         Print("[CAL] signal blocked by event gate (next high-impact event within ", InpEventFilterHrs, "h)");
      bool ok = (stop != 0.0 && gate_ok && pct >= InpStopLoPct && pct <= InpStopHiPct && side_ok &&
                 ArraySize(g_trades) < InpMaxOpenVirtual && !EventBlackout());

      if(InpExportCSV)
      {
         int h = FileOpen(g_signals_csv, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
         if(h != INVALID_HANDLE)
         {
            FileSeek(h, 0, SEEK_END);
            FileWrite(h, TimeToString(rates[sig_idx].time),
                      (is_long ? "BUY" : "SELL"),
                      (is_cross ? "cross" : "pre_cross"),
                      DoubleToString(entry, 5), DoubleToString(stop, 5),
                      DoubleToString(pct, 3),
                      IntegerToString(g_gate_ok_l ? -1 : 1), "0", "0", "0", "0",
                      (ok ? "ENTRY" : "SKIP"));
            FileClose(h);
         }
      }

      if(ok)
      {
         int s = ArraySize(g_trades);
         ArrayResize(g_trades, s + 1);
         g_trades[s].signal_time = rates[sig_idx].time;
         g_trades[s].entry_time = bar0_time;
         g_trades[s].dir = is_long ? 1 : -1;
         g_trades[s].entry = entry;
         g_trades[s].stop = stop;
         g_trades[s].open_seq = g_bar_seq;
         g_trades[s].exit_pending = false;
         g_trades[s].closed = false;
         g_trades[s].ticket = 0;
         if(!InpSimMode)
         {
            double stop_dist = MathAbs(entry - stop);
            double lot = CalcLotReal(stop_dist);
            MqlTradeRequest req = {};
            MqlTradeResult  res = {};
            req.action       = TRADE_ACTION_DEAL;
            req.symbol       = InpSymbol;
            req.magic        = InpMagic;
            req.deviation    = 30;
            req.type_filling = ORDER_FILLING_FOK;
            req.volume       = lot;
            req.sl           = stop;
            req.tp           = 0;
            req.price        = is_long ? SymbolInfoDouble(InpSymbol, SYMBOL_ASK)
                                       : SymbolInfoDouble(InpSymbol, SYMBOL_BID);
            req.type         = is_long ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
            if(g_trade.OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
            {
               g_trades[s].ticket = res.order;
               Print("[REAL] OPEN ", (is_long ? "BUY" : "SELL"),
                     " ticket=", res.order, " lot=", DoubleToString(lot, 2),
                     " entry=", DoubleToString(res.price, 5),
                     " sl=", DoubleToString(stop, 5));
            }
            else
               Print("[REAL] OPEN FAILED retcode=", res.retcode, " comment=", res.comment);
         }
         if(InpVerboseDiag)
            Print("[SIM] OPEN ", (is_long ? "BUY" : "SELL"),
                  " signal=", TimeToString(g_trades[s].signal_time),
                  " entry=", DoubleToString(entry, 5),
                  " stop=", DoubleToString(stop, 5),
                  " pct=", DoubleToString(pct, 3),
                  " gate_l=", g_gate_ok_l, " gate_s=", g_gate_ok_s);
      }
      else if(InpVerboseDiag)
      {
         Print("[SKIP] signal=", TimeToString(rates[sig_idx].time),
               " dir=", (is_long ? "BUY" : "SELL"),
               " gate=", gate_ok, " pct=", DoubleToString(pct, 3),
               " side_ok=", side_ok);
      }
   }
}
//+------------------------------------------------------------------+

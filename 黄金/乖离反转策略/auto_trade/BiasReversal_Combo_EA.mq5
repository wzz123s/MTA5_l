//+------------------------------------------------------------------+
//|                  BiasReversal_Combo_EA.mq5                       |
//|  多空组合 EA（P3）                                               |
//|  做多: 6H bias5>0 & bias55>0 门 + M30 SMMA5 金叉 SMMA13          |
//|        -> 下一根 M30 bar 开盘做多（参考 2H_M30_6H 顺势逻辑）       |
//|  做空: H4 bias55>=InpShortGateThr 超涨门 + 2H up 段 SMA13 涨幅    |
//|        >= InpRiseThr + 段极值 way_s_way/vol_way_s_way >= InpWThr  |
//|        -> 下一根 2H bar 开盘做空（R3 超涨反转）                    |
//|  退出: SL InpStopPct% / TP InpTP_R*R / 反向交叉平仓                |
//|  多空各最多 1 仓（magic 区分），真实下单 + OnInit 恢复持仓          |
//+------------------------------------------------------------------+
#property copyright "BiasReversal Research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "=== Account ==="
input ulong   InpMagicLong    = 372036;   // 做多仓 magic
input ulong   InpMagicShort   = 372037;   // 做空仓 magic
input string  InpSymbol       = "XAUUSDm";

input group "=== 做空（超涨反转 R3）==="
input double  InpShortGateThr = 3.5;      // H4 bias55 超涨阈值 (%)
input double  InpRiseThr      = 3.0;      // 2H 当前up段 SMA13 涨幅阈值 (%)
input double  InpWThr         = 0.5;      // way_s_way / vol_way_s_way 阈值
input int     InpShortCdLoss  = 2;        // 连续止损达到该次数后冷却
input int     InpShortCdHours = 120;      // 冷却时长（小时）

input group "=== 做空开关（研究落地 2026-08-27）==="
input bool    InpEnableShort   = false;    // 做空分支总开关（信号级复核：做空侧 24笔仅+787pts/PF1.01，停用后整体 MaxDD -44%）


input group "=== 做多（模式）==="
input int     InpLongMode     = 0;        // 0=6H门+H1金叉（顺势，默认） 1=超跌镜像反转（H4超跌门+2H down段）
input double  InpLongGateThr  = 0.0;      // 6H bias5/bias55 必须 > 0（仅 InpLongMode=0 使用）

input group "=== Risk ==="
input double  InpRiskPct      = 1.0;      // 风险 %（真实余额）
input double  InpStopPct      = 1.2;      // 止损 %（固定）
input double  InpTpR          = 3.0;      // 止盈 R 倍数
input double  InpMinLots      = 0.01;
input double  InpMaxLots      = 10.0;

input group "=== Runtime ==="
input bool    InpSimMode      = true;     // true=只打印信号（安全）
input bool    InpAllowRealTrading = false;// 真实下单第二闸
input bool    InpExportLedger = true;     // 台账 CSV
input bool    InpVerboseDiag = true;
input int     InpHistoryBars = 600;      // 2H 结构计算窗口

input group "=== 台账回放（对齐 v9 基线口径，须 SimMode=true）==="
input bool    InpLedgerReplay  = false;   // true=只做 v9 口径虚拟台账回放(不产生订单/信号)
input double  InpReplayCostPct = 0.05;    // 回放成本(每边 %；python backtest_v9 固定 0.05)

//--- globals
string g_ledger_csv = "bias_reversal_combo_trade_ledger.csv";
int    g_ledger_handle = INVALID_HANDLE;
datetime g_last_m30 = 0;
datetime g_last_h1 = 0;
datetime g_last_h2 = 0;
datetime g_last_h4 = 0;
datetime g_last_h6 = 0;
bool   g_long_gate_ok = false;    // 6H 多头门
bool   g_short_gate_ok = false;   // H4 超涨门
bool   g_long_mirror_gate_ok = false;   // H4 超跌门（镜像做多，InpLongMode=1 时使用）
//--- 做多信号（M30 金叉 pending）
bool     g_long_pending = false;
datetime g_long_pending_time = 0;
//--- 做空信号（2H 结构 pending）
bool     g_short_pending = false;
datetime g_short_pending_time = 0;
int      g_short_loss_streak = 0;    // 做空连续止损计数
datetime g_short_cd_until = 0;       // 做空冷却截止时间
bool     g_short_had_pos = false;    // 上一 2H bar 是否有做空仓
//--- 台账回放(对齐 v9 基线口径)状态
bool     g_rp_ready = false;      // 回放初始化完成
bool     g_rp_requested = false;  // 回放请求(Tester 内 SimMode 自动启用; 实盘图表不受影响)
datetime g_rp_last_h1 = 0;        // 上一已处理 H1 新 bar open
datetime g_rp_last_h6 = 0;        // 上一已追加 H6 新 bar open
double   g_h1_open[];  double g_h1_close[];  double g_h1_s5[];  double g_h1_s13[];  // H1 全序列(自回放起点)
double   g_h6_open[];  double g_h6_close[];  double g_h6_s5[];  double g_h6_s55[];  // H6 全序列
int      g_h1_n = 0;  int g_h6_n = 0;
bool     g_rp_pos = false;        // 虚拟多仓(python 语义, 与实盘互不相干)
int      g_rp_entry_seq = -1;
double   g_rp_entry = 0.0, g_rp_stop = 0.0, g_rp_tp = 0.0;
CTrade g_trade;

//+------------------------------------------------------------------+
//| SMMA（与 Python calc_smma 一致）                                  |
//+------------------------------------------------------------------+
bool CalcSmmaArray(const MqlRates &r[], int n, int period, double &out[])
{
   if(n < period) return false;
   ArrayResize(out, n);
   double sum = 0.0;
   for(int i = 0; i < period; i++) sum += r[i].close;
   out[period - 1] = sum / period;
   for(int i = period; i < n; i++)
      out[i] = (out[i - 1] * (period - 1) + r[i].close) / period;
   for(int i = 0; i < period - 1; i++) out[i] = 0.0;
   return true;
}

//+------------------------------------------------------------------+
//| 门刷新：H4 超涨门 / 6H 多头门                                     |
//+------------------------------------------------------------------+
void RefreshGates()
{
   // H4 超涨门（做空资格）
   MqlRates h4[];
   int n4 = CopyRates(InpSymbol, PERIOD_H4, 0, 300, h4);
   g_short_gate_ok = false;
   g_long_mirror_gate_ok = false;
   if(n4 >= 57)
   {
      double s5[], s55[];
      if(CalcSmmaArray(h4, n4, 5, s5) && CalcSmmaArray(h4, n4, 55, s55))
      {
         int i = n4 - 2;   // 最新已收盘 H4 bar
         if(s55[i] > 0.0)
         {
            double bias55 = (h4[i].close - s55[i]) / s55[i] * 100.0;
            g_short_gate_ok = (h4[i].close > s5[i] && h4[i].close > s55[i] && bias55 >= InpShortGateThr);
            g_long_mirror_gate_ok = (h4[i].close < s5[i] && h4[i].close < s55[i] && bias55 <= -InpShortGateThr);
         }
      }
   }
   // 6H 多头门（做多资格）
   MqlRates h6[];
   int n6 = CopyRates(InpSymbol, PERIOD_H6, 0, 300, h6);
   g_long_gate_ok = false;
   if(n6 >= 57)
   {
      double s5b[], s55b[];
      if(CalcSmmaArray(h6, n6, 5, s5b) && CalcSmmaArray(h6, n6, 55, s55b))
      {
         int i = n6 - 2;
         if(s5b[i] > 0.0 && s55b[i] > 0.0)
         {
            double b5 = (h6[i].close - s5b[i]) / s5b[i] * 100.0;
            double b55 = (h6[i].close - s55b[i]) / s55b[i] * 100.0;
            g_long_gate_ok = (b5 > InpLongGateThr && b55 > InpLongGateThr);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| 2H 段结构：当前 up 段 SMA13 涨幅 + 段极值 way/vol_way             |
//| 返回 true 表示满足做空条件                                        |
//+------------------------------------------------------------------+
bool Check2HShortSetup(double &rise_out)
{
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_H2, 0, InpHistoryBars, r);
   if(n < 100) return false;
   double s5[], s13[], vol_ma[];
   if(!CalcSmmaArray(r, n, 5, s5)) return false;
   if(!CalcSmmaArray(r, n, 13, s13)) return false;
   // volume MA120 (BUG审查 2026-09-06): 原实现为窗口前缀累计均值, 与注释/Python rolling(120) 不符。
   // 对齐 Python vol_ma_120 = rolling(120, min_periods=1).mean()（含当前 bar 的前 <=120 根均值）。
   ArrayResize(vol_ma, n);
   {
      double vsum = 0.0;
      int cnt = 0;
      for(int i = 0; i < n; i++)
      {
         vsum += r[i].tick_volume;
         cnt++;
         if(i >= 120)
         {
            vsum -= r[i - 120].tick_volume;
            cnt--;
         }
         vol_ma[i] = (cnt > 0) ? vsum / cnt : 0.0;
      }
   }
   int last = n - 2;   // 最新已收盘 2H bar
   if(last < 2) return false;
   // 找当前段起点（最近一次 S5/S13 交叉之后）
   int seg_start = 0;
   bool seg_up = (s5[0] > s13[0]);
   for(int i = 1; i <= last; i++)
   {
      bool up = (s5[i] > s13[i]);
      if(up != seg_up) { seg_up = up; seg_start = i; }
   }
   if(!seg_up) return false;   // 只在 up 段做空
   // 找上一段（从 seg_start 再往前）
   int prev_end = seg_start - 1;
   if(prev_end < 1) return false;
   bool prev_up = (s5[prev_end] > s13[prev_end]);
   int prev_start = 0;
   for(int i = prev_end - 1; i >= 0; i--)
   {
      bool up = (s5[i] > s13[i]);
      if(up != prev_up) { prev_start = i + 1; break; }
   }
   if(prev_up) return false;   // 上一段必须是 down 段
   // prev_seg SMA13 最低
   double prev_min = DBL_MAX;
   for(int i = prev_start; i <= prev_end; i++)
      if(s13[i] > 0.0 && s13[i] < prev_min) prev_min = s13[i];
   if(prev_min <= 0.0 || prev_min >= DBL_MAX) return false;
   // 当前段 SMA13 最高 + way/vol_way（段极值 bar）
   double cur_max = 0.0;
   int y = 0, x = 0, z = 0;
   double ext_wsw = 0.0, ext_vwsw = 0.0;
   int ext_idx = -1;
   double ext_high = 0.0;
   for(int i = seg_start; i <= last; i++)
   {
      y++;
      bool ok_x = (r[i].low >= s13[i] && r[i].high >= r[i - 1].high);
      bool ok_z = (r[i].tick_volume <= vol_ma[i]);
      if(ok_x) x++;
      if(ok_z) z++;
      if(s13[i] > cur_max) cur_max = s13[i];
      if(r[i].high > ext_high) { ext_high = r[i].high; ext_idx = i; }
      if(ext_idx == i)
      {
         ext_wsw = (y > 0) ? (double)x / y : 0.0;
         ext_vwsw = (y > 0) ? (double)z / y : 0.0;
      }
   }
   if(y < 3) return false;
   rise_out = (cur_max - prev_min) / prev_min * 100.0;
   if(InpVerboseDiag && rise_out >= InpRiseThr * 0.5)
      Print("[2H SEG] rise=", DoubleToString(rise_out, 2), "% wsw=", DoubleToString(ext_wsw, 2),
            " vwsw=", DoubleToString(ext_vwsw, 2), " y=", y);
   return (rise_out >= InpRiseThr && ext_wsw >= InpWThr && ext_vwsw >= InpWThr);
}

//+------------------------------------------------------------------+
//| 2H 段结构：当前 down 段 SMA13 跌幅 + 段极值 way/vol_way           |
//| 返回 true 表示满足做多（超跌镜像，InpLongMode=1）条件              |
//+------------------------------------------------------------------+
bool Check2HLongSetup(double &fall_out)
{
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_H2, 0, InpHistoryBars, r);
   if(n < 100) return false;
   double s5[], s13[], vol_ma[];
   if(!CalcSmmaArray(r, n, 5, s5)) return false;
   if(!CalcSmmaArray(r, n, 13, s13)) return false;
   // volume MA120 (BUG审查 2026-09-06): 同 Check2HShortSetup 修正, 尾随滚动 120 (含当前 bar)
   ArrayResize(vol_ma, n);
   {
      double vsum = 0.0;
      int cnt = 0;
      for(int i = 0; i < n; i++)
      {
         vsum += r[i].tick_volume;
         cnt++;
         if(i >= 120)
         {
            vsum -= r[i - 120].tick_volume;
            cnt--;
         }
         vol_ma[i] = (cnt > 0) ? vsum / cnt : 0.0;
      }
   }
   int last = n - 2;   // 最新已收盘 2H bar
   if(last < 2) return false;
   int seg_start = 0;
   bool seg_up = (s5[0] > s13[0]);
   for(int i = 1; i <= last; i++)
   {
      bool up = (s5[i] > s13[i]);
      if(up != seg_up) { seg_up = up; seg_start = i; }
   }
   if(seg_up) return false;   // 只在 down 段做多
   int prev_end = seg_start - 1;
   if(prev_end < 1) return false;
   bool prev_up = (s5[prev_end] > s13[prev_end]);
   int prev_start = 0;
   for(int i = prev_end - 1; i >= 0; i--)
   {
      bool up = (s5[i] > s13[i]);
      if(up != prev_up) { prev_start = i + 1; break; }
   }
   if(!prev_up) return false;   // 上一段必须是 up 段
   // prev_seg SMA13 最高
   double prev_max = 0.0;
   for(int i = prev_start; i <= prev_end; i++)
      if(s13[i] > 0.0 && s13[i] > prev_max) prev_max = s13[i];
   if(prev_max <= 0.0) return false;
   // 当前段 SMA13 最低 + way/vol_way（段极值 bar，极值=最低 low）
   double cur_min = DBL_MAX;
   int y = 0, x = 0, z = 0;
   double ext_wsw = 0.0, ext_vwsw = 0.0;
   int ext_idx = -1;
   double ext_low = DBL_MAX;
   for(int i = seg_start; i <= last; i++)
   {
      y++;
      bool ok_x = (r[i].high <= s13[i] && r[i].low <= r[i - 1].low);
      bool ok_z = (r[i].tick_volume <= vol_ma[i]);
      if(ok_x) x++;
      if(ok_z) z++;
      if(s13[i] > 0.0 && s13[i] < cur_min) cur_min = s13[i];
      if(r[i].low < ext_low) { ext_low = r[i].low; ext_idx = i; }
      if(ext_idx == i)
      {
         ext_wsw = (y > 0) ? (double)x / y : 0.0;
         ext_vwsw = (y > 0) ? (double)z / y : 0.0;
      }
   }
   if(y < 3) return false;
   fall_out = (prev_max - cur_min) / prev_max * 100.0;
   if(InpVerboseDiag && fall_out >= InpRiseThr * 0.5)
      Print("[2H SEG-L] fall=", DoubleToString(fall_out, 2), "% wsw=", DoubleToString(ext_wsw, 2),
            " vwsw=", DoubleToString(ext_vwsw, 2), " y=", y);
   return (fall_out >= InpRiseThr && ext_wsw >= InpWThr && ext_vwsw >= InpWThr);
}

//+------------------------------------------------------------------+
//| 手数                                                              |
//+------------------------------------------------------------------+
double CalcLot(double stop_dist)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = balance * InpRiskPct / 100.0;
   double lot = (stop_dist > 0.0) ? risk / (stop_dist * SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE)) : InpMinLots;
   if(lot < InpMinLots) lot = InpMinLots;
   if(lot > InpMaxLots) lot = InpMaxLots;
   double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;
   lot = MathFloor(lot / step) * step;
   return MathMax(InpMinLots, lot);
}

//+------------------------------------------------------------------+
//| 开仓（真实 / 信号）                                               |
//+------------------------------------------------------------------+
bool OpenPosition(int dir, ulong magic, double stop, string tag)
{
   if(InpSimMode)
   {
      if(InpVerboseDiag) Print("[SIG] ", tag, " ", (dir > 0 ? "BUY" : "SELL"),
            " (SimMode, no order) stop=", DoubleToString(stop, 5));
      return false;
   }
   double entry = (dir > 0) ? SymbolInfoDouble(InpSymbol, SYMBOL_ASK)
                            : SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   double stop_dist = MathAbs(entry - stop);
   double lot = CalcLot(stop_dist);
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = InpSymbol;
   req.magic        = magic;
   req.deviation    = 30;
   req.type_filling = ORDER_FILLING_FOK;
   req.volume       = lot;
   req.sl           = stop;
   // 开仓即挂服务器止盈: TP = entry ± (|entry-stop| × InpTpR)，与 Manage 逻辑一致
   req.tp           = (dir > 0) ? entry + stop_dist * InpTpR
                                : entry - stop_dist * InpTpR;
   req.price        = entry;
   req.type         = (dir > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(g_trade.OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
   {
      if(InpVerboseDiag)
         Print("[REAL] OPEN ", (dir > 0 ? "BUY" : "SELL"), " ", tag,
               " ticket=", res.order, " lot=", DoubleToString(lot, 2),
               " entry=", DoubleToString(res.price, 5), " sl=", DoubleToString(stop, 5));
      return true;
   }
   Print("[REAL] OPEN FAILED ", tag, " retcode=", res.retcode, " comment=", res.comment);
   return false;
}

//+------------------------------------------------------------------+
//| 台账追加（BUG-05: 平仓时记录一行）                                 |
//+------------------------------------------------------------------+
string RpTimeStr(datetime t)
{
   return TimeToString(t, TIME_DATE | TIME_SECONDS);
}

// 实盘平仓台账行(新列; 时间=平仓瞬间近似, 仅信息用途, 不参与对账)
void LedgerAppend(int dir, double entry, double stop, string reason, double exit_px)
{
   if(!InpExportLedger || g_ledger_handle == INVALID_HANDLE) return;
   FileSeek(g_ledger_handle, 0, SEEK_END);
   double pnl = (exit_px - entry) * dir;
   datetime now = TimeCurrent();
   FileWrite(g_ledger_handle,
             RpTimeStr(now), dir, DoubleToString(entry, 5), DoubleToString(stop, 5),
             RpTimeStr(now), DoubleToString(exit_px, 5), reason, DoubleToString(pnl, 2), 0,
             (dir > 0 ? "long" : "short"), RpTimeStr(now));
   FileFlush(g_ledger_handle);
}

//+------------------------------------------------------------------+
//| 台账回放引擎: 逐 H1 收盘行镜像 python long_ea_baseline 迭代        |
//| 开: pos空 && 上一行金叉 && 门 -> 以本行 open 开多(entry_i=本行),     |
//|     同迭代(if/else 语义)不再退出;                                 |
//| 平: 本行 low<=stop->SL(stop价); else high>=tp->TP(tp价);           |
//|     else 本行死叉 -> 以本行 open 价平(python opens[i] 回溯填);     |
//| pnl=(exit-entry)-entry*cost%/100*2; holding=行号差; 时间全 bar 戳  |
//+------------------------------------------------------------------+
void RpAppendH1(datetime t, double o, double h, double l, double c)
{
   if(g_h1_n >= 300000) return;
   int i = g_h1_n;
   g_h1_open[i] = (double)t;  g_h1_close[i] = c;
   double s5 = 0.0, s13 = 0.0;
   if(i == 4)
   {
      double sm = 0.0;
      for(int k = 0; k <= 4; k++) sm += g_h1_close[k];
      s5 = sm / 5.0;
   }
   else if(i > 4) s5 = (g_h1_s5[i - 1] * 4.0 + c) / 5.0;
   if(i == 12)
   {
      double sm = 0.0;
      for(int k = 0; k <= 12; k++) sm += g_h1_close[k];
      s13 = sm / 13.0;
   }
   else if(i > 12) s13 = (g_h1_s13[i - 1] * 12.0 + c) / 13.0;
   g_h1_s5[i] = s5;  g_h1_s13[i] = s13;
   g_h1_n++;
}

void RpAppendH6(datetime t, double o, double h, double l, double c)
{
   if(g_h6_n >= 60000) return;
   int i = g_h6_n;
   g_h6_open[i] = (double)t;  g_h6_close[i] = c;
   double s5 = 0.0, s55 = 0.0;
   if(i == 4)
   {
      double sm = 0.0;
      for(int k = 0; k <= 4; k++) sm += g_h6_close[k];
      s5 = sm / 5.0;
   }
   else if(i > 4) s5 = (g_h6_s5[i - 1] * 4.0 + c) / 5.0;
   if(i == 54)
   {
      double sm = 0.0;
      for(int k = 0; k <= 54; k++) sm += g_h6_close[k];
      s55 = sm / 55.0;
   }
   else if(i > 54) s55 = (g_h6_s55[i - 1] * 54.0 + c) / 55.0;
   g_h6_s5[i] = s5;  g_h6_s55[i] = s55;
   g_h6_n++;
}

// 门: 最新已收盘 H6(close_time<=close_target) 上 close>SMA5 且 close>SMA55
bool RpGateAt(datetime close_target)
{
   datetime bound = close_target - 6 * 3600;
   int l = 0, r = g_h6_n;
   while(l < r) { int m = (l + r) >> 1; if((datetime)g_h6_open[m] <= bound) l = m + 1; else r = m; }
   int idx = l - 1;
   if(idx < 55) return false;
   double c = g_h6_close[idx], s5 = g_h6_s5[idx], s55 = g_h6_s55[idx];
   if(s5 <= 0.0 || s55 <= 0.0) return false;
   return (c > s5 && c > s55);
}

// python 一次迭代(行 idx): 处理"刚收盘的 H1 行"
void RpPhaseB(MqlRates &row_i, int idx)
{
   bool gold_prev = false, dead_i = false;
   if(idx >= 14)
      gold_prev = (g_h1_s5[idx - 1] > g_h1_s13[idx - 1]) && (g_h1_s5[idx - 2] <= g_h1_s13[idx - 2]);
   if(idx >= 13)
      dead_i = (g_h1_s5[idx] < g_h1_s13[idx]) && (g_h1_s5[idx - 1] >= g_h1_s13[idx - 1]);
   if(!g_rp_pos)
   {
      if(gold_prev && RpGateAt(row_i.time + 3600))
      {
         g_rp_pos = true;  g_rp_entry_seq = idx;
         g_rp_entry = row_i.open;
         g_rp_stop  = row_i.open * (1.0 - InpStopPct / 100.0);
         g_rp_tp    = g_rp_entry + (g_rp_entry - g_rp_stop) * InpTpR;
      }
      return;    // python if/else: 入场行不做退出判定(最小持仓 1 行)
   }
   double exit_px = 0.0;  string reason = "";
   if(row_i.low  <= g_rp_stop)      { exit_px = g_rp_stop;  reason = "SL hit"; }
   else if(row_i.high >= g_rp_tp)   { exit_px = g_rp_tp;    reason = "TP hit"; }
   else if(dead_i)                  { exit_px = row_i.open; reason = "dead cross"; }
   if(reason != "")
   {
      double pnl = (exit_px - g_rp_entry) - g_rp_entry * InpReplayCostPct / 100.0 * 2.0;
      RpLedgerRow(idx, exit_px, reason, pnl);
      g_rp_pos = false;  g_rp_entry_seq = -1;
   }
}

void RpLedgerRow(int idx_exit, double exit_px, string reason, double pnl)
{
   if(!InpExportLedger || g_ledger_handle == INVALID_HANDLE) return;
   datetime sig_t = 0, entry_t = 0, exit_t = 0;
   if(g_rp_entry_seq >= 1) sig_t = (datetime)g_h1_open[g_rp_entry_seq - 1] + 3600;  // C_{entry-1}
   entry_t = (datetime)g_h1_open[g_rp_entry_seq];                                  // 入场行 open
   exit_t  = (datetime)g_h1_open[idx_exit] + 3600;                                  // C_exit
   FileSeek(g_ledger_handle, 0, SEEK_END);
   FileWrite(g_ledger_handle,
             RpTimeStr(sig_t), 1, DoubleToString(g_rp_entry, 5), DoubleToString(g_rp_stop, 5),
             RpTimeStr(exit_t), DoubleToString(exit_px, 5), reason,
             DoubleToString(pnl, 5), idx_exit - g_rp_entry_seq,
             "long", RpTimeStr(entry_t));
   FileFlush(g_ledger_handle);
}

void RpInit()
{
   g_rp_ready = false;
   g_rp_last_h1 = 0;  g_rp_last_h6 = 0;
   ArrayResize(g_h1_open, 300000);  ArrayResize(g_h1_close, 300000);
   ArrayResize(g_h1_s5, 300000);    ArrayResize(g_h1_s13, 300000);
   ArrayResize(g_h6_open, 60000);   ArrayResize(g_h6_close, 60000);
   ArrayResize(g_h6_s5, 60000);     ArrayResize(g_h6_s55, 60000);
   g_h1_n = 0;  g_h6_n = 0;
   g_rp_pos = false;  g_rp_entry_seq = -1;
   g_rp_ready = true;
}

void RpReplayTick()
{
   datetime h1_now = iTime(InpSymbol, PERIOD_H1, 0);
   datetime h6_now = iTime(InpSymbol, PERIOD_H6, 0);
   if(h1_now <= 0 || h6_now <= 0) return;
   if(h6_now != g_rp_last_h6)
   {
      g_rp_last_h6 = h6_now;
      MqlRates r6[];
      int k6 = CopyRates(InpSymbol, PERIOD_H6, 0, 2, r6);
      if(k6 >= 2 && (g_h6_n == 0 || (datetime)g_h6_open[g_h6_n - 1] != r6[0].time))
         RpAppendH6(r6[0].time, r6[0].open, r6[0].high, r6[0].low, r6[0].close);
   }
   if(h1_now == g_rp_last_h1) return;
   g_rp_last_h1 = h1_now;
   MqlRates r1[];
   int k1 = CopyRates(InpSymbol, PERIOD_H1, 0, 3, r1);
   if(k1 < 2) return;
   MqlRates row_i = r1[(k1 >= 3) ? 1 : 0];                  // 刚收盘 H1 行(起始段仅 1 根已收盘时取最老)
   if(g_h1_n > 0 && (datetime)g_h1_open[g_h1_n - 1] == row_i.time) return;
   RpAppendH1(row_i.time, row_i.open, row_i.high, row_i.low, row_i.close);
   RpPhaseB(row_i, g_h1_n - 1);
}

//+------------------------------------------------------------------+
//| 平仓（真实）                                                      |
//+------------------------------------------------------------------+
void CloseByMagic(ulong magic, string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != magic) continue;
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double stop  = PositionGetDouble(POSITION_SL);
      int dir      = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      if(InpSimMode) { if(InpVerboseDiag) Print("[SIG] CLOSE ", reason); continue; }
      if(!g_trade.PositionClose(ticket))
         Print("[REAL] CLOSE FAILED ticket=", ticket, " reason=", reason,
               " retcode=", g_trade.ResultRetcode());
      else
      {
         double exit_px = (dir > 0) ? SymbolInfoDouble(InpSymbol, SYMBOL_BID)
                                    : SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
         LedgerAppend(dir, entry, stop, reason, exit_px);
         if(InpVerboseDiag)
            Print("[REAL] CLOSE ticket=", ticket, " reason=", reason);
      }
   }
}

//+------------------------------------------------------------------+
//| 管理持仓：SL/TP/反向交叉                                          |
//+------------------------------------------------------------------+
void ManageLongH1()
{
   if(!PositionSelectByMagic(InpMagicLong)) return;
   double stop = PositionGetDouble(POSITION_SL);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   MqlRates bar0[];
   if(CopyRates(InpSymbol, PERIOD_H1, 0, 1, bar0) < 1) return;
   // SL 由服务器执行；检查 TP(3R) 与死叉
   double tp = entry + (entry - stop) * InpTpR;
   if(bar0[0].high >= tp)
   {
      CloseByMagic(InpMagicLong, "TP hit");
      return;
   }
   // H1 死叉（最新已收盘 bar）
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_H1, 0, 100, r);
   if(n < 14) return;
   double s5[], s13[];
   if(!CalcSmmaArray(r, n, 5, s5) || !CalcSmmaArray(r, n, 13, s13)) return;
   int i = n - 2;
   if(i >= 1 && s5[i] < s13[i] && s5[i - 1] >= s13[i - 1])
      CloseByMagic(InpMagicLong, "dead cross");
}

void ManageLongMirror()
{
   if(!PositionSelectByMagic(InpMagicLong)) return;
   double stop = PositionGetDouble(POSITION_SL);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   MqlRates bar0[];
   if(CopyRates(InpSymbol, PERIOD_H2, 0, 1, bar0) < 1) return;
   // SL 由服务器执行；检查 TP(3R) 与死叉（2H，镜像做空的 2H 金叉平仓）
   double tp = entry + (entry - stop) * InpTpR;
   if(bar0[0].high >= tp)
   {
      CloseByMagic(InpMagicLong, "TP hit");
      return;
   }
   // 2H 死叉（最新已收盘 bar）
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_H2, 0, 100, r);
   if(n < 14) return;
   double s5[], s13[];
   if(!CalcSmmaArray(r, n, 5, s5) || !CalcSmmaArray(r, n, 13, s13)) return;
   int i = n - 2;
   if(i >= 1 && s5[i] < s13[i] && s5[i - 1] >= s13[i - 1])
      CloseByMagic(InpMagicLong, "dead cross");
}

void ManageShort()
{
   bool had = g_short_had_pos;
   bool has = PositionSelectByMagic(InpMagicShort);
   if(had && !has)
   {
      // P2-3 修复: 区分 SL/TP 平仓(按最近平仓盈亏判定), 而非一律按 SL 计
      string reason = "SL hit";
      if(HistorySelect(0, TimeCurrent()))
      {
         int total = HistoryDealsTotal();
         for(int i = total - 1; i >= 0; i--)
         {
            ulong dt = HistoryDealGetTicket(i);
            if(dt == 0) continue;
            if(HistoryDealGetInteger(dt, DEAL_MAGIC) != InpMagicShort) continue;
            if(HistoryDealGetInteger(dt, DEAL_ENTRY) == DEAL_ENTRY_OUT)
            {
               double profit = HistoryDealGetDouble(dt, DEAL_PROFIT);
               reason = (profit > 0.0) ? "TP hit" : "SL hit";
               break;
            }
         }
      }
      UpdateShortCooldown(reason);
   }
   g_short_had_pos = has;
   if(!has) return;
   if(!PositionSelectByMagic(InpMagicShort)) return;
   double stop = PositionGetDouble(POSITION_SL);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   MqlRates bar0[];
   if(CopyRates(InpSymbol, PERIOD_H2, 0, 1, bar0) < 1) return;
   double tp = entry - (stop - entry) * InpTpR;
   if(bar0[0].low <= tp)
   {
      CloseByMagic(InpMagicShort, "TP hit");
      UpdateShortCooldown("TP hit");
      return;
   }
   // 2H 金叉（最新已收盘 bar）
   MqlRates r[];
   int n = CopyRates(InpSymbol, PERIOD_H2, 0, 100, r);
   if(n < 14) return;
   double s5[], s13[];
   if(!CalcSmmaArray(r, n, 5, s5) || !CalcSmmaArray(r, n, 13, s13)) return;
   int i = n - 2;
   if(i >= 1 && s5[i] > s13[i] && s5[i - 1] <= s13[i - 1])
   {
      CloseByMagic(InpMagicShort, "gold cross");
      UpdateShortCooldown("gold cross");
   }
}

bool PositionSelectByMagic(ulong magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionSelectByTicket(t))
         if(PositionGetString(POSITION_SYMBOL) == InpSymbol &&
            (ulong)PositionGetInteger(POSITION_MAGIC) == magic)
            return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| 恢复持仓（图表周期切换/重启后）                                    |
//+------------------------------------------------------------------+
void RestoreRealPositions()
{
   if(InpSimMode) return;
   // 虚拟模式不恢复；真实模式下仓位由服务器 SL 管理，magic 现查即可，
   // 无需内存状态（管理函数均按 magic 现查）。
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(!PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      ulong m = (ulong)PositionGetInteger(POSITION_MAGIC);
      if(m == InpMagicLong || m == InpMagicShort) cnt++;
   }
   if(cnt > 0 && InpVerboseDiag)
      Print("[REAL] RESTORED: tracking ", cnt, " position(s)");
}

//+------------------------------------------------------------------+
//| OnInit / OnDeinit / OnTick                                        |
//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagicLong);
   g_ledger_handle = INVALID_HANDLE;
   // 回放请求: 显式输入 或 (Strategy Tester + SimMode) 自动开启(对齐回测; 实盘不触发)
   g_rp_requested = InpLedgerReplay || (InpSimMode && MQLInfoInteger(MQL_TESTER) != 0);
   if(InpExportLedger)
   {
      // BUG-05 修复: FILE_READ|FILE_WRITE 追加模式（不再截断历史台账）
      bool is_replay = g_rp_requested;
      int open_flags = is_replay ? (FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ)
                                 : (FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ);  // 回放: 每次回测截断清空(ABC 同款)
      g_ledger_handle = FileOpen(g_ledger_csv, open_flags, ',');
      if(g_ledger_handle != INVALID_HANDLE)
      {
         if(!is_replay && FileSize(g_ledger_handle) > 0)
            FileSeek(g_ledger_handle, 0, SEEK_END);
         else
            FileWrite(g_ledger_handle,
                      "signal_time", "dir", "entry", "stop", "exit_time",
                      "exit", "exit_reason", "pnl_points", "holding_bars",
                      "side", "entry_time");
         FileFlush(g_ledger_handle);
      }
   }
   RefreshGates();
   RestoreRealPositions();
   if(g_rp_requested)
   {
      if(!InpSimMode)
      {
         Print("[REPLAY] 需 InpSimMode=true 才能回放; 回放未启用");
         g_rp_ready = false;
      }
      else if(InpLongMode != 0 || InpEnableShort)
      {
         Print("[REPLAY] 回放仅支持 InpLongMode=0 且 InpEnableShort=false; 回放未启用");
         g_rp_ready = false;
      }
      else
      {
         RpInit();
         Print("[REPLAY] 台账回放已启用(SimMode; cost=", DoubleToString(InpReplayCostPct, 2), "%)");
      }
   }
   Print("BiasReversal Combo EA initialized. SimMode=", InpSimMode,
         " AllowRealTrading=", InpAllowRealTrading,
         " LongMagic=", InpMagicLong, " ShortMagic=", InpMagicShort,
         " LongMode=", InpLongMode);
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
   if(!InpSimMode && !InpAllowRealTrading) return;
   if(g_rp_requested)                       // 回放对齐: 只写 v9 口径虚拟台账, 屏蔽信号/实盘逻辑
   {
      if(g_rp_ready) RpReplayTick();
      return;
   }

   datetime t_m30 = iTime(InpSymbol, PERIOD_M30, 0);
   datetime t_h1 = iTime(InpSymbol, PERIOD_H1, 0);
   datetime t_h2 = iTime(InpSymbol, PERIOD_H2, 0);
   datetime t_h4 = iTime(InpSymbol, PERIOD_H4, 0);
   datetime t_h6 = iTime(InpSymbol, PERIOD_H6, 0);
   if(t_m30 <= 0 || t_h2 <= 0) return;

   // H4 / 6H 门（各自新 bar 时刷新）
   if(t_h4 != g_last_h4) { g_last_h4 = t_h4; RefreshGates(); }
   if(t_h6 != g_last_h6) { g_last_h6 = t_h6; RefreshGates(); }

   // ---- M30 处理（做多：金叉信号 + 死叉平仓 + TP） ----
   if(t_m30 != g_last_m30)
   {
      g_last_m30 = t_m30;
      // 做多信号改用 H1 金叉（回测 PF 2.19 vs M30 1.57）；InpLongMode=1 时走镜像（2H 块处理）
      if(InpLongMode == 0 && t_h1 != g_last_h1)
      {
         g_last_h1 = t_h1;
         MqlRates r1[];
         int n1 = CopyRates(InpSymbol, PERIOD_H1, 0, 100, r1);
         if(n1 >= 14)
         {
            double s5b[], s13b[];
            if(CalcSmmaArray(r1, n1, 5, s5b) && CalcSmmaArray(r1, n1, 13, s13b))
            {
               int i = n1 - 2;
               bool gold_cross = (i >= 1 && s5b[i] > s13b[i] && s5b[i - 1] <= s13b[i - 1]);
               bool dead_cross = (i >= 1 && s5b[i] < s13b[i] && s5b[i - 1] >= s13b[i - 1]);
               if(gold_cross && g_long_gate_ok && !PositionSelectByMagic(InpMagicLong))
               {
                  double stop = r1[i].close * (1.0 - InpStopPct / 100.0);
                  OpenPosition(1, InpMagicLong, stop, "long_h1_gold_cross");
               }
               if(dead_cross)
                  CloseByMagic(InpMagicLong, "dead cross");
            }
         }
      }
      if(InpLongMode == 1)
         ManageLongMirror();
      else
         ManageLongH1();
   }

   // ---- 2H 处理（做空：结构反转信号 + 金叉平仓 + TP） ----
   if(t_h2 != g_last_h2)
   {
      g_last_h2 = t_h2;
      if(InpEnableShort && !PositionSelectByMagic(InpMagicShort) && TimeCurrent() >= g_short_cd_until)
      {
         double rise = 0.0;
         if(g_short_gate_ok && Check2HShortSetup(rise))
         {
            MqlRates r[];
            int n = CopyRates(InpSymbol, PERIOD_H2, 0, 2, r);
            if(n >= 2)
            {
               double stop = r[1].close * (1.0 + InpStopPct / 100.0);
               // 注意: 不得在开仓时清零连续止损计数，否则冷却永远无法触发
               //（连续止损只在 SL 平仓时 +1，TP/金叉平仓时归零，与回测 v7 一致）
               OpenPosition(-1, InpMagicShort, stop, "short_bias_reversal");
            }
         }
      }
      // ---- 镜像做多（InpLongMode=1：H4 超跌门 + 2H down 段结构反转） ----
      if(InpLongMode == 1 && !PositionSelectByMagic(InpMagicLong))
      {
         double fall = 0.0;
         if(g_long_mirror_gate_ok && Check2HLongSetup(fall))
         {
            MqlRates r2[];
            int n2 = CopyRates(InpSymbol, PERIOD_H2, 0, 2, r2);
            if(n2 >= 2)
            {
               double stop = r2[1].close * (1.0 - InpStopPct / 100.0);
               OpenPosition(1, InpMagicLong, stop, "long_mirror_reversal");
            }
         }
      }
      ManageShort();
   }
}

//+------------------------------------------------------------------+
//| 做空平仓后的冷却状态更新                                          |
//+------------------------------------------------------------------+
void UpdateShortCooldown(string reason)
{
   if(reason == "SL hit")
   {
      g_short_loss_streak++;
      if(g_short_loss_streak >= InpShortCdLoss)
      {
         g_short_cd_until = TimeCurrent() + InpShortCdHours * 3600;
         if(InpVerboseDiag)
            Print("[CD] short cooldown ", InpShortCdHours, "h after ", g_short_loss_streak, " consecutive SL");
      }
   }
   else
      g_short_loss_streak = 0;
}


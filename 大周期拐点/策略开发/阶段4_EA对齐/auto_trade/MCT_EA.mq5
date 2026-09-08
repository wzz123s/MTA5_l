//+------------------------------------------------------------------+
//|                       MCT_EA.mq5                                 |
//|  MCT 大周期拐点策略 · 原油候选包（EA 对齐契约 v2，因果实现）       |
//|  机会：D1 SMMA13x55 穿越(glue<=0.3%) → 武装 LONG/SHORT 40 天      |
//|  入场：H4 SMA5/13 状态机 + 增量 v4 链式吸收(min_len=8)；          |
//|        武装期内待定穿越点(good→BUY/bad→SELL) → 下一 bar open；    |
//|        bias55 同向；StopSpec 0.8%~2.5%                           |
//|  止损：待定穿越点前段 merged run 的 SMMA13 极值（因果）           |
//|  退出：hybrid：+1.5R 出 1/3(移保本) → 待定穿越点高取低移动(仅盈利) |
//|        → 止损 / 120 bar 超时；同方向 1 持仓；虚拟盘(SimMode)      |
//|  账本：CSV 与 stage4_causal.py expected ledger 同格式            |
//+------------------------------------------------------------------+
#property copyright "Codex"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "=== Account ==="
input ulong   InpMagic        = 411103;    // Magic Number
input string  InpSymbol       = "USOILm";  // Symbol
input double  InpRiskPct      = 1.0;       // Risk % (virtual, 仅用于手数计算)
input double  InpLots         = 0.01;      // 固定手数（对齐运行）
input double  InpSimStartBalance = 500.0;  // 虚拟起始余额

input group "=== Strategy: D1 机会层 ==="
input int     InpD1SMA13      = 13;        // D1 SMMA13
input int     InpD1SMA55      = 55;        // D1 SMMA55
input double  InpGlue         = 0.003;     // 13x55 粘合阈值
input int     InpArmDays      = 40;        // 武装有效期(天)
input string  InpD1DataStart  = "2019.03.01"; // D1 数据起点（对齐 Python 真密度窗口）

input group "=== Strategy: H4 入场/退出 ==="
input int     InpH4SMA5       = 5;         // H4 SMMA5
input int     InpH4SMA13      = 13;        // H4 SMMA13
input int     InpH4SMA55      = 55;        // H4 SMMA55（bias 用）
input int     InpMinLen       = 8;         // 段合并最小长度
input string  InpH4DataStart  = "2021.07.01"; // H4 数据起点（对齐 Python 真密度窗口）
input double  InpStopLoPct    = 0.008;     // StopSpec 下限
input double  InpStopHiPct    = 0.025;     // StopSpec 上限
input double  InpTp1R         = 1.5;       // 第一批止盈 R 倍数
input double  InpFrac1        = 0.3333;    // 第一批仓位比例
input int     InpTimeExitBars = 120;       // 超时 bar 数
input bool    InpBiasOn       = true;      // bias55 过滤开关

input group "=== Costs（对齐运行置 0）==="
input double  InpSpreadCost   = 0.0;       // 固定点差成本（价格单位）
input double  InpSwapCostBar  = 0.0;       // 每 bar 隔夜成本（价格单位）

input group "=== Runtime ==="
input bool    InpSimMode      = true;      // 虚拟盘（安全）
input bool    InpAllowRealTrading = false; // 实盘守卫
input bool    InpExportLedger = true;      // 账本 CSV
input bool    InpExportDiag   = true;      // 诊断 CSV

//--- globals
string g_ledger = "MCT_trade_ledger.csv";
string g_diag   = "MCT_diag.csv";
datetime g_last_bar_time = 0;
double   g_virtual_balance = 0.0;

//--- H4 状态（增量维护）
double g_h4_open[], g_h4_high[], g_h4_low[], g_h4_close[];
double g_h4_sma5[], g_h4_sma13[], g_h4_sma55[];
int    g_h4_raw[];          // 2=good,-2=bad,1=up,-1=down,0=nan
datetime g_h4_time[];       // bar 时间（时间锚定用）
int    g_h4_n = 0;
int    g_processed_n = 0;   // 已处理的 bar 数（增量吸收起点）
datetime g_array_start = 0; // 过滤后数组首 bar 时间（漂移检测）

//--- 幸存穿越点列表（增量链式吸收）
struct CrossPt { int pos; int type; double stop; datetime bar_time; };
CrossPt g_cands[];
int     g_cands_n = 0;

//--- D1 武装
struct ArmWin { datetime t0; datetime t1; int dir; };
ArmWin  g_arms[];
int     g_arms_n = 0;
datetime g_last_d1_close = 0;

//--- 虚拟持仓
struct VPos
{
   int      dir;            // +1 BUY, -1 SELL
   double   entry;
   double   stop;           // 当前止损
   double   init_stop;      // 初始结构止损
   double   R;
   datetime entry_time;
   datetime signal_time;
   int      hold;
   bool     tp1_hit;
   double   frac_open;
   double   realized;
};
VPos g_pos[];               // [0]=LONG, [1]=SHORT（同方向 1 持仓）
bool g_pos_open[2];

//+------------------------------------------------------------------+
//| CSV 账本                                                         |
//+------------------------------------------------------------------+
int CsvHandle(string fname)
{
   return FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
}

void CsvLedgerHeader()
{
   int h = FileOpen(g_ledger, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h != INVALID_HANDLE)
   {
      if(FileSize(h) == 0)
         FileWrite(h, "signal_time", "entry_time", "dir", "entry", "stop",
                      "exit_time", "exit_price", "reason", "pnl_points",
                      "pnl_usd", "virtual_balance");
      else
         FileSeek(h, 0, SEEK_END);
      FileClose(h);
   }
   if(InpExportDiag)
   {
      int d = FileOpen(g_diag, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(d != INVALID_HANDLE)
      {
         if(FileSize(d) == 0)
            FileWrite(d, "bar_time", "kind", "dir", "price", "detail");
         else
            FileSeek(d, 0, SEEK_END);
         FileClose(d);
      }
   }
}

void Diag(const datetime bt, const string kind, const int dir,
          const double price, const string detail)
{
   if(!InpExportDiag) return;
   int d = FileOpen(g_diag, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(d == INVALID_HANDLE) return;
   FileSeek(d, 0, SEEK_END);
   FileWrite(d, TimeToString(bt), kind, dir, DoubleToString(price, 5), detail);
   FileClose(d);
}

void CsvLedgerRow(const VPos &p, datetime exit_time, double exit_price,
                  string reason)
{
   if(!InpExportLedger) return;
   int h = FileOpen(g_ledger, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   double pnl_pts = p.realized;
   double pnl_usd = pnl_pts * 1000.0 * InpLots;   // USOIL 合约 1000
   g_virtual_balance += pnl_usd;
   FileWrite(h, TimeToString(p.signal_time), TimeToString(p.entry_time),
             (p.dir == 1 ? "BUY" : "SELL"),
             DoubleToString(p.entry, 5), DoubleToString(p.init_stop, 5),
             TimeToString(exit_time), DoubleToString(exit_price, 5),
             reason, DoubleToString(pnl_pts, 5),
             DoubleToString(pnl_usd, 5), DoubleToString(g_virtual_balance, 5));
   FileClose(h);
}

//+------------------------------------------------------------------+
//| SMMA（mean-init，与 Python calc_sma 一致）                        |
//+------------------------------------------------------------------+
void CalcSmma(const double &src[], int n, int period, double &out[])
{
   ArrayResize(out, n);
   for(int i = 0; i < n; i++) out[i] = 0.0;
   if(n < period) return;
   double sum = 0.0;
   for(int i = 0; i < period; i++) sum += src[i];
   out[period - 1] = sum / period;
   for(int i = period; i < n; i++)
      out[i] = (src[i] + (period - 1) * out[i - 1]) / period;
}

//+------------------------------------------------------------------+
//| H4 raw 状态码 + 增量链式吸收 + 前段极值                           |
//+------------------------------------------------------------------+
void UpdateH4State()
{
   MqlRates rates_all[];
   int got = CopyRates(InpSymbol, PERIOD_H4, 0, 20000, rates_all);
   if(got <= 0) return;
   // 数据起点过滤（对齐 Python 真密度窗口）
   datetime ds = StringToTime(InpH4DataStart);
   int off = 0;
   while(off < got && rates_all[off].time < ds) off++;
   int nn = got - off;
   if(nn < 2) { g_processed_n = 0; return; }
   MqlRates rates[];
   ArrayResize(rates, nn);
   for(int i = 0; i < nn; i++) rates[i] = rates_all[off + i];
   ArrayResize(g_h4_open, nn); ArrayResize(g_h4_high, nn);
   ArrayResize(g_h4_low, nn);  ArrayResize(g_h4_close, nn);
   ArrayResize(g_h4_time, nn);
   for(int i = 0; i < nn; i++)
   {
      g_h4_open[i]  = rates[i].open;
      g_h4_high[i]  = rates[i].high;
      g_h4_low[i]   = rates[i].low;
      g_h4_close[i] = rates[i].close;
      g_h4_time[i]  = rates[i].time;
   }
   double closes[];
   ArrayResize(closes, nn);
   for(int i = 0; i < nn; i++) closes[i] = g_h4_close[i];
   CalcSmma(closes, nn, InpH4SMA5,  g_h4_sma5);
   CalcSmma(closes, nn, InpH4SMA13, g_h4_sma13);
   CalcSmma(closes, nn, InpH4SMA55, g_h4_sma55);
   ArrayResize(g_h4_raw, nn);
   bool prev_above = false;
   bool have_prev = false;
   for(int i = 0; i < nn; i++)
   {
      if(g_h4_sma5[i] == 0.0 || g_h4_sma13[i] == 0.0)
      {
         g_h4_raw[i] = 0;
         continue;
      }
      bool above = g_h4_sma5[i] > g_h4_sma13[i];
      if(!have_prev)
      {
         g_h4_raw[i] = above ? 1 : -1;
         have_prev = true;
      }
      else if(above && !prev_above) g_h4_raw[i] = 2;
      else if(!above && prev_above) g_h4_raw[i] = -2;
      else g_h4_raw[i] = above ? 1 : -1;
      prev_above = above;
   }
   g_h4_n = nn;

   // 漂移检测：过滤后数组起点变化（Tester 缓存扩展）→ 全量重建一次
   if(g_array_start != 0 && g_array_start != g_h4_time[0])
   {
      g_cands_n = 0;
      g_processed_n = 0;
   }
   g_array_start = g_h4_time[0];
   // 增量吸收：只处理新增的已收盘 bar（成形 bar 不处理，避免 lookahead）
   if(g_processed_n < 0) g_processed_n = 0;
   if(g_processed_n > nn - 2) g_processed_n = nn - 2;
   for(int i = g_processed_n; i < nn - 1; i++)
   {
      int c = g_h4_raw[i];
      if(c == 2 || c == -2)
      {
         g_cands[g_cands_n].pos = i;
         g_cands[g_cands_n].type = c;
         g_cands[g_cands_n].bar_time = rates[i].time;
         g_cands_n++;
         // 尾部吸收（等价于前向算法：新穿越点到达只影响以其结尾的 pair 链）
         while(g_cands_n >= 2)
         {
            CrossPt a = g_cands[g_cands_n - 2];
            CrossPt b = g_cands[g_cands_n - 1];
            int region = 0;
            for(int k = a.pos + 1; k < b.pos; k++)
               if(g_h4_raw[k] == (a.type == 2 ? 1 : -1)) region++;
            if(region < InpMinLen)
               g_cands_n -= 2;
            else
               break;
         }
         // 计算待定穿越点前段极值（merged run 的 SMMA13 极值）
         if(g_cands_n >= 1)
         {
            CrossPt last = g_cands[g_cands_n - 1];
            int s0 = (g_cands_n >= 2) ? g_cands[g_cands_n - 2].pos + 1 : 0;
            double stopv = 0.0;
            if(last.type == 2)
            {
               double mn = DBL_MAX;
               for(int k = s0; k < last.pos; k++)
                  if(g_h4_sma13[k] > 0.0 && g_h4_sma13[k] < mn) mn = g_h4_sma13[k];
               stopv = (mn == DBL_MAX) ? 0.0 : mn;
            }
            else
            {
               double mx = 0.0;
               for(int k = s0; k < last.pos; k++)
                  if(g_h4_sma13[k] > mx) mx = g_h4_sma13[k];
               stopv = mx;
            }
            g_cands[g_cands_n - 1].stop = stopv;
            Diag(rates[i].time, "H4_pending", (c == 2 ? 1 : -1),
                 g_h4_close[i], "stop=" + DoubleToString(stopv, 5));
         }
      }
   }
   g_processed_n = nn - 1;
}


//+------------------------------------------------------------------+
//| D1 穿越检测 + 武装（每个新 H4 bar 检查一次）                      |
//+------------------------------------------------------------------+
void CheckD1AndArm(datetime now)
{
   MqlRates d1_all[];
   int got = CopyRates(InpSymbol, PERIOD_D1, 0, 5000, d1_all);
   if(got < 55) return;
   // 数据起点过滤
   datetime ds = StringToTime(InpD1DataStart);
   int off = 0;
   while(off < got && d1_all[off].time < ds) off++;
   int nn = got - off;
   if(nn < 55) return;
   MqlRates d1[];
   ArrayResize(d1, nn);
   for(int i = 0; i < nn; i++) d1[i] = d1_all[off + i];
   double closes[];
   ArrayResize(closes, nn);
   for(int i = 0; i < nn; i++) closes[i] = d1[i].close;
   double s13[], s55[];
   CalcSmma(closes, nn, InpD1SMA13, s13);
   CalcSmma(closes, nn, InpD1SMA55, s55);
   // 最后一个已收盘 D1 bar（shift 1）
   int last = nn - 2;
   if(last < 0) return;
   datetime last_time = d1[last].time;
   if(last_time == g_last_d1_close) return;   // 已处理
   if(last - 1 >= 0 && s13[last] > 0.0 && s55[last] > 0.0 &&
      s13[last-1] > 0.0 && s55[last-1] > 0.0)
   {
      bool prev_gt = s13[last-1] > s55[last-1];
      bool cur_gt  = s13[last]   > s55[last];
      int dir = 0;
      if(!prev_gt && cur_gt) dir = 1;
      else if(prev_gt && !cur_gt) dir = -1;
      if(dir != 0)
      {
         double glue = MathAbs(s13[last] - s55[last]) / s55[last];
         if(glue <= InpGlue)
         {
            g_arms[g_arms_n].t0 = last_time;
            g_arms[g_arms_n].t1 = last_time + InpArmDays * 86400;
            g_arms[g_arms_n].dir = dir;
            g_arms_n++;
            Diag(last_time, "D1_cross", dir, d1[last].close,
                 "glue=" + DoubleToString(glue, 4));
         }
         else
            Diag(last_time, "D1_cross_rej_glue", dir, d1[last].close,
                 "glue=" + DoubleToString(glue, 4));
      }
   }
   g_last_d1_close = last_time;
}

bool IsArmed(datetime t, int dir)
{
   for(int i = 0; i < g_arms_n; i++)
      if(g_arms[i].dir == dir && t > g_arms[i].t0 && t <= g_arms[i].t1)
         return true;
   return false;
}

//+------------------------------------------------------------------+
//| 开仓/平仓辅助                                                     |
//+------------------------------------------------------------------+
int PosIndex(int dir) { return (dir == 1) ? 0 : 1; }

void ClosePosition(int dir, datetime exit_time, double exit_price, string reason)
{
   int idx = PosIndex(dir);
   if(!g_pos_open[idx]) return;
   CsvLedgerRow(g_pos[idx], exit_time, exit_price, reason);
   g_pos_open[idx] = false;
}

void TryOpen(datetime now, int cur_bar)
{
   // 待定穿越点 = g_cands 最后一个（其在 cur_bar-1 处）
   if(g_cands_n == 0) return;
   CrossPt last = g_cands[g_cands_n - 1];
   // 待定穿越点必须是上一根已收盘 bar（用 bar 时间判断，免疫数组漂移）
   if(last.bar_time != iTime(InpSymbol, PERIOD_H4, 1))
   {
      Diag(now, "entry_skip_not_last", 0, 0.0,
           "last=" + TimeToString(last.bar_time) + " expect=" + TimeToString(iTime(InpSymbol, PERIOD_H4, 1)));
      return;
   }
   int d = (last.type == 2) ? 1 : -1;
   int idx = PosIndex(d);
   if(g_pos_open[idx]) return;
   if(!IsArmed(now, d))
   {
      Diag(now, "entry_skip_not_armed", d, 0.0, "arms=" + IntegerToString(g_arms_n));
      return;
   }
   if(InpBiasOn)
   {
      if(g_h4_sma55[last.pos] == 0.0)
      {
         Diag(now, "entry_skip_sma55_nan", d, 0.0, "pos=" + IntegerToString(last.pos));
         return;
      }
      if(d == 1 && g_h4_close[last.pos] <= g_h4_sma55[last.pos])
      {
         Diag(now, "entry_skip_bias", d, g_h4_close[last.pos],
              "sma55=" + DoubleToString(g_h4_sma55[last.pos], 5));
         return;
      }
      if(d == -1 && g_h4_close[last.pos] >= g_h4_sma55[last.pos])
      {
         Diag(now, "entry_skip_bias", d, g_h4_close[last.pos],
              "sma55=" + DoubleToString(g_h4_sma55[last.pos], 5));
         return;
      }
   }
   double stop = last.stop;
   if(stop <= 0.0)
   {
      Diag(now, "entry_skip_stop0", d, 0.0, "");
      return;
   }
   double entry = g_h4_open[cur_bar];
   double R = MathAbs(entry - stop);
   if(R <= 0.0)
   {
      Diag(now, "entry_skip_r0", d, entry, "stop=" + DoubleToString(stop, 5));
      return;
   }
   double ratio = R / entry;
   if(ratio < InpStopLoPct || ratio > InpStopHiPct)
   {
      Diag(now, "entry_skip_spec", d, entry,
           "stop=" + DoubleToString(stop, 5) + " ratio=" + DoubleToString(ratio, 5));
      return;
   }
   // 开仓
   g_pos[idx].dir = d;
   g_pos[idx].entry = entry;
   g_pos[idx].stop = stop;
   g_pos[idx].init_stop = stop;
   g_pos[idx].R = R;
   g_pos[idx].entry_time = iTime(InpSymbol, PERIOD_H4, 0);   // 当前 bar 开放时间
   g_pos[idx].signal_time = last.bar_time;
   g_pos[idx].hold = 0;
   g_pos[idx].tp1_hit = false;
   g_pos[idx].frac_open = 1.0;
   g_pos[idx].realized = 0.0;
   g_pos_open[idx] = true;
   Diag(now, "entry_open", d, entry,
        "stop=" + DoubleToString(stop, 5) + " R=" + DoubleToString(R, 5));
}

//+------------------------------------------------------------------+
//| 持仓管理（用刚收盘 bar cur_bar-1 的 OHLC）                        |
//+------------------------------------------------------------------+
void ManagePositions(int cur_bar)
{
   int bar = cur_bar - 1;
   if(bar < 0) return;
   double o = g_h4_open[bar], hi = g_h4_high[bar], lo = g_h4_low[bar], cl = g_h4_close[bar];
   // 高取低：待定穿越点（cur_bar-1 = 上一根已收盘）
   bool has_pend = false;
   int pend_type = 0;
   double pend_stop = 0.0;
   if(g_cands_n > 0 && g_cands[g_cands_n-1].pos == bar)
   {
      has_pend = true;
      pend_type = g_cands[g_cands_n-1].type;
      pend_stop = g_cands[g_cands_n-1].stop;
   }

   for(int d = -1; d <= 1; d += 2)
   {
      int idx = PosIndex(d);
      if(!g_pos_open[idx]) continue;
      VPos p = g_pos[idx];
      p.hold++;
      if(p.hold >= InpTimeExitBars)
      {
         p.realized += (cl - p.entry) * d * p.frac_open;
         g_pos[idx] = p;
         ClosePosition(d, iTime(InpSymbol, PERIOD_H4, 1), cl, "time exit");
         continue;
      }
      double sc = p.stop;
      if(has_pend)
      {
         if(d == 1 && pend_type == 2 && pend_stop > 0.0 && pend_stop > sc && cl > p.entry)
            p.stop = MathMax(p.entry, pend_stop);
         if(d == -1 && pend_type == -2 && pend_stop > 0.0 && pend_stop < sc && cl < p.entry)
            p.stop = MathMin(p.entry, pend_stop);
         sc = p.stop;
      }
      // 止损
      if(d == 1 && lo <= sc)
      {
         double xp = MathMin(sc, o);
         p.realized += (xp - p.entry) * d * p.frac_open;
         g_pos[idx] = p;
         ClosePosition(d, iTime(InpSymbol, PERIOD_H4, 1), xp,
                       p.tp1_hit ? "TP1+SL" : "SL hit");
         continue;
      }
      if(d == -1 && hi >= sc)
      {
         double xp = MathMax(sc, o);
         p.realized += (xp - p.entry) * d * p.frac_open;
         g_pos[idx] = p;
         ClosePosition(d, iTime(InpSymbol, PERIOD_H4, 1), xp,
                       p.tp1_hit ? "TP1+SL" : "SL hit");
         continue;
      }
      // TP1
      if(!p.tp1_hit)
      {
         double tp1 = p.entry + InpTp1R * p.R * d;
         if((d == 1 && hi >= tp1) || (d == -1 && lo <= tp1))
         {
            p.realized += (tp1 - p.entry) * d * InpFrac1;
            p.frac_open -= InpFrac1;
            p.stop = p.entry;
            p.tp1_hit = true;
         }
      }
      g_pos[idx] = p;
   }
}

//+------------------------------------------------------------------+
//| OnInit / OnTick                                                  |
//+------------------------------------------------------------------+
int OnInit()
{
   g_virtual_balance = InpSimStartBalance;
   ArrayResize(g_cands, 20000);
   ArrayResize(g_arms, 500);
   ArrayResize(g_pos, 2);
   g_pos_open[0] = false; g_pos_open[1] = false;
   CsvLedgerHeader();
   UpdateH4State();
   Diag(TimeCurrent(), "init", 0, g_h4_n, "cands=" + IntegerToString(g_cands_n));
   return INIT_SUCCEEDED;
}

int g_tick_count = 0;
int g_bar_count = 0;
void OnTick()
{
   g_tick_count++;
   datetime t = iTime(InpSymbol, PERIOD_H4, 0);
   if(t == g_last_bar_time) return;   // 仅新 bar 处理
   g_last_bar_time = t;
   g_bar_count++;
   UpdateH4State();
   int cur = g_h4_n - 1;              // 当前 forming bar
   CheckD1AndArm(t);
   ManagePositions(cur);
   TryOpen(t, cur);
   if(g_bar_count % 500 == 0)
      Diag(t, "bar_progress", g_bar_count, g_h4_n, "cands=" + IntegerToString(g_cands_n));
}

void OnDeinit(const int reason)
{
   // 数据末尾平仓（与 Python end of data 一致；OnTesterDeinit 在单次测试可能不触发）
   if(g_h4_n > 0)
   {
      double cl = g_h4_close[g_h4_n - 1];
      datetime bt = iTime(InpSymbol, PERIOD_H4, 0);
      for(int d = -1; d <= 1; d += 2)
      {
         int idx = PosIndex(d);
         if(g_pos_open[idx])
         {
            VPos p = g_pos[idx];
            p.realized += (cl - p.entry) * d * p.frac_open;
            g_pos[idx] = p;
            ClosePosition(d, bt, cl, "end of data");
         }
      }
   }
}

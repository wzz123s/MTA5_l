# EA 接入方案：宏观日历实时事件感知（研究结论落地）

> 配套报告：`报告/宏观日历影响分析报告.md` ｜ 状态：**已实施（2026-08-26，默认关闭，待模拟盘验证）**

## 1. 结论回顾（决定了要做什么、不做什么）

| 策略 | 是否加事件过滤 | 是否事件平仓 | 备注（信号级完整重放结论） |
|---|---|---|---|
| 1H_M30_4H | ❌ 不建议（收益 -32%） | ❌ 否决 | 冷却（cd_post6+损失冷却120h）已部署，属风控工具 |
| 30m2H | ✅ 可选：高影响事件前 2h 不开仓 | ❌ 否决 | 收益代价仅 -3%，PF 2.20→2.46，MaxDD -30%（"免费保险"） |
| 2H_M30_6H | ✅ 可选：高影响事件前 1h 不开仓 | ❌ 否决 | 收益代价仅 -3%，PF 1.52→1.58，MaxDD -15% |
| BiasReversal / USOIL2H | ❌ 不加 | ❌ 否决 | 无改善（乖离反转做空侧冷却已内建） |
| **USOIL4H** | ✅ 候选：高影响事件前 **4h**（信号级复核修正：T=2h/4h 收益持平+PF 1.73→2.18，T=8h 会误伤 +9,061 边界赢单） | ❌ 否决 | EA 参数 InpEventFilterHrs 8→4，模拟盘验证 |
| 全部 | — | — | 可选风控：事件后 4h 内波动 3-4x，可放宽止损距离保护；冷却+事件过滤叠加会过度砍仓 |

## 1.5 数据获取机制（定期更新 + 下单前读缓存）

- **定期更新：** EA 用 OnTimer(60s) 拉取“未来 N 小时事件表”存入内存缓存（300s 内不重复查询）。事件时间表提前公布，缓存延迟无影响。
- **下单前只读缓存：** 信号接受时 EventBlackout() 只读内存布尔值，零网络调用。
- **原因：** 首次日历同步可阻塞数分钟（实测 5 分钟初始化超时），必须放 OnTimer；下单路径不可做网络调用。

## 1.6 币种白名单（策略定义，硬编码）

- 事件门只拦截 **USD / EUR / GBP / CAD** 的高影响事件（IsWhitelistedCurrency）
- 依据：USD=直接定价货币（实测 4.07x）；EUR+GBP=USDX 权重 70%（实测 2.6x）；CAD=油价货币
- 测试证据：东京CPI（JPY）对黄金 1.28x/原油 0.95x≈无影响，不再触发黑名单；被拦信号 25 笔中 USD+EUR 占 21 笔（均亏损）

## 2. MQL5 日历 API 可用性（已实测，build 6140）

- `CalendarValueHistory(MqlCalendarValue &values[], from, to)` — 获取事件值（含 actual/forecast/prev，数值为 ×1e6 整数）
- `CalendarEventById(event_id, MqlCalendarEvent&)` — 事件名称（本地化）、importance（0-3，3=高影响）、country_id 等
- `CalendarCountryById(country_id, MqlCalendarCountry&)` — 国家/币种
- **注意**：首次调用会阻塞等待日历数据同步（曾触发 5 分钟 OnInit 超时），**必须放在 OnTimer 中异步调用**，不要放在 OnInit
- `MqlCalendarValue.impact_type` 在本 build 恒为 0/1/2（非 HIGH），**高影响判定请用 `MqlCalendarEvent.importance == 3`**

## 3. EA 改造实现（2026-08-26 已部署）

三个 EA 已注入事件门（默认 InpEventFilterOn=false，行为不变）：

| EA | InpEventFilterHrs | 注入位置 |
|---|---|---|
| 30m2H_ABC_EA | 2 | 信号接受处（币种白名单已注入） |
| 2H_M30_6H_ABC_EA | 1 | 信号接受处 |
| USOIL4H_Gate_On2H_EA | 8 | 开仓 ok 条件 |

实现要点：OnTimer(60s) 异步刷新（**不在 OnInit 调日历 API**——首次调用会阻塞同步导致 5 分钟初始化超时）；
CalendarValueHistory(now, now+N*3600) 取未来 N 小时事件，CalendarEventById 判 importance>=3 即置黑名单；
300s 缓存；开关关闭时零日历调用、零行为变化。补丁脚本：scripts/patch_ea_event_gate.py。

### 3.1 参数（以 30m2H 为例）

### 3.1 参数
```mql5
input group "=== Macro Calendar Filter (research) ==="
input bool   InpEventFilterOn   = false;   // 事件过滤总开关（默认关，先模拟盘）
input int    InpEventFilterHrs  = 8;       // 高影响事件前 N 小时内不开新仓
input int    InpEventCheckEvery = 300;     // 日历刷新间隔（秒），避免频繁请求
```

### 3.2 逻辑（挂载在信号接受处，开仓前判断）
```mql5
// OnTimer 中周期刷新（异步，避免阻塞）
datetime g_cal_until = 0;          // 最近一次日历查询的缓存截止
bool     g_event_blackout = false; // 未来 N 小时内有高影响 USD 事件

void RefreshCalendarGate()
{
   if(!InpEventFilterOn) return;
   if(TimeCurrent() < g_cal_until) return;
   g_cal_until = TimeCurrent() + InpEventCheckEvery;

   MqlCalendarValue vals[];
   if(CalendarValueHistory(vals, TimeCurrent(), TimeCurrent() + InpEventFilterHrs * 3600) < 0)
      return;                       // 数据未就绪：保守放行（记录诊断）
   g_event_blackout = false;
   for(int i = 0; i < ArraySize(vals); i++)
   {
      MqlCalendarEvent ev;
      if(!CalendarEventById(vals[i].event_id, ev)) continue;
      if(ev.importance >= 3 && ev.country_id == <USD的country_id>)   // 或用 currency 判断
      {
         g_event_blackout = true;
         break;
      }
   }
}

// 在"接受信号"处：
if(g_event_blackout)
{
   Print("EventGate: 未来 ", InpEventFilterHrs, "h 内有高影响事件，跳过信号");
   return;   // 不开新仓
}
```

### 3.3 注意事项
1. **先模拟盘验证 2-4 周**：回测改善（PF 1.73→2.96）基于 72 笔样本，需实盘前向确认。
2. 日历请求限频：`CalendarValueHistory` 每次调用有网络开销，300s 缓存一次足够（事件时间表是提前发布的）。
3. 终端时区：日历 `time` 为 UTC 秒级时间戳，与项目 K 线时间口径一致（已用非农 12:30/13:30 UTC 验证），无需换算。
4. 事件过滤只针对"新开仓"，**不要**平仓已有持仓（V2 回测为灾难性结果）。
5. 若需对黄金策略做"事件感知风控"（可选），在事件前检查持仓止损距离 < 2×ATR 时放宽，而非平仓。

## 4. 可选增强（后续研究）

1. **surprise 方向一致性**：actual vs forecast 的方向与持仓方向一致时持有/加仓，相反时收紧——需先做回测研究。
2. **非农专项过滤**（2H_M30_6H p=0.015）：只对"非农就业"类事件做开仓过滤的小样本试验。
3. **年度稳健性**：按年拆分检验结论是否由少数年份驱动。


---

## 5. 部署记录（2026-08-26 00:32）

- 三个 EA 编译 0 errors（warning 39 为旧代码原有：tickets ulong 当布尔），ex5 已部署到终端 Experts\Advisors
- 终端重启后 8 个 EA 全部加载成功（含改版的 30m2H_ABC / 2H_M30_6H_ABC / USOIL4H_Gate_On2H）
- 默认参数全部关闭 → 实盘行为与部署前完全一致；开启方式：图表属性 → 输入 → Macro Calendar Filter 组 → InpEventFilterOn=true（建议先在模拟盘验证 2-4 周）
- 验证要点：开启后日志出现 [CAL] event blackout: ... 表示事件门生效；[CAL] signal blocked... 表示信号被拦截

## 6. 币种白名单部署记录（2026-08-27 19:37 UTC）

- 三个 EA（30m2H / 2H_M30_6H / USOIL4H）事件门已加 IsWhitelistedCurrency（USD/EUR/GBP/CAD 硬编码）
- 编译 0 errors，部署完成，终端重启后 8 EA 全部加载
- 东京CPI等 JPY 事件不再触发黑名单；USOIL4H 实盘事件门保持开启（T=4h）

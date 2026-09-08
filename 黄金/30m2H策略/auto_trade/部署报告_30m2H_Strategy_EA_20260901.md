# 30m2H Strategy EA 部署报告（2026-09-01）

## 部署内容

修复版 `30m2H_Strategy_EA.ex5`（v3.35 + 4 处 BUGFIX）覆盖部署，替换旧版（2026-08-25 编译）。

| 项目 | 值 |
| --- | --- |
| 二进制 | `30m2H_Strategy_EA.ex5`（154,162B，编译 2026-09-01 12:15:43 UTC，0 errors/0 warnings） |
| 修复内容 | post_n 计数器首调符号 bug + 信号方向复核 + CTrade magic + 止损方向校验（详见 `说明文档/03_验证结果/EA_v3.35修复与部署记录_20260901.md`） |
| 部署位置 | `MQL5\Experts\30m2H_Strategy_EA.ex5`（chart07, XAUUSDm M30） |
| Magic | 302036（三腿 302037/38/39） |
| 运行模式 | 不变：InpSimMode=false / InpAllowRealTrading=true（真实模式模拟盘） |
| 旧版备份 | 终端内 `30m2H_Strategy_EA.ex5.bak_v335_prebugfix_20260901`（152,994B）+ 项目 `auto_trade/30m2H_Strategy_EA.ex5.bak_v335_prebugfix_20260901` |

## 部署步骤（2026-09-01 20:47-20:51）

1. 备份终端旧 ex5 → `.bak_v335_prebugfix_20260901`；
2. 复制修复版 ex5 → `MQL5\Experts\30m2H_Strategy_EA.ex5`；
3. 终端重启：**explorer 托管**（`explorer.exe terminal64.exe`，PID 16424，20:51:25 启动）——
   注意：`Start-Process` 直启的终端会随沙箱 pwsh 进程退出被杀（第一次 20:49 启动即失败），须用 explorer 脱离进程树。

## 验证状态

- ✅ 编译：0 errors, 0 warnings（MetaEditor 命令行，`auto_trade/compile_prebugfix_check.log`）
- ✅ 文件复制：`MQL5\Experts\30m2H_Strategy_EA.ex5` 为修复版（mtime 12:15:43 UTC）
- ✅ 终端重启后日志（20:51:26.848）：`expert 30m2H_Strategy_EA (XAUUSDm,M30) loaded successfully`
- ✅ 账户连接：277752085 授权成功（Exness-MT5Trial5）
- ✅ 持仓完好：2 仓（1H_M30_4H SELL @4567.196 magic 312036；30m2H S1 BUY @4380.573 magic 302037）
- ⏳ 观察：下一信号/平仓起验证修复行为（观察项见修复记录第六节）

## 监控与回滚

监控：`observation_dashboard` 每 6 小时监测报告自动覆盖（30m2H 行）。

回滚：关闭 MT5 → 用 `30m2H_Strategy_EA.ex5.bak_v335_prebugfix_20260901` 覆盖
`MQL5\Experts\30m2H_Strategy_EA.ex5` → explorer 重启终端。

## 备注

- 修复仅影响信号方向判定/归因/止损校验，未改交易参数（门、spec、仓位、退出档位均不变）；
- 合并方向评估结论：维持无前视近似（延迟吸收回测更差），详见 `说明文档/合并方向对齐立项_20260901.md`。
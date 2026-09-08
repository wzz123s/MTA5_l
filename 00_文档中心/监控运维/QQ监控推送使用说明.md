# QQ 监控推送助手 — 使用与维护说明 (MTA5_l)

> 最后更新: 2026-09-08 ｜ 状态: 已上线运行（网关在线 / 快照与事件任务自动执行）
> 驱动方更正（2026-09-08 核实）：30 分钟监测循环由 DSH harness tool-jobs 驱动（非 Windows 计划任务），DSH Web 进程关闭则监测停摆；MTA5_alerts / MTA5_qq_digest 两任务在会话内无法枚举确认，仍待用户在任务计划程序复核。

## 一、系统架构

```
QQ 用户(你) ──C2C私聊──> 机器人mt5-i1905559335 (AppID 1905559335)
                            │  dsh --profile qqbot (网关 pwsh-8)            
                            │  = dsh-qqbot 插件 → dsh agent(LLM) 智能问答    
                            │                                             
监控数据源(自动) ──────────────────────────────────────────────┐           
  1) MT5 实盘(Exness 277752085): 账户/持仓每单SL TP/近72h成交      │           
  2) observation_dashboard: 9策略总览/警戒/信号/监测报告           │           
                                                                ▼           
  qq_snapshot.py (生成 qq_snapshot.json) ──> 问答/推送共用数据快照         
                                                                │           
  watch_signal_alerts.py (2分钟, 开仓/平仓/新信号)  ─┐              │         
  qq_digest_push.py       (30分钟, 总览推送)        ─┼─> notify_qq.mjs ─> 你的QQ
                                                   ┘  (REST直发)            
```

## 二、组件清单

| 组件 | 路径/位置 | 说明 |
|------|----------|------|
| QQ 网关 | dsh profile `qqbot`（~/.dsh/profiles/qqbot）+ 常驻进程 | 收发消息、智能问答入口 |
| 快照 | scripts/qq_snapshot.py | 读 MT5+dashboard 生成 observation_dashboard/qq_snapshot.json |
| 事件检测 | scripts/watch_signal_alerts.py | 持仓变化/新信号 → 提醒（幂等状态化） |
| 总览推送 | scripts/qq_digest_push.py | 每次刷新快照并推送文字总览 |
| 推送器 | scripts/notify_qq.mjs | QQ REST 主动消息（不占 WS 连接） |
| 推送配置 | scripts/qq_push_config.json | appId/appSecret/targetId(你的openid)/enabled |
| 计划任务 | MTA5_alerts(2min) / MTA5_qq_digest(30min) | Windows 任务计划自动运行 |
| 应答规范 | QQ_AGENT_INSTRUCTIONS.md | QQ 智能体回答规则（指令→动作映射） |

## 三、你(用户)在 QQ 里能做什么

- 发「状态 / 总览 / 监控」→ 账户余额/净值/持仓/策略警戒摘要
- 发「持仓 / 仓位」→ 每单: 开仓/现价/止损/止盈/浮盈
- 发「成交 / 最近交易」→ 近72h成交与净盈亏
- 发「信号」→ 各策略最新方向/时间/模式
- 发「报告」→ 最新监测报告摘要
- 机器人默认只回精简结论，需要你决策时才提问（一次一个）

## 四、主动推送（你无需操作，自动到达）

- 每 30 分钟: 监控总览（账户+持仓+策略+警戒）
- 实时(每2分钟轮询): 新开仓🟢 / 平仓🔴 / 新策略信号📡 即时提醒
- 平仓提醒含策略归属；止盈/止损判定可后续在快照中补 deal reason 增强

## 五、常用维护命令（在 F:\use_code\MTA5_l 下）

```powershell
# 立即刷新并推送一份总览（等价于30分钟任务）
python scripts\qq_digest_push.py

# 只刷新快照不推送
python scripts\qq_snapshot.py

# 手动跑一轮事件检测
python scripts\watch_signal_alerts.py

# 查看/编辑推送目标
notepad scripts\qq_push_config.json     # targetId = 你的QQ openid

# 查看推送日志
Get-Content scripts\alerts\qq_push.log -Tail 20

# 启动/停止 QQ 网关
dsh --profile qqbot                      # 前台（或做成计划任务/开机自启）
# 停止: 关掉对应进程即可
```

## 六、故障排查

| 现象 | 原因与处理 |
|------|-----------|
| 机器人不回复 | 1)网关未运行→启动 dsh --profile qqbot; 2)QQ侧沙箱白名单/IP→q.qq.com后台把本机公网IP(查 ip.sb)加入体验白名单并勾选C2C私聊事件 |
| 主动推送失败 | 查 scripts/alerts/qq_push.log 的 push_failed 记录; 主动消息有平台额度/窗口限制，超窗时按日志降级; 你在会话内消息后推送成功率最高 |
| 快照 MT5 失败 | MT5 终端未运行或登录失效; 运行 python scripts/qq_snapshot.py 看 mt5_live.error |
| 改机器人性格/范围 | 编辑 ~/.dsh/profiles/qqbot/cordis.patch.yml 中 directPrompt/groupPrompt → 保存即热更新 |

## 七、安全与合规提示

- 推送目标固定为你自己的 QQ（openid 已绑定），勿外泄 qq_push_config.json 与 appSecret
- MT5 为试用/模拟环境时，推送数字以实际账户为准；机器人禁止编造（已内置规范）
- 若日后启用实盘 EA 自动交易，建议收紧机器人权限并复查应答规范

## 八、验收清单（截至 2026-09-05）

- [x] 扫码绑定 + 网关在线（READY）
- [x] 私聊入站/出站双向通（C2C 实测 200）
- [x] 主动推送通（总览 HTTP 200）
- [x] 事件提醒链路（平仓事件模拟验证）
- [x] 定时总览推送通（HTTP 200）
- [x] 计划任务自动运行（LastTaskResult=0）
- [ ] 待你确认: 手机收到推送 + 智能问答回复正常

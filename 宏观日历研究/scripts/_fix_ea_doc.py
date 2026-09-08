
from pathlib import Path
p = Path(r"F:\use_code\MTA5_l\宏观日历研究\报告\EA接入方案.md")
text = p.read_text(encoding="utf-8")
old = """| 策略 | 是否加事件过滤 | 是否事件平仓 | 备注 |
|---|---|---|---|
| 1H_M30_4H / 30m2H / 2H_M30_6H / BiasReversal / USOIL2H | ❌ 不加（会砍利润） | ❌ 否决 | 事件窗口内交易是主要利润来源 |
| **USOIL4H** | ✅ 候选：高影响事件前 8h 不开新仓 | ❌ 否决 | 回测 PF 1.73→2.96，MaxDD -38%，待前向验证 |
| 全部 | — | — | 可选风控：事件后 4h 内波动 3-4x，可放宽止损距离保护 |"""
new = """| 策略 | 是否加事件过滤 | 是否事件平仓 | 备注（信号级完整重放结论） |
|---|---|---|---|
| 1H_M30_4H | ❌ 不建议（收益 -32%） | ❌ 否决 | 冷却（cd_post6+损失冷却120h）已部署，属风控工具 |
| 30m2H | ✅ 可选：高影响事件前 2h 不开仓 | ❌ 否决 | 收益代价仅 -3%，PF 2.20→2.46，MaxDD -30%（"免费保险"） |
| 2H_M30_6H | ✅ 可选：高影响事件前 1h 不开仓 | ❌ 否决 | 收益代价仅 -3%，PF 1.52→1.58，MaxDD -15% |
| BiasReversal / USOIL2H | ❌ 不加 | ❌ 否决 | 无改善（乖离反转做空侧冷却已内建） |
| **USOIL4H** | ✅ 候选：高影响事件前 8h 不开新仓 | ❌ 否决 | PF 1.73→2.96，MaxDD -38%（信号即交易，结论可靠），待模拟盘前向验证 |
| 全部 | — | — | 可选风控：事件后 4h 内波动 3-4x，可放宽止损距离保护；冷却+事件过滤叠加会过度砍仓 |"""
assert old in text
p.write_text(text.replace(old, new), encoding="utf-8")
print("EA doc table updated")

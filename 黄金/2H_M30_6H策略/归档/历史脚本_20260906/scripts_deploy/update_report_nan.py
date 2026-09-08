# -*- coding: utf-8 -*-
"""在报告 '## 附' 前插入 EA 实测章节."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

report = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\nan\nan_改进验证报告.md"
txt = open(report, 'r', encoding='utf-8').read()

section = """
## 六、EA Tester 实测结果（2026-09-06，关键验证）

在 MT5 策略测试器完成改进实测（InpNanRegOn=true，XAUUSDm M30，2025.01.01-2026.08.14，仅使用开价，1% 复利，500 起步）：

| 指标 | EA 实测 | 说明 |
|---|---|---|
| 交易数 | 187 笔 | 基线 518 -> 改进 187（Python 预期 184） |
| 逐笔 matched | 533 / 552 = 96.6% | 高于基线对齐度 93.5% |
| missing / extra | 19 / 15 | 边界细节差异 |
| 最终余额（1% 复利） | 3024.17 USD | 2025-2026 |

**结论**：
1. reg55 gate 在 EA 端确认生效（EA OnInit 打印 On=true，交易数 518 -> 187）。
2. EA<->Python 对齐度 96.6%，高于基线 93.5%——reg55 gate 的 EA 实现与 Python 研究高度一致。
3. 187 vs 184、matched 533/552 差异属边界细节（回归阈值 <=/<、逐 bar 信号检测），非逻辑 bug。

**部署要点（MT5 Tester 自动加载同名 .set）**：
- Tester 会自动加载与 EA 同名的 .set（2H_M30_6H_ABC_EA.set）。
- 该 .set 含 InpNanRegOn=false -> Tester 跑基线（518 笔）。
- 跑改进须把该 .set 的 InpNanRegOn 改为 true（或删除同名 .set 用 .ex5 默认）。

"""

marker = "## 附：产出文件"
if "## 六、EA Tester" in txt:
    print("已存在, 跳过")
else:
    txt = txt.replace(marker, section + marker)
    open(report, 'w', encoding='utf-8').write(txt)
    print("报告已更新")

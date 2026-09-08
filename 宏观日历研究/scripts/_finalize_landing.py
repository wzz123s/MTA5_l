# -*- coding: utf-8 -*-
from pathlib import Path

# 1) 行动项复核.md 追加落地记录
p = Path(r"F:\use_code\MTA5_l\宏观日历研究\报告\行动项复核.md")
text = p.read_text(encoding="utf-8")
text += """

---

## 落地执行记录（2026-08-27 19:26 UTC）

| 行动项 | 执行内容 | 状态 |
|---|---|---|
| 1. USOIL4H 事件门 | 源码默认 InpEventFilterOn=true、InpEventFilterHrs=4；chart09.chr 显式传参（备份 .bak_eventgate_20260827） | ✅ 编译部署，终端重启后 8 EA 正常加载 |
| 2. 1H_M30_4H post_n 降档 | **确认早已部署**：源码默认 InpDropPostN5=true/InpDropPostN6=true + chart03 显式传参（实盘只做 post_n2-4）；本次信号级复核（PF 1.47→1.64、MaxDD -31%、2026 +41%）验证了该部署正确 | ✅ 无需改动（口径说明：Python 监控重放 572 笔含 post_n5/6，与实盘 EA 行为有差异，属已知口径差异） |
| 3. BiasReversal 做空侧 | 新增 InpEnableShort=false（源码默认停用做空）；做空开仓条件加开关；chart10.chr 显式传参（备份 .bak_shortoff_20260827）；已有空单继续按规则管理 | ✅ 编译部署，现有实盘空单（magic 372037，浮盈 +$63）不受影响 |

验证要点（用户可在终端 UI 工具箱→专家标签查看）：
- USOIL4H：当未来 4h 内有高影响事件时，日志出现 [CAL] event blackout: <事件名>；事件前 4h 内的信号在 signals CSV 记为 SKIP
- BiasReversal：做空信号不再产生（若 H4 超涨门触发，也不开空单）
- 恢复方法：USOIL4H 把 InpEventFilterOn 改 false；BiasReversal 把 InpEnableShort 改 true（或改 chart09/chart10 配置后重启）
"""
p.write_text(text, encoding="utf-8")
print("action review appended")

# 2) 计划文档状态
p2 = Path(r"F:\use_code\MTA5_l\宏观日历研究\计划_宏观数据影响测试.md")
t2 = p2.read_text(encoding="utf-8")
t2 = t2.replace(
    "- \u2b1c \u540e\u7eed\uff1a\u4e8b\u4ef6\u8fc7\u6ee4\u6a21\u62df\u76d8\u524d\u5411\u9a8c\u8bc1\uff082-4 \u5468\uff09\uff1bsurprise \u65b9\u5411\u4e00\u81f4\u6027\u7814\u7a76\uff1b2H_M30_6H \u975e\u519c\u4e13\u9879\u8fc7\u6ee4\u8bd5\u9a8c",
    "- \u2705 **\u4e09\u4e2a\u843d\u5730\u52a8\u4f5c\u5df2\u6267\u884c\uff082026-08-27\uff09**\uff1a\u2460 USOIL4H \u4e8b\u4ef6\u95e8\u5f00\u542f T=4h\uff08\u4fe1\u53f7\u7ea7\u590d\u6838\u540e\u4fee\u6b63\uff09\uff1b\u2461 1H_M30_4H post_n \u964d\u6863\u786e\u8ba4\u5df2\u90e8\u7f72\uff08InpDropPostN5/6=true\uff09\uff1b\u2462 BiasReversal \u505c\u7528\u505a\u7a7a\u5206\u652f\uff08InpEnableShort=false\uff09\u2014\u2014\u5747\u7f16\u8bd1\u90e8\u7f72\u5b8c\u6210\uff0c8 EA \u6b63\u5e38\u52a0\u8f7d\n- \u2b1c \u540e\u7eed\uff1a\u4e8b\u4ef6\u95e8\u5b9e\u76d8\u524d\u5411\u89c2\u5bdf\uff082-4 \u5468\uff09\uff1bsurprise \u65b9\u5411\u4e00\u81f4\u6027\u7814\u7a76\uff1b2H_M30_6H \u975e\u519c\u4e13\u9879\u8fc7\u6ee4\u8bd5\u9a8c")
p2.write_text(t2, encoding="utf-8")
print("plan updated")

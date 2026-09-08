# -*- coding: utf-8 -*-
"""三个落地动作执行：
1) USOIL4H: InpEventFilterOn=true, InpEventFilterHrs=8->4（源码默认 + chart09显式）
2) 1H_M30_4H: 已部署（InpDropPostN5/6=true 源码默认+chart03），无需改动
3) BiasReversal: 新增 InpEnableShort=false 停用做空分支（源码 + chart10显式）
"""
from pathlib import Path

EDITS = []

# ---- 1) USOIL4H 源码 ----
p = Path(r"F:\use_code\MTA5_l\原油\原油4H门策略\auto_trade\USOIL4H_Gate_On2H_EA.mq5")
t = p.read_text(encoding="utf-8")
o1 = "input bool   InpEventFilterOn   = false;  // 事件过滤总开关（默认关，先模拟盘）"
n1 = "input bool   InpEventFilterOn   = true;   // 事件过滤总开关（信号级复核 T=4h：收益持平+PF 1.73->2.18+MaxDD-21%）"
assert t.count(o1) == 1
t = t.replace(o1, n1)
o2 = "input int    InpEventFilterHrs  = 8;  // 高影响事件前 N 小时内不开新仓"
n2 = "input int    InpEventFilterHrs  = 4;  // 高影响事件前 N 小时内不开新仓（复核修正：8h 会误伤边界赢单）"
assert t.count(o2) == 1
t = t.replace(o2, n2)
p.write_text(t, encoding="utf-8")
print("[1] USOIL4H 源码: InpEventFilterOn=true, InpEventFilterHrs=4")

# ---- 3) BiasReversal 源码 ----
p = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\auto_trade\BiasReversal_Combo_EA.mq5")
t = p.read_text(encoding="utf-8")
o3 = "input int     InpShortCdHours = 120;      // 冷却时长（小时）"
n3 = o3 + """

input group "=== 做空开关（研究落地 2026-08-27）==="
input bool    InpEnableShort   = false;    // 做空分支总开关（信号级复核：做空侧 24笔仅+787pts/PF1.01，停用后整体 MaxDD -44%）
"""
assert t.count(o3) == 1
t = t.replace(o3, n3)
o4 = "      if(!PositionSelectByMagic(InpMagicShort) && TimeCurrent() >= g_short_cd_until)"
n4 = "      if(InpEnableShort && !PositionSelectByMagic(InpMagicShort) && TimeCurrent() >= g_short_cd_until)"
assert t.count(o4) == 1
t = t.replace(o4, n4)
p.write_text(t, encoding="utf-8")
print("[3] BiasReversal 源码: InpEnableShort=false + 做空开仓条件已加开关")

# ---- 图表配置 ----
charts = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Charts\Default")
def patch_chr(name, add_lines, backup_tag):
    f = charts / name
    bak = charts / (name + ".bak_" + backup_tag)
    if not bak.exists():
        bak.write_bytes(f.read_bytes())
    text = f.read_bytes().decode("utf-16")
    lines = text.split("\r\n")
    out = []
    added = False
    for ln in lines:
        out.append(ln)
        if ln.strip() == "<inputs>" and not added:
            for a in add_lines:
                out.append(a)
            added = True
    text = "\r\n".join(out)
    f.write_bytes(text.encode("utf-16"))
    print(f"[cfg] {name}: +{len(add_lines)} lines ({', '.join(a.split('=')[0] for a in add_lines)})")

patch_chr("chart09.chr",
          ["InpEventFilterOn=true", "InpEventFilterHrs=4"],
          "eventgate_20260827")
patch_chr("chart10.chr",
          ["InpEnableShort=false"],
          "shortoff_20260827")
print("charts patched")

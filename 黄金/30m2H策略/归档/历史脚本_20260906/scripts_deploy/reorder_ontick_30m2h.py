# -*- coding: utf-8 -*-
"""重排 30m2H OnTick: open pending 移到信号检测后 (P2-5)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

ea30 = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5"
src = open(ea30, encoding='utf-8').read()

# 定位 open pending 块: 从注释到 "g_pending = false;\n   }"
start_marker = "   // 1) open pending signal at current bar open"
start = src.index(start_marker)
# 找到块结束: start 后的第一个 "g_pending = false;" + 其后的 "\n   }"
pend_end_marker = "      g_pending = false;"
pe_idx = src.index(pend_end_marker, start)
# 找 pe_idx 后的 "\n   }" 结束
close_idx = src.index("\n   }", pe_idx) + len("\n   }")

block = src[start:close_idx]
print("open pending 块长度:", len(block))
print("块开头:", block[:60].replace("\n","\\n"))
print("块结尾:", block[-60:].replace("\n","\\n"))

# 从 src 删除块
src2 = src[:start] + src[close_idx:]

# 在 "if(InpExportCSV)" 前插入块 (信号检测 + set pending 后)
insert_marker = "   if(InpExportCSV)"
ins_idx = src2.index(insert_marker)
block2 = "   // 3) open pending at current bar open (P2-5: 移到信号检测后, 不晚1bar)\n" + block[block.index("   if(g_pending)"):]
src2 = src2[:ins_idx] + block2 + "\n\n" + src2[ins_idx:]

open(ea30, 'w', encoding='utf-8').write(src2)
print("OnTick 已重排")

# -*- coding: utf-8 -*-
"""修复: 移除 OnInit 误插块, 插到 OnTick 正确位置."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

ea30 = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5"
src = open(ea30, encoding='utf-8').read()

# 1) 定位 OnInit 误插块 (含注释头)
start_marker = "   // 3) open pending at current bar open (P2-5"
start = src.index(start_marker)
block_end_marker = "      g_pending = false;\n   }"
be = src.index(block_end_marker, start)
end = be + len(block_end_marker)
# 块内容 = if(g_pending) 开头的块
block_start_in = src.index("   if(g_pending)", start)
open_block = src[block_start_in:end]
print("open_block len:", len(open_block))

# 2) 从 OnInit 删除误插整段 (注释头到块结束 + 可能空行)
remove_end = end
# 删除后可能留 \n\n, 处理
src2 = src[:start] + src[remove_end:]

# 3) 在 OnTick 的 CSV (FileOpen g_signals_csv) 前插入
ins_marker = "   if(InpExportCSV)\n   {\n      int h = FileOpen(g_signals_csv"
ins = src2.index(ins_marker)
insertion = "   // 3) open pending at current bar open (P2-5: 移到信号检测后, 当前bar开盘立即入场)\n" + open_block + "\n\n"
src2 = src2[:ins] + insertion + src2[ins:]

open(ea30, 'w', encoding='utf-8').write(src2)
print("修复完成")

# 验证结构
import re
for pat in ['int OnInit', 'void OnTick', 'open pending at current bar open', 'void OnDeinit']:
    print(pat, "->", len(re.findall(re.escape(pat), src2)), "处")

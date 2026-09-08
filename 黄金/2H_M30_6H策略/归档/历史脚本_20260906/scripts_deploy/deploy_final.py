# -*- coding: utf-8 -*-
"""部署最终版 ex5 + 恢复基线 set (os.path.join)."""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')

ws = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade"
dst_base = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"

ex5_dst = os.path.join(dst_base, "MQL5", "Experts", "Advisors", "2H_M30_6H_ABC_EA.ex5")
shutil.copy2(os.path.join(ws, "2H_M30_6H_ABC_EA.ex5"), ex5_dst)
print("ex5 已部署:", os.path.getmtime(ex5_dst))

set_dst = os.path.join(dst_base, "MQL5", "Profiles", "Tester", "2H_M30_6H_ABC_EA.set")
shutil.copy2(os.path.join(ws, "2H_M30_6H_ABC_SimDeployment_EA.set"), set_dst)
print("基线 set 已恢复")

txt = open(set_dst, encoding='utf-8').read()
for l in txt.split('\n'):
    if 'InpNanReg' in l or 'InpM30SMA55' in l:
        print("  set:", l.strip())

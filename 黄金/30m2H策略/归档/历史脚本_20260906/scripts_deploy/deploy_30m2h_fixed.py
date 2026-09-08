# -*- coding: utf-8 -*-
"""部署新 ex5 到 DAD3."""
import os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
ws = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade"
dst = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
shutil.copy2(os.path.join(ws, "30m2H_ABC_EA.ex5"), os.path.join(dst, "MQL5", "Experts", "Advisors", "30m2H_ABC_EA.ex5"))
print("新 ex5 已部署")

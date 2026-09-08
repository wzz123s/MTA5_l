# -*- coding: utf-8 -*-
"""部署新 ex5 + 跑 Tester."""
import os, shutil, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8')
ws = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade"
dst = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
shutil.copy2(os.path.join(ws, "30m2H_ABC_EA.ex5"), os.path.join(dst, "MQL5", "Experts", "Advisors", "30m2H_ABC_EA.ex5"))
print("ex5 部署 OK")
# 跑 Tester (run_dad3_30m2h.py 检查 EA + 点开始)
r = subprocess.run(["python", os.path.join(ws, "..", "scripts", "deploy", "run_dad3_30m2h.py")], capture_output=True, text=True)
# subprocess 管道可能被沙箱限制, 改为直接提示
print("请手动运行 run_dad3_30m2h.py")

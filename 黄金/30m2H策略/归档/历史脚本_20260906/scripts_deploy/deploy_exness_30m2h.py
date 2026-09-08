# -*- coding: utf-8 -*-
"""部署 30m2H 到 B695BCB6 + 启动 EXNESS."""
import sys, os, shutil, subprocess, time
sys.stdout.reconfigure(encoding='utf-8')

ws = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade"
dst = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"

shutil.copy2(os.path.join(ws, "30m2H_ABC_EA.ex5"), os.path.join(dst, "MQL5", "Experts", "Advisors", "30m2H_ABC_EA.ex5"))
print("ex5 部署 OK")
shutil.copy2(os.path.join(ws, "30m2H_ABC_EA.set"), os.path.join(dst, "MQL5", "Profiles", "Tester", "30m2H_ABC_EA.set"))
print("set 部署 OK")

# 确认 XAUUSDm 数据 (H2/M30)
hist = os.path.join(dst, "bases")
if os.path.exists(hist):
    for root, dirs, files in os.walk(hist):
        for f in files:
            if "XAUUSDm" in f:
                print("  数据文件:", os.path.join(root, f))
else:
    print("无 bases 目录")

# 启动 EXNESS
subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
time.sleep(2)
subprocess.Popen([r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"])
print("EXNESS 启动中, 等 45 秒...")
time.sleep(45)
print("done")

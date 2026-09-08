# -*- coding: utf-8 -*-
import sys, subprocess, os, time
sys.stdout.reconfigure(encoding='utf-8')

EA = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.mq5"
LOG = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\compile_bug11.log"
ME = r"F:\Program Files\MetaTrader 5\MetaEditor64.exe"

# 编译
cmd = [ME, '/compile:"%s"' % EA, '/log:"%s"' % LOG]
print("编译命令:", " ".join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True)
print("returncode:", r.returncode)
time.sleep(2)

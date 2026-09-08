# -*- coding: utf-8 -*-
"""EA状态快速检查 - 双击运行即可"""
import os
from datetime import datetime

BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"

print("=" * 55)
print("📊 1H_M30_4H EA 部署状态检查")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 55)

# 检查文件
files = [
    ("EA程序", f"{BASE}\MQL5\Experts\1H_M30_4H_CurrentCandidate_EA.ex5"),
    ("参数包", f"{BASE}\MQL5\Presets\1H_M30_4H_SimDeployment_EA.set"),
]

all_ok = True
for name, path in files:
    ok = os.path.exists(path)
    icon = "✅" if ok else "❌"
    print(f"{icon} {name}: {'已就位' if ok else '缺失!'}")
    all_ok = all_ok and ok

# 检查日志
log_dir = f"{BASE}\logs"
if os.path.exists(log_dir):
    logs = sorted(
        [f for f in os.listdir(log_dir) if f.endswith('.log')],
        key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
        reverse=True
    )
    print(f"\n📋 最近日志文件:")
    for lf in logs[:3]:
        fp = os.path.join(log_dir, lf)
        size = os.path.getsize(fp)
        mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%H:%M:%S")
        print(f"   📄 {lf} ({size:,} bytes) - {mtime}")

print("\n" + "=" * 55)
if all_ok:
    print("✅ 文件检查通过！可以在MT5中加载EA")
else:
    print("❌ 缺少必需文件！请先运行部署脚本")
print("=" * 55)
input("\n按回车键退出...")

# -*- coding: utf-8 -*-
"""运行Strategy Tester并检查结果"""

import time
import os
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 55)
    log("运行Strategy Tester (v1.01测试)")
    log("=" * 55)

    desktop = Desktop(backend="uia")

    # 找MT5窗口
    mt5_win = None
    for w in desktop.windows():
        t = w.window_text()
        if "Exness" in t and "MetaTrader" not in t:
            mt5_win = w
            break

    if not mt5_win:
        log("MT5未找到", "ERROR")
        return False

    mt5_app = Application(backend="uia").connect(handle=mt5_win.handle)
    mt5 = mt5_app.window(handle=mt5_win.handle)

    # 打开Strategy Tester
    log("打开Strategy Tester (Ctrl+R)...")
    mt5.set_focus()
    time.sleep(1)
    send_keys("^r")
    time.sleep(3)

    # 尝试启动
    log("启动Tester...")
    send_keys("{ENTER}")

    # 检查多个位置的ledger文件
    mt5_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
    common_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\Common\Files"

    ledger_locations = [
        ("MQL5/Files", os.path.join(mt5_dir, "MQL5", "Files", "2H_M30_6H_current_candidate_trade_ledger.csv")),
        ("Common/Files", os.path.join(common_dir, "2H_M30_6H_current_candidate_trade_ledger.csv")),
    ]

    log("等待回测完成...")
    log(f"检查位置: {[name for name, _ in ledger_locations]}", "INFO")

    for i in range(180):  # 最多等3分钟
        time.sleep(1)
        for name, path in ledger_locations:
            if os.path.exists(path):
                size = os.path.getsize(path)
                if size > 50:
                    log(f"检测到ledger! [{name}] {size} bytes ({i+1}s)", "SUCCESS")
                    try:
                        with open(path, "r") as f:
                            content = f.read()
                        lines = content.strip().split("\n")
                        log(f"交易笔数: {len(lines) - 1}", "SUCCESS")
                        for line in lines[:5]:
                            log(f"  {line}", "INFO")
                    except:
                        pass
                    return True

        if i % 30 == 29:
            log(f"回测中... ({i+1}s)")

    log("3分钟内未检测到ledger", "WARNING")
    log("可能原因:", "INFO")
    log("  1. EA初始化失败 (H6 handle创建失败)", "INFO")
    log("  2. 回测仍在进行中", "INFO")
    log("  3. Tester未正确启动", "INFO")

    # 最后检查所有位置
    log("\n=== 最终检查 ===", "INFO")
    for name, path in ledger_locations:
        if os.path.exists(path):
            log(f"  [{name}] {os.path.getsize(path)} bytes - {time.ctime(os.path.getmtime(path))}", "INFO")
        else:
            log(f"  [{name}] 不存在", "INFO")

    return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 55)
    if success:
        print("检测到交易数据!")
    else:
        print("未检测到交易数据")
    print("=" * 55)

# -*- coding: utf-8 -*-
"""编译v1.03并运行Tester - 全自动"""

import time
import os
import shutil
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 55)
    log("v1.03 编译 + Tester 全自动")
    log("=" * 55)

    desktop = Desktop(backend="uia")
    mt5_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
    v103_file = os.path.join(mt5_dir, "MQL5", "Experts", "2H_M30_6H_EA_v103.mq5")
    v103_ex5 = v103_file.replace(".mq5", ".ex5")
    target_ex5 = os.path.join(mt5_dir, "MQL5", "Experts", "2H_M30_6H_CurrentCandidate_EA.ex5")

    # === Step 1: 在MetaEditor中打开v1.03文件 ===
    log("[1/5] 在MetaEditor中打开v1.03...")
    me_win = None
    for w in desktop.windows():
        if "MetaEditor" in w.window_text() and "Debugging" not in w.window_text():
            me_win = w
            break

    if not me_win:
        log("MetaEditor未运行", "ERROR")
        return False

    me_app = Application(backend="uia").connect(handle=me_win.handle)
    me = me_app.window(handle=me_win.handle)
    me.set_focus()
    time.sleep(0.5)

    # Ctrl+O 打开文件
    send_keys("^o")
    time.sleep(2)

    for dlg_title in ["Open", "打开"]:
        try:
            dlg = me_app.window(title=dlg_title)
            if dlg.exists(timeout=3):
                ed = dlg.child_window(control_type="Edit", found_index=0)
                if ed.exists(timeout=2):
                    ed.set_focus()
                    ed.set_text(v103_file)
                    time.sleep(0.5)
                    send_keys("{ENTER}")
                    log("v1.03文件已打开", "SUCCESS")
                    time.sleep(3)
                break
        except:
            continue

    log(f"窗口: {me_win.window_text()}")

    # === Step 2: 编译 (F7) ===
    log("[2/5] 编译 (F7)...")
    start = time.time()
    me.set_focus()
    time.sleep(0.3)
    send_keys("{F7}")

    for i in range(30):
        time.sleep(1)
        if os.path.exists(v103_ex5):
            mtime = os.path.getmtime(v103_ex5)
            if mtime > start:
                size = os.path.getsize(v103_ex5)
                log(f"编译成功! {size:,} bytes ({i+1}s)", "SUCCESS")
                # 复制到目标位置
                shutil.copy2(v103_ex5, target_ex5)
                log(f"已复制到: {target_ex5}", "SUCCESS")
                break
        if i % 5 == 4:
            log(f"编译中... ({i+1}s)")
    else:
        log("编译超时 - v1.03可能有错误", "ERROR")
        return False

    # === Step 3: 在MT5中运行Tester ===
    log("[3/5] 运行Strategy Tester...")
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
    mt5.set_focus()
    time.sleep(1)
    send_keys("^r")  # Ctrl+R
    time.sleep(3)
    send_keys("{ENTER}")  # 启动
    log("Tester已启动", "SUCCESS")

    # === Step 4: 等待ledger文件 ===
    log("[4/5] 等待回测完成...")
    ledger = os.path.join(mt5_dir, "MQL5", "Files", "2H_M30_6H_current_candidate_trade_ledger.csv")

    for i in range(300):
        time.sleep(1)
        if os.path.exists(ledger):
            size = os.path.getsize(ledger)
            if size > 50:
                log(f"检测到ledger! {size} bytes ({i+1}s)", "SUCCESS")
                with open(ledger, "r") as f:
                    content = f.read()
                lines = content.strip().split("\n")
                log(f"交易笔数: {len(lines) - 1}", "SUCCESS")
                for line in lines[:5]:
                    log(f"  {line}", "INFO")
                return True
        if i % 30 == 29:
            log(f"回测中... ({i+1}s)")

    log("5分钟内未检测到ledger", "WARNING")
    return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 55)
    if success:
        print("成功！检测到交易数据!")
    else:
        print("未成功")
    print("=" * 55)

# -*- coding: utf-8 -*-
"""关闭文件 → 重新打开 → 编译 → Tester"""

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
    log("关闭→重开→编译→Tester")
    log("=" * 55)

    desktop = Desktop(backend="uia")
    mt5_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
    ex5_path = os.path.join(mt5_dir, "MQL5", "Experts", "2H_M30_6H_CurrentCandidate_EA.ex5")

    # 找MetaEditor
    me_win = None
    for w in desktop.windows():
        if "MetaEditor" in w.window_text() and "Debugging" not in w.window_text():
            me_win = w
            break

    if not me_win:
        log("MetaEditor未找到", "ERROR")
        return

    app = Application(backend="uia").connect(handle=me_win.handle)
    me = app.window(handle=me_win.handle)
    log(f"当前: {me_win.window_text()}")

    # Step 1: 关闭当前文件 (Ctrl+F4)
    log("[1] 关闭当前文件 (Ctrl+F4)...")
    me.set_focus()
    time.sleep(0.3)
    send_keys("^{F4}")
    time.sleep(2)
    log(f"关闭后: {me_win.window_text()}")

    # Step 2: 从导航器重新打开文件
    log("[2] 从导航器重新打开文件...")
    nav = me.child_window(title="导航器", control_type="Pane")
    if not nav.exists(timeout=3):
        # 尝试显示导航器
        send_keys("^n")  # Ctrl+N 可能切换导航器
        time.sleep(1)
        nav = me.child_window(title="导航器", control_type="Pane")

    if nav.exists(timeout=3):
        tree = nav.child_window(control_type="Tree")
        if tree.exists(timeout=3):
            # 查找文件项
            ea_item = tree.child_window(title="2H_M30_6H_CurrentCandidate_EA.mq5", control_type="TreeItem")
            if ea_item.exists(timeout=3):
                ea_item.double_click_input()
                log("文件已重新打开", "SUCCESS")
                time.sleep(3)
            else:
                log("未直接找到文件项，尝试展开目录...", "WARNING")
                # 展开Experts
                experts = tree.child_window(title="Experts", control_type="TreeItem")
                if experts.exists(timeout=2):
                    experts.click_input()
                    time.sleep(0.5)
                    # 展开Advisors
                    advisors = tree.child_window(title="Advisors", control_type="TreeItem")
                    if advisors.exists(timeout=2):
                        advisors.click_input()
                        time.sleep(0.5)
                        ea_item = tree.child_window(title="2H_M30_6H_CurrentCandidate_EA.mq5", control_type="TreeItem")
                        if ea_item.exists(timeout=2):
                            ea_item.double_click_input()
                            log("文件已打开(展开后)", "SUCCESS")
                            time.sleep(3)
                        else:
                            log("Advisors下未找到文件", "ERROR")
                            return
                    else:
                        log("未找到Advisors", "ERROR")
                        return
                else:
                    log("未找到Experts", "ERROR")
                    return
        else:
            log("未找到Tree", "ERROR")
            return
    else:
        log("未找到导航器", "ERROR")
        return

    log(f"打开后: {me_win.window_text()}")

    # Step 3: 编译 (F7)
    log("[3] 编译 (F7)...")
    start = time.time()
    me.set_focus()
    time.sleep(0.5)
    send_keys("{F7}")

    for i in range(30):
        time.sleep(1)
        if os.path.exists(ex5_path):
            mtime = os.path.getmtime(ex5_path)
            if mtime > start:
                size = os.path.getsize(ex5_path)
                log(f"编译成功! {size:,} bytes ({i+1}s)", "SUCCESS")

                # Step 4: 运行Tester
                log("[4] 运行Strategy Tester...")
                mt5_win = None
                for w in desktop.windows():
                    t = w.window_text()
                    if "Exness" in t and "MetaTrader" not in t:
                        mt5_win = w
                        break

                if mt5_win:
                    mt5_app = Application(backend="uia").connect(handle=mt5_win.handle)
                    mt5 = mt5_app.window(handle=mt5_win.handle)
                    mt5.set_focus()
                    time.sleep(1)
                    send_keys("^r")  # Ctrl+R
                    time.sleep(3)
                    send_keys("{ENTER}")
                    log("Tester已启动", "SUCCESS")

                    # 等待ledger
                    ledger = os.path.join(mt5_dir, "MQL5", "Files", "2H_M30_6H_current_candidate_trade_ledger.csv")
                    log("等待ledger文件...")
                    for j in range(300):
                        time.sleep(1)
                        if os.path.exists(ledger):
                            sz = os.path.getsize(ledger)
                            if sz > 50:
                                log(f"检测到ledger! {sz} bytes ({j+1}s)", "SUCCESS")
                                with open(ledger, "r") as f:
                                    content = f.read()
                                lines = content.strip().split("\n")
                                log(f"交易笔数: {len(lines) - 1}", "SUCCESS")
                                for line in lines[:5]:
                                    log(f"  {line}")
                                return
                        if j % 30 == 29:
                            log(f"回测中... ({j+1}s)")
                    log("5分钟内未检测到ledger", "WARNING")
                return

        if i % 5 == 4:
            log(f"编译中... ({i+1}s)")

    log("编译超时", "ERROR")
    log(f"窗口: {me_win.window_text()}")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""用剪贴板更新代码 + 编译 + Tester"""

import time
import os
import subprocess
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys
import win32clipboard

def set_clipboard(text):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()

def main():
    print("=" * 55)
    print("v1.03 剪贴板更新 + 编译 + Tester")
    print("=" * 55)

    desktop = Desktop(backend="uia")
    mt5_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
    ex5_path = os.path.join(mt5_dir, "MQL5", "Experts", "2H_M30_6H_CurrentCandidate_EA.ex5")

    # 读取v1.03代码
    with open(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5", "r", encoding="utf-8") as f:
        code = f.read()
    print(f"代码长度: {len(code)} 字符")

    # 找MetaEditor
    me_win = None
    for w in desktop.windows():
        if "MetaEditor" in w.window_text() and "Debugging" not in w.window_text():
            me_win = w
            break

    if not me_win:
        print("MetaEditor未找到")
        return

    app = Application(backend="uia").connect(handle=me_win.handle)
    me = app.window(handle=me_win.handle)
    me.set_focus()
    time.sleep(1)

    # 复制代码到剪贴板
    set_clipboard(code)
    print("代码已复制到剪贴板")

    # 全选+粘贴
    me.set_focus()
    time.sleep(0.3)
    send_keys("^a")
    time.sleep(0.5)
    send_keys("^v")
    time.sleep(1)
    print("代码已粘贴到编辑器")

    # 保存
    send_keys("^s")
    time.sleep(2)
    print("已保存")

    # 编译
    start = time.time()
    print("编译 (F7)...")
    me.set_focus()
    time.sleep(0.3)
    send_keys("{F7}")

    for i in range(30):
        time.sleep(1)
        if os.path.exists(ex5_path):
            mtime = os.path.getmtime(ex5_path)
            if mtime > start:
                size = os.path.getsize(ex5_path)
                print(f"编译成功! {size:,} bytes ({i+1}s)")

                # 运行Tester
                print("\n=== 运行Strategy Tester ===")
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
                    send_keys("^r")
                    time.sleep(3)
                    send_keys("{ENTER}")
                    print("Tester已启动")

                    ledger = os.path.join(mt5_dir, "MQL5", "Files", "2H_M30_6H_current_candidate_trade_ledger.csv")
                    print("等待ledger文件...")
                    for j in range(300):
                        time.sleep(1)
                        if os.path.exists(ledger):
                            sz = os.path.getsize(ledger)
                            if sz > 50:
                                print(f"检测到ledger! {sz} bytes ({j+1}s)")
                                with open(ledger, "r") as f:
                                    content = f.read()
                                lines = content.strip().split("\n")
                                print(f"交易笔数: {len(lines) - 1}")
                                for line in lines[:5]:
                                    print(f"  {line}")
                                return
                        if j % 30 == 29:
                            print(f"回测中... ({j+1}s)")
                    print("5分钟内未检测到ledger")
                return

        if i % 5 == 4:
            print(f"编译中... ({i+1}s)")

    print("编译超时")

if __name__ == "__main__":
    main()

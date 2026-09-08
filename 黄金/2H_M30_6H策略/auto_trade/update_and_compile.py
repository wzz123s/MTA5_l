# -*- coding: utf-8 -*-
"""更新代码+编译+复制"""

import time
import os
import shutil
import win32clipboard
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def set_clipboard(text):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()

def main():
    print("=" * 55)
    print("更新代码 + 编译 + 复制")
    print("=" * 55)

    desktop = Desktop(backend="uia")
    
    # 找MetaEditor
    me_win = None
    for w in desktop.windows():
        title = w.window_text()
        if "MetaEditor" in title:
            me_win = w
            print(f"找到: {title}")
            break
    
    if not me_win:
        print("MetaEditor未找到")
        return

    app = Application(backend="uia").connect(handle=me_win.handle)
    me = app.window(handle=me_win.handle)
    me.set_focus()
    time.sleep(1)

    # 读取v1.03代码
    with open(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5", "r", encoding="utf-8") as f:
        code = f.read()
    print(f"代码: {len(code)} 字符")

    # 复制到剪贴板
    set_clipboard(code)
    print("代码已复制到剪贴板")

    # 全选+粘贴+保存
    me.set_focus()
    time.sleep(0.3)
    send_keys("^a")
    time.sleep(0.5)
    send_keys("^v")
    time.sleep(1)
    print("代码已粘贴")

    send_keys("^s")
    time.sleep(2)
    print("已保存")

    # 编译
    ex5_src = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.ex5"
    ex5_experts = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\2H_M30_6H_CurrentCandidate_EA.ex5"
    ex5_advisors = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\Advisors\2H_M30_6H_CurrentCandidate_EA.ex5"

    # 删除旧.ex5
    for p in [ex5_src, ex5_experts, ex5_advisors]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except:
                pass

    start = time.time()
    print("编译 (F7)...")
    me.set_focus()
    time.sleep(0.3)
    send_keys("{F7}")

    for i in range(30):
        time.sleep(1)
        for p in [ex5_src, ex5_experts]:
            if os.path.exists(p):
                mtime = os.path.getmtime(p)
                if mtime > start:
                    size = os.path.getsize(p)
                    print(f"编译成功! {size:,} bytes ({i+1}s)")
                    # 复制到所有位置
                    if p == ex5_src:
                        shutil.copy2(p, ex5_experts)
                        shutil.copy2(p, ex5_advisors)
                    else:
                        shutil.copy2(p, ex5_advisors)
                        shutil.copy2(p, ex5_src)
                    print("已复制到所有位置")
                    return
        if i % 5 == 4:
            print(f"编译中... ({i+1}s)")

    print("编译超时")

if __name__ == "__main__":
    main()

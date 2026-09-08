# -*- coding: utf-8 -*-
"""2H_M30_6H EA 编译 v4 - 使用菜单操作"""

import time
import os
import shutil
import subprocess
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 50)
    log("2H_M30_6H EA 编译 v4")
    log("=" * 50)

    ea_file = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5"
    mt5_experts = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts"
    ex5_path = os.path.join(mt5_experts, "2H_M30_6H_CurrentCandidate_EA.ex5")
    src_ex5 = ea_file.replace(".mq5", ".ex5")

    # Step 1: 连接MetaEditor
    log("[1/4] 连接MetaEditor...")
    desktop = Desktop(backend="uia")
    
    me_win = None
    for w in desktop.windows():
        if "MetaEditor" in w.window_text():
            me_win = w
            break
    
    if not me_win:
        log("MetaEditor未运行，启动中...", "WARNING")
        subprocess.Popen([r"F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe"])
        time.sleep(5)
        for w in desktop.windows():
            if "MetaEditor" in w.window_text():
                me_win = w
                break
    
    if not me_win:
        log("无法找到MetaEditor", "ERROR")
        return False
    
    app = Application(backend="uia").connect(handle=me_win.handle)
    me = app.window(handle=me_win.handle)
    me.set_focus()
    time.sleep(1)
    log(f"已连接: {me_win.window_text()}", "SUCCESS")

    # Step 2: 用命令行打开文件（确保新标签页）
    log("[2/4] 打开EA文件...")
    subprocess.Popen([
        r"F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe",
        ea_file
    ])
    time.sleep(5)
    
    # 重新查找窗口（可能是新窗口或同一窗口新标签）
    log(f"当前标题: {me_win.window_text()}", "INFO")
    
    # 尝试切换到新标签页 (Ctrl+Tab)
    me.set_focus()
    time.sleep(0.5)
    
    # 检查是否有多标签页，尝试切换
    for _ in range(5):
        send_keys("^{TAB}")  # Ctrl+Tab
        time.sleep(0.5)
        title = me_win.window_text()
        if "2H_M30_6H" in title:
            log(f"已切换到目标标签: {title}", "SUCCESS")
            break
    else:
        log(f"当前标签: {me_win.window_text()}", "INFO")
        log("尝试直接编译当前标签...", "INFO")

    # Step 3: 编译 (F7)
    log("[3/4] 编译 (F7)...")
    me.set_focus()
    time.sleep(0.5)
    send_keys("{F7}")
    log("F7已发送", "SUCCESS")

    # Step 4: 等待编译结果
    log("[4/4] 等待编译完成...")
    start_time = time.time()
    
    for i in range(60):
        time.sleep(1)
        
        # 检查多个位置
        for path in [ex5_path, src_ex5]:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if mtime > start_time:
                    size = os.path.getsize(path)
                    elapsed = int(time.time() - start_time)
                    log(f"编译成功！{size:,} bytes ({elapsed}s)", "SUCCESS")
                    log(f"文件: {path}", "INFO")
                    
                    # 如果在源码目录，复制到MT5目录
                    if path != ex5_path:
                        shutil.copy2(path, ex5_path)
                        log(f"已复制到: {ex5_path}", "INFO")
                    
                    return True
        
        if i % 5 == 4:
            log(f"等待中... ({i+1}s)")
    
    log("60秒内未生成.ex5文件", "WARNING")
    log("请手动在MetaEditor中检查:", "INFO")
    log("  1. 打开 2H_M30_6H_CurrentCandidate_EA.mq5", "INFO")
    log("  2. 按F7编译", "INFO")
    log("  3. 查看底部Errors面板", "INFO")
    return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("编译成功！")
    else:
        print("编译未完成，请查看上方信息")
    print("=" * 50)

# -*- coding: utf-8 -*-
"""2H_M30_6H EA 编译 v5 - 从MT5启动MetaEditor"""

import time
import os
import shutil
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def main():
    log("=" * 50)
    log("2H_M30_6H EA 编译 v5 - 从MT5启动MetaEditor")
    log("=" * 50)

    ea_file_en = r"C:\Users\3762\ea_compile_temp\2H_M30_6H_EA.mq5"
    ea_file_src = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5"
    mt5_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts"
    ex5_en = ea_file_en.replace(".mq5", ".ex5")
    ex5_mt5 = os.path.join(mt5_dir, "2H_M30_6H_CurrentCandidate_EA.ex5")

    # 准备源码
    shutil.copy2(ea_file_src, ea_file_en)
    if os.path.exists(ex5_en):
        os.remove(ex5_en)
    log(f"源码已准备: {os.path.getsize(ea_file_en):,} bytes")

    # Step 1: 从MT5按F4启动MetaEditor
    log("[1] 从MT5启动MetaEditor (F4)...")
    desktop = Desktop(backend="uia")
    
    mt5_win = None
    for w in desktop.windows():
        title = w.window_text()
        if "Exness" in title and "模拟" in title:
            mt5_win = w
            break
    
    if not mt5_win:
        log("未找到MT5窗口")
        return False
    
    mt5_app = Application(backend="uia").connect(handle=mt5_win.handle)
    mt5 = mt5_app.window(handle=mt5_win.handle)
    mt5.set_focus()
    time.sleep(1)
    send_keys("{F4}")
    log("F4已发送")
    time.sleep(10)

    # 查找MetaEditor窗口
    me_win = None
    for w in desktop.windows():
        if "MetaEditor" in w.window_text():
            me_win = w
            log(f"找到MetaEditor: {w.window_text()}")
            break
    
    if not me_win:
        log("MetaEditor未启动，尝试直接启动...")
        import subprocess
        subprocess.Popen([r"F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe"])
        time.sleep(10)
        
        for w in desktop.windows():
            if "MetaEditor" in w.window_text():
                me_win = w
                log(f"找到MetaEditor: {w.window_text()}")
                break
    
    if not me_win:
        log("无法启动MetaEditor", "ERROR")
        return False

    me_app = Application(backend="uia").connect(handle=me_win.handle)
    me = me_app.window(handle=me_win.handle)
    me.set_focus()
    time.sleep(1)

    # Step 2: 打开文件 (Ctrl+O)
    log("[2] 打开EA文件...")
    send_keys("^o")
    time.sleep(2)

    # 查找对话框
    dialog_found = False
    for dlg_title in ["Open", "打开", "Open File"]:
        try:
            dlg = me_app.window(title=dlg_title)
            if dlg.exists(timeout=3):
                log(f"找到对话框: {dlg_title}")
                
                # 尝试多种方式输入文件路径
                try:
                    ed = dlg.child_window(control_type="Edit", found_index=0)
                    if ed.exists(timeout=2):
                        ed.set_focus()
                        ed.set_text(ea_file_en)
                        time.sleep(0.5)
                        send_keys("{ENTER}")
                        log("文件已打开")
                        dialog_found = True
                        time.sleep(3)
                        break
                except Exception as e:
                    log(f"Edit方式失败: {e}")
                
                break
        except:
            continue

    if not dialog_found:
        log("对话框未找到，尝试直接在MetaEditor中操作...")
        # 可能文件已经通过之前的方式打开了

    # Step 3: 编译 (F7)
    log("[3] 编译 (F7)...")
    me.set_focus()
    time.sleep(0.5)
    send_keys("{F7}")
    log("F7已发送")

    # Step 4: 等待编译结果
    log("[4] 等待编译完成...")
    start = time.time()
    
    for i in range(45):
        time.sleep(1)
        
        for path in [ex5_en, ex5_mt5]:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if mtime > start:
                    size = os.path.getsize(path)
                    elapsed = int(time.time() - start)
                    log(f"编译成功! {size:,} bytes ({elapsed}s)")
                    log(f"文件: {path}")
                    
                    if path != ex5_mt5:
                        shutil.copy2(path, ex5_mt5)
                        log(f"已复制到MT5目录: {ex5_mt5}")
                    
                    return True
        
        if i % 5 == 4:
            log(f"等待中... ({i+1}s)")
    
    log("45秒内未生成.ex5文件")
    log(f"当前窗口: {me_win.window_text()}")
    log("请手动检查MetaEditor中的错误信息")
    return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("编译成功！")
    else:
        print("编译未完成")
    print("=" * 50)

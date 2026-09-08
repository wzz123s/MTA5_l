# -*- coding: utf-8 -*-
"""
2H_M30_6H EA 编译自动化脚本
使用 pywinauto 操作 MetaEditor GUI 进行编译
"""

import time
import sys
from pywinauto import Application, Desktop

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 50)
    log("2H_M30_6H EA 编译自动化")
    log("=" * 50)

    # Step 1: 查找并连接MetaEditor
    log("\n[1/5] 连接MetaEditor...")
    desktop = Desktop(backend='uia')
    
    me_windows = [w for w in desktop.windows() if 'MetaEditor' in w.window_text()]
    
    if not me_windows:
        log("❌ MetaEditor未运行，正在启动...", "WARNING")
        # 启动MetaEditor
        import subprocess
        subprocess.Popen([r'F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe'])
        time.sleep(5)
        
        # 重新查找
        me_windows = [w for w in desktop.windows() if 'MetaEditor' in w.window_text()]
        if not me_windows:
            log("❌ 无法启动MetaEditor", "ERROR")
            return False
    
    me_win = me_windows[0]
    log(f"✅ 找到MetaEditor: {me_win.window_text()}", "SUCCESS")
    
    # 连接到MetaEditor
    try:
        app = Application(backend='uia').connect(handle=me_win.handle)
        me = app.window(handle=me_win.handle)
    except Exception as e:
        log(f"❌ 连接失败: {e}", "ERROR")
        return False
    
    # Step 2: 打开EA文件
    log("\n[2/5] 打开EA源码文件...")
    ea_file = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5"
    
    # 检查是否已经打开了这个文件
    current_title = me.window_text()
    if '2H_M30_6H_CurrentCandidate' in current_title:
        log("✅ 文件已打开", "SUCCESS")
    else:
        # 使用Ctrl+O打开文件对话框
        me.set_focus()
        time.sleep(0.5)
        
        from pywinauto.keyboard import send_keys
        send_keys('^o')  # Ctrl+O
        time.sleep(2)
        
        # 在文件名输入框中输入路径
        # 查找打开文件对话框
        open_dialog = app.window(title='Open')
        if not open_dialog.exists(timeout=3):
            open_dialog = app.window(title='打开')
        
        if open_dialog.exists(timeout=3):
            log("✅ 找到打开文件对话框", "SUCCESS")
            # 输入文件路径
            file_edit = open_dialog.child_window(control_type="Edit")
            if file_edit.exists(timeout=2):
                file_edit.set_text(ea_file)
                time.sleep(0.5)
                send_keys('{ENTER}')
                time.sleep(2)
                log("✅ 已打开文件", "SUCCESS")
            else:
                log("⚠️ 未找到文件名输入框", "WARNING")
                send_keys('{ESC}')
        else:
            log("⚠️ 未找到打开文件对话框", "WARNING")
            # 尝试直接用命令行参数打开
            import subprocess
            subprocess.Popen([r'F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe', ea_file])
            time.sleep(3)
            log("✅ 已通过命令行打开文件", "SUCCESS")
    
    # Step 3: 编译 (F7)
    log("\n[3/5] 编译EA (按F7)...")
    me.set_focus()
    time.sleep(0.5)
    
    from pywinauto.keyboard import send_keys
    send_keys('{F7}')
    log("✅ 已发送F7编译命令", "SUCCESS")
    
    # Step 4: 等待编译完成
    log("\n[4/5] 等待编译完成...")
    
    # 编译可能需要几秒到几十秒
    # 检查错误面板是否出现
    max_wait = 60  # 最多等待60秒
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        time.sleep(2)
        elapsed = int(time.time() - start_time)
        
        # 检查是否有错误窗口
        error_dialog = app.window(title='Compile')
        if error_dialog.exists(timeout=1):
            log(f"⏳ 编译中... ({elapsed}s)", "INFO")
            continue
        
        # 检查MetaEditor标题栏是否变化
        current_title = me.window_text()
        if 'compiling' in current_title.lower() or '编译' in current_title:
            log(f"⏳ 编译中... ({elapsed}s)", "INFO")
            continue
        
        # 检查底部错误面板
        try:
            error_panel = me.child_window(auto_id="ErrorPane", control_type="Pane")
            if error_panel.exists(timeout=1):
                log(f"✅ 编译完成 ({elapsed}s)", "SUCCESS")
                break
        except:
            pass
        
        # 如果超过10秒且没有编译中的标志，可能已经完成
        if elapsed > 10:
            log(f"✅ 编译可能已完成 ({elapsed}s)", "SUCCESS")
            break
    
    # Step 5: 检查编译结果
    log("\n[5/5] 检查编译结果...")
    
    import os
    ex5_path = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\2H_M30_6H_CurrentCandidate_EA.ex5"
    ex5_path_local = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.ex5"
    
    # 检查MT5目录
    if os.path.exists(ex5_path):
        size = os.path.getsize(ex5_path)
        mtime = time.ctime(os.path.getmtime(ex5_path))
        log(f"✅ 编译成功！", "SUCCESS")
        log(f"   文件: {ex5_path}", "INFO")
        log(f"   大小: {size:,} bytes", "INFO")
        log(f"   时间: {mtime}", "INFO")
        return True
    
    # 检查本地目录
    if os.path.exists(ex5_path_local):
        size = os.path.getsize(ex5_path_local)
        mtime = time.ctime(os.path.getmtime(ex5_path_local))
        log(f"✅ 编译成功！", "SUCCESS")
        log(f"   文件: {ex5_path_local}", "INFO")
        log(f"   大小: {size:,} bytes", "INFO")
        log(f"   时间: {mtime}", "INFO")
        return True
    
    log("⚠️ 未找到.ex5文件", "WARNING")
    log("请检查MetaEditor中的错误面板", "INFO")
    log("如果编译失败，请查看错误信息并告知我", "INFO")
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        print("\n" + "=" * 50)
        if success:
            print("✅ 编译成功！可以继续运行Tester")
        else:
            print("⚠️ 编译可能失败，请检查MetaEditor")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ 出错: {e}")
        import traceback
        traceback.print_exc()

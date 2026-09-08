# -*- coding: utf-8 -*-
"""
2H_M30_6H EA 编译自动化 v3
直接在MetaEditor中操作菜单和编辑器
"""

import time
import os
import shutil
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys
from pywinauto.timings import TimeoutError

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 50)
    log("2H_M30_6H EA 编译 v3 - 直接操作MetaEditor")
    log("=" * 50)

    ea_file = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5"
    mt5_experts = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts"
    ex5_expected = os.path.join(mt5_experts, "2H_M30_6H_CurrentCandidate_EA.ex5")

    # Step 1: 连接MetaEditor
    log("\n[1/5] 连接MetaEditor...")
    desktop = Desktop(backend='uia')
    
    me_win = None
    for w in desktop.windows():
        if 'MetaEditor' in w.window_text():
            me_win = w
            break
    
    if not me_win:
        log("❌ MetaEditor未运行", "ERROR")
        return False
    
    log(f"✅ 找到: {me_win.window_text()}", "SUCCESS")
    
    app = Application(backend='uia').connect(handle=me_win.handle)
    me = app.window(handle=me_win.handle)
    me.set_focus()
    time.sleep(1)
    
    # Step 2: 使用菜单 File > Open 打开文件
    log("\n[2/5] 通过菜单打开文件...")
    
    # 方法: 先按Ctrl+O，然后在对话框中输入路径
    me.set_focus()
    time.sleep(0.3)
    send_keys('^o')  # Ctrl+O
    time.sleep(2)
    
    # 查找打开文件对话框
    open_dlg = None
    for title in ['Open', '打开', 'Open File']:
        try:
            d = app.window(title=title)
            if d.exists(timeout=2):
                open_dlg = d
                log(f"✅ 找到对话框: {title}", "SUCCESS")
                break
        except:
            continue
    
    if open_dlg:
        # 在文件名输入框中输入完整路径
        try:
            # 找到文件名输入框 (通常是ComboBox或Edit)
            file_combo = open_dlg.child_window(control_type="ComboBox", found_index=0)
            if file_combo.exists(timeout=2):
                file_edit = file_combo.child_window(control_type="Edit")
                file_edit.set_focus()
                file_edit.set_text(ea_file)
                time.sleep(0.5)
                send_keys('{ENTER}')
                time.sleep(3)
                log("✅ 文件已打开", "SUCCESS")
        except Exception as e:
            log(f"⚠️ ComboBox操作失败: {e}", "WARNING")
            # 尝试直接找Edit控件
            try:
                edit = open_dlg.child_window(control_type="Edit", found_index=0)
                if edit.exists(timeout=2):
                    edit.set_focus()
                    edit.set_text(ea_file)
                    time.sleep(0.5)
                    send_keys('{ENTER}')
                    time.sleep(3)
                    log("✅ 文件已打开(通过Edit)", "SUCCESS")
            except Exception as e2:
                log(f"⚠️ Edit操作也失败: {e2}", "WARNING")
                send_keys('{ESC}')
    else:
        log("⚠️ 未找到打开文件对话框", "WARNING")
        # 尝试直接输入路径
        log("尝试直接用命令行打开...", "INFO")
        import subprocess
        subprocess.Popen([
            r'F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe',
            ea_file
        ])
        time.sleep(5)
    
    # 检查当前窗口标题
    time.sleep(2)
    current_title = me.window_text()
    log(f"当前窗口标题: {current_title}", "INFO")
    
    # Step 3: 编译 (F7)
    log("\n[3/5] 编译 (F7)...")
    me.set_focus()
    time.sleep(0.5)
    send_keys('{F7}')
    log("✅ F7已发送", "SUCCESS")
    
    # Step 4: 等待编译完成
    log("\n[4/5] 等待编译完成...")
    
    # 记录编译前的时间
    start_time = time.time()
    
    # 等待.ex5文件出现
    for i in range(45):  # 最多等45秒
        time.sleep(1)
        
        # 检查.ex5文件
        for check_path in [ex5_expected, ea_file.replace('.mq5', '.ex5')]:
            if os.path.exists(check_path):
                mtime = os.path.getmtime(check_path)
                if mtime > start_time:  # 是编译后创建的
                    size = os.path.getsize(check_path)
                    log(f"✅ 编译成功！({i+1}s)", "SUCCESS")
                    log(f"   文件: {check_path}", "INFO")
                    log(f"   大小: {size:,} bytes", "INFO")
                    
                    # 复制到MT5目录
                    if check_path != ex5_expected:
                        shutil.copy2(check_path, ex5_expected)
                        log(f"   已复制到: {ex5_expected}", "INFO")
                    
                    return True
        
        if i % 5 == 4:
            log(f"⏳ 等待中... ({i+1}s)")
    
    # Step 5: 检查编译错误
    log("\n[5/5] 检查编译错误...")
    log("30秒内未生成.ex5文件，可能有编译错误", "WARNING")
    
    # 尝试读取错误面板
    try:
        # MetaEditor底部通常有错误面板
        # 尝试查找Error List或类似控件
        for ctrl in me.descendants():
            try:
                ctrl_type = ctrl.element_info.control_type
                if ctrl_type in ['ListView', 'ListBox', 'DataGrid']:
                    name = ctrl.element_info.name
                    if name and ('error' in name.lower() or '错误' in name):
                        log(f"找到错误面板: {name}", "INFO")
                        items = ctrl.items()
                        for item in items[:10]:
                            log(f"  ❌ {item.window_text()}", "ERROR")
                        break
            except:
                continue
    except:
        pass
    
    # 最终检查
    log("\n=== 最终检查所有位置 ===", "INFO")
    for path in [ex5_expected, ea_file.replace('.mq5', '.ex5')]:
        if os.path.exists(path):
            size = os.path.getsize(path)
            mtime = time.ctime(os.path.getmtime(path))
            log(f"✅ 找到: {path}", "SUCCESS")
            log(f"   大小: {size:,} bytes, 时间: {mtime}", "INFO")
            return True
    
    log("❌ 未找到.ex5文件", "ERROR")
    log("\n📋 请手动检查MetaEditor:", "INFO")
    log("   1. 确认打开了 2H_M30_6H_CurrentCandidate_EA.mq5", "INFO")
    log("   2. 按F7编译", "INFO")
    log("   3. 查看底部Errors面板的错误信息", "INFO")
    log("   4. 将错误信息发给我修复", "INFO")
    return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("✅ 编译成功！")
    else:
        print("⚠️ 编译失败，请查看上方信息")
    print("=" * 50)

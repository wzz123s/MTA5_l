# -*- coding: utf-8 -*-
"""
2H_M30_6H EA 编译自动化 v2
精确控制MetaEditor窗口
"""

import time
import sys
import os
import subprocess
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 50)
    log("2H_M30_6H EA 编译自动化 v2")
    log("=" * 50)

    ea_file = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_CurrentCandidate_EA.mq5"
    mt5_experts = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts"
    
    # 确保源码也在MT5目录
    import shutil
    dst_mq5 = os.path.join(mt5_experts, "2H_M30_6H_CurrentCandidate_EA.mq5")
    shutil.copy2(ea_file, dst_mq5)
    log(f"✅ 源码已复制到MT5 Experts目录")

    # Step 1: 用命令行打开文件（确保新窗口）
    log("\n[1/4] 用MetaEditor打开EA文件...")
    
    # 先关闭已有的MetaEditor窗口（可选）
    # 或者直接用命令行打开新文件
    subprocess.Popen([
        r'F:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe',
        ea_file
    ])
    time.sleep(5)
    
    # Step 2: 查找打开了正确文件的MetaEditor窗口
    log("\n[2/4] 查找正确的MetaEditor窗口...")
    desktop = Desktop(backend='uia')
    
    target_window = None
    for attempt in range(5):
        for w in desktop.windows():
            title = w.window_text()
            if 'MetaEditor' in title and '2H_M30_6H_CurrentCandidate' in title:
                target_window = w
                log(f"✅ 找到目标窗口: {title}", "SUCCESS")
                break
        if target_window:
            break
        log(f"⏳ 等待窗口出现... (尝试 {attempt+1}/5)")
        time.sleep(2)
    
    if not target_window:
        log("⚠️ 未找到打开了目标文件的窗口", "WARNING")
        log("尝试在当前MetaEditor窗口中操作...", "INFO")
        
        # 使用任何MetaEditor窗口
        for w in desktop.windows():
            if 'MetaEditor' in w.window_text():
                target_window = w
                log(f"使用窗口: {w.window_text()}", "INFO")
                break
    
    if not target_window:
        log("❌ 无法找到MetaEditor窗口", "ERROR")
        return False
    
    # 连接到窗口
    try:
        app = Application(backend='uia').connect(handle=target_window.handle)
        me = app.window(handle=target_window.handle)
        me.set_focus()
        time.sleep(1)
    except Exception as e:
        log(f"❌ 连接窗口失败: {e}", "ERROR")
        return False
    
    # Step 3: 发送F7编译
    log("\n[3/4] 发送F7编译命令...")
    
    # 确保窗口有焦点
    me.set_focus()
    time.sleep(0.5)
    
    # 发送F7
    send_keys('{F7}')
    log("✅ 已发送F7", "SUCCESS")
    
    # Step 4: 等待编译完成并检查结果
    log("\n[4/4] 等待编译完成...")
    
    # 等待编译完成（检查.ex5文件）
    ex5_path = os.path.join(mt5_experts, "2H_M30_6H_CurrentCandidate_EA.ex5")
    ex5_src_path = ea_file.replace('.mq5', '.ex5')
    
    max_wait = 30  # 最多等30秒
    for i in range(max_wait):
        time.sleep(1)
        
        # 检查多个位置
        for path in [ex5_path, ex5_src_path]:
            if os.path.exists(path):
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                # 确认是刚刚创建的（最近2分钟内）
                if time.time() - mtime < 120:
                    log(f"✅ 编译成功！", "SUCCESS")
                    log(f"   文件: {path}", "INFO")
                    log(f"   大小: {size:,} bytes", "INFO")
                    
                    # 如果不在MT5目录，复制过去
                    if path != ex5_path:
                        shutil.copy2(path, ex5_path)
                        log(f"   已复制到MT5目录: {ex5_path}", "INFO")
                    
                    return True
        
        if i % 5 == 4:
            log(f"⏳ 等待中... ({i+1}s)")
    
    # 编译可能失败，检查错误
    log("⚠️ 30秒内未找到.ex5文件", "WARNING")
    log("可能编译有错误，尝试读取错误信息...", "INFO")
    
    # 尝试查看MetaEditor的错误面板
    try:
        # 查找错误列表
        error_list = me.child_window(control_type="ListView", found_index=0)
        if error_list.exists(timeout=3):
            log("发现错误面板，内容:", "INFO")
            # 读取错误信息
            items = error_list.items()
            for item in items[:10]:
                log(f"  错误: {item.window_text()}", "ERROR")
    except:
        pass
    
    # 最后再检查一次所有可能的位置
    log("\n=== 最终检查 ===", "INFO")
    for path in [ex5_path, ex5_src_path]:
        if os.path.exists(path):
            size = os.path.getsize(path)
            mtime = time.ctime(os.path.getmtime(path))
            log(f"找到: {path} ({size:,} bytes, {mtime})", "INFO")
            return True
    
    log("❌ 未找到.ex5文件", "ERROR")
    log("请手动在MetaEditor中按F7编译，并查看错误信息", "INFO")
    return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("✅ 编译成功！可以继续运行Tester")
    else:
        print("⚠️ 编译可能失败")
    print("=" * 50)

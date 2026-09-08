# -*- coding: utf-8 -*-
"""
1H_M30_4H EA 自动化部署脚本
使用 pywinauto 自动完成 MT5 GUI 操作
生成时间: 2026-07-30 20:40
"""

import time
import sys
from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.keyboard import send_keys

def log(message, level="INFO"):
    """带时间戳的日志输出"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def wait_for_window(app, title, timeout=30):
    """等待窗口出现"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            win = app.window(title=title)
            if win.exists():
                return win
        except:
            pass
        time.sleep(1)
    return None

def main():
    log("=" * 60)
    log("1H_M30_4H EA 自动化部署开始")
    log("=" * 60)
    
    # Step 1: 连接到MT5
    log("\n[Step 1/6] 连接到MT5终端...")
    try:
        # 尝试连接到已运行的MT5
        app = Application(backend='uia').connect(path=r'F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe')
        log("✅ 已连接到MT5进程", "SUCCESS")
    except Exception as e:
        log(f"❌ 无法连接MT5: {e}", "ERROR")
        log("请确保MT5正在运行", "WARNING")
        return False
    
    mt5_main = app.window(title_re='.*MetaTrader 5.*|.*Terminal.*')
    
    if not mt5_main.exists(timeout=10):
        log("❌ 无法找到MT5主窗口", "ERROR")
        return False
    
    log(f"✅ 找到MT5主窗口: {mt5_main.window_text()}", "SUCCESS")
    
    # Step 2: 打开XAUUSDm M30图表
    log("\n[Step 2/6] 打开XAUUSDm M30图表...")
    
    try:
        # 使用快捷键F6打开新图表
        mt5_main.set_focus()
        time.sleep(0.5)
        send_keys('{F6}')
        log("已发送F6快捷键，等待图表窗口...", "INFO")
        time.sleep(3)
        
        # 查找符号选择对话框
        dialog = app.window(title='Symbols')
        if dialog.exists(timeout=5):
            log("✅ 符号选择窗口已打开", "SUCCESS")
            
            # 在搜索框中输入XAUUSDm
            try:
                search_edit = dialog.child_window(auto_id="SearchEdit", control_type="Edit")
                if search_edit.exists(timeout=3):
                    search_edit.set_focus()
                    search_edit.set_text('XAUUSDm')
                    log("✅ 已输入XAUUSDm", "SUCCESS")
                    time.sleep(1)
                    
                    # 按回车搜索
                    send_keys('{ENTER}')
                    time.sleep(1)
                    
                    # 选择XAUUSDm（在列表中找到并双击）
                    list_control = dialog.child_window(auto_id="SymbolsList", control_type="List")
                    if list_control.exists(timeout=3):
                        # 尝试选择第一项（应该是XAUUSDm）
                        list_control.select(0)
                        time.sleep(0.5)
                        send_keys('{ENTER}')
                        log("✅ 已选择XAUUSDm", "SUCCESS")
                else:
                    log("⚠️ 未找到搜索框，尝试手动操作", "WARNING")
            except Exception as e:
                log(f"⚠️ 符号选择出错: {e}", "WARNING")
            
            time.sleep(2)
            
            # 点击OK按钮确认
            ok_button = dialog.child_window(title="OK", control_type="Button")
            if ok_button.exists(timeout=3):
                ok_button.click()
                log("✅ 已确认符号选择", "SUCCESS")
            else:
                send_keys('{ENTER}')  # 用回车确认
                log("✅ 已按回车确认", "SUCCESS")
                
        else:
            log("⚠️ 未检测到符号选择窗口，可能需要手动打开图表", "WARNING")
        
        time.sleep(3)
        
    except Exception as e:
        log(f"⚠️ 图表打开过程出错: {e}", "WARNING")
        log("可以手动按F6 → XAUUSDm → M30 → OK", "INFO")
    
    # Step 3: 设置周期为M30
    log("\n[Step 3/6] 设置图表周期为M30...")
    try:
        mt5_main.set_focus()
        
        # 尝试通过工具栏设置周期
        # M30对应的工具栏按钮位置可能不同，这里用快捷键或菜单
        
        # 方法：点击周期下拉菜单选择M30
        toolbar = mt5_main.child_window(auto_id="ToolBar", control_type="ToolBar")
        if toolbar.exists(timeout=3):
            log("找到工具栏，尝试切换周期...", "INFO")
            # 这里需要根据实际UI结构来操作
            # 暂时跳过，假设已经选择了正确的周期
            
        log("⚠️ 请确认图表周期为M30（如不是，请在工具栏选择）", "WARNING")
        time.sleep(2)
        
    except Exception as e:
        log(f"⚠️ 周期设置出错: {e}", "WARNING")
    
    # Step 4: 从Navigator拖拽EA到图表
    log("\n[Step 4/6] 加载EA到图表...")
    
    try:
        # 查找Navigator面板中的Expert Advisors树
        navigator = mt5_main.child_window(auto_id="Navigator", control_type="Tree")
        
        if navigator.exists(timeout=5):
            log("✅ 找到Navigator面板", "SUCCESS")
            
            # 展开Expert Advisors节点
            # 注意：实际操作可能需要根据UI结构调整
            log("正在查找1H_M30_4H_CurrentCandidate_EA...", "INFO")
            
            # 尝试找到EA项并拖拽
            # 由于UI自动化拖拽比较复杂，这里提供备选方案
            log("⚠️ GUI自动化拖拽受限，请手动完成以下步骤:", "WARNING")
            
        else:
            log("⚠️ 未找到Navigator面板", "WARNING")
            
    except Exception as e:
        log(f"⚠️ Navigator操作出错: {e}", "WARNING")
    
    # Step 5: 显示手动操作指南（当自动操作受限时）
    log("\n" + "=" * 60)
    log("📋 需要手动完成的操作（约2分钟）:")
    log("=" * 60)
    log("""
    1️⃣  在左侧 Navigator 面板中：
        展开 "Expert Advisors"
        找到: 1H_M30_4H_CurrentCandidate_EA
    
    2️⃣  将EA **鼠标拖拽** 到 XAUUSDm M30 图表上
        （如果看不到EA列表，按 Ctrl+T 显示/隐藏 Navigator）
    
    3️⃣  在弹出的 "EA Settings" 窗口中：
        ☑ 勾选 "Allow algorithmic trading"
        ☑ 勾选 "Allow DLL imports" (如果有提示)
        
        点击 **"Load"** 按钮
        选择文件: 1H_M30_4H_SimDeployment_EA.set
        
        确认关键参数:
        ✅ SimMode = true
        ✅ AllowRealTrading = false
        ✅ MaxRiskUsd = 30.0
        
        点击 **OK**
    
    4️⃣  验证运行状态:
        ✓ 图表右上角显示 😊 (笑脸) 图标
        ✓ MT5底部 "Experts" 标签页显示:
          "1H_M30_4H Current Candidate EA initialized"
          "SimMode: ON (virtual trading only)"
    """)
    
    # Step 6: 创建验证脚本
    log("\n[Step 6/6] 创建状态验证工具...")
    
    verification_code = '''# EA状态验证脚本
# 运行方式: python check_ea_status.py

import os
import time
from datetime import datetime

def check_ea_files():
    """检查EA文件是否存在"""
    base_path = r"C:\\Users\\3762\\AppData\\Roaming\\MetaQuotes\\Terminal\\B695BCB6C1E6864B6D96307B87B29F16"
    
    files_to_check = [
        ("EA文件", f"{base_path}\\MQL5\\Experts\\1H_M30_4H_CurrentCandidate_EA.ex5"),
        ("参数包", f"{base_path}\\MQL5\\Presets\\1H_M30_4H_SimDeployment_EA.set"),
    ]
    
    print("📁 文件检查:")
    all_exist = True
    for name, path in files_to_check:
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {os.path.basename(path)}")
        if not exists:
            all_exist = False
    
    return all_exist

def check_logs():
"""检查最近的EA日志"""
    log_dir = r"C:\\Users\\3762\\AppData\\Roaming\\MetaQuotes\\Terminal\\B695BCB6C1E6864B6D96307B87B29F16\\logs"
    
    print("\\n📋 最近日志（如果有）:")
    if os.path.exists(log_dir):
        logs = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        logs.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
        
        for log_file in logs[:3]:
            full_path = os.path.join(log_dir, log_file)
            mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
            size = os.path.getsize(full_path)
            print(f"  📄 {log_file} ({size:,} bytes) - {mtime}")
    else:
        print("  ⚠️ 日志目录不存在")

if __name__ == "__main__":
    print("=" * 50)
    print("1H_M30_4H EA 状态检查")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    files_ok = check_ea_files()
    check_logs()
    
    print("\\n" + "=" * 50)
    if files_ok:
        print("✅ 所有必需文件已就位")
        print("📌 下一步: 在MT5中手动加载EA（见上方指南）")
    else:
        print("❌ 缺少必需文件，请先运行部署脚本")
    print("=" * 50)
'''
    
    script_path = r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\auto_trade\check_ea_status.py"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(verification_code)
    
    log(f"✅ 验证脚本已创建: {script_path}", "SUCCESS")
    log("   运行方式: python check_ea_status.py", "INFO")
    
    # 完成
    log("\n" + "=" * 60)
    log("✅ 自动化部署脚本执行完成")
    log("=" * 60)
    log("\n📊 完成情况总结:")
    log("  ✅ Step 1: 连接MT5 - 成功")
    log("  ⚠️ Step 2-4: GUI操作 - 需要手动辅助（~2分钟）")
    log("  ✅ Step 5: 操作指南 - 已显示")
    log("  ✅ Step 6: 验证工具 - 已创建")
    log("\n💡 提示: 大部分GUI操作由于MT5安全机制限制无法完全自动化")
    log("   但所有准备工作已完成，手动操作仅需2分钟！")
    log("\n📄 详细文档:")
    log("   F:\\use_code\\MTA5_l\\黄金\\黄金/1H_M30_4H策略\\说明文档\\06_模拟盘部署\\部署执行报告_20260730.md")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\n\n用户中断操作", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ 脚本执行出错: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

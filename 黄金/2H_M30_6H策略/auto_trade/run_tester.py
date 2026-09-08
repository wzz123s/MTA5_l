# -*- coding: utf-8 -*-
"""2H_M30_6H Strategy Tester 自动化运行"""

import time
import os
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 50)
    log("2H_M30_6H Strategy Tester 自动化")
    log("=" * 50)

    desktop = Desktop(backend="uia")

    # 找MT5窗口
    mt5_win = None
    for w in desktop.windows():
        t = w.window_text()
        if "Exness" in t and "MetaTrader" not in t:
            mt5_win = w
            break

    if not mt5_win:
        log("未找到MT5窗口", "ERROR")
        return False

    log(f"找到MT5: {mt5_win.window_text()[:40]}", "SUCCESS")

    app = Application(backend="uia").connect(handle=mt5_win.handle)
    mt5 = app.window(handle=mt5_win.handle)
    mt5.set_focus()
    time.sleep(1)

    # Step 1: 打开Strategy Tester (Ctrl+R)
    log("[1/4] 打开Strategy Tester (Ctrl+R)...")
    send_keys("^r")
    time.sleep(2)

    # Step 2: 配置Tester参数
    log("[2/4] 配置Tester参数...")

    # 尝试找到Strategy Tester面板
    # MT5的Strategy Tester面板通常在底部
    tester_panel = None
    try:
        # 尝试多种方式查找Tester面板
        for name in ["Strategy Tester", "策略测试", "Tester"]:
            try:
                panel = mt5.child_window(title=name, control_type="Pane")
                if panel.exists(timeout=3):
                    tester_panel = panel
                    log(f"找到Tester面板: {name}", "SUCCESS")
                    break
            except:
                continue

        if not tester_panel:
            # 尝试查找底部的Tab区域
            for tab_name in ["Strategy Tester", "策略测试", "Tester", "测试"]:
                try:
                    tab = mt5.child_window(title=tab_name, control_type="TabItem")
                    if tab.exists(timeout=2):
                        tab.click_input()
                        tester_panel = tab
                        log(f"点击Tester标签: {tab_name}", "SUCCESS")
                        break
                except:
                    continue
    except Exception as e:
        log(f"查找Tester面板出错: {e}", "WARNING")

    # Step 3: 设置EA和参数
    log("[3/4] 设置EA和回测参数...")

    # 在Strategy Tester面板中:
    # - 选择EA: 2H_M30_6H_CurrentCandidate_EA
    # - 选择Symbol: XAUUSDm
    # - 选择Period: M30
    # - 设置日期范围
    # - 选择Model: Every tick

    # 尝试查找EA选择下拉框
    ea_selected = False
    try:
        if tester_panel:
            # 查找ComboBox（EA选择）
            combos = tester_panel.descendants(control_type="ComboBox")
            for i, combo in enumerate(combos):
                try:
                    current = combo.window_text()
                    log(f"ComboBox[{i}]: {current}", "INFO")

                    # 第一个ComboBox通常是EA选择
                    if i == 0:
                        combo.click_input()
                        time.sleep(0.5)

                        # 查找2H_M30_6H_CurrentCandidate_EA
                        items = combo.descendants(control_type="ListItem")
                        for item in items:
                            if "2H_M30_6H" in item.window_text():
                                item.click_input()
                                log(f"已选择EA: {item.window_text()}", "SUCCESS")
                                ea_selected = True
                                time.sleep(0.5)
                                break

                        if not ea_selected:
                            # 尝试输入
                            send_keys("2H_M30_6H")
                            time.sleep(0.5)
                            send_keys("{ENTER}")
                            ea_selected = True
                            log("已通过输入选择EA", "SUCCESS")
                except:
                    continue
    except Exception as e:
        log(f"EA选择出错: {e}", "WARNING")

    # Step 4: 点击Start按钮
    log("[4/4] 开始回测...")

    start_clicked = False
    try:
        if tester_panel:
            # 查找Start按钮
            buttons = tester_panel.descendants(control_type="Button")
            for btn in buttons:
                title = btn.window_text()
                if "Start" in title or "开始" in title or "Run" in title:
                    btn.click_input()
                    log(f"已点击: {title}", "SUCCESS")
                    start_clicked = True
                    break
    except Exception as e:
        log(f"Start按钮查找出错: {e}", "WARNING")

    if not start_clicked:
        # 备用方案: 尝试用快捷键
        log("尝试用Enter键开始...", "INFO")
        send_keys("{ENTER}")

    # 等待回测完成
    log("等待回测完成...")
    log("回测可能需要几分钟到几十分钟（取决于数据量和模型）", "INFO")

    # 检查回测结果文件
    mt5_files = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Files"
    tester_reports = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\reports"

    log(f"\n回测结果将保存在:", "INFO")
    log(f"  账单文件: {mt5_files}", "INFO")
    log(f"  报告文件: {tester_reports}", "INFO")
    log(f"\nEA生成的ledger: 2H_M30_6H_current_candidate_trade_ledger.csv", "INFO")

    return True

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("Tester已启动！请观察MT5中的回测进度")
    else:
        print("Tester启动失败")
    print("=" * 50)

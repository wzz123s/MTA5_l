# -*- coding: utf-8 -*-
"""全自动编译v1.02 + 运行Strategy Tester"""

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
    log("全自动编译 + Strategy Tester")
    log("=" * 55)

    ea_file = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\2H_M30_6H_CurrentCandidate_EA.mq5"
    ex5_file = ea_file.replace(".mq5", ".ex5")
    mt5_dir = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"

    desktop = Desktop(backend="uia")

    # === Step 1: 连接MetaEditor ===
    log("[1/6] 连接MetaEditor...")
    me_win = None
    for w in desktop.windows():
        if "MetaEditor" in w.window_text():
            me_win = w
            break

    if not me_win:
        log("MetaEditor未运行", "ERROR")
        return False

    log(f"找到: {me_win.window_text()}", "SUCCESS")
    me_app = Application(backend="uia").connect(handle=me_win.handle)
    me = me_app.window(handle=me_win.handle)

    # === Step 2: 打开v1.02文件 ===
    log("[2/6] 打开v1.02源码...")
    current_title = me_win.window_text()
    if "2H_M30_6H_CurrentCandidate" in current_title:
        log("文件已打开", "SUCCESS")
    else:
        # 用Ctrl+O打开
        me.set_focus()
        time.sleep(0.5)
        send_keys("^o")
        time.sleep(2)

        # 查找对话框
        for dlg_title in ["Open", "打开"]:
            try:
                dlg = me_app.window(title=dlg_title)
                if dlg.exists(timeout=3):
                    log(f"对话框: {dlg_title}")
                    ed = dlg.child_window(control_type="Edit", found_index=0)
                    if ed.exists(timeout=2):
                        ed.set_focus()
                        ed.set_text(ea_file)
                        time.sleep(0.5)
                        send_keys("{ENTER}")
                        log("文件已打开", "SUCCESS")
                        time.sleep(3)
                    break
            except:
                continue

    # === Step 3: 编译 (F7) ===
    log("[3/6] 编译 (F7)...")
    # 删除旧.ex5
    if os.path.exists(ex5_file):
        os.remove(ex5_file)

    me.set_focus()
    time.sleep(0.5)
    send_keys("{F7}")
    log("F7已发送", "SUCCESS")

    # 等待编译完成
    compile_start = time.time()
    for i in range(45):
        time.sleep(1)
        if os.path.exists(ex5_file):
            mtime = os.path.getmtime(ex5_file)
            if mtime > compile_start:
                size = os.path.getsize(ex5_file)
                log(f"编译成功! {size:,} bytes ({i+1}s)", "SUCCESS")
                break
        if i % 5 == 4:
            log(f"编译中... ({i+1}s)")
    else:
        log("编译超时", "ERROR")
        return False

    # === Step 4: 连接MT5 ===
    log("[4/6] 连接MT5...")
    mt5_win = None
    for w in desktop.windows():
        t = w.window_text()
        if "Exness" in t and "MetaTrader" not in t:
            mt5_win = w
            break

    if not mt5_win:
        log("MT5未找到", "ERROR")
        return False

    mt5_app = Application(backend="uia").connect(handle=mt5_win.handle)
    mt5 = mt5_app.window(handle=mt5_win.handle)
    log(f"MT5: {mt5_win.window_text()[:30]}", "SUCCESS")

    # === Step 5: 打开Strategy Tester ===
    log("[5/6] 打开Strategy Tester (Ctrl+R)...")
    mt5.set_focus()
    time.sleep(1)
    send_keys("^r")
    time.sleep(3)

    # === Step 6: 配置并运行Tester ===
    log("[6/6] 配置Tester参数...")

    # 尝试在Tester面板中操作
    # MT5 Strategy Tester面板通常有:
    # - Expert下拉框
    # - Symbol下拉框
    # - Period下拉框
    # - Model下拉框
    # - From/To日期
    # - Start按钮

    # 由于UI自动化限制，尝试用键盘操作
    # 在Tester面板中:
    # 1. Tab到Expert下拉框
    # 2. 输入EA名称
    # 3. Tab到其他字段
    # 4. 最后按Enter或点击Start

    # 尝试查找Tester面板中的控件
    tester_found = False
    try:
        # 查找所有ComboBox
        for w in mt5.descendants():
            try:
                if w.element_info.control_type == "ComboBox":
                    name = w.element_info.name
                    if name:
                        log(f"找到ComboBox: {name}", "INFO")
            except:
                continue

        # 尝试查找Start按钮
        for w in mt5.descendants():
            try:
                if w.element_info.control_type == "Button":
                    name = w.element_info.name
                    if name and ("Start" in name or "开始" in name):
                        log(f"找到按钮: {name}", "INFO")
            except:
                continue
    except:
        pass

    # 使用Enter键尝试启动
    mt5.set_focus()
    time.sleep(0.5)
    send_keys("{ENTER}")
    log("已尝试启动Tester", "INFO")

    # 等待回测完成
    log("等待回测完成...")
    ledger_file = os.path.join(mt5_dir, "MQL5", "Files", "2H_M30_6H_current_candidate_trade_ledger.csv")

    # 检查ledger文件（表示EA成功运行）
    for i in range(300):  # 最多等5分钟
        time.sleep(1)
        if os.path.exists(ledger_file):
            size = os.path.getsize(ledger_file)
            if size > 50:  # 有实际内容
                log(f"检测到ledger文件! {size} bytes ({i+1}s)", "SUCCESS")
                # 读取内容
                try:
                    with open(ledger_file, "r") as f:
                        content = f.read()
                    lines = content.strip().split("\n")
                    log(f"交易笔数: {len(lines) - 1}", "SUCCESS")
                    if len(lines) > 1:
                        log("前3笔交易:", "INFO")
                        for line in lines[:4]:
                            log(f"  {line}", "INFO")
                except:
                    pass
                return True

        if i % 30 == 29:
            log(f"回测进行中... ({i+1}s)")
    else:
        log("5分钟内未检测到ledger文件", "WARNING")
        log("请检查MT5中的Tester状态", "INFO")

    return True

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 55)
    if success:
        print("自动化流程完成!")
    else:
        print("流程未完成")
    print("=" * 55)

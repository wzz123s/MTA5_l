# -*- coding: utf-8 -*-

"""30m2H EA v3.32: 注入 [Tester] 配置到 DAD3B8CC terminal.ini + UIA 启动全量回测
输出: Agent Files 的 30m2H_strategy_trade_ledger.csv
"""
import os
import re
import shutil
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

TERMINAL_ID = "DAD3B8CC3EAC09C0C9725021DF0C7A65"
INI = rf"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\{TERMINAL_ID}\config\terminal.ini"
TERMINAL_PID = 20732  # DAD3B8CC 终端进程

AGENT_FILES = [
    rf"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\{TERMINAL_ID}\Agent-127.0.0.1-3000\MQL5\Files",
    rf"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\{TERMINAL_ID}\Agent-127.0.0.1-3001\MQL5\Files",
]
LEDGER_NAME = "30m2H_strategy_trade_ledger.csv"

TESTER_BLOCK = """; 30m2H EA v3.32 Tester config (auto-injected 2026-08-12)
[Tester]
Expert=30m2H_Strategy_EA
Symbol=XAUUSDm
Period=M30
Model=1
FromDate=2018.01.01
ToDate=2026.08.11
ForwardMode=0
Deposit=2000
Currency=USD
Leverage=100
Optimization=0
Visual=0
Report=30m2H_tester_report
ShutdownTerminal=0
UseLocal=1
UseRemote=0
UseCloud=0
"""


def inject_ini():
    with open(INI, "r", encoding="utf-16") as f:
        content = f.read()
    if "[Tester]" in content:
        content = re.sub(r"\[Tester\].*?(?=\n\[|\Z)", TESTER_BLOCK, content, flags=re.S)
    else:
        content = content.rstrip() + "\n" + TESTER_BLOCK
    with open(INI, "w", encoding="utf-16") as f:
        f.write(content)
    print("terminal.ini [Tester] injected (utf-16)")


def find_terminal_window():
    desktop = Desktop(backend="uia")
    for w in desktop.windows():
        try:
            if w.element_info.process_id == TERMINAL_PID:
                return w
        except Exception:
            continue
    return None


def open_tester_panel(win):
    """Ctrl+R 打开测试器面板（dock 或独立窗口）"""
    win.set_focus()
    time.sleep(1)
    send_keys("^r")
    time.sleep(4)


def find_start_button(win):
    """在终端主窗口的测试器区域内找 开始/停止 按钮"""
    for desc in win.descendants():
        try:
            if desc.element_info.control_type != "Button":
                continue
            t = desc.window_text()
            if t == "开始":
                return desc
            if t == "停止":
                print("tester running/stopped; clicking 停止 first")
                desc.click_input()
                time.sleep(3)
        except Exception:
            continue
    return None


def main():
    # 清理旧 ledger（避免读到上一次的结果）
    for root in AGENT_FILES:
        p = os.path.join(root, LEDGER_NAME)
        if os.path.exists(p):
            os.remove(p)
            print("removed old ledger:", p)
    inject_ini()
    win = find_terminal_window()
    if win is None:
        print("DAD3B8CC terminal window not found (pid 20732)")
        return False

    open_tester_panel(win)
    start = find_start_button(win)
    if start is None:
        # 尝试视图菜单打开测试器
        send_keys("%v")
        time.sleep(1.5)
        for desc in win.descendants():
            try:
                if desc.element_info.control_type == "MenuItem" and "策略测试" in desc.window_text():
                    desc.click_input()
                    time.sleep(3)
                    break
            except Exception:
                continue
        start = find_start_button(win)
    if start is None:
        print("start button not found")
        return False
    try:
        start.invoke()
        print("start invoked")
    except Exception:
        start.click_input()
        print("start clicked")

    # 轮询 ledger: 等待 2 分钟无变化 且 数据覆盖到 2026
    deadline = time.time() + 40 * 60
    last_size = -1
    stable = 0
    while time.time() < deadline:
        for root in AGENT_FILES:
            p = os.path.join(root, LEDGER_NAME)
            if os.path.exists(p):
                sz = os.path.getsize(p)
                if sz != last_size:
                    print(f"{time.strftime('%H:%M:%S')} size={sz}", flush=True)
                    last_size = sz
                    stable = 0
                else:
                    stable += 1
                if stable >= 12:  # 2 分钟无变化
                    with open(p, "r", errors="replace") as f:
                        lines = f.read().strip().splitlines()
                    last_line = lines[-1] if len(lines) > 1 else ""
                    print(f"stable; rows={len(lines)-1}; last={last_line[:40]}")
                    if len(lines) > 100 and "2026" in last_line:
                        print("=== DONE ===")
                        return True
        time.sleep(10)
    print("ledger not stable in 40min")
    return False


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""30m2H EA 模拟盘运行状态监测 - DAD3B8CC 终端 (只读检查, 不修改任何文件)

检查:
  1. terminal64.exe 进程是否运行 (DAD3B8CC 数据目录)
  2. Experts 日志是否出现 30m2H EA initialized + SIM 事件 + New M30 bar
  3. signals CSV (30m2H_strategy_signals_export.csv) 是否创建/更新

注意: SimMode=true 时 trade ledger CSV 不导出 (EA guard) —
      实盘模拟监控依据 = Experts 日志 + signals CSV。
"""
import os
import subprocess
from datetime import datetime

TERMINAL_DIR = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
EANAME = "30m2H_Strategy_EA"
SIGNALS_CSV = "30m2H_strategy_signals_export.csv"


def check_process():
    """Check if MT5 (DAD3B8CC) is running by scanning processes."""
    found = False
    try:
        out = subprocess.check_output(
            ['powershell.exe', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process -Filter \"name='terminal64.exe'\" | ForEach-Object { $_.CommandLine }"],
            timeout=30, text=True
        )
        for line in out.splitlines():
            if "DAD3B8CC3EAC09C0C9725021DF0C7A65" in line or ("MetaTrader 5" in line and "EXNESS" not in line):
                found = True
                break
    except Exception as e:
        print(f"  ⚠️ 进程检查出错: {e}")
    return found


def check_experts_log():
    """Check today's Experts log for 30m2H EA activity."""
    today = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(TERMINAL_DIR, "MQL5", "logs", f"{today}.log")
    if not os.path.exists(log_path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(log_path))
    hits = []
    try:
        with open(log_path, "r", encoding="utf-16-le", errors="ignore") as f:
            for line in f:
                if EANAME in line:
                    hits.append(line.strip()[:150])
    except Exception:
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if EANAME in line:
                        hits.append(line.strip()[:150])
        except Exception as e:
            print(f"  ⚠️ 日志读取出错: {e}")
    return {"hits": hits, "log_mtime": mtime}


def check_signals_csv():
    """Check signals CSV existence and last update."""
    path = os.path.join(TERMINAL_DIR, "MQL5", "Files", SIGNALS_CSV)
    if not os.path.exists(path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    size = os.path.getsize(path)
    lines = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = sum(1 for _ in f)
    except Exception:
        pass
    return {"size": size, "lines": lines, "mtime": mtime}


def main():
    print("=" * 60)
    print(" 30m2H EA 运行状态监测 (DAD3B8CC)")
    print(f" ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n[1] MT5 进程 (DAD3B8CC):", end=" ")
    running = check_process()
    print("✅ 运行中" if running else "❌ 未运行")
    if not running:
        print("    → 请启动 F:\\Program Files\\MetaTrader 5\\terminal64.exe")

    print("\n[2] Experts 日志:", end=" ")
    log = check_experts_log()
    if log is None:
        print("今日无日志")
    else:
        print(f"最后更新 {log['log_mtime'].strftime('%H:%M:%S')}")
        # 筛选关键事件
        init = [h for h in log["hits"] if "Initializing" in h or "initialized" in h.lower()]
        sim = [h for h in log["hits"] if "SIM " in h]
        bar = [h for h in log["hits"] if "New M30 bar" in h]
        if init:
            print(f"    ✅ 初始化: {len(init)} 条")
            print(f"      • {init[-1][:120]}")
        else:
            print("    ❌ 今日无初始化记录 → EA 可能未加载")
        if bar:
            print(f"    ✅ M30 bar 检测: {len(bar)} 条 (最近: {bar[-1][:90]})")
        if sim:
            print(f"    ⚠️ SIM 事件: {len(sim)} 条 (最近: {sim[-1][:90]})")
        # 最近信号判定 (LAYER/DIAG/CSV row)
        diag = [h for h in log["hits"] if "DIAG" in h or "CSV] row" in h]
        if diag:
            print(f"    信号判定: {len(diag)} 条 (最近: {diag[-1][:90]})")

    print("\n[3] signals CSV:", end=" ")
    sig = check_signals_csv()
    if sig is None:
        print(f"❌ 未找到 {SIGNALS_CSV}")
        print("    → EA 尚未创建，可能未加载")
    else:
        print(f"✅ 存在 ({sig['size']:,} bytes, {sig['lines']} 行)")
        print(f"    最后更新 {sig['mtime'].strftime('%Y-%m-%d %H:%M:%S')}")

    # 状态判定
    print("\n" + "=" * 60)
    if running and init and sig is not None:
        print(" ✅ 状态: 30m2H EA 已加载且运行正常 (SimMode 全虚拟)")
    elif running:
        print(" ⚠️ 状态: 进程运行，但 EA 今日无初始化或 CSV 未创建")
        print("   → 检查图表 chart07 (XAUUSDm M30) 是否加载 30m2H_Strategy_EA")
    else:
        print(" ⏳ 状态: MT5 未运行")
    print("=" * 60)


if __name__ == "__main__":
    main()

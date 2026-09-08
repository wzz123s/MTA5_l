# -*- coding: utf-8 -*-
"""1H_M30_4H EA 运行状态监测 - DAD3B8CC 终端

检查:
  1. terminal64.exe 进程是否运行 (DAD3B8CC 数据目录)
  2. Experts 日志是否出现 1H_M30_4H EA 的 initialized 记录
  3. 模拟账单 CSV 是否创建/更新
"""
import os
import time
from datetime import datetime

TERMINAL_DIR = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
EANAME = "1H_M30_4H_CurrentCandidate_EA"
LEDGER = "1H_M30_4H_sim_deployment_trade_ledger.csv"


def check_process():
    """Check if MT5 (DAD3B8CC) is running by scanning processes."""
    found = False
    try:
        import subprocess
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
    """Check today's Experts log for 1H EA initialization."""
    today = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(TERMINAL_DIR, "MQL5", "logs", f"{today}.log")
    if not os.path.exists(log_path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(log_path))
    hits = []
    try:
        with open(log_path, "r", encoding="utf-16-le", errors="ignore") as f:
            for line in f:
                if EANAME in line or "1H_M30_4H" in line:
                    hits.append(line.strip()[:120])
    except Exception:
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if EANAME in line or "1H_M30_4H" in line:
                        hits.append(line.strip()[:120])
        except Exception as e:
            print(f"  ⚠️ 日志读取出错: {e}")
    return {"hits": hits, "log_mtime": mtime}


def check_ledger():
    """Check ledger CSV existence and last update."""
    path = os.path.join(TERMINAL_DIR, "MQL5", "Files", LEDGER)
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
    print(f" 1H_M30_4H EA 运行状态监测 (DAD3B8CC)")
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
        if log["hits"]:
            print(f"    含 {len(log['hits'])} 条 1H EA 相关记录:")
            for h in log["hits"][-5:]:
                print(f"      • {h}")
        else:
            print("    今日无 1H EA 记录 → EA 可能未加载")

    print("\n[3] 模拟账单 CSV:", end=" ")
    ledger = check_ledger()
    if ledger is None:
        print(f"❌ 未找到 {LEDGER}")
        print("    → EA 尚未创建账单，可能未加载或未触发")
    else:
        print(f"✅ 存在 ({ledger['size']:,} bytes, {ledger['lines']} 行)")
        print(f"    最后更新 {ledger['mtime'].strftime('%Y-%m-%d %H:%M:%S')}")

    # 状态判定
    print("\n" + "=" * 60)
    if running and ledger is not None and log and log["hits"]:
        print(" ✅ 状态: EA 已加载且运行正常")
    elif running and ledger is not None:
        print(" ⚠️ 状态: 进程运行，账单已创建，但今日无初始化日志（可能已运行多日）")
    else:
        print(" ⏳ 状态: 文件已就位，等待加载 EA 到图表")
        print("   → 按 MANUAL_LOAD_INSTRUCTIONS_20260811.txt 操作 (约2分钟)")
    print("=" * 60)


if __name__ == "__main__":
    main()

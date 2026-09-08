# -*- coding: utf-8 -*-
"""一键自动挂载 MCT_EA 到主监控终端（DAD3B8CC）的 USOILm H4 图表（chart13.chr）。

背景：chart13.chr 已在 2026-09-02 配好完整 MCT_EA expert 块（SimMode 虚拟盘、
InpAllowRealTrading=false），但未加入 order.wnd 启动窗口列表 -> 终端重启后图表未打开，
EA 从未加载（终端 09-03 08:55 启动日志中 10 个 EA 无 MCT_EA）。

本脚本补齐最后两步（与仓库其他 EA 部署脚本同套路）：
  1) chart13.chr 追加进 Profiles\\Charts\\Default\\order.wnd
  2) 重启【仅主终端】F:\\Program Files\\MetaTrader 5\\terminal64.exe（绝不动 EXNESS 终端）
  3) 轮询日志确认 "expert MCT_EA ... loaded successfully"，并检查 MCT_trade_ledger.csv

安全：EA 为虚拟盘；重启前若主账户有持仓会中止并提示。用法：
  python 大周期拐点\\策略开发\\阶段4_EA对齐\\auto_trade\\attach_mct_ea_to_chart.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
CHART = CHARTS / "chart13.chr"          # 已含 MCT_EA expert 块的 USOILm H4 空图表槽
ORDER = CHARTS / "order.wnd"
EXPERT = BASE / "MQL5" / "Experts" / "Advisors" / "MCT_EA.ex5"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5\terminal64.exe")
LOG_DIR = BASE / "logs"
FILES_DIR = BASE / "MQL5" / "Files"

# --- T20 守卫（2026-09-09 加）：本脚本假设 chart13.chr 已含 MCT_EA expert 块，
# 实测 chart13.chr 仅 2122B 且无 <expert> 块，而 MCT_EA 实际挂在 chart12.chr（USOILm,H4，
# 终端日志 09-08 00:21:31.059 loaded successfully，MCT_diag.csv 持续在写）。
# 盲跑会把空图表加进 order.wnd 并**重启主终端**（打断 9 个实例、其中 6 个在真下单）却挂不上 EA。
# 默认拒绝执行；确需重跑加 --force。依据 00_README T20。
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
try:
    import live_attribution as _la
except ImportError as _e:
    raise SystemExit(f"[abort] 无法加载 T20 守卫 live_attribution（{_e}）→ 拒绝盲跑部署脚本")
_la.guard_deploy("attach_mct_ea_to_chart.py", "MCT_EA", "chart13.chr")


def read_utf16(p: Path) -> str:
    raw = p.read_bytes()
    return raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")


def write_utf16(p: Path, text: str) -> None:
    p.write_bytes(text.encode("utf-16"))  # 与 MT5 .chr/order.wnd 一致：UTF-16 LE + BOM


def main_terminals() -> list:
    """主安装（F:\\Program Files\\MetaTrader 5\\terminal64.exe）的进程 PID 列表。"""
    pids = []
    try:
        import psutil  # 项目内已有（auto_run_tester_mct.py 使用）
        for p in psutil.process_iter(["pid", "exe"]):
            try:
                if p.info["exe"] and Path(p.info["exe"]).resolve() == TERMINAL_EXE.resolve():
                    pids.append(p.info["pid"])
            except Exception:
                continue
    except ImportError:
        out = subprocess.run(["wmic", "process", "where", "name='terminal64.exe'",
                              "get", "ProcessId,ExecutablePath", "/format:csv"],
                             capture_output=True, text=True).stdout
        for ln in out.splitlines():
            if TERMINAL_EXE.lower() in ln.lower() and ln.strip():
                try:
                    pids.append(int(ln.split(",")[-1]))
                except ValueError:
                    pass
    return pids


def check_positions() -> int:
    """主账户持仓数（只读）。返回 -1 表示无法判断。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
        import MetaTrader5 as mt5
    except Exception:
        return -1
    if not mt5.initialize(path=str(TERMINAL_EXE)):
        return -1
    try:
        pos = mt5.positions_get()
        return len(pos) if pos else 0
    finally:
        mt5.shutdown()


def wait_mct_loaded(timeout_s: float = 150.0) -> tuple[bool, list[str]]:
    """轮询最新日志看 MCT_EA 是否加载成功。"""
    deadline = time.time() + timeout_s
    hits: list[str] = []
    while time.time() < deadline:
        logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        for lg in logs[:3]:
            try:
                text = read_utf16(lg)
            except Exception:
                continue
            for ln in text.splitlines():
                if "MCT_EA" in ln and "loaded successfully" in ln:
                    hits.append(ln.strip())
            if hits:
                return True, hits
        time.sleep(5)
    return False, hits


def main() -> int:
    if not CHART.exists():
        print(f"[abort] 未找到 {CHART}")
        return 2
    text = read_utf16(CHART)
    if "name=MCT_EA" not in text or "path=Experts\\Advisors\\MCT_EA.ex5" not in text:
        print("[abort] chart13.chr 里没有 MCT_EA expert 块，请先核对配置")
        return 2
    if not EXPERT.exists():
        print(f"[abort] 终端缺少 {EXPERT}")
        return 2

    n = check_positions()
    if n > 0:
        print(f"[abort] 主账户有 {n} 个持仓，为避免打断交易请稍后（无持仓）再运行")
        return 3
    print(f"[preflight] 主账户持仓: {n if n >= 0 else '无法读取(继续)'}")

    # 1) order.wnd 追加 chart13
    ow = read_utf16(ORDER) if ORDER.exists() else ""
    if "chart13.chr" in ow:
        print("[order.wnd] chart13.chr 已在列表，跳过追加")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(ORDER, ORDER.with_name(f"order.wnd.bak_attachMCT_{ts}"))
        shutil.copy2(CHART, CHART.with_name(f"chart13.chr.bak_attachMCT_{ts}"))
        ow = ow.rstrip("\r\n") + "\r\nchart13.chr\r\n"
        write_utf16(ORDER, ow)
        print(f"[order.wnd] 已备份并追加 chart13.chr (bak_attachMCT_{ts})")

    # 2) 重启主终端（只杀主安装，不动 EXNESS）
    pids = main_terminals()
    print(f"[restart] 主终端 PID: {pids or '未运行(直接启动)'}")
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    time.sleep(5)
    subprocess.Popen([str(TERMINAL_EXE)], cwd=str(TERMINAL_EXE.parent))
    print("[restart] 已启动主终端，等待 EA 加载 ...")

    # 3) 验证
    ok, hits = wait_mct_loaded()
    if ok:
        print("[verify] MCT_EA 加载成功:")
        for h in hits[-3:]:
            print("   ", h)
        time.sleep(10)  # 给 OnInit 一次机会写账本表头
        for f in ("MCT_trade_ledger.csv", "MCT_diag.csv"):
            fp = FILES_DIR / f
            print(f"[verify] {f}: {'存在 %dB' % fp.stat().st_size if fp.exists() else '尚未生成'}")
        return 0
    print("[verify] 超时未在日志发现 MCT_EA 加载行；请人工检查终端（图表 chart13 是否打开）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

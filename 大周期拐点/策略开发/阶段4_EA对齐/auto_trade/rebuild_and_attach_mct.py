# -*- coding: utf-8 -*-
"""重建 chart13.chr（MCT_EA）为 MT5 原生紧凑格式并挂载到主监控终端。

背景：旧 chart13.chr（2026-09-02 脚本生成）整文件"每行后空一行"，与 MT5 自写紧凑格式
（chart01-12）不同；加入 order.wnd 重启后 MT5 静默跳过该窗口，MCT_EA 从不加载。

方案：以已验证可加载的 chart12.chr（Oil_DataEvent_EA, USOILm H4）为结构模板，
替换为紧凑版 MCT_EA expert 块 + 随机 id 写回 chart13.chr；确保 chart13 在 order.wnd；
只重启主终端并轮询验证 "expert MCT_EA ... loaded successfully"。

用法: python rebuild_and_attach_mct.py
"""
from __future__ import annotations

import random
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
CHART = CHARTS / "chart13.chr"
TEMPLATE = CHARTS / "chart12.chr"
ORDER = CHARTS / "order.wnd"
EXPERT = BASE / "MQL5" / "Experts" / "Advisors" / "MCT_EA.ex5"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5\terminal64.exe")
LOG_DIR = BASE / "logs"
FILES_DIR = BASE / "MQL5" / "Files"

CRLF = "\r\n"

# --- T20 守卫（2026-09-09 加）：本脚本假设 chart12=Oil_DataEvent_EA（结构模板）、
# chart13=MCT_EA（目标），实测 **chart12 已经是 MCT_EA**、chart13 是无 expert 块的空图表
# （Oil_DataEvent_EA 实际在 chart10，且原油三 EA 已于 09-07 从终端摘除）。
# 盲跑会以 MCT 自己的图表为模板再造一个 chart13=MCT_EA → **MCT 双挂**（同 magic 411103，
# MCT_diag.csv / MCT_trade_ledger.csv 被两实例交替覆盖），并重启主终端打断全部 EA。
# 默认拒绝执行；确需重跑加 --force。依据 00_README T20。
import sys

sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
try:
    import live_attribution as _la
except ImportError as _e:
    raise SystemExit(f"[abort] 无法加载 T20 守卫 live_attribution（{_e}）→ 拒绝盲跑部署脚本")
_la.guard_deploy("rebuild_and_attach_mct.py", "MCT_EA", "chart13.chr",
                 template_chart="chart12.chr", template_ea="Oil_DataEvent_EA")

MCT_INPUTS = [
    ("InpMagic", "411103"), ("InpSymbol", "USOILm"),
    ("InpRiskPct", "1.0"), ("InpLots", "0.01"), ("InpSimStartBalance", "500.0"),
    ("InpD1SMA13", "13"), ("InpD1SMA55", "55"), ("InpGlue", "0.003"),
    ("InpArmDays", "40"), ("InpD1DataStart", "2019.03.01"),
    ("InpH4SMA5", "5"), ("InpH4SMA13", "13"), ("InpH4SMA55", "55"),
    ("InpMinLen", "8"), ("InpH4DataStart", "2021.07.01"),
    ("InpStopLoPct", "0.008"), ("InpStopHiPct", "0.025"),
    ("InpTp1R", "1.5"), ("InpFrac1", "0.3333"), ("InpTimeExitBars", "120"),
    ("InpBiasOn", "true"), ("InpSpreadCost", "0.0"), ("InpSwapCostBar", "0.0"),
    ("InpSimMode", "true"), ("InpAllowRealTrading", "false"),
    ("InpExportLedger", "true"), ("InpExportDiag", "false"),
]

EXPERT_BLOCK = (
    "<expert>" + CRLF +
    "name=MCT_EA" + CRLF +
    "path=Experts\\Advisors\\MCT_EA.ex5" + CRLF +
    "expertmode=1" + CRLF +
    "<inputs>" + CRLF +
    CRLF.join(f"{k}={v}" for k, v in MCT_INPUTS) + CRLF +
    "</inputs>" + CRLF +
    "</expert>"
)


def read_text(p: Path) -> str:
    raw = p.read_bytes()
    return raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")


def write_utf16(p: Path, text: str) -> None:
    p.write_bytes(text.encode("utf-16"))


def main_terminal_pids() -> list:
    pids = []
    try:
        import psutil
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
    try:
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


def rebuild_chart13() -> None:
    tpl = read_text(TEMPLATE)
    start = tpl.find("<expert>")
    end = tpl.find("</expert>")
    if start < 0 or end < 0:
        raise SystemExit("chart12.chr 里找不到 expert 块，模板无效")
    end += len("</expert>")
    new = tpl[:start] + EXPERT_BLOCK + tpl[end:]
    lines = new.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("id="):
            lines[i] = "id=%d" % random.randrange(10**17, 10**18)
            break
    new = "\n".join(lines)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(CHART, CHART.with_name(f"chart13.chr.bak_rebuild_{ts}"))
    write_utf16(CHART, new)
    print(f"[rebuild] chart13.chr 已重建（chart12 模板 + MCT_EA 块，bak_rebuild_{ts}）")


def ensure_order() -> None:
    ow = read_text(ORDER) if ORDER.exists() else ""
    if "chart13.chr" in ow:
        print("[order.wnd] chart13.chr 已在列表")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(ORDER, ORDER.with_name(f"order.wnd.bak_{ts}"))
    ow = ow.rstrip("\r\n") + CRLF + "chart13.chr" + CRLF
    write_utf16(ORDER, ow)
    print(f"[order.wnd] 已追加 chart13.chr（bak_{ts}）")


def wait_mct_loaded(timeout_s: float = 150.0) -> tuple[bool, list[str]]:
    deadline = time.time() + timeout_s
    hits: list[str] = []
    while time.time() < deadline:
        logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        for lg in logs[:3]:
            try:
                text = read_text(lg)
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
    if not TEMPLATE.exists() or not EXPERT.exists():
        print("[abort] 模板 chart12.chr 或 MCT_EA.ex5 缺失")
        return 2
    n = check_positions()
    if n > 0:
        print(f"[abort] 主账户有 {n} 个持仓，请稍后（无持仓）再运行")
        return 3
    print(f"[preflight] 主账户持仓: {n if n >= 0 else '无法读取(继续)'}")

    rebuild_chart13()
    ensure_order()

    pids = main_terminal_pids()
    print(f"[restart] 主终端 PID: {pids or '未运行(直接启动)'}")
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    time.sleep(5)
    subprocess.Popen([str(TERMINAL_EXE)], cwd=str(TERMINAL_EXE.parent))
    print("[restart] 已启动主终端，等待 EA 加载 ...")

    ok, hits = wait_mct_loaded()
    if ok:
        print("[verify] MCT_EA 加载成功:")
        for h in hits[-3:]:
            print("   ", h)
        time.sleep(8)
        for f in ("MCT_trade_ledger.csv", "MCT_diag.csv"):
            fp = FILES_DIR / f
            print(f"[verify] {f}: {'存在 %dB' % fp.stat().st_size if fp.exists() else '尚未生成'}")
        return 0
    print("[verify] 超时未在日志发现 MCT_EA 加载行；请人工检查终端图表 chart13")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

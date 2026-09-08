# -*- coding: utf-8 -*-
"""策略监测循环（30 分钟一次）：完整刷新监控 -> 事件门状态 -> EA运行状态 -> 生成监测报告。

由 DSH harness 的 tool-jobs 后台任务按 30 分钟周期调用（任务登记在 harness 内，非 Windows 计划任务）。
注：旧版文案误写为「每 6 小时」；2026-09-08 先按实测产出节奏改为 30 分钟，
后经 harness 会话存储中的 tool-jobs 完成通知核实，驱动方为 DSH harness——
若 DSH Web 进程未运行，本监测循环会随之停止（不随开机自启）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
PY = r"F:\Program Files\Python\python.exe"
MONITOR = ROOT / "scripts" / "monitor_all_strategies.py"
DASH = ROOT / "observation_dashboard"
REPORT_DIR = DASH / "监测报告"
EVENTS_CSV = ROOT / "宏观日历研究" / "data" / "calendar_export.csv"
WHITELIST = {"USD", "EUR", "GBP", "CAD"}
TERMINAL_LOG = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\logs")


def run_monitor() -> tuple:
    """先尝试完整刷新（拉最新MT5 K线）；失败（终端离线等）自动降级缓存重算。返回 (ok, refreshed)。"""
    logf = REPORT_DIR / "_monitor_run.log"
    with logf.open("w", encoding="utf-8") as fh:
        try:
            res = subprocess.run([PY, str(MONITOR)], stdout=fh, stderr=fh, timeout=1200)
        except subprocess.TimeoutExpired:
            print("[monitor] 完整刷新 TIMEOUT，降级")
            res = None
    if res is not None and res.returncode == 0:
        print("[monitor] 完整刷新 OK")
        return True, True
    with logf.open("a", encoding="utf-8") as fh:
        try:
            res2 = subprocess.run([PY, str(MONITOR), "--no-refresh"], stdout=fh, stderr=fh, timeout=900)
        except subprocess.TimeoutExpired:
            print("[monitor] 降级 TIMEOUT")
            return False, False
    print("[monitor] 降级缓存 rc:", res2.returncode)
    return res2.returncode == 0, False


def upcoming_events(hours: int = 12) -> list:
    df = pd.read_csv(EVENTS_CSV, sep="|", dtype={"event_id": "int64", "time": "int64"})
    df["t"] = pd.to_datetime(df["time"], unit="s", utc=True)
    now = datetime.now(timezone.utc)
    hi = df[(df["importance"] >= 3) & (df["currency"].isin(WHITELIST))]
    fut = hi[(hi["t"] >= now) & (hi["t"] <= now + timedelta(hours=hours))]
    return fut.sort_values("t")[["t", "event_name", "currency"]].to_dict("records")


def ea_load_state() -> str:
    logs = sorted(TERMINAL_LOG.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for log in logs[:3]:
        raw = log.read_bytes()
        enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
        try:
            text = raw.decode(enc, errors="ignore")
        except Exception:
            continue
        loaded = [ln.split("expert ")[1].split(" (")[0] for ln in text.splitlines()
                  if "expert " in ln and "loaded successfully" in ln]
        if loaded:
            return str(len(set(loaded))) + " 个 EA 加载（" + ",".join(sorted(set(loaded))) + "）"
    return "未找到 EA 加载日志"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ok, refreshed = run_monitor()
    if not ok:
        print("[monitor] FAILED - 报告将基于上次数据生成")

    dash = pd.read_csv(DASH / "dashboard.csv")
    lines = []
    lines.append("# 策略监测报告（30 分钟自动）")
    lines.append("")
    lines.append("> 生成：" + now.strftime("%Y-%m-%d %H:%M UTC") + " ｜ 数据刷新：" +
                 ("成功(MT5完整刷新)" if refreshed else "降级(缓存数据)") if ok else
                 "失败(使用上次数据)")
    lines.append("> EA 状态：" + ea_load_state())

    lines.append("")
    lines.append("## 总览")
    lines.append("| 策略 | 交易 | 累计(pts) | 0.5%/1%净值 | 新增 | 回补 | 实盘手数 | 浮盈USD | 数据bar | 警告 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in dash.iterrows():
        lines.append("| " + str(r["strategy"]) + " | " + str(int(r["total_trades"])) + " | " +
                     format(float(r["total_weighted_pts"]), ",.0f") + " | " +
                     "$" + format(float(r["equity_0_5pct"]), ",.0f") + "/" + format(float(r["equity_1pct"]), ",.0f") + " | " +
                     str(int(r["new_since_last"])) + " | " + str(int(r["backfill_since_last"])) + " | " +
                     format(float(r["real_volume"]), ".2f") + " | $" + format(float(r["real_profit"]), ",.2f") + " | " +
                     str(r["data_last_bar"]) + " | " + str(r["warnings"]) + " |")

    lines.append("")
    lines.append("## 未来 12h 白名单高影响事件（USD/EUR/GBP/CAD，事件门关注）")
    evs = upcoming_events(12)
    if evs:
        for e in evs:
            lines.append("- " + e["t"].strftime("%m-%d %H:%M UTC") + " [" + e["currency"] + "] " + e["event_name"])
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("## 实盘持仓（MT5 实时读数）")
    any_open = False
    for _, r in dash.iterrows():
        if float(r["real_volume"]) > 0:
            any_open = True
            lines.append("- " + str(r["strategy"]) + ": " + format(float(r["real_volume"]), ".2f") + " 手，浮盈 $" +
                         format(float(r["real_profit"]), ",.2f"))
    if not any_open:
        lines.append("- 无实盘持仓")

    lines.append("")
    lines.append("## 最近24h新增信号")
    for strat in ["1H_M30_4H", "30m2H", "2H_M30_6H", "USOIL2H", "USOIL4H", "BiasReversal"]:
        f = DASH / strat / "trades_snapshot.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, parse_dates=["signal_time"])
        df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
        recent = df[df["signal_time"] >= now - timedelta(hours=24)]
        if len(recent):
            lines.append("")
            lines.append("### " + strat + "（" + str(len(recent)) + " 笔）")
            for _, r in recent.tail(8).iterrows():
                lines.append("- " + str(r["signal_time"]) + " " + str(r["dir"]) + " " + str(r["mode"]) +
                             " 盈亏" + format(float(r["weighted_pts"]), "+,.1f") + "pts (" + str(r["stage3_reason"]) + ")")

    warn_count = sum(1 for _, r in dash.iterrows() if str(r["warnings"]) != "无")
    lines.append("")
    lines.append("## 警戒摘要：" + str(warn_count) + " 个策略有警告")
    for _, r in dash.iterrows():
        if str(r["warnings"]) != "无":
            lines.append("- **" + str(r["strategy"]) + "**：" + str(r["warnings"]))
    lines.append("")
    lines.append("---")
    lines.append("*自动生成：scripts/monitor_cycle.py（DSH harness tool-jobs，30 分钟周期）*")

    stamp = now.strftime("%Y%m%d_%H%M")
    out = REPORT_DIR / ("监测报告_" + stamp + ".md")
    # 报告用 utf-8-sig（带 BOM）：保证记事本/旧 ANSI 工具按 UTF-8 识别，避免中文乱码
    out.write_text("\n".join(lines), encoding="utf-8-sig")
    print("[report]", out)

    files = sorted(REPORT_DIR.glob("监测报告_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[20:]:
        old.unlink()
    print("[cleanup] kept", min(len(files), 20), "reports")

    # SimMode 观察（调试终端 30m2H SimMode，独立滚动记录，不污染 dashboard 表）
    try:
        subprocess.run(
            [PY, str(ROOT / "scripts" / "observe_sim_30m2h.py")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
        )
        print("[sim] SimMode observation appended")
    except Exception as e:
        print("[sim] SimMode observation failed:", e)


if __name__ == "__main__":
    main()

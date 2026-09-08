# -*- coding: utf-8 -*-
"""30m2H SimMode 调试终端观察：读取 B695BCB6（MetaTrader 5 EXNESS）的 SimMode EA 输出，
生成快照并追加到 observation_dashboard/SimMode_30m2H/30m2H_SimMode_观察日志.md。

SimMode 口径：InpSimMode=true（虚拟，不下单）→ signals_export.csv 记录逐 bar 决策
（decision=SIGNAL 表示 SimMode 内部触发了虚拟信号）；trade_ledger.csv 在 SimMode 下仅表头
（真实平仓才落盘），虚拟成交以 signals 决策流观测。

用法：python scripts/observe_sim_30m2h.py
"""
from __future__ import annotations
from pathlib import Path
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
SIM_FILES = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Files")
OUT_DIR = ROOT / "observation_dashboard" / "SimMode_30m2H"
SIG_CSV = SIM_FILES / "30m2H_strategy_signals_export.csv"
LED_CSV = SIM_FILES / "30m2H_strategy_trade_ledger.csv"

sys.stdout.reconfigure(encoding="utf-8")


def read_csv(p: Path):
    if not p.exists():
        return None
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            df = pd.read_csv(p, encoding=enc, on_bad_lines="skip")
            return df
        except Exception:
            continue
    return None


def fmt(ts) -> str:
    if pd.isna(ts):
        return "-"
    return str(ts)


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append(f"## 快照 {now}")

    sig = read_csv(SIG_CSV)
    led = read_csv(LED_CSV)

    # EA 运行状态（signals 文件新鲜度）
    if sig is not None and not sig.empty:
        mtime = datetime.fromtimestamp(SIG_CSV.stat().st_mtime, tz=timezone.utc)
        fresh = (datetime.now(timezone.utc) - mtime).total_seconds()
        lines.append(f"- EA 状态: 运行中（signals 最新 {mtime:%H:%M:%S} UTC，{int(fresh)}s 前更新，{len(sig)} 行）")
        # 决策分布
        if "decision" in sig.columns:
            dc = sig["decision"].fillna("N/A").value_counts().to_dict()
            lines.append(f"- 决策分布: {dc}")
        if "skip_reason" in sig.columns:
            sc = sig["skip_reason"].fillna("").astype(str)
            sc = sc[sc != ""].value_counts().to_dict()
            if sc:
                lines.append(f"- skip 原因: {sc}")
        # 最近 SIGNAL（虚拟触发）
        sig_sig = sig[sig["decision"].astype(str).str.upper().eq("SIGNAL")] if "decision" in sig.columns else sig.iloc[0:0]
        if len(sig_sig):
            lines.append(f"- 虚拟信号触发（decision=SIGNAL）: {len(sig_sig)} 条，最近:")
            for _, r in sig_sig.tail(5).iterrows():
                t = fmt(r.get("bar_time"))
                lines.append(f"    - {t} dir={r.get('h2_dir','-')} cross={r.get('m30_cross','-')} reason={r.get('skip_reason','-')}")
        else:
            lines.append("- 虚拟信号触发: 0（尚无 decision=SIGNAL）")
        # 最后一行（当前 bar 状态）
        last = sig.tail(1).iloc[0]
        def num(v):
            try:
                f = float(v)
                return f"{f:.3f}"
            except (TypeError, ValueError):
                return "-"
        lines.append("- 最新 bar: " + fmt(last.get('bar_time')) + " close=" + num(last.get('close')) +
                     " sma5=" + num(last.get('m30_sma5')) + " sma13=" + num(last.get('m30_sma13')) +
                     " h2_dir=" + str(last.get('h2_dir')) + " decision=" + str(last.get('decision')) +
                     " skip=" + str(last.get('skip_reason')))
    else:
        lines.append("- EA 状态: 未见 signals 输出（SimMode EA 未运行或尚未写入）")

    if led is not None and len(led) > 1:
        lines.append(f"- 虚拟 ledger: {len(led) - 1} 条（SimMode 通常仅表头，真实平仓才落盘）")
    else:
        lines.append("- 虚拟 ledger: 仅表头（SimMode 下虚拟成交不落盘，符合设计）")

    lines.append("")

    # 追加记录
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rec = OUT_DIR / "30m2H_SimMode_观察日志.md"
    if not rec.exists():
        rec.write_text("# 30m2H SimMode 观察日志（调试终端 MetaTrader 5 EXNESS / B695BCB6）\n"
                       "> 口径：SimMode 虚拟信号（Magic 302027，不下单），EA 修复版；信号与主终端真实 30m2H 同源逻辑对照。\n"
                       "> 更新：python scripts/observe_sim_30m2h.py（可手动或挂任务计划）。\n\n", encoding="utf-8")
    body = rec.read_text(encoding="utf-8")
    # 保持记录有界：最多保留最近 60 个快照块
    blocks = body.split("## 快照 ")
    body = blocks[0] + "".join("## 快照 " + b for b in blocks[1:][-60:])
    rec.write_text(body + "\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("[record]", rec)


if __name__ == "__main__":
    main()

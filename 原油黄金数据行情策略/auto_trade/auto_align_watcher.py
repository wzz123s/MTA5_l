# -*- coding: utf-8 -*-
"""M4.5 Tester ledger 自动回收 + 逐笔对齐 watcher。
用法: python auto_trade/auto_align_watcher.py [--name gold|oil] [--timeout-min 240]
流程: 轮询 Tester agent 目录的 Gold/Oil_DataEvent_trade_ledger.csv
      → 文件存在且 60s 无增长（回测完成）→ 复制到 data/validation/tester_actual_<name>.csv
      → 运行 align_ledgers.py → 结果写入 报告/对齐结果_<ts>.md
前置: 人工在 MT5 策略测试面板点【开始】（沙箱无法点击，见 M4 记录）
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
TROOT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65")
REPORTS = ROOT / "报告"

LEDGER_NAMES = {"gold": "Gold_DataEvent_trade_ledger.csv",
                "oil": "Oil_DataEvent_trade_ledger.csv"}


def find_ledger(name: str) -> Path | None:
    if not TROOT.exists():
        return None
    for p in TROOT.rglob(LEDGER_NAMES[name]):
        return p
    return None


def rows(p: Path) -> int:
    try:
        return sum(1 for _ in open(p, "rb")) - 1
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="gold", choices=["gold", "oil"])
    ap.add_argument("--timeout-min", type=int, default=240)
    args = ap.parse_args()

    print(f"[watcher] waiting for {LEDGER_NAMES[args.name]} (timeout {args.timeout_min} min) ...", flush=True)
    deadline = time.time() + args.timeout_min * 60
    last_rows = -1
    stable_since = None
    ledger = None
    while time.time() < deadline:
        time.sleep(20)
        p = find_ledger(args.name)
        if p is None:
            print(f"[watcher] {datetime.now().strftime('%H:%M:%S')} no ledger yet", flush=True)
            continue
        r = rows(p)
        print(f"[watcher] {datetime.now().strftime('%H:%M:%S')} ledger {p.name} rows={r}", flush=True)
        if r == last_rows:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since > 60:
                ledger = p
                break
        else:
            stable_since = None
        last_rows = r

    if ledger is None:
        print("[watcher] TIMEOUT: ledger not found", flush=True)
        return 1

    dst = ROOT / "data" / "validation" / f"tester_actual_{args.name}.csv"
    shutil.copy2(ledger, dst)
    print(f"[watcher] ledger copied: {ledger} -> {dst} ({rows(dst)} rows)", flush=True)

    exp = ROOT / "data" / "validation" / f"expected_ledger_{args.name}.csv"
    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate" / "align_ledgers.py"),
                          "--expected", str(exp), "--actual", str(dst), "--name", args.name],
                         cwd=str(ROOT))
    print(f"[watcher] align_ledgers rc={res.returncode}", flush=True)

    # 汇总报告
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    report = REPORTS / f"对齐结果_{args.name}_{now}.md"
    report.write_text(
        f"# Tester 逐笔对齐结果（{args.name}）\n\n"
        f"> 自动回收：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"> actual ledger：{dst}（{rows(dst)} 行）\n"
        f"> expected ledger：{exp}\n\n"
        f"详见上方 align_ledgers.py 输出（终端窗口）。\n"
        f"PASS 条件：expected=actual=matched 100% 且字段差异 0。\n"
        f"已知差异源（M3.6/M4）：post_n 止损、stage3 退出、6H 门 bias13、EA 同向/损失冷却。\n",
        encoding="utf-8")
    print(f"[watcher] report: {report}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

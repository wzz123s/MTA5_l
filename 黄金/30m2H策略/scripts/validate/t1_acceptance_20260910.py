# -*- coding: utf-8 -*-
"""T1 主线 v3.37 正式验收脚本（可重复）。

口径（见 T1_最终验收报告_20260910.md）：
  - EA 侧：Tester ledger 去重（anchor+dir），窗口 2020-03-06~2026-06-11
  - Python 侧：ea_executable_diag=True + rolling_merged=True + MAXPOS=3
  - Layer1：以 EA signals_export 真值过滤（completed |bias55|>3% 或 q2_early_pass）
  - 剔除：EA Tester 收盘不可成交（Market closed）两笔已知伪差
  - 判据：±120min 同向匹配 >= 94%
运行：从 参考实现工程 或本目录执行均可（脚本自动加引擎路径）。
用法：python 黄金/30m2H策略/scripts/validate/t1_acceptance_20260910.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
REF = os.path.join(ROOT, "黄金", "30m2H策略", "参考实现工程")
for p in (REF, os.path.join(REF, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _build_expected_ledger as ble  # noqa: E402
import _current_baseline as cb  # noqa: E402

DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")
EA_SIG = os.path.join(DST, "30m2H_strategy_signals_export_t1export3_20260910.csv")
EA_LED = os.path.join(DST, "30m2H_strategy_trade_ledger.csv")
OUT_LED = os.path.join(DST, "30m2H_python_acceptance_expected_trade_ledger_mp3.csv")
OUT_MD = os.path.join(DST, "T1_验收报告_acceptance_run_20260910.md")

MARKET_CLOSED = {("2022-03-07 19:30", "L"), ("2026-01-26 18:30", "S")}
W0 = pd.Timestamp("2020-03-06")
W1 = pd.Timestamp("2026-06-11 23:59")


def read_csv(path, **kw):
    for enc in ("utf-8-sig", "utf-8", "gbk", "mbcs", "utf-16"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except Exception:
            continue
    raise RuntimeError("read fail " + path)


def norm(f):
    f = f.copy()
    t = f["signal_anchor_time"].astype(str)
    a = pd.to_datetime(t, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if a.isna().any():
        a = pd.to_datetime(t, format="%Y.%m.%d %H:%M", errors="coerce")
    if a.isna().any():
        a = pd.to_datetime(t, errors="coerce")
    f["anchor"] = a
    f["dir"] = f["dir"].astype(str).str.upper().map({"BUY": "L", "SELL": "S"})
    return f.dropna(subset=["anchor"]).drop_duplicates(["anchor", "dir"]).sort_values("anchor").reset_index(drop=True)


def main() -> None:
    print("loading EA Layer1 truth:", EA_SIG, flush=True)
    es = read_csv(EA_SIG)
    es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
    es = es[["bar_time", "h2_comp_bias55", "q2_early_pass"]].dropna()
    es["layer1_ea"] = (es["h2_comp_bias55"] > 3.0) | (es["q2_early_pass"] == 1)
    ea_map = dict(zip(es["bar_time"], es["layer1_ea"].astype(int)))

    orig = cb.apply_layer3_ea_executable

    def gate_wrapper(final_acc, h2, top_pct=34, lookback=500):
        threshold, out = orig(final_acc, h2, top_pct=top_pct, lookback=lookback)
        keep = []
        for _, row in out.iterrows():
            ev = pd.Timestamp(row["date"]) + pd.Timedelta(minutes=30)
            if bool(ea_map.get(ev, 1)):
                keep.append(row)
        return threshold, pd.DataFrame(keep).reset_index(drop=True)

    cb.apply_layer3_ea_executable = gate_wrapper

    print("building Python expected ledger (ea + rolling + MAXPOS3 + EA Layer1 truth)...", flush=True)
    ble.LEDGER_PATH = OUT_LED
    ble.SUMMARY_PATH = OUT_MD.replace("_acceptance_run", "_summary")
    ble.build_ledger(ea_executable=True, rolling_merged=True, max_pos_sim=3)

    ea = norm(read_csv(EA_LED))
    py = norm(read_csv(OUT_LED))
    ea = ea[(ea["anchor"] >= W0) & (ea["anchor"] <= W1)].reset_index(drop=True)
    py = py[(py["anchor"] >= W0) & (py["anchor"] <= W1)].reset_index(drop=True)
    key = py["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + py["dir"]
    py = py[~key.isin([f"{t}|{d}" for t, d in MARKET_CLOSED])].reset_index(drop=True)

    def calc(p, tol):
        use = set()
        mm = 0
        for _, r in p.iterrows():
            cand = ea[(ea["dir"] == r["dir"]) & ((ea["anchor"] - r["anchor"]).abs() <= pd.Timedelta(minutes=tol)) & (~ea.index.isin(use))]
            if len(cand):
                use.add(cand.index[0])
                mm += 1
        return mm, len(p), len(ea) - len(use)

    rows = []
    for tol in (0, 30, 60, 120, 180):
        m, n, ex = calc(py, tol)
        rows.append((tol, m, n, round(100 * m / max(n, 1), 2)))
    m, n, ex = calc(py, 120)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# T1 主线 v3.37 验收运行报告（可重复脚本）\n\n")
        f.write(f"- Python expected: {n}\n- matched(±120): {m}\n- 对齐率: {100 * m / max(n, 1):.2f}%\n")
        f.write(f"- missing: {n - m}\n- EA extra: {ex}\n\n")
        f.write("| ±容差 | matched | 对齐率 |\n|---|---:|---:|\n")
        for tol, mm, nn, pct in rows:
            f.write(f"| {tol} | {mm}/{nn} | {pct}% |\n")
    print(f"PASS? {100 * m / max(n, 1) >= 94.0} | matched {m}/{n} = {100 * m / max(n, 1):.2f}% | report: {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()

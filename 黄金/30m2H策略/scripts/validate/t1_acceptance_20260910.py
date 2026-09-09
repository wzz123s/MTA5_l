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
import bisect

import pandas as pd
import numpy as np

ROOT = r"F:\use_code\MTA5_l"
REF = os.path.join(ROOT, "黄金", "30m2H策略", "参考实现工程")
for p in (REF, os.path.join(REF, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _build_expected_ledger as ble  # noqa: E402
import _current_baseline as cb  # noqa: E402

DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")
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
    print("loading df/h2 once for Python Layer1 replica...", flush=True)
    dfx, h2x, _ = cb.load_market_context()
    dfx = dfx.copy().reset_index(drop=True)
    dfx["date"] = pd.to_datetime(dfx["date"])
    h2x = h2x.copy().reset_index(drop=True)
    h2x["date"] = pd.to_datetime(h2x["date"])
    h2x = h2x[h2x["SMA_55"].notna()].reset_index(drop=True)
    close_map = dict(zip(dfx["date"], dfx["close"].astype(float)))
    ht = h2x["date"].values.astype("datetime64[ns]")
    s55 = h2x["SMA_55"].values.astype(float)

    def layer1_python(t_open):
        tick = np.datetime64(t_open) + np.timedelta64(30, "m")
        idx = int(bisect.bisect_right(ht, tick)) - 1
        if idx < 0:
            return False
        cur_open = pd.Timestamp(ht[idx])
        completed_b55 = abs((h2x["close"].iloc[idx] - h2x["SMA_55"].iloc[idx]) / h2x["SMA_55"].iloc[idx]) * 100
        if completed_b55 > 3.0:
            return True
        if idx < 1 or t_open < cur_open or s55[idx] == 0:
            return False
        prev_open = pd.Timestamp(ht[idx - 1])
        if t_open < prev_open:
            return False
        elapsed = int((t_open - prev_open) / pd.Timedelta(minutes=30))
        if elapsed < 2:
            return False
        partial = close_map.get(pd.Timestamp(t_open))
        if partial is None:
            return False
        est55 = s55[idx] + (partial - s55[idx]) / 55.0
        return bool(abs((partial - est55) / est55) * 100 > 3.0)

    orig = cb.apply_layer3_ea_executable

    def gate_wrapper(final_acc, h2, top_pct=34, lookback=500):
        threshold, out = orig(final_acc, h2, top_pct=top_pct, lookback=lookback)
        keep = []
        for _, row in out.iterrows():
            if layer1_python(pd.Timestamp(row["date"])):
                keep.append(row)
        return threshold, pd.DataFrame(keep).reset_index(drop=True)

    cb.apply_layer3_ea_executable = gate_wrapper

    print("building Python expected ledger (ea + rolling + MAXPOS3 + Python Layer1 replica)...", flush=True)
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

# -*- coding: utf-8 -*-

"""模式判定层深挖: EA 信号 vs Python 候选逐信号归因

对差异信号 (EA 独有 349 / Python 独有 105) 逐条检查:
  - Layer1 状态 (q2_pass_set)
  - 滚动 post_n counter
  - pre_cross 条件 (gap / setup)
  - cross 条件 (SMA 翻转)
"""
import os
import re
import sys

os.chdir(r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程\scripts")

import numpy as np
import pandas as pd

import _current_baseline as base
from processing.smma import calc_smma

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260812.log"
START = 902309380
CH = 8 * 1024 * 1024


def extract_ea_signals():
    """EA Layer1 PASS 的信号: anchor -> (mode, 判定时刻)"""
    sigs = {}
    with open(LOG, "rb") as f:
        f.seek(START)
        carry = b""
        while True:
            chunk = f.read(CH)
            if not chunk:
                break
            data = carry + chunk
            txt = data.decode("utf-16-le", errors="ignore")
            lines = txt.split("\n")
            carry = lines[-1].encode("utf-16-le")
            for ln in lines[:-1]:
                m = re.search(
                    r"\[M30 CLOSE\] \[DIAG\] Candidate \| mode=(\S+).*anchor=([\d.]+ [\d:]+)", ln
                )
                if not m:
                    continue
                key = m.group(2)
                if key in sigs:
                    continue
                # 检查该信号是否 Layer1 PASS: 后续行有 LAYER1 PASS 且判定时刻匹配?
                sigs[key] = m.group(1)
    return sigs


def main():
    df, final_acc = base.build_final_accepted(
        spec_lo=5, spec_hi=35, ea_executable_diag=True, rolling_merged=True,
    )
    # Python 候选 (anchor -> mode)
    py_sigs = {}
    for _, row in final_acc.iterrows():
        a = pd.to_datetime(row["date"]).strftime("%Y.%m.%d %H:%M")
        if a not in py_sigs:
            py_sigs[a] = row["mode"]

    # EA 信号 (模式判定, Layer1 前 — 用 Layer1 PASS 过滤)
    # 从日志: 模式信号 + LAYER1 PASS 行 (判定时刻 - 30min = anchor)
    ea_all = extract_ea_signals()
    ea_l1 = set()
    with open(LOG, "rb") as f:
        f.seek(START)
        carry = b""
        while True:
            chunk = f.read(CH)
            if not chunk:
                break
            data = carry + chunk
            txt = data.decode("utf-16-le", errors="ignore")
            lines = txt.split("\n")
            carry = lines[-1].encode("utf-16-le")
            for ln in lines[:-1]:
                m = re.search(r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}):\d{2}.*\[M30 CLOSE\].*LAYER1 PASS", ln)
                if m:
                    t = pd.to_datetime(m.group(1), format="%Y.%m.%d %H:%M")
                    ea_l1.add((t - pd.Timedelta(minutes=30)).strftime("%Y.%m.%d %H:%M"))
    ea_sigs = {k: v for k, v in ea_all.items() if k in ea_l1}
    print(f"EA Layer1 PASS 信号: {len(ea_sigs)}  Python 候选: {len(py_sigs)}")
    ea_k, py_k = set(ea_sigs), set(py_sigs)
    print(f"交集: {len(ea_k & py_k)}")
    ea_only = ea_k - py_k
    py_only = py_k - ea_k
    print(f"EA 独有: {len(ea_only)}  Python 独有: {len(py_only)}")

    # ---- Python 侧数据准备 ----
    # Layer1 (q2_pass_set)
    h2 = base.load_h2_context()
    q2_pass_set, q2_factor_map, _, _ = base.h2t.early_precompute(h2, df, 2, False)
    q2_times = set()
    if q2_pass_set:
        q2_times = set(df.loc[list(q2_pass_set), "date"].dt.strftime("%Y.%m.%d %H:%M"))
    # 滚动 counter
    codes, roll_pn = base.rolling_merged_postn(df)
    df["tstr"] = df["date"].dt.strftime("%Y.%m.%d %H:%M")
    # pre_cross 条件
    from _m15_early_entry_test import PRE_GAP
    direction = df["方向"].values
    sma5 = df["SMA_5"].values
    sma13 = df["SMA_13"].values
    close = df["close"].values
    # merged 方向 (滚动)
    merged_dir = []
    for c in codes:
        if c == 2:
            merged_dir.append("good")
        elif c == -2:
            merged_dir.append("bad")
        elif c == 1:
            merged_dir.append("up")
        else:
            merged_dir.append("down")
    df["merged_dir"] = merged_dir

    def bar_info(tstr):
        i = df.index[df["tstr"] == tstr]
        if len(i) == 0:
            return None
        i = i[0]
        return {
            "i": i,
            "l1": tstr in q2_times,
            "roll_pn": int(roll_pn[i]),
            "dir": direction[i],
            "gap": abs(sma5[i] - sma13[i]) / sma13[i],
            "l1_pct": abs(sma5[i] - sma13[i]) / sma13[i] * 100,
        }

    # ---- EA 独有归因 ----
    from collections import Counter
    cat = Counter()
    samples = []
    for k in sorted(ea_only):
        info = bar_info(k)
        if info is None:
            cat["EA信号不在Python数据"] += 1
            continue
        mode = ea_sigs[k]
        if not info["l1"]:
            cat["Python Layer1 FAIL"] += 1
        elif mode.startswith("post_n"):
            if 2 <= abs(info["roll_pn"]) <= 6:
                cat["post_n: counter一致但候选缺失"] += 1
            else:
                cat[f"post_n: counter差异 (py={info['roll_pn']})"] += 1
        elif mode == "pre_cross":
            if info["gap"] > PRE_GAP:
                cat[f"pre_cross: gap超限 (py_gap={info['gap']:.5f})"] += 1
            else:
                cat["pre_cross: gap合规但候选缺失"] += 1
        elif mode == "cross":
            cat["cross: 候选缺失"] += 1
        else:
            cat["其他"] += 1
        if len(samples) < 6:
            samples.append((k, mode, info))
    print()
    print("=== EA 独有信号归因 ===")
    for k, v in cat.most_common():
        print(f"  {k}: {v}")
    for k, mode, info in samples:
        print(f"  样本 {k} {mode}: L1={info['l1']} roll_pn={info['roll_pn']} dir={info['dir']} gap={info['gap']:.5f}")

    # ---- Python 独有归因 ----
    cat2 = Counter()
    samples2 = []
    for k in sorted(py_only):
        info = bar_info(k)
        mode = py_sigs[k]
        if info is None:
            cat2["无数据"] += 1
            continue
        if mode.startswith("post_n"):
            cat2[f"post_n (py counter={info['roll_pn']})"] += 1
        elif mode == "pre_cross":
            cat2["pre_cross"] += 1
        elif mode == "cross":
            cat2["cross"] += 1
        else:
            cat2["其他"] += 1
        if len(samples2) < 6:
            samples2.append((k, mode, info))
    print()
    print("=== Python 独有信号归因 ===")
    for k, v in cat2.most_common():
        print(f"  {k}: {v}")
    for k, mode, info in samples2:
        print(f"  样本 {k} {mode}: L1={info['l1']} roll_pn={info['roll_pn']} dir={info['dir']} gap={info['gap']:.5f}")


if __name__ == "__main__":
    main()

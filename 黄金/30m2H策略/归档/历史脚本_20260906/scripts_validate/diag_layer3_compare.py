# -*- coding: utf-8 -*-

"""对比 EA 日志 Layer3 判定 vs Python 滚动 Layer3 → 信号层差异归因"""
import os
import re
import sys

os.chdir(r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程\scripts")

import pandas as pd

import _current_baseline as base

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260812.log"
START = 902309380  # v3.35 段起点
CH = 8 * 1024 * 1024


def extract_ea_layer3():
    """提取 EA 日志 Layer3 判定: key = 信号 anchor (判定时刻 - 30min = bar open)"""
    pass_set, fail_set = {}, {}
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
                    r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}):\d{2}\s+\[(M30 CLOSE|M15 SLOT\d)\].*Layer3 \| "
                    r"bias5=([\d.]+) threshold=([\d.]+).*result=(PASS|FAIL)",
                    ln,
                )
                if m:
                    bar_close = m.group(1)
                    # anchor = 信号 bar open = 判定时刻 - 30min (M30 CLOSE 路径)
                    t = pd.to_datetime(bar_close, format="%Y.%m.%d %H:%M")
                    anchor = (t - pd.Timedelta(minutes=30)).strftime("%Y.%m.%d %H:%M")
                    if m.group(5) == "PASS":
                        pass_set[anchor] = (float(m.group(3)), float(m.group(4)))
                    else:
                        fail_set[anchor] = (float(m.group(3)), float(m.group(4)))
    return pass_set, fail_set


def main():
    ea_pass, ea_fail = extract_ea_layer3()
    print(f"EA Layer3 PASS: {len(ea_pass)}  FAIL: {len(ea_fail)}")

    # Python 滚动口径: 重建 final_acc
    df, final_acc = base.build_final_accepted(
        spec_lo=5, spec_hi=35, ea_executable_diag=True, rolling_merged=True,
    )
    h2 = base.load_h2_context()

    # 逐候选重算 layer3 (内联 apply_layer3_ea_executable 逻辑)
    h2_bias = base._build_h2_bias5_lookup(h2)
    h2_times = pd.to_datetime(h2_bias["date"]).tolist()
    h2_bias_values = h2_bias["Bias_5_calc"].tolist()
    lookback = 500
    top_pct = 34.0

    py_pass = set()
    py_fail = set()
    py_info = {}
    for _, row in final_acc.iterrows():
        a = pd.to_datetime(row["date"])
        eval_time = a + pd.Timedelta(minutes=30)  # M30 CLOSE
        idx = __import__("bisect").bisect_right(h2_times, eval_time) - 1
        if idx < 0:
            continue
        start = max(0, idx - lookback + 1)
        hist = h2_bias_values[start : idx + 1]
        current_bias5 = float(h2_bias_values[idx])
        threshold = base._rolling_top_threshold(hist, top_pct)
        key = a.strftime("%Y.%m.%d %H:%M")
        if pd.isna(threshold) or current_bias5 >= threshold:
            py_pass.add(key)
            py_info[key] = (current_bias5, float(threshold) if not pd.isna(threshold) else 0.0, True)
        else:
            py_fail.add(key)
            py_info[key] = (current_bias5, float(threshold), False)
    print(f"Python Layer3 PASS: {len(py_pass)}  FAIL: {len(py_fail)}")

    ea_keys = set(ea_pass) | set(ea_fail)
    py_keys = py_pass | py_fail
    print(f"EA 判定信号: {len(ea_keys)}  Python 候选: {len(py_keys)}")
    print(f"交集: {len(ea_keys & py_keys)}")
    print(f"EA 有 Python 无: {len(ea_keys - py_keys)}")
    print(f"Python 有 EA 无: {len(py_keys - ea_keys)}")
    # 交集内判定一致性
    both = ea_keys & py_keys
    agree = 0
    for k in both:
        ea_r = (k in ea_pass)
        py_r = (k in py_pass)
        if ea_r == py_r:
            agree += 1
    print(f"交集内判定一致: {agree}/{len(both)}")
    # 不一致样本
    print()
    print("=== 不一致样本 (前8) ===")
    n = 0
    for k in sorted(both):
        ea_r = 'PASS' if k in ea_pass else 'FAIL'
        py_r = 'PASS' if k in py_pass else 'FAIL'
        if ea_r != py_r:
            ea_v = ea_pass.get(k) or ea_fail.get(k)
            print(f'  {k}: EA={ea_r}(bias5={ea_v[0]:.5f},thr={ea_v[1]:.5f})  Python={py_r}')
            n += 1
            if n >= 8:
                break


if __name__ == "__main__":
    main()

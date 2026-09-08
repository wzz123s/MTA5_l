# -*- coding: utf-8 -*-

"""精确归因: EA 73 笔 vs expected 81 笔的 56 笔差异逐笔检查"""
import os
import re
import sys

os.chdir(r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程\scripts")

import pandas as pd

import _current_baseline as base

EXP = r"F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\final_ea_alignment_20260811\python_expected_trade_ledger.csv"
ACT = r"F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\final_ea_alignment_20260811\30m2H_strategy_trade_ledger_v335.csv"
LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260812.log"
START = 1063111564  # v3.36 段 (最后初始化)
CH = 8 * 1024 * 1024


def main():
    exp = pd.read_csv(EXP, encoding="utf-8-sig")
    act = pd.read_csv(ACT, encoding="utf-8-sig")
    exp_a = set(pd.to_datetime(exp["signal_anchor_time"]).dt.strftime("%Y.%m.%d %H:%M"))
    act_a = set(pd.to_datetime(act["signal_anchor_time"]).dt.strftime("%Y.%m.%d %H:%M"))
    both = exp_a & act_a
    exp_only = exp_a - act_a
    act_only = act_a - exp_a
    print(f"交集 {len(both)} | expected 独有 {len(exp_only)} | EA 独有 {len(act_only)}")

    # ---- EA 独有 24 笔: EA 执行了, Python expected 无 ----
    # 从日志提取这些信号的执行状态 (SIGNAL / SPEC_FAIL / Layer3)
    ea_exec = {}   # anchor -> result
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
                m = re.search(r"anchor=([\d.]+ [\d:]+).*result=(SIGNAL_EXEC|SPEC_FAIL|SKIP_STRICT|NO_STOP|POSTN_STOP_INVALID)", ln)
                if not m:
                    m = re.search(r"\[M30 CLOSE\].*anchor=([\d.]+ [\d:]+).*result=SPEC_FAIL", ln)
                    if m:
                        ea_exec.setdefault(m.group(1), "SPEC_FAIL")
                    continue
                ea_exec.setdefault(m.group(1), m.group(2))
            m2 = re.search(r"\[SIGNAL\]", "")
    # SIGNAL 行格式: [M30 CLOSE] [SIGNAL] BUY! mode=cross ... anchor=2020.03.06 19:30
    ea_signal = set()
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
                if "[SIGNAL]" not in ln:
                    continue
                m = re.search(r"anchor=([\d.]+ [\d:]+)", ln)
                if m:
                    ea_signal.add(m.group(1))
    # 修正: 信号行格式可能不同 → 打印样本
    print("\n=== EA 独有 24 笔的日志状态 ===")
    for k in sorted(act_only):
        status = "SIGNAL_EXEC" if k in ea_signal else ("SPEC_FAIL" if k in ea_exec else "日志未知")
        print(f"  {k}  {status}")

    # ---- expected 独有 32 笔: Python 有, EA 无 ----
    print("\n=== expected 独有 32 笔 ===")
    # Python 侧状态: 模式/spec/Layer3 (final_acc)
    df, final_acc = base.build_final_accepted(
        spec_lo=5, spec_hi=35, ea_executable_diag=True, rolling_merged=True,
    )
    for k in sorted(exp_only):
        row = final_acc[final_acc["date"].dt.strftime("%Y.%m.%d %H:%M") == k]
        if len(row):
            r = row.iloc[0]
            print(f"  {k} mode={r['mode']} sd={r.get('sd', '?'):.2f} spec={r.get('spec_pass', '?')} "
                  f"l3={r.get('layer3_pass_ea', '?')}")
        else:
            print(f"  {k} 不在 final_acc")


if __name__ == "__main__":
    main()

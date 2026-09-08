# -*- coding: utf-8 -*-
"""一键分析管线：事件邻近 → 波动率验证 → 过滤变体 → 报告。"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PY = r"F:\Program Files\Python\python.exe"

STEPS = [
    ("analyze_trades_vs_events.py", ["--events", str(SCRIPTS.parent / "data" / "calendar_export.csv")]),
    ("volatility_check.py", ["--events", str(SCRIPTS.parent / "data" / "calendar_export.csv")]),
    ("filter_sim.py", ["--events", str(SCRIPTS.parent / "data" / "calendar_export.csv")]),
    ("gen_report.py", []),
]

for name, extra in STEPS:
    print(f"\n{'='*60}\n>>> {name}\n{'='*60}")
    res = subprocess.run([PY, str(SCRIPTS / name), *extra], cwd=str(SCRIPTS))
    if res.returncode != 0:
        print(f"[FAIL] {name} rc={res.returncode}")
        sys.exit(res.returncode)
print("\nALL STEPS DONE")

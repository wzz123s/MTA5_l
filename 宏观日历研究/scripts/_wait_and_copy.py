# -*- coding: utf-8 -*-
"""等待日历导出完成 -> 拷贝到项目 -> 校验摘要。"""
import shutil
import sys
import time
from pathlib import Path

SRC_DIR = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Files")
DONE = SRC_DIR / "calendar_export_done.txt"
OUT = SRC_DIR / "calendar_export.csv"
DST = Path(r"F:\use_code\MTA5_l\宏观日历研究\data") / "calendar_export.csv"

deadline = time.time() + 2400
while time.time() < deadline:
    if DONE.exists():
        print("DONE:", DONE.read_text(encoding="utf-8", errors="replace").strip())
        if OUT.exists():
            DST.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OUT, DST)
            print("copied ->", DST)
            import pandas as pd
            df = pd.read_csv(DST, sep="|", dtype={"time": "int64"}, nrows=None)
            print("rows:", len(df), "cols:", list(df.columns))
            print("year coverage:", df.groupby(pd.to_datetime(df["time"], unit="s", utc=True).dt.year).size().to_dict())
            print("high impact:", (df["impact_type"] == 3).sum(), "importance>=70:", (df["importance"] >= 70).sum())
        sys.exit(0)
    time.sleep(10)
print("TIMEOUT 2400s")
sys.exit(3)

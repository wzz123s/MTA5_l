# -*- coding: utf-8 -*-
"""
宏观慢变量数据下载脚本（FRED 免费 CSV，无 API key）
====================================================
下载实际利率(DFII10)、贸易加权美元(DTWEXBGS) 到 ../data/
建议定期（每周）运行一次刷新；央行购金需从世界黄金协会季度报告手工维护。

注意：实测 Python urllib 下载 FRED 会 read timeout，本脚本改用 curl 调用。
"""
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE, "..", "data"))
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
SERIES = {
    "dfii10": "DFII10",       # 10Y TIPS 收益率 = 实际利率
    "dtwexbgs": "DTWEXBGS",   # 贸易加权美元指数 broad
}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    for name, sid in SERIES.items():
        url = FRED_URL.format(sid=sid)
        out = os.path.join(DATA_DIR, f"{name}.csv")
        try:
            r = subprocess.run(["curl", "-s", "-m", "30", url, "-o", out],
                               capture_output=True, timeout=40)
            if r.returncode == 0 and os.path.getsize(out) > 100:
                n = sum(1 for _ in open(out, encoding="utf-8"))
                print(f"OK   {name:10} <- {sid:10}  ({n} 行) -> {out}")
            else:
                print(f"FAIL {name:10} <- {sid:10}   curl rc={r.returncode}")
        except Exception as e:
            print(f"FAIL {name:10} <- {sid:10}   {str(e)[:80]}")


if __name__ == "__main__":
    main()

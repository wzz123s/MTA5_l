
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
df = pd.read_csv(r"F:\use_code\MTA5_l\宏观日历研究\data\calendar_export.csv", sep="|")
print("total rows:", len(df))
print("impact_type dist:", df["impact_type"].value_counts().to_dict())
print("importance dist:", df["importance"].value_counts().sort_index().to_dict())
t = pd.to_datetime(df["time"], unit="s", utc=True)
df["t"] = t
# NFP/CPI 发布时间分布（名称含关键词）
for kw in ["非农", "CPI", "消费者物价"]:
    sub = df[df["event_name"].str.contains(kw, na=False)]
    print(f"--- 名称含[{kw}]: {len(sub)} 条, 小时分布:", sub["t"].dt.hour.value_counts().sort_index().head(8).to_dict())
# 检查importance=3的事件名称样例
imp3 = df[df["importance"] == 3]
print("importance=3 rows:", len(imp3))
print(imp3[["event_name", "t", "actual", "forecast", "prev", "country"]].head(10).to_string())
imp3.to_csv(r"F:\use_code\MTA5_l\宏观日历研究\data\importance3_sample.csv", index=False, encoding="utf-8-sig")
print("saved importance3 sample")

# -*- coding: utf-8 -*-
import pandas as pd
df = pd.read_csv(r"F:\use_code\MTA5_l\宏观日历研究\data\calendar_export.csv", sep="|", dtype={"event_id": "int64", "time": "int64"})
t = pd.to_datetime(df["time"], unit="s", utc=True)
import datetime
now = datetime.datetime(2026, 8, 27, 19, 30, tzinfo=datetime.timezone.utc)
fut = df[(t >= now) & (t <= now + datetime.timedelta(hours=12))].copy()
fut["t"] = t[fut.index]
hi = fut[fut["importance"] >= 3]
print("未来12小时高影响事件数:", len(hi))
print(hi[["event_name", "t", "importance"]].head(20).to_string(index=False))

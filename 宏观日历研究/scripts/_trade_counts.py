
import pandas as pd
from pathlib import Path
root = Path(r"F:\use_code\MTA5_l\observation_dashboard")
for strat in ["1H_M30_4H", "30m2H", "2H_M30_6H", "USOIL2H", "USOIL4H", "BiasReversal"]:
    f = root / strat / "trades_snapshot.csv"
    if not f.exists():
        print(strat, "MISSING"); continue
    df = pd.read_csv(f, parse_dates=["signal_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
    years = df["signal_time"].dt.year.value_counts().sort_index()
    yrs = {str(k): int(v) for k, v in years.items()}
    print(f'{strat}: n={len(df)}  {df["signal_time"].min().date()} ~ {df["signal_time"].max().date()}  by_year={yrs}')


import pandas as pd
from pathlib import Path
root = Path(r"F:\use_code\MTA5_l\observation_dashboard")
for strat in ["1H_M30_4H", "30m2H", "2H_M30_6H", "USOIL2H", "USOIL4H", "BiasReversal"]:
    df = pd.read_csv(root / strat / "trades_snapshot.csv")
    print(strat, dict(df["mode"].value_counts()), "| reasons:", dict(df["stage3_reason"].value_counts().head(4)))

# -*- coding: utf-8 -*-
"""V反策略 P1：特征计算（SMMA/方向状态机/bias/段极值/结构止损）

输出：data/processed/<symbol>_<TF>_features.csv
列：dt, open, high, low, close, tick_volume, spread,
    sma5, sma13, sma55,
    dir（good/up/bad/down）,
    bias5_pct, bias13_pct, bias55_pct（无方向偏离）,
    seg_high_price, seg_high_sma13, seg_low_price, seg_low_sma13（当前段极值）,
    prev_seg_high_sma13, prev_seg_low_sma13（结构止损用）,
    seg_len, rise（当前up段）, wsw, vol_ma120
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = Path(__file__).resolve().parents[1] / "data" / "processed"

def calc_smma(close: pd.Series, n: int) -> pd.Series:
    """SMMA：初始化前n根算术平均，之后递推 SMA(i)=(1*C(i)+(n-1)*SMA(i-1))/n"""
    sma = pd.Series(np.nan, index=close.index)
    if len(close) < n:
        return sma
    sma.iloc[n - 1] = close.iloc[:n].mean()
    for i in range(n, len(close)):
        sma.iloc[i] = (close.iloc[i] + (n - 1) * sma.iloc[i - 1]) / n
    return sma

def mark_direction(df: pd.DataFrame) -> pd.DataFrame:
    """good/up/bad/down 状态机（5SMA 上/下穿 13SMA）"""
    d = pd.Series("", index=df.index, dtype=object)
    state = None
    for i in range(len(df)):
        s5, s13 = df["sma5"].iloc[i], df["sma13"].iloc[i]
        if pd.isna(s5) or pd.isna(s13):
            d.iloc[i] = ""
            continue
        if state is None:
            state = "up" if s5 >= s13 else "down"
        elif state == "down" and s5 >= s13:
            d.iloc[i] = "good"
            state = "up"
        elif state == "up" and s5 < s13:
            d.iloc[i] = "bad"
            state = "down"
        elif state == "up":
            d.iloc[i] = "up"
        else:
            d.iloc[i] = "down"
        # 穿越点后的持续状态标记
        if d.iloc[i] in ("good", "bad"):
            pass
    # 补上 good/bad 之后的 up/down 行（上面逻辑中 good 行后下一轮才置 up）
    df = df.copy()
    df["dir"] = d
    # 简化：good 行后首行为 up（状态机处理：穿越后持续标记）
    return df

def segment_features(df: pd.DataFrame) -> pd.DataFrame:
    """段极值追踪 + prev_seg 结构止损 + 段属性"""
    df = df.copy()
    n = len(df)
    df["seg_high_price"] = np.nan
    df["seg_high_sma13"] = np.nan
    df["seg_low_price"] = np.nan
    df["seg_low_sma13"] = np.nan
    df["prev_seg_high_sma13"] = np.nan
    df["prev_seg_low_sma13"] = np.nan
    df["seg_len"] = 0
    df["rise"] = np.nan
    df["wsw"] = 0.0
    df["vol_ma120"] = df["tick_volume"].rolling(120).mean()

    up_high_p = -np.inf
    up_high_s = -np.inf
    dn_low_p = np.inf
    dn_low_s = np.inf
    prev_up_high_s = np.nan
    prev_dn_low_s = np.nan
    seg_start = 0
    cur_dir = None
    last_cross_idx = 0

    for i in range(n):
        d = df["dir"].iloc[i]
        if d == "":
            continue
        if d in ("good", "bad"):
            # 穿越点：记录上一段极值（结构止损）
            if cur_dir == "up" or cur_dir == "bad":
                df.loc[df.index[i], "prev_seg_high_sma13"] = up_high_s if np.isfinite(up_high_s) else np.nan
            if cur_dir == "down" or cur_dir == "good":
                df.loc[df.index[i], "prev_seg_low_sma13"] = dn_low_s if np.isfinite(dn_low_s) else np.nan
            # 重置段
            prev_up_high_s = up_high_s
            prev_dn_low_s = dn_low_s
            up_high_p = -np.inf
            up_high_s = -np.inf
            dn_low_p = np.inf
            dn_low_s = np.inf
            seg_start = i
            last_cross_idx = i
            cur_dir = "up" if d == "good" else "down"
            # 穿越行自身参与极值
            if cur_dir == "up":
                up_high_p = df["high"].iloc[i]
                up_high_s = df["sma13"].iloc[i]
            else:
                dn_low_p = df["low"].iloc[i]
                dn_low_s = df["sma13"].iloc[i]
            df.loc[df.index[i], "seg_len"] = 1
            continue
        if d in ("up", "down"):
            seg_len = i - seg_start + 1
            df.loc[df.index[i], "seg_len"] = seg_len
            if d == "up":
                if df["high"].iloc[i] > up_high_p:
                    up_high_p = df["high"].iloc[i]
                if df["sma13"].iloc[i] > up_high_s:
                    up_high_s = df["sma13"].iloc[i]
                df.loc[df.index[i], "seg_high_price"] = up_high_p
                df.loc[df.index[i], "seg_high_sma13"] = up_high_s
                # rise：当前up段SMA13最高 - 上一down段SMA13最低）/ 上一down段最低
                if prev_dn_low_s is not None and np.isfinite(prev_dn_low_s) and prev_dn_low_s > 0:
                    df.loc[df.index[i], "rise"] = (up_high_s - prev_dn_low_s) / prev_dn_low_s
            else:
                if df["low"].iloc[i] < dn_low_p:
                    dn_low_p = df["low"].iloc[i]
                if df["sma13"].iloc[i] < dn_low_s:
                    dn_low_s = df["sma13"].iloc[i]
                df.loc[df.index[i], "seg_low_price"] = dn_low_p
                df.loc[df.index[i], "seg_low_sma13"] = dn_low_s
    return df

def process(symbol: str, tf: str) -> None:
    path = RAW / f"{symbol}_{tf}.csv"
    if not path.exists():
        print(f"[{symbol} {tf}] 无文件，跳过")
        return
    df = pd.read_csv(path)
    df["dt"] = pd.to_datetime(df["date_utc"], utc=True)
    df["sma5"] = calc_smma(df["close"], 5)
    df["sma13"] = calc_smma(df["close"], 13)
    df["sma55"] = calc_smma(df["close"], 55)
    df = mark_direction(df)
    df["bias5_pct"] = (df["close"] - df["sma5"]) / df["sma5"] * 100
    df["bias13_pct"] = (df["close"] - df["sma13"]) / df["sma13"] * 100
    df["bias55_pct"] = (df["close"] - df["sma55"]) / df["sma55"] * 100
    df = segment_features(df)
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"{symbol}_{tf}_features.csv"
    df.to_csv(out_path, index=False)
    print(f"[{symbol} {tf}] rows={len(df)} dirs={df['dir'].ne('').sum()} good={df['dir'].eq('good').sum()} bad={df['dir'].eq('bad').sum()} -> {out_path.name}")

def main() -> None:
    for symbol in ["XAUUSDm", "USOILm"]:
        for tf in ["M15", "M30", "H1", "H2", "H4", "H6", "H8", "W1", "D1"]:
            process(symbol, tf)

if __name__ == "__main__":
    main()

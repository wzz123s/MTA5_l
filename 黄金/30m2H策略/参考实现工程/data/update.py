# -*- coding: utf-8 -*-
"""data.update - MT5 data downloader for XAUUSD and USOIL multi-timeframe"""
import MetaTrader5 as mt5
import pandas as pd
import pytz
from datetime import datetime
from pathlib import Path
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / 'data' / 'raw'
DATA_RAW.mkdir(parents=True, exist_ok=True)
SYMBOLS = ['XAUUSDm', 'USOILm']
TIMEFRAMES = {
    'M15': mt5.TIMEFRAME_M15,
    'M30': mt5.TIMEFRAME_M30,
    'H1': mt5.TIMEFRAME_H1,
    'H2': mt5.TIMEFRAME_H2,
    'H4': mt5.TIMEFRAME_H4,
}
def download_data(symbol, timeframe, max_bars=99999):
    """Download OHLCV data from MT5."""
    timezone = pytz.timezone("Etc/UTC")
    time_back = datetime.now(timezone)
    rates = mt5.copy_rates_from(symbol, timeframe, time_back, max_bars)
    if rates is None or len(rates) == 0:
        print(f"Warning: No data for {symbol} at {str(timeframe)[-3:]}")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['time'] = df['time'] + pd.Timedelta(hours=8)
    df = df.rename(columns={
        'time': 'date', 'tick_volume': 'volume',
        'real_volume': 'real_volume', 'spread': 'spread',
    })
    df['symbol'] = symbol
    df['time_diff'] = df['date'].diff()
    expected_diff = pd.Timedelta(minutes={
        'M15': 15, 'M30': 30, 'H1': 60, 'H2': 120, 'H4': 240
    }.get({v: k for k, v in TIMEFRAMES.items()}.get(timeframe, 'H4'), 240))
    df = df[df['time_diff'] == expected_diff]
    df = df.dropna(subset=['date'])
    cols = ['date', 'open', 'high', 'low', 'close', 'volume',
            'spread', 'real_volume', 'symbol', 'time_diff']
    available = [c for c in cols if c in df.columns]
    return df[available]
def update_all():
    """Download all symbols at all timeframes."""
    if not mt5.initialize():
        print(f"MT5 initialize failed: {mt5.last_error()}")
        mt5.shutdown()
        return
    print(f"MT5 initialized. Downloading {len(SYMBOLS)} symbols x {len(TIMEFRAMES)} timeframes...")
    downloaded = []
    for symbol in SYMBOLS:
        for tf_name, tf_const in TIMEFRAMES.items():
            df = download_data(symbol, tf_const)
            if df is not None and len(df) > 0:
                filename = f'{symbol}{tf_name.lower()}.csv'
                name_map = {
                    'XAUUSDmm15': 'XAUUSDm15.csv',
                    'XAUUSDmm30': 'XAUUSDm30.csv',
                    'XAUUSDmh1': 'XAUUSD1H.csv',
                    'XAUUSDmh2': 'XAUUSD2H.csv',
                    'XAUUSDmh4': 'XAUUSD4H.csv',
                }
                fname = name_map.get(symbol + tf_name.lower(), filename)
                out_path = DATA_RAW / fname
                df.to_csv(out_path, index=False, encoding='gbk')
                print(f"Saved {len(df)} rows -> {out_path}")
                downloaded.append(out_path)
            else:
                print(f"Skipped {symbol} {tf_name} (no data)")
    mt5.shutdown()
    print(f"\nDone. {len(downloaded)} files downloaded.")
    return downloaded
if __name__ == '__main__':
    update_all()

# -*- coding: utf-8 -*-
"""
automated trading bot for 30m x 2H strategy on XAUUSD

MT5 connection -> load data -> detect signals -> place orders -> monitor positions

Usage:
    python auto_trade/auto_trader.py

Requires:
    - MetaTrader 5 terminal running (Exness)
    - MetaTrader5 Python package installed
    - Account logged in
"""
import sys, os, time, json, logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================
# v3.17 sync (2026-06-22): stop_lookback / min_bars_for_stop added to mirror
# EA FindStopSMA inputs. stop_lo/stop_hi unchanged (3.0-35.0 spec 点 = $3-$35).
CONFIG = {
    # MT5 connection
    "mt5_path": r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    "account": 277752085,
    "password": "Wazz20501166!",
    "server": "Exness-MT5Trial5",

    # Trading
    "symbol": "XAUUSDm",
    "timeframe_main": mt5.TIMEFRAME_M30,   # 30 minutes
    "timeframe_high": mt5.TIMEFRAME_H2,    # 2 hours
    "risk_pct": 3.0,          # risk % of equity per trade
    "pt_value_per_lot": 10.0, # $ per point per standard lot
    "min_lots": 0.01,         # minimum lot size
    "max_lots": 10.0,         # maximum lot size
    "max_positions": 3,       # max concurrent positions
    "magic_number": 302025,   # unique identifier for our orders
    "deviation": 30,          # allowed slippage (points)

    # Strategy parameters (v3.17: spec 点 = USD price for XAUUSD)
    "stop_lo": 3.0,           # minimum stop distance (spec 点 = $3)
    "stop_hi": 35.0,          # maximum stop distance (spec 点 = $35)
    "sma13_threshold": 0.5,   # 2H SMA13 distance > 0.5%
    # v3.17: stop search params (mirror EA FindStopSMA inputs)
    "stop_lookback": 200,     # M30 bars of history for stop search
    "min_bars_for_stop": 30,  # MIN_BARS guard for stop search (array OOB defence)

    # Runtime
    "check_interval": 15,     # seconds between checks
    "max_bars": 5000,         # bars to load for analysis
    "log_file": "auto_trade/trader.log",
}

# ============================================================
# LOGGING SETUP
# ============================================================
os.makedirs("auto_trade", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("AutoTrader")


# ============================================================
# MT5 CONNECTION
# ============================================================
def connect_mt5():
    """Connect to MT5 terminal and login to account."""
    # Try initialize with path
    if not mt5.initialize(path=CONFIG["mt5_path"]):
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return False

    # Login to account
    authorized = mt5.login(
        login=CONFIG["account"],
        password=CONFIG["password"],
        server=CONFIG["server"],
    )
    if not authorized:
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False

    # Verify
    info = mt5.account_info()
    if info is None:
        logger.error("Cannot get account info")
        mt5.shutdown()
        return False

    logger.info(f"Connected: account={info.login}, balance=${info.balance:.2f}, "
                f"equity=${info.equity:.2f}, leverage=1:{info.leverage}")

    # Check symbol
    sym = mt5.symbol_info(CONFIG["symbol"])
    if sym is None:
        logger.error(f"Symbol {CONFIG['symbol']} not found")
        mt5.shutdown()
        return False

    mt5.symbol_select(CONFIG["symbol"], True)
    logger.info(f"Symbol: {CONFIG['symbol']}, digits={sym.digits}, "
                f"min_lot={sym.volume_min}, max_lot={sym.volume_max}, "
                f"lot_step={sym.volume_step}, contract_size={sym.trade_contract_size}")

    return True


# ============================================================
# DATA LOADING AND DIRECTION MARKING
# ============================================================
def smma(series, n, m=1):
    """Smoothed Moving Average."""
    r = np.full(len(series), np.nan)
    r[n-1] = series[:n].mean()
    for i in range(n, len(series)):
        r[i] = (m * series[i] + (n - m) * r[i-1]) / n
    return r


def get_rates(symbol, timeframe, count):
    """Get OHLCV rates from MT5."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.rename(columns={"time": "date"})
    return df


def mark_direction(df):
    """Mark SMA5/13 crossover directions on DataFrame."""
    df = df.copy()
    close = df["close"].values
    n = len(df)
    sma5_arr = smma(close, 5)
    sma13_arr = smma(close, 13)
    df["SMA_5"] = sma5_arr
    df["SMA_13"] = sma13_arr

    s5g = sma5_arr > sma13_arr
    s5p = np.roll(s5g, 1)
    s5p[0] = s5g[0]

    direction = np.full(n, "", dtype=object)
    for i in range(n):
        if s5g[i] and not s5p[i]:
            direction[i] = "good"
        elif not s5g[i] and s5p[i]:
            direction[i] = "bad"
        elif s5g[i]:
            direction[i] = "up"
        else:
            direction[i] = "down"
    df["方向"] = direction

    # Merge short segments
    merged = direction.copy()
    crossings = [(i, direction[i]) for i in range(n) if direction[i] in ("good", "bad")]
    if len(crossings) > 0:
        state = "down" if crossings[0][1] == "good" else "up"
        i = 0
        while i < len(crossings):
            pos, tp = crossings[i]
            if i + 1 >= len(crossings):
                break
            npos, ntp = crossings[i + 1]
            cnt = sum(1 for j in range(pos + 1, npos)
                      if direction[j] == ("up" if tp == "good" else "down"))
            if cnt < 8:
                merged[pos:npos] = state
                crossings.pop(i + 1)
                crossings.pop(i)
            else:
                state = "up" if tp == "good" else "down"
                i += 1
    df["方向_合并后"] = merged
    return df


def get_high_direction_at(high_df, time):
    """Get 2H direction at or before a given time."""
    hd = pd.to_datetime(high_df["date"])
    mask = hd <= time
    if not mask.any():
        return None, None, None
    row = high_df.iloc[high_df[mask].index[-1]]
    return row.get("方向_合并后", ""), row.get("SMA_13", 0), row.get("close", 0)


# ============================================================
# SIGNAL DETECTION
# ============================================================
def check_new_signal(main_df, high_df):
    """
    Check if the latest completed bar on main_df has a valid trading signal.

    v3.17 (2026-06-22): aligned with EA FindStopSMA rollback.
    - MIN_BARS=30 guard added at top (defends against array OOB).
    - stop search uses np.nanmin/nanmax over [k, last_completed) — equivalent
      to EA's "search entire history for most recent cross → MathMin/MathMax".
    - spec range check (3.0-35.0 spec 点 = $3-$35) is done by caller (line ~270).

    Returns dict with signal info, or None if no valid signal.
    """
    mdir = main_df["方向_合并后"].values
    n = len(main_df)

    # v3.17: MIN_BARS guard (mirrors EA FindStopSMA MIN_BARS=30).
    if n < CONFIG["min_bars_for_stop"]:
        return None

    # Check last bar (index n-2, since n-1 is the in-progress bar)
    last_completed = n - 2
    if last_completed < 0:
        return None

    direction = mdir[last_completed]
    if direction not in ("good", "bad"):
        return None

    is_long = (direction == "good")

    # Find previous opposite crossing for stop calculation
    k = last_completed - 1
    while k >= 0 and mdir[k] not in ("good", "bad"):
        k -= 1
    if k < 0:
        return None

    # Check 2H direction alignment
    row = main_df.iloc[last_completed]
    t = row["date"]
    hd, sma13_val, close_val = get_high_direction_at(high_df, t)
    if hd is None:
        return None

    aligned = (hd in ("up", "good")) if is_long else (hd in ("down", "bad"))
    if not aligned:
        return None

    # Check SMA13 distance on 2H
    if sma13_val and sma13_val > 0:
        dist_pct = abs(close_val - sma13_val) / sma13_val * 100
        if dist_pct < CONFIG["sma13_threshold"]:
            return None

    # Calculate entry and stop
    # v3.17: stop = SMA13 extreme of prior segment (no v3.16 4-guard).
    # LONG: prior segment DOWN → np.nanmin = lowest SMA13 (stop below entry).
    # SHORT: prior segment UP → np.nanmax = highest SMA13 (stop above entry).
    sma13_arr = main_df["SMA_13"].values
    if is_long:
        seg_sma = sma13_arr[max(0, k):last_completed]
        stop_price = np.nanmin(seg_sma) if len(seg_sma) > 0 else np.nan
        entry_price = (row["high"] + row["low"] + row["close"]) / 3.0
        stop_pts = entry_price - stop_price
    else:
        seg_sma = sma13_arr[max(0, k):last_completed]
        stop_price = np.nanmax(seg_sma) if len(seg_sma) > 0 else np.nan
        entry_price = (row["high"] + row["low"] + row["close"]) / 3.0
        stop_pts = stop_price - entry_price

    if np.isnan(stop_price) or np.isnan(entry_price):
        return None

    # Validate stop
    if is_long and stop_price >= entry_price:
        return None
    if not is_long and stop_price <= entry_price:
        return None
    # v3.17: spec range check at caller (mirrors EA line ~1147).
    # stop_lo/stop_hi are in spec 点 (= USD price for XAUUSDm).
    if stop_pts < CONFIG["stop_lo"] or stop_pts > CONFIG["stop_hi"]:
        return None

    # Find next opposite crossing for exit check
    opp = "bad" if is_long else "good"
    j = last_completed + 1
    while j < n and mdir[j] != opp:
        j += 1

    return {
        "time": t,
        "is_long": is_long,
        "direction": "做多" if is_long else "做空",
        "entry_price": round(entry_price, 3),
        "stop_price": round(stop_price, 3),
        "stop_pts": round(stop_pts, 2),
        "exit_bar_idx": j if j < n else n - 1,
    }


# ============================================================
# ORDER MANAGEMENT
# ============================================================
def calculate_lots(stop_pts):
    """Calculate lot size based on current equity and risk %."""
    info = mt5.account_info()
    if info is None:
        return CONFIG["min_lots"]
    equity = info.equity
    risk_amount = equity * CONFIG["risk_pct"] / 100.0
    if stop_pts <= 0:
        return CONFIG["min_lots"]
    lots = risk_amount / (stop_pts * CONFIG["pt_value_per_lot"])
    lots = max(CONFIG["min_lots"], min(lots, CONFIG["max_lots"]))
    # Round to lot_step
    sym = mt5.symbol_info(CONFIG["symbol"])
    step = sym.volume_step if sym else 0.01
    lots = round(lots / step) * step
    return max(CONFIG["min_lots"], lots)


def place_order(is_long, entry_price, stop_price, stop_pts):
    """Place a market order with stop loss."""
    symbol = CONFIG["symbol"]

    # Get current prices
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error("Cannot get tick")
        return None

    lots = calculate_lots(stop_pts)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": mt5.ORDER_TYPE_BUY if is_long else mt5.ORDER_TYPE_SELL,
        "price": tick.ask if is_long else tick.bid,
        "sl": stop_price,
        "tp": 0.0,
        "deviation": CONFIG["deviation"],
        "magic": CONFIG["magic_number"],
        "comment": f"30mx2H_{'L' if is_long else 'S'}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order failed: retcode={result.retcode}, comment={result.comment}")
        return None

    logger.info(f"ORDER: {request['comment']} | lots={lots:.2f} | "
                f"entry={request['price']:.3f} | sl={stop_price:.3f} | "
                f"risk={stop_pts*lots*CONFIG['pt_value_per_lot']:.1f}$ | ticket={result.order}")
    return result.order


def check_positions():
    """Get all open positions for our strategy."""
    positions = mt5.positions_get(symbol=CONFIG["symbol"])
    if positions is None:
        return []
    return [p for p in positions if p.magic == CONFIG["magic_number"]]


def close_position(position):
    """Close an open position."""
    symbol = CONFIG["symbol"]
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False

    pos_type = position.type
    close_price = tick.bid if pos_type == mt5.POSITION_TYPE_BUY else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": close_price,
        "deviation": CONFIG["deviation"],
        "magic": CONFIG["magic_number"],
        "comment": "exit_signal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Close failed: ticket={position.ticket}, retcode={result.retcode}")
        return False

    profit = position.profit
    logger.info(f"CLOSE: ticket={position.ticket} | profit=${profit:.2f}")
    return True


def should_exit_position(position, main_df):
    """Check if position should be closed (opposite crossing on main_df)."""
    mdir = main_df["方向_合并后"].values
    n = len(main_df)
    last_completed = n - 2
    if last_completed < 0:
        return False

    pos_is_long = (position.type == mt5.POSITION_TYPE_BUY)
    exit_signal = "bad" if pos_is_long else "good"

    # Check if latest completed bar is the exit signal
    return mdir[last_completed] == exit_signal


# ============================================================
# MAIN LOOP
# ============================================================
def run():
    """Main trading loop."""
    logger.info("=" * 60)
    logger.info("AutoTrader starting...")
    logger.info(f"Config: {CONFIG['symbol']}, {CONFIG['timeframe_main']}x{CONFIG['timeframe_high']}")
    logger.info(f"Risk: {CONFIG['risk_pct']}%, Stop: {CONFIG['stop_lo']}-{CONFIG['stop_hi']}pt")

    if not connect_mt5():
        logger.error("Cannot connect to MT5")
        return

    last_bar_time = None
    signal_checked_this_bar = False

    try:
        while True:
            try:
                # ======== LOAD DATA ========
                main_df = get_rates(CONFIG["symbol"], CONFIG["timeframe_main"], CONFIG["max_bars"])
                high_df = get_rates(CONFIG["symbol"], CONFIG["timeframe_high"], CONFIG["max_bars"])
                if main_df is None or high_df is None:
                    logger.warning("Cannot get rates, retrying...")
                    time.sleep(CONFIG["check_interval"])
                    continue

                # ======== MARK DIRECTION ========
                main_df = mark_direction(main_df)
                high_df = mark_direction(high_df)

                # ======== CHECK NEW BAR ========
                current_last = main_df["date"].iloc[-1]
                if current_last != last_bar_time:
                    last_bar_time = current_last
                    signal_checked_this_bar = False
                    logger.info(f"New bar: {current_last}")

                # ======== MANAGE POSITIONS ========
                positions = check_positions()
                for pos in positions:
                    if should_exit_position(pos, main_df):
                        logger.info(f"Exit signal for ticket={pos.ticket}")
                        close_position(pos)

                # ======== CHECK NEW SIGNAL ========
                if not signal_checked_this_bar and len(positions) < CONFIG["max_positions"]:
                    signal = check_new_signal(main_df, high_df)
                    if signal:
                        logger.info(f"SIGNAL: {signal['direction']} @ {signal['time']} | "
                                    f"entry={signal['entry_price']:.3f} | stop={signal['stop_price']:.3f} | "
                                    f"risk={signal['stop_pts']:.1f}pt")

                        # Check if we already have a position in this direction
                        has_same = any(
                            (p.type == mt5.POSITION_TYPE_BUY) == signal["is_long"]
                            for p in positions
                        )
                        if not has_same:
                            order = place_order(
                                signal["is_long"],
                                signal["entry_price"],
                                signal["stop_price"],
                                signal["stop_pts"],
                            )
                            if order:
                                signal_checked_this_bar = True

                # ======== STATUS REPORT (every 5 min) ========
                if datetime.now().minute % 5 == 0 and datetime.now().second < CONFIG["check_interval"]:
                    info = mt5.account_info()
                    if info:
                        pos = check_positions()
                        pnl = sum(p.profit for p in pos) if pos else 0
                        logger.info(f"STATUS: equity=${info.equity:.2f} | "
                                    f"positions={len(pos)} | PnL=${pnl:.2f}")

                time.sleep(CONFIG["check_interval"])

            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                time.sleep(CONFIG["check_interval"])

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        mt5.shutdown()
        logger.info("MT5 disconnected. AutoTrader stopped.")


if __name__ == "__main__":
    run()

# -*- coding: utf-8 -*-
"""
Step-by-step verification script for AutoTrader
测试顺序: 连接 -> 读数据 -> 合约信息 -> 信号模拟(不下单)

Usage:
    python auto_trade/verify_connection.py
"""
import sys, os, time, logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

# ============================================================
# CONFIG (from auto_trader.py)
# ============================================================
CONFIG = {
    "mt5_path": r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    "account": 277752085,
    "password": "Wazz20501166!",
    "server": "Exness-MT5Trial5",
    "symbol": "XAUUSDm",
    "timeframe_main": mt5.TIMEFRAME_M30,
    "timeframe_high": mt5.TIMEFRAME_H2,
    "max_bars": 5000,
    "sma13_threshold": 0.5,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("Verify")


# ============================================================
# STEP 1: 连接测试
# ============================================================
def step1_connect():
    print("\n" + "=" * 60)
    print("STEP 1: MT5 连接测试")
    print("=" * 60)

    if not mt5.initialize(path=CONFIG["mt5_path"]):
        print(f"[FAIL] MT5 初始化失败: {mt5.last_error()}")
        return False

    authorized = mt5.login(
        login=CONFIG["account"],
        password=CONFIG["password"],
        server=CONFIG["server"],
    )
    if not authorized:
        print(f"[FAIL] MT5 登录失败: {mt5.last_error()}")
        mt5.shutdown()
        return False

    info = mt5.account_info()
    if info is None:
        print(f"[FAIL] 无法获取账户信息: {mt5.last_error()}")
        mt5.shutdown()
        return False

    print(f"[PASS] 连接成功!")
    print(f"       账号:     {info.login}")
    print(f"       服务器:   {CONFIG['server']}")
    print(f"       余额:     ${info.balance:.2f}")
    print(f"       净值:     ${info.equity:.2f}")
    print(f"       杠杆:     1:{info.leverage}")
    print(f"       保证金:   ${info.margin}: {info.margin_level:.1f}%")
    positions = mt5.positions_get(); print(f"       持仓数:   {len(positions)}")
    return True


# ============================================================
# STEP 2: 合约信息
# ============================================================
def step2_symbol_info():
    print("\n" + "=" * 60)
    print("STEP 2: 合约信息检查")
    print("=" * 60)

    sym = mt5.symbol_info(CONFIG["symbol"])
    if sym is None:
        print(f"[FAIL] 合约 {CONFIG['symbol']} 不存在或未找到")
        return False

    mt5.symbol_select(CONFIG["symbol"], True)

    print(f"[PASS] 合约: {sym.name}")
    print(f"       描述:        {sym.description}")
    print(f"       报价位数:    {sym.digits} (digits)")
    print(f"       合约大小:    {sym.trade_contract_size}")
    print(f"       最小手数:   {sym.volume_min}")
    print(f"       最大手数:   {sym.volume_max}")
    print(f"       手数步进:   {sym.volume_step}")
    print(f"       买价:       {sym.bid}")
    print(f"       卖价:       {sym.ask}")
    print(f"       点差:       {sym.spread}")
    print(f"       合约规模:   {sym.trade_contract_size}")
    print(f"       止损级别:   {sym.trade_stops_level} pts")

    # Try getting tick data
    tick = mt5.symbol_info_tick(CONFIG["symbol"])
    if tick:
        print(f"       最新报价:   bid={tick.bid:.5f} ask={tick.ask:.5f} time={tick.time}")
    return True


# ============================================================
# STEP 3: 数据读取
# ============================================================
def step3_read_data():
    print("\n" + "=" * 60)
    print("STEP 3: 历史数据读取")
    print("=" * 60)

    count = 100  # 先读100根K线测试

    rates_m30 = mt5.copy_rates_from_pos(CONFIG["symbol"], CONFIG["timeframe_main"], 0, count)
    rates_h2 = mt5.copy_rates_from_pos(CONFIG["symbol"], CONFIG["timeframe_high"], 0, count)

    if rates_m30 is None or len(rates_m30) == 0:
        print(f"[FAIL] 无法读取M30数据: {mt5.last_error()}")
        return None, None
    if rates_h2 is None or len(rates_h2) == 0:
        print(f"[FAIL] 无法读取H2数据: {mt5.last_error()}")
        return None, None

    df_m30 = pd.DataFrame(rates_m30)
    df_h2 = pd.DataFrame(rates_h2)

    df_m30["time"] = pd.to_datetime(df_m30["time"], unit="s")
    df_h2["time"] = pd.to_datetime(df_h2["time"], unit="s")

    print(f"[PASS] M30 数据: {len(df_m30)} 根K线")
    print(f"       时间范围: {df_m30['time'].iloc[-1]} ~ {df_m30['time'].iloc[0]}")
    print(f"       最新收盘: {df_m30['close'].iloc[-1]:.5f}")
    print(f"       最新成交量: {df_m30['tick_volume'].iloc[-1]}")
    print()
    print(f"[PASS] H2 数据: {len(df_h2)} 根K线")
    print(f"       时间范围: {df_h2['time'].iloc[-1]} ~ {df_h2['time'].iloc[0]}")
    print(f"       最新收盘: {df_h2['close'].iloc[-1]:.5f}")

    return df_m30, df_h2


# ============================================================
# STEP 4: 信号逻辑模拟
# ============================================================
def smma(series, n, m=1):
    """Smoothed Moving Average."""
    r = np.full(len(series), np.nan)
    r[n-1] = series[:n].mean()
    for i in range(n, len(series)):
        r[i] = (m * series[i] + (n - m) * r[i-1]) / n
    return r


def mark_direction(df):
    """Mark SMA5/13 crossover directions."""
    df = df.copy()
    close = df["close"].values
    sma5 = smma(close, 5)
    sma13 = smma(close, 13)
    df["SMA_5"] = sma5
    df["SMA_13"] = sma13

    s5g = sma5 > sma13
    cross_up = np.zeros(len(s5g), dtype=bool)
    cross_down = np.zeros(len(s5g), dtype=bool)
    for i in range(1, len(s5g)):
        cross_up[i] = s5g[i] and not s5g[i-1]
        cross_down[i] = s5g[i-1] and not s5g[i]

    df["cross_up"] = cross_up
    df["cross_down"] = cross_down

    pct_dist = (sma13 - sma5) / sma5 * 100
    df["pct_dist"] = pct_dist

    return df


def step4_signal_logic(df_m30, df_h2):
    print("\n" + "=" * 60)
    print("STEP 4: 信号逻辑模拟 (不下单)")
    print("=" * 60)

    df_m30 = mark_direction(df_m30)
    df_h2 = mark_direction(df_h2)

    # H2 direction filter
    h2_sma13 = df_h2["SMA_13"].iloc[-1]
    h2_sma5 = df_h2["SMA_5"].iloc[-1]
    h2_pct = (h2_sma13 - h2_sma5) / h2_sma5 * 100
    h2_long = h2_pct > CONFIG["sma13_threshold"]
    h2_short = h2_pct < -CONFIG["sma13_threshold"]

    print(f"H2 周期状态:")
    print(f"  SMA5={h2_sma5:.3f}  SMA13={h2_sma13:.3f}")
    print(f"  偏离度: {h2_pct:+.3f}%  (阈值: ±{CONFIG['sma13_threshold']}%)")
    print(f"  方向:   {'H2看多' if h2_long else ('H2看空' if h2_short else 'H2中性')}")
    print()

    # Last 5 completed M30 bars
    n = len(df_m30)
    last_n = df_m30.iloc[max(0, n-6):n-1]  # skip current bar

    print(f"M30 最近 {len(last_n)} 根已完成K线:")
    print(f"{'时间':<22} {'收盘':>10} {'SMA5':>10} {'SMA13':>10} {'偏离%':>8} {'信号':>6}")
    print("-" * 70)
    for _, row in last_n.iterrows():
        pct = row["pct_dist"] if not np.isnan(row["pct_dist"]) else 0
        sig = ""
        if row["cross_up"]:
            sig = "金叉"
        elif row["cross_down"]:
            sig = "死叉"
        print(f"{str(row['time']):<22} {row['close']:>10.5f} {row['SMA_5']:>10.3f} {row['SMA_13']:>10.3f} {pct:>+8.3f} {sig:>6}")

    print()
    print(f"当前H2方向: {'做空' if h2_short else ('做多' if h2_long else '无信号')}")

    # Check for cross signals
    completed = df_m30.iloc[n-2]
    if completed["cross_up"] and h2_long:
        print(f">>> 买入信号模拟: M30金叉 + H2看多，当前收盘={completed['close']:.5f}")
    elif completed["cross_down"] and h2_short:
        print(f">>> 卖出信号模拟: M30死叉 + H2看空，当前收盘={completed['close']:.5f}")
    else:
        sig = "金叉" if completed["cross_up"] else ("死叉" if completed["cross_down"] else "无交叉")
        print(f">>> 无模拟信号 (M30={sig}, H2={'看多' if h2_long else ('看空' if h2_short else '中性')})")

    return True


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "#" * 60)
    print("#  AutoTrader 验证脚本")
    print("#  测试顺序: 连接 -> 合约 -> 数据 -> 信号模拟")
    print("#" * 60)

    results = {}

    # Step 1
    results["连接"] = step1_connect()
    if not results["连接"]:
        print("\n[ERROR] 连接失败，无法继续后续测试。请检查:")
        print("  1. MT5 终端是否已打开并登录")
        print("  2. 账号/密码/服务器是否正确")
        return

    # Step 2
    results["合约"] = step2_symbol_info()

    # Step 3
    df_m30, df_h2 = step3_read_data()
    results["数据"] = df_m30 is not None

    if df_m30 is not None and df_h2 is not None:
        # Step 4
        results["信号"] = step4_signal_logic(df_m30, df_h2)
    else:
        results["信号"] = False

    # Summary
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    for name, ok in results.items():
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status} {name}")

    all_pass = all(results.values())
    print()
    if all_pass:
        print("所有测试通过! 可以运行 auto_trader.py 进行模拟交易")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"失败项: {', '.join(failed)}")

    mt5.shutdown()
    print("\nMT5 连接已关闭。")


if __name__ == "__main__":
    main()

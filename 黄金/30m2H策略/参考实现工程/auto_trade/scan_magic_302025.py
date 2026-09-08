# -*- coding: utf-8 -*-
"""scan_magic_302025 - Scan MT5 terminal for 30m2H EA positions.

Detects duplicate opens caused by EA being attached to multiple charts
(same signal fires twice → 0.06 × 2 = 0.12 lots per signal).

Usage:
    python auto_trade/scan_magic_302025.py

Magic layout (from 30m2H_Strategy_EA.mq5):
    InpMagic         = 302025       (base)
    InpMagic + 1     = 302026       (Stage 1)
    InpMagic + 2     = 302027       (Stage 2)
    InpMagic + 3     = 302028       (Stage 3)

A clean run (EA on M30 only) should show positions grouped as triplets:
    {ticket_1: magic=302026, ticket_2: magic=302027, ticket_3: magic=302028}
    all with the same entry time / price (one signal = one triplet).

If EA is on both H2 + M30 charts, you'd see TWO triplets per signal
(2 charts × 3 stages = 6 positions for the same entry bar).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# ===== Config (must match auto_trade/auto_trader.py) =====
CONFIG = {
    "mt5_path": r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    "account": 277752085,
    "password": "Wazz20501166!",
    "server": "Exness-MT5Trial5",
    "symbol": "XAUUSDm",
    "magic": 302025,
}


def connect():
    if not mt5.initialize(path=CONFIG["mt5_path"]):
        print(f"[FAIL] MT5 initialize: {mt5.last_error()}")
        return False
    if not mt5.login(
        login=CONFIG["account"],
        password=CONFIG["password"],
        server=CONFIG["server"],
    ):
        print(f"[FAIL] MT5 login: {mt5.last_error()}")
        mt5.shutdown()
        return False
    info = mt5.account_info()
    print(f"[OK] Connected: account={info.login}, balance=${info.balance:.2f}, "
          f"equity=${info.equity:.2f}")
    return True


def scan_positions():
    """Scan all positions, return DataFrame with magic grouping."""
    positions = mt5.positions_get(symbol=CONFIG["symbol"])
    if positions is None:
        print(f"[FAIL] positions_get: {mt5.last_error()}")
        return pd.DataFrame()
    if len(positions) == 0:
        print("[OK] No open positions.")
        return pd.DataFrame()

    rows = []
    for p in positions:
        rows.append({
            "ticket": p.ticket,
            "magic": p.magic,
            "stage": _stage_label(p.magic),
            "symbol": p.symbol,
            "type": "LONG" if p.type == mt5.ORDER_TYPE_BUY else "SHORT",
            "volume": p.volume,
            "price_open": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "price_current": p.price_current,
            "profit": p.profit,
            "time_open": datetime.fromtimestamp(p.time),
            "time_update": datetime.fromtimestamp(p.time_update),
            "comment": p.comment,
        })
    return pd.DataFrame(rows)


def scan_recent_deals(days=2):
    """Scan recent deal history for our magic numbers."""
    from datetime import timedelta
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)
    deals = mt5.history_deals_get(date_from, date_to, symbol=CONFIG["symbol"])
    if deals is None:
        return pd.DataFrame()
    rows = []
    for d in deals:
        if d.entry != mt5.DEAL_ENTRY_OUT and d.entry != mt5.DEAL_ENTRY_INOUT:
            continue  # skip non-entry deals
        rows.append({
            "ticket": d.ticket,
            "order": d.order,
            "magic": d.magic,
            "stage": _stage_label(d.magic),
            "type": "LONG" if d.type == mt5.DEAL_TYPE_BUY else "SHORT",
            "volume": d.volume,
            "price": d.price,
            "time": datetime.fromtimestamp(d.time),
            "entry": "IN" if d.entry == mt5.DEAL_ENTRY_IN else "OUT",
            "reason": _reason_str(d.reason),
            "comment": d.comment,
        })
    return pd.DataFrame(rows)


def _reason_str(reason):
    reasons = {
        mt5.DEAL_REASON_CLIENT: "CLIENT",
        mt5.DEAL_REASON_MOBILE: "MOBILE",
        mt5.DEAL_REASON_WEB: "WEB",
        mt5.DEAL_REASON_EXPERT: "EXPERT",
        mt5.DEAL_REASON_SL: "SL",
        mt5.DEAL_REASON_TP: "TP",
        mt5.DEAL_REASON_SO: "SO",
    }
    return reasons.get(reason, f"?{reason}")


def _stage_label(magic):
    """Map magic suffix to stage label (302025 = base, +1/2/3 = stage 1/2/3)."""
    suffix = magic - CONFIG["magic"]
    return {1: "Stage1", 2: "Stage2", 3: "Stage3"}.get(suffix, f"raw({magic})")


def detect_duplicates(df):
    """Detect duplicate opens.

    Strategy:
      Group positions by (entry time, entry price, direction). A healthy signal
      shows exactly 3 positions (Stage 1/2/3) sharing the same entry.
      If 6 positions share the same entry → EA is double-attached.
    """
    if df.empty:
        return []

    df = df.copy()
    df["entry_round"] = df["price_open"].round(2)
    df["time_round"] = df["time_open"].dt.floor("1min")

    grouped = df.groupby(["time_round", "entry_round", "type"])
    findings = []
    for (t, p, ty), grp in grouped:
        stages = sorted(grp["stage"].tolist())
        n = len(grp)
        expected = 3
        status = "OK"
        if n != expected:
            status = f"DUPLICATE (got {n}, expected {expected})"
        findings.append({
            "entry_time": t,
            "entry_price": p,
            "direction": ty,
            "n_positions": n,
            "stages": ", ".join(stages),
            "total_volume": grp["volume"].sum(),
            "tickets": ", ".join(str(x) for x in grp["ticket"]),
            "status": status,
        })
    return findings


def main():
    if not connect():
        sys.exit(1)

    print()
    print("=" * 70)
    print(f"  30m2H EA Position Scanner (magic={CONFIG['magic']})")
    print("=" * 70)

    df = scan_positions()

    # Filter to our magic only (302025 + 1/2/3 = 302026/27/28)
    magic_min = CONFIG["magic"] + 1
    magic_max = CONFIG["magic"] + 3

    print(f"\n[SCAN] Total open positions on {CONFIG['symbol']}: {len(df)}")
    if df.empty:
        print("       (no open positions on XAUUSDm)")
        ours = pd.DataFrame()
        findings = []
    else:
        ours = df[(df["magic"] >= magic_min) & (df["magic"] <= magic_max)].copy()
        others = df[~((df["magic"] >= magic_min) & (df["magic"] <= magic_max))].copy()
        print(f"       30m2H EA (magic {magic_min}-{magic_max}): {len(ours)}")
        if len(others) > 0:
            print(f"       Other magic: {len(others)} (not our EA)")

        if len(ours) == 0:
            print("\n[OK] No 30m2H EA positions open.")
        else:
            # Detail table
            print("\n" + "-" * 70)
            print(f"  {'Ticket':<10} {'Stage':<8} {'Type':<6} {'Lots':>6} {'Entry':>10} {'SL':>10} {'Profit':>9}")
            print("-" * 70)
            for _, r in ours.iterrows():
                print(f"  {r['ticket']:<10} {r['stage']:<8} {r['type']:<6} "
                      f"{r['volume']:>6.2f} {r['price_open']:>10.2f} {r['sl']:>10.2f} "
                      f"{r['profit']:>+9.2f}")

        findings = detect_duplicates(ours)

    # Summary
    print("\n" + "=" * 70)
    print("  Summary (Current Open Positions)")
    print("=" * 70)
    if df.empty or len(ours) == 0:
        print("  Signals detected:     0")
        print("  Duplicate signals:    0")
        print("  Total lots open:      0.00")
        print("  Total unrealized PnL: $0.00")
        print("\n  [OK] No open positions, nothing to double-check.")
    else:
        findings = detect_duplicates(ours)
        n_signals = len(findings)
        n_dup = sum(1 for f in findings if "DUPLICATE" in f["status"])
        total_lots = ours["volume"].sum()
        total_pnl = ours["profit"].sum()

        print(f"  Signals detected:     {n_signals}")
        print(f"  Duplicate signals:    {n_dup}")
        print(f"  Total lots open:      {total_lots:.2f}")
        print(f"  Total unrealized PnL: ${total_pnl:+.2f}")

        if n_dup > 0:
            print(f"\n  [!!] ACTION REQUIRED:")
            print(f"      EA is double-attached to multiple charts.")
            print(f"      Fix: remove EA from the H2 chart, keep only M30.")
        elif n_signals > 0:
            print(f"\n  [OK] All {n_signals} signal(s) have exactly 3 positions (Stage 1/2/3).")
            print(f"      No duplicate detected, EA is correctly attached to 1 chart only.")

    # ===== Recent deal history scan =====
    print("\n" + "=" * 70)
    print("  Recent Deal History (last 2 days)")
    print("=" * 70)
    deals_df = scan_recent_deals(days=2)
    if deals_df.empty:
        print("  (no recent deals)")
    else:
        # Filter to our magic
        ours_deals = deals_df[(deals_df["magic"] >= magic_min) & (deals_df["magic"] <= magic_max)].copy()
        if ours_deals.empty:
            print(f"  (no {magic_min}-{magic_max} magic deals in last 2 days)")
        else:
            print(f"  Found {len(ours_deals)} 30m2H EA deals (entries + exits):\n")
            print(f"  {'Time':<19} {'Ticket':<10} {'Stage':<8} {'Type':<6} {'Lots':>5} {'Price':>10} {'Entry':<4} {'Reason':<8}")
            print("  " + "-" * 75)
            for _, r in ours_deals.sort_values("time").iterrows():
                print(f"  {r['time'].strftime('%Y-%m-%d %H:%M:%S'):<19} "
                      f"{r['ticket']:<10} {r['stage']:<8} {r['type']:<6} "
                      f"{r['volume']:>5.2f} {r['price']:>10.2f} "
                      f"{r['entry']:<4} {r['reason']:<8}")

            # Detect duplicate opens in history
            print("\n" + "=" * 70)
            print("  Historical Duplicate Detection (entry deals grouped by time)")
            print("=" * 70)
            entries = ours_deals[ours_deals["entry"] == "IN"].copy()
            if entries.empty:
                print("  No entry deals found.")
            else:
                entries["time_round"] = entries["time"].dt.floor("1min")
                entries["price_round"] = entries["price"].round(2)
                hist_findings = []
                for (t, p), grp in entries.groupby(["time_round", "price_round"]):
                    hist_findings.append({
                        "time": t, "price": p,
                        "n": len(grp),
                        "stages": ", ".join(sorted(grp["stage"].tolist())),
                        "lots": grp["volume"].sum(),
                    })
                for f in hist_findings:
                    marker = "[!!]" if f["n"] != 3 else "[OK]"
                    note = " (DUPLICATE: expected 3 stages)" if f["n"] != 3 else ""
                    print(f"  {marker} {f['time']} @ {f['price']}: "
                          f"{f['n']} entries, {f['stages']}, "
                          f"total {f['lots']:.2f} lots{note}")

    mt5.shutdown()


if __name__ == "__main__":
    main()

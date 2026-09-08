# -*- coding: utf-8 -*-
"""模拟盘前向观察（M5）：连接 MT5 演示账户，输出观察报告。
重点：UTC 13-16h 核心盈利时段 + 1/6/8 月旺季（405 笔口径季节性对照）。
用法: python scripts/observe_sim_account.py [--hours 12]
输出: 报告/监测/模拟盘观察_YYYYMMDD_HHMM.md
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "报告" / "监测"
MAGIC_GOLD = 411101
MAGIC_OIL = 411102
WINDOW = (13, 16)          # UTC 13-16h 核心盈利时段
PEAK_MONTHS = (1, 6, 8)    # 旺季：1/6/8 月


def load_baseline() -> pd.DataFrame:
    f = ROOT / "data" / "validation" / "baseline_gold_trades.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, parse_dates=["entry_time"])
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    return df


def seasonal_table(b: pd.DataFrame) -> list[str]:
    lines = []
    lines.append("| 月 | n | EV(pts) | 胜率 | 旺季 |")
    lines.append("|---|---|---|---|---|")
    tot = b.groupby(b["entry_time"].dt.month)["pnl_r_units"].agg(["size", "sum"])
    wr = b.assign(w=(b["pnl_r_units"] > 0)).groupby(b["entry_time"].dt.month)["w"].mean()
    for m in range(1, 13):
        if m not in tot.index:
            continue
        n = int(tot.loc[m, "size"])
        ev = tot.loc[m, "sum"]
        w = wr.get(m, 0)
        flag = "★" if m in PEAK_MONTHS else ""
        lines.append(f"| {m} | {n} | {ev:+.0f} | {w:.0%} | {flag} |")
    return lines


def upcoming_events(hours: float) -> pd.DataFrame:
    ev = pd.read_csv(ROOT / "data" / "processed" / "calendar_events.csv", parse_dates=["event_time_utc"])
    ev["event_time_utc"] = pd.to_datetime(ev["event_time_utc"], utc=True)
    now = pd.Timestamp.utcnow()
    return ev[(ev["is_blackout_event"] == True) & (ev["event_time_utc"] >= now)  # noqa: E712
              & (ev["event_time_utc"] <= now + pd.Timedelta(hours=hours))].sort_values("event_time_utc")


def mt5_snapshot() -> dict:
    """连接运行中的终端，读取账户/持仓/成交；失败时返回错误信息。"""
    try:
        import MetaTrader5 as mt5
    except Exception as e:  # noqa: BLE001
        return {"error": f"MetaTrader5 import failed: {e!r}"}
    if not mt5.initialize():
        return {"error": f"mt5.initialize() failed rc={mt5.last_error()}"}
    try:
        info = mt5.account_info()
        out = {
            "login": info.login if info else None,
            "server": info.server if info else None,
            "balance": info.balance if info else None,
            "equity": info.equity if info else None,
            "currency": info.currency if info else None,
        }
        positions = mt5.positions_get()
        pos_rows = []
        if positions:
            for p in positions:
                pos_rows.append({
                    "ticket": p.ticket, "symbol": p.symbol, "magic": p.magic,
                    "type": "BUY" if p.type == 0 else "SELL", "volume": p.volume,
                    "open_time": datetime.fromtimestamp(p.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    "open": p.price_open, "sl": p.sl, "tp": p.tp,
                    "profit": p.profit,
                })
        out["positions"] = pos_rows
        # 最近 24h 成交（DataEvent magic）
        now_ts = int(pd.Timestamp.utcnow().timestamp())
        deals = mt5.history_deals_get(now_ts - 86400, now_ts)
        out["deals_24h"] = []
        if deals:
            for d in deals:
                if d.magic in (MAGIC_GOLD, MAGIC_OIL):
                    out["deals_24h"].append({
                        "ticket": d.ticket, "symbol": d.symbol, "magic": d.magic,
                        "type": d.type, "volume": d.volume, "price": d.price,
                        "time": datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "profit": d.profit,
                    })
        return out
    finally:
        try:
            mt5.shutdown()
        except Exception:  # noqa: BLE001
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12.0)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    utc_h = now.hour
    in_core_window = WINDOW[0] <= utc_h <= WINDOW[1]
    month = now.month
    in_peak_month = month in PEAK_MONTHS

    REPORTS.mkdir(parents=True, exist_ok=True)
    b = load_baseline()
    snap = mt5_snapshot()

    lines = []
    lines.append("# 模拟盘观察报告（M5 前向观察）")
    lines.append("")
    lines.append(f"> 生成：{now.strftime('%Y-%m-%d %H:%M')} UTC（北京时间 {now.hour+8:02d}:{now.minute:02d}）")
    lines.append("")
    lines.append("## 一、当前时段定位（观察重点）")
    lines.append("")
    lines.append(f"- UTC 时刻：**{utc_h:02d}时** → {'✅ 处于 UTC 13-16h 核心盈利时段（美盘数据窗口）' if in_core_window else '⏳ 非核心时段（核心=UTC 13-16h，贡献 405 笔口径 68% 正收益）'}")
    lines.append(f"- 当前月份：**{month}月** → {'✅ 旺季（1/6/8 月，6 月最强 +134,568pts / 1 月 +107,345 / 8 月 +62,021）' if in_peak_month else '常规月（旺季=1/6/8 月）'}")
    lines.append("")
    lines.append("## 二、账户快照（MetaTrader5 API）")
    lines.append("")
    if "error" in snap:
        lines.append(f"- ⚠️ 无法连接终端：{snap['error']}")
    else:
        lines.append(f"- 账户：{snap.get('login')}（{snap.get('server')}）｜ 余额 {snap.get('balance')} {snap.get('currency')} ｜ 净值 {snap.get('equity')}")
        pos = snap.get("positions", [])
        lines.append(f"- 持仓数：{len(pos)}（含既有策略与 DataEvent magic 411101/411102）")
        if pos:
            lines.append("")
            lines.append("| 品种 | 方向 | 手数 | magic | 开仓(UTC) | 入场 | SL | 浮盈 |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for p in pos:
                lines.append(f"| {p['symbol']} | {p['type']} | {p['volume']} | {p['magic']} | {p['open_time']} | {p['open']} | {p['sl']} | {p['profit']:.2f} |")
        de = snap.get("deals_24h", [])
        lines.append(f"- 近 24h DataEvent 成交：{len(de)} 笔")
        for d in de:
            lines.append(f"  - {d['time']} {d['symbol']} magic={d['magic']} type={d['type']} vol={d['volume']} px={d['price']} pnl={d['profit']}")
        lines.append("")
        lines.append("> 说明：M4 对齐通过前 EA 未挂图表；若 magic 411101/411102 有成交/持仓，说明 EA 已在前向运行。")
    lines.append("")
    lines.append(f"## 三、未来 {args.hours:g}h 白名单高影响事件（事件门将拦截开仓）")
    lines.append("")
    ev = upcoming_events(args.hours)
    if len(ev):
        lines.append("| 时间(UTC) | 币种 | 类别 | 事件 | 距当前(h) |")
        lines.append("|---|---|---|---|---|")
        for _, r_ in ev.iterrows():
            gap = (r_["event_time_utc"] - pd.Timestamp.utcnow()).total_seconds() / 3600
            lines.append(f"| {r_['event_time_utc']} | {r_['currency']} | {r_['category']} | {r_['event_name']} | {gap:.1f} |")
    else:
        lines.append("无")
    lines.append("")
    lines.append("## 四、季节性对照（黄金 405 笔口径 baseline）")
    lines.append("")
    lines.extend(seasonal_table(b))
    lines.append("")
    lines.append("## 五、观察清单核对")
    lines.append("")
    lines.append("- [ ] 事件门拦截：[CAL] event blackout / signal blocked 日志（≥3 次且合理）")
    lines.append("- [ ] V1 过滤不误伤：被拦信号事后 4h 无大幅有利行情")
    lines.append("- [ ] V5 止损放宽：[CAL] widen stop 日志（≥1 次）")
    lines.append("- [ ] 信号方向与 expected ledger 一致（命中率 ≥80%）")
    lines.append("- [ ] 无异常点差/滑点、无崩溃重复下单")
    lines.append("")
    lines.append("## 六、警戒")
    lines.append("")
    lines.append("- 连续 3 月后 2 月为负 / 空单占比 >85% / 12 月加权为负 / MaxDD 达 80% → 暂停观察上报")
    lines.append("")
    lines.append("---")
    lines.append("*自动生成：scripts/observe_sim_account.py（对齐通过后每日运行；UTC 13-16h 建议人工值守）*")

    report = "\n".join(lines)
    out = REPORTS / f"模拟盘观察_{now.strftime('%Y%m%d_%H%M')}.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()

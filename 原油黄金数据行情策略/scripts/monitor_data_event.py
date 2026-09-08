# -*- coding: utf-8 -*-
"""数据行情策略独立监控（每6小时可调度）。
读取本工程的基线/变体交易数据 + 未来事件预告，生成监测报告。
不修改 MTA5_l 现有 observation_dashboard（8 EA 运行中，避免干扰）。
用法: python scripts/monitor_data_event.py [--hours 12]
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "data" / "validation"
REPORTS = ROOT / "报告" / "监测"


def load_trades(name: str) -> pd.DataFrame:
    f = VALIDATION / f"baseline_{name}_trades.csv"
    if not f.exists():
        return pd.DataFrame()
    return pd.read_csv(f, parse_dates=["entry_time"])


def upcoming_events(hours: float = 12.0) -> pd.DataFrame:
    ev = pd.read_csv(ROOT / "data" / "processed" / "calendar_events.csv", parse_dates=["event_time_utc"])
    ev["event_time_utc"] = pd.to_datetime(ev["event_time_utc"], utc=True)
    now = pd.Timestamp.utcnow()
    return ev[(ev["is_blackout_event"] == True) & (ev["event_time_utc"] >= now)
              & (ev["event_time_utc"] <= now + pd.Timedelta(hours=hours))].sort_values("event_time_utc")


def stats(df: pd.DataFrame, col: str) -> dict:
    if df.empty:
        return {"n": 0}
    pn = df[col]
    wins = pn[pn > 0]
    return {"n": len(pn), "wr": round(len(wins) / len(pn), 3),
            "ev": round(float(pn.sum()), 1),
            "pf": round(float(wins.sum() / -pn[pn <= 0].sum()), 3) if (pn <= 0).any() else 999}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12.0)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    REPORTS.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"# 数据行情策略监测报告")
    lines.append(f"")
    lines.append(f"> 生成：{now.strftime('%Y-%m-%d %H:%M')} UTC ｜ 位置：F:\\use_code\\MTA5_l\\原油黄金数据行情策略")
    lines.append(f"")
    lines.append(f"## 总览（基线历史累计）")
    lines.append(f"")
    lines.append(f"| 策略 | 交易 | 胜率 | 累计(EV) | PF | 最新事件 |")
    lines.append(f"|---|---|---|---|---|---|")
    for name, col in (("gold", "pnl_r_units"), ("oil", "pnl_pts")):
        s = stats(load_trades(name), col)
        lines.append(f"| {'Gold' if name=='gold' else 'Oil'}_DataEvent | {s['n']} | {s.get('wr','-')} | {s.get('ev','-')} | {s.get('pf','-')} | — |")
    lines.append(f"")
    lines.append(f"## 未来 {args.hours:g}h 白名单高影响事件")
    lines.append(f"")
    ev = upcoming_events(args.hours)
    if len(ev):
        lines.append(f"| 时间(UTC) | 币种 | 类别 | 事件 |")
        lines.append(f"|---|---|---|---|")
        for _, r_ in ev.iterrows():
            lines.append(f"| {r_['event_time_utc']} | {r_['currency']} | {r_['category']} | {r_['event_name']} |")
    else:
        lines.append("无")
    lines.append(f"")
    lines.append(f"## 警戒")
    lines.append(f"- （规则：连续3月后2月为负 / 空单占比>85% / 12月加权为负 / MaxDD 达80%）")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*自动生成：scripts/monitor_data_event.py（可配 Windows 任务计划每 6h 运行）*")
    report = "\n".join(lines)
    out = REPORTS / f"监测报告_{now.strftime('%Y%m%d_%H%M')}.md"
    out.write_text(report, encoding="utf-8-sig")  # BOM：避免旧 ANSI 工具打开乱码
    print(report)


if __name__ == "__main__":
    main()


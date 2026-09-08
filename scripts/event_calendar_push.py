# -*- coding: utf-8 -*-
"""事件日历定时推送：推送未来 N 天高影响事件(EIA/非农/CPI/FOMC等)到 QQ。

复用现有基础设施：
  - 数据：原油黄金数据行情策略/data/processed/calendar_events.csv（MT5 财经日历导出，2019-2026）
  - 推送：scripts/notify_qq.mjs（受 scripts/qq_push_config.json 控制）

用法：
  python scripts/event_calendar_push.py                 # 推送未来3天(默认)高影响事件
  python scripts/event_calendar_push.py --days 7        # 推送未来7天
  python scripts/event_calendar_push.py --console       # 只打印不推送
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CALENDAR = ROOT / "原油黄金数据行情策略" / "data" / "processed" / "calendar_events.csv"
PUSH_CONFIG = ROOT / "scripts" / "qq_push_config.json"

# 原油监控关键事件类别（可按需增删）
WATCH_CATEGORIES = [
    "EIA原油库存",   # 每周三，原油最直接
    "非农就业",      # 每月首个周五
    "CPI通胀",       # 月度
    "FOMC利率决议",  # 每6周
    "失业率/初请",   # 周度，就业
    "PCE通胀",       # 月度，美联储偏好
    "PPI生产者价格", # 月度
    "GDP",           # 季度
]

# 类别优先级排序（摘要里靠前）
CATEGORY_ORDER = {c: i for i, c in enumerate(WATCH_CATEGORIES)}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_events(days: int) -> pd.DataFrame:
    df = pd.read_csv(CALENDAR)
    df["event_time_utc"] = pd.to_datetime(df["event_time_utc"], utc=True)
    now = now_utc()
    horizon = now + timedelta(days=days)
    mask = (
        df["is_high"].astype(bool)
        & (df["currency"] == "USD")           # 美国事件（对原油/美元影响最大）
        & (df["category"].isin(WATCH_CATEGORIES))
        & (df["event_time_utc"] >= now)
        & (df["event_time_utc"] <= horizon)
    )
    sel = df.loc[mask].copy()
    sel["order"] = sel["category"].map(CATEGORY_ORDER).fillna(99)
    sel = sel.sort_values(["event_time_utc", "order"])
    return sel


def fmt_cn(dt: pd.Timestamp) -> str:
    """UTC -> 北京时间(UTC+8)。"""
    return (dt + timedelta(hours=8)).strftime("%m-%d %H:%M")


def build_text(sel: pd.DataFrame, days: int) -> str:
    now = now_utc()
    lines = [
        f"【原油·事件日历】未来 {days} 天高影响事件（美国）",
        f"生成: {now.strftime('%Y-%m-%d %H:%M')} UTC",
        f"共 {len(sel)} 条 | 只含 EIA/非农/CPI/FOMC/失业率/PCE/PPI/GDP",
        "",
    ]
    if sel.empty:
        lines.append("（未来 {} 天无高影响事件）".format(days))
        return "\n".join(lines)

    # 按天分组（统一用北京时间，避免跨日事件分错组）
    prev_day = None
    for _, r in sel.iterrows():
        t = r["event_time_utc"]
        t_cn = t + timedelta(hours=8)  # 北京时间
        day = t_cn.strftime("%m-%d")
        if day != prev_day:
            if prev_day is not None:
                lines.append("")
            lines.append(f"◆ {t_cn.strftime('%m-%d %a')}（北京时间）")
            prev_day = day
        name = str(r["event_name"])
        cat = str(r["category"])
        lines.append(f"  {t_cn.strftime('%m-%d %H:%M')}  [{cat}] {name}")
    return "\n".join(lines)


def push(text: str) -> None:
    cfg = {}
    try:
        cfg = json.loads(PUSH_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        pass
    if not (cfg.get("enabled") and cfg.get("targetId")):
        print("[event_calendar] QQ 未启用(enabled/targetId)，仅输出摘要")
        return
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(text)
            tmp = tf.name
        node = str(cfg.get("node_path") or "node")
        subprocess.run([node, str(ROOT / "scripts" / "notify_qq.mjs"), "--file", tmp], check=False)
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--console", action="store_true")
    args = ap.parse_args()

    sel = load_events(args.days)
    text = build_text(sel, args.days)
    print(text)
    if not args.console:
        push(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Render a stop-loss review report for the current main strategy."""
import html
import os
import sys
from collections import Counter

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _stage12_combo_test as s12


RESULT_ROOT = os.path.join(ROOT, "data", "results", "current_strategy_20260627", "stop_loss_review")
CHART_DIR = os.path.join(RESULT_ROOT, "charts")
CSV_PATH = os.path.join(RESULT_ROOT, "stop_loss_trades.csv")
HTML_PATH = os.path.join(RESULT_ROOT, "stop_loss_report.html")

STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
LOTS_PER_STAGE = 0.02
PT_VALUE_PER_LOT = 10.0
MERGED_DIR_COL = "\u65b9\u5411_\u5408\u5e76\u540e"


def first_opposite_idx(direction, start_i, is_long):
    target = "bad" if is_long else "good"
    for i in range(start_i + 1, len(direction)):
        if direction[i] == target:
            return i
    return len(direction) - 1


def sl_hit_before(df, start_i, end_i, is_long, stop):
    if end_i <= start_i:
        return None
    seg = df.iloc[start_i + 1 : end_i + 1]
    if len(seg) == 0:
        return None
    hits = seg["low"] <= stop if is_long else seg["high"] >= stop
    if hits.any():
        hit_pos = hits.to_numpy().argmax()
        row = seg.iloc[hit_pos]
        return {
            "price": float(stop),
            "time": pd.Timestamp(row["date"]),
            "idx": int(seg.index[hit_pos]),
        }
    return None


def stage1_exit_detail(df, trade, stage1_r):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    risk = abs(entry - stop)
    target = entry + stage1_r * risk if is_long else entry - stage1_r * risk

    for j in range(i + 1, len(df)):
        row = df.iloc[j]
        if is_long and row["low"] <= stop:
            return {
                "pnl": -risk,
                "exit": "SL hit",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": stop,
                "stop_type": "hard_stop",
            }
        if (not is_long) and row["high"] >= stop:
            return {
                "pnl": -risk,
                "exit": "SL hit",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": stop,
                "stop_type": "hard_stop",
            }
        if is_long and row["high"] >= target:
            return {
                "pnl": stage1_r * risk,
                "exit": f"{stage1_r:.1f}R TP",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": target,
                "stop_type": "",
            }
        if (not is_long) and row["low"] <= target:
            return {
                "pnl": stage1_r * risk,
                "exit": f"{stage1_r:.1f}R TP",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": target,
                "stop_type": "",
            }
    return {
        "pnl": 0.0,
        "exit": "data end",
        "time": pd.Timestamp(df.iloc[-1]["date"]),
        "idx": len(df) - 1,
        "price": float(df.iloc[-1]["close"]),
        "stop_type": "",
    }


def stage2_exit_detail(df, trade, trail_r, force_r):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    risk = abs(entry - stop)
    trail_start = entry + trail_r * risk if is_long else entry - trail_r * risk
    force = entry + force_r * risk if is_long else entry - force_r * risk
    trail_sl = stop
    end_i = first_opposite_idx(df[MERGED_DIR_COL].values, i, is_long)

    for j in range(i + 1, end_i + 1):
        row = df.iloc[j]
        if is_long and row["high"] >= force:
            return {
                "pnl": force_r * risk,
                "exit": f"{force_r:.1f}R forced",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": force,
                "stop_type": "",
            }
        if (not is_long) and row["low"] <= force:
            return {
                "pnl": force_r * risk,
                "exit": f"{force_r:.1f}R forced",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": force,
                "stop_type": "",
            }
        if is_long and row["low"] <= trail_sl:
            return {
                "pnl": trail_sl - entry,
                "exit": "trail/SL hit",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": trail_sl,
                "stop_type": "hard_stop" if abs(trail_sl - stop) < 1e-9 else "trail_stop",
            }
        if (not is_long) and row["high"] >= trail_sl:
            return {
                "pnl": entry - trail_sl,
                "exit": "trail/SL hit",
                "time": pd.Timestamp(row["date"]),
                "idx": j,
                "price": trail_sl,
                "stop_type": "hard_stop" if abs(trail_sl - stop) < 1e-9 else "trail_stop",
            }
        if is_long and row["high"] >= trail_start and row["SMA_13"] > trail_sl:
            trail_sl = float(row["SMA_13"])
        if (not is_long) and row["low"] <= trail_start and (row["SMA_13"] < trail_sl or trail_sl == stop):
            trail_sl = float(row["SMA_13"])

    exit_price = float(df.iloc[end_i]["close"])
    return {
        "pnl": exit_price - entry if is_long else entry - exit_price,
        "exit": "M30 merged cross",
        "time": pd.Timestamp(df.iloc[end_i]["date"]),
        "idx": end_i,
        "price": exit_price,
        "stop_type": "",
    }


def stage3_exit_detail(df, trade):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    end_i = first_opposite_idx(df[MERGED_DIR_COL].values, i, is_long)
    sl = sl_hit_before(df, i, end_i, is_long, stop)
    if sl is not None:
        return {
            "pnl": -abs(entry - stop),
            "exit": "SL hit",
            "time": sl["time"],
            "idx": sl["idx"],
            "price": float(stop),
            "stop_type": "hard_stop",
        }
    exit_price = float(df.iloc[end_i]["close"])
    return {
        "pnl": exit_price - entry if is_long else entry - exit_price,
        "exit": "M30 merged cross",
        "time": pd.Timestamp(df.iloc[end_i]["date"]),
        "idx": end_i,
        "price": exit_price,
        "stop_type": "",
    }


def classify_stop_pattern(row):
    parts = []
    if row["stage1_stop"]:
        parts.append("stage1")
    if row["stage2_stop"]:
        parts.append("stage2")
    if row["stage3_stop"]:
        parts.append("stage3")
    key = "_".join(parts) if parts else "no_stop"
    labels = {
        "stage1_stage2_stage3": "\u4e09\u6bb5\u5168\u90e8\u6b62\u635f",
        "stage1_stage2": "Stage 1 + Stage 2 \u6b62\u635f",
        "stage1_stage3": "Stage 1 + Stage 3 \u6b62\u635f",
        "stage2_stage3": "Stage 2 + Stage 3 \u6b62\u635f",
        "stage1": "Stage 1 \u6b62\u635f",
        "stage2": "Stage 2 \u6b62\u635f",
        "stage3": "Stage 3 \u6b62\u635f",
        "no_stop": "\u65e0",
    }
    return key, labels[key]


def build_stop_frame():
    df, signals = s12.build_combo_signals()
    rows = []
    for _, trade in signals.iterrows():
        stage1 = stage1_exit_detail(df, trade, STAGE1_R)
        stage2 = stage2_exit_detail(df, trade, STAGE2_TRAIL_R, STAGE2_FORCE_R)
        stage3 = stage3_exit_detail(df, trade)
        total_points = stage1["pnl"] + stage2["pnl"] + stage3["pnl"]
        row = {
            "date": pd.Timestamp(trade["date"]),
            "entry_time": pd.Timestamp(trade["entry_time"]),
            "mode": trade["mode"],
            "dir": trade["dir"],
            "anchor_i": int(trade["anchor_i"]),
            "i": int(trade["i"]),
            "entry": float(trade["entry"]),
            "stop": float(trade["stop"]),
            "sd": float(trade["sd"]),
            "Bias_5": float(trade["Bias_5"]),
            "Bias_13": float(trade["Bias_13"]),
            "Bias_55": float(trade["Bias_55"]),
            "spec_reason": trade["spec_reason"],
            "stage1_pnl": float(stage1["pnl"]),
            "stage1_exit": stage1["exit"],
            "stage1_time": stage1["time"],
            "stage1_idx": int(stage1["idx"]),
            "stage1_price": float(stage1["price"]),
            "stage1_stop_type": stage1["stop_type"],
            "stage2_pnl": float(stage2["pnl"]),
            "stage2_exit": stage2["exit"],
            "stage2_time": stage2["time"],
            "stage2_idx": int(stage2["idx"]),
            "stage2_price": float(stage2["price"]),
            "stage2_stop_type": stage2["stop_type"],
            "stage3_pnl": float(stage3["pnl"]),
            "stage3_exit": stage3["exit"],
            "stage3_time": stage3["time"],
            "stage3_idx": int(stage3["idx"]),
            "stage3_price": float(stage3["price"]),
            "stage3_stop_type": stage3["stop_type"],
            "total_points": float(total_points),
            "total_$": float(total_points * LOTS_PER_STAGE * PT_VALUE_PER_LOT),
        }
        row["stage1_stop"] = row["stage1_exit"] == "SL hit"
        row["stage2_stop"] = "SL" in str(row["stage2_exit"])
        row["stage3_stop"] = "SL" in str(row["stage3_exit"])
        row["any_stop"] = row["stage1_stop"] or row["stage2_stop"] or row["stage3_stop"]
        row["stop_stage_count"] = int(row["stage1_stop"]) + int(row["stage2_stop"]) + int(row["stage3_stop"])
        row["pattern_key"], row["pattern_label"] = classify_stop_pattern(row)
        row["holding_bars"] = max(row["stage1_idx"], row["stage2_idx"], row["stage3_idx"]) - row["i"]
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    stop_df = out[out["any_stop"]].copy().reset_index(drop=True)
    stop_df["trade_id"] = [f"T{idx + 1:02d}" for idx in range(len(stop_df))]
    return df, out, stop_df


def plot_candles(ax, frame):
    x = frame["plot_x"].to_list()
    width = 0.55
    for xval, (_, row) in zip(x, frame.iterrows()):
        color = "#16a34a" if row["close"] >= row["open"] else "#dc2626"
        ax.vlines(xval, row["low"], row["high"], color=color, linewidth=1.0, alpha=0.9)
        lower = min(row["open"], row["close"])
        height = abs(row["close"] - row["open"])
        if height < 0.02:
            height = 0.02
        rect = Rectangle(
            (xval - width / 2.0, lower),
            width,
            height,
            facecolor=color,
            edgecolor=color,
            linewidth=0.7,
            alpha=0.75,
        )
        ax.add_patch(rect)
    return x


def render_trade_chart(df, row):
    left = max(int(row["i"]) - 12, 0)
    right = min(max(int(row["stage1_idx"]), int(row["stage2_idx"]), int(row["stage3_idx"])) + 8, len(df) - 1)
    frame = df.iloc[left : right + 1].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["plot_x"] = list(range(len(frame)))
    path = os.path.join(CHART_DIR, f"{row['trade_id']}_{row['date']:%Y%m%d_%H%M}_{row['mode']}_{row['dir']}.png")

    fig, ax = plt.subplots(figsize=(12, 5.6))
    plot_candles(ax, frame)
    ax.plot(frame["plot_x"], frame["SMA_5"], color="#f59e0b", linewidth=1.4, label="SMA 5")
    ax.plot(frame["plot_x"], frame["SMA_13"], color="#2563eb", linewidth=1.4, label="SMA 13")

    hold_end = max(int(row["stage1_idx"]), int(row["stage2_idx"]), int(row["stage3_idx"]))
    entry_x = int(row["i"]) - left
    stage1_x = int(row["stage1_idx"]) - left
    stage2_x = int(row["stage2_idx"]) - left
    stage3_x = int(row["stage3_idx"]) - left
    ax.hlines(
        float(row["stop"]),
        xmin=entry_x,
        xmax=max(stage1_x, stage2_x, stage3_x),
        colors="#7c3aed",
        linestyles="--",
        linewidth=1.2,
        label="Stop",
    )
    ax.axvline(entry_x, color="#334155", linestyle=":", linewidth=1.0, alpha=0.8)

    markers = [
        ("Entry", entry_x, float(row["entry"]), "#111827", "^"),
        ("Stage 1", stage1_x, float(row["stage1_price"]), "#9333ea", "o"),
        ("Stage 2", stage2_x, float(row["stage2_price"]), "#0891b2", "s"),
        ("Stage 3", stage3_x, float(row["stage3_price"]), "#dc2626", "D"),
    ]
    for label, xval, yval, color, marker in markers:
        ax.scatter([xval], [yval], color=color, marker=marker, s=56, zorder=5)
        ax.annotate(
            label,
            (xval, yval),
            xytext=(4, 8),
            textcoords="offset points",
            fontsize=8,
            color=color,
            weight="bold",
        )

    ax.set_title(
        f"{row['trade_id']}  {row['date']:%Y-%m-%d %H:%M}  {row['dir']}  {row['mode']}  total {row['total_points']:+.2f} pt",
        fontsize=11,
    )
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.18)
    ax.legend(loc="upper left", ncol=4, fontsize=8, frameon=False)
    tick_step = max(len(frame) // 6, 1)
    tick_positions = list(range(0, len(frame), tick_step))
    if tick_positions[-1] != len(frame) - 1:
        tick_positions.append(len(frame) - 1)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([frame.iloc[pos]["date"].strftime("%m-%d\n%H:%M") for pos in tick_positions])
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def mode_table(stop_df):
    counts = stop_df["mode"].value_counts()
    rows = []
    for mode, count in counts.items():
        avg_loss = stop_df.loc[stop_df["mode"] == mode, "total_points"].mean()
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(mode))}</td>"
            f"<td>{int(count)}</td>"
            f"<td>{avg_loss:+.2f} pt</td>"
            "</tr>"
        )
    return "\n".join(rows)


def pattern_table(stop_df):
    counts = stop_df["pattern_label"].value_counts()
    rows = []
    for label, count in counts.items():
        avg_loss = stop_df.loc[stop_df["pattern_label"] == label, "total_points"].mean()
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(label))}</td>"
            f"<td>{int(count)}</td>"
            f"<td>{avg_loss:+.2f} pt</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_trade_card(row, rel_img):
    stage_tags = []
    for stage_name, stopped, exit_name, stop_type, pnl in [
        ("Stage 1", row["stage1_stop"], row["stage1_exit"], row["stage1_stop_type"], row["stage1_pnl"]),
        ("Stage 2", row["stage2_stop"], row["stage2_exit"], row["stage2_stop_type"], row["stage2_pnl"]),
        ("Stage 3", row["stage3_stop"], row["stage3_exit"], row["stage3_stop_type"], row["stage3_pnl"]),
    ]:
        cls = "tag-stop" if stopped else "tag-pass"
        text = f"{stage_name}: {exit_name} ({pnl:+.2f} pt)"
        if stop_type:
            text += f" / {stop_type}"
        stage_tags.append(f'<span class="tag {cls}">{html.escape(text)}</span>')

    return f"""
    <section class="trade-card" id="{row['trade_id']}">
      <div class="trade-head">
        <div>
          <h2>{row['trade_id']} | {row['date']:%Y-%m-%d %H:%M} | {row['dir']} | {html.escape(str(row['mode']))}</h2>
          <p class="sub">{row['pattern_label']} | total {row['total_points']:+.2f} pt | ${row['total_$']:+.2f}</p>
        </div>
        <div class="meta-grid">
          <div><span>Entry</span><strong>{row['entry']:.3f}</strong></div>
          <div><span>Stop</span><strong>{row['stop']:.3f}</strong></div>
          <div><span>SD</span><strong>{row['sd']:.3f}</strong></div>
          <div><span>Bars</span><strong>{int(row['holding_bars'])}</strong></div>
          <div><span>Bias55</span><strong>{row['Bias_55']:.3f}%</strong></div>
          <div><span>Stage count</span><strong>{int(row['stop_stage_count'])}</strong></div>
        </div>
      </div>
      <div class="tag-row">
        {''.join(stage_tags)}
      </div>
      <img loading="lazy" src="{html.escape(rel_img)}" alt="{row['trade_id']} chart" />
    </section>
    """


def render_html(all_df, stop_df, image_map):
    total_points = float(stop_df["total_points"].sum())
    total_dollar = float(stop_df["total_$"].sum())
    full_stop_count = int((stop_df["pattern_key"] == "stage1_stage2_stage3").sum())
    worst_row = stop_df.nsmallest(1, "total_points").iloc[0]
    html_cards = []
    for _, row in stop_df.iterrows():
        rel_img = os.path.relpath(image_map[row["trade_id"]], RESULT_ROOT).replace("\\", "/")
        html_cards.append(build_trade_card(row, rel_img))

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>止损交易复盘</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --panel: #ffffff;
      --line: #dbe4ee;
      --text: #0f172a;
      --muted: #475569;
      --accent: #2563eb;
      --stop: #b91c1c;
      --good: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    .wrap {{
      width: min(1400px, calc(100vw - 32px));
      margin: 24px auto 48px;
    }}
    .hero, .panel, .trade-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .hero {{
      padding: 20px 22px;
      margin-bottom: 16px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    .hero h1 {{ font-size: 28px; margin-bottom: 8px; }}
    .hero p {{ color: var(--muted); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 16px 0 0;
    }}
    .stat {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .stat strong {{ font-size: 24px; }}
    .grid2 {{
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .panel {{
      padding: 16px 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    .table-scroll {{ overflow-x: auto; }}
    .trade-list {{
      display: grid;
      gap: 16px;
    }}
    .trade-card {{
      padding: 16px;
    }}
    .trade-card img {{
      width: 100%;
      height: auto;
      display: block;
      border: 1px solid var(--line);
      border-radius: 6px;
      margin-top: 14px;
      background: #fff;
    }}
    .trade-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
    }}
    .trade-head h2 {{
      font-size: 18px;
      margin-bottom: 6px;
    }}
    .sub {{
      color: var(--muted);
      font-size: 14px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(96px, 1fr));
      gap: 10px 12px;
      min-width: 340px;
    }}
    .meta-grid span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }}
    .meta-grid strong {{
      font-size: 15px;
    }}
    .tag-row {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }}
    .tag {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: #f8fafc;
    }}
    .tag-stop {{
      border-color: #fecaca;
      background: #fef2f2;
      color: var(--stop);
    }}
    .tag-pass {{
      border-color: #bbf7d0;
      background: #f0fdf4;
      color: var(--good);
    }}
    .mini-note {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 10px;
    }}
    @media (max-width: 1080px) {{
      .grid2 {{ grid-template-columns: 1fr; }}
      .trade-head {{ flex-direction: column; }}
      .meta-grid {{
        min-width: 0;
        width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>当前主线策略止损交易复盘</h1>
      <p>基于当前主线策略：Layer 1 `|H2 Bias_55| > 3.0%`，Layer 2 `pre_cross + cross + post_n(2-6)`，Layer 3 `Bias_5 top 30%`，M15 `replace_any + rescue`，H2 `q2 early-gate`，退出 `2.0R / 1.5R trail / 4.0R force / m30_merged_cross`。</p>
      <div class="stats">
        <div class="stat"><span>总交易数</span><strong>{len(all_df)}</strong></div>
        <div class="stat"><span>任一阶段止损</span><strong>{len(stop_df)}</strong></div>
        <div class="stat"><span>三段全部止损</span><strong>{full_stop_count}</strong></div>
        <div class="stat"><span>止损单总计</span><strong>{total_points:+.1f} pt</strong></div>
        <div class="stat"><span>止损单美元合计</span><strong>${total_dollar:+.0f}</strong></div>
        <div class="stat"><span>最差单</span><strong>{worst_row['trade_id']} {worst_row['total_points']:+.1f} pt</strong></div>
      </div>
      <p class="mini-note">说明：这里的“止损交易”指 Stage 1 / Stage 2 / Stage 3 任一阶段出现 `SL hit` 或 `trail/SL hit`。因此它包含“整单三段都被打掉”的单子，也包含“其中一段止损、但整单最后仍盈利”的单子。</p>
    </section>

    <div class="grid2">
      <section class="panel">
        <h3>按止损模式汇总</h3>
        <div class="table-scroll">
          <table>
            <thead><tr><th>模式</th><th>笔数</th><th>平均 total</th></tr></thead>
            <tbody>
              {pattern_table(stop_df)}
            </tbody>
          </table>
        </div>
      </section>
      <section class="panel">
        <h3>按入场机会汇总</h3>
        <div class="table-scroll">
          <table>
            <thead><tr><th>mode</th><th>笔数</th><th>平均 total</th></tr></thead>
            <tbody>
              {mode_table(stop_df)}
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="panel" style="margin-bottom:16px;">
      <h3>止损交易清单</h3>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Date</th><th>Dir</th><th>Mode</th><th>Pattern</th>
              <th>Entry</th><th>Stop</th><th>SD</th><th>Total pt</th><th>$</th>
            </tr>
          </thead>
          <tbody>
            {"".join(
                f"<tr><td><a href='#{row['trade_id']}'>{row['trade_id']}</a></td><td>{row['date']:%Y-%m-%d %H:%M}</td><td>{row['dir']}</td><td>{html.escape(str(row['mode']))}</td><td>{html.escape(str(row['pattern_label']))}</td><td>{row['entry']:.3f}</td><td>{row['stop']:.3f}</td><td>{row['sd']:.3f}</td><td>{row['total_points']:+.2f}</td><td>${row['total_$']:+.2f}</td></tr>"
                for _, row in stop_df.iterrows()
            )}
          </tbody>
        </table>
      </div>
    </section>

    <div class="trade-list">
      {''.join(html_cards)}
    </div>
  </div>
</body>
</html>
"""
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(doc)


def main():
    os.makedirs(CHART_DIR, exist_ok=True)
    df, all_df, stop_df = build_stop_frame()
    stop_df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    image_map = {}
    for _, row in stop_df.iterrows():
        image_map[row["trade_id"]] = render_trade_chart(df, row)

    render_html(all_df, stop_df, image_map)

    counts = Counter(stop_df["pattern_label"])
    print(f"All trades: {len(all_df)}")
    print(f"Stop trades: {len(stop_df)}")
    for key, value in counts.items():
        print(f"- {key}: {value}")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {HTML_PATH}")


if __name__ == "__main__":
    main()

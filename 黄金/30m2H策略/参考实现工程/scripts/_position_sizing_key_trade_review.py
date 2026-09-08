# -*- coding: utf-8 -*-
"""Render graphical review for the most important position-sizing gap trades."""
import html
import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _current_baseline as base
import _stop_loss_trade_report as slr


RESULT_ROOT = os.path.join(ROOT, "data", "results", "position_sizing_strict_certify_20260628")
REVIEW_ROOT = os.path.join(RESULT_ROOT, "key_trade_review")
CHART_DIR = os.path.join(REVIEW_ROOT, "charts")
HTML_PATH = os.path.join(REVIEW_ROOT, "position_sizing_key_trade_review.html")
TOP_CSV = os.path.join(REVIEW_ROOT, "top20_key_trades.csv")
GAP_CURVE_PATH = os.path.join(REVIEW_ROOT, "gap_curve_top20.png")
EQUITY_COMPARE_PATH = os.path.join(REVIEW_ROOT, "equity_compare_top20.png")
REPORT_PATH = os.path.join(ROOT, "30m2H策略", "仓位档位关键交易图形复盘.md")
GAP_INPUT = os.path.join(RESULT_ROOT, "position_sizing_gap_contributors.csv")

TOP_N = 20


def zh_dir(value):
    return "多单" if value == "L" else "空单"


def gap_side(delta_value):
    return "拉开收益差距" if delta_value >= 0 else "缩小收益差距"


def money(value):
    return f"${value:+.2f}"


def build_review_frame():
    result = base.summarize_strategy()
    price_df = result["df"].copy()
    picked = result["picked"].copy()
    rows = []
    for _, trade in picked.iterrows():
        stage1 = slr.stage1_exit_detail(price_df, trade, base.DEFAULT_STAGE1_R)
        stage2 = slr.stage2_exit_detail(price_df, trade, base.DEFAULT_STAGE2_TRAIL_R, base.DEFAULT_STAGE2_FORCE_R)
        stage3 = slr.stage3_exit_detail(price_df, trade)
        total_points = stage1["pnl"] + stage2["pnl"] + stage3["pnl"]
        rows.append(
            {
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
                "total_$": float(total_points * slr.LOTS_PER_STAGE * slr.PT_VALUE_PER_LOT),
                "holding_bars": max(int(stage1["idx"]), int(stage2["idx"]), int(stage3["idx"])) - int(trade["i"]),
            }
        )
    detail_df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    gap_df = pd.read_csv(GAP_INPUT, encoding="utf-8-sig")
    gap_df["date"] = pd.to_datetime(gap_df["date"])

    keep_cols = [
        "date",
        "mode",
        "dir",
        "entry_time",
        "anchor_i",
        "i",
        "entry",
        "stop",
        "sd",
        "Bias_5",
        "Bias_13",
        "Bias_55",
        "spec_reason",
        "stage1_pnl",
        "stage1_exit",
        "stage1_time",
        "stage1_idx",
        "stage1_price",
        "stage1_stop_type",
        "stage2_pnl",
        "stage2_exit",
        "stage2_time",
        "stage2_idx",
        "stage2_price",
        "stage2_stop_type",
        "stage3_pnl",
        "stage3_exit",
        "stage3_time",
        "stage3_idx",
        "stage3_price",
        "stage3_stop_type",
        "total_points",
        "total_$",
        "holding_bars",
    ]
    merged = gap_df.merge(
        detail_df[keep_cols],
        on=["date", "mode", "dir", "stage1_exit", "stage2_exit", "stage3_exit"],
        how="left",
        validate="one_to_one",
    )
    if merged["i"].isna().any():
        missing = merged[merged["i"].isna()][["date", "mode", "dir"]].head(5)
        raise RuntimeError(f"Failed to rebuild detailed trades for:\n{missing.to_string(index=False)}")

    merged["abs_delta_$"] = merged["delta_$"].abs()
    merged["gap_side"] = merged["delta_$"].apply(gap_side)
    merged = merged.sort_values("date").reset_index(drop=True)

    top = merged.sort_values(["abs_delta_$", "delta_$", "date"], ascending=[False, False, True]).head(TOP_N).copy()
    top = top.reset_index(drop=True)
    top["review_id"] = [f"K{idx + 1:02d}" for idx in range(len(top))]
    return price_df, merged, top


def render_gap_curve(merged, top):
    fig, ax = plt.subplots(figsize=(12.5, 4.2))
    ax.plot(merged["date"], merged["cum_gap_$"], color="#2563eb", linewidth=2.0, label="Cumulative gap")
    ax.axhline(0.0, color="#64748b", linewidth=1.0, linestyle="--", alpha=0.8)
    ax.scatter(
        top["date"],
        top["cum_gap_$"],
        color=["#16a34a" if v >= 0 else "#dc2626" for v in top["delta_$"]],
        s=34,
        zorder=5,
        label="Top 20 key trades",
    )
    for _, row in top.head(8).iterrows():
        ax.annotate(
            row["review_id"],
            (row["date"], row["cum_gap_$"]),
            xytext=(4, 8),
            textcoords="offset points",
            fontsize=8,
            color="#0f172a",
        )
    ax.set_title("Peak vs Balanced: cumulative gap")
    ax.set_ylabel("Gap ($)")
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(GAP_CURVE_PATH, dpi=150)
    plt.close(fig)


def render_equity_compare(merged):
    fig, ax = plt.subplots(figsize=(12.5, 4.2))
    ax.plot(merged["date"], merged["balanced_eq_$"], color="#0891b2", linewidth=2.0, label="Balanced 0.5/1.0/1.5")
    ax.plot(merged["date"], merged["peak_eq_$"], color="#7c3aed", linewidth=2.0, label="Peak 0.5/0.5/2.0")
    ax.set_title("Equity curve comparison")
    ax.set_ylabel("Equity ($)")
    ax.grid(True, alpha=0.18)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(EQUITY_COMPARE_PATH, dpi=150)
    plt.close(fig)


def render_trade_chart(price_df, row):
    left = max(int(row["i"]) - 14, 0)
    right = min(max(int(row["stage1_idx"]), int(row["stage2_idx"]), int(row["stage3_idx"])) + 10, len(price_df) - 1)
    frame = price_df.iloc[left : right + 1].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["plot_x"] = list(range(len(frame)))
    path = os.path.join(
        CHART_DIR,
        f"{row['review_id']}_{row['date']:%Y%m%d_%H%M}_{row['mode']}_{row['dir']}.png",
    )

    fig, ax = plt.subplots(figsize=(13.6, 6.2))
    slr.plot_candles(ax, frame)
    ax.plot(frame["plot_x"], frame["SMA_5"], color="#f59e0b", linewidth=1.5, label="SMA 5")
    ax.plot(frame["plot_x"], frame["SMA_13"], color="#2563eb", linewidth=1.5, label="SMA 13")

    entry_x = int(row["i"]) - left
    stage1_x = int(row["stage1_idx"]) - left
    stage2_x = int(row["stage2_idx"]) - left
    stage3_x = int(row["stage3_idx"]) - left
    hold_end_x = max(stage1_x, stage2_x, stage3_x)

    ax.axvspan(entry_x, hold_end_x, color="#cbd5e1", alpha=0.12)
    ax.axvline(entry_x, color="#334155", linestyle=":", linewidth=1.0, alpha=0.85)
    ax.hlines(
        float(row["stop"]),
        xmin=entry_x,
        xmax=hold_end_x,
        colors="#7c3aed",
        linestyles="--",
        linewidth=1.3,
        label="Stop",
    )

    entry_marker = "^" if row["dir"] == "L" else "v"
    markers = [
        (f"Entry {row['dir']}", entry_x, float(row["entry"]), "#111827", entry_marker, (5, 10)),
        ("S1 exit", stage1_x, float(row["stage1_price"]), "#9333ea", "o", (5, 10)),
        ("S2 exit", stage2_x, float(row["stage2_price"]), "#0891b2", "s", (5, -14)),
        ("S3 exit", stage3_x, float(row["stage3_price"]), "#dc2626", "D", (5, 10)),
    ]
    for label, xval, yval, color, marker, offset in markers:
        ax.scatter([xval], [yval], color=color, marker=marker, s=62, zorder=6)
        ax.annotate(
            label,
            (xval, yval),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            color=color,
            weight="bold",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": "none", "alpha": 0.78},
        )

    info_lines = [
        f"{row['review_id']} | {row['date']:%Y-%m-%d %H:%M} | {row['dir']} | {row['mode']}",
        f"Balanced: {money(row['balanced_$'])} / {row['balanced_rr']:+.2f}R",
        f"Peak: {money(row['peak_$'])} / {row['peak_rr']:+.2f}R",
        f"Trade gap: {money(row['delta_$'])} | Cum gap: {money(row['cum_gap_$'])}",
        f"S1: {row['stage1_exit']} @ {row['stage1_price']:.3f}",
        f"S2: {row['stage2_exit']} @ {row['stage2_price']:.3f}",
        f"S3: {row['stage3_exit']} @ {row['stage3_price']:.3f}",
        f"Entry {row['entry']:.3f} | Stop {row['stop']:.3f} | Risk {abs(float(row['entry']) - float(row['stop'])):.3f}",
    ]
    fig.subplots_adjust(right=0.78)
    ax.text(
        1.01,
        1.0,
        "\n".join(info_lines),
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        color="#0f172a",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#f8fafc", "edgecolor": "#cbd5e1"},
    )

    ax.set_title(
        f"{row['review_id']}  {money(row['delta_$'])}  |  base total {row['total_points']:+.2f} pt",
        fontsize=11,
    )
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.18)
    ax.legend(loc="upper left", ncol=3, fontsize=8, frameon=False)

    tick_step = max(len(frame) // 7, 1)
    tick_positions = list(range(0, len(frame), tick_step))
    if tick_positions[-1] != len(frame) - 1:
        tick_positions.append(len(frame) - 1)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([frame.iloc[pos]["date"].strftime("%m-%d\n%H:%M") for pos in tick_positions])
    fig.tight_layout()
    fig.savefig(path, dpi=145)
    plt.close(fig)
    return path


def build_overview_table(top):
    rows = []
    for _, row in top.iterrows():
        rows.append(
            "<tr>"
            f"<td><a href=\"#{row['review_id']}\">{row['review_id']}</a></td>"
            f"<td>{row['date']:%Y-%m-%d %H:%M}</td>"
            f"<td>{html.escape(str(row['mode']))}</td>"
            f"<td>{zh_dir(row['dir'])}</td>"
            f"<td>{html.escape(str(row['gap_side']))}</td>"
            f"<td>{money(row['delta_$'])}</td>"
            f"<td>{money(row['cum_gap_$'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_trade_card(row, rel_img):
    exit_rows = [
        ("Stage 1", row["stage1_exit"], row["stage1_price"], row["balanced_$"], row["peak_$"]),
        ("Stage 2", row["stage2_exit"], row["stage2_price"], None, None),
        ("Stage 3", row["stage3_exit"], row["stage3_price"], None, None),
    ]
    exit_html = []
    for stage, exit_name, exit_price, _, _ in exit_rows:
        exit_html.append(
            "<li>"
            f"<strong>{stage}</strong>: {html.escape(str(exit_name))} @ {exit_price:.3f}"
            "</li>"
        )

    return f"""
    <section class="trade-card" id="{row['review_id']}">
      <div class="trade-head">
        <div>
          <h2>{row['review_id']} | {row['date']:%Y-%m-%d %H:%M} | {zh_dir(row['dir'])} | {html.escape(str(row['mode']))}</h2>
          <p class="sub">{html.escape(str(row['gap_side']))} | 单笔差额 {money(row['delta_$'])} | 累计差额 {money(row['cum_gap_$'])}</p>
        </div>
        <div class="meta-grid">
          <div><span>Entry</span><strong>{row['entry']:.3f}</strong></div>
          <div><span>Stop</span><strong>{row['stop']:.3f}</strong></div>
          <div><span>Bars</span><strong>{int(row['holding_bars'])}</strong></div>
          <div><span>Bias55</span><strong>{row['Bias_55']:.3f}%</strong></div>
          <div><span>平衡推荐</span><strong>{money(row['balanced_$'])}</strong></div>
          <div><span>收益峰值</span><strong>{money(row['peak_$'])}</strong></div>
        </div>
      </div>
      <div class="compare-grid">
        <div class="metric-box">
          <span>平衡推荐 0.5/1.0/1.5</span>
          <strong>{money(row['balanced_$'])}</strong>
          <small>{row['balanced_rr']:+.2f}R</small>
        </div>
        <div class="metric-box peak">
          <span>收益峰值 0.5/0.5/2.0</span>
          <strong>{money(row['peak_$'])}</strong>
          <small>{row['peak_rr']:+.2f}R</small>
        </div>
      </div>
      <ul class="exit-list">
        {''.join(exit_html)}
      </ul>
      <p class="spec">spec: {html.escape(str(row['spec_reason']))}</p>
      <img loading="lazy" src="{html.escape(rel_img)}" alt="{row['review_id']} chart" />
    </section>
    """


def render_html(merged, top, image_map):
    overview_rows = build_overview_table(top)
    cards = []
    for _, row in top.iterrows():
        rel_img = os.path.relpath(image_map[row["review_id"]], REVIEW_ROOT).replace("\\", "/")
        cards.append(build_trade_card(row, rel_img))

    rel_gap = os.path.relpath(GAP_CURVE_PATH, REVIEW_ROOT).replace("\\", "/")
    rel_eq = os.path.relpath(EQUITY_COMPARE_PATH, REVIEW_ROOT).replace("\\", "/")
    best_pos = merged.loc[merged["delta_$"].idxmax()]
    best_neg = merged.loc[merged["delta_$"].idxmin()]

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>仓位档位关键交易图形复盘</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --line: #dbe4ee;
      --accent: #2563eb;
      --accent2: #7c3aed;
      --good: #15803d;
      --bad: #dc2626;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--bg);
      line-height: 1.55;
    }}
    .wrap {{
      width: min(1380px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 20px 0 40px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    .hero, .panel, .trade-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px 18px;
      margin-bottom: 16px;
    }}
    .hero p, .sub, .spec, td, li {{ color: var(--muted); }}
    .overview {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .overview .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfdff;
    }}
    .metric span, .meta-grid span, .metric-box span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }}
    .metric strong, .meta-grid strong, .metric-box strong {{
      font-size: 22px;
      font-weight: 700;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 14px;
    }}
    .chart-grid img, .trade-card img {{
      width: 100%;
      height: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      display: block;
      background: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      background: #fbfdff;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    .trade-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      min-width: 440px;
    }}
    .meta-grid > div, .metric-box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      background: #fbfdff;
    }}
    .compare-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .metric-box small {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }}
    .metric-box.peak {{
      border-color: #ddd6fe;
      background: #faf5ff;
    }}
    .exit-list {{
      margin: 0 0 10px 18px;
      padding: 0;
    }}
    .spec {{
      margin-bottom: 12px;
      font-size: 13px;
    }}
    .footnote {{
      font-size: 13px;
      color: var(--muted);
      margin-top: 10px;
    }}
    @media (max-width: 1100px) {{
      .overview, .chart-grid, .compare-grid {{
        grid-template-columns: 1fr;
      }}
      .trade-head {{
        flex-direction: column;
      }}
      .meta-grid {{
        min-width: 0;
        width: 100%;
      }}
    }}
    @media (max-width: 720px) {{
      .meta-grid {{
        grid-template-columns: 1fr 1fr;
      }}
      .overview {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>仓位档位关键交易图形复盘</h1>
      <p>对比对象：平衡推荐 `0.5/1.0/1.5` vs 收益峰值 `0.5/0.5/2.0`。这里挑出最影响两套方案差额的前 20 笔交易，直接看图，不只看表。</p>
      <div class="overview">
        <div class="metric"><span>总差额</span><strong>{money(merged['delta_$'].sum())}</strong></div>
        <div class="metric"><span>最大拉开</span><strong>{money(best_pos['delta_$'])}</strong></div>
        <div class="metric"><span>最大缩小</span><strong>{money(best_neg['delta_$'])}</strong></div>
        <div class="metric"><span>前20覆盖</span><strong>{money(top['delta_$'].sum())}</strong></div>
      </div>
      <div class="chart-grid">
        <div class="panel">
          <h3>累计差额曲线</h3>
          <p class="footnote">绿色点是正向拉开差距，红色点是反向缩小差距。</p>
          <img src="{html.escape(rel_gap)}" alt="gap curve" />
        </div>
        <div class="panel">
          <h3>资金曲线对比</h3>
          <p class="footnote">同样的交易、不同的三段仓位分配，曲线差异主要来自 Stage 3 权重。</p>
          <img src="{html.escape(rel_eq)}" alt="equity compare" />
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>前20关键交易总览</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>时间</th>
            <th>Mode</th>
            <th>方向</th>
            <th>作用</th>
            <th>单笔差额</th>
            <th>累计差额</th>
          </tr>
        </thead>
        <tbody>
          {overview_rows}
        </tbody>
      </table>
    </section>

    {''.join(cards)}
  </div>
</body>
</html>
"""
    with open(HTML_PATH, "w", encoding="utf-8-sig") as f:
        f.write(doc)


def render_md(top):
    lines = []
    lines.append("# 仓位档位关键交易图形复盘")
    lines.append("")
    lines.append("> 对比对象：`平衡推荐 0.5/1.0/1.5` vs `收益峰值 0.5/0.5/2.0`。")
    lines.append("> 本文件只做索引，详细图表请打开 HTML。")
    lines.append("")
    lines.append("## 输出文件")
    lines.append("")
    lines.append(f"- HTML：`data\\results\\position_sizing_strict_certify_20260628\\key_trade_review\\{os.path.basename(HTML_PATH)}`")
    lines.append(f"- 总览表：`data\\results\\position_sizing_strict_certify_20260628\\key_trade_review\\{os.path.basename(TOP_CSV)}`")
    lines.append(f"- 累计差额图：`data\\results\\position_sizing_strict_certify_20260628\\key_trade_review\\{os.path.basename(GAP_CURVE_PATH)}`")
    lines.append(f"- 资金曲线图：`data\\results\\position_sizing_strict_certify_20260628\\key_trade_review\\{os.path.basename(EQUITY_COMPARE_PATH)}`")
    lines.append("")
    lines.append("## 前 10 笔差额最大的交易")
    lines.append("")
    lines.append("| ID | 时间 | Mode | 方向 | 作用 | 单笔差额 | 累计差额 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for _, row in top.head(10).iterrows():
        lines.append(
            f"| {row['review_id']} | {row['date']:%Y-%m-%d %H:%M} | {row['mode']} | {zh_dir(row['dir'])} | "
            f"{row['gap_side']} | {money(row['delta_$'])} | {money(row['cum_gap_$'])} |"
        )
    lines.append("")
    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


def main():
    os.makedirs(CHART_DIR, exist_ok=True)
    price_df, merged, top = build_review_frame()
    render_gap_curve(merged, top)
    render_equity_compare(merged)

    image_map = {}
    for _, row in top.iterrows():
        image_map[row["review_id"]] = render_trade_chart(price_df, row)

    top.to_csv(TOP_CSV, index=False, encoding="utf-8-sig")
    render_html(merged, top, image_map)
    render_md(top)

    print(f"Wrote {TOP_CSV}")
    print(f"Wrote {GAP_CURVE_PATH}")
    print(f"Wrote {EQUITY_COMPARE_PATH}")
    print(f"Wrote {HTML_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()

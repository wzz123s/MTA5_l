# -*- coding: utf-8 -*-
"""Render a fast single-file HTML for full market candles and all trade markers."""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from _stop_loss_trade_report import build_stop_frame


RESULT_ROOT = os.path.join(ROOT, "data", "results", "current_strategy_20260627", "full_market_view")
HTML_PATH = os.path.join(RESULT_ROOT, "full_market_trade_view.html")


def ensure_sma55(df):
    if "SMA_55" not in df.columns:
        df = df.copy()
        df["SMA_55"] = df["close"].rolling(55, min_periods=1).mean()
    return df


def pack_bars(df):
    cols = ["date", "open", "high", "low", "close", "SMA_5", "SMA_13", "SMA_55"]
    out = []
    for row in df[cols].itertuples(index=False):
        out.append([
            int(pd.Timestamp(row.date).value // 1_000_000),
            round(float(row.open), 3),
            round(float(row.high), 3),
            round(float(row.low), 3),
            round(float(row.close), 3),
            round(float(row.SMA_5), 3),
            round(float(row.SMA_13), 3),
            round(float(row.SMA_55), 3),
        ])
    return out


def pack_events(trades):
    events = []
    for row in trades.itertuples(index=False):
        final_loss = float(row.total_points) <= 0.0

        entry_group = "entryLong" if row.dir == "L" else "entryShort"
        events.append({
            "group": entry_group,
            "idx": int(row.i),
            "t": int(pd.Timestamp(row.date).value // 1_000_000),
            "p": round(float(row.entry), 3),
            "tradeId": row.trade_id,
            "mode": row.mode,
            "dir": row.dir,
            "label": "Entry",
            "detail": f"entry {row.entry:.3f}",
            "finalLoss": final_loss,
        })

        events.append({
            "group": "initialStop",
            "idx": int(row.i),
            "t": int(pd.Timestamp(row.date).value // 1_000_000),
            "p": round(float(row.stop), 3),
            "tradeId": row.trade_id,
            "mode": row.mode,
            "dir": row.dir,
            "label": "Initial Stop",
            "detail": f"stop {row.stop:.3f}",
            "finalLoss": final_loss,
        })

        for stage_name, group, idx_col, time_col, price_col, exit_col, pnl_col in [
            ("Stage 1", "stage1Exit", "stage1_idx", "stage1_time", "stage1_price", "stage1_exit", "stage1_pnl"),
            ("Stage 2", "stage2Exit", "stage2_idx", "stage2_time", "stage2_price", "stage2_exit", "stage2_pnl"),
            ("Stage 3", "stage3Exit", "stage3_idx", "stage3_time", "stage3_price", "stage3_exit", "stage3_pnl"),
        ]:
            price = float(getattr(row, price_col))
            exit_name = str(getattr(row, exit_col))
            pnl = float(getattr(row, pnl_col))
            events.append({
                "group": group,
                "idx": int(getattr(row, idx_col)),
                "t": int(pd.Timestamp(getattr(row, time_col)).value // 1_000_000),
                "p": round(price, 3),
                "tradeId": row.trade_id,
                "mode": row.mode,
                "dir": row.dir,
                "label": stage_name,
                "detail": f"{exit_name} | {pnl:+.2f} pt",
                "finalLoss": final_loss,
            })

        for stage_name, flag_col, idx_col, time_col, price_col, exit_col, pnl_col in [
            ("Stage 1 Stop", "stage1_stop", "stage1_idx", "stage1_time", "stage1_price", "stage1_exit", "stage1_pnl"),
            ("Stage 2 Stop", "stage2_stop", "stage2_idx", "stage2_time", "stage2_price", "stage2_exit", "stage2_pnl"),
            ("Stage 3 Stop", "stage3_stop", "stage3_idx", "stage3_time", "stage3_price", "stage3_exit", "stage3_pnl"),
        ]:
            if not bool(getattr(row, flag_col)):
                continue
            price = float(getattr(row, price_col))
            exit_name = str(getattr(row, exit_col))
            pnl = float(getattr(row, pnl_col))
            events.append({
                "group": "stopHit",
                "idx": int(getattr(row, idx_col)),
                "t": int(pd.Timestamp(getattr(row, time_col)).value // 1_000_000),
                "p": round(price, 3),
                "tradeId": row.trade_id,
                "mode": row.mode,
                "dir": row.dir,
                "label": stage_name,
                "detail": f"{exit_name} | {pnl:+.2f} pt",
                "finalLoss": final_loss,
            })
    return events


def pack_trades(trades):
    out = []
    for _, row in trades.iterrows():
        item = {
            "tradeId": row["trade_id"],
            "date": int(pd.Timestamp(row["date"]).value // 1_000_000),
            "mode": row["mode"],
            "dir": row["dir"],
            "entryIdx": int(row["i"]),
            "entryPrice": round(float(row["entry"]), 3),
            "stopPrice": round(float(row["stop"]), 3),
            "sd": round(float(row["sd"]), 3),
            "patternLabel": str(row["pattern_label"]),
            "totalPoints": round(float(row["total_points"]), 3),
            "totalDollar": round(float(row["total_$"]), 3),
            "finalLoss": float(row["total_points"]) <= 0.0,
            "stages": [
                {
                    "key": "stage1",
                    "label": "第一次减仓",
                    "idx": int(row["stage1_idx"]),
                    "time": int(pd.Timestamp(row["stage1_time"]).value // 1_000_000),
                    "price": round(float(row["stage1_price"]), 3),
                    "exit": str(row["stage1_exit"]),
                    "pnl": round(float(row["stage1_pnl"]), 3),
                    "stop": bool(row["stage1_stop"]),
                },
                {
                    "key": "stage2",
                    "label": "第二次减仓",
                    "idx": int(row["stage2_idx"]),
                    "time": int(pd.Timestamp(row["stage2_time"]).value // 1_000_000),
                    "price": round(float(row["stage2_price"]), 3),
                    "exit": str(row["stage2_exit"]),
                    "pnl": round(float(row["stage2_pnl"]), 3),
                    "stop": bool(row["stage2_stop"]),
                },
                {
                    "key": "stage3",
                    "label": "最终清仓",
                    "idx": int(row["stage3_idx"]),
                    "time": int(pd.Timestamp(row["stage3_time"]).value // 1_000_000),
                    "price": round(float(row["stage3_price"]), 3),
                    "exit": str(row["stage3_exit"]),
                    "pnl": round(float(row["stage3_pnl"]), 3),
                    "stop": bool(row["stage3_stop"]),
                },
            ],
        }
        out.append(item)
    return out


def make_html(bars_json, events_json, trades_json, meta_json):
    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>全行情交互总览</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --line: #d7e0ea;
      --text: #0f172a;
      --muted: #526277;
      --accent: #2563eb;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; background: var(--bg); color: var(--text); font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
    .wrap { max-width: 1640px; margin: 0 auto; padding: 16px; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 12px;
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 24px; margin-bottom: 6px; }
    .sub { color: var(--muted); line-height: 1.5; }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .stat {
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
    }
    .stat span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
    .stat strong { font-size: 20px; }
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      align-items: center;
      margin-bottom: 10px;
    }
    .btn-row, .toggle-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button {
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--text);
      border-radius: 6px;
      padding: 6px 10px;
      cursor: pointer;
      font-size: 13px;
    }
    button:hover { border-color: #b8c6d6; background: #f8fbff; }
    label {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    input[type="checkbox"] { margin: 0; }
    .status {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
    }
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 12px;
      align-items: start;
    }
    .chart-box {
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .canvas-holder {
      position: relative;
      width: 100%;
      height: 720px;
      background: #ffffff;
    }
    .mini-holder {
      position: relative;
      width: 100%;
      height: 110px;
      border-top: 1px solid var(--line);
      background: #fbfdff;
    }
    canvas {
      display: block;
      width: 100%;
      height: 100%;
    }
    .side {
      display: grid;
      gap: 12px;
    }
    .info-box {
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .info-box h3 {
      font-size: 16px;
      margin-bottom: 8px;
    }
    .info-box pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12px;
      line-height: 1.45;
      color: #172033;
    }
    .legend-note {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    @media (max-width: 1180px) {
      .info-grid { grid-template-columns: 1fr; }
      .canvas-holder { height: 620px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>全行情交互总览</h1>
      <p class="sub" id="summaryText"></p>
      <div class="stats">
        <div class="stat"><span>M30 Bars</span><strong id="statBars"></strong></div>
        <div class="stat"><span>Total Trades</span><strong id="statTrades"></strong></div>
        <div class="stat"><span>Stop Trades</span><strong id="statStops"></strong></div>
        <div class="stat"><span>Final Loss Trades</span><strong id="statLoss"></strong></div>
      </div>
    </section>

    <section class="panel">
      <div class="controls">
        <div class="btn-row">
          <button data-range="1440">1M</button>
          <button data-range="4320">3M</button>
          <button data-range="8640">6M</button>
          <button data-range="17520">1Y</button>
          <button data-range="52560">3Y</button>
          <button id="btnAll">All</button>
          <button id="btnReset">Reset</button>
          <button id="btnClearSelected">Clear Selected</button>
        </div>
        <div class="toggle-row">
          <label><input type="checkbox" id="tgSma5" checked />SMA 5</label>
          <label><input type="checkbox" id="tgSma13" checked />SMA 13</label>
          <label><input type="checkbox" id="tgSma55" checked />SMA 55</label>
          <label><input type="checkbox" id="tgEntryLong" checked />Long Open</label>
          <label><input type="checkbox" id="tgEntryShort" checked />Short Open</label>
          <label><input type="checkbox" id="tgInitialStop" checked />Initial Stop</label>
          <label><input type="checkbox" id="tgStage1" checked />Reduce 1</label>
          <label><input type="checkbox" id="tgStage2" checked />Reduce 2</label>
          <label><input type="checkbox" id="tgStage3" checked />Final Close</label>
          <label><input type="checkbox" id="tgStopHit" checked />Stop Hit</label>
          <label><input type="checkbox" id="tgOnlyLoss" />Only Final Loss Trades</label>
        </div>
      </div>
      <div class="status">
        <div id="rangeText"></div>
        <div id="perfText"></div>
      </div>
      <div class="info-grid">
        <div class="chart-box">
          <div class="canvas-holder"><canvas id="mainCanvas"></canvas></div>
          <div class="mini-holder"><canvas id="miniCanvas"></canvas></div>
        </div>
        <div class="side">
          <section class="info-box">
            <h3>当前指针</h3>
            <pre id="hoverInfo">把鼠标放到K线上，或放大到局部看单根结构。</pre>
          </section>
          <section class="info-box">
            <h3>选中交易</h3>
            <pre id="selectedInfo">点击某个交易标记后，这里会显示这笔交易的完整生命周期：开仓、减仓、清仓、止损。</pre>
          </section>
          <section class="info-box">
            <h3>说明</h3>
            <div class="legend-note">
              这版为了减少卡顿，不再一次性交给通用图表库去渲染 97,627 根 K 线，而是改成浏览器 canvas 分层绘制。<br><br>
              全量数据都在 HTML 里。缩小时按可见区间做像素级聚合，避免密集重叠；放大后会恢复到更接近单根 K 线的展示。<br><br>
              操作方式：滚轮缩放，拖拽平移，双击重置；底部概览条可以点击跳转，也可以拖动当前窗口。<br><br>
              现在交易动作语义固定为：Long/Short Open = 开仓；Reduce 1 / Reduce 2 = 两次减仓；Final Close = 最终清仓；Stop Hit = 实际止损触发点。
            </div>
          </section>
        </div>
      </div>
    </section>
  </div>

  <script>
    const bars = __BARS_JSON__;
    const events = __EVENTS_JSON__;
    const trades = __TRADES_JSON__;
    const meta = __META_JSON__;

    const mainCanvas = document.getElementById('mainCanvas');
    const miniCanvas = document.getElementById('miniCanvas');
    const hoverInfo = document.getElementById('hoverInfo');
    const selectedInfo = document.getElementById('selectedInfo');
    const rangeText = document.getElementById('rangeText');
    const perfText = document.getElementById('perfText');
    const tradeMap = Object.fromEntries(trades.map(t => [t.tradeId, t]));

    const state = {
      start: Math.max(0, bars.length - 2400),
      end: bars.length - 1,
      draggingMain: false,
      mainMoved: false,
      draggingMini: false,
      miniMode: 'jump',
      dragStartX: 0,
      dragStartRange: [0, 0],
      hover: null,
      renderQueued: false,
      selectedTradeId: null
    };

    const toggles = {
      sma5: document.getElementById('tgSma5'),
      sma13: document.getElementById('tgSma13'),
      sma55: document.getElementById('tgSma55'),
      entryLong: document.getElementById('tgEntryLong'),
      entryShort: document.getElementById('tgEntryShort'),
      initialStop: document.getElementById('tgInitialStop'),
      stage1Exit: document.getElementById('tgStage1'),
      stage2Exit: document.getElementById('tgStage2'),
      stage3Exit: document.getElementById('tgStage3'),
      stopHit: document.getElementById('tgStopHit'),
      onlyLoss: document.getElementById('tgOnlyLoss')
    };

    const GROUP_STYLE = {
      entryLong:  { color: '#166534', shape: 'triangleUp' },
      entryShort: { color: '#991b1b', shape: 'triangleDown' },
      initialStop:{ color: '#7c3aed', shape: 'x' },
      stage1Exit: { color: '#d97706', shape: 'circle' },
      stage2Exit: { color: '#0891b2', shape: 'square' },
      stage3Exit: { color: '#1d4ed8', shape: 'diamond' },
      stopHit:    { color: '#b91c1c', shape: 'xBold' }
    };

    const EVENT_NAME = {
      entryLong: '多单开仓',
      entryShort: '空单开仓',
      initialStop: '初始止损',
      stage1Exit: '第一次减仓',
      stage2Exit: '第二次减仓',
      stage3Exit: '最终清仓',
      stopHit: '止损触发'
    };

    function dirName(dir) {
      return dir === 'L' ? '多单' : '空单';
    }

    function formatSigned(v) {
      return (v >= 0 ? '+' : '') + Number(v).toFixed(2);
    }

    function updateSelectedInfo() {
      if (!state.selectedTradeId || !tradeMap[state.selectedTradeId]) {
        selectedInfo.textContent = '点击某个交易标记后，这里会显示这笔交易的完整生命周期：开仓、减仓、清仓、止损。';
        return;
      }
      const tr = tradeMap[state.selectedTradeId];
      const lines = [];
      lines.push(`${tr.tradeId} | ${dirName(tr.dir)} | ${tr.mode}`);
      lines.push(`${formatDate(tr.date, true)}`);
      lines.push(`开仓 ${tr.entryPrice.toFixed(3)} | 初始止损 ${tr.stopPrice.toFixed(3)} | SD ${tr.sd.toFixed(3)}`);
      lines.push(`总结果 ${formatSigned(tr.totalPoints)} pt | ${tr.finalLoss ? '最终亏损' : '最终盈利'} | ${tr.patternLabel}`);
      lines.push('');
      lines.push(`1. ${dirName(tr.dir)}开仓  @ ${tr.entryPrice.toFixed(3)}  (${formatDate(tr.date, true)})`);
      tr.stages.forEach((st, idx) => {
        const stopTag = st.stop ? ' | 止损触发' : '';
        lines.push(`${idx + 2}. ${st.label}  @ ${st.price.toFixed(3)}  (${formatDate(st.time, true)})`);
        lines.push(`   ${st.exit} | ${formatSigned(st.pnl)} pt${stopTag}`);
      });
      selectedInfo.textContent = lines.join('\n');
    }

    function setupSummary() {
      document.getElementById('summaryText').textContent =
        `当前主线共 ${meta.totalTrades} 笔交易，其中 ${meta.stopTrades} 笔在某一阶段触发过止损，` +
        `${meta.finalLossTrades} 笔整单最终亏损。当前文件为单页 HTML，自带全量 M30 K 线、SMA 5 / 13 / 55 和全部交易标记。点击某个交易点后，会高亮这笔交易的完整生命周期。`;
      document.getElementById('statBars').textContent = meta.totalBars.toLocaleString();
      document.getElementById('statTrades').textContent = String(meta.totalTrades);
      document.getElementById('statStops').textContent = String(meta.stopTrades);
      document.getElementById('statLoss').textContent = String(meta.finalLossTrades);
    }

    function resizeCanvas(canvas) {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      const ctx = canvas.getContext('2d');
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return ctx;
    }

    let mainCtx = null;
    let miniCtx = null;

    function formatDate(ts, detail) {
      const d = new Date(ts);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      return detail ? `${y}-${m}-${day} ${hh}:${mm}` : `${m}-${day} ${hh}:${mm}`;
    }

    function clampRange() {
      let start = Math.max(0, Math.min(state.start, bars.length - 2));
      let end = Math.max(start + 10, Math.min(state.end, bars.length - 1));
      if (end - start + 1 > bars.length) {
        start = 0;
        end = bars.length - 1;
      }
      state.start = start;
      state.end = end;
    }

    function setVisibleCount(count) {
      const width = Math.max(60, Math.min(count, bars.length));
      state.end = bars.length - 1;
      state.start = Math.max(0, state.end - width + 1);
      clampRange();
      queueRender();
    }

    function resetView() {
      state.start = Math.max(0, bars.length - 2400);
      state.end = bars.length - 1;
      state.hover = null;
      clampRange();
      queueRender();
    }

    function clearSelectedTrade() {
      state.selectedTradeId = null;
      updateSelectedInfo();
      queueRender();
    }

    function queueRender() {
      if (state.renderQueued) return;
      state.renderQueued = true;
      requestAnimationFrame(() => {
        state.renderQueued = false;
        render();
      });
    }

    function aggregateVisible(start, end, widthPx) {
      const count = end - start + 1;
      const bucket = Math.max(1, Math.ceil(count / Math.max(10, Math.floor(widthPx))));
      const out = [];
      for (let i = start; i <= end; i += bucket) {
        const j = Math.min(end, i + bucket - 1);
        let high = -Infinity;
        let low = Infinity;
        let sma5 = 0;
        let sma13 = 0;
        let sma55 = 0;
        for (let k = i; k <= j; k++) {
          const bar = bars[k];
          if (bar[2] > high) high = bar[2];
          if (bar[3] < low) low = bar[3];
          sma5 += bar[5];
          sma13 += bar[6];
          sma55 += bar[7];
        }
        out.push({
          start: i,
          end: j,
          mid: Math.round((i + j) / 2),
          t: bars[Math.round((i + j) / 2)][0],
          o: bars[i][1],
          h: high,
          l: low,
          c: bars[j][4],
          s5: sma5 / (j - i + 1),
          s13: sma13 / (j - i + 1),
          s55: sma55 / (j - i + 1)
        });
      }
      return { items: out, bucket };
    }

    function visibleEvents() {
      const onlyLoss = toggles.onlyLoss.checked;
      return events.filter(evt =>
        evt.idx >= state.start &&
        evt.idx <= state.end &&
        toggles[evt.group] &&
        toggles[evt.group].checked &&
        (!onlyLoss || evt.finalLoss)
      );
    }

    function drawMarker(ctx, x, y, style) {
      const color = style.color;
      const shape = style.shape;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = shape === 'xBold' ? 2 : 1.4;
      if (shape === 'triangleUp') {
        ctx.beginPath();
        ctx.moveTo(x, y - 6);
        ctx.lineTo(x - 5, y + 4);
        ctx.lineTo(x + 5, y + 4);
        ctx.closePath();
        ctx.fill();
      } else if (shape === 'triangleDown') {
        ctx.beginPath();
        ctx.moveTo(x, y + 6);
        ctx.lineTo(x - 5, y - 4);
        ctx.lineTo(x + 5, y - 4);
        ctx.closePath();
        ctx.fill();
      } else if (shape === 'circle') {
        ctx.beginPath();
        ctx.arc(x, y, 4.2, 0, Math.PI * 2);
        ctx.fill();
      } else if (shape === 'square') {
        ctx.fillRect(x - 4, y - 4, 8, 8);
      } else if (shape === 'diamond') {
        ctx.beginPath();
        ctx.moveTo(x, y - 5);
        ctx.lineTo(x - 5, y);
        ctx.lineTo(x, y + 5);
        ctx.lineTo(x + 5, y);
        ctx.closePath();
        ctx.fill();
      } else if (shape === 'x' || shape === 'xBold') {
        ctx.beginPath();
        ctx.moveTo(x - 5, y - 5);
        ctx.lineTo(x + 5, y + 5);
        ctx.moveTo(x + 5, y - 5);
        ctx.lineTo(x - 5, y + 5);
        ctx.stroke();
      }
      ctx.restore();
    }

    function priceFormatter(value) {
      return value >= 1000 ? value.toFixed(2) : value.toFixed(3);
    }

    function render() {
      clampRange();
      const startedAt = performance.now();
      const width = mainCanvas.clientWidth;
      const height = mainCanvas.clientHeight;
      const dims = { left: 76, right: 22, top: 18, bottom: 34 };
      const plotW = Math.max(10, width - dims.left - dims.right);
      const plotH = Math.max(10, height - dims.top - dims.bottom);

      mainCtx.clearRect(0, 0, width, height);
      mainCtx.fillStyle = '#ffffff';
      mainCtx.fillRect(0, 0, width, height);

      const agg = aggregateVisible(state.start, state.end, plotW);
      const visible = agg.items;
      const visibleCount = state.end - state.start + 1;
      const vEvents = visibleEvents();

      let minPrice = Infinity;
      let maxPrice = -Infinity;
      for (const bar of visible) {
        if (bar.l < minPrice) minPrice = bar.l;
        if (bar.h > maxPrice) maxPrice = bar.h;
        if (toggles.sma5.checked) { if (bar.s5 < minPrice) minPrice = bar.s5; if (bar.s5 > maxPrice) maxPrice = bar.s5; }
        if (toggles.sma13.checked) { if (bar.s13 < minPrice) minPrice = bar.s13; if (bar.s13 > maxPrice) maxPrice = bar.s13; }
        if (toggles.sma55.checked) { if (bar.s55 < minPrice) minPrice = bar.s55; if (bar.s55 > maxPrice) maxPrice = bar.s55; }
      }
      for (const evt of vEvents) {
        if (evt.p < minPrice) minPrice = evt.p;
        if (evt.p > maxPrice) maxPrice = evt.p;
      }
      if (!Number.isFinite(minPrice) || !Number.isFinite(maxPrice) || minPrice === maxPrice) {
        minPrice = 0;
        maxPrice = 1;
      }
      const pad = Math.max((maxPrice - minPrice) * 0.08, 1.0);
      minPrice -= pad;
      maxPrice += pad;

      const xForIdx = idx => dims.left + ((idx - state.start) / Math.max(1, visibleCount - 1)) * plotW;
      const yForPrice = price => dims.top + ((maxPrice - price) / Math.max(1e-9, maxPrice - minPrice)) * plotH;

      mainCtx.strokeStyle = '#e5edf4';
      mainCtx.lineWidth = 1;
      mainCtx.fillStyle = '#66768a';
      mainCtx.font = '12px Segoe UI';
      for (let i = 0; i <= 5; i++) {
        const y = dims.top + (plotH / 5) * i;
        mainCtx.beginPath();
        mainCtx.moveTo(dims.left, y);
        mainCtx.lineTo(width - dims.right, y);
        mainCtx.stroke();
        const price = maxPrice - ((maxPrice - minPrice) / 5) * i;
        mainCtx.fillText(priceFormatter(price), 8, y + 4);
      }

      const tickCount = 6;
      for (let i = 0; i <= tickCount; i++) {
        const idx = state.start + Math.round((visibleCount - 1) * (i / tickCount));
        const x = xForIdx(idx);
        mainCtx.beginPath();
        mainCtx.moveTo(x, dims.top);
        mainCtx.lineTo(x, dims.top + plotH);
        mainCtx.stroke();
        const label = formatDate(bars[idx][0], false);
        mainCtx.fillText(label, x - 24, height - 10);
      }

      const candleStep = plotW / Math.max(1, visible.length);
      const candleWidth = Math.max(1, Math.min(10, candleStep * 0.72));
      for (const bar of visible) {
        const x = xForIdx(bar.mid);
        const yHigh = yForPrice(bar.h);
        const yLow = yForPrice(bar.l);
        const yOpen = yForPrice(bar.o);
        const yClose = yForPrice(bar.c);
        const up = bar.c >= bar.o;
        const color = up ? '#16a34a' : '#dc2626';
        mainCtx.strokeStyle = color;
        mainCtx.fillStyle = color;
        mainCtx.beginPath();
        mainCtx.moveTo(x, yHigh);
        mainCtx.lineTo(x, yLow);
        mainCtx.stroke();
        const top = Math.min(yOpen, yClose);
        const body = Math.max(1, Math.abs(yClose - yOpen));
        mainCtx.fillRect(x - candleWidth / 2, top, candleWidth, body);
      }

      function drawLine(accessor, color, enabled) {
        if (!enabled) return;
        mainCtx.beginPath();
        mainCtx.strokeStyle = color;
        mainCtx.lineWidth = 1.5;
        let started = false;
        for (const bar of visible) {
          const x = xForIdx(bar.mid);
          const y = yForPrice(accessor(bar));
          if (!started) {
            mainCtx.moveTo(x, y);
            started = true;
          } else {
            mainCtx.lineTo(x, y);
          }
        }
        mainCtx.stroke();
      }

      drawLine(bar => bar.s5, '#f59e0b', toggles.sma5.checked);
      drawLine(bar => bar.s13, '#2563eb', toggles.sma13.checked);
      drawLine(bar => bar.s55, '#64748b', toggles.sma55.checked);

      const markerPositions = [];
      for (const evt of vEvents) {
        const style = GROUP_STYLE[evt.group];
        const x = xForIdx(evt.idx);
        const y = yForPrice(evt.p);
        drawMarker(mainCtx, x, y, style);
        markerPositions.push({ x, y, evt });
      }

      drawSelectedTrade(mainCtx, xForIdx, yForPrice, dims, plotW, plotH);

      if (state.hover) {
        mainCtx.save();
        mainCtx.strokeStyle = 'rgba(37,99,235,0.35)';
        mainCtx.lineWidth = 1;
        mainCtx.setLineDash([5, 5]);
        if (state.hover.x != null) {
          mainCtx.beginPath();
          mainCtx.moveTo(state.hover.x, dims.top);
          mainCtx.lineTo(state.hover.x, dims.top + plotH);
          mainCtx.stroke();
        }
        if (state.hover.y != null) {
          mainCtx.beginPath();
          mainCtx.moveTo(dims.left, state.hover.y);
          mainCtx.lineTo(dims.left + plotW, state.hover.y);
          mainCtx.stroke();
        }
        mainCtx.restore();
      }

      renderMiniMap();

      const startBar = bars[state.start];
      const endBar = bars[state.end];
      rangeText.textContent =
        `范围: ${formatDate(startBar[0], true)} -> ${formatDate(endBar[0], true)} | ` +
        `${visibleCount.toLocaleString()} bars | 渲染桶宽 ${agg.bucket}`;
      perfText.textContent =
        `marker ${vEvents.length} | render ${(performance.now() - startedAt).toFixed(1)} ms`;

      mainCanvas.__dims = dims;
      mainCanvas.__plotW = plotW;
      mainCanvas.__plotH = plotH;
      mainCanvas.__markerPositions = markerPositions;
      mainCanvas.__xForIdx = xForIdx;
      mainCanvas.__yForPrice = yForPrice;
    }

    function drawSelectedTrade(ctx, xForIdx, yForPrice, dims, plotW, plotH) {
      if (!state.selectedTradeId || !tradeMap[state.selectedTradeId]) return;
      const tr = tradeMap[state.selectedTradeId];
      const points = [
        { idx: tr.entryIdx, price: tr.entryPrice, text: tr.dir === 'L' ? '多开' : '空开', color: tr.dir === 'L' ? '#166534' : '#991b1b', shape: tr.dir === 'L' ? 'triangleUp' : 'triangleDown' },
        { idx: tr.stages[0].idx, price: tr.stages[0].price, text: tr.stages[0].stop ? '减仓1/止损' : '减仓1', color: '#d97706', shape: 'circle' },
        { idx: tr.stages[1].idx, price: tr.stages[1].price, text: tr.stages[1].stop ? '减仓2/止损' : '减仓2', color: '#0891b2', shape: 'square' },
        { idx: tr.stages[2].idx, price: tr.stages[2].price, text: tr.stages[2].stop ? '清仓/止损' : '清仓', color: '#1d4ed8', shape: 'diamond' },
      ];

      ctx.save();
      ctx.beginPath();
      ctx.rect(dims.left, dims.top, plotW, plotH);
      ctx.clip();
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(15,23,42,0.5)';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      points.forEach((pt, idx) => {
        const x = xForIdx(pt.idx);
        const y = yForPrice(pt.price);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);

      points.forEach(pt => {
        const x = xForIdx(pt.idx);
        const y = yForPrice(pt.price);
        drawMarker(ctx, x, y, { color: pt.color, shape: pt.shape });
        if (x < dims.left - 40 || x > dims.left + plotW + 40 || y < dims.top - 20 || y > dims.top + plotH + 20) return;
        const labelW = ctx.measureText(pt.text).width + 12;
        const boxX = Math.max(dims.left + 2, Math.min(x + 8, dims.left + plotW - labelW - 2));
        const boxY = Math.max(dims.top + 2, Math.min(y - 20, dims.top + plotH - 18));
        ctx.fillStyle = 'rgba(255,255,255,0.92)';
        ctx.strokeStyle = pt.color;
        ctx.lineWidth = 1;
        ctx.fillRect(boxX, boxY, labelW, 18);
        ctx.strokeRect(boxX, boxY, labelW, 18);
        ctx.fillStyle = pt.color;
        ctx.font = '12px Segoe UI';
        ctx.fillText(pt.text, boxX + 6, boxY + 13);
      });
      ctx.restore();
    }

    function renderMiniMap() {
      const width = miniCanvas.clientWidth;
      const height = miniCanvas.clientHeight;
      miniCtx.clearRect(0, 0, width, height);
      miniCtx.fillStyle = '#fbfdff';
      miniCtx.fillRect(0, 0, width, height);

      const dims = { left: 12, right: 12, top: 10, bottom: 14 };
      const plotW = Math.max(10, width - dims.left - dims.right);
      const plotH = Math.max(10, height - dims.top - dims.bottom);

      const sample = aggregateVisible(0, bars.length - 1, plotW).items;
      let min = Infinity;
      let max = -Infinity;
      for (const bar of sample) {
        if (bar.l < min) min = bar.l;
        if (bar.h > max) max = bar.h;
      }
      const yFor = price => dims.top + ((max - price) / Math.max(1e-9, max - min)) * plotH;

      miniCtx.beginPath();
      miniCtx.strokeStyle = '#8aa1b8';
      miniCtx.lineWidth = 1;
      let started = false;
      for (let i = 0; i < sample.length; i++) {
        const x = dims.left + (i / Math.max(1, sample.length - 1)) * plotW;
        const y = yFor(sample[i].c);
        if (!started) {
          miniCtx.moveTo(x, y);
          started = true;
        } else {
          miniCtx.lineTo(x, y);
        }
      }
      miniCtx.stroke();

      const selLeft = dims.left + (state.start / Math.max(1, bars.length - 1)) * plotW;
      const selRight = dims.left + (state.end / Math.max(1, bars.length - 1)) * plotW;
      miniCtx.fillStyle = 'rgba(37,99,235,0.12)';
      miniCtx.fillRect(selLeft, dims.top, Math.max(1, selRight - selLeft), plotH);
      miniCtx.strokeStyle = '#2563eb';
      miniCtx.lineWidth = 1.5;
      miniCtx.strokeRect(selLeft, dims.top, Math.max(1, selRight - selLeft), plotH);

      miniCanvas.__dims = dims;
      miniCanvas.__plotW = plotW;
      miniCanvas.__plotH = plotH;
    }

    function pointerPos(evt, canvas) {
      const rect = canvas.getBoundingClientRect();
      return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
    }

    function handleHover(evt) {
      const pos = pointerPos(evt, mainCanvas);
      const dims = mainCanvas.__dims;
      if (!dims) return;
      if (pos.x < dims.left || pos.x > dims.left + mainCanvas.__plotW || pos.y < dims.top || pos.y > dims.top + mainCanvas.__plotH) {
        state.hover = null;
        hoverInfo.textContent = '把鼠标放到K线上，或放大到局部看单根结构。';
        queueRender();
        return;
      }

      const markers = mainCanvas.__markerPositions || [];
      let best = null;
      for (const mk of markers) {
        const dx = mk.x - pos.x;
        const dy = mk.y - pos.y;
        const d2 = dx * dx + dy * dy;
        if (d2 <= 81 && (!best || d2 < best.d2)) best = { d2, mk };
      }
      if (best) {
        const evtInfo = best.mk.evt;
        state.hover = { x: best.mk.x, y: best.mk.y };
        hoverInfo.textContent =
          `${evtInfo.tradeId} | ${EVENT_NAME[evtInfo.group] || evtInfo.label}\n` +
          `${formatDate(evtInfo.t, true)}\n` +
          `${evtInfo.mode} | ${dirName(evtInfo.dir)}\n` +
          `${evtInfo.detail}\n` +
          `price ${evtInfo.p.toFixed(3)}\n` +
          `final ${evtInfo.finalLoss ? '亏损' : '盈利'}`;
        queueRender();
        return;
      }

      const ratio = (pos.x - dims.left) / Math.max(1, mainCanvas.__plotW);
      const idx = Math.max(state.start, Math.min(state.end, Math.round(state.start + ratio * (state.end - state.start))));
      const bar = bars[idx];
      state.hover = { x: mainCanvas.__xForIdx(idx), y: null };
      hoverInfo.textContent =
        `${formatDate(bar[0], true)}\n` +
        `O ${bar[1].toFixed(3)}  H ${bar[2].toFixed(3)}\n` +
        `L ${bar[3].toFixed(3)}  C ${bar[4].toFixed(3)}\n` +
        `SMA5 ${bar[5].toFixed(3)}\n` +
        `SMA13 ${bar[6].toFixed(3)}\n` +
        `SMA55 ${bar[7].toFixed(3)}`;
      queueRender();
    }

    mainCanvas.addEventListener('wheel', evt => {
      evt.preventDefault();
      const dims = mainCanvas.__dims;
      if (!dims) return;
      const pos = pointerPos(evt, mainCanvas);
      const ratio = Math.max(0, Math.min(1, (pos.x - dims.left) / Math.max(1, mainCanvas.__plotW)));
      const visible = state.end - state.start + 1;
      const zoom = evt.deltaY < 0 ? 0.82 : 1.22;
      const nextVisible = Math.max(40, Math.min(bars.length, Math.round(visible * zoom)));
      const center = state.start + ratio * visible;
      state.start = Math.round(center - ratio * nextVisible);
      state.end = state.start + nextVisible - 1;
      clampRange();
      queueRender();
    }, { passive: false });

    mainCanvas.addEventListener('mousedown', evt => {
      state.draggingMain = true;
      state.mainMoved = false;
      state.dragStartX = evt.clientX;
      state.dragStartRange = [state.start, state.end];
    });

    window.addEventListener('mousemove', evt => {
      if (state.draggingMain) {
        const dims = mainCanvas.__dims;
        if (!dims) return;
        const dx = evt.clientX - state.dragStartX;
        if (Math.abs(dx) > 3) state.mainMoved = true;
        const visible = state.dragStartRange[1] - state.dragStartRange[0] + 1;
        const shift = Math.round(-(dx / Math.max(1, mainCanvas.__plotW)) * visible);
        state.start = state.dragStartRange[0] + shift;
        state.end = state.dragStartRange[1] + shift;
        clampRange();
        queueRender();
      } else if (state.draggingMini) {
        const rect = miniCanvas.getBoundingClientRect();
        const x = Math.max(0, Math.min(rect.width, evt.clientX - rect.left));
        const visible = state.dragStartRange[1] - state.dragStartRange[0] + 1;
        if (state.miniMode === 'pan') {
          const dx = evt.clientX - state.dragStartX;
          const shift = Math.round((dx / Math.max(1, rect.width)) * bars.length);
          state.start = state.dragStartRange[0] + shift;
          state.end = state.start + visible - 1;
        } else {
          const center = Math.round((x / Math.max(1, rect.width)) * (bars.length - 1));
          state.start = center - Math.round(visible / 2);
          state.end = state.start + visible - 1;
        }
        clampRange();
        queueRender();
      } else {
        handleHover(evt);
      }
    });

    window.addEventListener('mouseup', () => {
      state.draggingMain = false;
      state.draggingMini = false;
    });

    mainCanvas.addEventListener('click', evt => {
      if (state.mainMoved) return;
      const pos = pointerPos(evt, mainCanvas);
      const markers = mainCanvas.__markerPositions || [];
      let best = null;
      for (const mk of markers) {
        const dx = mk.x - pos.x;
        const dy = mk.y - pos.y;
        const d2 = dx * dx + dy * dy;
        if (d2 <= 196 && (!best || d2 < best.d2)) best = { d2, mk };
      }
      if (best) {
        state.selectedTradeId = best.mk.evt.tradeId;
        updateSelectedInfo();
        queueRender();
      }
    });

    mainCanvas.addEventListener('dblclick', evt => {
      evt.preventDefault();
      resetView();
    });

    miniCanvas.addEventListener('mousedown', evt => {
      const rect = miniCanvas.getBoundingClientRect();
      const x = evt.clientX - rect.left;
      const dims = miniCanvas.__dims;
      if (!dims) return;
      const plotLeft = dims.left + (state.start / Math.max(1, bars.length - 1)) * miniCanvas.__plotW;
      const plotRight = dims.left + (state.end / Math.max(1, bars.length - 1)) * miniCanvas.__plotW;
      state.draggingMini = true;
      state.dragStartX = evt.clientX;
      state.dragStartRange = [state.start, state.end];
      state.miniMode = (x >= plotLeft && x <= plotRight) ? 'pan' : 'jump';
    });

    miniCanvas.addEventListener('click', evt => {
      if (state.draggingMini) return;
      const rect = miniCanvas.getBoundingClientRect();
      const x = evt.clientX - rect.left;
      const visible = state.end - state.start + 1;
      const center = Math.round((x / Math.max(1, rect.width)) * (bars.length - 1));
      state.start = center - Math.round(visible / 2);
      state.end = state.start + visible - 1;
      clampRange();
      queueRender();
    });

    document.querySelectorAll('[data-range]').forEach(btn => {
      btn.addEventListener('click', () => setVisibleCount(parseInt(btn.dataset.range, 10)));
    });
    document.getElementById('btnAll').addEventListener('click', () => {
      state.start = 0;
      state.end = bars.length - 1;
      queueRender();
    });
    document.getElementById('btnReset').addEventListener('click', () => resetView());
    document.getElementById('btnClearSelected').addEventListener('click', () => clearSelectedTrade());
    Object.values(toggles).forEach(el => el.addEventListener('change', () => queueRender()));

    function init() {
      setupSummary();
      updateSelectedInfo();
      mainCtx = resizeCanvas(mainCanvas);
      miniCtx = resizeCanvas(miniCanvas);
      queueRender();
    }

    window.addEventListener('resize', () => {
      mainCtx = resizeCanvas(mainCanvas);
      miniCtx = resizeCanvas(miniCanvas);
      queueRender();
    });

    init();
  </script>
</body>
</html>
"""
    return (
        template
        .replace("__BARS_JSON__", bars_json)
        .replace("__EVENTS_JSON__", events_json)
        .replace("__TRADES_JSON__", trades_json)
        .replace("__META_JSON__", meta_json)
    )


def main():
    os.makedirs(RESULT_ROOT, exist_ok=True)
    df, all_trades, stop_trades = build_stop_frame()
    df = ensure_sma55(df)
    df["date"] = pd.to_datetime(df["date"])

    all_trades = all_trades.copy().sort_values("date").reset_index(drop=True)
    if "trade_id" not in all_trades.columns:
        all_trades["trade_id"] = [f"A{idx + 1:02d}" for idx in range(len(all_trades))]

    bars = pack_bars(df)
    events = pack_events(all_trades)
    trades = pack_trades(all_trades)
    meta = {
        "totalBars": len(df),
        "totalTrades": len(all_trades),
        "stopTrades": len(stop_trades),
        "finalLossTrades": int((all_trades["total_points"] <= 0).sum()),
    }

    html_text = make_html(
        json.dumps(bars, ensure_ascii=False, separators=(",", ":")),
        json.dumps(events, ensure_ascii=False, separators=(",", ":")),
        json.dumps(trades, ensure_ascii=False, separators=(",", ":")),
        json.dumps(meta, ensure_ascii=False, separators=(",", ":")),
    )
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_text)

    print(f"Bars: {len(df)}")
    print(f"Trades: {len(all_trades)}")
    print(f"Stop trades: {len(stop_trades)}")
    print(f"Wrote {HTML_PATH}")


if __name__ == "__main__":
    main()

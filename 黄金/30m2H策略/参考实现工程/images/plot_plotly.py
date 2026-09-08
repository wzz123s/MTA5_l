# -*- coding: utf-8 -*-
"""
plot_plotly.py
交互式 HTML 图表 — 用 plotly 实现：可在浏览器缩放/十字光标/图例切换。
输出:
  - chart_full.html
  - chart_zoom.html
"""
import sys
import io
# 注意: 不在模块顶部重写 sys.stdout,避免 plot_prepare 已经重写后再次重写导致 closed
# (Windows GBK -> UTF-8 重写在 plot_prepare.py 中已经做)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# 颜色 (与 mplfinance 版本一致)
UP_COLOR = '#26A69A'
DOWN_COLOR = '#EF5350'
SMA5_COLOR = '#1E88E5'
SMA13_COLOR = '#FFC107'
UP_BAND = 'rgba(165, 214, 167, 0.18)'
DOWN_BAND = 'rgba(239, 154, 154, 0.18)'
GOOD_COLOR = '#00C853'
BAD_COLOR = '#D50000'


def _add_segment_bands(fig, df, seg_starts, seg_ends, seg_type, row=1, col=1, yref='y'):
    """按段添加背景矩形 (plotly add_shape)。row/col 必须同时给。"""
    for s, e, t in zip(seg_starts, seg_ends, seg_type):
        x0 = df.index[s]
        x1 = df.index[e]
        if pd.isna(x0) or pd.isna(x1):
            continue
        color = UP_BAND if t == 'up' else DOWN_BAND
        fig.add_shape(
            type='rect', xref=f'x{row if row > 1 else ""}',
            yref=f'y{row if row > 1 else ""}' if row > 1 else yref,
            x0=x0, x1=x1, y0=0, y1=1,
            fillcolor=color, line=dict(width=0), layer='below',
            row=row, col=col,
        )


def _build_figure(df, meta, title):
    """构建 plotly 交互图。"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.62, 0.20, 0.18],
        subplot_titles=(title, '段内强度比值 (way_s/way, vol_way/way)', '成交量 + vol_MA_120 (北京时间)'),
    )

    # ---------- Row 1: 主图 ----------
    # X 轴是整数索引 (消除非交易时段留白),hover 时显示真实北京时间
    # 用 hovertext 数组逐根写 (兼容老 plotly 5.16 报 hovertemplate 非法)
    date_strs = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M')
    hover_texts = [
        f'时间: {d}<br>开: {o} 高: {h}<br>低: {l} 收: {c}'
        for d, o, h, l, c in zip(
            date_strs, df['open'], df['high'], df['low'], df['close']
        )
    ]
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color=UP_COLOR, decreasing_line_color=DOWN_COLOR,
        increasing_fillcolor=UP_COLOR, decreasing_fillcolor=DOWN_COLOR,
        name='K线', showlegend=True,
        hovertext=hover_texts, hoverinfo='text',
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['SMA_5'], mode='lines',
        line=dict(color=SMA5_COLOR, width=1.0), name='5 SMMA',
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['SMA_13'], mode='lines',
        line=dict(color=SMA13_COLOR, width=1.0), name='13 SMMA',
    ), row=1, col=1)

    # 段方向色带 (在主图上)
    _add_segment_bands(fig, df, meta['seg_starts'], meta['seg_ends'], meta['seg_type'],
                      row=1, yref='y')

    # 真实穿越点 markers
    if len(meta['real_good_pos']) > 0:
        gp = meta['real_good_pos']
        fig.add_trace(go.Scatter(
            x=df.index[gp], y=df['low'].iloc[gp] * 0.997,
            mode='markers', name='真实 good (上穿)',
            marker=dict(symbol='triangle-up', size=10, color=GOOD_COLOR,
                        line=dict(color='black', width=0.5)),
        ), row=1, col=1)

    if len(meta['real_bad_pos']) > 0:
        bp = meta['real_bad_pos']
        fig.add_trace(go.Scatter(
            x=df.index[bp], y=df['high'].iloc[bp] * 1.003,
            mode='markers', name='真实 bad (下穿)',
            marker=dict(symbol='triangle-down', size=10, color=BAD_COLOR,
                        line=dict(color='black', width=0.5)),
        ), row=1, col=1)

    # 段色带图例
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(size=15, color='rgba(165, 214, 167, 0.5)', symbol='square'),
        name='up 段 (绿带)',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(size=15, color='rgba(239, 154, 154, 0.5)', symbol='square'),
        name='down 段 (红带)',
    ), row=1, col=1)

    # ---------- Row 2: 强度比值 ----------
    fig.add_trace(go.Scatter(
        x=df.index, y=df['way_s_way'], mode='lines',
        line=dict(color='#1B5E20', width=0.9), name='way_s / way',
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['vol_way_s_way'], mode='lines',
        line=dict(color='#6A1B9A', width=0.9), name='vol_way / way',
    ), row=2, col=1)

    # 强度副图也加段色带
    _add_segment_bands(fig, df, meta['seg_starts'], meta['seg_ends'], meta['seg_type'],
                      row=2, yref='y2')

    # ---------- Row 3: 成交量 ----------
    vol_colors = [UP_COLOR if df['close'].iloc[i] >= df['open'].iloc[i] else DOWN_COLOR
                  for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index, y=df['volume'], name='成交量',
        marker_color=vol_colors, showlegend=False,
    ), row=3, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['vol_ma_120'], mode='lines',
        line=dict(color='#FF6F00', width=0.8), name='vol_MA_120',
    ), row=3, col=1)

    # ---------- 布局 ----------
    fig.update_layout(
        title=dict(
            text=f'XAUUSDm 4H (北京时间) 段分析交互图 — 段数={meta["n_seg"]}, '
                 f'真实 good={meta["n_real_good"]}, 真实 bad={meta["n_real_bad"]}',
            x=0.5, xanchor='center',
        ),
        xaxis_rangeslider_visible=False,  # 关闭 rangeslider
        hovermode='x unified',
        height=900, width=1600,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        template='plotly_white',
    )
    fig.update_yaxes(title_text='价格', row=1, col=1)
    fig.update_yaxes(title_text='比值', range=[-1.1, 1.1], row=2, col=1)
    fig.update_yaxes(title_text='成交量', row=3, col=1)
    fig.update_xaxes(rangeslider=dict(visible=False), row=1, col=1)

    return fig


def plot_full_html(df, meta, out_path):
    print(f"  绘制 plotly 全图: {out_path}")
    fig = _build_figure(df, meta, 'XAUUSDm 4H (北京时间) — 段分析全景 (全 9 年)')
    fig.write_html(out_path, include_plotlyjs='cdn', config={'scrollZoom': True})
    print(f"    ✓ {out_path} 已保存")


def plot_zoom_html(df, meta, out_path, n_tail=200):
    df_z = df.iloc[-n_tail:].copy()
    offset = len(df) - n_tail
    seg_starts_z, seg_ends_z, seg_type_z = [], [], []
    for s, e, t in zip(meta['seg_starts'], meta['seg_ends'], meta['seg_type']):
        if e < offset or s >= len(df):
            continue
        s_z, e_z = max(0, s - offset), min(n_tail - 1, e - offset)
        if e_z < s_z:
            continue
        seg_starts_z.append(s_z)
        seg_ends_z.append(e_z)
        seg_type_z.append(t)
    real_good_z = meta['real_good_pos'][meta['real_good_pos'] >= offset] - offset
    real_bad_z = meta['real_bad_pos'][meta['real_bad_pos'] >= offset] - offset

    meta_z = {
        'seg_starts': np.array(seg_starts_z),
        'seg_ends': np.array(seg_ends_z),
        'seg_type': np.array(seg_type_z),
        'n_seg': len(seg_starts_z),
        'n_real_good': len(real_good_z),
        'n_real_bad': len(real_bad_z),
        'real_good_pos': real_good_z,
        'real_bad_pos': real_bad_z,
    }
    print(f"  绘制 plotly 放大图: {out_path}")
    fig = _build_figure(df_z, meta_z, f'XAUUSDm 4H (北京时间) — 段分析 (末尾 {n_tail} 根 ≈ {n_tail // 6} 天)')
    fig.write_html(out_path, include_plotlyjs='cdn', config={'scrollZoom': True})
    print(f"    ✓ {out_path} 已保存")


if __name__ == '__main__':
    from plot_prepare import prepare
    df, meta = prepare('F:/use_code/MTA5/data/原始行情/XAUUSDm16388.csv')
    plot_full_html(df, meta, 'F:/use_code/MTA5/chart_full.html')
    plot_zoom_html(df, meta, 'F:/use_code/MTA5/chart_zoom.html', n_tail=200)
    print("✓ plotly 完成")

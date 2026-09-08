# -*- coding: utf-8 -*-
"""
plot_mplfinance.py
静态 PNG 图表 — K线 + 5/13 SMMA + 段方向色带 + 真实穿越点 markers + 强度副图 + 成交量副图

X 轴策略: 假 DatetimeIndex 中转 (消除非交易时段留白)
  - df 是 RangeIndex (整数 0..N-1) — 来自 plot_prepare.reset_index(drop=True)
  - 喂给 mplfinance 之前用 pd.date_range('2000-01-01', periods=N, freq='4h') 替换 index
  - mplfinance 内部轴用假日期;主图/成交量副图的叠加层(段色带、markers、vol_ma)也用假日期
  - X 轴刻度用 FuncFormatter 反向映射为整数 0..N-1
  - show_nontrading=False (假日期本就连续无 gap,留它无意义)
"""
import sys
import io
# UTF-8 输出在 plot_prepare.py 中已处理,这里不再重写避免 closed
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Rectangle
from matplotlib import rcParams

# 中文字体设置 (避免 savefig 时的 CJK 警告)
try:
    rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    rcParams['axes.unicode_minus'] = False
except Exception:
    pass

# 自定义 K线颜色
UP_COLOR = '#26A69A'   # 上涨绿
DOWN_COLOR = '#EF5350' # 下跌红
SMA5_COLOR = '#1E88E5' # 5 SMMA 蓝
SMA13_COLOR = '#FFC107' # 13 SMMA 黄
UP_BAND = '#A5D6A7'    # 段方向色带: up 浅绿
DOWN_BAND = '#EF9A9A'  # 段方向色带: down 浅红
GOOD_COLOR = '#00C853' # 真实穿越点: 绿
BAD_COLOR = '#D50000'  # 真实穿越点: 红

# 假日期起点: matplotlib date_num 起点;4h freq 保证 1 根 K线 = step 天
_FAKE_DATE_START = pd.Timestamp('2000-01-01')
_FAKE_STEP_DAY = 4.0 / 24.0  # 4 hours = 1/6 day


def _make_fake_index(n):
    """生成等间距的连续假 DatetimeIndex, 用于喂 mplfinance。"""
    return pd.date_range(start=_FAKE_DATE_START, periods=n, freq='4h')


def _to_int_formatter(n):
    """FuncFormatter: 假日期 (matplotlib date_num) → 整数 0..n-1。"""
    t0 = _FAKE_DATE_START.value / (24 * 3600 * 1e9)  # ns → day

    def _fmt(x, pos):
        i = int(round((x - t0) / _FAKE_STEP_DAY))
        if i < 0:
            i = 0
        elif i > n - 1:
            i = n - 1
        return str(i)

    return mticker.FuncFormatter(_fmt)


def _build_segment_overlay(df, ax, seg_starts, seg_ends, seg_type, x_index=None):
    """在 ax 上画段方向色带 (v2 合并后)。

    x_index: 用于 axvspan 的 x 序列。None → 默认 df.index (整数)；
             主图/成交量副图上必须传 df_for_mpf.index (假 DatetimeIndex) 以与
             mplfinance 内部轴对齐。
    """
    xseq = x_index if x_index is not None else df.index
    ymin, ymax = ax.get_ylim()
    for s, e, t in zip(seg_starts, seg_ends, seg_type):
        x0 = xseq[s]
        x1 = xseq[e]
        color = UP_BAND if t == 'up' else DOWN_BAND
        # 跨越整段宽度的矩形
        ax.axvspan(x0, x1, color=color, alpha=0.18, zorder=0)


def _build_markers(df, ax, positions, marker, color, size,
                   offset_pct=0.005, x_index=None):
    """在 ax 上叠加穿越点 markers。x_index 同 _build_segment_overlay。"""
    if len(positions) == 0:
        return
    xseq = x_index if x_index is not None else df.index
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin
    for p in positions:
        x = xseq[p]
        if marker == '^':
            y = df['low'].iloc[p] - yrange * offset_pct
        else:
            y = df['high'].iloc[p] + yrange * offset_pct
        ax.scatter(x, y, marker=marker, s=size, color=color,
                   edgecolors='black', linewidths=0.5, zorder=10)


def _build_strength_subplot(df, seg_starts, seg_ends, seg_type, x_index=None):
    """构建段内信号副图: way + way_s + way_s_way + 段方向色带。

    x_index: 与 mplfinance 主图轴对齐的假日期序列 (强度副图是独立 plt.subplots,
             默认用 df.index 整数;但若需与主图共用 X 轴也支持传入 x_index)。
    """
    fig, axes = plt.subplots(2, 1, figsize=(20, 4), sharex=True,
                             gridspec_kw={'height_ratios': [1, 0.6]})
    ax1, ax2 = axes
    xseq = x_index if x_index is not None else df.index

    # 主: way 柱状 + way_s 折线
    way = df['way']
    colors_way = [UP_COLOR if v >= 0 else DOWN_COLOR for v in way]
    ax1.bar(xseq, way, color=colors_way, alpha=0.6, width=_FAKE_STEP_DAY, label='way')
    ax1.plot(xseq, df['way_s'], color='#1B5E20', linewidth=1.0, label='way_s')
    ax1.axhline(0, color='black', linewidth=0.5)
    ax1.set_ylabel('way / way_s')
    ax1.set_title('段内信号强度 (way / way_s)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(alpha=0.3)
    _build_segment_overlay(df, ax1, seg_starts, seg_ends, seg_type, x_index=xseq)

    # 副: way_s_way 比值 (强势占比) + vol_way_s_way
    ax2.plot(xseq, df['way_s_way'], color='#1B5E20', linewidth=1.0, label='way_s/way')
    ax2.plot(xseq, df['vol_way_s_way'], color='#6A1B9A', linewidth=1.0, label='vol_way/way')
    ax2.axhline(0, color='black', linewidth=0.5)
    ax2.set_ylabel('比值')
    ax2.set_title('强度比值 (way_s_way / vol_way_s_way)', fontsize=11)
    ax2.set_ylim(-1.1, 1.1)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(alpha=0.3)
    _build_segment_overlay(df, ax2, seg_starts, seg_ends, seg_type, x_index=xseq)

    return fig, axes


def plot_mplfinance(df, meta, out_path, title_suffix=''):
    """画一张完整的 mplfinance 图。"""
    print(f"  绘制 mplfinance: {out_path}")

    # ⭐ 假 DatetimeIndex 中转: 消除非交易时段留白
    n = len(df)
    df_for_mpf = df.copy()
    df_for_mpf.index = _make_fake_index(n)

    # ---------- 1) 主图：K线 + SMMA + 段色带 + 穿越点 ----------
    market_colors = mpf.make_marketcolors(up=UP_COLOR, down=DOWN_COLOR,
                                          edge='inherit', wick='inherit', volume='inherit')
    style = mpf.make_mpf_style(marketcolors=market_colors, gridstyle=':', gridcolor='#E0E0E0',
                                rc={'font.size': 9})

    addplots = [
        mpf.make_addplot(df_for_mpf['SMA_5'], color=SMA5_COLOR, width=1.0,
                         label='SMA_5', secondary_y=False),
        mpf.make_addplot(df_for_mpf['SMA_13'], color=SMA13_COLOR, width=1.0,
                         label='SMA_13', secondary_y=False),
        mpf.make_addplot(df_for_mpf['way_s_way'], panel=1, color='#1B5E20', width=0.8,
                         ylabel='way_s/way\nvol_way/way', ylim=(-1.1, 1.1)),
        mpf.make_addplot(df_for_mpf['vol_way_s_way'], panel=1, color='#6A1B9A', width=0.8),
    ]

    fig, axes = mpf.plot(
        df_for_mpf, type='candle', style=style,
        addplot=addplots,
        volume=True, volume_panel=2,
        panel_ratios=(5, 2, 2),
        figsize=(22, 13),
        title=f'XAUUSDm 4H (北京时间) — 段分析全景图{title_suffix}\n'
              f'段数={meta["n_seg"]}, 真实 good={meta["n_real_good"]}, '
              f'真实 bad={meta["n_real_bad"]}',
        returnfig=True,
        tight_layout=True,
        show_nontrading=False,  # 假日期本就连续,留它无意义
    )
    main_ax = axes[0]
    sub_ax = axes[2]   # 强度副图
    vol_ax = axes[4]   # 成交量副图

    # ⭐ X 轴刻度反向映射: 假日期 → 整数 0..n-1
    int_fmt = _to_int_formatter(n)
    for ax in (main_ax, sub_ax, vol_ax):
        ax.xaxis.set_major_formatter(int_fmt)

    # ---------- 2) 主图叠加：段方向色带 + 穿越点 markers ----------
    _build_segment_overlay(df, main_ax,
                           meta['seg_starts'], meta['seg_ends'], meta['seg_type'],
                           x_index=df_for_mpf.index)
    _build_markers(df, main_ax, meta['real_good_pos'], '^', GOOD_COLOR, size=90,
                   x_index=df_for_mpf.index)
    _build_markers(df, main_ax, meta['real_bad_pos'], 'v', BAD_COLOR, size=90,
                   x_index=df_for_mpf.index)

    # 在主图上 legend 加一段说明
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=SMA5_COLOR, lw=1.5, label='5 SMMA'),
        Line2D([0], [0], color=SMA13_COLOR, lw=1.5, label='13 SMMA'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor=GOOD_COLOR,
               markeredgecolor='black', markersize=10, label='真实 good (上穿)'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor=BAD_COLOR,
               markeredgecolor='black', markersize=10, label='真实 bad (下穿)'),
        Rectangle((0, 0), 1, 1, color=UP_BAND, alpha=0.3, label='up 段'),
        Rectangle((0, 0), 1, 1, color=DOWN_BAND, alpha=0.3, label='down 段'),
    ]
    main_ax.legend(handles=legend_elements, loc='upper left', fontsize=8, ncol=2)

    # ---------- 3) 副图也加段色带 (与主图同 x 轴) ----------
    _Build_segment_overlay_call = _build_segment_overlay
    _Build_segment_overlay_call(df, sub_ax,
                                meta['seg_starts'], meta['seg_ends'], meta['seg_type'],
                                x_index=df_for_mpf.index)
    # 副图上叠加 0 轴线
    sub_ax.axhline(0, color='black', linewidth=0.5, alpha=0.5)
    sub_ax.axhline(1.0, color='#1B5E20', linewidth=0.4, alpha=0.3, linestyle='--')
    sub_ax.axhline(-1.0, color='#6A1B9A', linewidth=0.4, alpha=0.3, linestyle='--')
    sub_ax.legend(loc='upper left', fontsize=8)

    # 成交量副图加 vol_ma_120 (用假日期 x 与 mplfinance 内部轴对齐)
    vol_ax.plot(df_for_mpf.index, df['vol_ma_120'],
                color='#FF6F00', linewidth=0.8, label='vol_MA_120')
    vol_ax.legend(loc='upper left', fontsize=8)

    fig.savefig(out_path, dpi=120, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"    ✓ {out_path} 已保存")


def plot_full(df, meta, out_path):
    plot_mplfinance(df, meta, out_path, title_suffix='（全 9 年）')


def plot_zoom(df, meta, out_path, n_tail=200):
    """末尾 n_tail 根的放大窗口。整数索引下取末尾。"""
    df_z = df.iloc[-n_tail:].copy()  # 整数索引,reset_index 后 iloc 自然取末段
    # 重新定位段边界到缩窄后的 df
    seg_starts_z = []
    seg_ends_z = []
    seg_type_z = []
    n_total = len(df_z)
    offset = len(df) - n_tail
    for s, e, t in zip(meta['seg_starts'], meta['seg_ends'], meta['seg_type']):
        if e < offset or s >= len(df):
            continue
        s_z = max(0, s - offset)
        e_z = min(n_total - 1, e - offset)
        if e_z < s_z:
            continue
        seg_starts_z.append(s_z)
        seg_ends_z.append(e_z)
        seg_type_z.append(t)

    # 重新定位穿越点
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
    plot_mplfinance(df_z, meta_z, out_path,
                    title_suffix=f'（末尾 {n_tail} 根 4H ≈ {n_tail // 6} 天,北京时间）')


if __name__ == '__main__':
    from plot_prepare import prepare
    df, meta = prepare('F:/use_code/MTA5/data/原始行情/XAUUSDm16388.csv')
    plot_full(df, meta, 'F:/use_code/MTA5/chart_full.png')
    plot_zoom(df, meta, 'F:/use_code/MTA5/chart_zoom.png', n_tail=200)
    print("✓ mplfinance 完成")

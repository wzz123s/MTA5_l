# -*- coding: utf-8 -*-
"""
plot_all.py
一键运行：准备数据 + 生成全部 4 张图。

输出:
  F:/use_code/MTA5/chart_full.png    (mplfinance 全图, 静态 PNG)
  F:/use_code/MTA5/chart_zoom.png    (mplfinance 末尾 200 根, 静态 PNG)
  F:/use_code/MTA5/chart_full.html   (plotly 全图, 交互 HTML)
  F:/use_code/MTA5/chart_zoom.html   (plotly 末尾 200 根, 交互 HTML)
"""
import sys
import io
# 不在入口脚本里重写 sys.stdout,避免模块导入链中重复重写导致 closed。
# UTF-8 编码重写在 plot_prepare.py 中已处理。

from plot_prepare import prepare
from plot_mplfinance import plot_full, plot_zoom
from plot_plotly import plot_full_html, plot_zoom_html


def main():
    csv_path = 'F:/use_code/MTA5/data/原始行情/XAUUSDm16388.csv'
    out_dir = 'F:/use_code/MTA5'

    print("=" * 60)
    print("XAUUSDm 段分析图表 — 一键生成")
    print("=" * 60)

    # 1) 准备数据
    print("\n[1/3] 准备数据...")
    df, meta = prepare(csv_path)
    print(f"  ✓ 数据形状: {df.shape}")
    print(f"  ✓ 段数: {meta['n_seg']}")
    print(f"  ✓ 真实穿越点: good={meta['n_real_good']}, bad={meta['n_real_bad']}, "
          f"差={meta['n_real_good'] - meta['n_real_bad']}")

    # 2) mplfinance PNG
    print("\n[2/3] mplfinance 静态 PNG...")
    plot_full(df, meta, f'{out_dir}/chart_full.png')
    plot_zoom(df, meta, f'{out_dir}/chart_zoom.png', n_tail=200)

    # 3) plotly HTML
    print("\n[3/3] plotly 交互 HTML...")
    plot_full_html(df, meta, f'{out_dir}/chart_full.html')
    plot_zoom_html(df, meta, f'{out_dir}/chart_zoom.html', n_tail=200)

    print("\n" + "=" * 60)
    print("✓ 全部完成")
    print("=" * 60)
    print(f"输出文件:")
    print(f"  {out_dir}/chart_full.png   (~0.4 MB)")
    print(f"  {out_dir}/chart_zoom.png   (~0.3 MB)")
    print(f"  {out_dir}/chart_full.html  (~3.8 MB)")
    print(f"  {out_dir}/chart_zoom.html  (~0.06 MB)")


if __name__ == '__main__':
    main()

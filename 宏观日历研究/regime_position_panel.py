# -*- coding: utf-8 -*-
"""
regime 仓位面板（2026-09-07 简化版）
=====================================
输出：三档仓位系数 position_scale ∈ {0.5, 1.0, 1.5}

判定依据（经回测验证，见《regime面板收益回测报告_20260907.md》）：
  只用同步层 Bias_55 = |(close - SMA_55)/SMA_55 * 100%|（H2 周期）判 regime：
     Bias_55 > 6.0%         → 0.5x（强趋势透支，防尾部）
     3.0% <= Bias_55 <= 4.5% → 1.5x（弱趋势甜区，加仓）
     其余（<3% 震荡 / 4.5~6% 中趋势）→ 1.0x（保持）

宏观慢变量（实际利率 / 美元 / 央行购金）仅作【背景参考】展示，
不参与仓位系数——回测证明其作为仓位缩放因子是负贡献（-1648 点）。

用法：
  python regime_position_panel.py                 # 自动读本地/下载宏观数据
  python regime_position_panel.py --cbg 买入      # 手工指定央行购金(仅背景展示)
"""
import argparse
import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
MACRO_DIR = os.path.join(BASE, "data")
H2_PATH = r"F:/use_code/MTA5_l/黄金/30m2H策略/参考实现工程/base_data/H2_XAUUSDm_39col.csv"
# MT5 实时导出（每根 M30 bar 追加一行，含 h2_close=当前价 + h2_sma55=H2 SMA55）
MT5_FILES_DIR = r"C:/Users/3762/AppData/Roaming/MetaQuotes/Terminal/DAD3B8CC3EAC09C0C9725021DF0C7A65/MQL5/Files"
REALTIME_CSV = os.path.join(MT5_FILES_DIR, "30m2H_strategy_signals_export.csv")

# FRED 免费 CSV 端点（无 API key）
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_SERIES = {
    "dfii10":    "DFII10",      # 10Y TIPS 收益率 = 实际利率
    "dtwexbgs":  "DTWEXBGS",    # 贸易加权美元指数 broad
}

# 阈值
RATE_DELTA_TH = 0.2     # 实际利率 63日Δ 阈值(百分点)
USD_PCT_TH = 2.0        # 美元 63日变化率阈值(%)
LOOKBACK_DAYS = 63      # 约 3 个月交易日


def load_fred_csv(sid):
    """读本地 data/<sid>.csv；无则从 FRED 下载；失败返回 None。"""
    local = os.path.join(MACRO_DIR, f"{sid}.csv")
    if os.path.isfile(local):
        df = pd.read_csv(local)
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    url = FRED_URL.format(sid=sid)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
        os.makedirs(MACRO_DIR, exist_ok=True)
        with open(local, "w", encoding="utf-8") as f:
            f.write(raw)
        df = pd.read_csv(local)
        df.columns = [c.strip().lower() for c in df.columns]
        print(f"[数据] 已从 FRED 下载并缓存 {sid} ({len(df)} 行)")
        return df
    except Exception as e:
        print(f"[警告] FRED 下载 {sid} 失败: {str(e)[:80]}")
        return None


def series_change(df, sid):
    """返回 (最新值, 最新日期, 63日Δ)。"""
    if df is None or len(df) < LOOKBACK_DAYS:
        return None, None, None
    val_col = [c for c in df.columns if c != "observation_date"][0]
    s = df.copy()
    s["observation_date"] = pd.to_datetime(s["observation_date"])
    s[val_col] = pd.to_numeric(s[val_col], errors="coerce")
    s = s.dropna(subset=[val_col]).reset_index(drop=True)
    if len(s) < LOOKBACK_DAYS:
        return None, None, None
    recent = float(s[val_col].iloc[-1])
    recent_date = s["observation_date"].iloc[-1]
    past = float(s[val_col].iloc[-LOOKBACK_DAYS])
    return recent, recent_date, recent - past


def macro_background(cbg_input=None):
    """宏观背景参考（仅展示，不参与仓位系数）。返回 detail_dict。"""
    detail = {}
    df_rate = load_fred_csv(FRED_SERIES["dfii10"])
    rv, rd, rdelta = series_change(df_rate, FRED_SERIES["dfii10"])
    detail["实际利率"] = {"值": rv, "日期": str(rd)[:10] if rd else None,
                          "63日Δ": round(rdelta, 3) if rdelta is not None else None,
                          "方向": ("下行(利多黄金)" if (rdelta is not None and rdelta < -RATE_DELTA_TH)
                                   else ("上行(利空黄金)" if (rdelta is not None and rdelta > RATE_DELTA_TH)
                                         else ("持平(中性)" if rdelta is not None else "无数据")))}

    df_usd = load_fred_csv(FRED_SERIES["dtwexbgs"])
    uv, ud, udelta = series_change(df_usd, FRED_SERIES["dtwexbgs"])
    usd_pct = None
    if udelta is not None and uv is not None and (uv - udelta) != 0:
        usd_pct = udelta / (uv - udelta) * 100.0
    detail["美元指数"] = {"值": uv, "日期": str(ud)[:10] if ud else None,
                          "63日Δ%": round(usd_pct, 2) if usd_pct is not None else None,
                          "方向": ("走弱(利多黄金)" if (usd_pct is not None and usd_pct < -USD_PCT_TH)
                                   else ("走强(利空黄金)" if (usd_pct is not None and usd_pct > USD_PCT_TH)
                                         else ("无方向(中性)" if usd_pct is not None else "无数据")))}

    detail["央行购金"] = {"值": cbg_input if cbg_input else "未知",
                          "方向": "持续净购(利多)" if cbg_input == "买入" else ("暂停/卖出(利空)" if cbg_input == "卖出" else "未知(中性)")}
    return detail


def bias55_bucket(bias55):
    """Bias_55 分档。返回 (档位名, 档位代码)。"""
    if bias55 is None:
        return "无数据", "na"
    if bias55 < 3.0:
        return "震荡(<3%)", "low"
    if bias55 <= 4.5:
        return "弱趋势(3~4.5%, 甜区)", "sweet"
    if bias55 <= 6.0:
        return "中趋势(4.5~6%)", "mid"
    return "强趋势(>6%, 透支)", "high"


def calc_bias55():
    """算最新 Bias_55。优先读 MT5 实时导出，回退历史 H2 CSV。
    返回 (bias55, 时间戳, 数据来源) —— 来源: "realtime" | "backtest" | "none"。
    """
    if os.path.isfile(REALTIME_CSV):
        try:
            rt = pd.read_csv(REALTIME_CSV)
            rt.columns = [c.strip() for c in rt.columns]
            if {"h2_close", "h2_sma55"} <= set(rt.columns) and len(rt) > 0:
                row = rt.iloc[-1]
                close = float(row["h2_close"])
                sma55 = float(row["h2_sma55"])
                if sma55 != 0:
                    ts = str(row["bar_time"]) if "bar_time" in rt.columns else "?"
                    return abs((close - sma55) / sma55 * 100.0), ts, "realtime"
        except Exception as e:
            print(f"[警告] 读实时导出失败: {str(e)[:60]}")
    if os.path.isfile(H2_PATH):
        h2 = pd.read_csv(H2_PATH, encoding="utf-8-sig")
        h2.columns = [c.strip() for c in h2.columns]
        if "SMA_55" in h2.columns and "close" in h2.columns:
            h2 = h2.dropna(subset=["SMA_55", "close"])
            if len(h2) > 0:
                close = float(h2["close"].iloc[-1])
                sma55 = float(h2["SMA_55"].iloc[-1])
                ts = str(h2["date"].iloc[-1])[:16] if "date" in h2.columns else "?"
                if sma55 != 0:
                    return abs((close - sma55) / sma55 * 100.0), ts, "backtest"
    return None, None, "none"


def map_scale(bias55):
    """只用 Bias_55 判仓位系数（回测验证 +33% 的方案）。返回 (scale, reason)。"""
    if bias55 is None:
        return 1.0, "Bias_55 无数据 → 兜底 1.0x（宁可不调）"
    bucket = bias55_bucket(bias55)[1]
    if bucket == "high":
        return 0.5, f"强趋势透支(Bias_55={bias55:.2f}%>6%) → 0.5x 防尾部"
    if bucket == "sweet":
        return 1.5, f"弱趋势甜区(Bias_55={bias55:.2f}%∈3~4.5%) → 1.5x 加仓"
    if bucket == "low":
        return 1.0, f"震荡(Bias_55={bias55:.2f}%<3%) → 1.0x 保持"
    return 1.0, f"中趋势(Bias_55={bias55:.2f}%∈4.5~6%) → 1.0x 保持"


def main():
    ap = argparse.ArgumentParser(description="regime 仓位面板（只用 Bias_55 判 regime）")
    ap.add_argument("--cbg", choices=["买入", "卖出", "未知"], default=None,
                    help="央行购金手工输入（仅背景展示，不参与系数）")
    args = ap.parse_args()

    print("=" * 66)
    print(" regime 仓位面板  |  只用 Bias_55 判 regime，宏观仅背景")
    print("=" * 66)

    # 背景参考：宏观慢变量（不参与系数）
    detail = macro_background(args.cbg)
    print(f"\n[背景参考] 宏观慢变量（仅展示，不参与仓位系数）")
    for k, v in detail.items():
        print(f"  - {k}: {v['方向']}  ({'值 '+str(v.get('值')) if v.get('值') is not None else '无数据'})")

    # 同步层：Bias_55（唯一判定依据）
    bias55, h2_ts, bias_src = calc_bias55()
    bucket_name, _ = bias55_bucket(bias55)
    src_label = {"realtime": "MT5 实时导出", "backtest": "历史回测 CSV", "none": "无数据"}.get(bias_src, bias_src)
    if bias55 is not None:
        print(f"\n[同步层] Bias_55 = {bias55:.3f}%  →  {bucket_name}")
    else:
        print(f"\n[同步层] Bias_55 = 无数据  →  {bucket_name}")
    print(f"          来源: {src_label} ｜ 最新 bar: {h2_ts}")

    # 合成（只用 Bias_55）
    scale, reason = map_scale(bias55)
    print(f"\n[合成]   position_scale = {scale}x")
    print(f"         理由: {reason}")

    out = {
        "position_scale": scale,
        "bias55": round(bias55, 4) if bias55 is not None else None,
        "bias55_bucket": bucket_name,
        "bias55_source": bias_src,
        "bias55_bar": h2_ts,
        "macro_background": detail,
        "reason": reason,
    }
    json_path = os.path.join(BASE, "regime_scale_output.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[JSON]  已写 {json_path}")
    print("=" * 66)


if __name__ == "__main__":
    main()

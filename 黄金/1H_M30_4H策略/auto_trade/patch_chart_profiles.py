# -*- coding: utf-8 -*-
"""修改 MT5 chart profile 注入 EA 配置（在 MT5 关闭状态下运行）

1. chart02.chr (XAUUSDm M30 空闲图表): 插入 1H_M30_4H_CurrentCandidate_EA expert 段
2. chart04.chr (2H EA 图表): 切换为 SimDeployment 参数 (Magic 332026 + 专用 ledger)
"""
import os

BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
PROF = os.path.join(BASE, "MQL5", "Profiles", "Charts", "Default")

# --- 1H EA expert 段（参数来自 1H_M30_4H_SimDeployment_EA.set）---
EXPERT_1H = """<expert>
name=1H_M30_4H_CurrentCandidate_EA
path=Experts\\1H_M30_4H_CurrentCandidate_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=312026
InpSymbol=XAUUSDm
=== Candidate Parameters ====
InpLots=0.01
InpStopLoPt=8.0
InpStopHiPt=28.0
InpSideExtremeThresholdPct=2.0
InpCloseMomentumMinPct=-0.4
InpShortVolWayMax=0.7
InpH1StopLookback=6
InpWayMergeMinLen=8
=== Timeframes ====
InpM30Period=30
InpH1Period=16385
InpH4Period=16388
=== Runtime ====
InpSimMode=true
InpAllowRealTrading=false
InpExportLedger=true
InpLedgerFile=1H_M30_4H_sim_deployment_trade_ledger.csv
InpHistoryBarsM30=2500
InpHistoryBarsH1=2500
InpHistoryBarsH4=900
InpCheckSec=1
InpSlippage=30
=== Live Guards ====
InpMaxOpenPositions=1
InpMaxSpreadPricePt=0.8
InpMaxRiskUsd=30.0
InpMinFreeMarginAfterTradeUsd=100.0
</inputs>
</expert>
"""


def read_utf16(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-16")


def write_utf16(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-16"))


def inject_expert_into_chart02():
    path = os.path.join(PROF, "chart02.chr")
    text = read_utf16(path)
    if "<expert>" in text:
        print("[chart02] 已有 expert 段，跳过插入")
        return
    # 在 windows_total=1 行之后插入 expert 段（文件为 CRLF）
    marker = "windows_total=1\r\n"
    idx = text.find(marker)
    if idx < 0:
        marker = "windows_total=1\n"
        idx = text.find(marker)
    if idx < 0:
        print("[chart02] ERROR: 未找到 windows_total 标记")
        raise SystemExit(1)
    insert_at = idx + len(marker)
    # 需要保留 \r\n 风格吗？原文件是 \r\n 还是 \n？探测
    has_crlf = "\r\n" in text
    sep = "\r\n" if has_crlf else "\n"
    new_text = text[:insert_at] + EXPERT_1H.replace("\n", sep) + text[insert_at:]
    write_utf16(path, new_text)
    print("[chart02] ✅ 已插入 1H EA expert 段")


def update_chart04_to_simdeployment():
    path = os.path.join(PROF, "chart04.chr")
    text = read_utf16(path)
    orig = text
    # 替换 Magic 和 ledger 文件名
    text = text.replace("InpMagic=322026", "InpMagic=332026")
    text = text.replace(
        "InpLedgerFile=2H_M30_6H_current_candidate_trade_ledger.csv",
        "InpLedgerFile=2H_M30_6H_sim_deployment_trade_ledger.csv",
    )
    if text == orig:
        print("[chart04] 无变化（可能已切换）")
    else:
        write_utf16(path, text)
        print("[chart04] ✅ 已切换为 SimDeployment (Magic 332026)")


if __name__ == "__main__":
    inject_expert_into_chart02()
    update_chart04_to_simdeployment()
    print("\n完成。请重启 MT5 使配置生效。")

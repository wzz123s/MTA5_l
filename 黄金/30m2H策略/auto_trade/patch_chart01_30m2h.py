# -*- coding: utf-8 -*-
"""修改 MT5 chart profile 注入 30m2H EA 配置（在 MT5 关闭状态下运行）

chart07.chr (XAUUSDm M30 空闲图表): 插入 30m2H_Strategy_EA expert 段 (v3.36 SimDeployment)
参数与 30m2H_SimDeployment_EA.set 一致 (Magic 302036, SimMode=true, AllowRealTrading=false)
"""
import os

BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
PROF = os.path.join(BASE, "MQL5", "Profiles", "Charts", "Default")

EXPERT_30M2H = """<expert>
name=30m2H_Strategy_EA
path=Experts\\30m2H_Strategy_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=302036
InpSymbol=XAUUSDm
=== Risk & Position ====
InpRiskPct=3.0
InpStopLo=5000.0
InpStopHi=35000.0
InpMaxPos=3
InpMinLots=0.01
InpMaxLots=10.0
InpUseDynamicLots=true
=== Live Risk Guards ====
InpEnableLiveRiskGuards=false
InpLiveBalanceCap=2000.0
InpMaxDailyLossUSD=120.0
InpMaxDrawdownUSD=200.0
InpMaxNewPositionsPerDay=9
InpMaxSpreadPoints=300
InpMarginGuardPct=500.0
InpLiveMaxLotCap=0.10
InpLeverageOverride=0
=== v3.0 Layer Config ====
InpBias55Threshold=3.0
InpPreCrossGapPct=0.300
InpPostNMin=2
InpPostNMax=6
InpUseLayer1=true
InpUseH2EarlyGateQ2=true
InpH2EarlyGateQ=2
InpUseLayer3=true
InpBias5TopPct=34.0
InpBias5Lookback=500
=== M15 Early Entry ====
InpUseM15EarlyEntry=false
InpEnableM15Slot2=false
InpUseM15RescueTag=true
InpM15Period=15
InpVerboseDecisionDiag=true
=== Split TP ====
InpStageCount=3
InpStage1Lots=0.01
InpStage2Lots=0.02
InpStage3Lots=0.03
InpStage1R=2.0
InpStage2TrailR=1.5
InpStage2ForceR=4.0
InpH2CrossBars=3
InpStage3On=true
InpDebugStages=true
=== Exports ====
InpExportCSV=true
InpExportTradeLedger=true
InpExportStagePriceDiag=false
InpExportM15EntryDiag=false
=== Strategy ====
InpFastMA=5
InpSlowMA=13
InpStopLookback=200
InpH2Thresh=0.0
InpH2Period=16386
InpM30Period=30
=== H2 SMMA ====
InpH2SMA5=5
InpH2SMA13=13
InpH2SMA55=55
InpH2SMA144=144
InpH2SMA233=233
=== Execution ====
InpSlippage=30
InpCheckSec=1
InpSimMode=true
InpAllowRealTrading=false
</inputs>
</expert>
"""


def read_utf16(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-16")


def write_utf16(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-16"))


def inject_expert_into_chart07():
    path = os.path.join(PROF, "chart07.chr")
    text = read_utf16(path)
    if "<expert>" in text:
        print("[chart07] 已有 expert 段，跳过插入")
        return
    marker = "windows_total=1\r\n"
    idx = text.find(marker)
    if idx < 0:
        marker = "windows_total=1\n"
        idx = text.find(marker)
    if idx < 0:
        print("[chart07] ERROR: 未找到 windows_total 标记")
        raise SystemExit(1)
    insert_at = idx + len(marker)
    has_crlf = "\r\n" in text
    sep = "\r\n" if has_crlf else "\n"
    new_text = text[:insert_at] + EXPERT_30M2H.replace("\n", sep) + text[insert_at:]
    write_utf16(path, new_text)
    print("[chart07] ✅ 已插入 30m2H EA expert 段 (Magic 302036, chart07 M30)")


if __name__ == "__main__":
    inject_expert_into_chart07()
    print("\n完成。请重启 MT5 使配置生效。")

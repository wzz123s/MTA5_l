# build_datalevent_charts.ps1
# 将 Gold_DataEvent_EA (XAUUSDm H4) 与 Oil_DataEvent_EA (USOILm H4) 注入 MT5 Default 图表配置
$ErrorActionPreference = 'Stop'
$term = 'C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65'
$prof = "$term\MQL5\Profiles\Charts\Default"
$bak  = "$term\MQL5\Profiles\Charts\Default_backup_20260901_datalevent"

if (!(Test-Path $prof)) { Write-Error "profile dir missing: $prof"; exit 1 }

if (!(Test-Path $bak)) {
  Copy-Item $prof $bak -Recurse
  Write-Output "backup -> $bak"
} else { Write-Output "backup already exists: $bak" }

$enc = New-Object System.Text.UTF8Encoding($false)

$goldExpert = @"
<expert>
name=Gold_DataEvent_EA
path=Experts\Advisors\Gold_DataEvent_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=411101
InpSymbol=XAUUSDm
=== Risk & Virtual Position ====
InpRiskPct=1.0
InpStopLoPt=5.0
InpStopHiPt=35.0
InpMaxOpenVirtual=3
InpMinLots=0.01
InpMaxLots=10.0
InpSimStartBalance=500.0
=== Layer 2 (three opportunities) ====
InpPreCrossGapPct=0.300
InpPostNMin=2
InpPostNMax=6
InpSameDirCdBars=3
InpLossCdLoss=2
InpLossCdHours=120
InpMergedMinLen=8
=== 6H Gate (bias5>0 AND bias55>0, trade-direction) ====
InpH6SMA5=5
InpH6SMA55=55
InpM30SMA5=5
InpM30SMA13=13
=== Split TP (three stages) ====
InpStage1R=2.0
InpStage2TrailR=1.5
InpStage2ForceR=4.0
InpStage1Units=0.5
InpStage2Units=1.0
InpStage3Units=1.5
=== Runtime ====
InpHistoryBars=600
InpSimMode=true
InpAllowRealTrading=false
InpExportCSV=true
InpExportLedger=true
InpVerboseDiag=true
=== Macro Calendar Filter (research, default OFF) ====
InpEventFilterOn=true
InpEventFilterHrs=2
InpEventCheckEvery=300
</inputs>
</expert>
"@

$oilExpert = @"
<expert>
name=Oil_DataEvent_EA
path=Experts\Advisors\Oil_DataEvent_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=411102
InpSymbol=USOILm
=== Risk & Virtual Position ====
InpRiskPct=1.0
InpStopLoPct=0.1
InpStopHiPct=1.0
InpMaxOpenVirtual=10
InpMinLots=0.01
InpMaxLots=10.0
InpSimStartBalance=500.0
=== Strategy (2H) ====
InpSMA5=5
InpSMA13=13
InpPreGap=0.003
InpHistoryBars2H=20000
=== 4H Gate ====
InpGateSMA5=5
InpGateSMA13=13
InpMergedMinLen=8
InpVolMaPeriod=120
InpGateThr=0.5
InpGateAmpLo=0.5
InpGateAmpHi=5.0
InpHistoryBars4H=10000
=== Runtime ====
InpSimMode=true
InpAllowRealTrading=false
InpExportCSV=true
InpExportLedger=true
InpVerboseDiag=true
=== Macro Calendar Filter (research, default OFF) ====
InpEventFilterOn=true
InpEventFilterHrs=1
InpEventCheckEvery=300
</inputs>
</expert>
"@

$c1 = [System.IO.File]::ReadAllText("$prof\chart01.chr")
$id1 = ([DateTime]::UtcNow.Ticks).ToString()
$c1 = [regex]::Replace($c1, '(?m)^id=.*$', "id=$id1")
$c1 = [regex]::Replace($c1, '(?m)^window_left=.*$', 'window_left=1404')
$c1 = [regex]::Replace($c1, '(?m)^window_top=.*$', 'window_top=0')
$c1 = [regex]::Replace($c1, '(?m)^window_right=.*$', 'window_right=1872')
$c1 = [regex]::Replace($c1, '(?m)^window_bottom=.*$', 'window_bottom=119')
$c1 = [regex]::Replace($c1, '<window>', $goldExpert + "`r`n`r`n<window>", 1)
[System.IO.File]::WriteAllText("$prof\chart11.chr", $c1, $enc)
Write-Output "chart11.chr written (Gold XAUUSDm H4) id=$id1"

$c2 = [System.IO.File]::ReadAllText("$prof\chart05.chr")
$c2 = [regex]::Replace($c2, '(?s)<expert>.*?</expert>\r?\n?', '')
$id2 = ([DateTime]::UtcNow.Ticks + 1234567).ToString()
$c2 = [regex]::Replace($c2, '(?m)^id=.*$', "id=$id2")
$c2 = [regex]::Replace($c2, '(?m)^period_size=.*$', 'period_size=4')
$c2 = [regex]::Replace($c2, '(?m)^window_left=.*$', 'window_left=1404')
$c2 = [regex]::Replace($c2, '(?m)^window_top=.*$', 'window_top=238')
$c2 = [regex]::Replace($c2, '(?m)^window_right=.*$', 'window_right=1872')
$c2 = [regex]::Replace($c2, '(?m)^window_bottom=.*$', 'window_bottom=357')
$c2 = [regex]::Replace($c2, '<window>', $oilExpert + "`r`n`r`n<window>", 1)
[System.IO.File]::WriteAllText("$prof\chart12.chr", $c2, $enc)
Write-Output "chart12.chr written (Oil USOILm H4) id=$id2"

$ow = @(Get-Content "$prof\order.wnd") | Where-Object { $_ -notmatch '^chart1[12]\.chr\s*$' }
$ow += 'chart11.chr'
$ow += 'chart12.chr'
[System.IO.File]::WriteAllLines("$prof\order.wnd", $ow, $enc)
Write-Output 'order.wnd updated:'
Get-Content "$prof\order.wnd" | ForEach-Object { Write-Output "  $_" }

Write-Output '--- chart11 checks ---'
$m11 = Select-String -Path "$prof\chart11.chr" -Pattern '^name=Gold_DataEvent_EA|^path=Experts|^InpSimMode=|^InpEventFilterOn=|^InpEventFilterHrs=|^symbol=|^period_size='
$m11 | ForEach-Object { Write-Output ('  ' + $_.Line) }
Write-Output '--- chart12 checks ---'
$m12 = Select-String -Path "$prof\chart12.chr" -Pattern '^name=Oil_DataEvent_EA|^path=Experts|^InpSimMode=|^InpEventFilterOn=|^InpEventFilterHrs=|^symbol=|^period_size='
$m12 | ForEach-Object { Write-Output ('  ' + $_.Line) }
Write-Output 'DONE'

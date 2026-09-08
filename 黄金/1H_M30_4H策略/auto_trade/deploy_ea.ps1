param(
    [string]$TerminalRoot = ""
)

$ErrorActionPreference = "Stop"

$Strategy = "1H_M30_4H"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceMq5 = Join-Path $Here "1H_M30_4H_Strategy_EA.mq5"
$SourceSet = Join-Path $Here "1H_M30_4H_Strategy_EA.set"

$Candidates = @()
if ($TerminalRoot) {
    $Candidates += $TerminalRoot
}
$Candidates += @(
    "F:\Program Files\MetaTrader 5 EXNESS",
    "C:\Program Files\MetaTrader 5 EXNESS",
    "C:\Program Files\MetaTrader 5"
)

$Root = $Candidates | Where-Object { $_ -and (Test-Path (Join-Path $_ "MQL5")) } | Select-Object -First 1
if (-not $Root) {
    throw "MT5 root not found. Pass -TerminalRoot with the folder that contains MQL5."
}

$ExpertsDir = Join-Path $Root "MQL5\Experts"
$TesterDir = Join-Path $Root "MQL5\Profiles\Tester"
New-Item -ItemType Directory -Force -Path $ExpertsDir, $TesterDir | Out-Null

$DestMq5 = Join-Path $ExpertsDir "1H_M30_4H_Strategy_EA.mq5"
$DestSet = Join-Path $TesterDir "1H_M30_4H_Strategy_EA.set"
Copy-Item -LiteralPath $SourceMq5 -Destination $DestMq5 -Force
Copy-Item -LiteralPath $SourceSet -Destination $DestSet -Force

Write-Host "[$Strategy] copied EA source to: $DestMq5"
Write-Host "[$Strategy] copied tester preset to: $DestSet"
Write-Host "Open MetaEditor, compile 1H_M30_4H_Strategy_EA.mq5, then run MT5 Strategy Tester with 1H_M30_4H_Strategy_EA.set."

param(
    [string]$TerminalRoot = ""
)

$ErrorActionPreference = "Stop"

$Strategy = "1H_M30_4H"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceMq5 = Join-Path $Here "1H_M30_4H_CurrentCandidate_EA.mq5"
$SourceEx5 = Join-Path $Here "1H_M30_4H_CurrentCandidate_EA.ex5"
$SourceSet = Join-Path $Here "1H_M30_4H_CurrentCandidate_EA.set"

$Candidates = @()
if ($TerminalRoot) {
    $Candidates += $TerminalRoot
}
$Candidates += @(
    "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16",
    "F:\Program Files\MetaTrader 5 EXNESS",
    "C:\Program Files\MetaTrader 5 EXNESS",
    "C:\Program Files\MetaTrader 5"
)

$Root = $Candidates | Where-Object { $_ -and (Test-Path (Join-Path $_ "MQL5")) } | Select-Object -First 1
if (-not $Root) {
    throw "MT5 root not found. Pass -TerminalRoot with the folder that contains MQL5."
}

$ExpertsDir = Join-Path $Root "MQL5\Experts\Advisors"
$TesterDir = Join-Path $Root "MQL5\Profiles\Tester"
New-Item -ItemType Directory -Force -Path $ExpertsDir, $TesterDir | Out-Null

$DestMq5 = Join-Path $ExpertsDir "1H_M30_4H_CurrentCandidate_EA.mq5"
$DestEx5 = Join-Path $ExpertsDir "1H_M30_4H_CurrentCandidate_EA.ex5"
$DestSet = Join-Path $TesterDir "1H_M30_4H_CurrentCandidate_EA.set"
Copy-Item -LiteralPath $SourceMq5 -Destination $DestMq5 -Force
if (Test-Path $SourceEx5) {
    Copy-Item -LiteralPath $SourceEx5 -Destination $DestEx5 -Force
}
Copy-Item -LiteralPath $SourceSet -Destination $DestSet -Force

Write-Host "[$Strategy] copied current candidate EA source to: $DestMq5"
if (Test-Path $DestEx5) {
    Write-Host "[$Strategy] copied current candidate compiled EA to: $DestEx5"
}
Write-Host "[$Strategy] copied current candidate tester preset to: $DestSet"
Write-Host "Compile 1H_M30_4H_CurrentCandidate_EA.mq5, then run MT5 Strategy Tester with 1H_M30_4H_CurrentCandidate_EA.set."
Write-Host "Default InpSimMode=true exports a virtual ledger: 1H_M30_4H_current_candidate_trade_ledger.csv"

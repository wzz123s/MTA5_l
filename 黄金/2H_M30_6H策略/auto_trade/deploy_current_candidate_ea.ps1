param(
    [string]$TerminalRoot = ""
)

$ErrorActionPreference = "Stop"

$Strategy = "2H_M30_6H"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceMq5 = Join-Path $Here "2H_M30_6H_CurrentCandidate_EA.mq5"
$SourceEx5 = Join-Path $Here "2H_M30_6H_CurrentCandidate_EA.ex5"
$SourceSet = Join-Path $Here "2H_M30_6H_CurrentCandidate_EA.set"
$SimSet = Join-Path $Here "2H_M30_6H_SimDeployment_EA.set"

$Candidates = @()
if ($TerminalRoot) {
    $Candidates += $TerminalRoot
}
$Candidates += @(
    "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65",
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
$PresetsDir = Join-Path $Root "MQL5\Presets"
New-Item -ItemType Directory -Force -Path $ExpertsDir, $PresetsDir | Out-Null

$DestMq5 = Join-Path $ExpertsDir "2H_M30_6H_CurrentCandidate_EA.mq5"
$DestEx5 = Join-Path $ExpertsDir "2H_M30_6H_CurrentCandidate_EA.ex5"
Copy-Item -LiteralPath $SourceMq5 -Destination $DestMq5 -Force
if (Test-Path $SourceEx5) {
    Copy-Item -LiteralPath $SourceEx5 -Destination $DestEx5 -Force
}
if (Test-Path $SimSet) {
    Copy-Item -LiteralPath $SimSet -Destination (Join-Path $PresetsDir "2H_M30_6H_SimDeployment_EA.set") -Force
}

Write-Host "[$Strategy] copied current candidate EA source to: $DestMq5"
Write-Host "[$Strategy] copied current candidate compiled EA to: $DestEx5"
Write-Host "[$Strategy] copied sim deployment preset to: $PresetsDir\2H_M30_6H_SimDeployment_EA.set"
Write-Host "Default InpSimMode=true exports a virtual ledger: 2H_M30_6H_sim_deployment_trade_ledger.csv"

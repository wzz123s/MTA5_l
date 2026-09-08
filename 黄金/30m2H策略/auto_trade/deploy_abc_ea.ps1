param(
    [string]$TerminalRoot = ""
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Strategy = "30m2H"
$EAName = "30m2H_ABC_EA"

$SourceMq5 = Join-Path $Here "$EAName.mq5"
$SourceEx5 = Join-Path $Here "$EAName.ex5"
$SourceSet = Join-Path $Here "30m2H_ABC_SimDeployment_EA.set"

$Root = "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
if ($TerminalRoot) { $Root = $TerminalRoot }
if (-not (Test-Path (Join-Path $Root "MQL5"))) { throw "MT5 root not found: $Root" }

$ExpertsDir = Join-Path $Root "MQL5\Experts\Advisors"
$PresetsDir = Join-Path $Root "MQL5\Presets"
New-Item -ItemType Directory -Force -Path $ExpertsDir, $PresetsDir | Out-Null

Copy-Item -LiteralPath $SourceMq5 -Destination (Join-Path $ExpertsDir "$EAName.mq5") -Force
Copy-Item -LiteralPath $SourceEx5 -Destination (Join-Path $ExpertsDir "$EAName.ex5") -Force
Copy-Item -LiteralPath $SourceSet -Destination (Join-Path $PresetsDir "30m2H_ABC_SimDeployment_EA.set") -Force

Write-Host "[$Strategy] copied $EAName source/ex5/set to $Root"

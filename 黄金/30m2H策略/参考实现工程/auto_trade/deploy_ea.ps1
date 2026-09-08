#Requires -RunAsAdministrator
# Deploy 30m2H_Strategy_EA.ex5 to all known MT5 installs' MQL5\Experts
# Run once: right-click -> Run with PowerShell -> "Open" (it will UAC-elevate automatically)

$ErrorActionPreference = "Stop"
$src = "F:\use_code\MTA5\auto_trade\30m2H_Strategy_EA.ex5"
$installs = @(
    "F:\Program Files\MetaTrader 5 EXNESS",
    "C:\Program Files\MetaTrader 5",
    "C:\Program Files\MetaTrader 5 EXNESS"
)

Write-Host "=== 30m2H EA Deployment ===" -ForegroundColor Cyan
if (-not (Test-Path $src)) {
    Write-Host "ERROR: source not found: $src" -ForegroundColor Red
    exit 1
}
Write-Host ("Source: " + $src + " (size=" + (Get-Item $src).Length + " bytes)")

$ok = $false
foreach ($inst in $installs) {
    if (-not (Test-Path $inst)) {
        Write-Host ("  SKIP: " + $inst + " (not found)") -ForegroundColor Yellow
        continue
    }
    $dstDir = Join-Path $inst "MQL5\Experts"
    try {
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
        $dst = Join-Path $dstDir "30m2H_Strategy_EA.ex5"
        Copy-Item -Force $src $dst
        Write-Host ("  OK: " + $dst) -ForegroundColor Green
        $ok = $true
    } catch {
        Write-Host ("  FAIL: " + $dstDir + " : " + $_.Exception.Message) -ForegroundColor Red
    }
}

if (-not $ok) {
    Write-Host "No MQL5\Experts could be created. Check admin rights." -ForegroundColor Red
    exit 2
}

Write-Host ""
Write-Host "=== Next steps in MT5 ===" -ForegroundColor Cyan
Write-Host "1. Press Ctrl+N to open Navigator"
Write-Host "2. Right-click 'Expert Advisors' -> Refresh"
Write-Host "3. Drag '30m2H_Strategy_EA' onto XAUUSDm chart"
Write-Host "4. In the dialog, confirm InpSimMode = false -> OK"
Write-Host ""
Write-Host "Done." -ForegroundColor Green

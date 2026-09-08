# 1H_M30_4H EA Auto-Deployment Script
# Generated: 2026-07-30 20:26
# Purpose: Automate MT5 EA deployment steps

param(
    [switch]$AutoStart = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StrategyRoot = "F:\use_code\MTA5_l\黄金\1H_M30_4H策略"
$MT5DataDir = "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
$MT5ExePath = "F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
$EAName = "1H_M30_4H_CurrentCandidate_EA"
$SetName = "1H_M30_4H_SimDeployment_EA"
$Symbol = "XAUUSDm"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 1H_M30_4H EA Auto-Deployment Script" -ForegroundColor Cyan
Write-Host " Generated: 2026-07-30 20:26" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify EA compiled file exists
Write-Host "[Step 1/4] Verifying EA compilation..." -ForegroundColor Yellow
$EAEx5File = "$StrategyRoot\auto_trade\$EAName.ex5"
if (-not (Test-Path $EAEx5File)) {
    Write-Host "❌ ERROR: Compiled EA not found: $EAEx5File" -ForegroundColor Red
    exit 1
}
$eaInfo = Get-Item $EAEx5File
Write-Host "✅ Found: $($eaInfo.Name) ($([math]::Round($eaInfo.Length/1KB, 1)) KB, $($eaInfo.LastWriteTime))" -ForegroundColor Green

# Step 2: Copy files to MT5 directory
Write-Host "`n[Step 2/4] Copying files to MT5 directory..." -ForegroundColor Yellow
$ExpertsDir = "$MT5DataDir\MQL5\Experts"
$PresetsDir = "$MT5DataDir\MQL5\Presets"

New-Item -ItemType Directory -Force -Path $ExpertsDir | Out-Null
New-Item -ItemType Directory -Force -Path $PresetsDir | Out-Null

Copy-Item -Path $EAEx5File -Destination "$ExpertsDir\" -Force
Copy-Item -Path "$StrategyRoot\auto_trade\$SetName.set" -Destination "$PresetsDir\" -Force

if ((Test-Path "$ExpertsDir\$EAName.ex5") -and (Test-Path "$PresetsDir\$SetName.set")) {
    Write-Host "✅ Files copied successfully:" -ForegroundColor Green
    Write-Host "   → $ExpertsDir\$EAName.ex5" -ForegroundColor Gray
    Write-Host "   → $PresetsDir\$SetName.set" -ForegroundColor Gray
} else {
    Write-Host "❌ ERROR: File copy failed" -ForegroundColor Red
    exit 1
}

# Step 3: Prepare MT5 configuration
Write-Host "`n[Step 3/4] Preparing MT5 configuration..." -ForegroundColor Yellow

# Create deployment info file for verification
$deployInfo = @{
    DeploymentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    EAName = $EAName
    SetName = $SetName
    Symbol = $Symbol
    Status = "Ready to load"
    SafetyConfig = @{
        SimMode = $true
        AllowRealTrading = $false
        MaxRiskUsd = 30.0
        MaxPositions = 1
    }
} | ConvertTo-Json -Depth 3

$deployInfo | Out-File -FilePath "$StrategyRoot\auto_trade\deployment_status.json" -Encoding UTF8
Write-Host "✅ Deployment status saved" -ForegroundColor Green

# Step 4: Generate manual load instructions (for user)
Write-Host "`n[Step 4/4] Generating load instructions..." -ForegroundColor Yellow

$instructions = @"

========================================
  📋 MANUAL LOAD INSTRUCTIONS
========================================

MT5 is starting (or already running)...
Please follow these steps in MT5:

1️⃣  OPEN CHART
    • Press F6 or go to File → New Chart
    • Select: $Symbol
    • Select Period: M30 (30 minutes)
    • Click OK

2️⃣  NAVIGATE TO EXPERT ADVISORS
    • In MT5 Navigator panel (left side)
    • Expand 'Expert Advisors' section
    • Find: $EAName

3️⃣  ATTACH EA TO CHART
    • Drag & drop $EAName onto the chart
    • OR right-click the EA → 'Attach to Chart'

4️⃣  CONFIGURE EA PARAMETERS
    In the popup window:

    [Common Tab]
    ☑ Allow live trading
    ☑ Allow DLL imports (if prompted)

    [Inputs Tab]
    • Click 'Load' button
    • Select preset: $SetName.set
    • Verify these CRITICAL safety settings:
      - SimMode = true ✅
      - AllowRealTrading = false ✅
      - MaxRiskUsd = 30.0 ✅
      - MaxOpenPositions = 1 ✅

    • Click OK

5️⃣  VERIFY SUCCESS
    Check these indicators:
    ✓ Smile face icon 😊 on chart (top-right)
    ✓ No error messages in Experts log (bottom tab)
    ✓ Ledger file created: MQL5\Files\*_trade_ledger.csv

========================================
  ⚠️  SAFETY CONFIRMATION
========================================

✅ This is SIMULATION MODE only
✅ NO real trades will be executed
✅ Even if 'Allow live trading' is checked,
   the EA's internal SimMode=true blocks it
✅ Maximum risk per trade: \$30
✅ Maximum positions: 1

========================================
"@

$instructions | Out-File -FilePath "$StrategyRoot\auto_trade\MANUAL_LOAD_INSTRUCTIONS.txt" -Encoding UTF8
Write-Host "✅ Instructions saved to: MANUAL_LOAD_INSTRUCTIONS.txt" -ForegroundColor Green

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " DEPLOYMENT SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Status: ✅ READY TO LOAD" -ForegroundColor Green
Write-Host ""
Write-Host "Files deployed:" -ForegroundColor Yellow
Write-Host "  • EA: $EAName.ex5 → MQL5\Experts\" -ForegroundColor Gray
Write-Host "  • Set: $SetName.set → MQL5\Presets\" -ForegroundColor Gray
Write-Host ""
Write-Host "Next action:" -ForegroundColor Yellow
Write-Host "  Open MANUAL_LOAD_INSTRUCTIONS.txt and follow steps" -ForegroundColor White
Write-Host ""

if ($AutoStart) {
    Write-Host "Starting MT5..." -ForegroundColor Yellow
    Start-Process $MT5ExePath
    Write-Host "✅ MT5 launched" -ForegroundColor Green
}

Write-Host "========================================" -ForegroundColor Cyan

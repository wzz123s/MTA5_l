param(
    [string]$InstallRoot = "F:\Program Files\MetaTrader 5 EXNESS",
    [string]$TerminalDataPath = "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16",
    [string]$Login = "277752085",
    [string]$Server = "Exness-MT5Trial5",
    [int]$TimeoutSec = 300,
    [switch]$CopyCachedXauHistory
)

$ErrorActionPreference = "Stop"

$Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PortableRoot = Join-Path $Workspace "mt5_portable_alignment"
$PortableTerminal = Join-Path $PortableRoot "terminal64.exe"
$LogDir = Join-Path $Workspace "ea_alignment_logs"
$IniPath = Join-Path $LogDir "1H_M30_4H_CurrentCandidate_EA.portable_alignment_20200102_20231229.ini"
$ReportPath = Join-Path $LogDir "1H_M30_4H_CurrentCandidate_EA.portable_tester_report.xml"
$LedgerName = "1H_M30_4H_current_candidate_trade_ledger.csv"
$AlignmentDir = Join-Path $Workspace "黄金/1H_M30_4H策略\data\validation\ea_alignment_current_candidate"
$LedgerDest = Join-Path $AlignmentDir $LedgerName

$strategyDir = Get-ChildItem -LiteralPath $Workspace -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "auto_trade\1H_M30_4H_CurrentCandidate_EA.mq5") } |
    Sort-Object Name |
    Select-Object -First 1
if (-not $strategyDir) {
    throw "strategy directory not found for prefix 1H_M30_4H"
}

$sourceMq5 = Join-Path $strategyDir.FullName "auto_trade\1H_M30_4H_CurrentCandidate_EA.mq5"
$sourceEx5 = Join-Path $strategyDir.FullName "auto_trade\1H_M30_4H_CurrentCandidate_EA.ex5"
$sourceSet = Join-Path $strategyDir.FullName "auto_trade\1H_M30_4H_CurrentCandidate_EA.set"

foreach ($required in @($sourceMq5, $sourceEx5, $sourceSet)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "required file missing: $required"
    }
}

New-Item -ItemType Directory -Force -Path $PortableRoot, $LogDir, $AlignmentDir | Out-Null

foreach ($exeName in @("terminal64.exe", "metatester64.exe", "MetaEditor64.exe")) {
    $sourceExe = Join-Path $InstallRoot $exeName
    if (Test-Path -LiteralPath $sourceExe) {
        Copy-Item -LiteralPath $sourceExe -Destination (Join-Path $PortableRoot $exeName) -Force
    }
}

$portableExperts = Join-Path $PortableRoot "MQL5\Experts\Advisors"
$portableProfiles = Join-Path $PortableRoot "MQL5\Profiles\Tester"
$portableConfig = Join-Path $PortableRoot "config"
New-Item -ItemType Directory -Force -Path $portableExperts, $portableProfiles, $portableConfig | Out-Null
Copy-Item -LiteralPath $sourceMq5 -Destination (Join-Path $portableExperts "1H_M30_4H_CurrentCandidate_EA.mq5") -Force
Copy-Item -LiteralPath $sourceEx5 -Destination (Join-Path $portableExperts "1H_M30_4H_CurrentCandidate_EA.ex5") -Force
Copy-Item -LiteralPath $sourceSet -Destination (Join-Path $portableProfiles "1H_M30_4H_CurrentCandidate_EA.set") -Force

$serversDat = Join-Path $TerminalDataPath "config\servers.dat"
if (Test-Path -LiteralPath $serversDat) {
    Copy-Item -LiteralPath $serversDat -Destination (Join-Path $portableConfig "servers.dat") -Force
}

if ($CopyCachedXauHistory) {
    $sourceServer = Join-Path $TerminalDataPath "bases\Exness-MT5Trial5"
    $portableServer = Join-Path $PortableRoot "bases\Exness-MT5Trial5"
    New-Item -ItemType Directory -Force -Path $portableServer | Out-Null

    foreach ($dirName in @("symbols")) {
        $sourceDir = Join-Path $sourceServer $dirName
        if (Test-Path -LiteralPath $sourceDir) {
            Copy-Item -LiteralPath $sourceDir -Destination $portableServer -Recurse -Force
        }
    }

    $sourceHistory = Join-Path $sourceServer "history\XAUUSDm"
    $portableHistory = Join-Path $portableServer "history\XAUUSDm"
    New-Item -ItemType Directory -Force -Path $portableHistory | Out-Null
    foreach ($yearFile in @("2020.hcc", "2021.hcc", "2022.hcc", "2023.hcc")) {
        $sourceFile = Join-Path $sourceHistory $yearFile
        if (Test-Path -LiteralPath $sourceFile) {
            try {
                Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $portableHistory $yearFile) -Force
            } catch {
                Write-Host "history_copy_skipped=$sourceFile error=$($_.Exception.Message)"
            }
        }
    }

    $sourceTicks = Join-Path $sourceServer "ticks\XAUUSDm"
    $portableTicks = Join-Path $portableServer "ticks\XAUUSDm"
    New-Item -ItemType Directory -Force -Path $portableTicks | Out-Null
    if (Test-Path -LiteralPath $sourceTicks) {
        Get-ChildItem -LiteralPath $sourceTicks -File -Force -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $portableTicks $_.Name) -Force
                } catch {
                    Write-Host "tick_copy_skipped=$($_.FullName) error=$($_.Exception.Message)"
                }
            }
    }
}

$iniLines = @(
    "; Portable current candidate Strategy Tester alignment run",
    "; Generated 2026-07-26",
    "[Common]",
    "Login=$Login",
    "Server=$Server",
    "",
    "[Tester]",
    "Expert=Advisors\1H_M30_4H_CurrentCandidate_EA.ex5",
    "Symbol=XAUUSDm",
    "Period=M30",
    "Optimization=0",
    "Model=0",
    "FromDate=2020.01.02",
    "ToDate=2023.12.29",
    "ForwardMode=0",
    "Deposit=500",
    "Currency=USD",
    "ProfitInPips=0",
    "Leverage=2000",
    "ExecutionMode=0",
    "OptimizationCriterion=0",
    "Visual=0",
    "ReplaceReport=1",
    "ShutdownTerminal=1",
    "Report=$ReportPath",
    "",
    "[TesterInputs]"
)
$setLines = Get-Content -LiteralPath $sourceSet | Where-Object {
    $line = $_.Trim()
    $line -and -not $line.StartsWith(";")
}
Set-Content -LiteralPath $IniPath -Value ($iniLines + $setLines) -Encoding ASCII

if (-not (Test-Path -LiteralPath $PortableTerminal)) {
    throw "portable terminal missing: $PortableTerminal"
}

$startedAt = Get-Date
Write-Host "started_at=$($startedAt.ToString('s'))"
Write-Host "portable_root=$PortableRoot"
Write-Host "portable_terminal=$PortableTerminal"
Write-Host "ini=$IniPath"
Write-Host "report=$ReportPath"
Write-Host "copy_cached_xau_history=$CopyCachedXauHistory"

$args = "/portable /config:`"$IniPath`""
$process = Start-Process -FilePath $PortableTerminal -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
Write-Host "portable_terminal_exit=$($process.ExitCode)"

$deadline = $startedAt.AddSeconds($TimeoutSec)
if ($process.ExitCode -ne 0) {
    $deadline = (Get-Date).AddSeconds(5)
}
$latestLedger = $null
$reportFound = $false

while ((Get-Date) -lt $deadline) {
    $reportFound = Test-Path -LiteralPath $ReportPath
    $latestLedger = Get-ChildItem -LiteralPath $PortableRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq $LedgerName } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($reportFound -or ($latestLedger -and $latestLedger.LastWriteTime -ge $startedAt.AddSeconds(-2))) {
        break
    }

    Start-Sleep -Seconds 5
}

if ($latestLedger) {
    Copy-Item -LiteralPath $latestLedger.FullName -Destination $LedgerDest -Force
    Write-Host "ledger_source=$($latestLedger.FullName)"
    Write-Host "ledger_last_write=$($latestLedger.LastWriteTime.ToString('s'))"
    Write-Host "ledger_copied=$LedgerDest"
} else {
    Write-Host "ledger_missing=$LedgerName"
}

if ($reportFound) {
    $reportDest = Join-Path $AlignmentDir "1H_M30_4H_CurrentCandidate_EA.portable_tester_report.xml"
    Copy-Item -LiteralPath $ReportPath -Destination $reportDest -Force
    Write-Host "report_copied=$reportDest"
} else {
    Write-Host "report_missing=$ReportPath"
}

Write-Host "recent_portable_logs:"
Get-ChildItem -LiteralPath $PortableRoot -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -eq ".log" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 10 |
    ForEach-Object { Write-Host "$($_.LastWriteTime.ToString('s')) $($_.FullName)" }

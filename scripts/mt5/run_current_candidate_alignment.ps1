param(
    [string]$InstallRoot = "F:\Program Files\MetaTrader 5 EXNESS",
    [string]$TerminalDataPath = "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16",
    [int]$TimeoutSec = 240,
    [switch]$CloseExistingTerminal
)

$ErrorActionPreference = "Stop"

$Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Terminal = Join-Path $InstallRoot "terminal64.exe"
$IniPath = Join-Path $Workspace "ea_alignment_logs\1H_M30_4H_CurrentCandidate_EA.alignment_20200226_20231230.ini"
$ReportPath = Join-Path $Workspace "ea_alignment_logs\1H_M30_4H_CurrentCandidate_EA.tester_report.xml"
$StrategyDir = Get-ChildItem -LiteralPath $Workspace -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "auto_trade\1H_M30_4H_CurrentCandidate_EA.mq5") } |
    Sort-Object Name |
    Select-Object -First 1
if (-not $StrategyDir) {
    throw "strategy directory containing current candidate EA not found"
}
$AlignmentDir = Join-Path $StrategyDir.FullName "data\validation\ea_alignment_current_candidate"
$LedgerName = "1H_M30_4H_current_candidate_trade_ledger.csv"
$LedgerDest = Join-Path $AlignmentDir $LedgerName

$TerminalRoot = Split-Path -Parent $TerminalDataPath
$MetaQuotesRoot = Split-Path -Parent $TerminalRoot
$TerminalId = Split-Path -Leaf $TerminalDataPath
$TesterDataPath = Join-Path (Join-Path $MetaQuotesRoot "Tester") $TerminalId

function Get-TesterFilesDirs {
    if (-not (Test-Path -LiteralPath $TesterDataPath)) {
        return @()
    }

    $agents = Get-ChildItem -LiteralPath $TesterDataPath -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "Agent-*" }
    $dirs = @()
    foreach ($agent in $agents) {
        $filesDir = Join-Path $agent.FullName "MQL5\Files"
        if (Test-Path -LiteralPath $filesDir) {
            $dirs += $filesDir
        }
    }
    return $dirs
}

function Get-LedgerCandidates {
    $matches = @()
    foreach ($filesDir in Get-TesterFilesDirs) {
        $candidate = Join-Path $filesDir $LedgerName
        if (Test-Path -LiteralPath $candidate) {
            $matches += Get-Item -LiteralPath $candidate
        }
    }
    return $matches | Sort-Object LastWriteTime -Descending
}

if (-not (Test-Path -LiteralPath $Terminal)) {
    throw "terminal64.exe not found: $Terminal"
}
if (-not (Test-Path -LiteralPath $IniPath)) {
    throw "tester ini not found: $IniPath"
}

New-Item -ItemType Directory -Force -Path $AlignmentDir | Out-Null

$startedAt = Get-Date
$existingTerminals = Get-Process -Name terminal64 -ErrorAction SilentlyContinue |
    Select-Object Id, StartTime, MainWindowTitle

Write-Host "started_at=$($startedAt.ToString('s'))"
Write-Host "terminal=$Terminal"
Write-Host "ini=$IniPath"
Write-Host "report=$ReportPath"
Write-Host "tester_data=$TesterDataPath"
if ($existingTerminals) {
    foreach ($proc in $existingTerminals) {
        Write-Host "existing_terminal id=$($proc.Id) start=$($proc.StartTime) title=$($proc.MainWindowTitle)"
    }
} else {
    Write-Host "existing_terminal none"
}

if ($CloseExistingTerminal -and $existingTerminals) {
    foreach ($procInfo in $existingTerminals) {
        $proc = Get-Process -Id $procInfo.Id -ErrorAction SilentlyContinue
        if (-not $proc) {
            continue
        }

        Write-Host "closing_existing_terminal id=$($proc.Id)"
        if ($proc.MainWindowHandle -ne 0) {
            [void]$proc.CloseMainWindow()
            if (-not $proc.WaitForExit(20000)) {
                Stop-Process -Id $proc.Id -Force
                Write-Host "forced_existing_terminal_stop id=$($proc.Id)"
            } else {
                Write-Host "closed_existing_terminal id=$($proc.Id)"
            }
        } else {
            Stop-Process -Id $proc.Id -Force
            Write-Host "stopped_headless_terminal id=$($proc.Id)"
        }
    }
}

$testerArgs = "/config:`"$IniPath`""
$tester = Start-Process -FilePath $Terminal -ArgumentList $testerArgs -Wait -PassThru -WindowStyle Hidden
Write-Host "terminal_launch_exit=$($tester.ExitCode)"

$deadline = $startedAt.AddSeconds($TimeoutSec)
$reportFound = $false
$ledgerFound = $false
$latestLedger = $null

while ((Get-Date) -lt $deadline) {
    $reportFound = Test-Path -LiteralPath $ReportPath
    $latestLedger = Get-LedgerCandidates | Select-Object -First 1
    $ledgerFound = $null -ne $latestLedger -and $latestLedger.LastWriteTime -ge $startedAt.AddSeconds(-2)

    if ($reportFound -or $ledgerFound) {
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
    $reportDest = Join-Path $AlignmentDir "1H_M30_4H_CurrentCandidate_EA.tester_report.xml"
    Copy-Item -LiteralPath $ReportPath -Destination $reportDest -Force
    Write-Host "report_copied=$reportDest"
} else {
    Write-Host "report_missing=$ReportPath"
}

Write-Host "tester_files_dirs:"
foreach ($filesDir in Get-TesterFilesDirs) {
    Write-Host $filesDir
}

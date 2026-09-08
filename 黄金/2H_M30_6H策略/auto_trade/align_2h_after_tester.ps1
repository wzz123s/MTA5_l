param(
    [string]$Ledger = ""
)

$ErrorActionPreference = "Stop"

$defaultLedger = "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Files\2H_M30_6H_current_candidate_trade_ledger.csv"
if (-not $Ledger) {
    $Ledger = $defaultLedger
}
if (-not (Test-Path -LiteralPath $Ledger)) {
    Write-Error "EA ledger not found: $Ledger"
}

$destDir = "F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\ea_alignment_current_candidate"
New-Item -ItemType Directory -Path $destDir -Force | Out-Null
$destLedger = Join-Path $destDir "ea_actual_trade_ledger.csv"
Copy-Item -LiteralPath $Ledger -Destination $destLedger -Force

Write-Output "EA ledger copied to $destLedger"
python "F:\use_code\MTA5_l\黄金\2H_M30_6H策略\scripts\export_2h_current_candidate_ea_alignment.py" $destLedger

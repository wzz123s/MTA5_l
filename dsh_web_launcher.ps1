# dsh_web_launcher.ps1 (ASCII only)
# Set window title + cd workspace + tee dsh web output to screen & log
param(
    [Parameter(Mandatory=$true)][string]$WS,
    [Parameter(Mandatory=$true)][int]$PORT
)
$ErrorActionPreference = 'Continue'
$host.UI.RawUI.WindowTitle = "DSH Web [$WS] port $PORT"
Set-Location -LiteralPath $WS
$logPath = Join-Path $env:TEMP "dsh_web_$PORT.log"
"=== dsh web launcher at $(Get-Date -Format o) | log=$logPath ===" | Out-File -FilePath $logPath -Encoding utf8 -Append
& dsh web --port $PORT *>&1 | Tee-Object -FilePath $logPath -Append | Out-Host

# dsh_reopen_ui.ps1 (ASCII only)
# Auto-fetch token URL from dsh web launcher log and open browser
$ErrorActionPreference = 'SilentlyContinue'
$temp = $env:TEMP
$logs = Get-ChildItem -Path $temp -Filter 'dsh_web_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if (-not $logs) {
    Write-Host "[dsh] no dsh_web_*.log found. Is DSH Web running? Start it with option [1] first." -ForegroundColor Yellow
    exit 1
}
$log = $logs[0]
Write-Host "[dsh] using log: $($log.FullName)"
$text = Get-Content $log.FullName -Raw -Encoding utf8
$pattern = 'http://127\.0\.0\.1:\d+/\?token=[A-Za-z0-9_-]+'
$ms = [regex]::Matches($text, $pattern)
if ($ms.Count -eq 0) {
    Write-Host "[dsh] no token URL found in log yet. dsh web may still be starting; wait ~10s and retry [3]." -ForegroundColor Yellow
    exit 2
}
# use the LATEST (last) token URL in the log
$url = $ms[$ms.Count - 1].Value
Write-Host "[dsh] opening: $url" -ForegroundColor Green
Start-Process $url
Write-Host "[dsh] opened in default browser." -ForegroundColor Green

# ============================================================
# 手动执行助手：Tester 回测 + 逐笔对齐（黄金/原油数据事件 EA）
# 用法：双击运行（Windows PowerShell），按提示操作
# ============================================================
$ErrorActionPreference = "Continue"
$ROOT = "F:\use_code\MTA5_l\原油黄金数据行情策略"
$PY = "F:\Program Files\Python\python.exe"
$TERM = "F:\Program Files\MetaTrader 5\terminal64.exe"
$TD = "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
$LEDGER_DIR = "$TD\MQL5\Files"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  数据行情策略 Tester 回测 + 逐笔对齐助手" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ---- 1. 选择策略 ----
Write-Host "请选择要回测的策略：" -ForegroundColor Yellow
Write-Host "  1) Gold_DataEvent_EA（黄金，XAUUSDm H4，2023-2024 冒烟）"
Write-Host "  2) Gold_DataEvent_EA（黄金，XAUUSDm H4，2021-2026 全量）"
Write-Host "  3) Oil_DataEvent_EA（原油，USOILm H4，2021-2026）"
$choice = Read-Host "输入 1/2/3"
# 注：16388=H4（此前 16386 为 H2 的笔误；EA 信号基于 M30 数据，图周期仅影响 tick 驱动，但为与文档一致统一用 H4）
switch ($choice) {
  "1" { $EA="Gold_DataEvent_EA"; $SYM="XAUUSDm"; $PER="16388"; $F="2023.01.01"; $T="2024.12.31"; $EXP="expected_ledger_gold.csv"; $NAME="gold" }
  "2" { $EA="Gold_DataEvent_EA"; $SYM="XAUUSDm"; $PER="16388"; $F="2019.01.01"; $T="2026.08.30"; $EXP="expected_ledger_gold.csv"; $NAME="gold" }
  "3" { $EA="Oil_DataEvent_EA"; $SYM="USOILm"; $PER="16388"; $F="2021.01.01"; $T="2026.08.30"; $EXP="expected_ledger_oil.csv"; $NAME="oil" }
  default { Write-Host "无效选择，退出" -ForegroundColor Red; exit 1 }
}

# ---- 2. 注入 Tester 配置 ----
Write-Host ""
Write-Host "[1/6] 注入 Tester 配置（$EA / $SYM / $F ~ $T）..." -ForegroundColor Green
& $PY "$ROOT\auto_trade\inject_tester_ini.py" $EA $SYM $PER $F $T

# ---- 3. 启动终端 ----
Write-Host "[2/6] 启动 MT5 终端..." -ForegroundColor Green
if (-not (Get-Process terminal64 -ErrorAction SilentlyContinue)) {
  Start-Process $TERM
  Start-Sleep -Seconds 30
} else {
  Write-Host "      终端已在运行，跳过启动" -ForegroundColor Gray
}

# ---- 4. 等待用户操作 ----
Write-Host ""
Write-Host "==============================================" -ForegroundColor Yellow
Write-Host "【请手动操作】在 MT5 终端中：" -ForegroundColor Yellow
Write-Host "  1. 按 Ctrl+R 打开【策略测试】面板" -ForegroundColor Yellow
Write-Host "  2. 确认 EA=$EA / 品种=$SYM / 周期=H4 / 日期=$F ~ $T" -ForegroundColor Yellow
Write-Host "  3. 点击【开始】按钮运行回测" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Yellow
Read-Host "回测运行完成后按回车继续..."

# ---- 5. 回收 ledger ----
Write-Host "[3/6] 回收 ledger CSV..." -ForegroundColor Green
$ledger = Get-ChildItem "$LEDGER_DIR" -Filter "*DataEvent_trade_ledger.csv" -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $ledger) {
  $ledger = Get-ChildItem "$LEDGER_DIR" -Filter "*_trade_ledger.csv" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if ($ledger) {
  $dst = "$ROOT\data\validation\tester_actual_$NAME.csv"
  Copy-Item $ledger.FullName $dst -Force
  Write-Host "      已回收: $($ledger.Name) -> $dst" -ForegroundColor Gray
} else {
  Write-Host "未找到 ledger，请检查 $LEDGER_DIR" -ForegroundColor Red
  Read-Host "按回车退出"
  exit 1
}

# ---- 6. 运行对齐 ----
Write-Host "[4/6] 运行逐笔对齐..." -ForegroundColor Green
& $PY "$ROOT\scripts\validate\align_ledgers.py" --expected "$ROOT\data\validation\$EXP" --actual $dst --name $NAME
Write-Host ""
Write-Host "[5/6] 若为 FAIL，请查看差异明细并调整口径（见 M4 报告）" -ForegroundColor Yellow
Write-Host "[6/6] 对齐通过后可挂载 EA 做模拟盘观察（见 05b 手册）" -ForegroundColor Green
Write-Host ""
Read-Host "按回车退出"

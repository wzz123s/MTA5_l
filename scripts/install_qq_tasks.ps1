# install_qq_tasks.ps1 — 注册 MTA5 QQ 监控任务（需在真实终端或提权下运行一次）
$py = 'F:\Program Files\Python\python.exe'
$watch = 'F:\use_code\MTA5_l\scripts\watch_signal_alerts.py'
$digest = 'F:\use_code\MTA5_l\scripts\qq_digest_push.py'
$calendar = 'F:\use_code\MTA5_l\scripts\event_calendar_push.py'

# 每分钟任务（信号告警 / 总览摘要）
$minuteTasks = @(
  @{ n='MTA5_qq_alerts';  mo=2;  cmd="$py `"$watch`"" },
  @{ n='MTA5_qq_digest'; mo=30; cmd="$py `"$digest`"" }
)
foreach ($t in $minuteTasks) {
  schtasks /create /f /tn $t.n /sc minute /mo $t.mo /tr $t.cmd
}

# 每天任务：事件日历推送（北京时间 08:00，推未来 3 天高影响事件）
schtasks /create /f /tn 'MTA5_event_calendar' /sc daily /st 08:00 /tr "$py `"$calendar`""

schtasks /query /tn MTA5_qq_alerts /fo LIST
schtasks /query /tn MTA5_qq_digest /fo LIST
schtasks /query /tn MTA5_event_calendar /fo LIST

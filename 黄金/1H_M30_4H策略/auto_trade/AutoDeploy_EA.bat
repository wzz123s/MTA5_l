@echo off
chcp 65001 >nul
echo ============================================
echo   1H_M30_4H EA 自动部署脚本
echo   生成时间: 2026-07-30 20:40
echo ============================================
echo.

:: Step 1: 验证文件存在
echo [Step 1/4] 验证EA文件...
if not exist "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\1H_M30_4H_CurrentCandidate_EA.ex5" (
    echo ❌ EA文件未找到！请先运行复制脚本。
    pause
    exit /b 1
)
echo ✅ EA文件已就位

if not exist "C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Presets\1H_M30_4H_SimDeployment_EA.set" (
    echo ❌ 参数包未找到！请先运行复制脚本。
    pause
    exit /b 1
)
echo ✅ 参数包已就位
echo.

:: Step 2: 启动MT5
echo [Step 2/4] 启动MT5终端...
start "" "F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
echo ✅ MT5已启动
echo.

:: 等待MT5完全加载
echo ⏳ 等待MT5初始化（10秒）...
timeout /t 10 /nobreak >nul
echo.

:: Step 3: 打开XAUUSDm M30图表
echo [Step 3/4] 正在打开XAUUSDm M30图表...
echo 注意: 此步骤需要MT5 GUI支持
echo 如果MT5没有自动打开图表，请手动按 F6 → 选择 XAUUSDm + M30
echo.

:: Step 4: 显示手动操作指南
echo [Step 4/4] 部署完成检查清单
echo ============================================
echo.
echo 📋 请在MT5中完成以下操作（约2分钟）:
echo.
echo   1️⃣  在Navigator面板找到 "Expert Advisors"
echo       展开 → 找到 "1H_M30_4H_CurrentCandidate_EA"
echo.
echo   2️⃣  将EA拖拽到 XAUUSDm M30 图表上
echo       （如果没有M30图表，先按F6新建一个）
echo.
echo   3️⃣  在弹出的设置窗口中:
echo       ☑ 勾选 "Allow algorithmic trading"
echo       点击 "Load" 按钮
echo       选择: 1H_M30_4H_SimDeployment_EA.set
echo       确认参数: SimMode = true ✅
echo       点击 OK
echo.
echo   4️⃣  验证运行状态:
echo       ✓ 图表右上角显示 😊 笑脸图标
echo       ✓ 底部 "Experts" 标签显示初始化信息
echo.
echo ============================================
echo ✅ 自动化部分完成！剩余手动操作约2分钟
echo.
echo 📄 详细操作指南请查看:
echo    F:\use_code\MTA5_l\黄金\1H_M30_4H策略\说明文档\06_模拟盘部署\部署执行报告_20260730.md
echo.
pause
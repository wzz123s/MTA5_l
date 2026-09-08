@echo off
title DSH Web Launcher
set "NPM=C:\Users\3762\AppData\Roaming\npm"
where dsh >nul 2>&1 || set "PATH=%NPM%;%PATH%"
:menu
cls
echo ==================================================
echo   DSH Web Launcher  -  pick a workspace
echo   Each DSH Web instance = one workspace + one port
echo ==================================================
echo.
echo   [1] Workspace: F:\use_code\MTA5_l    (port 3080)
echo   [2] Type your own workspace folder   (pick a free port)
echo   [3] Re-open UI at 127.0.0.1:3080 (needs browser session)
echo   [0] Exit
echo.
set "c="
set /p "c=Your choice (default 1): "
if "%c%"=="" set "c=1"
if "%c%"=="2" goto custom
if "%c%"=="3" goto openui
if "%c%"=="0" goto done
if not "%c%"=="1" goto menu
set "WS=F:\use_code\MTA5_l"
set "PORT=3080"
goto run
:custom
set "WS="
set "PORT="
set /p "WS=Full workspace folder path: "
if "%WS%"=="" goto menu
if not exist "%WS%" (echo NOT FOUND: "%WS%" & pause & goto menu)
set /p "PORT=Port (Enter = 3080): "
if "%PORT%"=="" set "PORT=3080"
goto run
:run
powershell -NoProfile -Command "if(Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue){exit 1}else{exit 0}"
if errorlevel 1 (
  echo.
  echo Port %PORT% is already in use.
  echo Maybe that instance is already running - choose [3] to open it,
  echo or pick another port.
  pause
  goto menu
)
start "DSH Web [%WS%] port %PORT%" powershell -NoExit -File "%~dp0dsh_web_launcher.ps1" -WS "%WS%" -PORT %PORT%
echo.
echo   dsh web is starting... it prints an authenticated URL like:
echo     dsh web: http://127.0.0.1:%PORT%/?token=...
echo   and the launcher also tees the output to
echo     %%TEMP%%\dsh_web_%PORT%.log
echo   so [3] can auto-redirect you to the token URL.
echo.
goto done
:openui
echo   Looking up the latest token URL from the launcher log...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dsh_reopen_ui.ps1"
echo.
goto done
:done
echo.
pause
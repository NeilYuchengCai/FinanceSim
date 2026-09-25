@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================================
::  FinanceSim Launcher — 单一文件启动器
:: ============================================================

cd /d "%~dp0.."

:: ── 检测 Python ─────────────────────────────────────────────
set "PYTHON="
for %%p in (
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
) do if exist "%%~p" if not defined PYTHON set "PYTHON=%%~p"
if not defined PYTHON for /f "tokens=*" %%p in ('where python 2^>nul') do set "PYTHON=%%~p"
if not defined PYTHON (
    echo [ERROR] Python not found. Install Python 3.12+
    pause >nul
    exit /b 1
)

:: ── 检测 Node ───────────────────────────────────────────────
set "NODE="
for %%n in (
    "C:\Program Files\nodejs\node.exe"
    "C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"
) do if exist "%%~n" if not defined NODE set "NODE=%%~n"
if not defined NODE for /f "tokens=*" %%n in ('where node 2^>nul') do set "NODE=%%~n"
if not defined NODE (
    echo [ERROR] Node.js not found. Install Node.js 22+.
    pause >nul
    exit /b 1
)

:: ── PID 文件 ─────────────────────────────────────────────────
set "PID_FILE=%TEMP%\financesim_pids.txt"
if exist "%PID_FILE%" del /f /q "%PID_FILE%" >nul 2>&1

:menu
cls
echo.
echo   +------------------------------------------------+
echo   |        FinanceSim Control Panel                |
echo   +------------------------------------------------+
echo.
echo     [1] Start Local Server     (localhost only)
echo     [2] Start LAN Access       (share with devices)
echo     [3] Stop All Services
echo     [4] Check Status
echo     [5] Open Browser
echo     [6] Restart
echo     [0] Exit
echo.
set /p choice="Choose [0-6]: "

if "!choice!"=="1" goto :start_local
if "!choice!"=="2" goto :start_lan
if "!choice!"=="3" goto :stop_all
if "!choice!"=="4" goto :check_status
if "!choice!"=="5" goto :open_browser
if "!choice!"=="6" goto :restart
if "!choice!"=="0" goto :exit
echo.
echo   Invalid choice.
timeout /t 1 >nul
goto :menu

:: ── 安装依赖并初始化 DB ───────────────────────────────────────
:install_deps
echo   Installing dependencies...
pushd "%~dp0..\backend"
"%PYTHON%" -m pip install -r requirements.txt -q
popd
echo   Initializing database...
"%PYTHON%" "%~dp0\init_db.py" >nul 2>&1
goto :eof

:: ── 保存 PID ──────────────────────────────────────────────────
:save_pids
(
echo !BACKEND_PID!
echo !FRONTEND_PID!
) > "%PID_FILE%"
goto :eof

:: ── 杀掉 PID ──────────────────────────────────────────────────
:kill_pids
if exist "%PID_FILE%" (
    for /f "tokens=1,2" %%a in (%PID_FILE%) do (
        taskkill /PID %%a /F >nul 2>&1
        taskkill /PID %%b /F >nul 2>&1
    )
    del /f /q "%PID_FILE%" >nul 2>&1
)
goto :eof

:: ── 启动本地 ──────────────────────────────────────────────────
:start_local
call :install_deps
echo.
echo   Starting backend (port 8000)...
start "" /min cmd /k "title FinanceSim-Backend && cd /d \"%~dp0..\backend\" && \"%PYTHON%\" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level info"
timeout /t 2 >nul
for /f "tokens=*" %%a in ('wmic process where "name='cmd.exe' and caption like '%%FinanceSim-Backend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "BACKEND_PID=%%a"

echo   Starting frontend (port 5173)...
start "" /min cmd /k "title FinanceSim-Frontend && cd /d \"%~dp0..\frontend\" && npm run dev"
timeout /t 3 >nul
for /f "tokens=*" %%a in ('wmic process where "name='cmd.exe' and caption like '%%FinanceSim-Frontend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "FRONTEND_PID=%%a"

call :save_pids

echo.
echo   +------------------------------------------------+
echo   |   http://localhost:5173                        |
echo   |   API: http://localhost:8000/api/v1           |
echo   |   Docs: http://localhost:8000/docs            |
echo   +------------------------------------------------+
echo.
echo   Press any key to return to menu...
pause >nul
goto :menu

:: ── 启动 LAN ──────────────────────────────────────────────────
:start_lan
call :install_deps

set "LOCAL_IP=unknown"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    for /f "tokens=1" %%i in ("%%a") do set "LOCAL_IP=%%~i"
)

echo.
echo   Starting backend (port 8000, LAN)...
start "" /min cmd /k "title FinanceSim-Backend && cd /d \"%~dp0..\backend\" && \"%PYTHON%\" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info"
timeout /t 2 >nul
for /f "tokens=*" %%a in ('wmic process where "name='cmd.exe' and caption like '%%FinanceSim-Backend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "BACKEND_PID=%%a"

echo   Starting frontend (port 5173, LAN)...
start "" /min cmd /k "title FinanceSim-Frontend && cd /d \"%~dp0..\frontend\" && npm run dev -- --host 0.0.0.0"
timeout /t 3 >nul
for /f "tokens=*" %%a in ('wmic process where "name='cmd.exe' and caption like '%%FinanceSim-Frontend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "FRONTEND_PID=%%a"

call :save_pids

echo.
echo   +------------------------------------------------+
echo   |   Local:  http://localhost:5173                |
echo   |   LAN:    http://!LOCAL_IP!:5173              |
echo   |   API:    http://!LOCAL_IP!:8000/api/v1       |
echo   |                                              |
echo   |   NOTE: Allow ports 8000/5173 in Firewall      |
echo   +------------------------------------------------+
echo.
echo   Press any key to return to menu...
pause >nul
goto :menu

:: ── 停止所有 ──────────────────────────────────────────────────
:stop_all
echo.
echo   Stopping all services...
call :kill_pids
taskkill /IM uvicorn.exe /T /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
echo   Done.
echo.
echo   Press any key to return to menu...
pause >nul
goto :menu

:: ── 检查状态 ──────────────────────────────────────────────────
:check_status
cls
echo.
echo   +------------------------------------------------+
echo   |           Service Status                       |
echo   +------------------------------------------------+
echo.
echo   [Backend - port 8000]
netstat -ano 2>nul | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 ( echo     RUNNING  ) else ( echo     STOPPED  )
echo.
echo   [Frontend - port 5173]
netstat -ano 2>nul | findstr ":5173" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 ( echo     RUNNING  ) else ( echo     STOPPED  )
echo.
echo   [Processes]
tasklist /FI "IMAGENAME eq uvicorn.exe" 2>nul | findstr /I "uvicorn" >nul 2>&1
if !errorlevel! equ 0 ( echo     uvicorn:   RUNNING ) else ( echo     uvicorn:   stopped )
tasklist /FI "IMAGENAME eq node.exe" 2>nul | findstr /I "node" >nul 2>&1
if !errorlevel! equ 0 ( echo     node:      RUNNING ) else ( echo     node:      stopped )
echo.
echo   Press any key to return to menu...
pause >nul
goto :menu

:: ── 打开浏览器 ────────────────────────────────────────────────
:open_browser
start "" "http://localhost:5173"
timeout /t 1 >nul
goto :menu

:: ── 重启 ──────────────────────────────────────────────────────
:restart
echo.
echo   Restarting FinanceSim...
call :stop_all
goto :start_local

:: ── 退出 ──────────────────────────────────────────────────────
:exit
call :kill_pids >nul 2>&1
echo.
echo   Bye!
timeout /t 1 >nul
endlocal
exit /b 0

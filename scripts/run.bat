@echo off
setlocal enabledelayedexpansion

:: Get project root - resolve to absolute path
set "PROOT=%~dp0"
set "PROOT=%PROOT:~0,-1%"
for %%i in ("%PROOT%\..") do set "PROOT=%%~fi"

:: Detect Python
set "PYTHON="
for %%p in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
) do if exist "%%~p" if not defined PYTHON set "PYTHON=%%~p"
if not defined PYTHON for /f "tokens=*" %%p in ('where python 2^>nul') do set "PYTHON=%%~p"
if not defined PYTHON (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

:: Detect Node
set "NODE="
for %%n in (
    "C:\Program Files\nodejs\node.exe"
    "%USERPROFILE%\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"
) do if exist "%%~n" if not defined NODE set "NODE=%%~n"
if not defined NODE for /f "tokens=*" %%n in ('where node 2^>nul') do set "NODE=%%~n"
if not defined NODE (
    echo [ERROR] Node.js not found.
    pause
    exit /b 1
)

:: Paths (absolute, no cd needed)
set "BDIR=%PROOT%\backend"
set "FDIR=%PROOT%\frontend"
set "PID=%TEMP%\fs_pid.txt"

:: Install deps (run from correct dirs without changing cwd)
:install_deps
echo Installing...
"%PYTHON%" -m pip install -r "%BDIR%\requirements.txt" -q
if errorlevel 1 echo [WARN] pip issues
cmd /c "cd /d \"%FDIR%\" && npm ci --silent >nul 2>&1 || npm install --silent >nul 2>&1"
echo Done.
goto :eof

:: Kill backend/frontend processes
:stop_services
taskkill /IM uvicorn.exe /T /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
goto :eof

:: Check if services are running
:check_services
netstat -ano 2>nul | findstr ":8000 " >nul 2>&1
set "_backend=STOPPED"
if !errorlevel! equ 0 set "_backend=RUNNING"
netstat -ano 2>nul | findstr ":5173 " >nul 2>&1
set "_frontend=STOPPED"
if !errorlevel! equ 0 set "_frontend=RUNNING"
goto :eof

:menu
cls
echo.
echo ========================================
echo   FinanceSim Control Panel
echo ========================================
echo.
echo   [1] Start Local Server
echo   [2] Start LAN Access
echo   [3] Stop All Services
echo   [4] Check Status
echo   [5] Open Browser
echo   [6] Restart
echo   [0] Exit
echo.
call :check_services
echo   Backend:  !_backend!
echo   Frontend: !_frontend!
echo.
set /p choice="Choose [0-6]: "

if "!choice!"=="1" goto :start_local
if "!choice!"=="2" goto :start_lan
if "!choice!"=="3" goto :stop_all
if "!choice!"=="4" goto :check_status
if "!choice!"=="5" goto :open_browser
if "!choice!"=="6" goto :restart
if "!choice!"=="0" goto :exit
echo Invalid.
timeout /t 2 >nul
goto :menu

:start_local
call :install_deps
echo.
echo Starting backend (port 8000)...
start "" /min cmd /k "title FS-Backend && cd /d \"%BDIR%\" && \"%PYTHON%\" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level info"
timeout /t 4 >nul

echo Starting frontend (port 5173)...
start "" /min cmd /k "title FS-Frontend && cd /d \"%FDIR%\" && npm run dev"
timeout /t 5 >nul

echo.
echo ========================================
echo   http://localhost:5173
echo   API:  http://localhost:8000/api/v1
echo   Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to return...
pause >nul
goto :menu

:start_lan
call :install_deps
echo.
echo Starting backend (port 8000, LAN)...
start "" /min cmd /k "title FS-Backend && cd /d \"%BDIR%\" && \"%PYTHON%\" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info"
timeout /t 4 >nul

echo Starting frontend (port 5173, LAN)...
start "" /min cmd /k "title FS-Frontend && cd /d \"%FDIR%\" && npm run dev -- --host 0.0.0.0"
timeout /t 5 >nul

set "LOCAL_IP=unknown"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    for /f "tokens=1" %%i in ("%%a") do set "LOCAL_IP=%%~i"
)

echo.
echo ========================================
echo   Local:  http://localhost:5173
echo   LAN:    http://!LOCAL_IP!:5173
echo   API:    http://!LOCAL_IP!:8000/api/v1
echo   NOTE: Allow ports 8000/5173 in Firewall
echo ========================================
echo.
echo Press any key to return...
pause >nul
goto :menu

:stop_all
echo.
echo Stopping all services...
call :stop_services
echo Done.
echo.
echo Press any key to return...
pause >nul
goto :menu

:check_status
cls
echo.
echo ========================================
echo         Service Status
echo ========================================
echo.
call :check_services
echo   Backend:  !_backend!
echo   Frontend: !_frontend!
echo.
echo Press any key to return...
pause >nul
goto :menu

:open_browser
start "" "http://localhost:5173"
timeout /t 1 >nul
goto :menu

:restart
echo.
echo Restarting...
call :stop_services
timeout /t 1 >nul
goto :start_local

:exit
call :stop_services >nul 2>&1
echo.
echo Done.
timeout /t 1 >nul
endlocal
exit /b 0

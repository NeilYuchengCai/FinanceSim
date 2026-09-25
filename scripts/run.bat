@echo off
setlocal enabledelayedexpansion

:: Get project root from script location
set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"

:: Detect Python
set "PYTHON="
for %%p in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
) do if exist "%%~p" if not defined PYTHON set "PYTHON=%%~p"
if not defined PYTHON for /f "tokens=*" %%p in ('where python 2^>nul') do set "PYTHON=%%~p"
if not defined PYTHON (
    echo [ERROR] Python not found. Install Python 3.12+.
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
    echo [ERROR] Node.js not found. Install Node.js 22+.
    pause
    exit /b 1
)

:: Paths
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "PID_FILE=%TEMP%\fs_pids.txt"

:: Save PIDs
:save_pids
(
echo %BACKEND_PID%
echo %FRONTEND_PID%
) > "%PID_FILE%"
goto :eof

:: Kill PIDs
:kill_pids
if exist "%PID_FILE%" (
    set /p BPID=<"%PID_FILE%"
    for /f "skip=1 tokens=*" %%a in ('type "%PID_FILE%"') do set LPID=%%a
    if defined BPID taskkill /PID !BPID! /F >nul 2>&1
    if defined LPID taskkill /PID !LPID! /F >nul 2>&1
    del /f /q "%PID_FILE%" >nul 2>&1
)
taskkill /IM uvicorn.exe /T /F >nul 2>&1
goto :eof

:: Install deps
:install_deps
echo Installing dependencies...
cd /d "%BACKEND_DIR%"
"%PYTHON%" -m pip install -r requirements.txt -q
if errorlevel 1 echo [WARN] pip install had issues (may be OK)
cd /d "%FRONTEND_DIR%"
npm ci --silent >nul 2>&1 || npm install --silent >nul 2>&1
echo Done.
goto :eof

:menu
cls
echo.
echo   +----------------------------------------+
echo   |     FinanceSim Control Panel           |
echo   +----------------------------------------+
echo.
echo     [1] Start Local Server
echo     [2] Start LAN Access
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
echo Invalid choice.
timeout /t 2 >nul
goto :menu

:start_local
call :install_deps
echo.
echo Starting backend (port 8000)...
cd /d "%BACKEND_DIR%"
start "" /min cmd /k "title FS-Backend && \"%PYTHON%\" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level info"
timeout /t 3 >nul
for /f "tokens=*" %%a in ('wmic process where "name=\"cmd.exe\" and caption like '%%FS-Backend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "BACKEND_PID=%%a"

echo Starting frontend (port 5173)...
cd /d "%FRONTEND_DIR%"
start "" /min cmd /k "title FS-Frontend && npm run dev"
timeout /t 4 >nul
for /f "tokens=*" %%a in ('wmic process where "name=\"cmd.exe\" and caption like '%%FS-Frontend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "FRONTEND_PID=%%a"

call :save_pids

echo.
echo   +----------------------------------------+
echo   |   http://localhost:5173                |
echo   |   API: http://localhost:8000/api/v1    |
echo   |   Docs: http://localhost:8000/docs     |
echo   +----------------------------------------+
echo.
echo Press any key to return to menu...
pause >nul
goto :menu

:start_lan
call :install_deps
echo.
echo Starting backend (port 8000, LAN)...
cd /d "%BACKEND_DIR%"
start "" /min cmd /k "title FS-Backend && \"%PYTHON%\" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info"
timeout /t 3 >nul
for /f "tokens=*" %%a in ('wmic process where "name=\"cmd.exe\" and caption like '%%FS-Backend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "BACKEND_PID=%%a"

echo Starting frontend (port 5173, LAN)...
cd /d "%FRONTEND_DIR%"
start "" /min cmd /k "title FS-Frontend && npm run dev -- --host 0.0.0.0"
timeout /t 4 >nul
for /f "tokens=*" %%a in ('wmic process where "name=\"cmd.exe\" and caption like '%%FS-Frontend%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do set "FRONTEND_PID=%%a"

call :save_pids

set "LOCAL_IP=unknown"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    for /f "tokens=1" %%i in ("%%a") do set "LOCAL_IP=%%~i"
)

echo.
echo   +----------------------------------------+
echo   |   Local:  http://localhost:5173        |
echo   |   LAN:    http://!LOCAL_IP!:5173       |
echo   |   API:    http://!LOCAL_IP!:8000/api/v1|
echo   |                                        |
echo   |   NOTE: Allow ports 8000/5173 firewall |
echo   +----------------------------------------+
echo.
echo Press any key to return to menu...
pause >nul
goto :menu

:stop_all
echo.
echo Stopping all services...
call :kill_pids
echo Done.
echo.
echo Press any key to return to menu...
pause >nul
goto :menu

:check_status
cls
echo.
echo   +----------------------------------------+
echo   |           Service Status               |
echo   +----------------------------------------+
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
echo Press any key to return to menu...
pause >nul
goto :menu

:open_browser
start "" "http://localhost:5173"
timeout /t 1 >nul
goto :menu

:restart
echo.
echo Restarting FinanceSim...
call :stop_all
goto :start_local

:exit
call :kill_pids >nul 2>&1
echo.
echo Done.
timeout /t 1 >nul
endlocal
exit /b 0

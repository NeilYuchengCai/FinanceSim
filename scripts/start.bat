@echo off
chcp 65001 >nul
setlocal
:: 从本脚本所在目录推导项目根（scripts\ 的上一级），避免硬编码中文路径
set "ROOT=%~dp0.."
set "PY=C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
set "NODE=C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-6/node.exe"
set "NPM=C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-6/node_modules/npm/bin/npm-cli.js"
set "BE_PORT=8000"
set "FE_PORT=5174"

echo Starting FinanceSim...
echo.

if not exist "%PY%" ( echo [ERROR] python not found: %PY% & pause & exit /b 1 )

:: Start backend in background
cd /d "%ROOT%/backend"
start /B "%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port %BE_PORT% --log-level warning

:: Wait for backend to start
timeout /t 3 /nobreak >nul

if not exist "%NODE%" ( echo [ERROR] node not found: %NODE% & pause & exit /b 1 )

:: Start frontend in background
cd /d "%ROOT%/frontend"
start /B "%NODE%" "%NPM%" run dev -- --port %FE_PORT%

:: Open browser
timeout /t 5 /nobreak >nul
start http://localhost:%FE_PORT%

echo.
echo FinanceSim started!
echo Frontend: http://localhost:%FE_PORT%
echo Backend:  http://localhost:%BE_PORT%
echo.
echo Press any key to exit...
pause >nul

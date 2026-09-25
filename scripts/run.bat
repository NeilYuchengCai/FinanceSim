@echo off
echo ========================================
echo   FinanceSim Starting...
echo ========================================

cd /d "C:/Users/Administrator/Desktop/金融/FinSim/backend"
start "Backend" python -m uvicorn app.main:app --host 127.0.0.1 --port 8080

timeout /t 4 >nul

cd /d "C:/Users/Administrator/Desktop/金融/FinSim/frontend"
start "Frontend" npm run dev -- --port 3000

timeout /t 5 >nul

start http://localhost:3000

echo.
echo ========================================
echo   FinanceSim is running!
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8080
echo.
echo ========================================
pause

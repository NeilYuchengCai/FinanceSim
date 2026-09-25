@echo off
echo Starting FinanceSim...
echo.

:: Start backend in background
cd /d "C:\Users\Administrator\Desktop\金融\FinSim\backend"
start /B python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning

:: Wait for backend to start
timeout /t 3 /nobreak > nul

:: Start frontend in background
cd /d "C:\Users\Administrator\Desktop\金融\FinSim\frontend"
start /B npm run dev

:: Open browser
timeout /t 5 /nobreak > nul
start http://localhost:5173

echo.
echo FinanceSim started!
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo.
echo Press any key to exit...
pause > nul

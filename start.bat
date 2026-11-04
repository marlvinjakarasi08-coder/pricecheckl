@echo off
setlocal
cd /d "%~dp0"

echo Starting PriceCheck backend on port 8000...
start "PriceCheck Backend" cmd /k "cd /d "%~dp0backend" && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) else (py -m venv .venv && call .venv\Scripts\activate.bat && pip install -r requirements.txt) && py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting PriceCheck frontend on port 5173...
start "PriceCheck Frontend" cmd /k "cd /d "%~dp0frontend" && if not exist node_modules (npm install) && npm run dev"

echo.
echo Backend:  http://127.0.0.1:8000/health
echo Frontend: http://127.0.0.1:5173/
echo.
echo Leave both black windows open. Close them to stop the app.
pause

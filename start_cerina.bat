@echo off
setlocal

REM Root folder of the project (this .bat file's directory)
set "PROJECT_ROOT=%~dp0"

echo [Cerina] Starting backend (FastAPI + LangGraph)...
start "Cerina Backend" cmd /k "cd /d "%PROJECT_ROOT%backend" ^&^& call .venv\Scripts\activate.bat ^&^& python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [Cerina] Starting frontend (React + Vite)...
start "Cerina Frontend" cmd /k "cd /d "%PROJECT_ROOT%frontend" ^&^& npm run dev"

REM Give the servers a few seconds to boot, then open the dashboard
timeout /t 7 >nul
echo [Cerina] Opening dashboard in default browser...
start "" "http://localhost:5173/"

endlocal

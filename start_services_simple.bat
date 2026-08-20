@echo off
cd /d C:\GitHub\3A\backend
start /B python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
timeout /t 5 /nobreak >nul
cd /d C:\GitHub\3A\frontend
start /B npx vite --host 127.0.0.1 --port 3000
timeout /t 30 /nobreak >nul
echo ==============================
echo Service Status:
curl -s http://127.0.0.1:8000/health >nul 2>&1 && echo BACKEND: OK || echo BACKEND: DOWN
curl -s -o nul -w "FRONTEND: HTTP %{http_code}\n" http://127.0.0.1:3000
echo ==============================
pause

@echo off
cd /d backend
start "backend" /B python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
start "frontend" /B cmd /c "cd /d C:\GitHub\3A\frontend && npx vite --host 127.0.0.1 --port 3000"
echo Services started.

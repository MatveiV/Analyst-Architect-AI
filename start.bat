@echo off
start /B python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
start /B npx vite --host 127.0.0.1 --port 3000
echo Services started.

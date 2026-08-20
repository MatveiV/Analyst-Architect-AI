@echo off
cd /d C:\GitHub\3A\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > C:\GitHub\3A\backend\server.log 2>&1
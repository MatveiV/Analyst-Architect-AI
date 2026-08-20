Start-Job -Name backend -ScriptBlock { Set-Location $args[0]; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 } -ArgumentList "C:\GitHub\3A\backend"
Start-Job -Name frontend -ScriptBlock { Set-Location $args[0]; npx vite --host 127.0.0.1 --port 3000 } -ArgumentList "C:\GitHub\3A\frontend"
Start-Sleep -Seconds 45
try { Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 10 | Out-Null; Write-Host "BACKEND: OK" } catch { Write-Host "BACKEND: DOWN" }
try { Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 10 -UseBasicParsing | Out-Null; Write-Host "FRONTEND: OK" } catch { Write-Host "FRONTEND: DOWN" }

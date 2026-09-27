# FocusWarmup vertical slice — starts API (:8000) + client (:5173) in separate windows.
# Usage (repo root):  .\dev.ps1
$api = "$PSScriptRoot\services\api"
$client = "$PSScriptRoot\apps\client"

Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$api'; .\.venv\Scripts\python -m uvicorn app.main:app --reload"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$client'; npm run dev"

Write-Host ""
Write-Host "API     → http://localhost:8000  (docs at /docs)"
Write-Host "Client  → http://localhost:5173  (open this one)"
Write-Host "The client shows a clear error banner until the API is up."

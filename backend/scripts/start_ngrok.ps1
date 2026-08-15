# Start PayCrew API + ngrok tunnel
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

# Kill existing on 8000
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "Starting uvicorn on :8000..."
Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "main:app","--host","0.0.0.0","--port","8000" -WorkingDirectory (Get-Location) -WindowStyle Minimized

Start-Sleep -Seconds 3

Write-Host "Starting ngrok..."
Write-Host ""
Write-Host "Send Shresth: https://YOUR-NGROK-URL/v1"
Write-Host ""
ngrok http 8000

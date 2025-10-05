# Development Startup Script
# Starts both backend and frontend in separate terminals

Write-Host "=== Multimodal Insights Application - Development Mode ===" -ForegroundColor Cyan

$repoRoot = Split-Path -Parent $PSScriptRoot

# Start Backend
Write-Host "`nStarting Backend..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$repoRoot\multimodal_insights_app\backend'; .\start.ps1"

# Wait a bit for backend to start
Start-Sleep -Seconds 2

# Start Frontend
Write-Host "`nStarting Frontend..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$repoRoot\multimodal_insights_app\frontend'; npm run dev"

Write-Host "`n=== Application Started ===" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Development Setup Script for Multimodal Insights Application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Multimodal Insights - Full Stack Dev" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to start backend in new terminal
function Start-Backend {
    Write-Host "[Backend] Starting backend server..." -ForegroundColor Yellow
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\start.ps1"
}

# Function to start frontend in new terminal
function Start-Frontend {
    Write-Host "[Frontend] Starting frontend dev server..." -ForegroundColor Blue
    Start-Sleep -Seconds 3  # Wait for backend to start
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; .\start.ps1"
}

# Check if backend dependencies exist
Write-Host "Checking backend setup..." -ForegroundColor Cyan
if (-not (Test-Path "backend\venv")) {
    Write-Host "Backend virtual environment not found. Please run setup first." -ForegroundColor Red
    Write-Host "Run: cd backend; python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check if frontend dependencies exist
Write-Host "Checking frontend setup..." -ForegroundColor Cyan
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Frontend dependencies not found. Installing now..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
}

# Start both servers
Write-Host ""
Write-Host "Starting development servers..." -ForegroundColor Green
Write-Host ""

Start-Backend
Start-Frontend

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Development servers are starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in each terminal to stop servers" -ForegroundColor Gray
Write-Host ""

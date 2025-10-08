#!/usr/bin/env pwsh

# PowerShell start script for Agent Patterns Demo
# This script starts both the backend API and frontend development server

Write-Host "🚀 Starting Agent Patterns Demo" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if Python is installed
try {
    python --version | Out-Null
    Write-Host "✅ Python found" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.8+ and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Node.js is installed
try {
    node --version | Out-Null
    Write-Host "✅ Node.js found" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js is not installed. Please install Node.js 18+ and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if .env file exists
if (-not (Test-Path "backend\.env")) {
    Write-Host "⚠️  Environment file not found. Please copy backend\.env.example to backend\.env and configure your Azure OpenAI credentials." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "📦 Installing backend dependencies..." -ForegroundColor Blue
Set-Location backend

if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
& "venv\Scripts\Activate.ps1"
pip install -r requirements.txt

Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Blue
Set-Location ..\frontend
npm install

Write-Host "🎯 Starting services..." -ForegroundColor Blue

# Start backend
Set-Location ..\backend
& "venv\Scripts\Activate.ps1"
Write-Host "Starting backend on http://localhost:8000" -ForegroundColor Green
$backend = Start-Process python -ArgumentList "api.py" -PassThru -WindowStyle Hidden

# Wait for backend to start
Start-Sleep -Seconds 3

# Start frontend
Set-Location ..\frontend
Write-Host "Starting frontend on http://localhost:5174" -ForegroundColor Green
$frontend = Start-Process npm -ArgumentList "run", "dev" -PassThru -WindowStyle Hidden

Write-Host "✅ Services started successfully!" -ForegroundColor Green
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5174" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

# Function to cleanup processes on exit
$cleanup = {
    Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
    try {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
        Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    } catch {
        # Ignore errors when stopping processes
    }
}

# Register cleanup function
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanup | Out-Null

try {
    # Wait for user to press Ctrl+C
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    & $cleanup
}
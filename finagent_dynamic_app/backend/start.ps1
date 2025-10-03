#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the finagent_dynamic_app backend server

.DESCRIPTION
    Starts the FastAPI backend server with hot reload enabled
#>

Write-Host "Starting Financial Research API - Dynamic Planning" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (!(Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Check if .env exists
if (!(Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Red
    Write-Host "Copy .env.example to .env and configure your settings" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to continue anyway"
}

# Start the server
Write-Host ""
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start both backend and frontend for finagent_dynamic_app

.DESCRIPTION
    Starts the FastAPI backend and React frontend in separate PowerShell windows
#>

Write-Host "=============================================" -ForegroundColor Green
Write-Host "Financial Research - Dynamic Planning" -ForegroundColor Green
Write-Host "Starting Development Environment" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

$ErrorActionPreference = "Stop"

# Check if in correct directory
if (!(Test-Path "backend") -or !(Test-Path "frontend")) {
    Write-Host "ERROR: Must run from finagent_dynamic_app root directory" -ForegroundColor Red
    exit 1
}

# Start backend in new window
Write-Host "Starting Backend Server..." -ForegroundColor Cyan
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd backend; .\start.ps1"

# Wait a moment for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend in new window
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd frontend; .\start.ps1"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "Development servers starting..." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the opened terminal windows for logs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop servers" -ForegroundColor Yellow
Write-Host ""

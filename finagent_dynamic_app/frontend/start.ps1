#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the finagent_dynamic_app frontend

.DESCRIPTION
    Starts the Vite dev server for the React frontend
#>

Write-Host "Starting Financial Research Frontend - Dynamic Planning" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Check if node_modules exists
if (!(Test-Path "node_modules")) {
    Write-Host "Dependencies not installed. Running npm install..." -ForegroundColor Yellow
    npm install
}

Write-Host ""
Write-Host "Starting dev server on http://localhost:5173" -ForegroundColor Green
Write-Host "Make sure backend is running on http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

npm run dev

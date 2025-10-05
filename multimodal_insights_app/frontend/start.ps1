# Quick Start Script for Multimodal Insights Frontend

Write-Host "Starting Multimodal Insights Frontend..." -ForegroundColor Green

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Start development server
Write-Host "Starting Vite development server..." -ForegroundColor Cyan
npm run dev

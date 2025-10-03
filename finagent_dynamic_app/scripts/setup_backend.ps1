# Financial Research Application - Development Scripts

## Backend Setup Script
Write-Host "Setting up Financial Research Backend..." -ForegroundColor Cyan

# Navigate to backend directory
Set-Location -Path "backend"

# Check if virtual environment exists
if (-Not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.template" ".env"
    Write-Host "Please edit .env with your API keys and configuration" -ForegroundColor Red
}

Write-Host "Backend setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the backend server:" -ForegroundColor Cyan
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White

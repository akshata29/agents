# Start script for Advisor Productivity App backend

Write-Host "Starting Advisor Productivity App Backend..." -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env file with your Azure credentials before running." -ForegroundColor Red
    Read-Host "Press Enter to continue or Ctrl+C to exit"
}

# Install/update dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create necessary directories
Write-Host "Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "data" | Out-Null

# Start the application
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host "Backend will be available at http://localhost:8000" -ForegroundColor Cyan
Write-Host "API documentation at http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

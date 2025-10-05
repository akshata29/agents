# Multimodal Insights Backend Startup Script
# Activates virtual environment and starts the FastAPI server

Write-Host "Starting Multimodal Insights Backend..." -ForegroundColor Green

# Check if virtual environment exists
if (!(Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    # Activate virtual environment
    .\venv\Scripts\Activate.ps1
}

# Check if .env file exists
if (!(Test-Path ".env")) {
    Write-Host "Warning: .env file not found. Please create one from .env.example" -ForegroundColor Red
    Write-Host "Press any key to continue anyway..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Start FastAPI server
Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Cyan
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

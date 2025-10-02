# Deep Research App Setup Script
# This script sets up both backend and frontend for the Deep Research application

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Deep Research App Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Get the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$FrameworkDir = Join-Path $RootDir "framework"
$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"

# Function to check if command exists
function Test-Command {
    param($Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
if (-not (Test-Command python)) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
$PythonVersion = python --version
Write-Host "✓ Found: $PythonVersion" -ForegroundColor Green

# Check Node.js
if (-not (Test-Command node)) {
    Write-Host "ERROR: Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}
$NodeVersion = node --version
Write-Host "✓ Found: Node.js $NodeVersion" -ForegroundColor Green

# Check npm
if (-not (Test-Command npm)) {
    Write-Host "ERROR: npm not found. Please install npm" -ForegroundColor Red
    exit 1
}
$NpmVersion = npm --version
Write-Host "✓ Found: npm $NpmVersion" -ForegroundColor Green

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Step 1: Framework Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Install framework
Write-Host "Installing Magentic Foundation Framework..." -ForegroundColor Yellow
Push-Location $FrameworkDir
try {
    python -m pip install -e . --quiet
    Write-Host "✓ Framework installed successfully" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to install framework" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Step 2: Backend Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Install backend dependencies
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
Push-Location $BackendDir
try {
    python -m pip install -r requirements.txt --quiet
    Write-Host "✓ Backend dependencies installed" -ForegroundColor Green
    
    # Create .env if it doesn't exist
    $EnvFile = Join-Path $BackendDir ".env"
    $EnvExample = Join-Path $BackendDir ".env.example"
    if (-not (Test-Path $EnvFile)) {
        Copy-Item $EnvExample $EnvFile
        Write-Host "✓ Created .env file (please configure with your API keys)" -ForegroundColor Yellow
    } else {
        Write-Host "✓ .env file already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: Failed to install backend dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Step 3: Frontend Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Install frontend dependencies
Write-Host "Installing frontend dependencies (this may take a few minutes)..." -ForegroundColor Yellow
Push-Location $FrontendDir
try {
    npm install --quiet
    Write-Host "✓ Frontend dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to install frontend dependencies" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure your environment:" -ForegroundColor White
Write-Host "   Edit backend/.env with your API keys" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start the backend:" -ForegroundColor White
Write-Host "   cd deep_research_app/backend" -ForegroundColor Gray
Write-Host "   python app/main.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Start the frontend (in a new terminal):" -ForegroundColor White
Write-Host "   cd deep_research_app/frontend" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Open your browser:" -ForegroundColor White
Write-Host "   http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "For more information, see:" -ForegroundColor Yellow
Write-Host "   deep_research_app/README.md" -ForegroundColor Gray
Write-Host ""

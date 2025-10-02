# Development Startup Script - Run Both Backend and Frontend

Write-Host "Starting Financial Research Application..." -ForegroundColor Cyan
Write-Host ""

# Get the script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Function to start backend
$BackendJob = Start-Job -ScriptBlock {
    param($ProjectRoot)
    Set-Location "$ProjectRoot\backend"
    & ".\venv\Scripts\Activate.ps1"
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
} -ArgumentList $ProjectRoot

Write-Host "✓ Backend starting on http://localhost:8000" -ForegroundColor Green

# Function to start frontend
$FrontendJob = Start-Job -ScriptBlock {
    param($ProjectRoot)
    Set-Location "$ProjectRoot\frontend"
    npm run dev
} -ArgumentList $ProjectRoot

Write-Host "✓ Frontend starting on http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop both services" -ForegroundColor Yellow
Write-Host ""

# Wait for jobs and show output
try {
    Receive-Job -Job $BackendJob -Wait
    Receive-Job -Job $FrontendJob -Wait
} finally {
    # Cleanup jobs on exit
    Stop-Job -Job $BackendJob, $FrontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $BackendJob, $FrontendJob -ErrorAction SilentlyContinue
    Write-Host "Services stopped" -ForegroundColor Yellow
}

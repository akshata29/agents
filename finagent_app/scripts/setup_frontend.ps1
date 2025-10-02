# Financial Research Application - Frontend Setup Script

Write-Host "Setting up Financial Research Frontend..." -ForegroundColor Cyan

# Navigate to frontend directory
Set-Location -Path "frontend"

# Check if node_modules exists
if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "Node modules already installed. Run 'npm install' to update." -ForegroundColor Yellow
}

Write-Host "Frontend setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the frontend development server:" -ForegroundColor Cyan
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "The app will be available at http://localhost:5173" -ForegroundColor Green

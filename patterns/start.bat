@echo off
REM Start script for Agent Patterns Demo
REM This script starts both the backend API and frontend development server

echo 🚀 Starting Agent Patterns Demo
echo ================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed. Please install Node.js 18+ and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist "backend\.env" (
    echo ⚠️  Environment file not found. Please copy backend\.env.example to backend\.env and configure your Azure OpenAI credentials.
    pause
    exit /b 1
)

echo 📦 Installing backend dependencies...
cd backend
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt

echo 📦 Installing frontend dependencies...
cd ..\frontend
call npm install

echo 🎯 Starting services...

REM Start backend
cd ..\backend
call venv\Scripts\activate.bat
echo Starting backend on http://localhost:8000
start "Backend API" cmd /c "python api.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
cd ..\frontend
echo Starting frontend on http://localhost:5174
start "Frontend Dev Server" cmd /c "npm run dev"

echo ✅ Services started successfully!
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5174
echo.
echo Press any key to open frontend in browser...
pause >nul
start http://localhost:5174
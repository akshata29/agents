#!/bin/bash

# Start script for Agent Patterns Demo
# This script starts both the backend API and frontend development server

echo "🚀 Starting Agent Patterns Demo"
echo "================================"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Environment file not found. Please copy backend/.env.example to backend/.env and configure your Azure OpenAI credentials."
    exit 1
fi

echo "📦 Installing backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
pip install -r requirements.txt

echo "📦 Installing frontend dependencies..."
cd ../frontend
npm install

echo "🎯 Starting services..."

# Start backend in background
cd ../backend
source venv/bin/activate
echo "Starting backend on http://localhost:8000"
python api.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
cd ../frontend
echo "Starting frontend on http://localhost:5174"
npm run dev &
FRONTEND_PID=$!

echo "✅ Services started successfully!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5174"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup processes on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Trap Ctrl+C
trap cleanup INT

# Wait for processes
wait
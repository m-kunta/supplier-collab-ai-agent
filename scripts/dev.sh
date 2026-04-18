#!/usr/bin/env bash
# scripts/dev.sh
# Starts both the FastAPI backend and Next.js frontend for local development

echo "=========================================================="
echo "🚀 Starting Supplier Collab AI Agent - Dev Environment"
echo "=========================================================="

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment '.venv' not found."
    echo "Please run 'make setup' first."
    exit 1
fi

# Function to clean up background processes on exit
cleanup() {
    echo -e "\n🛑 Stopping development servers..."
    kill $API_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    echo "👋 Servers stopped."
    exit 0
}

# Trap termination signals to run cleanup
trap cleanup SIGINT SIGTERM EXIT

echo "🟢 [1/2] Starting FastAPI backend on http://127.0.0.1:8000..."
source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &
API_PID=$!

echo "🟢 [2/2] Starting Next.js frontend on http://localhost:3000..."
cd frontend
npm run dev > /dev/null 2>&1 &
UI_PID=$!

cd ..

echo "=========================================================="
echo "✅ Services are running!"
echo "   - Frontend UI:  http://localhost:3000"
echo "   - Backend API:  http://127.0.0.1:8000"
echo "   - API Docs:     http://127.0.0.1:8000/docs"
echo "   Press Ctrl+C to stop both servers."
echo "=========================================================="

# Wait indefinitely (until interrupted by user)
wait

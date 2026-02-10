#!/bin/bash
# 🚀 deploy_all_services.sh - Deploy all MonitoringAlert services to EC2

set -e

echo "================================"
echo "🚀 MonitoringAlert Deployment"
echo "================================"

# Check if running on EC2
if [ ! -d "$HOME/MonitoringAlert" ]; then
    echo "❌ Directory ~/MonitoringAlert not found!"
    echo "Please clone the repository first:"
    echo "  git clone https://github.com/tipseetroy-code/MonitoringAlert ~/MonitoringAlert"
    exit 1
fi

cd ~/MonitoringAlert

echo ""
echo "📦 Step 1: Pull latest code..."
git pull origin main
echo "✅ Code pulled successfully"

echo ""
echo "📦 Step 2: Activate virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "✅ Virtual environment activated"

echo ""
echo "📦 Step 3: Install/update dependencies..."
pip3 install -q -r backend/requirements.txt
echo "✅ Dependencies installed"

echo ""
echo "🔑 Step 4: Check GOOGLE_API_KEY..."
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not set!"
    echo "Please set it before starting services:"
    echo "  export GOOGLE_API_KEY='your-api-key-here'"
    read -p "Enter GOOGLE_API_KEY: " GOOGLE_API_KEY
    export GOOGLE_API_KEY="$GOOGLE_API_KEY"
fi
echo "✅ API key configured"

echo ""
echo "================================"
echo "🤖 Starting Services..."
echo "================================"

# Create log directory
mkdir -p logs

# Kill any existing processes on these ports
for port in 8000 8001 8501; do
    PID=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo "Stopping service on port $port..."
        kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
done

echo ""
echo "📌 Starting services..."
echo ""

# Start Autonomous Agent Server
echo "🤖 Starting Autonomous Agent Server (port 8001)..."
nohup python3 -m uvicorn backend.api.agent_server:app \
    --host 0.0.0.0 --port 8001 \
    > logs/agent_server.log 2>&1 &
AGENT_PID=$!
echo "✅ Agent Server PID: $AGENT_PID"

sleep 2

# Start Copilot KB API
echo "🧠 Starting Copilot KB API (port 8000)..."
nohup python3 -m uvicorn backend.api.copilot_kb_api:app \
    --host 0.0.0.0 --port 8000 \
    > logs/copilot_kb_api.log 2>&1 &
KB_PID=$!
echo "✅ Copilot KB API PID: $KB_PID"

sleep 2

# Start Streamlit Dashboard
echo "📱 Starting Streamlit Dashboard (port 8501)..."
nohup python3 -m streamlit run frontend/perception_and_action_hub.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "✅ Streamlit PID: $STREAMLIT_PID"

sleep 3

echo ""
echo "================================"
echo "✅ All Services Started!"
echo "================================"
echo ""
echo "📊 Service URLs:"
echo "  🤖 Agent Server:        http://18.237.102.97:8001"
echo "  🧠 Copilot KB API:      http://18.237.102.97:8000"
echo "  📱 Streamlit Dashboard: http://18.237.102.97:8501"
echo ""
echo "📋 Process IDs:"
echo "  Agent Server:  $AGENT_PID"
echo "  Copilot KB:    $KB_PID"
echo "  Streamlit:     $STREAMLIT_PID"
echo ""
echo "📝 Log files:"
echo "  logs/agent_server.log"
echo "  logs/copilot_kb_api.log"
echo "  logs/streamlit.log"
echo ""
echo "💡 View logs: tail -f logs/*.log"
echo "🛑 Stop all:  killall python3"
echo ""

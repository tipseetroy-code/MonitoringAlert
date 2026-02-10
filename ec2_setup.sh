#!/bin/bash
# EC2 Setup Script for Copilot KB API & Streamlit App
# Run this on your EC2 instance

set -e

echo "🚀 Setting up Copilot KB API & Streamlit on EC2..."
echo ""

# ==================== STEP 1: Update System ====================
echo "📦 Step 1: Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ==================== STEP 2: Install Python & Pip ====================
echo "🐍 Step 2: Installing Python3 and pip3..."
sudo apt-get install -y python3 python3-pip python3-venv

# Verify installation
echo "✅ Verifying Python installation:"
python3 --version
pip3 --version

# ==================== STEP 3: Navigate to Project ====================
echo ""
echo "📁 Step 3: Navigating to project..."
if [ ! -d "$HOME/MonitoringAlert" ]; then
    echo "❌ MonitoringAlert directory not found at $HOME/MonitoringAlert"
    echo "Please clone the repository first:"
    echo "  git clone <repo-url> ~/MonitoringAlert"
    exit 1
fi

cd ~/MonitoringAlert
echo "✅ Working directory: $(pwd)"

# ==================== STEP 4: Create Virtual Environment ====================
echo ""
echo "🔧 Step 4: Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment activated"

# ==================== STEP 5: Install Dependencies ====================
echo ""
echo "📚 Step 5: Installing Python dependencies..."
pip3 install -r backend/requirements.txt
echo "✅ Dependencies installed"

# ==================== STEP 6: Set Environment Variables ====================
echo ""
echo "🔑 Step 6: Setting environment variables..."
echo ""
echo "⚠️  You need to set your Google API key. Do one of:"
echo ""
echo "Option A - Set in current session:"
echo "  export GOOGLE_API_KEY='your-gemini-api-key-here'"
echo ""
echo "Option B - Add to ~/.bashrc (persistent):"
echo "  echo \"export GOOGLE_API_KEY='your-gemini-api-key-here'\" >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""
echo "Option C - Create .env file:"
echo "  echo \"GOOGLE_API_KEY=your-gemini-api-key-here\" > .env"
echo ""

# ==================== STEP 7: Start Copilot KB API ====================
echo ""
echo "🤖 Step 7: Starting Copilot KB API..."
echo ""
echo "Starting API on port 8000..."

# Create a separate log file for the API
touch kb_api.log

# Run in background with nohup
nohup python3 -m uvicorn backend.api.copilot_kb_api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 > kb_api.log 2>&1 &

KB_PID=$!
echo "✅ Copilot KB API started (PID: $KB_PID)"
echo "📝 Logs: $(pwd)/kb_api.log"

# Wait for API to start
sleep 3

# Verify API is running
echo ""
echo "🔍 Verifying API health..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is healthy!"
    curl http://localhost:8000/health
else
    echo "⏳ API starting, give it a moment..."
    sleep 3
    curl http://localhost:8000/health
fi

# ==================== STEP 8: Start Streamlit App ====================
echo ""
echo "📊 Step 8: Starting Streamlit application..."
echo ""
echo "Starting Streamlit on port 8501..."

# Create a separate log file for Streamlit
touch streamlit.log

# Run in background
nohup python3 -m streamlit run frontend/perception_and_action_hub.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --logger.level=info > streamlit.log 2>&1 &

STREAMLIT_PID=$!
echo "✅ Streamlit started (PID: $STREAMLIT_PID)"
echo "📝 Logs: $(pwd)/streamlit.log"

# ==================== STEP 9: Display Access Information ====================
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ SETUP COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📋 Service Status:"
echo "  🤖 Copilot KB API: http://localhost:8000 (PID: $KB_PID)"
echo "  📊 Streamlit App:  http://localhost:8501 (PID: $STREAMLIT_PID)"
echo ""
echo "🌐 Access from your browser:"
echo "  Streamlit:        http://$(hostname -I | awk '{print $1}'):8501"
echo "  API Health:       http://$(hostname -I | awk '{print $1}'):8000/health"
echo ""
echo "📝 Log Files:"
echo "  API Logs:     ~/MonitoringAlert/kb_api.log"
echo "  Streamlit:    ~/MonitoringAlert/streamlit.log"
echo ""
echo "🛠️  Useful Commands:"
echo "  View API logs:       tail -f kb_api.log"
echo "  View Streamlit logs: tail -f streamlit.log"
echo "  Stop API:            kill $KB_PID"
echo "  Stop Streamlit:      kill $STREAMLIT_PID"
echo "  Stop all:            pkill -f 'uvicorn|streamlit'"
echo ""
echo "⚠️  IMPORTANT:"
echo "  1. Set GOOGLE_API_KEY before API will work fully"
echo "  2. Check logs if services don't start"
echo "  3. Ensure security group allows ports 8000 and 8501"
echo ""
echo "════════════════════════════════════════════════════════════"


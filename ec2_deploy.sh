#!/bin/bash
# EC2 Deployment Script for Confluence Integration
# Run this on EC2 instance: 18.237.102.97

echo "=== Pulling latest code from GitHub ==="
cd /root/MonitoringAlert || cd ~/MonitoringAlert || { echo "MonitoringAlert directory not found"; exit 1; }
git pull origin main

echo ""
echo "=== Setting Confluence environment variables ==="
export CONFLUENCE_USER="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-token-here"
export CONFLUENCE_BASE_URL="https://teammeenakshi.atlassian.net"

# Optional: Save to .env file for persistence
cat > .env << 'EOF'
CONFLUENCE_USER=your-email@company.com
CONFLUENCE_API_TOKEN=your-token-here
CONFLUENCE_BASE_URL=https://teammeenakshi.atlassian.net
EOF

echo "Environment variables set"

echo ""
echo "=== Stopping existing Streamlit process ==="
pkill -f "streamlit run" || echo "No existing Streamlit process found"
sleep 2

echo ""
echo "=== Starting Streamlit with Confluence integration ==="
nohup streamlit run frontend/perception_and_action_hub.py --server.address 0.0.0.0 --server.port 8501 > streamlit.log 2>&1 &

echo ""
echo "=== Waiting for Streamlit to start ==="
sleep 5

echo ""
echo "=== Checking Streamlit status ==="
if curl -s http://localhost:8501 > /dev/null; then
    echo "✅ Streamlit is running successfully!"
    echo "Access dashboard at: http://18.237.102.97:8501"
else
    echo "❌ Streamlit failed to start. Check logs:"
    tail -n 20 streamlit.log
fi

echo ""
echo "=== Current Streamlit processes ==="
ps aux | grep streamlit | grep -v grep

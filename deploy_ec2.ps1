# 🚀 EC2 Deployment Script for MonitoringAlert
# Run this to deploy all changes to EC2

param(
    [string]$EC2_IP = "18.237.102.97",
    [string]$EC2_USER = "ubuntu",
    [string]$KEY_PATH = "your-ec2-key.pem"
)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "🚀 MonitoringAlert EC2 Deployment" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify connectivity
Write-Host "📌 Step 1: Checking EC2 connectivity..." -ForegroundColor Yellow
$testConnection = ssh -i $KEY_PATH -o ConnectTimeout=5 ${EC2_USER}@${EC2_IP} "echo OK" 2>$null
if ($testConnection -ne "OK") {
    Write-Host "❌ Cannot connect to EC2. Check:" -ForegroundColor Red
    Write-Host "  - EC2 IP: $EC2_IP"
    Write-Host "  - Key path: $KEY_PATH"
    Write-Host "  - Security group allows SSH (port 22)"
    exit 1
}
Write-Host "✅ Connected to $EC2_IP" -ForegroundColor Green
Write-Host ""

# Step 2: Pull latest code
Write-Host "📌 Step 2: Pulling latest code..." -ForegroundColor Yellow
ssh -i $KEY_PATH ${EC2_USER}@${EC2_IP} "cd ~/MonitoringAlert && git pull origin main" | Out-String
Write-Host "✅ Code pulled" -ForegroundColor Green
Write-Host ""

# Step 3: Get API Key
Write-Host "📌 Step 3: API Key Configuration..." -ForegroundColor Yellow
$apiKey = Read-Host "Enter GOOGLE_API_KEY (or press Enter to skip)"
if ($apiKey) {
    Write-Host "Setting API key on EC2..." -ForegroundColor Cyan
    ssh -i $KEY_PATH ${EC2_USER}@${EC2_IP} "echo 'export GOOGLE_API_KEY=$apiKey' >> ~/.bashrc && source ~/.bashrc" 2>$null
    Write-Host "✅ API key configured" -ForegroundColor Green
} else {
    Write-Host "⚠️  Skipped API key (you must set it manually on EC2)" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Deploy services
Write-Host "📌 Step 4: Deploying services..." -ForegroundColor Yellow
Write-Host "Running deploy script on EC2..." -ForegroundColor Cyan

ssh -i $KEY_PATH ${EC2_USER}@${EC2_IP} @"
    cd ~/MonitoringAlert
    source venv/bin/activate 2>/dev/null
    
    # Install dependencies
    pip3 install -q -r backend/requirements.txt
    
    # Create logs directory
    mkdir -p logs
    
    # Kill existing services
    pkill -f "uvicorn.*8001" 2>/dev/null || true
    pkill -f "uvicorn.*8000" 2>/dev/null || true
    pkill -f "streamlit run" 2>/dev/null || true
    sleep 2
    
    # Start Agent Server
    export GOOGLE_API_KEY=$apiKey
    nohup python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001 > logs/agent_server.log 2>&1 &
    sleep 1
    
    # Start Copilot KB API
    nohup python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000 > logs/copilot_kb_api.log 2>&1 &
    sleep 1
    
    # Start Streamlit
    nohup python3 -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
    sleep 2
    
    echo "Services started. Checking status..."
    curl -s http://localhost:8001/ | grep -q "Autonomous Agent Server" && echo "✅ Agent Server running" || echo "⚠️  Agent Server check failed"
    curl -s http://localhost:8000/health | grep -q "running" && echo "✅ Copilot KB API running" || echo "⚠️  Copilot KB check failed"
"@

Write-Host "✅ Services deployed" -ForegroundColor Green
Write-Host ""

Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Access your services:" -ForegroundColor Green
Write-Host "  🤖 Agent Server:        http://$EC2_IP:8001" -ForegroundColor Cyan
Write-Host "  🧠 Copilot KB API:      http://$EC2_IP:8000" -ForegroundColor Cyan
Write-Host "  📱 Streamlit Dashboard: http://$EC2_IP:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Verify deployment:" -ForegroundColor Green
Write-Host "  curl http://$EC2_IP:8001/api/agents/status" -ForegroundColor Yellow
Write-Host "  curl http://$EC2_IP:8000/health" -ForegroundColor Yellow
Write-Host ""

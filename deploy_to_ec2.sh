#!/bin/bash
# Quick deployment script for Agentic SRE Copilot on EC2
# Run this from your local machine

set -e

# Configuration
EC2_HOST="18.237.102.97"
EC2_USER="ubuntu"
PEM_KEY="c:\Users\KF879ZY\Downloads\Team Meenakshi.pem"
REMOTE_PATH="/root/MonitoringAlert"

echo "=========================================="
echo "Agentic SRE Copilot - EC2 Deployment"
echo "=========================================="
echo ""

# Get API key from user
read -sp "Enter your Google Gemini API Key: " GOOGLE_API_KEY
echo ""

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: Google API Key is required"
    exit 1
fi

echo ""
echo "📡 Connecting to EC2 instance..."

# Deploy via SSH
ssh -i "$PEM_KEY" ${EC2_USER}@${EC2_HOST} sudo -i bash << ENDSSH
set -e

echo "✅ Connected to EC2"
echo ""

# Navigate to project
cd ${REMOTE_PATH}
echo "📂 Working directory: \$(pwd)"
echo ""

# Create environment file
echo "🔑 Configuring API key..."
cat > /root/.sre-agent.env << 'EOF'
# Google Gemini API Key
GOOGLE_API_KEY=${GOOGLE_API_KEY}

# Optional: Add JIRA credentials
# JIRA_URL=https://your-company.atlassian.net
# JIRA_USERNAME=your-email@company.com
# JIRA_API_TOKEN=your-jira-api-token

# Optional: Add SMTP credentials
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-smtp-password
# SMTP_FROM=sre-agent@company.com
# SMTP_TO=oncall@company.com
EOF
chmod 600 /root/.sre-agent.env
echo "✅ Environment file created"
echo ""

# Update systemd service
echo "⚙️ Updating systemd service..."
cat > /etc/systemd/system/sre-agent.service << 'EOF'
[Unit]
Description=SRE Agentic Copilot - Autonomous Incident Management
After=network.target
Documentation=https://github.com/tipseetroy-code/MonitoringAlert

[Service]
Type=simple
User=root
WorkingDirectory=/root/MonitoringAlert
Environment="PYTHONPATH=/root/MonitoringAlert"
EnvironmentFile=/root/.sre-agent.env
ExecStart=/usr/bin/python3 /root/MonitoringAlert/backend/agentic/run_agentic.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/sre-agent/agentic.log
StandardError=append:/var/log/sre-agent/agentic.log

# Security
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/sre-agent /var/log/sre-agent

[Install]
WantedBy=multi-user.target
EOF
echo "✅ Systemd service updated"
echo ""

# Reload and start
echo "🚀 Starting SRE Agent service..."
systemctl daemon-reload
systemctl enable sre-agent
systemctl restart sre-agent
sleep 2
echo "✅ Service started"
echo ""

# Check status
echo "📊 Service Status:"
systemctl status sre-agent --no-pager -l || true
echo ""

# Show recent logs
echo "📋 Recent Logs:"
journalctl -u sre-agent -n 15 --no-pager || true
echo ""

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "📍 Next Steps:"
echo "  1. Check logs: journalctl -u sre-agent -f"
echo "  2. View status: systemctl status sre-agent"
echo "  3. Configure apps in: ${REMOTE_PATH}/backend/config/agentic_config.py"
echo "  4. View memory: cat /var/lib/sre-agent/incident_memory.json"
echo ""
ENDSSH

echo ""
echo "🎉 Deployment script completed!"
echo ""

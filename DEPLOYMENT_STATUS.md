# ✅ AGENTIC SRE COPILOT - EC2 DEPLOYMENT STATUS

**Deployment Date**: February 9, 2026  
**EC2 Instance**: 18.237.102.97  
**Deployment Path**: `/root/MonitoringAlert`  
**Status**: **DEPLOYED ✅** (Pending API keys configuration)

---

## 📦 What Has Been Deployed

### 1. Code Deployed ✅
- **GitHub Repository**: https://github.com/tipseetroy-code/MonitoringAlert
- **Commit**: ca4f903 (17 files, 6,256 insertions)
- **Components Deployed**:
  - 8 Python modules (core, perception, reasoning, executor, jira, notifications, audit, orchestrator)
  - 5 documentation files (2,100+ lines)
  - Systemd service file
  - Configuration template

### 2. Dependencies Installed ✅
```bash
✅ Python 3.12.3
✅ fastapi
✅ uvicorn
✅ python-dotenv
✅ google-genai (1.62.0)
✅ psutil
✅ requests
✅ streamlit (1.54.0)
✅ All transitive dependencies (numpy, pandas, pydantic, etc.)
```

### 3. Directory Structure Created ✅
```
/root/MonitoringAlert/
├── backend/
│   ├── agentic/                    ✅ 8 core modules
│   │   ├── __init__.py
│   │   ├── core.py                 (Agentic loop)
│   │   ├── perception.py           (Signal collection)
│   │   ├── reasoning.py            (LLM reasoning)
│   │   ├── executor.py             (Safe actions)
│   │   ├── jira_integration.py     (JIRA API)
│   │   ├── notifications.py        (SMTP alerts)
│   │   ├── audit.py                (Compliance)
│   │   ├── orchestrator.py         (Main coordinator)
│   │   └── run_agentic.py          (Entry point)
│   └── config/
│       ├── __init__.py
│       ├── agentic_config.py       ✅ Active config
│       └── agentic_config.example.py
├── etc/systemd/system/
│   └── sre-agent.service           ✅ Service file
├── AGENTIC_ARCHITECTURE.md         ✅ Architecture guide
├── DEPLOYMENT_QUICK_START.md       ✅ Deployment guide
├── README_AGENTIC.md               ✅ README
├── IMPLEMENTATION_SUMMARY.md       ✅ Summary
└── VISUAL_ARCHITECTURE.md          ✅ Visual diagrams

/var/lib/sre-agent/                 ✅ Storage directory (memory + audit DB)
/var/log/sre-agent/                 ✅ Log directory
/etc/systemd/system/sre-agent.service  ✅ Systemd service installed
```

### 4. Systemd Service Configured ✅
```bash
✅ Service file: /etc/systemd/system/sre-agent.service
✅ Status: Loaded (disabled, not started yet)
✅ Auto-restart: Configured (on-failure)
✅ Working directory: /root/MonitoringAlert
```

---

## ⚠️ REQUIRED NEXT STEPS (Manual Configuration Needed)

### 🔑 Step 1: Set API Keys & Credentials

**SSH to EC2**:
```bash
ssh -i "c:\Users\KF879ZY\Downloads\Team Meenakshi.pem" ubuntu@18.237.102.97
sudo -i
cd /root/MonitoringAlert
```

**Create environment file** (`.env` or export):
```bash
# Create .env file
cat > /root/.sre-agent.env << 'EOF'
# Google Gemini API Key (REQUIRED for LLM reasoning)
GOOGLE_API_KEY=your-google-gemini-api-key-here

# JIRA Credentials (Optional - for escalations)
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# SMTP Credentials (Optional - for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=sre-agent@company.com
SMTP_TO=oncall@company.com,team@company.com
EOF

# Make it secure
chmod 600 /root/.sre-agent.env
```

**Update systemd service to load .env file**:
```bash
# Edit the service file
nano /etc/systemd/system/sre-agent.service

# Add this line under [Service] section:
EnvironmentFile=/root/.sre-agent.env

# Reload systemd
systemctl daemon-reload
```

---

### 📝 Step 2: Configure Monitoring Targets

Edit `/root/MonitoringAlert/backend/config/agentic_config.py`:

```python
# Update the apps to monitor
APPS_TO_MONITOR = [
    {
        "name": "your-api-service",
        "health_url": "http://localhost:8000/health",    # Your actual endpoint
        "log_path": "/var/log/your-app/app.log",        # Your actual log file
        "systemd_service": "your-service.service"        # Your actual service name
    },
    {
        "name": "another-service",
        "health_url": "http://localhost:8080/health",
        "log_path": "/var/log/another-app/app.log",
        "systemd_service": "another-service.service"
    }
]

# Update policy thresholds (optional)
POLICY_CONFIG = {
    "allow_auto_restart": True,              # Allow automatic restarts
    "max_restarts_per_day": 5,               # Rate limit
    "require_approval_for_critical": True,   # Require approval for CRITICAL
    "change_window_start": "09:00",          # Change window 9 AM - 5 PM UTC
    "change_window_end": "17:00",
    "escalation_threshold": 3                # Escalate after 3 incidents in 60 min
}
```

---

### 🚀 Step 3: Start the Service

```bash
# Enable the service to start on boot
systemctl enable sre-agent

# Start the service
systemctl start sre-agent

# Check status
systemctl status sre-agent

# View logs
journalctl -u sre-agent -f

# Or tail the log file
tail -f /var/log/sre-agent/agentic.log
```

---

## 🧪 Testing the Deployment

### Test 1: Manual Run (Quick Test)
```bash
cd /root/MonitoringAlert
export PYTHONPATH=/root/MonitoringAlert
export GOOGLE_API_KEY=your-key-here
python3 backend/agentic/run_agentic.py
```

**Expected Output**:
```
2026-02-09 XX:XX:XX - __main__ - INFO - SRE Agentic Copilot Starting
2026-02-09 XX:XX:XX - __main__ - INFO - Configuration loaded: 3 apps to monitor
2026-02-09 XX:XX:XX - backend.agentic.orchestrator - INFO - [ORCHESTRATOR] Initializing...
2026-02-09 XX:XX:XX - backend.agentic.orchestrator - INFO - [ORCHESTRATOR] Started successfully
2026-02-09 XX:XX:XX - backend.agentic.perception - INFO - [PERCEPTION] Collecting signals...
```

### Test 2: Check Perception Engine
```bash
# SSH to EC2
cd /root/MonitoringAlert
export PYTHONPATH=/root/MonitoringAlert
python3 -c "
from backend.agentic.orchestrator import SREAgentOrchestrator
orchestrator = SREAgentOrchestrator()
signals = orchestrator.test_perception()
print(f'Collected {len(signals)} signals')
for s in signals:
    print(f'  - {s.app}: {s.status} ({s.source})')
"
```

### Test 3: Verify API Access
```bash
# Test Gemini API
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

---

## 📊 Monitoring the Agent

### View Real-Time Logs
```bash
# Systemd logs (structured)
journalctl -u sre-agent -f

# Application logs (detailed)
tail -f /var/log/sre-agent/agentic.log

# Search for specific events
grep "INCIDENT DETECTED" /var/log/sre-agent/agentic.log
grep "ACTION EXECUTED" /var/log/sre-agent/agentic.log
grep "RESOLVED" /var/log/sre-agent/agentic.log
```

### Check Incident Memory
```bash
cat /var/lib/sre-agent/incident_memory.json | python3 -m json.tool
```

### Query Audit Database
```bash
sqlite3 /var/lib/sre-agent/sre_audit.db "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 10;"
```

### Check Service Status
```bash
systemctl status sre-agent
ps aux | grep run_agentic.py
```

---

## 🔄 Updating the Code

When you make changes and push to GitHub:

```bash
# SSH to EC2
ssh -i "c:\Users\KF879ZY\Downloads\Team Meenakshi.pem" ubuntu@18.237.102.97
sudo -i
cd /root/MonitoringAlert

# Pull latest code
git pull origin main

# Restart the service
systemctl restart sre-agent

# Verify it's running
systemctl status sre-agent
journalctl -u sre-agent -n 50
```

---

## 🐛 Troubleshooting

### Issue 1: Service Won't Start
```bash
# Check logs for errors
journalctl -u sre-agent -n 100 --no-pager

# Common issues:
# - GOOGLE_API_KEY not set → Add to .env file
# - Module import errors → Check PYTHONPATH in service file
# - Permission errors → Check ownership of /var/lib/sre-agent
```

### Issue 2: No Incidents Detected
```bash
# Test perception manually
cd /root/MonitoringAlert
export PYTHONPATH=/root/MonitoringAlert
python3 -c "
from backend.agentic.perception import PerceptionEngine
from backend.config.agentic_config import APPS_TO_MONITOR
engine = PerceptionEngine(APPS_TO_MONITOR)
signals = engine.collect_all_signals()
print(f'Collected {len(signals)} signals')
"

# Check configuration
cat backend/config/agentic_config.py | grep -A 10 APPS_TO_MONITOR
```

### Issue 3: LLM Reasoning Fails
```bash
# Verify API key
echo $GOOGLE_API_KEY

# Test Gemini API directly
python3 -c "
import google.genai as genai
genai.configure(api_key='YOUR_KEY')
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content('Test')
print(response.text)
"
```

### Issue 4: Actions Not Executing
```bash
# Check policy configuration
cat backend/config/agentic_config.py | grep -A 10 POLICY_CONFIG

# Verify service has sudo permissions (if needed)
grep User /etc/systemd/system/sre-agent.service  # Should be root

# Check action logs
grep "ACTION EXECUTED" /var/log/sre-agent/agentic.log
grep "POLICY GATE" /var/log/sre-agent/agentic.log
```

---

## 📈 Next Steps (Integration with Streamlit)

### Add Agentic Tab to Streamlit UI

**File**: `/root/MonitoringAlert/frontend/app.py`

```python
# Add new tab
tabs = st.tabs([
    "🏠 Home",
    "🔍 SSL Monitoring",
    "📊 App Health",
    "🤖 Agentic Copilot",  # NEW TAB
    "⚙️ Settings"
])

with tabs[3]:  # Agentic Copilot tab
    st.title("🤖 Agentic SRE Copilot")
    
    from backend.agentic.orchestrator import SREAgentOrchestrator
    orchestrator = SREAgentOrchestrator()
    
    # Display monitoring status
    status = orchestrator.get_monitoring_status()
    st.metric("Status", status["status"])
    st.metric("Uptime", status["uptime"])
    st.metric("Total Incidents", status["total_incidents"])
    
    # Recent incidents
    st.subheader("Recent Incidents")
    incidents = orchestrator.get_recent_incidents(limit=10)
    for inc in incidents:
        with st.expander(f"{inc['app']} - {inc['severity']} - {inc['status']}"):
            st.write(f"**Description**: {inc['description']}")
            st.write(f"**Detected**: {inc['detected_at']}")
            if inc['status'] == 'RESOLVED':
                st.write(f"**MTTR**: {inc['mttr_seconds']}s")
    
    # Performance metrics
    st.subheader("Performance Metrics")
    metrics = orchestrator.get_performance_metrics()
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg MTTR", f"{metrics['avg_mttr_seconds']}s")
    col2.metric("Success Rate", f"{metrics['success_rate']}%")
    col3.metric("Total Actions", metrics['total_actions'])
```

---

## 🎯 Summary

### ✅ What's Working
- Code deployed to EC2 ✅
- All dependencies installed ✅
- Directory structure created ✅
- Systemd service configured ✅
- Configuration file ready ✅

### ⏳ What's Pending (Manual Steps)
1. **Set GOOGLE_API_KEY** (required for LLM reasoning)
2. **Configure JIRA credentials** (optional, for escalations)
3. **Configure SMTP credentials** (optional, for notifications)
4. **Update monitoring targets** in `agentic_config.py`
5. **Start the service** with `systemctl start sre-agent`
6. **Test and validate** the deployment

### 📚 Documentation Available
- [AGENTIC_ARCHITECTURE.md](AGENTIC_ARCHITECTURE.md) - Complete architecture
- [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md) - Detailed deployment guide
- [README_AGENTIC.md](README_AGENTIC.md) - Usage guide
- [VISUAL_ARCHITECTURE.md](VISUAL_ARCHITECTURE.md) - Visual diagrams
- **THIS FILE** - Deployment status & next steps

---

## 🚀 Quick Start Command

```bash
# Complete deployment in one go:
ssh -i "c:\Users\KF879ZY\Downloads\Team Meenakshi.pem" ubuntu@18.237.102.97 << 'ENDSSH'
sudo -i bash << 'ENDROOT'
# 1. Set API key
export GOOGLE_API_KEY="your-google-api-key-here"
echo "export GOOGLE_API_KEY=$GOOGLE_API_KEY" >> /root/.bashrc

# 2. Update service file with environment
cat >> /etc/systemd/system/sre-agent.service << 'EOF'
Environment="GOOGLE_API_KEY=your-google-api-key-here"
Environment="PYTHONPATH=/root/MonitoringAlert"
EOF

# 3. Start service
systemctl daemon-reload
systemctl enable sre-agent
systemctl start sre-agent

# 4. Check status
systemctl status sre-agent
journalctl -u sre-agent -n 20
ENDROOT
ENDSSH
```

**Replace `your-google-api-key-here` with your actual Gemini API key!**

---

## 📞 Support

For issues or questions:
- Check logs: `/var/log/sre-agent/agentic.log`
- Review documentation in the repo
- Check systemd status: `systemctl status sre-agent`
- GitHub repo: https://github.com/tipseetroy-code/MonitoringAlert

---

**Deployment completed by GitHub Copilot on February 9, 2026** 🎉

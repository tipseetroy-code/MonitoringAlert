# QUICK START: Deploy Agentic SRE Copilot

## Step 1: Prepare Environment Variables

Create `.env` file in `/root/MonitoringAlert/`:

```bash
# Google Gemini API
export GOOGLE_API_KEY="your-gemini-api-key"

# JIRA
export JIRA_BASE_URL="https://yourcompany.atlassian.net"
export JIRA_USER_EMAIL="sre-bot@company.com"
export JIRA_API_TOKEN="your-jira-api-token"
export JIRA_PROJECT_KEY="OPS"

# SMTP
export SMTP_SERVER="smtp.company.com"
export SMTP_PORT="587"
export SMTP_FROM="sre-agent@company.com"
export SMTP_USERNAME="sre-agent@company.com"
export SMTP_PASSWORD="your-password"

# Storage
export MEMORY_PATH="/var/lib/sre-agent/incident_memory.json"
export AUDIT_DB_PATH="/var/lib/sre-agent/sre_audit.db"
export LOG_FILE="/var/log/sre-agent/agentic.log"
```

## Step 2: Create Directories

```bash
sudo mkdir -p /var/lib/sre-agent /var/log/sre-agent
sudo mkdir -p /root/MonitoringAlert/backend/config
sudo mkdir -p /etc/sre-agent
sudo chown -R ubuntu:ubuntu /var/lib/sre-agent /var/log/sre-agent
sudo chmod 755 /var/lib/sre-agent /var/log/sre-agent
```

## Step 3: Copy Configuration

```bash
# From your local machine to EC2
scp -i "Team Meenakshi.pem" backend/config/agentic_config.py \
    ubuntu@18.237.102.97:/tmp/

# On EC2
sudo cp /tmp/agentic_config.py /root/MonitoringAlert/backend/config/
```

## Step 4: Install Systemd Service

```bash
# Copy systemd service file
sudo cp etc/systemd/system/sre-agent.service /etc/systemd/system/

# Create environment file for systemd
sudo bash -c 'cat > /etc/sre-agent/sre-agent.env << EOF
GOOGLE_API_KEY=your-key
JIRA_BASE_URL=your-url
JIRA_USER_EMAIL=your-email
JIRA_API_TOKEN=your-token
JIRA_PROJECT_KEY=OPS
SMTP_SERVER=smtp.company.com
SMTP_PORT=587
SMTP_FROM=sre-agent@company.com
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
MEMORY_PATH=/var/lib/sre-agent/incident_memory.json
AUDIT_DB_PATH=/var/lib/sre-agent/sre_audit.db
LOG_FILE=/var/log/sre-agent/agentic.log
EOF'

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable sre-agent.service
sudo systemctl start sre-agent.service

# Check status
sudo systemctl status sre-agent.service
```

## Step 5: Verify Deployment

```bash
# Check service is running
sudo systemctl status sre-agent.service

# Watch logs
tail -f /var/log/sre-agent/agentic.log

# Check audit database
ls -la /var/lib/sre-agent/

# Verify in Streamlit UI
# Navigate to http://18.237.102.97:8501
# Check "Agentic Copilot" tab
# Click "Test Perception" to collect signals
```

## Step 6: Test Integration with Streamlit

In `frontend/app.py`, add new tab:

```python
if tabs[3] == "Agentic Copilot":
    st.subheader("🤖 Agentic SRE Copilot")
    
    from backend.agentic import get_orchestrator
    import asyncio
    
    orchestrator = get_orchestrator()
    
    if st.button("Collect Signals"):
        signals = asyncio.run(orchestrator.test_perception())
        st.json(signals)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Running Incidents", 
                 orchestrator.get_monitoring_status()["running_incidents"])
    with col2:
        st.metric("Monitoring Active", 
                 "✅" if orchestrator.get_monitoring_status()["running"] else "❌")
    
    st.subheader("Recent Incidents")
    incidents = orchestrator.get_recent_incidents(5)
    if incidents:
        st.dataframe(incidents)
    else:
        st.info("No recent incidents")
    
    st.subheader("Performance Metrics (7 days)")
    metrics = orchestrator.get_performance_metrics(7)
    st.json(metrics)
    
    st.subheader("Audit Trail")
    incident_id = st.text_input("Enter Incident ID")
    if incident_id:
        trail = orchestrator.get_incident_audit_trail(incident_id)
        st.dataframe(trail)
```

## Step 7: Restart Streamlit

```bash
# SSH into EC2
ssh -i "Team Meenakshi.pem" ubuntu@18.237.102.97

# Stop Streamlit
sudo pkill -9 streamlit

# Navigate to app
cd /root/MonitoringAlert

# Start Streamlit
streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8501 &
```

## Step 8: Test Each Component

### Test Perception
```bash
# In EC2 terminal
cd /root/MonitoringAlert
python -c "
from backend.agentic.perception import PerceptionEngine
from backend.config.agentic_config import APPS_CONFIG
import asyncio

async def test():
    pe = PerceptionEngine(APPS_CONFIG)
    signals = await pe.collect_signals()
    for s in signals:
        print(f'{s.app_name} - {s.source}: {s.status}')

asyncio.run(test())
"
```

### Test Reasoning
```bash
# In EC2 terminal
python -c "
from backend.agentic.reasoning import LLMReasoner
from backend.agentic.core import Incident, IncidentSeverity, Memory
import os

memory = Memory('/tmp/test_memory.json')
reasoner = LLMReasoner()

incident = Incident(
    id='TEST-1',
    timestamp='2026-02-09T14:00:00Z',
    severity=IncidentSeverity.HIGH,
    app_name='api-server',
    description='High memory usage detected',
    signals=[],
    context={}
)

decision = reasoner.reason_about_incident(incident, memory)
print(f'Recommended actions: {decision.recommended_actions}')
print(f'Confidence: {decision.confidence:.0%}')
print(f'Risk level: {decision.risk_level}')
"
```

### Test JIRA Integration
```bash
# In EC2 terminal
python -c "
from backend.agentic.jira_integration import JiraClient
from backend.agentic.core import Incident, IncidentSeverity
import os

jira = JiraClient(
    base_url=os.getenv('JIRA_BASE_URL'),
    user_email=os.getenv('JIRA_USER_EMAIL'),
    api_token=os.getenv('JIRA_API_TOKEN'),
    project_key=os.getenv('JIRA_PROJECT_KEY')
)

incident = Incident(
    id='TEST-1',
    timestamp='2026-02-09T14:00:00Z',
    severity=IncidentSeverity.HIGH,
    app_name='api-server',
    description='Test incident for verification',
    signals=[],
    context={}
)

ticket = jira.create_incident_ticket(incident)
print(f'Created ticket: {ticket}')
"
```

## Step 9: Monitor Logs

```bash
# Watch agentic logs in real-time
sudo tail -f /var/log/sre-agent/agentic.log

# Watch systemd journal
sudo journalctl -u sre-agent.service -f

# View stored incidents
cat /var/lib/sre-agent/incident_memory.json | python -m json.tool

# Query audit database
sqlite3 /var/lib/sre-agent/sre_audit.db "SELECT * FROM audit_events LIMIT 10;"
```

## Troubleshooting

### Service won't start
```bash
sudo systemctl status sre-agent.service
sudo journalctl -u sre-agent.service -n 50
```

### No signals collected
```bash
# Verify health check endpoints are reachable
curl http://localhost:8000/health
curl http://localhost:5432/health (if applicable)

# Verify log files exist
ls -la /var/log/api-server.log
ls -la /var/log/postgresql/postgresql.log

# Verify systemd services exist
systemctl list-units --type=service | grep -E "api|db|redis"
```

### LLM reasoning fails
```bash
# Verify GOOGLE_API_KEY is set
echo $GOOGLE_API_KEY

# Test API access
python -c "from google import genai; c = genai.Client(api_key='$GOOGLE_API_KEY'); print(c)"
```

### JIRA integration fails
```bash
# Verify JIRA credentials
export JIRA_BASE_URL=https://yourcompany.atlassian.net
export JIRA_USER_EMAIL=your-email@company.com
export JIRA_API_TOKEN=your-token

# Test connectivity
curl -u $JIRA_USER_EMAIL:$JIRA_API_TOKEN $JIRA_BASE_URL/rest/api/3/projects
```

### SMTP fails
```bash
# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.company.com', 587)
server.starttls()
server.login('user@company.com', 'password')
print('SMTP OK')
"
```

## Next Steps

1. ✅ Agentic framework deployed
2. ✅ All components integrated
3. ✅ Systemd service running
4. ✅ Streamlit UI updated
5. **→** Monitor incidents in real-time
6. **→** Tune policies based on patterns
7. **→** Integrate with your monitoring stack
8. **→** Train team on new system

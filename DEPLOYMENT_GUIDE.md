# 🚀 Complete EC2 Deployment Guide
# Deploy MonitoringAlert with Autonomous Agents

## Step 1: SSH to EC2
```bash
ssh -i your-key.pem ubuntu@18.237.102.97
```

## Step 2: Pull Latest Code
```bash
cd ~/MonitoringAlert
git pull origin main
```

## Step 3: Activate Virtual Environment
```bash
source ~/MonitoringAlert/venv/bin/activate
```

## Step 4: Install Dependencies (if needed)
```bash
pip3 install -r backend/requirements.txt
```

## Step 5: Set Google API Key (CRITICAL!)
```bash
export GOOGLE_API_KEY='your-actual-gemini-api-key-here'
```

Or make it persistent:
```bash
echo "export GOOGLE_API_KEY='your-actual-gemini-api-key-here'" >> ~/.bashrc
source ~/.bashrc
```

---

## 🎯 Start All Services (In Separate Terminals)

### Terminal 1: Start Autonomous Agent Server
```bash
cd ~/MonitoringAlert
source venv/bin/activate
export GOOGLE_API_KEY='your-api-key'
python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     ✅ Autonomous Agent Server started - Agents running in background
```

### Terminal 2: Start Copilot KB API
```bash
cd ~/MonitoringAlert
source venv/bin/activate
export GOOGLE_API_KEY='your-api-key'
python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 3: Start Streamlit Dashboard
```bash
cd ~/MonitoringAlert
source venv/bin/activate
python3 -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

**Expected Output:**
```
You can now view your Streamlit app in your browser.
External URL: http://18.237.102.97:8501
```

---

## ✅ Verification Checklist

### 1. Check Agent Server Health
```bash
curl http://18.237.102.97:8001/
```
**Expected:** JSON response with agent endpoints

### 2. Check Agent Status
```bash
curl http://18.237.102.97:8001/api/agents/status
```
**Expected:** All agents running

### 3. Check Copilot KB API Health
```bash
curl http://18.237.102.97:8000/health
```
**Expected:** `{"status": "✅ Copilot KB API is running", "model": "gemini-1.5-pro"}`

### 4. Test Vulnerability Query
```bash
curl -X POST http://18.237.102.97:8000/api/vulnerability/query \
  -H "Content-Type: application/json" \
  -d '{"vulnerability_id": "CVE-2024-1234", "cve": ""}'
```

### 5. Access Streamlit Dashboard
```
http://18.237.102.97:8501
```

---

## 🔗 Live Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Agent Server** | http://18.237.102.97:8001 | Autonomous agents & decisions |
| **Agent Status** | http://18.237.102.97:8001/api/agents/status | Monitor all agents |
| **Agent Decisions** | http://18.237.102.97:8001/api/agents/decisions | View autonomous decisions |
| **Copilot KB API** | http://18.237.102.97:8000 | Vulnerability knowledge base |
| **Streamlit Dashboard** | http://18.237.102.97:8501 | Monitoring UI |

---

## 🛑 Stop All Services

```bash
# Terminal 1
^C  # Ctrl+C to stop Agent Server

# Terminal 2
^C  # Ctrl+C to stop Copilot KB API

# Terminal 3
^C  # Ctrl+C to stop Streamlit
```

---

## 📋 What's Running

### 🤖 Autonomous Agents (Port 8001)
- ✅ SSL Certificate Agent (every 1h)
- ✅ Vulnerability Remediation Agent (every 6h)
- ✅ Health Check Agent (every 5min)
- ✅ Problem Detection Agent (every 15min)

### 🧠 Copilot KB API (Port 8000)
- 📊 Vulnerability query endpoint
- 🔧 Remediation guidance endpoint
- 🏷️ Classification endpoint
- 🔎 Search endpoint
- ✅ TVT checklist endpoint
- 🎟️ Jira template endpoint

### 📱 Streamlit Dashboard (Port 8501)
- 💻 Chatbot with LLM
- 🚀 Deployment tracking
- 🔐 SSL Certificate monitoring
- 🛡️ Vulnerability remediation
- 🏥 Health check monitoring
- 📋 Problem tracking
- 🤖 Agent status (read-only)

---

## 🚨 Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8001
lsof -i :8001

# Kill process
kill -9 <PID>
```

### Missing GOOGLE_API_KEY
```
ModuleNotFoundError: No module named 'google.generativeai'
```
→ Make sure you set `export GOOGLE_API_KEY='...'`

### Streamlit Connection Refused
```
curl: (7) Failed to connect to 18.237.102.97 port 8501
```
→ Check security group allows inbound on ports 8000, 8001, 8501

### Agent Service Not Starting
```
ModuleNotFoundError: No module named 'asyncio'
```
→ Reinstall dependencies: `pip3 install -r backend/requirements.txt`

---

## 📊 Deployment Summary

✅ **All autonomous agents deployed and running 24/7**
✅ **Copilot KB API ready for vulnerability queries**
✅ **Streamlit dashboard monitoring all services**
✅ **No manual agent controls (fully autonomous)**
✅ **Read-only UI (just displays agent decisions)**

🎉 **Your autonomous SRE platform is live!**

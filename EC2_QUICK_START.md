# EC2 Quick Setup - Copilot KB API & Streamlit

## Problem: `python` not found on EC2

**Solution:** Use `python3` instead (Ubuntu doesn't have `python` by default)

---

## Quick Start (5 Minutes)

### Step 1: SSH to EC2
```bash
ssh -i your-key.pem ubuntu@18.237.102.97
```

### Step 2: Clone/Navigate to Project
```bash
cd ~/MonitoringAlert
```

### Step 3: Run Setup Script
```bash
chmod +x ec2_setup.sh
./ec2_setup.sh
```

This will:
- ✅ Install Python3 & pip3
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Start Copilot KB API on port 8000
- ✅ Start Streamlit on port 8501

---

## Manual Setup (If Script Doesn't Work)

### Step 1: Update & Install Python
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
```

### Step 2: Create Virtual Environment
```bash
cd ~/MonitoringAlert
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip3 install -r backend/requirements.txt
```

### Step 4: Set Google API Key
```bash
export GOOGLE_API_KEY='your-gemini-api-key-here'
```

### Step 5: Start Copilot KB API (in separate terminal)
```bash
source venv/bin/activate
cd ~/MonitoringAlert
python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 6: Verify API is Running (new terminal)
```bash
curl http://localhost:8000/health

# Should return:
# {"status":"✅ Copilot KB API is running","model":"gemini-pro"}
```

### Step 7: Start Streamlit (in 3rd terminal)
```bash
cd ~/MonitoringAlert
python3 -m streamlit run frontend/perception_and_action_hub.py --server.port 8501 --server.address 0.0.0.0
```

**Output should show:**
```
You can now view your Streamlit app in your browser.
Network URL: http://0.0.0.0:8501
```

---

## Run Services in Background

### Option A: Using nohup (Recommended)
```bash
# Start API in background
nohup python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000 > kb_api.log 2>&1 &

# Start Streamlit in background
nohup python3 -m streamlit run frontend/perception_and_action_hub.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &

# Check logs
tail -f kb_api.log
tail -f streamlit.log
```

### Option B: Using screen (Better terminal mgmt)
```bash
# Terminal 1: API
screen -S kb_api
python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000
# Press Ctrl+A then D to detach

# Terminal 2: Streamlit
screen -S streamlit
python3 -m streamlit run frontend/perception_and_action_hub.py --server.port 8501 --server.address 0.0.0.0
# Press Ctrl+A then D to detach

# Reattach to screens
screen -r kb_api
screen -r streamlit
```

### Option C: Using systemd (Most Robust)
See advanced section below.

---

## Verify Everything is Running

```bash
# Check API
curl http://localhost:8000/health

# Check Streamlit (should return HTML)
curl http://localhost:8501

# List running processes
ps aux | grep -E 'uvicorn|streamlit'

# Check port usage
lsof -i :8000
lsof -i :8501
```

---

## Access from Browser

Replace `18.237.102.97` with your EC2 instance IP:

- **Streamlit App:** http://18.237.102.97:8501
- **API Health:** http://18.237.102.97:8000/health

---

## Troubleshooting

### Port Already in Use
```bash
# Kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use a different port
python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8001
```

### API Not Found Error
```bash
# Wrong command
python backend/api/copilot_kb_api.py  # ❌ Won't work

# Correct command
python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000  # ✅
```

### ModuleNotFoundError
```bash
# Make sure you're in virtual environment
source venv/bin/activate

# Reinstall dependencies
pip3 install -r backend/requirements.txt
```

### GOOGLE_API_KEY Not Set
```bash
# Check if set
echo $GOOGLE_API_KEY

# Set it
export GOOGLE_API_KEY='your-key-here'

# Or make it persistent
echo "export GOOGLE_API_KEY='your-key-here'" >> ~/.bashrc
source ~/.bashrc
```

---

## Security Group Configuration

**Make sure EC2 security group allows:**
- Port 8000 (Copilot KB API) - can be restricted to your IP
- Port 8501 (Streamlit) - can be restricted to your IP
- Port 22 (SSH) - for your access

### AWS CLI
```bash
# Open ports (replace sg-xxxxx with your security group)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 8501 \
  --cidr 0.0.0.0/0
```

---

## Advanced: Run as Systemd Service

### Create API Service
```bash
sudo tee /etc/systemd/system/copilot-kb.service > /dev/null <<EOF
[Unit]
Description=Copilot KB API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/MonitoringAlert
Environment="GOOGLE_API_KEY=your-key-here"
ExecStart=/home/ubuntu/MonitoringAlert/venv/bin/python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable copilot-kb
sudo systemctl start copilot-kb
sudo systemctl status copilot-kb
```

### Create Streamlit Service
```bash
sudo tee /etc/systemd/system/streamlit-app.service > /dev/null <<EOF
[Unit]
Description=Streamlit Monitoring App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/MonitoringAlert
ExecStart=/home/ubuntu/MonitoringAlert/venv/bin/python3 -m streamlit run frontend/perception_and_action_hub.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable streamlit-app
sudo systemctl start streamlit-app
sudo systemctl status streamlit-app
```

### Manage Services
```bash
# Check status
sudo systemctl status copilot-kb
sudo systemctl status streamlit-app

# View logs
sudo journalctl -u copilot-kb -f
sudo journalctl -u streamlit-app -f

# Stop/Start
sudo systemctl stop copilot-kb
sudo systemctl start copilot-kb
sudo systemctl restart copilot-kb
```

---

## Summary

| Command | Purpose |
|---------|---------|
| `python3 -m venv venv` | Create virtual environment |
| `source venv/bin/activate` | Activate environment |
| `pip3 install -r backend/requirements.txt` | Install dependencies |
| `python3 -m uvicorn backend.api.copilot_kb_api:app --host 0.0.0.0 --port 8000` | Start API |
| `python3 -m streamlit run frontend/perception_and_action_hub.py --server.port 8501` | Start Streamlit |
| `curl http://localhost:8000/health` | Test API |
| `tail -f kb_api.log` | View API logs |

---

## Support

If issues persist:
1. Check security group allows ports 8000, 8501
2. Verify Google API key is set: `echo $GOOGLE_API_KEY`
3. Check logs: `tail -f kb_api.log` and `tail -f streamlit.log`
4. Ensure Python3 is installed: `python3 --version`
5. Reinstall dependencies: `pip3 install --upgrade pip && pip3 install -r backend/requirements.txt`

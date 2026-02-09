# 🔄 Autonomous Health Check & Docker Auto-Restart

## Overview

The **Health Check Agent** continuously monitors URLs from `apps.csv` and **automatically restarts Docker containers** when services go down.

## How It Works

1. **Monitor** - Agent checks all URLs in `apps.csv` every 5 minutes
2. **Detect** - Identifies services that return HTTP errors or are unreachable  
3. **Analyze** - LLM (Gemini) analyzes the situation and decides whether to restart (confidence > 70%)
4. **Execute** - Automatically stops and starts the Docker container
5. **Verify** - Re-checks the URL to confirm service is back online

## Configuration

### 1. Update Docker Container Mapping

Edit `backend/api/autonomous_agent_service.py` - `HealthCheckAgent.__init__()`:

```python
self.docker_containers = {
    "AuthService": "auth-service",        # AppName -> Container Name
    "PaymentAPI": "payment-api",
    "UserService": "user-service",
    "OrderService": "order-service",
    "InventoryAPI": "inventory-api",
    "FlakyService": "flaky-service"
}
```

### 2. Update apps.csv

Add your services to monitor:

```csv
AppName,URL,Expected
AuthService,http://localhost:8081,
PaymentAPI,http://localhost:8082,
UserService,http://localhost:8083,
```

### 3. Start Docker Containers

Use the provided `docker-compose.yml`:

```bash
# Start all demo containers
docker-compose up -d

# Check container status
docker ps

# View logs
docker-compose logs -f
```

## Usage

### Start the Agent Server

```bash
# On EC2 or local
python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001
```

The Health Check Agent will:
- ✅ Monitor all URLs every 5 minutes
- ⚠️ Log warnings when services are down
- 🔄 Automatically restart Docker containers
- ✅ Verify services are back online

### Monitor Agent Activity

```bash
# Check agent status
curl http://localhost:8001/api/agents/health

# View recent decisions
curl http://localhost:8001/api/agents/decisions?limit=10
```

## Example Logs

```
INFO:🤖 Health Check Agent monitoring...
INFO:⚠️ AuthService is UNREACHABLE: Connection refused
INFO:🤖 Health Check Agent → APPROVE
INFO:📋 Action: restart_service
INFO:⚙️ Applying remediation: restart_docker...
INFO:♻️ Restarting Docker container: auth-service (for AuthService)
INFO:🛑 Stopping container: auth-service
INFO:▶️ Starting container: auth-service
INFO:✅ Successfully restarted auth-service
INFO:✅ AuthService is now HEALTHY (HTTP 200)
```

## Testing Auto-Restart

```bash
# 1. Stop a container manually
docker stop auth-service

# 2. Wait for next health check cycle (up to 5 minutes)
# The agent will detect it's down and restart it automatically

# 3. Verify in logs:
# - "⚠️ AuthService is DOWN"
# - "♻️ Restarting Docker container: auth-service"
# - "✅ AuthService is now HEALTHY"

# 4. Check container is running again
docker ps | grep auth-service
```

## Adding Your Own Services

### Step 1: Create Docker Container

```dockerfile
# Example: Your custom service
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

### Step 2: Add to docker-compose.yml

```yaml
  my-service:
    build: ./my-service
    container_name: my-custom-service
    ports:
      - "9000:8000"
    restart: unless-stopped
```

### Step 3: Update apps.csv

```csv
MyCustomService,http://localhost:9000/health,OK
```

### Step 4: Update Docker Mapping

```python
self.docker_containers = {
    "MyCustomService": "my-custom-service",
    # ... other services
}
```

## Requirements

- ✅ Docker installed and running
- ✅ Agent has permissions to run `docker stop` and `docker start`
- ✅ Google Gemini API key configured (`GOOGLE_API_KEY`)

## Permissions (Linux/EC2)

If running on EC2, ensure the user can control Docker:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Restart to apply
sudo systemctl restart docker

# Verify
docker ps
```

## Troubleshooting

### "Docker command not found"
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### "Permission denied accessing Docker socket"
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### "Container not found"
```bash
# Check container name matches mapping
docker ps -a | grep auth-service

# Verify in autonomous_agent_service.py
self.docker_containers = {
    "AuthService": "auth-service",  # Must match actual container name
}
```

## Architecture

```
┌───────────────────────────────────────────────┐
│         Health Check Agent (Port 8001)        │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │ Monitor Loop (Every 5 minutes)          │ │
│  └─────────────────────────────────────────┘ │
│                    ↓                          │
│  ┌─────────────────────────────────────────┐ │
│  │ Read apps.csv & Check all URLs          │ │
│  └─────────────────────────────────────────┘ │
│                    ↓                          │
│  ┌─────────────────────────────────────────┐ │
│  │ LLM Analysis (Gemini 2.5 Flash)         │ │
│  │ - Confidence scoring                    │ │
│  │ - Decide: restart or defer              │ │
│  └─────────────────────────────────────────┘ │
│                    ↓                          │
│  ┌─────────────────────────────────────────┐ │
│  │ Execute: docker stop -> docker start    │ │
│  └─────────────────────────────────────────┘ │
│                    ↓                          │
│  ┌─────────────────────────────────────────┐ │
│  │ Verify: Re-check URL health             │ │
│  └─────────────────────────────────────────┘ │
└───────────────────────────────────────────────┘
                     ↓
        ┌────────────────────────┐
        │  Docker Containers     │
        │  - auth-service        │
        │  - payment-api         │
        │  - user-service        │
        │  - ...                 │
        └────────────────────────┘
```

## Advanced: Custom Health Checks

You can customize the health check logic in `_collect_metrics()`:

```python
async def _collect_metrics(self) -> Dict:
    # Custom health check logic
    # - Check response time
    # - Validate response content
    # - Check multiple endpoints
    # - Monitor error rates
    pass
```

## API Endpoints

```bash
# Get Health Check Agent status
GET http://localhost:8001/api/agents/health

# Get all agent decisions
GET http://localhost:8001/api/agents/decisions?limit=20

# Get all agent statuses
GET http://localhost:8001/api/agents/status
```

## Monitoring in Streamlit UI

The Streamlit dashboard (port 8501) shows:
- ✅ Agent status (running/stopped)
- 📊 Recent autonomous decisions
- 🔄 Restart history
- ⏰ Last run timestamp

Access at: `http://localhost:8501` (or EC2 IP:8501)

## Next Steps

1. ✅ Deploy to EC2: See `DEPLOYMENT_GUIDE.md`
2. ✅ Add your production services to `apps.csv`
3. ✅ Update Docker container mappings
4. ✅ Start containers with `docker-compose up -d`
5. ✅ Start agents with `python3 -m uvicorn backend.api.agent_server:app --port 8001`
6. ✅ Monitor via Streamlit UI or API calls

---

**🎯 Result**: Fully autonomous health monitoring with zero manual intervention. Services auto-restart when they fail!

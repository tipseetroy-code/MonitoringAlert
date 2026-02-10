# Docker Auto-Restart Test Guide

## Quick Test: Agent Auto-Restart Docker Container

### Step 1: Start Test Container

Run a simple nginx container on port 8090:

```powershell
docker run -d --name test-nginx -p 8090:80 nginx:alpine
```

**Verify it's running:**
```powershell
docker ps | findstr test-nginx
curl http://localhost:8090
```

### Step 2: Add to apps.csv

Add this line to `apps.csv`:

```csv
TestNginx,http://localhost:8090,test-nginx,
```

Or use the full apps.csv:
```csv
AppName,URL,DockerContainer,Expected
AuthService,http://localhost:8081,auth-service,
PaymentAPI,http://localhost:8082,payment-api,
UserService,http://localhost:8083,user-service,
OrderService,http://localhost:8084,order-service,
InventoryAPI,http://localhost:8085,inventory-api,
FlakyService,http://localhost:8086,flaky-service,
EPAS_Health_Check,http://18.237.102.97:8000/health/epas,EPAS_Service,OK
TestNginx,http://localhost:8090,test-nginx,
```

### Step 3: Test Auto-Restart Flow

#### 3A. Stop the Container (Simulate Failure)

```powershell
docker stop test-nginx
```

**Verify it's stopped:**
```powershell
docker ps -a | findstr test-nginx
curl http://localhost:8090  # Should fail
```

#### 3B. Run Health Check in UI

1. Go to **Health Check Monitoring** tab in Streamlit
2. Enable **"Enable agentic flow"** checkbox
3. Click **"🚀 Run Health Check"**

#### 3C. Watch Agent Diagnostics & Auto-Restart

The agent will:
1. ✅ **Detect failure** for TestNginx
2. 🔍 **Run diagnostics:**
   - Check disk space (should be >10% free)
   - Check port 8090 (should be free since container is stopped)
   - Check Docker container status (should show "exited")
3. 🔄 **Execute restart:** `docker restart test-nginx`
4. ✅ **Verify recovery**

**Expected Output in UI:**

```
🤖 Agentic Decisions
TestNginx → restart | safe=True | reason: Health check failed; outside change window

Diagnostics:
- Disk: 45.2% free (ok)
- Port 8090: free
- Docker: exited
- Action: Docker restart executed for test-nginx
- Outcome: resolved
```

#### 3D. Verify Container is Running Again

```powershell
docker ps | findstr test-nginx
curl http://localhost:8090  # Should return nginx welcome page
```

### Step 4: Advanced Testing

#### Test Disk Space Issue (Simulated)

Modify the `min_free_pct` parameter in `_disk_space_diagnostics()` to trigger low disk warnings:

```python
def _disk_space_diagnostics(min_free_pct: int = 90) -> Dict[str, str]:  # Set to 90% to simulate low disk
```

#### Test Port Conflict

Start another service on port 8090 before the health check:

```powershell
docker stop test-nginx
# Start something else on 8090
docker run -d --name port-blocker -p 8090:80 httpd:alpine
```

The diagnostics will show `port: in_use` and the restart will fail with a port conflict error.

### Clean Up

```powershell
docker stop test-nginx
docker rm test-nginx
```

---

## Multiple Container Test

Start multiple containers for comprehensive testing:

```powershell
docker run -d --name test-nginx -p 8090:80 nginx:alpine
docker run -d --name test-redis -p 6379:6379 redis:alpine
docker run -d --name test-postgres -p 5433:5432 -e POSTGRES_PASSWORD=test postgres:alpine
```

Add to apps.csv:
```csv
TestNginx,http://localhost:8090,test-nginx,
TestRedis,http://localhost:6379,test-redis,
TestPostgres,http://localhost:5433,test-postgres,
```

**Stop all and test batch restart:**
```powershell
docker stop test-nginx test-redis test-postgres
```

Then run health check and watch all 3 auto-restart!

---

## Expected Health Check Logs

```
2026-02-10 14:30:00Z | RUN_START | total_apps=8
2026-02-10 14:30:01Z | CHECK_FAIL | app=TestNginx | url=http://localhost:8090 | status=N/A
2026-02-10 14:30:01Z | AGENTIC_DECIDE | app=TestNginx | action=restart | safe=True | reason=Health check failed
2026-02-10 14:30:02Z | AGENTIC_RESTART | app=TestNginx | outcome=resolved
2026-02-10 14:30:05Z | RETRY_OK | app=TestNginx | url=http://localhost:8090 | status=200
```

---

## Diagnostics Output Format

```json
{
  "outcome": "resolved",
  "details": "Docker restart executed for test-nginx",
  "diagnostics": {
    "disk": {
      "status": "ok",
      "free_pct": "45.2",
      "drive": "C:\\"
    },
    "port": {
      "status": "free",
      "host": "localhost",
      "port": "8090"
    },
    "docker": {
      "status": "exited"
    }
  }
}
```

---

## Troubleshooting

### Docker not found
```
Error: docker: command not found
```
**Solution:** Install Docker Desktop for Windows

### Permission denied
```
Error: permission denied while trying to connect to the Docker daemon
```
**Solution:** Run PowerShell as Administrator or add user to `docker-users` group

### Container restart fails
Check Docker logs:
```powershell
docker logs test-nginx
docker inspect test-nginx
```

### Port already in use
Find what's using the port:
```powershell
netstat -ano | findstr :8090
```

Kill the process:
```powershell
taskkill /PID <PID> /F
```

---

## Policy Configuration

Adjust restart behavior in UI:

- **Allow restart:** Enable/disable auto-restart
- **Require approval:** Manual approval before restart
- **Max restarts/day:** Limit restart frequency (default: 2)
- **Change window:** Only restart during business hours (9AM-6PM)

**Example:** To test without restrictions:
1. ✅ Enable agentic flow
2. ❌ Disable "Require approval"
3. ✅ Enable "Allow restart"
4. Set max restarts to 10

Then stop containers and watch automatic recovery!

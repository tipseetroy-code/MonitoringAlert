#!/bin/bash
echo "=== EC2 Service Diagnostics ==="
echo ""

echo "1. Checking Docker Service:"
sudo systemctl status docker | head -5
echo ""

echo "2. Listing ALL Docker Containers:"
docker ps -a
echo ""

echo "3. Checking Running Containers:"
docker ps
echo ""

echo "4. Checking Listening Ports:"
sudo netstat -tuln | grep -E '8090|6379|5432|27017|3306|8000|8001|8501|8080' || echo "No matching ports found"
echo ""

echo "5. Testing Local Services:"
echo "Testing EPAS (port 8000):"
curl -s -m 3 http://localhost:8000/health/epas || echo "EPAS not responding"
echo ""

echo "Testing Agent Server (port 8001):"
curl -s -m 3 http://localhost:8001/api/agents/status || echo "Agent Server not responding"
echo ""

echo "6. Disk Space:"
df -h | grep -E 'Filesystem|/dev/xvd|/dev/nvme'
echo ""

echo "7. Docker Container Status (Individual):"
for container in test-nginx redis postgres mongodb mysql; do
    echo "  - $container: $(docker inspect -f '{{.State.Status}}' $container 2>/dev/null || echo 'NOT FOUND')"
done
echo ""

echo "8. Starting Stopped Containers:"
docker start test-nginx redis postgres mongodb mysql 2>/dev/null
echo "Done. Waiting 5 seconds for services to initialize..."
sleep 5
echo ""

echo "9. Final Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== Diagnostics Complete ==="

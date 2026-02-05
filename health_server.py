"""
Simple standalone health check server with healthy and unhealthy endpoints.
Run: python health_server.py
"""
from fastapi import FastAPI, Response
import uvicorn

app = FastAPI(title="Health Check Demo Server")

# Simulated EPAS app state - starts as DOWN (unhealthy)
epas_app_running = False
# Flaky endpoint state (first call fails, second succeeds)
flaky_state = {"count": 0}


@app.get("/health/ok")
def health_ok():
    """Always returns 200 OK - healthy endpoint"""
    return {"status": "OK", "message": "Service is healthy"}


@app.get("/health/fail")
def health_fail(response: Response):
    """Always returns 500 - unhealthy endpoint"""
    response.status_code = 500
    return {"status": "FAIL", "message": "Service is unhealthy"}


@app.get("/health/epas")
def health_epas(response: Response):
    """Simulated EPAS app - unhealthy until restarted"""
    global epas_app_running
    if epas_app_running:
        return {"status": "OK", "message": "EPAS application is running"}
    else:
        response.status_code = 503
        return {"status": "DOWN", "message": "EPAS application is not running - needs restart"}


@app.get("/health/flaky")
def health_flaky(response: Response):
    """Fails first time, succeeds on retry"""
    flaky_state["count"] += 1
    if flaky_state["count"] == 1:
        response.status_code = 503
        return {"status": "DOWN", "message": "Temporary failure - retry will recover"}
    return {"status": "OK", "message": "Recovered on retry"}


@app.post("/epas/restart")
def restart_epas():
    """Restart EPAS app - makes it healthy"""
    global epas_app_running
    epas_app_running = True
    return {"status": "RESTARTED", "message": "EPAS application restarted successfully"}


@app.post("/epas/stop")
def stop_epas():
    """Stop EPAS app - makes it unhealthy"""
    global epas_app_running
    epas_app_running = False
    return {"status": "STOPPED", "message": "EPAS application stopped"}


if __name__ == "__main__":
    print("🚀 Starting Health Check Demo Server...")
    print("📍 Healthy endpoint: http://localhost:8000/health/ok")
    print("📍 Unhealthy endpoint: http://localhost:8000/health/fail")
    print("📍 EPAS app (starts DOWN): http://localhost:8000/health/epas")
    print("🔄 Restart EPAS: POST http://localhost:8000/epas/restart")
    print("🛑 Stop EPAS: POST http://localhost:8000/epas/stop")
    uvicorn.run(app, host="0.0.0.0", port=8000)

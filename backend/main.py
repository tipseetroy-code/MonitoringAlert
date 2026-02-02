from fastapi import FastAPI
from .agent.agent_manager import start_agent, stop_agent, simulate_incident
from .services.storage import INCIDENTS

app = FastAPI(title="Agent Automation API")

@app.on_event("startup")
async def startup_event():
    # Auto-start the agent for 24/7 monitoring
    start_agent({"config": "auto"})
    print("Agent auto-started for 24/7 monitoring.")

@app.post("/agent/start")
def start(payload: dict):
    start_agent(payload)
    return {"status": "Agent started"}

@app.post("/agent/stop")
def stop():
    stop_agent()
    return {"status": "Agent stopped"}

@app.post("/agent/simulate")
def simulate():
    simulate_incident()
    return {"status": "Incident simulated"}

@app.get("/agent/status")
def get_agent_status():
    from .services.storage import AGENT_RUNNING
    return {"running": AGENT_RUNNING}

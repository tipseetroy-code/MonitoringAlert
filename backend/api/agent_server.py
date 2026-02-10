# backend/api/agent_server.py
"""
🚀 Agent Server - Autonomous agents run 24/7, UI just monitors
Agents detect, decide, and act autonomously
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
from .autonomous_agent_service import AutonomousAgentService, initialize_service, get_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Autonomous Agent Server",
    description="24/7 autonomous agents for SSL, vulnerability, health, problem management",
    version="2.0.0"
)

service: Optional[AutonomousAgentService] = None

@app.on_event("startup")
async def on_startup():
    """Start autonomous agents on server startup"""
    global service
    api_key = os.getenv("GOOGLE_API_KEY")
    
    initialize_service(api_key)
    service = get_service()
    service.start()
    
    logger.info("✅ Autonomous Agent Server started - Agents running in background")

@app.on_event("shutdown")
async def on_shutdown():
    """Stop agents on shutdown"""
    global service
    if service:
        service.stop()
    logger.info("🛑 Autonomous Agent Server stopped")

# ============== API Endpoints ==============

@app.get("/")
async def root():
    """Welcome message"""
    return {
        "message": "🤖 Autonomous Agent Server v2.0",
        "description": "SSL, Vulnerability, Health Check, Problem Detection agents running autonomously",
        "endpoints": {
            "status": "/api/agents/status",
            "decisions": "/api/agents/decisions",
            "start": "/api/agents/start",
            "stop": "/api/agents/stop",
            "trigger_manual": "/api/agents/trigger (ignores AUTO_RUN_AGENTS setting)"
        }
    }

@app.get("/api/agents/status")
async def get_agents_status():
    """Get all agents status"""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return service.get_status()

@app.get("/api/agents/decisions")
async def get_agent_decisions(limit: int = 50):
    """Get recent autonomous decisions made by agents"""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {
        "recent_decisions": service.get_decisions(limit),
        "total_decisions": len(service.decisions_log)
    }

@app.post("/api/agents/start")
async def start_agents():
    """Start all agents"""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    service.start()
    return {
        "message": "✅ All agents started",
        "status": service.get_status()
    }

@app.post("/api/agents/stop")
async def stop_agents():
    """Stop all agents"""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    service.stop()
    return {
        "message": "✅ All agents stopped",
        "status": service.get_status()
    }

@app.post("/api/agents/trigger")
async def trigger_agents_manual():
    """Manually trigger all agents once (ignores AUTO_RUN_AGENTS setting)"""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    service.run_agents_manual()
    return {
        "message": "🎯 Agents triggered! Running analysis now...",
        "note": "All agents will run once, regardless of AUTO_RUN_AGENTS setting",
        "status": service.get_status()
    }

@app.get("/api/agent/{agent_name}/decisions")
async def get_agent_specific_decisions(agent_name: str, limit: int = 20):
    """Get decisions from specific agent"""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    if agent_name not in service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    agent_decisions = [
        d for d in service.decisions_log if d.agent_name.lower().find(agent_name) != -1
    ]
    
    return {
        "agent": agent_name,
        "decisions": [
            {
                "decision": d.decision,
                "action": d.action.value,
                "confidence": d.confidence,
                "timestamp": d.timestamp.isoformat(),
                "executed": d.executed
            }
            for d in agent_decisions[-limit:]
        ]
    }

@app.get("/api/agents/ssl")
async def ssl_agent_status():
    """SSL Certificate Agent status"""
    if not service or "ssl" not in service.agents:
        raise HTTPException(status_code=500, detail="SSL Agent not found")
    
    agent = service.agents["ssl"]
    return {
        "agent": "SSL Certificate Agent",
        "status": "running" if service.running else "stopped",
        "last_run": agent.last_run.isoformat() if agent.last_run else None,
        "description": "Monitors certificates, auto-renews when expiring"
    }

@app.get("/api/agents/vulnerability")
async def vulnerability_agent_status():
    """Vulnerability Remediation Agent status"""
    if not service or "vulnerability" not in service.agents:
        raise HTTPException(status_code=500, detail="Vulnerability Agent not found")
    
    agent = service.agents["vulnerability"]
    return {
        "agent": "Vulnerability Remediation Agent",
        "status": "running" if service.running else "stopped",
        "last_run": agent.last_run.isoformat() if agent.last_run else None,
        "description": "Scans vulnerabilities, auto-patches low-risk ones"
    }

@app.get("/api/agents/health")
async def health_agent_status():
    """Health Check Agent status"""
    if not service or "health" not in service.agents:
        raise HTTPException(status_code=500, detail="Health Agent not found")
    
    agent = service.agents["health"]
    return {
        "agent": "Health Check Agent",
        "status": "running" if service.running else "stopped",
        "last_run": agent.last_run.isoformat() if agent.last_run else None,
        "description": "Monitors CPU, memory, disk; auto-restarts if needed"
    }

@app.get("/api/agents/problems")
async def problems_agent_status():
    """Problem Detection Agent status"""
    if not service or "problems" not in service.agents:
        raise HTTPException(status_code=500, detail="Problems Agent not found")
    
    agent = service.agents["problems"]
    return {
        "agent": "Problem Detection Agent",
        "status": "running" if service.running else "stopped",
        "last_run": agent.last_run.isoformat() if agent.last_run else None,
        "description": "Detects problems, auto-creates Jira if not solved by agents"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port from copilot KB API (8000)
    )

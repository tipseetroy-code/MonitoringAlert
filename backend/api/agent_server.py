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

# ============== Tableau Real API Endpoints ==============

import csv
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.tableau_client import get_tableau_client

# Flag to use real Tableau or fallback to CSV
USE_REAL_TABLEAU = os.getenv("USE_REAL_TABLEAU", "true").lower() == "true"

def load_vulnerabilities():
    """
    Load vulnerability data from Tableau or fallback to CSV
    Set USE_REAL_TABLEAU=true in .env to use live Tableau data
    """
    vulnerabilities = []
    
    # Try real Tableau first if enabled
    if USE_REAL_TABLEAU:
        try:
            logger.info("🔄 Fetching vulnerabilities from Tableau Server...")
            tableau_client = get_tableau_client()
            workbook_name = os.getenv("TABLEAU_WORKBOOK_NAME", "")
            view_name = os.getenv("TABLEAU_VIEW_NAME", "")
            
            vulnerabilities = tableau_client.fetch_view_data(
                view_name=view_name if view_name else None,
                workbook_name=workbook_name if workbook_name else None
            )
            
            if vulnerabilities:
                logger.info(f"✅ Loaded {len(vulnerabilities)} vulnerabilities from Tableau")
                return vulnerabilities
            else:
                logger.warning("⚠️ No data from Tableau, falling back to CSV")
        except Exception as e:
            logger.error(f"❌ Tableau fetch failed: {e}, falling back to CSV")
    
    # Fallback to CSV mock data
    csv_path = Path(__file__).parent.parent / "data" / "vulnerabilities.csv"
    
    if not csv_path.exists():
        logger.warning(f"Vulnerabilities CSV not found at {csv_path}")
        return vulnerabilities
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vulnerabilities.append(row)
        logger.info(f"✅ Loaded {len(vulnerabilities)} vulnerabilities from CSV (mock data)")
    except Exception as e:
        logger.error(f"❌ Failed to load vulnerabilities from CSV: {e}")
    
    return vulnerabilities

@app.get("/api/tableau/vulnerabilities")
async def fetch_tableau_vulnerabilities(status: Optional[str] = None):
    """
    Fetch vulnerabilities from Tableau Server (or CSV fallback)
    Optional filters: status=OPEN|REMEDIATED
    """
    vulnerabilities = load_vulnerabilities()
    
    # Filter by status if provided
    if status:
        vulnerabilities = [v for v in vulnerabilities if v.get("Status") == status]
    
    return {
        "success": True,
        "count": len(vulnerabilities),
        "data": vulnerabilities,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

@app.get("/api/tableau/vulnerabilities/{cve_id}")
async def fetch_vulnerability_detail(cve_id: str):
    """Fetch specific vulnerability details"""
    vulnerabilities = load_vulnerabilities()
    vuln = next((v for v in vulnerabilities if v.get("CVE_ID") == cve_id), None)
    
    if not vuln:
        raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found")
    
    return {
        "success": True,
        "data": vuln,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

@app.get("/api/tableau/vulnerabilities/summary")
async def fetch_tableau_summary():
    """Get vulnerability summary statistics"""
    vulnerabilities = load_vulnerabilities()
    
    summary = {
        "total": len(vulnerabilities),
        "critical": len([v for v in vulnerabilities if v.get("Severity") == "CRITICAL"]),
        "high": len([v for v in vulnerabilities if v.get("Severity") == "HIGH"]),
        "medium": len([v for v in vulnerabilities if v.get("Severity") == "MEDIUM"]),
        "low": len([v for v in vulnerabilities if v.get("Severity") == "LOW"]),
        "open": len([v for v in vulnerabilities if v.get("Status") == "OPEN"]),
        "remediated": len([v for v in vulnerabilities if v.get("Status") == "REMEDIATED"]),
        "exempted": len([v for v in vulnerabilities if v.get("Exempted") == "Yes"]),
        "lle": len([v for v in vulnerabilities if v.get("LLE") == "Yes"]),
    }
    
    return {
        "success": True,
        "summary": summary,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

class UpdateVulnerabilityRequest(BaseModel):
    cve_id: str
    status: str  # OPEN, REMEDIATED, etc.
    remediation_notes: Optional[str] = None

@app.post("/api/tableau/vulnerabilities/update")
async def update_vulnerability_status(request: UpdateVulnerabilityRequest):
    """
    Update vulnerability status in mock Tableau
    In production, this would update the actual Tableau datasource
    """
    vulnerabilities = load_vulnerabilities()
    csv_path = Path(__file__).parent.parent / "data" / "vulnerabilities.csv"
    
    # Find and update the vulnerability
    updated = False
    for vuln in vulnerabilities:
        if vuln.get("CVE_ID") == request.cve_id:
            vuln["Status"] = request.status
            if request.remediation_notes:
                vuln["Remediation"] = request.remediation_notes
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail=f"CVE {request.cve_id} not found")
    
    # Write back to CSV
    try:
        fieldnames = list(vulnerabilities[0].keys()) if vulnerabilities else []
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vulnerabilities)
        
        logger.info(f"✅ Updated {request.cve_id} status to {request.status}")
        return {
            "success": True,
            "message": f"Updated {request.cve_id} status to {request.status}",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to update vulnerability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port from copilot KB API (8000)
    )

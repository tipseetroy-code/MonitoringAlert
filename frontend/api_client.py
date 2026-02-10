import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Copilot KB API (port 8000)
BASE_URL = "http://localhost:8000"

# Autonomous Agent Server (port 8001) - for agent control
AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8001")

# ============= Copilot KB API Functions =============
def start_agent(payload):
    return requests.post(f"{BASE_URL}/agent/start", json=payload)

def stop_agent():
    return requests.post(f"{BASE_URL}/agent/stop")

def simulate_incident():
    return requests.post(f"{BASE_URL}/agent/simulate")

def fetch_incidents():
    try:
        return requests.get(f"{BASE_URL}/incidents", timeout=2).json()
    except requests.exceptions.RequestException:
        return []

# ============= Autonomous Agent Server Functions =============
def get_agent_status():
    """Get status of all autonomous agents"""
    try:
        response = requests.get(f"{AGENT_SERVER_URL}/api/agents/status", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def start_all_agents():
    """Start all agents (respects AUTO_RUN_AGENTS setting)"""
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/api/agents/start", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def stop_all_agents():
    """Stop all agents"""
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/api/agents/stop", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def trigger_agents_manual():
    """Manually trigger all agents once (ignores AUTO_RUN_AGENTS)"""
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/api/agents/trigger", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def get_agent_decisions(limit=50):
    """Get recent agent decisions"""
    try:
        response = requests.get(f"{AGENT_SERVER_URL}/api/agents/decisions?limit={limit}", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
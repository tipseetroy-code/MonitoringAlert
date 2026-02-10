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
    except requests.exceptions.ConnectTimeout:
        return {"success": False, "error": f"Connection timeout: Agent server not responding at {AGENT_SERVER_URL}. Make sure it's running on port 8001"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Cannot connect to agent server at {AGENT_SERVER_URL}. Please start it with: python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Agent server error: {str(e)}"}

def start_all_agents():
    """Start all agents (respects AUTO_RUN_AGENTS setting)"""
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/api/agents/start", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.ConnectTimeout:
        return {"success": False, "error": f"Connection timeout: Agent server not responding at {AGENT_SERVER_URL}. Make sure it's running on port 8001"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Cannot connect to agent server at {AGENT_SERVER_URL}. Please start it with: python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Agent server error: {str(e)}"}

def stop_all_agents():
    """Stop all agents"""
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/api/agents/stop", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.ConnectTimeout:
        return {"success": False, "error": f"Connection timeout: Agent server not responding at {AGENT_SERVER_URL}. Make sure it's running on port 8001"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Cannot connect to agent server at {AGENT_SERVER_URL}. Please start it with: python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Agent server error: {str(e)}"}

def trigger_agents_manual():
    """Manually trigger all agents once (ignores AUTO_RUN_AGENTS)"""
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/api/agents/trigger", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.ConnectTimeout:
        return {"success": False, "error": f"Connection timeout: Agent server not responding at {AGENT_SERVER_URL}. Make sure it's running on port 8001"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Cannot connect to agent server at {AGENT_SERVER_URL}. Please start it with: python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Agent server error: {str(e)}"}

def get_agent_decisions(limit=50):
    """Get recent agent decisions"""
    try:
        response = requests.get(f"{AGENT_SERVER_URL}/api/agents/decisions?limit={limit}", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.ConnectTimeout:
        return {"success": False, "error": f"Connection timeout: Agent server not responding at {AGENT_SERVER_URL}. Make sure it's running on port 8001"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Cannot connect to agent server at {AGENT_SERVER_URL}. Please start it with: python3 -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Agent server error: {str(e)}"}

# ============= Tableau Mock API Functions =============
def fetch_tableau_vulnerabilities(status=None):
    """Fetch vulnerabilities from Tableau API with CSV fallback"""
    try:
        url = f"{AGENT_SERVER_URL}/api/tableau/vulnerabilities"
        if status:
            url += f"?status={status}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        # Fallback to local CSV file
        import csv
        import os
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vulnerabilities.csv")
        if os.path.exists(csv_path):
            vulnerabilities = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if status and row.get('Status', '').lower() != status.lower():
                        continue
                    vulnerabilities.append(row)
            return {"success": True, "data": vulnerabilities, "source": "CSV_FALLBACK"}
        return {"success": False, "error": f"Failed to fetch from Tableau: {str(e)}"}

def fetch_tableau_summary():
    """Get vulnerability summary from Tableau"""
    try:
        response = requests.get(f"{AGENT_SERVER_URL}/api/tableau/vulnerabilities/summary", timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to fetch summary from Tableau: {str(e)}"}

def update_vulnerability_status(cve_id, status, remediation_notes=None):
    """Update vulnerability status in Tableau"""
    try:
        payload = {
            "cve_id": cve_id,
            "status": status,
            "remediation_notes": remediation_notes
        }
        response = requests.post(f"{AGENT_SERVER_URL}/api/tableau/vulnerabilities/update", json=payload, timeout=5)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to update vulnerability: {str(e)}"}

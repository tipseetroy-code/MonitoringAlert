"""
Add these functions to frontend/api_client.py after the existing functions
"""

# ============= Vulnerability Classification & Team Engagement =============
def classify_vulnerability(cve_id):
    """Classify vulnerability using AI and determine remediation team"""
    try:
        payload = {"cve_id": cve_id}
        response = requests.post(f"{AGENT_SERVER_URL}/api/vulnerabilities/classify", json=payload, timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to classify vulnerability: {str(e)}"}

def engage_team(cve_id, classification=None):
    """Engage remediation team via Jira, SDInfo, or Email"""
    try:
        payload = {
            "cve_id": cve_id,
            "classification": classification
        }
        response = requests.post(f"{AGENT_SERVER_URL}/api/vulnerabilities/engage-team", json=payload, timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to engage team: {str(e)}"}

def perform_tvt_validation(cve_id, asset, tests=None):
    """Perform TVT (Test & Verify) validation post-patching"""
    try:
        payload = {
            "cve_id": cve_id,
            "asset": asset,
            "tests": tests
        }
        response = requests.post(f"{AGENT_SERVER_URL}/api/vulnerabilities/tvt-validate", json=payload, timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to perform TVT: {str(e)}"}

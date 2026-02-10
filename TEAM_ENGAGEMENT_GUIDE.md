# Team Engagement Integration Guide

## Overview
This integration adds agentic team engagement for vulnerability remediation:
- **MAPS Team** (Jira) → Windows, Microsoft Edge vulnerabilities  
- **Middleware Team** (Jira) → Tomcat, JBoss, Apache, Nginx
- **Splunk Team** (SDInfo) → Splunk, BladeLogic installations
- **Auto TVT Validation** → Post-patching test & verify

## Files Created
1. `backend/integrations/vulnerability_classifier.py` - AI classification engine
2. `backend/integrations/jira_client.py` - Jira ticket creation
3. `backend/integrations/sdinfo_client.py` - SDInfo request submission
4. `backend/api/vulnerability_endpoints.py` - New API endpoints

## Step 1: Add to agent_server.py

Add after imports section (around line 13):
```python
from backend.api.vulnerability_endpoints import register_vulnerability_endpoints
```

Add before `if __name__ == "__main__":` (around line 362):
```python
# Register vulnerability classification endpoints
register_vulnerability_endpoints(app, load_vulnerabilities)
```

## Step 2: Add to frontend/api_client.py

Add after `update_vulnerability_status()` function (around line 131):
```python
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
```

## Step 3: Update .env Configuration

Add to .env file:
```env
# Jira Configuration (for team engagement)
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT=VULN

# SDInfo Configuration (for BladeLogic/Splunk)
SDINFO_URL=https://sdinfo.company.com/api
SDINFO_API_KEY=your_sdinfo_api_key
SDINFO_USERNAME=your_username
SDINFO_PASSWORD=your_password
```

## Step 4: Update frontend/app.py Imports

Add to imports section (around line 10):
```python
    classify_vulnerability, engage_team, perform_tvt_validation
```

## Step 5: Usage Example in UI

Replace the vulnerability display section in frontend/app.py (around line 2600+) with:

```python
for vuln in filtered_vulns[:10]:  # Show first 10
    with st.expander(f"🔴 {vuln.get('CVE_ID')} - {vuln.get('Component')} ({vuln.get('Severity')})"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Severity:** {vuln.get('Severity')}")
            st.markdown(f"**CVSS:** {vuln.get('CVSS_Score')}")
            st.markdown(f"**Asset:** {vuln.get('Asset')}")
        with col2:
            st.markdown(f"**Status:** {vuln.get('Status')}")
            st.markdown(f"**Detected:** {vuln.get('Detected_Date')}")
            st.markdown(f"**Component:** {vuln.get('Component')}")
        
        st.markdown(f"**Description:** {vuln.get('Description')}")
        st.markdown(f"**Remediation:** {vuln.get('Remediation')}")
        
        # Agentic workflow buttons
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("🧠 Classify", key=f"classify_{vuln.get('CVE_ID')}"):
                with st.spinner("Classifying with AI..."):
                    result = classify_vulnerability(vuln.get('CVE_ID'))
                    if result["success"]:
                        classification = result["data"]["classification"]
                        st.info(f"**Team:** {classification['team']}")
                        st.info(f"**Method:** {classification['method']}")
                        st.success(f"**Reasoning:** {classification['reasoning']}")
                        # Store in session state for engagement
                        st.session_state[f"classification_{vuln.get('CVE_ID')}"] = classification
                    else:
                        st.error(result["error"])
        
        with action_col2:
            if st.button("📧 Engage Team", key=f"engage_{vuln.get('CVE_ID')}"):
                with st.spinner("Engaging team..."):
                    # Use stored classification if available
                    classification = st.session_state.get(f"classification_{vuln.get('CVE_ID')}")
                    result = engage_team(vuln.get('CVE_ID'), classification)
                    if result["success"]:
                        data = result["data"]
                        st.success(f"✅ {data['team']} engaged via {data['method']}")
                        if data['result'].get('ticket_key'):
                            st.info(f"Ticket: {data['result']['ticket_key']}")
                        if data['result'].get('request_id'):
                            st.info(f"Request: {data['result']['request_id']}")
                    else:
                        st.error(result["error"])
        
        with action_col3:
            if st.button("✅ TVT Validate", key=f"tvt_{vuln.get('CVE_ID')}"):
                with st.spinner("Running TVT validation..."):
                    result = perform_tvt_validation(
                        vuln.get('CVE_ID'), 
                        vuln.get('Asset')
                    )
                    if result["success"]:
                        data = result["data"]
                        if data['tvt_status'] == 'PASS':
                            st.success("✅ All TVT tests passed!")
                            # Auto-update status to REMEDIATED
                            update_vulnerability_status(vuln.get('CVE_ID'), "REMEDIATED", "TVT validated")
                        else:
                            st.warning("⚠️ Some tests failed")
                    else:
                        st.error(result["error"])
```

## Testing

1. Start agent server:
   ```bash
   python -m uvicorn backend.api.agent_server:app --host 0.0.0.0 --port 8001
   ```

2. Test classification:
   ```bash
   curl -X POST http://localhost:8001/api/vulnerabilities/classify \
     -H "Content-Type: application/json" \
     -d '{"cve_id": "CVE-2024-12345"}'
   ```

3. Test team engagement:
   ```bash
   curl -X POST http://localhost:8001/api/vulnerabilities/engage-team \
     -H "Content-Type: application/json" \
     -d '{"cve_id": "CVE-2024-12345"}'
   ```

## Team Routing Logic

- **Windows/Edge** → MAPS Team (Jira patching request)
- **Middleware** → Middleware Team (Jira)
- **Splunk** → Splunk Team (SDInfo for BladeLogic installation)
- **Database** → Database Team (Jira)
- **Security** → Security Team (Jira)

All workflows include automatic TVT validation post-remediation.

# backend/api/copilot_kb_api.py
"""
🤖 Copilot KB API - AI-Powered Vulnerability Knowledge without Excel limits
Replaces static Excel KB with dynamic, scalable AI-powered knowledge retrieval
"""

import os
import json
import logging
from typing import Dict, List, Optional
import google.generativeai as genai
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

class CopilotKBAPI:
    """
    AI-Powered Vulnerability Knowledge API
    - No Excel row limits
    - Real-time AI-powered responses
    - Caching for performance
    - Multi-model support (Google Gemini, OpenAI, etc.)
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        """
        Initialize Copilot KB API
        
        Args:
            api_key: Google API key (or fetch from env)
            model: Model to use (gemini-pro, gemini-pro-vision, etc.)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set. Please set environment variable.")
        
        # Initialize Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        
        # Knowledge base cache
        self.kb_cache = {}
        
        logger.info(f"✅ CopilotKBAPI initialized with model: {model}")
    
    @lru_cache(maxsize=128)
    def query_vulnerability(self, vulnerability_id: str, cve: str = "") -> Dict:
        """
        Query vulnerability details without Excel limits
        
        Args:
            vulnerability_id: CWE ID, CVE ID, or vulnerability name
            cve: CVE ID for additional context
            
        Returns:
            Dictionary with vulnerability details
        """
        prompt = f"""
        Provide comprehensive security vulnerability information for: {vulnerability_id}
        {f'CVE: {cve}' if cve else ''}
        
        Return as JSON with these fields:
        {{
            "id": "Identifier",
            "name": "Vulnerability Name",
            "description": "Technical description",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "cvss_score": "Score 0-10",
            "impact": "Business impact",
            "remediation": "Fix steps",
            "affected_systems": ["List of affected systems"],
            "cis_controls": ["Relevant CIS controls"],
            "detection_methods": ["How to detect"],
            "prevention": "How to prevent"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            try:
                vuln_data = json.loads(response.text)
            except:
                vuln_data = {
                    "id": vulnerability_id,
                    "name": vulnerability_id,
                    "description": response.text,
                    "severity": "UNKNOWN"
                }
            
            # Cache result
            cache_key = f"{vulnerability_id}_{cve}"
            self.kb_cache[cache_key] = vuln_data
            
            return vuln_data
            
        except Exception as e:
            logger.error(f"❌ Error querying vulnerability {vulnerability_id}: {str(e)}")
            return {
                "id": vulnerability_id,
                "name": vulnerability_id,
                "error": str(e),
                "severity": "UNKNOWN"
            }
    
    def get_remediation_guidance(self, vulnerability_id: str, team: str = "") -> str:
        """
        Get AI-powered remediation guidance for a vulnerability
        
        Args:
            vulnerability_id: CWE/CVE ID
            team: Team type (MAPS, Middleware, BladeLogic, etc.)
            
        Returns:
            Remediation steps as string
        """
        team_context = f" for the {team} team" if team else ""
        
        prompt = f"""
        Provide step-by-step remediation guidance for vulnerability: {vulnerability_id}{team_context}
        
        Include:
        1. Pre-check requirements
        2. Remediation steps
        3. Post-remediation validation (TVT)
        4. Rollback procedures
        5. Success criteria
        
        Format as numbered steps for easy automation.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"❌ Error getting remediation: {str(e)}")
            return f"Error: {str(e)}"
    
    def classify_vulnerability(self, vuln_description: str) -> Dict:
        """
        AI-powered vulnerability classification
        
        Args:
            vuln_description: Description of the vulnerability
            
        Returns:
            Classification with team assignment
        """
        prompt = f"""
        Classify this vulnerability: {vuln_description}
        
        Return as JSON:
        {{
            "type": "OS|Middleware|Database|Application|Other",
            "category": "Security|Performance|Stability",
            "assigned_team": "MAPS|Middleware|BladeLogic|Database|Network",
            "priority": "CRITICAL|HIGH|MEDIUM|LOW",
            "estimated_effort": "hours",
            "risk_if_unpatched": "Description of risk"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            try:
                return json.loads(response.text)
            except:
                return {"classification": response.text}
        except Exception as e:
            logger.error(f"❌ Classification error: {str(e)}")
            return {"error": str(e)}
    
    def search_vulnerabilities(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        Search vulnerabilities by keyword (no Excel row limits)
        
        Args:
            keyword: Search term (vulnerability type, system, etc.)
            limit: Max results
            
        Returns:
            List of vulnerability matches
        """
        prompt = f"""
        Find vulnerabilities related to: {keyword}
        
        Return top {limit} results as JSON array with:
        [
            {{
                "id": "CVE/CWE ID",
                "name": "Vulnerability name",
                "severity": "CRITICAL|HIGH|MEDIUM|LOW",
                "description": "Brief description"
            }}
        ]
        """
        
        try:
            response = self.model.generate_content(prompt)
            try:
                results = json.loads(response.text)
                return results[:limit] if isinstance(results, list) else []
            except:
                return [{"result": response.text}]
        except Exception as e:
            logger.error(f"❌ Search error: {str(e)}")
            return []
    
    def get_tvt_checklist(self, vulnerability_id: str, system_type: str = "") -> str:
        """
        Generate TVT (Test & Verify) checklist for validation
        
        Args:
            vulnerability_id: Vulnerability ID
            system_type: Type of system (Windows, Linux, Middleware, etc.)
            
        Returns:
            TVT checklist steps
        """
        system_context = f" on {system_type}" if system_type else ""
        
        prompt = f"""
        Create a TVT (Test & Verify) checklist for validating patch/remediation 
        of vulnerability: {vulnerability_id}{system_context}
        
        Include:
        1. Pre-test validation
        2. Functional tests
        3. Security validation
        4. Performance checks
        5. Success criteria
        
        Format as checkboxes for TestRail/automated validation.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"❌ TVT generation error: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_jira_ticket_template(self, vulnerability_id: str, team: str) -> Dict:
        """
        Generate pre-filled Jira ticket template
        
        Args:
            vulnerability_id: Vulnerability ID
            team: Target team (MAPS, Middleware, BladeLogic)
            
        Returns:
            Jira ticket template dict
        """
        prompt = f"""
        Create a Jira ticket template for {team} team to remediate {vulnerability_id}
        
        Return as JSON:
        {{
            "summary": "Ticket summary",
            "description": "Full description with steps",
            "priority": "Highest|High|Medium|Low",
            "labels": ["vulnerability", "remediation", "team-name"],
            "acceptance_criteria": ["List of acceptance criteria"],
            "assignee": "Recommendation for assignee"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            try:
                return json.loads(response.text)
            except:
                return {"description": response.text}
        except Exception as e:
            logger.error(f"❌ Jira template error: {str(e)}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """Clear KB cache"""
        self.kb_cache.clear()
        logger.info("✅ KB cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "cached_items": len(self.kb_cache),
            "cache_keys": list(self.kb_cache.keys())
        }


# ============== REST API Endpoints ==============
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Copilot KB API", version="1.0.0")

# Initialize API
copilot_kb = None

@app.on_event("startup")
async def startup():
    global copilot_kb
    try:
        copilot_kb = CopilotKBAPI()
        logger.info("✅ Copilot KB API started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Copilot KB API: {str(e)}")

# Request/Response Models
class VulnerabilityQuery(BaseModel):
    vulnerability_id: str
    cve: str = ""

class RemediationRequest(BaseModel):
    vulnerability_id: str
    team: str = ""

class ClassificationRequest(BaseModel):
    description: str

class SearchRequest(BaseModel):
    keyword: str
    limit: int = 10

class TVTRequest(BaseModel):
    vulnerability_id: str
    system_type: str = ""

class JiraTicketRequest(BaseModel):
    vulnerability_id: str
    team: str

# Endpoints

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "✅ Copilot KB API is running",
        "model": copilot_kb.model_name if copilot_kb else "N/A"
    }

@app.post("/api/vulnerability/query")
async def query_vulnerability(request: VulnerabilityQuery):
    """Query vulnerability details"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    result = copilot_kb.query_vulnerability(request.vulnerability_id, request.cve)
    return result

@app.post("/api/remediation")
async def get_remediation(request: RemediationRequest):
    """Get remediation guidance"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    guidance = copilot_kb.get_remediation_guidance(request.vulnerability_id, request.team)
    return {"remediation": guidance}

@app.post("/api/classify")
async def classify(request: ClassificationRequest):
    """Classify vulnerability"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    classification = copilot_kb.classify_vulnerability(request.description)
    return classification

@app.post("/api/search")
async def search(request: SearchRequest):
    """Search vulnerabilities"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    results = copilot_kb.search_vulnerabilities(request.keyword, request.limit)
    return {"results": results}

@app.post("/api/tvt")
async def get_tvt(request: TVTRequest):
    """Get TVT checklist"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    checklist = copilot_kb.get_tvt_checklist(request.vulnerability_id, request.system_type)
    return {"tvt_checklist": checklist}

@app.post("/api/jira-template")
async def get_jira_template(request: JiraTicketRequest):
    """Get Jira ticket template"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    template = copilot_kb.get_jira_ticket_template(request.vulnerability_id, request.team)
    return template

@app.get("/api/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    return copilot_kb.get_cache_stats()

@app.delete("/api/cache/clear")
async def clear_cache():
    """Clear KB cache"""
    if not copilot_kb:
        raise HTTPException(status_code=500, detail="Copilot KB API not initialized")
    
    copilot_kb.clear_cache()
    return {"status": "✅ Cache cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

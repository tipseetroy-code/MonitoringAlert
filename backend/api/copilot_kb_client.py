# backend/api/copilot_kb_client.py
"""
Copilot KB API Client
- Seamless integration for Streamlit frontend
- Caching layer for performance
- Fallback support
"""

import requests
import json
import logging
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class CopilotKBClient:
    """
    Client for Copilot KB API
    Replaces static Excel KB with dynamic AI-powered knowledge
    """
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize API client
        
        Args:
            api_url: API base URL (default: local backend)
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = 30
        
        # Verify API is healthy
        if not self._health_check():
            logger.warning(f"⚠️ Copilot KB API not responding at {api_url}")
    
    def _health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def query_vulnerability(self, vulnerability_id: str, cve: str = "") -> Dict:
        """
        Query vulnerability details from Copilot
        
        Args:
            vulnerability_id: CVE, CWE, or vulnerability name
            cve: Optional CVE ID for context
            
        Returns:
            Vulnerability details dict
        """
        try:
            payload = {
                "vulnerability_id": vulnerability_id,
                "cve": cve
            }
            response = requests.post(
                f"{self.api_url}/api/vulnerability/query",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Error querying vulnerability: {str(e)}")
            return {"error": str(e), "id": vulnerability_id}
    
    def get_remediation(self, vulnerability_id: str, team: str = "") -> str:
        """
        Get remediation guidance
        
        Args:
            vulnerability_id: Vulnerability ID
            team: Target team (MAPS, Middleware, BladeLogic)
            
        Returns:
            Remediation steps as string
        """
        try:
            payload = {
                "vulnerability_id": vulnerability_id,
                "team": team
            }
            response = requests.post(
                f"{self.api_url}/api/remediation",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("remediation", "")
        except Exception as e:
            logger.error(f"❌ Error getting remediation: {str(e)}")
            return str(e)
    
    def classify(self, description: str) -> Dict:
        """
        Classify vulnerability
        
        Args:
            description: Vulnerability description
            
        Returns:
            Classification dict
        """
        try:
            payload = {"description": description}
            response = requests.post(
                f"{self.api_url}/api/classify",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Error classifying: {str(e)}")
            return {"error": str(e)}
    
    def search(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        Search vulnerabilities
        
        Args:
            keyword: Search term
            limit: Max results
            
        Returns:
            List of vulnerability matches
        """
        try:
            payload = {
                "keyword": keyword,
                "limit": limit
            }
            response = requests.post(
                f"{self.api_url}/api/search",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            logger.error(f"❌ Error searching: {str(e)}")
            return []
    
    def get_tvt_checklist(self, vulnerability_id: str, system_type: str = "") -> str:
        """
        Get TVT validation checklist
        
        Args:
            vulnerability_id: Vulnerability ID
            system_type: System type (Windows, Linux, etc.)
            
        Returns:
            TVT checklist
        """
        try:
            payload = {
                "vulnerability_id": vulnerability_id,
                "system_type": system_type
            }
            response = requests.post(
                f"{self.api_url}/api/tvt",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("tvt_checklist", "")
        except Exception as e:
            logger.error(f"❌ Error getting TVT: {str(e)}")
            return str(e)
    
    def get_jira_template(self, vulnerability_id: str, team: str) -> Dict:
        """
        Get Jira ticket template
        
        Args:
            vulnerability_id: Vulnerability ID
            team: Target team
            
        Returns:
            Jira ticket dict
        """
        try:
            payload = {
                "vulnerability_id": vulnerability_id,
                "team": team
            }
            response = requests.post(
                f"{self.api_url}/api/jira-template",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Error getting Jira template: {str(e)}")
            return {"error": str(e)}


# Streamlit Integration Helper
def get_copilot_kb_client(api_url: str = "http://localhost:8000") -> CopilotKBClient:
    """Get or create Copilot KB client for Streamlit"""
    return CopilotKBClient(api_url)

# backend/integrations/sdinfo_client.py
"""
SDInfo Client - Submit service requests for software installation and updates
Used for BladeLogic, Splunk, and other infrastructure software updates
"""

import os
import logging
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SDInfoClient:
    """Client for submitting SDInfo service requests"""
    
    def __init__(self):
        self.sdinfo_url = os.getenv("SDINFO_URL", "https://sdinfo.company.com/api")
        self.sdinfo_api_key = os.getenv("SDINFO_API_KEY", "")
        self.sdinfo_username = os.getenv("SDINFO_USERNAME", "")
        self.sdinfo_password = os.getenv("SDINFO_PASSWORD", "")
        
    def submit_installation_request(
        self,
        title: str,
        description: str,
        asset: str,
        category: str = "Software Installation",
        urgency: str = "High",
        team: str = ""
    ) -> Dict:
        """
        Submit a software installation request to SDInfo
        
        Args:
            title: Request title
            description: Detailed description
            asset: Target asset/server
            category: Request category
            urgency: High/Medium/Low
            team: Assigned team
        
        Returns:
            Dict with request_id and status
        """
        try:
            # Check if SDInfo is configured
            if not self.sdinfo_url or not (self.sdinfo_api_key or self.sdinfo_username):
                logger.warning("⚠️ SDInfo not configured, logging request instead")
                return self._log_request(title, description, asset, category, urgency, team)
            
            # Prepare request payload
            payload = {
                "title": title,
                "description": description,
                "category": category,
                "urgency": urgency,
                "asset": asset,
                "requestor": self.sdinfo_username or "sre_automation",
                "assigned_team": team,
                "type": "installation",
                "status": "open",
                "created_at": datetime.now().isoformat()
            }
            
            # Submit to SDInfo API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.sdinfo_api_key}" if self.sdinfo_api_key else ""
            }
            
            if not self.sdinfo_api_key and self.sdinfo_username:
                # Use basic auth if no API key
                response = requests.post(
                    f"{self.sdinfo_url}/requests",
                    json=payload,
                    auth=(self.sdinfo_username, self.sdinfo_password),
                    timeout=10
                )
            else:
                response = requests.post(
                    f"{self.sdinfo_url}/requests",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            
            response.raise_for_status()
            result = response.json()
            
            request_id = result.get("request_id", result.get("id", "UNKNOWN"))
            logger.info(f"✅ SDInfo request created: {request_id}")
            
            return {
                "success": True,
                "request_id": request_id,
                "url": f"{self.sdinfo_url}/requests/{request_id}",
                "status": "submitted",
                "message": f"SDInfo request {request_id} created successfully"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ SDInfo API error: {e}")
            # Fallback to logging
            return self._log_request(title, description, asset, category, urgency, team)
        
        except Exception as e:
            logger.error(f"❌ Failed to submit SDInfo request: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to submit SDInfo request"
            }
    
    def _log_request(
        self,
        title: str,
        description: str,
        asset: str,
        category: str,
        urgency: str,
        team: str
    ) -> Dict:
        """
        Fallback: Log request details when SDInfo is not available
        Returns mock request ID for tracking
        """
        from datetime import datetime
        import random
        
        request_id = f"SD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        logger.info(f"📋 SDInfo Request (Logged): {request_id}")
        logger.info(f"   Title: {title}")
        logger.info(f"   Asset: {asset}")
        logger.info(f"   Category: {category}")
        logger.info(f"   Urgency: {urgency}")
        logger.info(f"   Team: {team}")
        logger.info(f"   Description: {description[:200]}...")
        
        return {
            "success": True,
            "request_id": request_id,
            "url": f"#sdinfo-request-{request_id}",
            "status": "logged",
            "message": f"Request logged as {request_id} (SDInfo integration pending)"
        }
    
    def check_request_status(self, request_id: str) -> Dict:
        """Check status of an SDInfo request"""
        try:
            headers = {
                "Authorization": f"Bearer {self.sdinfo_api_key}" if self.sdinfo_api_key else ""
            }
            
            response = requests.get(
                f"{self.sdinfo_url}/requests/{request_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "data": response.json()
            }
        except Exception as e:
            logger.error(f"❌ Failed to check SDInfo request: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_sdinfo_client = None

def get_sdinfo_client() -> SDInfoClient:
    """Get or create SDInfo client singleton"""
    global _sdinfo_client
    if _sdinfo_client is None:
        _sdinfo_client = SDInfoClient()
    return _sdinfo_client

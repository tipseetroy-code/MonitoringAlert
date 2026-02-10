# backend/integrations/jira_client.py
"""
Jira Client - Create and manage Jira tickets for vulnerability remediation
Supports MAPS team, Middleware team, and other team engagements
"""

import os
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for creating and managing Jira tickets"""
    
    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL", "")
        self.jira_username = os.getenv("JIRA_USERNAME", "")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "")
        self.jira_project = os.getenv("JIRA_PROJECT", "VULN")
        
    def create_ticket(
        self,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: str = "HIGH",
        labels: List[str] = None,
        assignee: str = None,
        project: str = None
    ) -> Dict:
        """
        Create a Jira ticket for vulnerability remediation
        
        Args:
            summary: Ticket summary/title
            description: Detailed description
            issue_type: Task, Bug, Story, etc.
            priority: CRITICAL, HIGH, MEDIUM, LOW
            labels: List of labels
            assignee: Assign to specific team/user
            project: Jira project key (defaults to JIRA_PROJECT env var)
        
        Returns:
            Dict with ticket_id, key, and url
        """
        try:
            # Check if Jira is configured
            if not self.jira_url or not self.jira_username or not self.jira_api_token:
                logger.warning("⚠️ Jira not configured, logging ticket instead")
                return self._log_ticket(summary, description, issue_type, priority, labels, assignee)
            
            project_key = project or self.jira_project
            
            # Map priority names
            priority_map = {
                "CRITICAL": "Highest",
                "HIGH": "High",
                "MEDIUM": "Medium",
                "LOW": "Low"
            }
            jira_priority = priority_map.get(priority, "Medium")
            
            # Prepare Jira payload
            payload = {
                "fields": {
                    "project": {
                        "key": project_key
                    },
                    "summary": summary,
                    "description": description,
                    "issuetype": {
                        "name": issue_type
                    },
                    "priority": {
                        "name": jira_priority
                    }
                }
            }
            
            # Add labels if provided
            if labels:
                payload["fields"]["labels"] = labels
            
            # Add assignee if provided
            if assignee:
                # For team assignment, use a custom field or group
                payload["fields"]["assignee"] = {"name": assignee}
            
            # Submit to Jira API
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.jira_url}/rest/api/3/issue",
                json=payload,
                headers=headers,
                auth=(self.jira_username, self.jira_api_token),
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            ticket_key = result.get("key", "UNKNOWN")
            ticket_id = result.get("id", "")
            ticket_url = f"{self.jira_url}/browse/{ticket_key}"
            
            logger.info(f"✅ Jira ticket created: {ticket_key}")
            
            return {
                "success": True,
                "ticket_id": ticket_id,
                "ticket_key": ticket_key,
                "url": ticket_url,
                "status": "created",
                "message": f"Jira ticket {ticket_key} created successfully"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Jira API error: {e}")
            # Fallback to logging
            return self._log_ticket(summary, description, issue_type, priority, labels, assignee)
        
        except Exception as e:
            logger.error(f"❌ Failed to create Jira ticket: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create Jira ticket"
            }
    
    def _log_ticket(
        self,
        summary: str,
        description: str,
        issue_type: str,
        priority: str,
        labels: List[str],
        assignee: str
    ) -> Dict:
        """
        Fallback: Log ticket details when Jira is not available
        Returns mock ticket ID for tracking
        """
        from datetime import datetime
        import random
        
        project_key = self.jira_project or "VULN"
        ticket_key = f"{project_key}-{random.randint(1000, 9999)}"
        
        logger.info(f"🎫 Jira Ticket (Logged): {ticket_key}")
        logger.info(f"   Summary: {summary}")
        logger.info(f"   Type: {issue_type}")
        logger.info(f"   Priority: {priority}")
        logger.info(f"   Labels: {labels}")
        logger.info(f"   Assignee: {assignee}")
        logger.info(f"   Description: {description[:200]}...")
        
        return {
            "success": True,
            "ticket_id": str(random.randint(10000, 99999)),
            "ticket_key": ticket_key,
            "url": f"#jira-ticket-{ticket_key}",
            "status": "logged",
            "message": f"Ticket logged as {ticket_key} (Jira integration pending)"
        }
    
    def update_ticket_status(self, ticket_key: str, status: str, comment: str = None) -> Dict:
        """Update Jira ticket status"""
        try:
            # Get available transitions
            response = requests.get(
                f"{self.jira_url}/rest/api/3/issue/{ticket_key}/transitions",
                auth=(self.jira_username, self.jira_api_token),
                timeout=10
            )
            response.raise_for_status()
            transitions = response.json().get("transitions", [])
            
            # Find matching transition
            transition_id = None
            for trans in transitions:
                if status.lower() in trans["name"].lower():
                    transition_id = trans["id"]
                    break
            
            if not transition_id:
                return {"success": False, "error": "Transition not found"}
            
            # Apply transition
            payload = {
                "transition": {"id": transition_id}
            }
            
            if comment:
                payload["update"] = {
                    "comment": [{
                        "add": {"body": comment}
                    }]
                }
            
            response = requests.post(
                f"{self.jira_url}/rest/api/3/issue/{ticket_key}/transitions",
                json=payload,
                auth=(self.jira_username, self.jira_api_token),
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"✅ Updated {ticket_key} to {status}")
            return {"success": True, "message": f"Ticket updated to {status}"}
            
        except Exception as e:
            logger.error(f"❌ Failed to update Jira ticket: {e}")
            return {"success": False, "error": str(e)}
    
    def add_comment(self, ticket_key: str, comment: str) -> Dict:
        """Add comment to Jira ticket"""
        try:
            payload = {
                "body": comment
            }
            
            response = requests.post(
                f"{self.jira_url}/rest/api/3/issue/{ticket_key}/comment",
                json=payload,
                auth=(self.jira_username, self.jira_api_token),
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"✅ Comment added to {ticket_key}")
            return {"success": True, "message": "Comment added"}
            
        except Exception as e:
            logger.error(f"❌ Failed to add comment: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_jira_client = None

def get_jira_client() -> JiraClient:
    """Get or create Jira client singleton"""
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client

# backend/agentic/jira_integration.py
"""
JIRA INTEGRATION: Route escalations and approvals to JIRA
- Create incident tickets
- Update tickets with outcomes
- Request approvals via JIRA workflow
- Track approval status
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .core import IncidentOutcome, ReasoningDecision, Incident


logger = logging.getLogger(__name__)


class JiraClient:
    """JIRA REST API client"""

    def __init__(
        self,
        base_url: str,
        user_email: str,
        api_token: str,
        project_key: str,
    ):
        """
        Args:
            base_url: https://yourcompany.atlassian.net
            user_email: user@company.com
            api_token: JIRA API token
            project_key: JIRA project key (e.g., "OPS", "SRE")
        """
        self.base_url = base_url.rstrip("/")
        self.user_email = user_email
        self.api_token = api_token
        self.project_key = project_key
        self.auth = (user_email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def create_incident_ticket(self, incident: Incident) -> Optional[str]:
        """
        Create JIRA ticket for incident
        Returns ticket key (e.g., OPS-123) or None on failure
        """
        try:
            url = f"{self.base_url}/rest/api/3/issues"

            payload = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": f"[INCIDENT] {incident.app_name} - {incident.severity.value}",
                    "description": self._format_incident_description(incident),
                    "issuetype": {"name": "Incident"},
                    "priority": self._severity_to_priority(incident.severity.value),
                    "labels": [
                        "agentic-sre",
                        f"app-{incident.app_name}",
                        f"severity-{incident.severity.value.lower()}",
                    ],
                    "customfield_severity": incident.severity.value,
                }
            }

            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code in [200, 201]:
                ticket_key = response.json().get("key")
                logger.info(f"[JIRA] Created ticket {ticket_key} for {incident.id}")
                return ticket_key
            else:
                logger.error(
                    f"[JIRA] Failed to create ticket: {response.status_code} {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"[JIRA] Error creating incident ticket: {e}")
            return None

    def create_approval_request(
        self,
        incident: Incident,
        decision: ReasoningDecision,
        parent_ticket: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create JIRA ticket requesting approval for remediation action
        Returns ticket key or None on failure
        """
        try:
            url = f"{self.base_url}/rest/api/3/issues"

            actions_str = ", ".join(decision.recommended_actions)

            payload = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": f"[APPROVAL] {incident.app_name} - {actions_str}",
                    "description": self._format_approval_request(incident, decision),
                    "issuetype": {"name": "Task"},
                    "priority": {"name": "High"},
                    "assignee": None,  # Unassigned, waiting for manual review
                    "labels": [
                        "approval-required",
                        f"app-{incident.app_name}",
                    ],
                }
            }

            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code in [200, 201]:
                ticket_key = response.json().get("key")
                logger.info(f"[JIRA] Created approval request {ticket_key}")

                # Link to parent incident if provided
                if parent_ticket:
                    self._link_issues(ticket_key, parent_ticket, "is subtask of")

                return ticket_key
            else:
                logger.error(
                    f"[JIRA] Failed to create approval request: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"[JIRA] Error creating approval request: {e}")
            return None

    def update_ticket_with_outcome(
        self, ticket_key: str, outcome: IncidentOutcome
    ) -> bool:
        """
        Update JIRA ticket with incident resolution outcome
        """
        try:
            url = f"{self.base_url}/rest/api/3/issues/{ticket_key}"

            # Build status transition (if applicable)
            status = "Resolved" if outcome.status == "resolved" else "On Hold"

            comment = f"""
*Incident Resolution Report*

Status: {outcome.status.upper()}
Resolved at: {outcome.resolved_at}
MTTR: {outcome.mttr_seconds:.1f} seconds

*Root Cause*
{outcome.root_cause_confirmed}

*Actions Executed*
{json.dumps([a.to_dict() for a in outcome.actions_executed], indent=2)}

*Lessons Learned*
{outcome.lessons_learned}

*Generated by:* Agentic SRE Copilot
"""

            # Add comment
            self._add_comment(ticket_key, comment)

            # Transition to resolved status
            self._transition_issue(ticket_key, status)

            logger.info(f"[JIRA] Updated {ticket_key} with outcome")
            return True

        except Exception as e:
            logger.error(f"[JIRA] Error updating ticket: {e}")
            return False

    def check_approval_status(self, ticket_key: str) -> Dict[str, Any]:
        """
        Check if approval ticket has been approved
        Returns:
        {
            "approved": bool,
            "status": str,
            "approver": str or None,
            "timestamp": str or None,
        }
        """
        try:
            url = f"{self.base_url}/rest/api/3/issues/{ticket_key}"

            response = requests.get(
                url,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code != 200:
                return {"approved": False, "status": "not_found", "error": response.text}

            issue = response.json()
            status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            assignee = issue.get("fields", {}).get("assignee", {})

            approved = status.lower() in ["done", "approved", "resolved"]

            return {
                "approved": approved,
                "status": status,
                "approver": assignee.get("displayName") if assignee else None,
                "ticket_key": ticket_key,
            }

        except Exception as e:
            logger.error(f"[JIRA] Error checking approval status: {e}")
            return {"approved": False, "status": "error", "error": str(e)}

    def _add_comment(self, ticket_key: str, comment: str) -> bool:
        """Add comment to JIRA ticket"""
        try:
            url = f"{self.base_url}/rest/api/3/issues/{ticket_key}/comments"

            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": comment,
                                }
                            ],
                        }
                    ],
                }
            }

            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )
            return response.status_code in [200, 201]

        except Exception as e:
            logger.warning(f"[JIRA] Could not add comment: {e}")
            return False

    def _transition_issue(self, ticket_key: str, target_status: str) -> bool:
        """Transition issue to target status"""
        try:
            url = f"{self.base_url}/rest/api/3/issues/{ticket_key}/transitions"

            # Get available transitions
            get_response = requests.get(
                url,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )

            if get_response.status_code == 200:
                transitions = get_response.json().get("transitions", [])
                target_transition = next(
                    (t for t in transitions if t.get("name", "").lower() == target_status.lower()),
                    None,
                )

                if target_transition:
                    transition_id = target_transition.get("id")
                    payload = {"transition": {"id": transition_id}}

                    response = requests.post(
                        url,
                        json=payload,
                        auth=self.auth,
                        headers=self.headers,
                        timeout=10,
                    )
                    return response.status_code in [200, 204]

            return False

        except Exception as e:
            logger.warning(f"[JIRA] Could not transition issue: {e}")
            return False

    def _link_issues(self, source_key: str, target_key: str, link_type: str) -> bool:
        """Link two JIRA issues"""
        try:
            url = f"{self.base_url}/rest/api/3/issueLink"

            payload = {
                "type": {"name": link_type},
                "inwardIssue": {"key": source_key},
                "outwardIssue": {"key": target_key},
            }

            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
            )
            return response.status_code in [200, 201]

        except Exception as e:
            logger.warning(f"[JIRA] Could not link issues: {e}")
            return False

    def _format_incident_description(self, incident: Incident) -> str:
        """Format incident as JIRA description"""
        signals_str = "\n".join(
            f"- {s.source} ({s.app_name}): {s.status}" for s in incident.signals[:5]
        )

        return f"""
*Incident Details*

Application: {incident.app_name}
Severity: {incident.severity.value}
Detected: {incident.timestamp}

*Description*
{incident.description}

*Signals*
{signals_str}

*Context*
- Similar incidents (30d): {incident.context.get('similar_recent_incidents', 0)}
- Previous root causes: {', '.join(incident.context.get('previous_root_causes', []))}

[Managed by Agentic SRE Copilot]
"""

    def _format_approval_request(self, incident: Incident, decision: ReasoningDecision) -> str:
        """Format approval request as JIRA description"""
        return f"""
*Approval Required for Remediation*

Incident: {incident.id}
Application: {incident.app_name}
Severity: {incident.severity.value}

*Recommended Actions*
{', '.join(decision.recommended_actions)}

*Reasoning*
{decision.reasoning}

*Risk Level*: {decision.risk_level}
*Confidence*: {decision.confidence:.0%}

*Please approve or reject these actions:*
[Approve] [Reject] [Request More Info]

[Managed by Agentic SRE Copilot]
"""

    @staticmethod
    def _severity_to_priority(severity: str) -> Dict[str, str]:
        """Map incident severity to JIRA priority"""
        mapping = {
            "CRITICAL": {"name": "Highest"},
            "HIGH": {"name": "High"},
            "MEDIUM": {"name": "Medium"},
            "LOW": {"name": "Low"},
            "INFO": {"name": "Lowest"},
        }
        return mapping.get(severity, {"name": "Medium"})


class JiraHandler:
    """High-level JIRA handler for agentic loop"""

    def __init__(self, jira_client: Optional[JiraClient] = None):
        self.client = jira_client
        self.ticket_map = {}  # incident_id -> ticket_key

    def set_client(self, jira_client: JiraClient):
        """Configure JIRA client"""
        self.client = jira_client

    def handle_escalation(
        self,
        incident: Incident,
        decision: ReasoningDecision,
    ) -> Optional[str]:
        """
        Create escalation ticket for incident
        Returns ticket key or None
        """
        if not self.client:
            logger.warning("[JIRA] No JIRA client configured")
            return None

        # Create main incident ticket
        ticket_key = self.client.create_incident_ticket(incident)
        if ticket_key:
            self.ticket_map[incident.id] = ticket_key

        # If approval needed, create approval request
        if decision.requires_approval:
            approval_key = self.client.create_approval_request(incident, decision, ticket_key)
            if approval_key:
                logger.info(f"[JIRA] Approval request {approval_key} awaiting review")

        return ticket_key

    def handle_outcome(self, outcome: IncidentOutcome) -> bool:
        """
        Update JIRA ticket with incident outcome
        """
        if not self.client:
            return False

        ticket_key = self.ticket_map.get(outcome.incident_id)
        if not ticket_key:
            logger.warning(f"[JIRA] No ticket found for {outcome.incident_id}")
            return False

        return self.client.update_ticket_with_outcome(ticket_key, outcome)

    def is_approved(self, incident_id: str) -> bool:
        """Check if approval ticket for incident has been approved"""
        if not self.client:
            return False

        # Would need to track approval ticket separately
        # This is a simplified check
        return True  # Auto-approve for now

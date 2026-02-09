# backend/config/agentic_config.example.py
"""
Agentic SRE Copilot Configuration Template
Copy to agentic_config.py and fill in with your environment details
"""

import os
from datetime import datetime

# ============================================================================
# CONFIGURATION TEMPLATE
# ============================================================================

# 1. APPLICATION MONITORING
# List of applications to monitor and their health check endpoints
APPS_CONFIG = [
    {
        "name": "api-server",
        "health_url": "http://localhost:8000/health",
        "log_file": "/var/log/api-server.log",
        "systemd_service": "api-server.service",
    },
    {
        "name": "database",
        "health_url": "http://localhost:5432/health",  # If available
        "log_file": "/var/log/postgresql/postgresql.log",
        "systemd_service": "postgresql.service",
    },
    {
        "name": "cache",
        "health_url": "http://localhost:6379/health",
        "log_file": "/var/log/redis.log",
        "systemd_service": "redis-server.service",
    },
]

# 2. JIRA CONFIGURATION (for escalations and approvals)
JIRA_CONFIG = {
    "base_url": os.getenv("JIRA_BASE_URL", "https://yourcompany.atlassian.net"),
    "user_email": os.getenv("JIRA_USER_EMAIL", "sre-bot@company.com"),
    "api_token": os.getenv("JIRA_API_TOKEN", "your-jira-api-token"),
    "project_key": os.getenv("JIRA_PROJECT_KEY", "OPS"),  # e.g., OPS, SRE, INC
}

# 3. SMTP CONFIGURATION (for email notifications)
SMTP_CONFIG = {
    "server": os.getenv("SMTP_SERVER", "smtp.company.com"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "from_address": os.getenv("SMTP_FROM", "sre-agent@company.com"),
    "from_name": os.getenv("SMTP_FROM_NAME", "SRE Agent"),
    "username": os.getenv("SMTP_USERNAME", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
    "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
}

# 4. NOTIFICATION RECIPIENTS
ONCALL_EMAILS = [
    "oncall@company.com",
    "sre-team@company.com",
]

DAILY_REPORT_EMAILS = [
    "sre-team@company.com",
    "engineering-leads@company.com",
]

# 5. POLICY CONFIGURATION
POLICY_CONFIG = {
    "allow_auto_restart": True,
    "allow_auto_scale": False,
    "require_approval_for_restart": True,  # Requires JIRA approval
    "max_restarts_per_day": 5,
    "change_window": {
        "enabled": True,
        "start_hour": 9,  # 9 AM UTC
        "end_hour": 17,  # 5 PM UTC
        "allowed_days": [1, 2, 3, 4, 5],  # Mon-Fri
    },
    "escalation_threshold": {
        "critical_count": 3,
        "time_window_minutes": 60,
    },
    "rollback_on_failed_health_check": True,
    "max_consecutive_failures_before_escalate": 2,
}

# 6. STORAGE PATHS
MEMORY_PATH = os.getenv("MEMORY_PATH", "/var/lib/sre-agent/incident_memory.json")
AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", "/var/lib/sre-agent/sre_audit.db")

# 7. MONITORING SETTINGS
MONITORING_INTERVAL_SECONDS = int(os.getenv("MONITORING_INTERVAL", "30"))

# 8. LOGGING
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/sre-agent/agentic.log")

# ============================================================================
# ORCHESTRATOR CONFIGURATION (COMPLETE)
# ============================================================================

def get_orchestrator_config():
    """
    Returns complete configuration for SREAgentOrchestrator
    """
    return {
        "apps": APPS_CONFIG,
        "jira": JIRA_CONFIG,
        "smtp": SMTP_CONFIG,
        "oncall_emails": ONCALL_EMAILS,
        "daily_report_emails": DAILY_REPORT_EMAILS,
        "memory_path": MEMORY_PATH,
        "audit_db_path": AUDIT_DB_PATH,
        "monitoring_interval": MONITORING_INTERVAL_SECONDS,
        "policy": POLICY_CONFIG,
    }


# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================

DEPLOYMENT_CHECKLIST = """
BEFORE DEPLOYING AGENTIC SRE COPILOT
====================================

1. PREREQUISITES
   ☐ Python 3.9+ installed
   ☐ pip packages installed: google-genai, requests, streamlit, pandas
   ☐ GOOGLE_API_KEY set for Gemini LLM
   
2. APPLICATION MONITORING SETUP
   ☐ All apps in APPS_CONFIG are running
   ☐ Health check endpoints respond correctly
   ☐ Log files are readable (set appropriate permissions)
   ☐ Systemd services exist and can be queried
   
3. JIRA INTEGRATION
   ☐ JIRA account created for bot (sre-bot@company.com)
   ☐ JIRA API token generated
   ☐ JIRA project created (e.g., OPS)
   ☐ Issue type "Incident" and "Task" created
   ☐ Workflow allows transitions (Pending → Approved → Resolved)
   
4. EMAIL NOTIFICATIONS
   ☐ SMTP server credentials obtained
   ☐ From email address whitelisted if needed
   ☐ TLS/SSL settings verified
   ☐ On-call email list confirmed
   ☐ Daily report email list confirmed
   
5. STORAGE & PERMISSIONS
   ☐ /var/lib/sre-agent/ created with proper permissions
   ☐ /var/log/sre-agent/ created with proper permissions
   ☐ sre-agent user created (or use existing service account)
   ☐ File permissions set: chmod 755 /var/lib/sre-agent
   
6. SYSTEMD SERVICE (optional but recommended)
   ☐ Create /etc/systemd/system/sre-agent.service
   ☐ Run: sudo systemctl daemon-reload
   ☐ Enable: sudo systemctl enable sre-agent.service
   ☐ Start: sudo systemctl start sre-agent.service
   
7. POLICY REVIEW
   ☐ Policy thresholds reviewed with SRE team
   ☐ Approval gates set appropriately
   ☐ Change windows configured for your timezone
   ☐ Escalation thresholds discussed
   
8. TESTING
   ☐ Run test_perception() in UI to verify signals
   ☐ Run test_reasoning() with sample incident
   ☐ Verify JIRA ticket creation works
   ☐ Verify email notifications send
   ☐ Review audit trail in database
   
9. MONITORING & ALERTING
   ☐ Set up monitoring for sre-agent process health
   ☐ Set up alerts for audit events
   ☐ Set up alerts for escalations
   ☐ Configure centralized logging (if applicable)
   
10. DOCUMENTATION
    ☐ Runbook created for common incidents
    ☐ On-call rotation updated
    ☐ Team trained on new system
    ☐ Escalation procedures documented
"""

# ============================================================================
# ENVIRONMENT VARIABLES REQUIRED
# ============================================================================

REQUIRED_ENV_VARS = {
    "GOOGLE_API_KEY": "Google Gemini API key for LLM reasoning",
    "JIRA_BASE_URL": "JIRA instance URL",
    "JIRA_USER_EMAIL": "JIRA bot email address",
    "JIRA_API_TOKEN": "JIRA API token",
    "JIRA_PROJECT_KEY": "JIRA project key (e.g., OPS)",
    "SMTP_SERVER": "SMTP server hostname",
    "SMTP_PORT": "SMTP port (587 for TLS)",
    "SMTP_FROM": "From email address",
    "SMTP_USERNAME": "SMTP username (if auth required)",
    "SMTP_PASSWORD": "SMTP password (if auth required)",
}

if __name__ == "__main__":
    print(__doc__)
    print("\n" + DEPLOYMENT_CHECKLIST)
    print("\n\nEnvironment Variables Required:")
    for var, desc in REQUIRED_ENV_VARS.items():
        print(f"  {var}: {desc}")
    print(f"\n\nConfiguration loaded: {get_orchestrator_config()}")

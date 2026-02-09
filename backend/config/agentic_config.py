# backend/config/agentic_config.py
"""
Agentic SRE Copilot Configuration
Loaded from environment variables for production use.
"""

import os


# 1. APPLICATION MONITORING
APPS_CONFIG = [
    {
        "name": "api-server",
        "health_url": "http://localhost:8000/health",
        "log_file": "/var/log/api-server.log",
        "systemd_service": "api-server.service",
    },
    {
        "name": "database",
        "health_url": "http://localhost:5432/health",
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

# 2. JIRA CONFIGURATION
JIRA_CONFIG = {
    "base_url": os.getenv("JIRA_BASE_URL", "https://yourcompany.atlassian.net"),
    "user_email": os.getenv("JIRA_USER_EMAIL", "sre-bot@company.com"),
    "api_token": os.getenv("JIRA_API_TOKEN", "your-jira-api-token"),
    "project_key": os.getenv("JIRA_PROJECT_KEY", "OPS"),
}

# 3. SMTP CONFIGURATION
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

def _parse_email_list(value: str) -> list:
    return [email.strip() for email in value.split(",") if email.strip()]


ONCALL_EMAILS = _parse_email_list(
    os.getenv("ONCALL_EMAILS", "oncall@company.com,sre-team@company.com")
)

DAILY_REPORT_EMAILS = _parse_email_list(
    os.getenv("DAILY_REPORT_EMAILS", "sre-team@company.com,engineering-leads@company.com")
)

# 5. POLICY CONFIGURATION
POLICY_CONFIG = {
    "allow_auto_restart": True,
    "allow_auto_scale": False,
    "require_approval_for_restart": True,
    "max_restarts_per_day": 5,
    "change_window": {
        "enabled": True,
        "start_hour": 9,
        "end_hour": 17,
        "allowed_days": [1, 2, 3, 4, 5],
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

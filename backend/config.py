# Confluence Knowledge Base URL
CONFLUENCE_KB_URL = "https://teammeenakshi.atlassian.net/wiki/x/AgAH"
# config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AgentConfig:
    # Labels
    host_label: str = os.getenv("HOST_LABEL", "windows-demo-host")

    # Email
    to_email: str = os.getenv("TO_EMAIL", "abhigyanpal98@gmail.com")

    # URL backend
    backend_url: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    backend_host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))

    # Thresholds 
    cpu_threshold_pct: float = float(os.getenv("CPU_THRESHOLD_PCT", "20.0"))
    cpu_duration_seconds: int = int(os.getenv("CPU_DURATION_SECONDS", "3"))
    disk_threshold_pct: float = float(os.getenv("DISK_THRESHOLD_PCT", "20.0"))

    # Safe actions allowed (demo policy)
    allow_kill_process: bool = False
    allow_clear_temp: bool = True
    allow_restart_service: bool = True

    # URL remediation policy
    allow_backend_self_heal: bool = True

    # Google Search API
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    search_engine_id: str = os.getenv("SEARCH_ENGINE_ID", "")

    # Dummy Confluence KB for apps
    confluence_kb = {
        "web-app": {
            "restart_condition": "disk > 80% or url_down",
            "logs_to_clear": ["/var/log/web-app.log", "/tmp/web-app-temp.log"],
            "supporting_dirs": ["/var/www/web-app", "/var/data/web-app"],
            "restart_command": "systemctl restart web-app"
        },
        "api-service": {
            "restart_condition": "cpu > 90% or memory > 85%",
            "logs_to_clear": ["/var/log/api-service.log"],
            "supporting_dirs": ["/opt/api-service"],
            "restart_command": "systemctl restart api-service"
        }
    }

    # Dummy AutoSys jobs
    autosys_jobs = {
        "daily_backup": {"status": "SUCCESS", "last_run": "2026-01-31 10:00", "schedule": "daily 2am"},
        "data_sync": {"status": "RUNNING", "last_run": "2026-01-31 12:00", "schedule": "hourly"}
    }

    # Dummy SSL certificates
    ssl_certs = {
        "example.com": {"expiry": "2025-12-31", "vault_path": "/vault/certs/example.com", "renewal_script": "certbot renew example.com"},
        "api.example.com": {"expiry": "2026-06-15", "vault_path": "/vault/certs/api.example.com", "renewal_script": "certbot renew api.example.com"}
    }

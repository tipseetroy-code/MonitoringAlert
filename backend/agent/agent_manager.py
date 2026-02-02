from datetime import datetime
from ..services.storage import INCIDENTS, AGENT_RUNNING
from .detector import detect_cpu_issue, detect_disk_issue
from .remediator import remediate
from .notifier import send_email
from ..monitors.http_monitors import monitor_endpoints
import requests
import os
import threading
import time

def trigger_power_automate(incident: dict):
    """Trigger Power Automate flow with incident data."""
    pa_url = os.getenv("POWER_AUTOMATE_WEBHOOK_URL")
    if pa_url:
        try:
            requests.post(pa_url, json=incident, timeout=10)
        except Exception as e:
            print(f"Failed to trigger Power Automate: {e}")

def monitor_loop():
    while AGENT_RUNNING:
        # Check CPU
        incident = detect_cpu_issue()
        if incident:
            action, exit_code = remediate(incident)
            email_status = send_email(incident)
            full_incident = {
                "host": "linux-server-01",
                "type": "CPU 100%",
                "severity": "Critical",
                "detected_at": datetime.now().isoformat(),
                "decision": "Auto Remediation",
                "remediation": action,
                "exit_code": exit_code,
                "email_sent": email_status
            }
            INCIDENTS.append(full_incident)
            trigger_power_automate(full_incident)

        # Check Disk
        disk_incident = detect_disk_issue()
        if disk_incident:
            action, exit_code = remediate(disk_incident)
            email_status = send_email(disk_incident)
            full_incident = {
                "host": "linux-server-01",
                "type": f"Disk {disk_incident['value']}%",
                "severity": "High",
                "detected_at": datetime.now().isoformat(),
                "decision": "Auto Remediation",
                "remediation": action,
                "exit_code": exit_code,
                "email_sent": email_status
            }
            INCIDENTS.append(full_incident)
            trigger_power_automate(full_incident)

        # Check HTTP endpoints
        endpoints = [
            "http://18.237.102.97:9081/users",
            "http://18.237.102.97:9082/orders",
            "http://18.237.102.97:9083/products",
            "http://18.237.102.97:9084/notifications"
        ]
        http_incidents = monitor_endpoints(endpoints)
        for inc in http_incidents:
            full_incident = {
                "host": "ec2-instance",
                "type": inc["type"],
                "severity": inc["severity"],
                "detected_at": inc["timestamp"].isoformat(),
                "decision": "Monitor Only",
                "details": inc["details"]
            }
            INCIDENTS.append(full_incident)
            send_email({"type": inc["type"], "details": inc["details"], "severity": inc["severity"]})
            trigger_power_automate(full_incident)

        time.sleep(60)  # Monitor every 60 seconds

def start_agent(config):
    global AGENT_RUNNING
    if not AGENT_RUNNING:
        AGENT_RUNNING = True
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

def stop_agent():
    global AGENT_RUNNING
    AGENT_RUNNING = False

def simulate_incident():
    # Check CPU
    incident = detect_cpu_issue()
    if incident:
        action, exit_code = remediate(incident)
        email_status = send_email(incident)
        full_incident = {
            "host": "linux-server-01",
            "type": "CPU 100%",
            "severity": "Critical",
            "detected_at": datetime.now().isoformat(),
            "decision": "Auto Remediation",
            "remediation": action,
            "exit_code": exit_code,
            "email_sent": email_status
        }
        INCIDENTS.append(full_incident)
        trigger_power_automate(full_incident)

    # Check Disk
    disk_incident = detect_disk_issue()
    if disk_incident:
        action, exit_code = remediate(disk_incident)
        email_status = send_email(disk_incident)
        full_incident = {
            "host": "linux-server-01",
            "type": f"Disk {disk_incident['value']}%",
            "severity": "High",
            "detected_at": datetime.now().isoformat(),
            "decision": "Auto Remediation",
            "remediation": action,
            "exit_code": exit_code,
            "email_sent": email_status
        }
        INCIDENTS.append(full_incident)
        trigger_power_automate(full_incident)

    # Check HTTP endpoints
    endpoints = [
        "http://18.237.102.97:9081/users",
        "http://18.237.102.97:9082/orders",
        "http://18.237.102.97:9083/products",
        "http://18.237.102.97:9084/notifications"
    ]
    http_incidents = monitor_endpoints(endpoints)
    for inc in http_incidents:
        full_incident = {
            "host": "ec2-instance",
            "type": inc["type"],
            "severity": inc["severity"],
            "detected_at": inc["timestamp"].isoformat(),
            "decision": "Monitor Only",
            "details": inc["details"]
        }
        INCIDENTS.append(full_incident)
        send_email({"type": inc["type"], "details": inc["details"], "severity": inc["severity"]})
        trigger_power_automate(full_incident)

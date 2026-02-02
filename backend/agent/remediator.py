import os
import shutil
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from ..config import AgentConfig

def send_notification(subject, body, to_email):
    config = AgentConfig()
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config.to_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP('localhost')  # Assuming local SMTP
        server.sendmail(config.to_email, [to_email], msg.as_string())
        server.quit()
        return True
    except:
        return False

def check_confluence_kb(app_name, issue):
    config = AgentConfig()
    app_data = config.confluence_kb.get(app_name, {})
    if issue == "disk" and "disk > 80%" in app_data.get("restart_condition", ""):
        return app_data
    elif issue == "url_down" and "url_down" in app_data.get("restart_condition", ""):
        return app_data
    return None

def clear_logs(logs):
    cleared = 0
    for log_path in logs:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'w') as f:
                    f.write("")  # Clear log
                cleared += 1
            except:
                pass
    return cleared

def ensure_dirs(dirs):
    created = 0
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            created += 1
    return created

def simulate_restart(command):
    # Simulate restart
    return f"Simulated: {command}"

def handle_autosys(action, job_name=None):
    config = AgentConfig()
    if action == "create" and job_name:
        config.autosys_jobs[job_name] = {"status": "CREATED", "last_run": str(datetime.now()), "schedule": "manual"}
        return f"Created AutoSys job: {job_name}"
    elif action == "fetch" and job_name:
        return config.autosys_jobs.get(job_name, "Job not found")
    elif action == "restart":
        # Simulate restart
        return "AutoSys scheduler restarted"
    return "Invalid AutoSys action"

def handle_ssl_renewal(domain):
    config = AgentConfig()
    cert = config.ssl_certs.get(domain)
    if cert:
        # Send pre-notification
        send_notification(f"SSL Renewal Starting for {domain}", f"Renewal script: {cert['renewal_script']}", config.to_email)
        # Simulate renewal
        result = f"Simulated SSL renewal for {domain}"
        # Send post-notification
        send_notification(f"SSL Renewal Completed for {domain}", result, config.to_email)
        return result
    return "Certificate not found"

def remediate(incident):
    config = AgentConfig()
    
    if incident.get("metric") == "CPU":
        # Demo: restart service
        result = "Restarted service (demo)"
        send_notification("Incident Remediation", f"CPU issue resolved: {result}", config.to_email)
        return result, 0
    elif incident.get("metric") == "Disk" and config.allow_clear_temp:
        # Clear temp files
        temp_dirs = ["/tmp", "/var/tmp"]
        cleared_space = 0
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                            cleared_space += 1
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                            cleared_space += 1
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")
        result = f"Cleared {cleared_space} temp files"
        send_notification("Disk Cleanup Completed", result, config.to_email)
        return result, 0
    elif incident.get("type") == "url_down":
        app_name = incident.get("app", "web-app")
        kb_data = check_confluence_kb(app_name, "url_down")
        if kb_data:
            # Check if disk issue
            if "disk" in str(incident.get("details", "")):
                logs_cleared = clear_logs(kb_data.get("logs_to_clear", []))
                restart_result = simulate_restart(kb_data.get("restart_command", ""))
                result = f"Cleared {logs_cleared} logs and {restart_result}"
            else:
                restart_result = simulate_restart(kb_data.get("restart_command", ""))
                result = f"Restarted app: {restart_result}"
            send_notification("URL Down Remediation", result, config.to_email)
            return result, 0
    elif incident.get("type") == "deployment":
        app_name = incident.get("app", "web-app")
        kb_data = config.confluence_kb.get(app_name, {})
        dirs_created = ensure_dirs(kb_data.get("supporting_dirs", []))
        restart_result = simulate_restart(kb_data.get("restart_command", ""))
        result = f"Ensured {dirs_created} supporting directories and {restart_result}"
        send_notification("Deployment Remediation", result, config.to_email)
        return result, 0
    else:
        return "No remediation available", 1

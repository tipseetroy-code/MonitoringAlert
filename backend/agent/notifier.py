import smtplib
from email.mime.text import MIMEText
from ..config import AgentConfig

def validate_incident(incident):
    """Validate incident before sending email."""
    required_fields = ["type", "severity"]
    for field in required_fields:
        if field not in incident:
            return False, f"Missing required field: {field}"
    
    if incident["severity"] not in ["Low", "Medium", "High", "Critical"]:
        return False, f"Invalid severity: {incident['severity']}"
    
    return True, "Valid"

def send_email(incident):
    # Validate incident
    is_valid, message = validate_incident(incident)
    if not is_valid:
        print(f"Email not sent: {message}")
        return False
    
    config = AgentConfig()
    
    # Create message
    subject = f"Monitoring Alert: {incident['type']} - {incident['severity']}"
    body = f"""
Monitoring Alert

Type: {incident['type']}
Severity: {incident['severity']}
Details: {incident.get('details', 'N/A')}
Detected At: {incident.get('detected_at', 'N/A')}

This is an automated alert from the Monitoring System.
"""
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "alerts@monitoring.com"  # Change as needed
    msg['To'] = config.to_email
    
    try:
        # SMTP server (example: Gmail - requires app password)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your-email@gmail.com', 'your-app-password')  # Replace with actual
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        print(f"Email sent to {config.to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

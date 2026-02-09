# backend/agentic/notifications.py
"""
NOTIFICATIONS: SMTP-based incident alerting and reporting
- Alert on critical incidents
- Resolution notifications
- Daily/weekly reports
- On-call escalations
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime

from .core import IncidentOutcome, Incident


logger = logging.getLogger(__name__)


class SMTPNotifier:
    """SMTP-based email notifications"""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        from_address: str,
        from_name: str = "SRE Agent",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
    ):
        """
        Args:
            smtp_server: SMTP server hostname (e.g., smtp.gmail.com)
            smtp_port: SMTP port (587 for TLS, 465 for SSL)
            from_address: sender email address
            from_name: sender display name
            username: SMTP auth username (if required)
            password: SMTP auth password (if required)
            use_tls: use TLS encryption
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.from_name = from_name
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send_incident_alert(
        self,
        incident: Incident,
        recipients: List[str],
        escalation_ticket: Optional[str] = None,
    ) -> bool:
        """
        Send incident alert email
        """
        try:
            html_body = self._format_incident_alert_html(incident, escalation_ticket)
            subject = f"🚨 [{incident.severity.value}] {incident.app_name} Incident Alert"

            return self._send_email(subject, html_body, recipients)

        except Exception as e:
            logger.error(f"[NOTIFICATIONS] Error sending incident alert: {e}")
            return False

    def send_resolution_notification(
        self,
        outcome: IncidentOutcome,
        recipients: List[str],
        duration_seconds: float,
    ) -> bool:
        """
        Send incident resolution email
        """
        try:
            html_body = self._format_resolution_html(outcome, duration_seconds)
            subject = f"✅ Incident {outcome.incident_id} Resolved"

            return self._send_email(subject, html_body, recipients)

        except Exception as e:
            logger.error(f"[NOTIFICATIONS] Error sending resolution: {e}")
            return False

    def send_daily_report(
        self,
        incidents_today: List[Dict[str, Any]],
        recipients: List[str],
    ) -> bool:
        """
        Send daily incident summary report
        """
        try:
            html_body = self._format_daily_report_html(incidents_today)
            subject = f"📊 SRE Daily Report - {datetime.utcnow().strftime('%Y-%m-%d')}"

            return self._send_email(subject, html_body, recipients)

        except Exception as e:
            logger.error(f"[NOTIFICATIONS] Error sending daily report: {e}")
            return False

    def _send_email(
        self,
        subject: str,
        html_body: str,
        recipients: List[str],
    ) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = ", ".join(recipients)
            msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # Attach HTML body
            msg.attach(MIMEText(html_body, "html"))

            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()

                if self.username and self.password:
                    server.login(self.username, self.password)

                server.sendmail(self.from_address, recipients, msg.as_string())

            logger.info(f"[NOTIFICATIONS] Sent email to {', '.join(recipients)}")
            return True

        except Exception as e:
            logger.error(f"[NOTIFICATIONS] SMTP error: {e}")
            return False

    @staticmethod
    def _format_incident_alert_html(
        incident: Incident, escalation_ticket: Optional[str] = None
    ) -> str:
        """Format incident alert HTML email"""
        signals_html = ""
        for signal in incident.signals[:5]:
            signals_html += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">{signal.source}</td>
                <td style="padding:8px;border:1px solid #ddd;">{signal.app_name}</td>
                <td style="padding:8px;border:1px solid #ddd;">
                    <span style="padding:4px 8px;border-radius:4px;
                    {SMTPNotifier._status_style(signal.status)}">{signal.status.upper()}</span>
                </td>
                <td style="padding:8px;border:1px solid #ddd;">{signal.timestamp}</td>
            </tr>
            """

        ticket_html = ""
        if escalation_ticket:
            ticket_html = f"""
            <p><strong>Escalation Ticket:</strong> <a href="#">{escalation_ticket}</a></p>
            """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>🚨 Incident Alert</h2>

            <table style="border-collapse:collapse;margin:16px 0;">
                <tr style="background:#f5f5f5;">
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Incident ID</td>
                    <td style="padding:8px;border:1px solid #ddd;">{incident.id}</td>
                </tr>
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Application</td>
                    <td style="padding:8px;border:1px solid #ddd;">{incident.app_name}</td>
                </tr>
                <tr style="background:#f5f5f5;">
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Severity</td>
                    <td style="padding:8px;border:1px solid #ddd;">
                        <span style="padding:4px 8px;border-radius:4px;
                        {SMTPNotifier._severity_style(incident.severity.value)}">
                        {incident.severity.value}</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Detected</td>
                    <td style="padding:8px;border:1px solid #ddd;">{incident.timestamp}</td>
                </tr>
            </table>

            <h3>Description</h3>
            <p>{incident.description}</p>

            <h3>Detected Signals</h3>
            <table style="border-collapse:collapse;width:100%;">
                <tr style="background:#f5f5f5;">
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Source</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">App</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Status</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Time</th>
                </tr>
                {signals_html}
            </table>

            {ticket_html}

            <hr style="margin:24px 0;">
            <p style="color:#666;font-size:12px;">
                Generated by Agentic SRE Copilot at {datetime.utcnow().isoformat()}Z
            </p>
        </body>
        </html>
        """

    @staticmethod
    def _format_resolution_html(
        outcome: IncidentOutcome, duration_seconds: float
    ) -> str:
        """Format resolution notification HTML email"""
        actions_html = ""
        for exe in outcome.actions_executed:
            status_badge = (
                '<span style="color:green;font-weight:bold;">✓ Success</span>'
                if exe.success
                else '<span style="color:red;font-weight:bold;">✗ Failed</span>'
            )
            actions_html += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">{exe.action_id}</td>
                <td style="padding:8px;border:1px solid #ddd;">{exe.executed_at}</td>
                <td style="padding:8px;border:1px solid #ddd;">{status_badge}</td>
                <td style="padding:8px;border:1px solid #ddd;">{exe.execution_time_ms:.0f}ms</td>
            </tr>
            """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>✅ Incident Resolved</h2>

            <table style="border-collapse:collapse;margin:16px 0;">
                <tr style="background:#f5f5f5;">
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Incident ID</td>
                    <td style="padding:8px;border:1px solid #ddd;">{outcome.incident_id}</td>
                </tr>
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Status</td>
                    <td style="padding:8px;border:1px solid #ddd;">
                        <span style="color:green;font-weight:bold;">{outcome.status.upper()}</span>
                    </td>
                </tr>
                <tr style="background:#f5f5f5;">
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">MTTR</td>
                    <td style="padding:8px;border:1px solid #ddd;">{outcome.mttr_seconds:.1f}s</td>
                </tr>
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Resolved</td>
                    <td style="padding:8px;border:1px solid #ddd;">{outcome.resolved_at}</td>
                </tr>
            </table>

            <h3>Root Cause</h3>
            <p>{outcome.root_cause_confirmed}</p>

            <h3>Actions Executed</h3>
            <table style="border-collapse:collapse;width:100%;">
                <tr style="background:#f5f5f5;">
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Action ID</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Executed</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Status</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Duration</th>
                </tr>
                {actions_html}
            </table>

            <h3>Lessons Learned</h3>
            <p>{outcome.lessons_learned}</p>

            <hr style="margin:24px 0;">
            <p style="color:#666;font-size:12px;">
                Generated by Agentic SRE Copilot at {datetime.utcnow().isoformat()}Z
            </p>
        </body>
        </html>
        """

    @staticmethod
    def _format_daily_report_html(incidents_today: List[Dict[str, Any]]) -> str:
        """Format daily report HTML email"""
        incidents_html = ""
        total_mttr = 0
        resolved_count = 0

        for inc in incidents_today:
            status = inc.get("status", "unknown")
            severity = inc.get("severity", "INFO")
            incidents_html += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">{inc.get('id', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">{inc.get('app_name', 'N/A')}</td>
                <td style="padding:8px;border:1px solid #ddd;">
                    <span style="padding:4px 8px;border-radius:4px;
                    {SMTPNotifier._severity_style(severity)}">{severity}</span>
                </td>
                <td style="padding:8px;border:1px solid #ddd;">{inc.get('mttr_seconds', 'N/A'):.1f}s</td>
                <td style="padding:8px;border:1px solid #ddd;">{status}</td>
            </tr>
            """
            if status == "resolved":
                resolved_count += 1
                total_mttr += inc.get("mttr_seconds", 0)

        avg_mttr = total_mttr / resolved_count if resolved_count > 0 else 0

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>📊 SRE Daily Report</h2>
            <p><strong>Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d')}</p>

            <h3>Summary</h3>
            <ul>
                <li><strong>Total Incidents:</strong> {len(incidents_today)}</li>
                <li><strong>Resolved:</strong> {resolved_count}</li>
                <li><strong>Average MTTR:</strong> {avg_mttr:.1f}s</li>
            </ul>

            <h3>Incidents</h3>
            <table style="border-collapse:collapse;width:100%;">
                <tr style="background:#f5f5f5;">
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Incident ID</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Application</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Severity</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">MTTR</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Status</th>
                </tr>
                {incidents_html}
            </table>

            <hr style="margin:24px 0;">
            <p style="color:#666;font-size:12px;">
                Generated by Agentic SRE Copilot at {datetime.utcnow().isoformat()}Z
            </p>
        </body>
        </html>
        """

    @staticmethod
    def _severity_style(severity: str) -> str:
        """CSS style for severity badge"""
        styles = {
            "CRITICAL": "background-color:#fee2e2;color:#7f1d1d;border:1px solid #7f1d1d;",
            "HIGH": "background-color:#ffedd5;color:#9a3412;border:1px solid #9a3412;",
            "MEDIUM": "background-color:#fef3c7;color:#92400e;border:1px solid #92400e;",
            "LOW": "background-color:#dbeafe;color:#1d4ed8;border:1px solid #1d4ed8;",
            "INFO": "background-color:#f3f4f6;color:#374151;border:1px solid #374151;",
        }
        return styles.get(severity, styles["INFO"])

    @staticmethod
    def _status_style(status: str) -> str:
        """CSS style for status badge"""
        styles = {
            "healthy": "background-color:#dcfce7;color:#166534;border:1px solid #166534;",
            "degraded": "background-color:#fef08a;color:#854d0e;border:1px solid #854d0e;",
            "unhealthy": "background-color:#fed7aa;color:#9a3412;border:1px solid #9a3412;",
            "critical": "background-color:#fecaca;color:#7f1d1d;border:1px solid #7f1d1d;",
        }
        return styles.get(status, styles["healthy"])


class NotificationHandler:
    """High-level notification coordinator"""

    def __init__(self, notifier: Optional[SMTPNotifier] = None):
        self.notifier = notifier
        self.oncall_recipients: List[str] = []
        self.daily_report_recipients: List[str] = []

    def set_notifier(self, notifier: SMTPNotifier):
        """Configure SMTP notifier"""
        self.notifier = notifier

    def set_recipients(
        self, oncall: List[str], daily_report: List[str]
    ):
        """Configure notification recipients"""
        self.oncall_recipients = oncall
        self.daily_report_recipients = daily_report

    def notify_incident(
        self,
        incident: Incident,
        escalation_ticket: Optional[str] = None,
    ) -> bool:
        """Notify on-call about incident"""
        if not self.notifier or not self.oncall_recipients:
            return False

        return self.notifier.send_incident_alert(
            incident, self.oncall_recipients, escalation_ticket
        )

    def notify_resolution(
        self,
        outcome: IncidentOutcome,
        duration_seconds: float,
    ) -> bool:
        """Notify stakeholders about resolution"""
        if not self.notifier or not self.oncall_recipients:
            return False

        return self.notifier.send_resolution_notification(
            outcome, self.oncall_recipients, duration_seconds
        )

    def send_daily_report(self, incidents_today: List[Dict[str, Any]]) -> bool:
        """Send daily incident summary"""
        if not self.notifier or not self.daily_report_recipients:
            return False

        return self.notifier.send_daily_report(incidents_today, self.daily_report_recipients)

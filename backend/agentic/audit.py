# backend/agentic/audit.py
"""
AUDIT & REPORTING: Compliance and observability layer
- Complete audit trail of decisions and actions
- Compliance reporting
- Performance metrics and dashboards
- Post-incident reviews
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3
import os


logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """Single audit event"""

    timestamp: str
    event_type: str  # "incident_detected", "decision_made", "action_executed", "outcome_recorded"
    incident_id: str
    actor: str  # "perception_engine", "llm_reasoner", "executor", "system"
    action: str
    details: Dict[str, Any]
    result: str  # "success", "failed", "pending"
    user: Optional[str] = None  # Human user if manual approval

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "incident_id": self.incident_id,
            "actor": self.actor,
            "action": self.action,
            "details": self.details,
            "result": self.result,
            "user": self.user,
        }


class AuditLogger:
    """Persistent audit trail storage"""

    def __init__(self, db_path: str = "/tmp/sre_audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite audit database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    incident_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    result TEXT,
                    user TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_incident_id ON audit_events(incident_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)
                """
            )

            conn.commit()
            conn.close()
            logger.info(f"[AUDIT] Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"[AUDIT] Failed to initialize database: {e}")

    def log_event(self, event: AuditEvent) -> bool:
        """Log audit event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_events
                (timestamp, event_type, incident_id, actor, action, details, result, user)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp,
                    event.event_type,
                    event.incident_id,
                    event.actor,
                    event.action,
                    json.dumps(event.details),
                    event.result,
                    event.user,
                ),
            )

            conn.commit()
            conn.close()
            logger.debug(f"[AUDIT] Logged event: {event.event_type} for {event.incident_id}")
            return True

        except Exception as e:
            logger.error(f"[AUDIT] Failed to log event: {e}")
            return False

    def get_incident_audit_trail(self, incident_id: str) -> List[Dict]:
        """Get all audit events for an incident"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM audit_events
                WHERE incident_id = ?
                ORDER BY timestamp ASC
                """,
                (incident_id,),
            )

            events = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return events

        except Exception as e:
            logger.error(f"[AUDIT] Failed to retrieve audit trail: {e}")
            return []

    def get_events_by_date_range(
        self, start_date: str, end_date: str, event_type: Optional[str] = None
    ) -> List[Dict]:
        """Get audit events within date range"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if event_type:
                cursor.execute(
                    """
                    SELECT * FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ? AND event_type = ?
                    ORDER BY timestamp DESC
                    """,
                    (start_date, end_date, event_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp DESC
                    """,
                    (start_date, end_date),
                )

            events = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return events

        except Exception as e:
            logger.error(f"[AUDIT] Failed to retrieve events: {e}")
            return []


class ComplianceReporter:
    """Generate compliance and audit reports"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def generate_incident_report(self, incident_id: str) -> Dict[str, Any]:
        """
        Generate compliance-ready incident report
        """
        audit_trail = self.audit.get_incident_audit_trail(incident_id)

        timeline = []
        for event in audit_trail:
            timeline.append(
                {
                    "timestamp": event["timestamp"],
                    "phase": event["event_type"],
                    "actor": event["actor"],
                    "action": event["action"],
                    "result": event["result"],
                }
            )

        return {
            "incident_id": incident_id,
            "generated_at": datetime.utcnow().isoformat(),
            "audit_trail_length": len(audit_trail),
            "timeline": timeline,
            "raw_events": [dict(e) for e in audit_trail],
        }

    def generate_compliance_report(
        self, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit period
        Shows all decisions, approvals, escalations
        """
        events = self.audit.get_events_by_date_range(start_date, end_date)

        decision_count = sum(1 for e in events if e["event_type"] == "decision_made")
        action_count = sum(1 for e in events if e["event_type"] == "action_executed")
        escalation_count = sum(
            1 for e in events if e["actor"] == "jira_handler"
        )
        approval_count = sum(1 for e in events if e["user"] is not None)

        return {
            "report_period": {"start": start_date, "end": end_date},
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_events": len(events),
                "decision_count": decision_count,
                "action_count": action_count,
                "escalation_count": escalation_count,
                "approval_count": approval_count,
            },
            "events_by_type": self._group_by_type(events),
            "events_by_actor": self._group_by_actor(events),
        }

    def _group_by_type(self, events: List[Dict]) -> Dict[str, int]:
        """Group events by type"""
        result = {}
        for event in events:
            event_type = event["event_type"]
            result[event_type] = result.get(event_type, 0) + 1
        return result

    def _group_by_actor(self, events: List[Dict]) -> Dict[str, int]:
        """Group events by actor"""
        result = {}
        for event in events:
            actor = event["actor"]
            result[actor] = result.get(actor, 0) + 1
        return result


class PerformanceMetrics:
    """Track SRE copilot performance metrics"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def calculate_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate performance metrics for period
        """
        end_date = datetime.utcnow().isoformat()
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        events = self.audit.get_events_by_date_range(start_date, end_date)

        # Group by incident
        incidents = {}
        for event in events:
            inc_id = event["incident_id"]
            if inc_id not in incidents:
                incidents[inc_id] = []
            incidents[inc_id].append(event)

        # Calculate metrics per incident
        mttr_values = []
        decision_to_action_times = []

        for inc_id, inc_events in incidents.items():
            inc_events_sorted = sorted(inc_events, key=lambda x: x["timestamp"])

            if inc_events_sorted:
                first_time = datetime.fromisoformat(inc_events_sorted[0]["timestamp"])
                last_time = datetime.fromisoformat(inc_events_sorted[-1]["timestamp"])
                mttr_seconds = (last_time - first_time).total_seconds()
                mttr_values.append(mttr_seconds)

            # Time from decision to action
            decisions = [e for e in inc_events if e["event_type"] == "decision_made"]
            actions = [e for e in inc_events if e["event_type"] == "action_executed"]

            if decisions and actions:
                decision_time = datetime.fromisoformat(decisions[0]["timestamp"])
                action_time = datetime.fromisoformat(actions[0]["timestamp"])
                delay = (action_time - decision_time).total_seconds()
                decision_to_action_times.append(delay)

        # Calculate statistics
        def stats(values):
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "count": 0}
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values),
            }

        return {
            "period_days": days,
            "start_date": start_date,
            "end_date": end_date,
            "incident_count": len(incidents),
            "mttr_seconds": stats(mttr_values),
            "decision_to_action_delay_seconds": stats(decision_to_action_times),
            "success_rate": self._calculate_success_rate(events),
        }

    def _calculate_success_rate(self, events: List[Dict]) -> float:
        """Calculate success rate of actions"""
        action_events = [e for e in events if e["event_type"] == "action_executed"]
        if not action_events:
            return 0.0

        successful = sum(1 for e in action_events if e["result"] == "success")
        return (successful / len(action_events)) * 100


class PostIncidentReview:
    """Automated post-incident review generation"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def generate_pir(
        self, incident_id: str, manual_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate post-incident review
        """
        report = self.audit.audit_logger.generate_incident_report(incident_id)

        timeline = report["timeline"]

        pir = {
            "incident_id": incident_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "duration": self._extract_duration(timeline),
                "decision_time": self._extract_decision_time(timeline),
                "action_execution_time": self._extract_action_time(timeline),
                "total_actions": len([t for t in timeline if "action" in t["phase"]]),
            },
            "timeline": timeline,
            "root_cause_analysis": "Auto-generated from audit trail",
            "what_went_well": [
                "Automatic detection and alerting",
                "Policy gates prevented unauthorized changes",
            ],
            "what_could_improve": [
                "Recommendation to be added based on incident patterns",
            ],
            "action_items": [
                {
                    "action": "Update runbook for app",
                    "owner": "TBD",
                    "due_date": "TBD",
                }
            ],
            "manual_notes": manual_notes or "",
        }

        return pir

    def _extract_duration(self, timeline: List[Dict]) -> float:
        """Extract total incident duration from timeline"""
        if not timeline:
            return 0.0

        start = datetime.fromisoformat(timeline[0]["timestamp"])
        end = datetime.fromisoformat(timeline[-1]["timestamp"])
        return (end - start).total_seconds()

    def _extract_decision_time(self, timeline: List[Dict]) -> float:
        """Time from incident detection to decision"""
        detection = next((t for t in timeline if "detected" in t["phase"]), None)
        decision = next((t for t in timeline if "decision" in t["phase"]), None)

        if detection and decision:
            start = datetime.fromisoformat(detection["timestamp"])
            end = datetime.fromisoformat(decision["timestamp"])
            return (end - start).total_seconds()

        return 0.0

    def _extract_action_time(self, timeline: List[Dict]) -> float:
        """Time to execute action"""
        decision = next((t for t in timeline if "decision" in t["phase"]), None)
        action = next((t for t in timeline if "action" in t["phase"]), None)

        if decision and action:
            start = datetime.fromisoformat(decision["timestamp"])
            end = datetime.fromisoformat(action["timestamp"])
            return (end - start).total_seconds()

        return 0.0

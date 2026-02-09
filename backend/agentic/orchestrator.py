# backend/agentic/orchestrator.py
"""
MAIN ORCHESTRATOR: Ties all agentic components together
- Coordinates the full agentic loop
- Manages background monitoring
- Integrates all subsystems
- Provides APIs for Streamlit UI
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import json
import os

from .core import AgenticSRECopilot, Signal, Incident, ReasoningDecision, ActionStatus
from .perception import PerceptionEngine
from .reasoning import LLMReasoner
from .executor import ActionExecutor
from .jira_integration import JiraHandler, JiraClient
from .notifications import NotificationHandler, SMTPNotifier
from .audit import AuditLogger, AuditEvent, ComplianceReporter, PerformanceMetrics, PostIncidentReview


logger = logging.getLogger(__name__)


class SREAgentOrchestrator:
    """
    Main orchestrator for agentic SRE Copilot
    Manages all subsystems and provides unified interface
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize orchestrator with configuration

        Config format:
        {
            "apps": [{"name": "api", "health_url": "...", "systemd_service": "..."}],
            "jira": {"base_url": "...", "user_email": "...", "api_token": "...", "project_key": "..."},
            "smtp": {"server": "...", "port": 587, "from_address": "...", "username": "...", "password": "..."},
            "memory_path": "/tmp/incident_memory.json",
            "audit_db_path": "/tmp/sre_audit.db",
            "monitoring_interval": 30,
        }
        """
        self.config = config
        self.running = False

        # Initialize components
        logger.info("[ORCHESTRATOR] Initializing SRE Agent Orchestrator...")

        # Perception
        self.perception = PerceptionEngine(config.get("apps", []))

        # Reasoning
        self.reasoner = LLMReasoner()

        # Execution
        self.executor = ActionExecutor()

        # JIRA
        self.jira_handler = None
        if config.get("jira"):
            jira_config = config["jira"]
            jira_client = JiraClient(
                base_url=jira_config["base_url"],
                user_email=jira_config["user_email"],
                api_token=jira_config["api_token"],
                project_key=jira_config["project_key"],
            )
            self.jira_handler = JiraHandler(jira_client)

        # Notifications
        self.notification_handler = None
        if config.get("smtp"):
            smtp_config = config["smtp"]
            notifier = SMTPNotifier(
                smtp_server=smtp_config["server"],
                smtp_port=smtp_config.get("port", 587),
                from_address=smtp_config["from_address"],
                from_name=smtp_config.get("from_name", "SRE Agent"),
                username=smtp_config.get("username"),
                password=smtp_config.get("password"),
                use_tls=smtp_config.get("use_tls", True),
            )
            self.notification_handler = NotificationHandler(notifier)
            self.notification_handler.set_recipients(
                oncall=config.get("oncall_emails", []),
                daily_report=config.get("daily_report_emails", []),
            )

        # Audit
        self.audit_logger = AuditLogger(config.get("audit_db_path", "/tmp/sre_audit.db"))
        self.compliance_reporter = ComplianceReporter(self.audit_logger)
        self.performance_metrics = PerformanceMetrics(self.audit_logger)
        self.pir_generator = PostIncidentReview(self.audit_logger)

        # Core agentic loop
        def _reasoning_engine(incident: Incident, memory):
            return self.reasoner.reason_about_incident(incident, memory)

        def _action_executor(action):
            return self.executor.execute_action(action)

        self.copilot = AgenticSRECopilot(
            memory_path=config.get("memory_path", "/tmp/incident_memory.json"),
            reasoning_engine=_reasoning_engine,
            action_executor=_action_executor,
            notification_handler=self.notification_handler,
            jira_handler=self.jira_handler,
        )

        logger.info("[ORCHESTRATOR] Initialization complete")

    async def run_monitoring_loop(self, interval_seconds: int = 30):
        """
        Main monitoring loop
        Continuously collects signals and runs agentic loop
        """
        logger.info(f"[ORCHESTRATOR] Starting monitoring loop (interval: {interval_seconds}s)")
        self.running = True

        try:
            while self.running:
                await self._monitoring_iteration()
                await asyncio.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("[ORCHESTRATOR] Monitoring loop interrupted")
        finally:
            self.running = False
            logger.info("[ORCHESTRATOR] Monitoring loop stopped")

    async def _monitoring_iteration(self):
        """Single monitoring iteration"""
        try:
            # 1. PERCEIVE: Collect signals
            signals = await self.perception.collect_signals()

            if not signals:
                logger.debug("[ORCHESTRATOR] No signals collected")
                return

            # Log perception event
            for signal in signals:
                if signal.status in ["unhealthy", "critical", "degraded"]:
                    event = AuditEvent(
                        timestamp=datetime.utcnow().isoformat(),
                        event_type="incident_detected",
                        incident_id="PENDING",  # Will be updated after perception
                        actor="perception_engine",
                        action=f"signal_detected_{signal.source}",
                        details=signal.to_dict(),
                        result="success",
                    )
                    self.audit_logger.log_event(event)

            # 2-6. Run agentic loop: Reason → Plan → Act → Reflect → Learn
            outcomes = await self.copilot.run_agentic_loop(signals)

            # Log outcomes and escalations
            for outcome in outcomes:
                # Log outcome
                event = AuditEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="outcome_recorded",
                    incident_id=outcome.incident_id,
                    actor="copilot",
                    action="incident_resolved",
                    details=outcome.to_dict(),
                    result=outcome.status,
                )
                self.audit_logger.log_event(event)

                # If escalation needed, log JIRA handler
                if any(not exe.success for exe in outcome.actions_executed):
                    event = AuditEvent(
                        timestamp=datetime.utcnow().isoformat(),
                        event_type="escalation",
                        incident_id=outcome.incident_id,
                        actor="jira_handler",
                        action="create_escalation_ticket",
                        details={"status": outcome.status},
                        result="pending",
                    )
                    self.audit_logger.log_event(event)

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error in monitoring iteration: {e}", exc_info=True)

    def stop_monitoring(self):
        """Stop monitoring loop"""
        self.running = False
        logger.info("[ORCHESTRATOR] Monitoring loop stop requested")

    # ========== API METHODS FOR STREAMLIT UI ==========

    def get_incident_status(self, incident_id: str) -> Dict[str, Any]:
        """Get current incident status"""
        incident = self.copilot.running_incidents.get(incident_id)

        if not incident:
            return {"status": "not_found"}

        return {
            "id": incident.id,
            "app_name": incident.app_name,
            "severity": incident.severity.value,
            "description": incident.description,
            "detected_at": incident.timestamp,
            "signals_count": len(incident.signals),
            "status": "running",
        }

    def get_recent_incidents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent incidents from memory"""
        memory_data = self.copilot.memory.incidents
        incidents = list(memory_data.values())
        return sorted(incidents, key=lambda x: x.get("resolved_at", ""), reverse=True)[
            :limit
        ]

    def get_incident_audit_trail(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for incident"""
        return self.audit_logger.get_incident_audit_trail(incident_id)

    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.performance_metrics.calculate_metrics(days)

    def get_compliance_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get compliance report"""
        return self.compliance_reporter.generate_compliance_report(start_date, end_date)

    def get_pir(self, incident_id: str) -> Dict[str, Any]:
        """Get post-incident review"""
        return self.pir_generator.generate_pir(incident_id)

    def get_patterns(self) -> Dict[str, Any]:
        """Get learned patterns from memory"""
        return self.copilot.memory.patterns

    def get_policy(self) -> Dict[str, Any]:
        """Get current policy configuration"""
        return self.copilot.policy.config

    def update_policy(self, policy_update: Dict[str, Any]) -> bool:
        """Update policy configuration"""
        try:
            self.copilot.policy.config.update(policy_update)
            logger.info(f"[ORCHESTRATOR] Policy updated: {list(policy_update.keys())}")
            return True
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Failed to update policy: {e}")
            return False

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            "running": self.running,
            "running_incidents": len(self.copilot.running_incidents),
            "execution_counts": self.copilot.execution_counts_today,
            "last_update": datetime.utcnow().isoformat(),
        }

    async def test_perception(self) -> List[Dict[str, Any]]:
        """Test perception engine and return signals"""
        signals = await self.perception.collect_signals()
        return [s.to_dict() for s in signals]

    async def test_reasoning(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Test reasoning engine on a sample incident"""
        from .core import Incident, IncidentSeverity

        # Convert dict to Incident object
        inc = Incident(
            id=incident.get("id", "TEST"),
            timestamp=incident.get("timestamp", datetime.utcnow().isoformat()),
            severity=IncidentSeverity[incident.get("severity", "HIGH")],
            app_name=incident.get("app_name", "test-app"),
            description=incident.get("description", "Test incident"),
            signals=[],
            context=incident.get("context", {}),
        )

        decision = self.reasoner.reason_about_incident(inc, self.copilot.memory)
        return decision.to_dict()

    def get_system_config(self) -> Dict[str, Any]:
        """Get current system configuration"""
        return {
            "apps": self.config.get("apps", []),
            "monitoring_interval": self.config.get("monitoring_interval", 30),
            "memory_path": self.config.get("memory_path"),
            "audit_db_path": self.config.get("audit_db_path"),
            "jira_configured": self.jira_handler is not None,
            "smtp_configured": self.notification_handler is not None,
        }


# Singleton orchestrator instance
_orchestrator: Optional[SREAgentOrchestrator] = None


def initialize_orchestrator(config: Dict[str, Any]) -> SREAgentOrchestrator:
    """Initialize global orchestrator"""
    global _orchestrator
    _orchestrator = SREAgentOrchestrator(config)
    return _orchestrator


def get_orchestrator() -> Optional[SREAgentOrchestrator]:
    """Get global orchestrator instance"""
    return _orchestrator

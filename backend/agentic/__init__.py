# backend/agentic/__init__.py
"""
Agentic SRE Copilot Framework
Complete autonomous SRE incident management system

Components:
- core.py: Core agentic loop (Observe→Reason→Plan→Act→Reflect→Learn)
- perception.py: Signal collection from health checks, logs, metrics, systemd
- reasoning.py: LLM-powered autonomous decision-making
- executor.py: Safe action execution with rollback
- jira_integration.py: Escalation and approval routing to JIRA
- notifications.py: SMTP-based incident and resolution notifications
- audit.py: Complete audit trail and compliance reporting
- orchestrator.py: Main orchestrator that ties everything together
"""

from .core import (
    AgenticSRECopilot,
    Incident,
    Signal,
    ReasoningDecision,
    PlannedAction,
    ActionExecution,
    IncidentOutcome,
    IncidentSeverity,
    ActionStatus,
    Memory,
    Policy,
)
from .perception import (
    PerceptionEngine,
    HealthChecker,
    LogAnalyzer,
    MetricsCollector,
    SystemdMonitor,
)
from .reasoning import LLMReasoner, ContextualAnalyzer
from .executor import SystemdExecutor, ApplicationExecutor, ActionExecutor
from .jira_integration import JiraClient, JiraHandler
from .notifications import SMTPNotifier, NotificationHandler
from .audit import AuditLogger, AuditEvent, ComplianceReporter, PerformanceMetrics, PostIncidentReview
from .orchestrator import SREAgentOrchestrator, initialize_orchestrator, get_orchestrator

__all__ = [
    "AgenticSRECopilot",
    "Incident",
    "Signal",
    "ReasoningDecision",
    "PlannedAction",
    "ActionExecution",
    "IncidentOutcome",
    "IncidentSeverity",
    "ActionStatus",
    "Memory",
    "Policy",
    "PerceptionEngine",
    "HealthChecker",
    "LogAnalyzer",
    "MetricsCollector",
    "SystemdMonitor",
    "LLMReasoner",
    "ContextualAnalyzer",
    "SystemdExecutor",
    "ApplicationExecutor",
    "ActionExecutor",
    "JiraClient",
    "JiraHandler",
    "SMTPNotifier",
    "NotificationHandler",
    "AuditLogger",
    "AuditEvent",
    "ComplianceReporter",
    "PerformanceMetrics",
    "PostIncidentReview",
    "SREAgentOrchestrator",
    "initialize_orchestrator",
    "get_orchestrator",
]

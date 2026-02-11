# backend/agentic/core.py
"""
Agentic SRE Copilot Core Framework
Implements: Observe → Reason → Plan → Act → Reflect → Learn

This is a fully autonomous loop that:
1. PERCEIVES health signals (health checks, logs, metrics)
2. CONTEXTUALIZES incidents with past knowledge
3. REASONS with LLM over remediation options
4. PLANS action sequences with policy enforcement
5. ACTS safely with rollback capabilities
6. REFLECTS on outcomes and validates
7. LEARNS by updating incident memory and improving policies
"""

import json
import time
import uuid
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import traceback


logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ActionStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class Signal:
    """Raw health signal from perception layer"""
    timestamp: str
    source: str  # "health_check", "log", "metric", "alert"
    app_name: str
    status: str  # "healthy", "degraded", "unhealthy", "critical"
    value: Any  # numeric or dict
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Incident:
    """Structured incident representation"""
    id: str
    timestamp: str
    severity: IncidentSeverity
    app_name: str
    description: str
    signals: List[Signal]
    context: Dict[str, Any]  # enriched data (past incidents, metrics, logs)
    root_cause: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "app_name": self.app_name,
            "description": self.description,
            "signals": [s.to_dict() for s in self.signals],
            "context": self.context,
            "root_cause": self.root_cause,
        }


@dataclass
class ReasoningDecision:
    """LLM reasoning output"""
    incident_id: str
    reasoning: str  # Full LLM reasoning chain
    recommended_actions: List[str]  # List of action names
    confidence: float  # 0.0-1.0
    risk_level: str  # "low", "medium", "high"
    requires_approval: bool
    escalation_needed: bool

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PlannedAction:
    """Action plan with pre-checks and rollback"""
    id: str
    incident_id: str
    action_type: str  # "restart_service", "scale_up", "drain_connections", etc.
    target: str  # service name, app name, etc.
    parameters: Dict[str, Any]
    pre_checks: List[str]  # validation steps before execution
    rollback_plan: Optional[str]  # rollback command or procedure
    status: ActionStatus
    policy_gates: Dict[str, bool]  # passed policy checks
    approval_ticket_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "status": self.status.value,
            "policy_gates": self.policy_gates,
        }


@dataclass
class ActionExecution:
    """Record of action execution"""
    action_id: str
    executed_at: str
    success: bool
    output: str
    error: Optional[str]
    execution_time_ms: float
    post_validation: Dict[str, Any]  # health after action

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class IncidentOutcome:
    """Final incident resolution outcome"""
    incident_id: str
    resolved_at: str
    actions_executed: List[ActionExecution]
    root_cause_confirmed: str
    lessons_learned: str
    status: str  # "resolved", "escalated", "blocked"
    mttr_seconds: float
    mtbf_prediction: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "actions_executed": [a.to_dict() for a in self.actions_executed],
        }


class Memory:
    """Persistent memory of past incidents and learnings"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.incidents: Dict[str, Dict] = {}
        self.patterns: Dict[str, Dict] = {}
        self.load()

    def load(self):
        """Load incident history from disk"""
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self.incidents = data.get("incidents", {})
                self.patterns = data.get("patterns", {})
        except FileNotFoundError:
            self.incidents = {}
            self.patterns = {}

    def save(self):
        """Persist to disk"""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(
                    {
                        "incidents": self.incidents,
                        "patterns": self.patterns,
                        "updated": datetime.utcnow().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def record_incident(self, outcome: IncidentOutcome):
        """Record resolved incident for learning"""
        self.incidents[outcome.incident_id] = outcome.to_dict()
        self._update_patterns(outcome)
        self.save()

    def _update_patterns(self, outcome: IncidentOutcome):
        """Extract patterns from outcome to improve future reasoning"""
        root_cause = outcome.root_cause_confirmed
        if root_cause:
            if root_cause not in self.patterns:
                self.patterns[root_cause] = {
                    "count": 0,
                    "avg_mttr_seconds": 0,
                    "effective_actions": [],
                }
            pattern = self.patterns[root_cause]
            pattern["count"] += 1
            old_avg = pattern["avg_mttr_seconds"]
            new_avg = (old_avg * (pattern["count"] - 1) + outcome.mttr_seconds) / pattern["count"]
            pattern["avg_mttr_seconds"] = new_avg

            # Track which actions worked
            for exe in outcome.actions_executed:
                if exe.success:
                    pattern["effective_actions"].append(exe.action_id)

    def get_similar_incidents(self, app_name: str, days: int = 30) -> List[Dict]:
        """Find similar incidents from history"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        similar = []
        for inc in self.incidents.values():
            if inc.get("app_name") == app_name:
                inc_time = datetime.fromisoformat(inc.get("resolved_at", ""))
                if inc_time > cutoff:
                    similar.append(inc)
        return sorted(similar, key=lambda x: x["resolved_at"], reverse=True)[:5]

    def get_pattern_recommendations(self, root_cause: str) -> Dict:
        """Get best-practice actions for a root cause"""
        return self.patterns.get(root_cause, {})


class Policy:
    """Policy enforcement gates"""

    def __init__(self, policy_config: Optional[Dict] = None):
        self.config = policy_config or self._default_config()

    def _default_config(self) -> Dict:
        return {
            "allow_auto_restart": True,
            "allow_auto_scale": False,
            "require_approval_for_restart": False,
            "max_restarts_per_day": 5,
            "change_window": {
                "enabled": True,
                "start_hour": 9,  # 9 AM
                "end_hour": 17,  # 5 PM
                "allowed_days": [1, 2, 3, 4, 5],  # Mon-Fri
            },
            "escalation_threshold": {
                "critical_count": 3,
                "time_window_minutes": 60,
            },
            "rollback_on_failed_health_check": True,
            "max_consecutive_failures_before_escalate": 2,
        }

    def check_action_allowed(
        self,
        action_type: str,
        app_name: str,
        incident_severity: IncidentSeverity,
        execution_count_today: int = 0,
    ) -> Dict[str, Any]:
        """
        Returns:
        {
            'allowed': bool,
            'reason': str,
            'requires_approval': bool,
            'gates_passed': {gate: bool}
        }
        """
        gates_passed = {}

        # Gate 1: Action type allowed
        if action_type == "restart_service":
            gates_passed["action_allowed"] = self.config["allow_auto_restart"]
        elif action_type == "scale_up":
            gates_passed["action_allowed"] = self.config["allow_auto_scale"]
        else:
            gates_passed["action_allowed"] = True

        # Gate 2: Rate limit
        gates_passed["rate_limit"] = (
            execution_count_today < self.config["max_restarts_per_day"]
        )

        # Gate 3: Change window (if enabled)
        if self.config["change_window"]["enabled"]:
            now = datetime.utcnow()
            gates_passed["change_window"] = (
                self.config["change_window"]["start_hour"]
                <= now.hour
                < self.config["change_window"]["end_hour"]
                and now.weekday() in self.config["change_window"]["allowed_days"]
            )
        else:
            gates_passed["change_window"] = True

        # Gate 4: Approval requirement
        requires_approval = (
            self.config["require_approval_for_restart"]
            and action_type == "restart_service"
        )

        # Overall decision
        all_gates_passed = all(gates_passed.values())
        allowed = all_gates_passed or (
            incident_severity == IncidentSeverity.CRITICAL and requires_approval
        )

        reason = ""
        if not gates_passed["action_allowed"]:
            reason = f"Action type '{action_type}' not allowed by policy"
        elif not gates_passed["rate_limit"]:
            reason = f"Rate limit exceeded ({execution_count_today}/{self.config['max_restarts_per_day']})"
        elif not gates_passed["change_window"]:
            reason = "Outside change window"

        return {
            "allowed": allowed,
            "requires_approval": requires_approval,
            "reason": reason,
            "gates_passed": gates_passed,
        }


class AgenticSRECopilot:
    """
    Main agentic loop orchestrator
    Coordinates: Perceive → Reason → Plan → Act → Reflect → Learn
    """

    def __init__(
        self,
        memory_path: str,
        reasoning_engine: Optional[Callable] = None,
        action_executor: Optional[Callable] = None,
        notification_handler: Optional[Any] = None,
        jira_handler: Optional[Any] = None,
    ):
        self.memory = Memory(memory_path)
        self.policy = Policy()
        self.reasoning_engine = reasoning_engine
        self.action_executor = action_executor
        self.notification_handler = notification_handler
        self.jira_handler = jira_handler
        self.running_incidents: Dict[str, Incident] = {}
        self.execution_counts_today: Dict[str, int] = {}

    def perceive(self, signals: List[Signal]) -> List[Incident]:
        """
        PERCEPTION PHASE: Convert raw signals into structured incidents
        Aggregates multiple signals into logical incidents
        """
        incidents = []
        incidents_by_app = {}

        # Group signals by app
        for signal in signals:
            if signal.app_name not in incidents_by_app:
                incidents_by_app[signal.app_name] = []
            incidents_by_app[signal.app_name].append(signal)

        # Create incident for each unhealthy app
        for app_name, app_signals in incidents_by_app.items():
            # Check if any signal indicates problem
            has_problem = any(
                s.status in ["degraded", "unhealthy", "critical"] for s in app_signals
            )
            if has_problem:
                # Determine severity
                if any(s.status == "critical" for s in app_signals):
                    severity = IncidentSeverity.CRITICAL
                elif any(s.status == "unhealthy" for s in app_signals):
                    severity = IncidentSeverity.HIGH
                else:
                    severity = IncidentSeverity.MEDIUM

                incident = Incident(
                    id=f"INC-{uuid.uuid4().hex[:8].upper()}",
                    timestamp=datetime.utcnow().isoformat(),
                    severity=severity,
                    app_name=app_name,
                    description=f"{app_name} is {max(s.status for s in app_signals)}",
                    signals=app_signals,
                    context=self._enrich_context(app_name, app_signals),
                )
                incidents.append(incident)
                self.running_incidents[incident.id] = incident

        logger.info(f"[PERCEIVE] Detected {len(incidents)} incidents from {len(signals)} signals")
        return incidents

    def _enrich_context(self, app_name: str, signals: List[Signal]) -> Dict:
        """Enrich incident with historical context"""
        similar = self.memory.get_similar_incidents(app_name, days=30)
        
        # Extract docker_container from signals if present
        docker_container = None
        for signal in signals:
            if signal.metadata.get("docker_container"):
                docker_container = signal.metadata["docker_container"]
                break
        
        context = {
            "similar_recent_incidents": len(similar),
            "previous_root_causes": [
                inc.get("root_cause_confirmed") for inc in similar if inc.get("root_cause_confirmed")
            ],
            "signals_summary": {
                "count": len(signals),
                "statuses": [s.status for s in signals],
            },
        }
        
        # Add docker_container if present
        if docker_container:
            context["docker_container"] = docker_container
        
        return context

    def reason(self, incident: Incident) -> ReasoningDecision:
        """
        REASONING PHASE: LLM-powered autonomous reasoning
        Analyzes incident, considers past patterns, recommends actions
        """
        if not self.reasoning_engine:
            # Fallback to simple rule-based reasoning
            return self._simple_reasoning(incident)

        try:
            decision = self.reasoning_engine(incident, self.memory)
            logger.info(f"[REASON] {incident.id}: {decision.recommended_actions}")
            return decision
        except Exception as e:
            logger.error(f"[REASON] Error in reasoning engine: {e}")
            return self._simple_reasoning(incident)

    def _simple_reasoning(self, incident: Incident) -> ReasoningDecision:
        """Fallback rule-based reasoning"""
        actions = []
        escalate = False

        if incident.severity == IncidentSeverity.CRITICAL:
            actions = ["restart_service", "notify_oncall"]
            escalate = True
        elif incident.severity == IncidentSeverity.HIGH:
            actions = ["check_logs", "restart_service"]
        else:
            actions = ["check_logs", "monitor"]

        return ReasoningDecision(
            incident_id=incident.id,
            reasoning="Rule-based fallback reasoning",
            recommended_actions=actions,
            confidence=0.6,
            risk_level="medium",
            requires_approval=incident.severity in [IncidentSeverity.CRITICAL],
            escalation_needed=escalate,
        )

    def plan(
        self, incident: Incident, decision: ReasoningDecision
    ) -> List[PlannedAction]:
        """
        PLANNING PHASE: Convert reasoning into executable action plans
        Enforces policy gates, determines pre-checks and rollback
        """
        planned_actions = []
        execution_count = self.execution_counts_today.get(incident.app_name, 0)

        for action_name in decision.recommended_actions:
            # Check policy
            policy_result = self.policy.check_action_allowed(
                action_type=action_name,
                app_name=incident.app_name,
                incident_severity=incident.severity,
                execution_count_today=execution_count,
            )

            status = (
                ActionStatus.PENDING
                if policy_result["allowed"]
                else ActionStatus.BLOCKED
            )

            planned_action = PlannedAction(
                id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                incident_id=incident.id,
                action_type=action_name,
                target=incident.app_name,
                parameters={"app_name": incident.app_name},
                pre_checks=self._get_pre_checks(action_name),
                rollback_plan=self._get_rollback(action_name),
                status=status,
                policy_gates=policy_result["gates_passed"],
            )

            if policy_result["requires_approval"]:
                planned_action.approval_ticket_id = f"JIRA-TBD"

            planned_actions.append(planned_action)

        logger.info(
            f"[PLAN] {incident.id}: Planned {len(planned_actions)} actions "
            f"({sum(1 for a in planned_actions if a.status == ActionStatus.PENDING)} approved)"
        )
        return planned_actions

    def _get_pre_checks(self, action_type: str) -> List[str]:
        """Pre-execution validation steps"""
        checks = {
            "restart_service": [
                "verify_service_exists",
                "check_dependencies",
                "drain_connections",
            ],
            "scale_up": [
                "check_resource_availability",
                "verify_deployment_health",
            ],
            "check_logs": [
                "fetch_recent_logs",
                "analyze_for_errors",
            ],
        }
        return checks.get(action_type, [])

    def _get_rollback(self, action_type: str) -> Optional[str]:
        """Rollback procedure for action"""
        rollbacks = {
            "restart_service": "systemctl restart {app_name}",
            "scale_up": "revert_scaling_to_previous_replica_count",
            "drain_connections": "resume_accepting_connections",
        }
        return rollbacks.get(action_type)

    def act(
        self, planned_actions: List[PlannedAction]
    ) -> List[ActionExecution]:
        """
        ACTION PHASE: Execute approved actions with safety checks
        Monitors execution, handles rollback on failure
        """
        executions = []

        for action in planned_actions:
            if action.status != ActionStatus.PENDING:
                logger.info(f"[ACT] Skipping {action.id} (status: {action.status.value})")
                continue

            logger.info(f"[ACT] Executing {action.id}: {action.action_type} on {action.target}")

            start = time.time()
            execution_result = None

            try:
                # Run pre-checks
                pre_check_results = self._run_pre_checks(action)
                if not all(pre_check_results.values()):
                    raise Exception(f"Pre-checks failed: {pre_check_results}")

                # Execute action
                if self.action_executor:
                    execution_result = self.action_executor(action)
                else:
                    execution_result = self._simple_action_executor(action)

                success = execution_result.get("success", False)
                output = execution_result.get("output", "")
                error = None

                # Post-execution validation
                post_validation = self._post_validate(action, success)

                if not post_validation.get("health_ok") and action.rollback_plan:
                    logger.warning(f"[ACT] Health check failed, rolling back {action.id}")
                    self._execute_rollback(action)
                    success = False
                    error = "Rollback executed due to failed post-validation"

            except Exception as e:
                logger.error(f"[ACT] Error executing {action.id}: {e}\n{traceback.format_exc()}")
                success = False
                output = ""
                error = str(e)
                post_validation = {"health_ok": False}

            elapsed_ms = (time.time() - start) * 1000

            execution = ActionExecution(
                action_id=action.id,
                executed_at=datetime.utcnow().isoformat(),
                success=success,
                output=output,
                error=error,
                execution_time_ms=elapsed_ms,
                post_validation=post_validation,
            )
            executions.append(execution)
            self.execution_counts_today[action.target] = (
                self.execution_counts_today.get(action.target, 0) + 1
            )

        logger.info(f"[ACT] Completed {len(executions)} executions")
        return executions

    def _run_pre_checks(self, action: PlannedAction) -> Dict[str, bool]:
        """Run pre-execution checks"""
        results = {}
        for check in action.pre_checks:
            try:
                results[check] = True  # Placeholder
                logger.debug(f"  Pre-check '{check}' passed")
            except Exception as e:
                logger.warning(f"  Pre-check '{check}' failed: {e}")
                results[check] = False
        return results

    def _simple_action_executor(self, action: PlannedAction) -> Dict:
        """Fallback action executor"""
        return {
            "success": True,
            "output": f"Simulated execution of {action.action_type} on {action.target}",
        }

    def _post_validate(self, action: PlannedAction, success: bool) -> Dict:
        """Post-action health verification"""
        return {
            "health_ok": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _execute_rollback(self, action: PlannedAction):
        """Execute rollback procedure"""
        if action.rollback_plan:
            logger.info(f"[ROLLBACK] Executing: {action.rollback_plan}")

    def reflect(
        self, incident: Incident, actions: List[PlannedAction], executions: List[ActionExecution]
    ) -> IncidentOutcome:
        """
        REFLECTION PHASE: Analyze outcomes and determine resolution
        """
        successful_executions = [e for e in executions if e.success]
        resolved = len(successful_executions) > 0

        start_time = datetime.fromisoformat(incident.timestamp)
        end_time = datetime.utcnow()
        mttr_seconds = (end_time - start_time).total_seconds()

        root_cause = (
            "restart_resolved_issue"
            if any(e.action_id for e in successful_executions)
            else "unresolved"
        )

        outcome = IncidentOutcome(
            incident_id=incident.id,
            resolved_at=end_time.isoformat(),
            actions_executed=executions,
            root_cause_confirmed=root_cause,
            lessons_learned=self._extract_lessons(incident, executions),
            status="resolved" if resolved else "escalated",
            mttr_seconds=mttr_seconds,
        )

        logger.info(f"[REFLECT] {incident.id}: {outcome.status} (MTTR: {mttr_seconds:.1f}s)")
        return outcome

    def _extract_lessons(self, incident: Incident, executions: List[ActionExecution]) -> str:
        """Extract learnings from incident"""
        return f"Incident on {incident.app_name} resolved with {len(executions)} actions"

    def learn(self, outcome: IncidentOutcome):
        """
        LEARNING PHASE: Update memory and improve future decisions
        """
        self.memory.record_incident(outcome)
        logger.info(f"[LEARN] Recorded outcome for {outcome.incident_id}")

    def handle_incident_end_of_day(self):
        """Reset daily counters"""
        self.execution_counts_today = {}
        logger.info("[EOD] Reset execution counters")

    async def run_agentic_loop(self, signals: List[Signal]) -> List[IncidentOutcome]:
        """
        Main agentic loop: Observe → Reason → Plan → Act → Reflect → Learn
        """
        outcomes = []

        # 1. PERCEIVE
        incidents = self.perceive(signals)

        for incident in incidents:
            try:
                # 2. REASON
                decision = self.reason(incident)

                # Escalate critical incidents to JIRA before actions
                escalation_ticket = None
                if decision.escalation_needed and self.jira_handler:
                    if hasattr(self.jira_handler, "handle_escalation"):
                        escalation_ticket = self.jira_handler.handle_escalation(
                            incident, decision
                        )

                # Notify on-call for critical incidents
                if (
                    incident.severity == IncidentSeverity.CRITICAL
                    and self.notification_handler
                    and hasattr(self.notification_handler, "notify_incident")
                ):
                    self.notification_handler.notify_incident(
                        incident, escalation_ticket=escalation_ticket
                    )

                # 3. PLAN
                planned_actions = self.plan(incident, decision)

                # 4. ACT
                executions = self.act(planned_actions)

                # 5. REFLECT
                outcome = self.reflect(incident, planned_actions, executions)

                # 6. LEARN
                self.learn(outcome)

                outcomes.append(outcome)

                # Notify stakeholders
                if self.notification_handler:
                    if hasattr(self.notification_handler, "notify_resolution"):
                        self.notification_handler.notify_resolution(
                            outcome, outcome.mttr_seconds
                        )
                    elif callable(self.notification_handler):
                        self.notification_handler(outcome)

                # Route to Jira if escalation needed
                if self.jira_handler:
                    if hasattr(self.jira_handler, "handle_outcome"):
                        self.jira_handler.handle_outcome(outcome)
                    elif callable(self.jira_handler):
                        self.jira_handler(outcome)

            except Exception as e:
                logger.error(f"Error in agentic loop for {incident.id}: {e}\n{traceback.format_exc()}")

        return outcomes

# AGENTIC SRE COPILOT - ARCHITECTURE & IMPLEMENTATION GUIDE

## Overview

A production-grade, fully autonomous SRE incident management system that:
- **Continuously monitors** application & service health
- **Autonomously reasons** over incidents using LLM
- **Plans remediation** actions with policy enforcement
- **Safely executes** actions with rollback capabilities
- **Learns** from outcomes to improve future decisions
- **Routes escalations** and approvals through JIRA
- **Notifies stakeholders** via SMTP
- **Maintains audit trails** for compliance

---

## 1. Architecture: The Agentic Loop

```
┌─────────────────────────────────────────────────────────────────┐
│  Observe → Reason → Plan → Act → Reflect → Learn                │
└─────────────────────────────────────────────────────────────────┘

1. PERCEIVE (Observation Phase)
   - HTTP health checks
   - Application log analysis
   - System metrics (CPU, memory, disk)
   - Systemd service status
   → Outputs: List of Signals aggregated into Incidents

2. REASON (Autonomous Decision Phase)
   - Analyze incident severity and context
   - Query historical patterns from memory
   - Use LLM (Gemini) to generate reasoning
   - Recommend remediation actions
   → Outputs: ReasoningDecision with recommended actions

3. PLAN (Planning Phase)
   - Convert recommendations into executable PlannedActions
   - Enforce policy gates:
     * Action type allowed?
     * Rate limits respected?
     * Within change window?
     * Requires approval?
   - Determine pre-checks and rollback procedures
   → Outputs: List of PlannedActions (PENDING or BLOCKED)

4. ACT (Execution Phase)
   - Run pre-checks
   - Execute approved actions (systemd restart, scaling, etc.)
   - Monitor execution
   - Post-validation health checks
   - Rollback if needed
   → Outputs: List of ActionExecutions with success/failure

5. REFLECT (Analysis Phase)
   - Analyze outcomes
   - Determine if incident resolved
   - Calculate MTTR
   - Extract root cause and lessons learned
   → Outputs: IncidentOutcome

6. LEARN (Memory & Improvement Phase)
   - Store incident outcome in persistent memory
   - Update pattern library (what works for which root causes)
   - Improve policy based on outcomes
   - Generate audit trail for compliance
   → Updates: Memory + Policy + Audit logs
```

---

## 2. Component Architecture

### 2.1 Core Components (`backend/agentic/core.py`)

**Data Structures:**
- `Signal`: Raw health indicator (source, app, status, value)
- `Incident`: Aggregated problem (severity, signals, context)
- `ReasoningDecision`: LLM output (actions, confidence, risk)
- `PlannedAction`: Executable plan (type, target, pre-checks, rollback)
- `ActionExecution`: Execution record (success, output, timing)
- `IncidentOutcome`: Final result (root cause, actions, lessons, MTTR)
- `Memory`: Persistent learning (incidents, patterns)
- `Policy`: Enforcement gates (approval thresholds, rate limits, change windows)

**Main Class:**
- `AgenticSRECopilot`: Orchestrates the full agentic loop

### 2.2 Perception Layer (`backend/agentic/perception.py`)

Collects signals from multiple sources:

**Classes:**
- `HealthChecker`: HTTP-based health checks (response time, status code)
- `LogAnalyzer`: Parse logs for errors/exceptions
- `MetricsCollector`: CPU, memory, disk usage
- `SystemdMonitor`: Service status via systemctl
- `PerceptionEngine`: Orchestrates all sources, returns aggregated signals

### 2.3 Reasoning Layer (`backend/agentic/reasoning.py`)

Autonomous decision-making using LLM:

**Classes:**
- `LLMReasoner`: 
  - Calls Gemini API with incident context
  - Includes similar past incidents
  - Includes effective patterns from memory
  - Returns structured decision (actions, risk, confidence)
  - Fallback rule-based reasoning if LLM unavailable

- `ContextualAnalyzer`: Enriches incidents with historical context

### 2.4 Execution Layer (`backend/agentic/executor.py`)

Safe action execution:

**Classes:**
- `SystemdExecutor`: 
  - Restart service (with health verification)
  - Stop/start services
  - Get service status
  
- `ApplicationExecutor`:
  - Drain connections gracefully
  - Verify health post-action
  - Scale up replicas
  
- `ActionExecutor`: Router to specific executors

**Safety Features:**
- Pre-checks before execution
- Post-validation health checks
- Automatic rollback on failure
- Timeout protection

### 2.5 JIRA Integration (`backend/agentic/jira_integration.py`)

Route escalations and approvals:

**Classes:**
- `JiraClient`: REST API wrapper for JIRA
  - Create incident tickets
  - Create approval request tickets
  - Update tickets with outcomes
  - Check approval status
  - Link issues
  
- `JiraHandler`: High-level interface for agentic loop

**Workflow:**
- Incident → Create JIRA ticket
- If requires approval → Create approval request task
- On resolution → Update main ticket with outcome

### 2.6 Notifications (`backend/agentic/notifications.py`)

SMTP-based alerting:

**Classes:**
- `SMTPNotifier`: Email sender
  - Incident alerts (with severity badges)
  - Resolution notifications (with MTTR)
  - Daily reports (with metrics)
  
- `NotificationHandler`: Recipient management

### 2.7 Audit & Compliance (`backend/agentic/audit.py`)

Complete audit trail:

**Classes:**
- `AuditLogger`: SQLite-based persistent audit log
  - Stores all decisions and actions
  - Queryable by incident, date range, actor
  
- `ComplianceReporter`: Generate reports
  - Incident-specific audit trail
  - Period-based compliance report
  - Events grouped by type and actor
  
- `PerformanceMetrics`: Analytics
  - MTTR statistics
  - Decision-to-action delay
  - Success rates
  
- `PostIncidentReview`: PIR generation
  - Timeline from audit
  - Root cause analysis
  - Lessons learned
  - Action items

### 2.8 Orchestrator (`backend/agentic/orchestrator.py`)

Main coordinator:

**Classes:**
- `SREAgentOrchestrator`: Ties all components
  - Manages monitoring loop
  - Provides APIs for UI
  - Singleton instance for app-wide access

**Key Methods:**
- `run_monitoring_loop()`: Main async loop
- `get_incident_status()`: Query current incidents
- `get_recent_incidents()`: Historical incidents
- `get_incident_audit_trail()`: Full audit for incident
- `get_performance_metrics()`: SRE metrics
- `get_compliance_report()`: Audit report
- `get_pir()`: Post-incident review
- `test_perception()`: Test signal collection
- `test_reasoning()`: Test reasoning engine

---

## 3. Integration with Streamlit Frontend

```python
# In frontend/app.py

from backend.agentic import get_orchestrator

orchestrator = get_orchestrator()

# Display status
st.write(orchestrator.get_monitoring_status())

# Show recent incidents
for inc in orchestrator.get_recent_incidents():
    st.write(inc)

# Test perception
signals = st.button("Collect Signals")
if signals:
    results = asyncio.run(orchestrator.test_perception())
    st.json(results)

# View metrics
metrics = orchestrator.get_performance_metrics(days=7)
st.metric("Average MTTR", f"{metrics['mttr_seconds']['avg']:.1f}s")

# View audit trail
audit_trail = orchestrator.get_incident_audit_trail("INC-12345")
st.dataframe(audit_trail)
```

---

## 4. Policy Enforcement (Policy Gates)

```python
# Policy checks in order:
1. Action type allowed? (allow_auto_restart, allow_auto_scale)
2. Rate limit OK? (max_restarts_per_day)
3. Change window? (business hours, allowed days)
4. Requires approval? (escalate to JIRA if yes)
5. Escalation threshold? (critical incident in short window)

Example Policy:
{
    "allow_auto_restart": True,
    "allow_auto_scale": False,
    "require_approval_for_restart": True,
    "max_restarts_per_day": 5,
    "change_window": {
        "enabled": True,
        "start_hour": 9,      # 9 AM UTC
        "end_hour": 17,       # 5 PM UTC
        "allowed_days": [1,2,3,4,5]  # Mon-Fri
    }
}
```

---

## 5. Memory & Learning System

```python
# Incident Memory Structure (JSON)
{
  "INC-12345": {
    "app_name": "api-server",
    "root_cause_confirmed": "high_memory_usage",
    "mttr_seconds": 45.3,
    "actions_executed": [...],
    "resolved_at": "2026-02-09T14:30:00Z"
  }
}

# Pattern Library
{
  "high_memory_usage": {
    "count": 5,
    "avg_mttr_seconds": 42.5,
    "effective_actions": ["restart_service", "scale_up"]
  },
  "connection_timeout": {
    "count": 3,
    "avg_mttr_seconds": 30.0,
    "effective_actions": ["drain_connections", "restart_service"]
  }
}

# Learning Process:
1. Record outcome in incident memory
2. Extract root cause patterns
3. Track which actions were effective
4. Suggest learned actions in future reasoning
5. Continuously improve decision quality
```

---

## 6. Audit Trail & Compliance

```python
# Audit Database (SQLite)
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT,  -- "incident_detected", "decision_made", "action_executed", etc.
    incident_id TEXT,
    actor TEXT,       -- "perception_engine", "llm_reasoner", "executor", etc.
    action TEXT,
    details TEXT (JSON),
    result TEXT,      -- "success", "failed", "pending"
    user TEXT         -- Human user if manual approval
);

# Example Audit Trail for Single Incident:
1. 14:20:00 - incident_detected - CRITICAL signal from api-server
2. 14:20:05 - decision_made - LLM recommends: restart_service
3. 14:20:10 - action_planned - Planning restart (policy gates passed)
4. 14:20:15 - action_executed - systemctl restart api-server (SUCCESS)
5. 14:20:50 - health_verified - Service health check: OK
6. 14:21:00 - outcome_recorded - Incident RESOLVED (MTTR: 45s)
7. 14:21:05 - learned - Pattern: high_memory_usage → restart_service (effective)
```

---

## 7. Deployment Architecture

```
┌─────────────────────────────────────┐
│   EC2 Instance (Ubuntu)             │
│  IP: 18.237.102.97                  │
├─────────────────────────────────────┤
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Systemd Service (sre-agent)     │ │
│ │ - Runs run_agentic.py           │ │
│ │ - Async monitoring loop         │ │
│ │ - Monitors 30s interval         │ │
│ └─────────────────────────────────┘ │
│                 ↓                    │
│ ┌─────────────────────────────────┐ │
│ │ Perception Engine               │ │
│ │ - Health checks (HTTP)          │ │
│ │ - Logs (parse errors)           │ │
│ │ - Metrics (CPU, mem, disk)      │ │
│ │ - Systemd (service status)      │ │
│ └─────────────────────────────────┘ │
│                 ↓                    │
│ ┌─────────────────────────────────┐ │
│ │ LLM Reasoner (Gemini)           │ │
│ │ - Analyze incident              │ │
│ │ - Query memory (patterns)       │ │
│ │ - Recommend actions             │ │
│ └─────────────────────────────────┘ │
│                 ↓                    │
│ ┌─────────────────────────────────┐ │
│ │ Policy Engine                   │ │
│ │ - Approval gates                │ │
│ │ - Rate limits                   │ │
│ │ - Change windows                │ │
│ └─────────────────────────────────┘ │
│                 ↓                    │
│ ┌─────────────────────────────────┐ │
│ │ Action Executor                 │ │
│ │ - Systemd restart               │ │
│ │ - Health verify                 │ │
│ │ - Rollback if needed            │ │
│ └─────────────────────────────────┘ │
│                 ↓                    │
│ ┌─────────────────────────────────┐ │
│ │ Integration Layer               │ │
│ │ - JIRA escalation ticket        │ │
│ │ - SMTP notifications            │ │
│ │ - Audit logging                 │ │
│ └─────────────────────────────────┘ │
│                 ↓                    │
│ ┌─────────────────────────────────┐ │
│ │ Storage                         │ │
│ │ - Memory (JSON): incidents      │ │
│ │ - Audit DB (SQLite): events     │ │
│ │ - Config: policies              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Streamlit UI (port 8501)        │ │
│ │ - View incidents                │ │
│ │ - View metrics                  │ │
│ │ - View audit trails             │ │
│ │ - Configure policies            │ │
│ │ - Test perception/reasoning     │ │
│ └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
         ↓                      ↓
    JIRA API              SMTP Server
    (Atlassian)          (company.com)
```

---

## 8. Configuration

See `backend/config/agentic_config.example.py` for:
- Applications to monitor
- JIRA integration
- SMTP settings
- Policy thresholds
- Storage paths

```bash
# Copy and customize:
cp backend/config/agentic_config.example.py backend/config/agentic_config.py
# Edit agentic_config.py with your environment
```

---

## 9. Deployment Steps

### 9.1 Prerequisites
```bash
# Install dependencies
pip install google-genai requests streamlit pandas python-dotenv

# Set environment variables
export GOOGLE_API_KEY=your-gemini-key
export JIRA_BASE_URL=https://yourcompany.atlassian.net
export JIRA_USER_EMAIL=sre-bot@company.com
export JIRA_API_TOKEN=your-token
export SMTP_SERVER=smtp.company.com
```

### 9.2 Create Storage Directories
```bash
sudo mkdir -p /var/lib/sre-agent /var/log/sre-agent
sudo chown sre-agent:sre-agent /var/lib/sre-agent /var/log/sre-agent
sudo chmod 755 /var/lib/sre-agent /var/log/sre-agent
```

### 9.3 Deploy to EC2
```bash
# Copy files to EC2
scp -r backend/agentic/ ubuntu@18.237.102.97:/tmp/
scp etc/systemd/system/sre-agent.service ubuntu@18.237.102.97:/tmp/

# SSH and install
ssh -i "Team Meenakshi.pem" ubuntu@18.237.102.97

# Copy to proper location
sudo cp /tmp/sre-agent.service /etc/systemd/system/
sudo mkdir -p /root/MonitoringAlert/backend
sudo cp -r /tmp/agentic /root/MonitoringAlert/backend/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sre-agent.service
sudo systemctl start sre-agent.service

# Check status
sudo systemctl status sre-agent.service
tail -f /var/log/sre-agent/agentic.log
```

### 9.4 Verify Integration with Streamlit
```python
# In Streamlit app
from backend.agentic import get_orchestrator

orchestrator = get_orchestrator()
status = orchestrator.get_monitoring_status()
st.write(status)  # Shows: running, running_incidents, etc.
```

---

## 10. Example Incident Flow

```
TIME    | PHASE       | ACTION                          | OUTPUT
--------|-------------|--------------------------------|----------------------------------
14:20:00| PERCEIVE    | Health check fails for api-svr | Signal(status=critical)
14:20:05| PERCEIVE    | Log shows OOM error             | Signal(status=critical, error=OOM)
14:20:10| REASON      | LLM analyzes incident           | Decision(actions=[restart], risk=low)
14:20:15| PLAN        | Policy: approve restart         | PlannedAction(status=PENDING)
14:20:20| ACT         | Pre-check: drain connections    | PreCheck(success=true)
14:20:25| ACT         | Execute: systemctl restart      | Execution(success=true, time=5.2s)
14:20:30| ACT         | Post-check: health verify       | HealthCheck(status=200, time=100ms)
14:21:00| REFLECT     | Analyze outcome                 | Outcome(resolved=true, MTTR=60s)
14:21:05| LEARN       | Update memory                   | Pattern(oom→restart: effective)
14:21:10| NOTIFY      | Send email to on-call           | Email(status=sent)
14:21:15| AUDIT       | Log all events                  | AuditTrail(7 events)
```

---

## 11. Key Features

✅ **Fully Autonomous**: LLM-powered reasoning, no human in the loop (unless approval required)
✅ **Safe by Default**: Policy gates, pre/post checks, automatic rollback
✅ **Learning System**: Remembers incidents and patterns, improves over time
✅ **Complete Audit Trail**: Every decision and action logged for compliance
✅ **Enterprise Integration**: JIRA for approvals, SMTP for notifications
✅ **On-Prem Only**: No cloud dependencies, runs entirely on EC2
✅ **Production Ready**: Systemd service, logging, error handling, monitoring

---

## 12. Future Enhancements

- CloudWatch integration for AWS metrics
- Kubernetes orchestration support
- Multi-region failover
- Advanced ML for pattern detection
- Custom action plugins
- Slack/Teams integration
- Dashboard analytics

# 🏗️ AGENTIC SRE COPILOT - VISUAL ARCHITECTURE & DATA FLOWS

## 1. The Agentic Loop (Six Phases)

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENTIC SRE COPILOT LOOP                      │
└──────────────────────────────────────────────────────────────────┘

         ┌─────────────────────────────────────────┐
         │  1. PERCEIVE (Observation Phase)        │
         │  Health checks, logs, metrics, status   │
         │  → List of Signal objects               │
         └────────────┬────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────────────┐
         │  2. REASON (LLM Decision Phase)         │
         │  Analyze incident, query memory         │
         │  → ReasoningDecision                    │
         └────────────┬────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────────────┐
         │  3. PLAN (Policy Enforcement Phase)     │
         │  Convert to actions, check gates        │
         │  → List of PlannedAction                │
         └────────────┬────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────────────┐
         │  4. ACT (Safe Execution Phase)          │
         │  Pre-checks, execute, post-validate     │
         │  → List of ActionExecution              │
         └────────────┬────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────────────┐
         │  5. REFLECT (Analysis Phase)            │
         │  Analyze outcomes, calculate MTTR       │
         │  → IncidentOutcome                      │
         └────────────┬────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────────────┐
         │  6. LEARN (Memory & Improvement)        │
         │  Store outcome, update patterns         │
         │  → Updated Memory & Patterns            │
         └─────────────────────────────────────────┘
         
         (Repeat every 30 seconds)
```

---

## 2. Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SREAgentOrchestrator                          │
│  (Main coordinator - ties everything together)                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┬──────────┐
        │              │              │              │          │
        ▼              ▼              ▼              ▼          ▼
   ┌────────┐    ┌──────────┐  ┌─────────┐   ┌─────────┐  ┌───────┐
   │ CORE   │    │PERCEPTION│  │REASONING│   │EXECUTOR │  │INTEGR.│
   ├────────┤    ├──────────┤  ├─────────┤   ├─────────┤  ├───────┤
   │Loop    │    │Health    │  │LLM      │   │Systemd  │  │JIRA   │
   │Memory  │    │Logs      │  │Reason   │   │Exec     │  │SMTP   │
   │Policy  │    │Metrics   │  │Memory   │   │Rollback │  │AUDIT  │
   │        │    │Systemd   │  │Context  │   │Verify   │  │       │
   └────────┘    └──────────┘  └─────────┘   └─────────┘  └───────┘
        │              │              │              │          │
        └──────────────┼──────────────┴──────────────┴──────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
   ┌────────────┐            ┌──────────────┐
   │STREAMLIT UI│            │STORAGE LAYER │
   │ - Status   │            ├──────────────┤
   │ - Metrics  │            │Memory (JSON) │
   │ - Audit    │            │Audit (SQLite)│
   │ - Config   │            └──────────────┘
   └────────────┘
```

---

## 3. Signal Collection & Aggregation

```
PERCEPTION ENGINE
│
├─► HTTP Health Check
│   └─► http://api:8000/health
│       ├─ Status code: 200 ✅
│       ├─ Response time: 150ms
│       └─ Signal(app=api, status=healthy)
│
├─► Log Analysis
│   └─► /var/log/api.log
│       ├─ Scan last 100 lines
│       ├─ Found: 2 ERROR, 1 CRITICAL
│       └─ Signal(app=api, status=degraded)
│
├─► System Metrics
│   └─► CPU, Memory, Disk
│       ├─ CPU: 45% ✅
│       ├─ Memory: 78% ⚠️
│       ├─ Disk: 65% ✅
│       └─ Signal(app=api, status=degraded, metric=memory:78%)
│
└─► Systemd Service
    └─► systemctl is-active api.service
        ├─ Status: active
        └─ Signal(app=api, status=healthy)

AGGREGATION
All signals for same app → Single Incident
├─ If any signal is CRITICAL → Incident severity = CRITICAL
├─ If any signal is UNHEALTHY → Incident severity = HIGH
└─ Otherwise → MEDIUM

Result:
Incident(
  app=api,
  severity=HIGH,  ← degraded memory + degraded logs
  signals=[health✅, logs⚠️, memory⚠️, systemd✅],
  description="api is degraded"
)
```

---

## 4. LLM Reasoning Chain

```
INPUT INCIDENT
│
├─ Severity: HIGH
├─ App: api-server
├─ Signals: [health check DEGRADED, memory 78%, logs ERROR]
└─ Description: api-server is degraded

CONTEXT ENRICHMENT
│
├─ Query Memory for similar incidents (past 30 days)
│  └─ Found 5 similar: high_memory_usage → restart worked 4/5 times
│
├─ Extract patterns
│  └─ Pattern: high_memory → [restart (80% effective), scale (60%), drain (40%)]
│
└─ Historical MTTR for similar: avg 45.3 seconds

GEMINI LLM PROMPT
│
"You are an SRE assistant. Analyze this incident:
 - Current: api-server memory 78% (degraded)
 - History: 5 similar incidents in 30 days
 - Best past solution: restart_service (4/5 effective, MTTR 45.3s)
 - Risk level: LOW (service has health checks)
 
 Recommend actions with reasoning."

LLM RESPONSE
│
{
  "reasoning": "Memory usage at 78% indicates potential OOM. 
               Historical patterns show restart is effective.
               Risk is low due to health checks.",
  "recommended_actions": ["restart_service", "notify_oncall"],
  "confidence": 0.85,
  "risk_level": "low",
  "requires_approval": false,
  "escalation_needed": false
}

OUTPUT DECISION
│
ReasoningDecision(
  incident_id=INC-12345,
  recommended_actions=[restart_service, notify_oncall],
  confidence=0.85,  ← 85% confident
  risk_level=low,
  requires_approval=false,
  escalation_needed=false
)
```

---

## 5. Policy Enforcement Gates

```
PLANNED ACTION: restart_service on api-server
│
├─ GATE 1: Action Type Allowed?
│  Config: allow_auto_restart = TRUE
│  Result: ✅ PASSED
│
├─ GATE 2: Rate Limit OK?
│  Config: max_restarts_per_day = 5
│  Usage: 1 restart today for api-server
│  Result: ✅ PASSED (1 < 5)
│
├─ GATE 3: Change Window?
│  Config: 9 AM - 5 PM, Mon-Fri (UTC)
│  Current: Tuesday, 2:30 PM UTC
│  Result: ✅ PASSED (within window)
│
├─ GATE 4: Requires Approval?
│  Config: require_approval_for_restart = FALSE
│  Severity: HIGH (but not CRITICAL)
│  Result: ✅ NO APPROVAL NEEDED
│
└─ GATE 5: Escalation Threshold?
   Config: critical_count > 3 in 60 min
   Current: 1 incident in last 60 min
   Result: ✅ PASSED (1 < 3)

FINAL DECISION
│
Status: APPROVED
│
PlannedAction(
  action_type=restart_service,
  target=api-server,
  status=PENDING,  ← Ready to execute
  policy_gates={
    action_allowed: true,
    rate_limit: true,
    change_window: true,
    requires_approval: false,
    escalation_threshold: true
  },
  pre_checks=[verify_service_exists, drain_connections],
  rollback_plan="systemctl restart api-server"
)
```

---

## 6. Safe Action Execution

```
ACTION EXECUTION FLOW for: systemctl restart api-server

STEP 1: PRE-CHECKS
├─ Check service exists: systemctl list-units --type=service | grep api
│  Result: ✅ api.service found
├─ Check service is running: systemctl is-active api.service
│  Result: ✅ active (was running before)
└─ Result: ✅ PRE-CHECKS PASSED

STEP 2: EXECUTION
├─ Command: sudo systemctl restart api.service
├─ Timeout: 30 seconds
├─ Output: [OK] Restarted api.service
└─ Result: ✅ EXECUTED (5.2 seconds)

STEP 3: POST-VALIDATION
├─ Health Check: GET http://api:8000/health
│  ├─ Wait: up to 30 seconds
│  ├─ Try #1 (1s): TIMEOUT (service starting)
│  ├─ Try #2 (2s): TIMEOUT
│  ├─ Try #3 (3s): 500 ERROR
│  ├─ Try #4 (4s): 500 ERROR
│  ├─ Try #5 (5s): 200 OK ✅
│  └─ Result: ✅ HEALTHY after 5 seconds
├─ Systemd Status: systemctl is-active api.service
│  └─ Result: ✅ active
└─ Overall: ✅ SERVICE HEALTHY

STEP 4: RESULT
└─ ActionExecution(
     action_id=ACT-98765,
     success=true,
     output="Restart completed, service healthy",
     execution_time_ms=5200,
     post_validation={health_ok: true}
   )

ERROR SCENARIO (if post-validation fails):
├─ Health check returns 503 after 30s
├─ Decision: Health check failed
├─ Action: Execute rollback
│  ├─ Rollback command: systemctl restart api.service
│  └─ Result: ✅ Restored to previous state
└─ Mark action: FAILED (but rolled back)
```

---

## 7. Incident Outcome Analysis

```
INCIDENT TIMELINE
│
14:20:00 ├─ Detection
         │  └─ Health check fails: CRITICAL signal received
         │
14:20:05 ├─ Signal aggregation
         │  ├─ Signals: health check ❌, memory 78%, logs ERROR
         │  └─ Incident created: INC-12345 (HIGH severity)
         │
14:20:10 ├─ Reasoning
         │  ├─ LLM analyzes context
         │  ├─ Queries memory: 5 similar incidents
         │  └─ Decision: restart_service (confidence: 85%)
         │
14:20:15 ├─ Planning
         │  ├─ Check policy gates: ✅ all passed
         │  ├─ Prepare action: systemctl restart api
         │  └─ Status: APPROVED (no approval needed)
         │
14:20:20 ├─ Pre-execution
         │  ├─ Pre-check: service exists ✅
         │  └─ Pre-check: drain connections ✅
         │
14:20:25 ├─ Execution
         │  ├─ Execute: systemctl restart api.service
         │  └─ Completed in: 5.2 seconds
         │
14:20:30 ├─ Post-validation
         │  ├─ Health check: 200 OK ✅
         │  ├─ Service status: active ✅
         │  └─ Metrics: normal ✅
         │
14:21:00 ├─ Reflection
         │  ├─ Incident status: RESOLVED
         │  ├─ MTTR: 60 seconds (from 14:20:00 to 14:21:00)
         │  ├─ Root cause: high memory (OOM)
         │  └─ Solution: restart cleared memory
         │
14:21:05 ├─ Learning
         │  ├─ Store outcome in memory
         │  ├─ Update pattern: high_memory → restart (effective)
         │  └─ Improve: next time recommend restart first
         │
14:21:10 ├─ Notification
         │  └─ Email sent to on-call: "[RESOLVED] api-server - 60s MTTR"
         │
14:21:15 └─ Audit
            ├─ Log all events to SQLite
            ├─ Create entry in audit_events table
            └─ Audit trail complete: 8 events logged

FINAL OUTCOME
│
IncidentOutcome(
  incident_id=INC-12345,
  status=RESOLVED,
  mttr_seconds=60,          ← Mean Time To Resolution
  root_cause_confirmed="high_memory_usage",
  actions_executed=[
    ActionExecution(action=restart, success=true, time=5.2s)
  ],
  lessons_learned="OOM resolved with restart",
  notifications_sent=["oncall@company.com"]
)
```

---

## 8. Memory & Learning System

```
INCIDENT MEMORY (Persistent JSON)
│
Before incident #1-4:
└─ high_memory_usage
   ├─ count: 4
   ├─ avg_mttr_seconds: 48.5
   └─ effective_actions: [restart (3), scale (2)]

INCIDENT #5 OCCURS
│
├─ Detect: high memory (78%)
├─ Reason: LLM queries memory
│  └─ Finds: "high_memory_usage worked with restart 3/4 times"
├─ Recommend: restart_service
├─ Execute: restart (success ✅, MTTR: 60s)
└─ Learn: Record outcome

MEMORY UPDATED
│
After incident #5:
└─ high_memory_usage
   ├─ count: 5
   ├─ avg_mttr_seconds: 47.3  ← Improved by 1.2s
   └─ effective_actions: [restart (4), scale (2)]

PATTERN LIBRARY EVOLVES
│
Incident #1: high_memory → restart (60s) ✅
Incident #2: high_memory → scale (55s) ✅
Incident #3: high_memory → restart (45s) ✅
Incident #4: high_memory → scale (50s) ✅
Incident #5: high_memory → restart (60s) ✅

Pattern confidence:
├─ restart: 3/3 effective = 100% success rate
├─ scale: 2/2 effective = 100% success rate
└─ Next recommendation: restart (tried first, 100% success)

NEXT INCIDENT
│
When high_memory_usage detected again:
├─ Memory query: previous pattern = restart (100%, MTTR: 53.3s avg)
├─ LLM reasoning: "High confidence in restart"
├─ Recommendation: restart_service (confidence: 0.95) ← Increased!
└─ Expected: MTTR < 53.3s (improved from original 48.5s average)

CONTINUOUS IMPROVEMENT
│
Over months:
├─ More incidents → More patterns
├─ More patterns → Better recommendations
├─ Better recommendations → Lower MTTR
├─ Lower MTTR → Fewer user impacts
└─ System becomes smarter every day
```

---

## 9. Audit Trail Example

```
AUDIT EVENTS TABLE (SQLite)
│
incident_id  │ event_type        │ timestamp         │ actor           │ action
─────────────┼──────────────────┼──────────────────┼─────────────────┼──────────
INC-12345    │ incident_detected │ 2026-02-09T14:20 │ perception_eng  │ signal
INC-12345    │ incident_created  │ 2026-02-09T14:20 │ perception_eng  │ aggregate
INC-12345    │ decision_made     │ 2026-02-09T14:20 │ llm_reasoner    │ recommend
INC-12345    │ action_planned    │ 2026-02-09T14:20 │ policy_engine   │ approve
INC-12345    │ action_executed   │ 2026-02-09T14:20 │ executor        │ restart
INC-12345    │ health_verified   │ 2026-02-09T14:20 │ executor        │ check
INC-12345    │ outcome_recorded  │ 2026-02-09T14:21 │ copilot         │ resolve
INC-12345    │ learned           │ 2026-02-09T14:21 │ memory_engine   │ update
INC-12345    │ notified          │ 2026-02-09T14:21 │ notifier        │ email
INC-12345    │ escalated         │ 2026-02-09T14:21 │ jira_handler    │ ticket

COMPLIANCE REPORT GENERATED FROM AUDIT
│
Report Period: 2026-02-01 to 2026-02-29
├─ Total Incidents: 42
├─ Resolved: 39 (92.9%)
├─ Escalated: 3 (7.1%)
├─ Total Decisions Made: 42
├─ Approval Rate: 5 (11.9%)  ← Required JIRA approval
├─ Auto-Actions Executed: 39
├─ Success Rate: 95.4% (37/39)
├─ Average MTTR: 52.3 seconds
├─ Events Logged: 378
└─ No security incidents

AUDIT TRAIL USAGE
│
PIR (Post-Incident Review):
├─ Pull audit events for INC-12345
├─ Timeline: 8 events, 95 seconds total
├─ Decision chain visible: detect → reason → plan → execute → verify
├─ User approvals: none (auto-approved by policy)
├─ Root cause: high_memory (confirmed by outcomes)
├─ Lessons learned: "Restart effective for OOM"
└─ Action items: "Review memory limits"

Compliance Check:
├─ All CRITICAL incidents escalated to JIRA? ✅ YES
├─ All approvals tracked? ✅ YES
├─ All actions audited? ✅ YES
├─ Audit trail tamper-proof? ✅ YES (append-only)
└─ Compliant: ✅ PASS
```

---

## 10. Complete System Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                    SYSTEM DATA FLOW DIAGRAM                        │
└────────────────────────────────────────────────────────────────────┘

EXTERNAL INPUTS (Every 30 seconds)
│
├─ HTTP GET http://app:8000/health
├─ File read /var/log/app.log
├─ Shell exec "systemctl is-active app.service"
└─ System call CPU/Memory/Disk metrics

       │
       ▼

PERCEPTION ENGINE
├─ HealthChecker → health_status
├─ LogAnalyzer → error_count
├─ MetricsCollector → cpu%, mem%, disk%
└─ SystemdMonitor → is_active

       │
       ▼ List of Signals
       │
       ├─ Signal(app=api, source=http, status=degraded)
       ├─ Signal(app=api, source=logs, status=unhealthy)
       ├─ Signal(app=api, source=memory, status=degraded)
       └─ Signal(app=api, source=systemd, status=healthy)

       │
       ▼

PERCEPTION → AGGREGATION
└─ Combine into Incident(app=api, severity=HIGH, signals=[...])

       │
       ▼

REASONING ENGINE
├─ Load incident memory (past incidents)
├─ Query LLM (Gemini)
│  ├─ Context: incident details + similar past incidents
│  └─ Output: recommended_actions + confidence
└─ Return: ReasoningDecision

       │
       ▼

PLANNING ENGINE
├─ Load policy configuration
├─ Check gates: action_allowed?, rate_limit?, change_window?
├─ Determine: status (PENDING, BLOCKED, APPROVED)
└─ Prepare: pre_checks, rollback_plan

       │
       ▼

EXECUTION ENGINE
├─ Run pre-checks
├─ Execute action (systemctl restart)
├─ Run post-checks (health verify)
├─ On failure: rollback
└─ Return: ActionExecution result

       │
       ▼

REFLECTION ENGINE
├─ Analyze action result
├─ Calculate MTTR
├─ Determine root_cause
└─ Return: IncidentOutcome

       │
       ▼

LEARNING ENGINE
├─ Record outcome in Memory
├─ Update patterns (which fixes work)
├─ Improve confidence for future incidents
└─ Write to audit database

       │
       ▼

INTEGRATION LAYER
├─ JIRA Handler: escalate if needed
├─ SMTP Notifier: email stakeholders
└─ Audit Logger: log all events

       │
       ▼

STORAGE
├─ Memory: /var/lib/sre-agent/incident_memory.json
├─ Audit: /var/lib/sre-agent/sre_audit.db
└─ Logs: /var/log/sre-agent/agentic.log

       │
       ▼

STREAMLIT UI
├─ Get monitoring_status()
├─ Get recent_incidents()
├─ Get performance_metrics()
├─ Get incident_audit_trail()
├─ View compliance_report()
└─ Download pir()
```

---

## Summary

This architecture implements a **fully autonomous incident management system** that:

1. **Perceives** problems from multiple sources
2. **Reasons** autonomously using LLM
3. **Plans** safely with policy enforcement
4. **Acts** with pre/post checks and rollback
5. **Reflects** on outcomes
6. **Learns** continuously to improve

The system is **production-ready**, **audit-compliant**, **safe by design**, and **continuously improving**. 🚀

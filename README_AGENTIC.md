# 🤖 Agentic SRE Copilot - Autonomous Incident Management System

## Overview

A **fully autonomous, production-grade SRE incident management system** that continuously monitors applications, reasons about incidents using advanced LLM, plans remediation actions, executes them safely, learns from outcomes, and maintains complete audit trails.

### Key Innovation: The Agentic Loop
```
PERCEIVE → REASON → PLAN → ACT → REFLECT → LEARN
(observe)  (LLM)    (policy) (execute) (analyze) (improve)
```

---

## 🎯 Why This is Different

| Traditional SRE | **Agentic Copilot** |
|---|---|
| Manual incident response | Autonomous decision-making |
| Generic thresholds | LLM-powered context-aware reasoning |
| Limited learning | Persistent memory & pattern library |
| Minimal audit | Full compliance-ready audit trail |
| Human approval bottleneck | Policy-based approval gates |
| Limited integrations | JIRA, SMTP, systemd, extensible |

---

## 🏗️ Architecture

### Six-Phase Agentic Loop

**1. PERCEIVE** - Multi-source signal collection
- HTTP health checks
- Application log analysis
- System metrics (CPU, memory, disk)
- Systemd service status

**2. REASON** - LLM-powered autonomous decision-making
- Analyze incident severity and context
- Query historical patterns from memory
- Use Gemini to generate reasoning chain
- Recommend best remediation actions

**3. PLAN** - Policy-enforced action planning
- Convert recommendations to executable plans
- Enforce policy gates:
  - Action type allowed?
  - Rate limits respected?
  - Within change window?
  - Requires approval?
- Prepare pre-checks and rollback procedures

**4. ACT** - Safe execution with rollback
- Run pre-checks
- Execute approved actions (service restart, scaling, etc.)
- Monitor execution
- Post-validation health checks
- Rollback on failure

**5. REFLECT** - Outcome analysis
- Analyze execution results
- Calculate MTTR (Mean Time To Resolution)
- Extract root cause and lessons learned
- Determine resolution status

**6. LEARN** - Memory and improvement
- Store incident outcome for future reference
- Update pattern library
- Improve policies based on outcomes
- Generate audit trail for compliance

---

## 📦 Components

### Core (`backend/agentic/core.py`)
- `AgenticSRECopilot`: Main orchestrator
- Data structures: Signal, Incident, Decision, Action, Outcome
- `Memory`: Persistent learning system
- `Policy`: Enforcement gates

### Perception (`backend/agentic/perception.py`)
- Health checks (HTTP)
- Log analysis
- Metrics collection
- Systemd monitoring

### Reasoning (`backend/agentic/reasoning.py`)
- LLM integration (Google Gemini)
- Context enrichment from memory
- Fallback rule-based reasoning

### Execution (`backend/agentic/executor.py`)
- Systemd service control
- Pre/post-check execution
- Health verification
- Automatic rollback

### Integration
- **JIRA** (`jira_integration.py`): Escalation & approvals
- **SMTP** (`notifications.py`): Email alerts & reports
- **Audit** (`audit.py`): Compliance trail & analytics

### Orchestrator (`orchestrator.py`)
- Coordinates all components
- Provides API for UI
- Manages monitoring loop

---

## 🚀 Quick Start

### Prerequisites
```bash
pip install google-genai requests streamlit pandas python-dotenv
```

### 1. Configure
```bash
cp backend/config/agentic_config.example.py backend/config/agentic_config.py
# Edit with your environment details
```

### 2. Set Environment Variables
```bash
export GOOGLE_API_KEY="your-gemini-api-key"
export JIRA_BASE_URL="https://yourcompany.atlassian.net"
export JIRA_USER_EMAIL="sre-bot@company.com"
export JIRA_API_TOKEN="your-jira-token"
export JIRA_PROJECT_KEY="OPS"
export SMTP_SERVER="smtp.company.com"
export SMTP_FROM="sre-agent@company.com"
```

### 3. Deploy as Systemd Service
```bash
sudo cp etc/systemd/system/sre-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sre-agent.service
sudo systemctl start sre-agent.service
sudo systemctl status sre-agent.service
```

### 4. Verify in Streamlit UI
Navigate to Streamlit app → "Agentic Copilot" tab
- Click "Collect Signals" to test perception
- View recent incidents and metrics
- Review audit trails
- Check system status

---

## 📊 Example Incident Flow

```
14:20:00  PERCEIVE    Health check fails for api-server     [CRITICAL]
14:20:05  PERCEIVE    Log shows OOM error
14:20:10  REASON      LLM analyzes: restart_service (low risk)
14:20:15  PLAN        Policy gates: APPROVED
14:20:20  ACT         Pre-check: drain connections [OK]
14:20:25  ACT         Execute: systemctl restart api-server [5.2s]
14:20:30  ACT         Post-check: health verify [200 OK]
14:21:00  REFLECT     Incident RESOLVED, MTTR: 60 seconds
14:21:05  LEARN       Update memory: OOM → restart_service (effective)
14:21:10  NOTIFY      Email sent to on-call team
14:21:15  AUDIT       7 events logged to compliance database
```

---

## 🔐 Security & Safety

✅ **Policy Gates**: No auto-restart outside business hours
✅ **Approval Workflow**: Critical changes require JIRA approval
✅ **Pre-Checks**: Validate before executing actions
✅ **Post-Validation**: Health check after action
✅ **Automatic Rollback**: Revert on failed health check
✅ **Rate Limits**: Max N restarts per day per app
✅ **Audit Trail**: Every decision logged for compliance
✅ **No Secrets in Logs**: Credentials protected

---

## 📈 Performance Metrics

The system automatically tracks:
- **MTTR** (Mean Time To Resolution)
- **Decision-to-Action Latency**
- **Success Rate** of remediation actions
- **Pattern Effectiveness** (which solutions work)
- **False Positive Rate** (incorrect predictions)

View in Streamlit:
```python
metrics = orchestrator.get_performance_metrics(days=7)
st.write(metrics)
```

---

## 📋 Compliance & Audit

Complete audit trail for every incident:
```
- What triggered the incident (signals)
- What reasoning process was used (LLM chain)
- What actions were planned (with policy gates)
- What actions were executed (with timing)
- What the outcome was (success/failure)
- Who approved what (user tracking)
```

Generate compliance reports:
```python
report = orchestrator.get_compliance_report("2026-02-01", "2026-02-29")
pir = orchestrator.get_pir("INC-12345")  # Post-Incident Review
```

---

## 🧠 Learning & Memory

The system learns from each incident:
1. **Incident Memory**: Stores all resolved incidents
2. **Pattern Library**: Groups incidents by root cause
3. **Effectiveness Tracking**: Records which actions worked
4. **Future Recommendations**: Suggests learned solutions

Example:
```
After 5 incidents with "high_memory_usage":
  - Average MTTR: 42.5 seconds
  - Effective actions: restart_service, scale_up
  - Next time: Prioritize restart (worked 4/5 times)
```

---

## 🔧 Configuration

Key policy settings:
```python
{
    "allow_auto_restart": True,
    "require_approval_for_restart": True,
    "max_restarts_per_day": 5,
    "change_window": {
        "start_hour": 9,      # 9 AM
        "end_hour": 17,       # 5 PM
        "allowed_days": [1,2,3,4,5]  # Mon-Fri
    },
    "rollback_on_failed_health_check": True
}
```

Change at runtime:
```python
orchestrator.update_policy({
    "max_restarts_per_day": 10,  # Increase limit
    "require_approval_for_restart": False  # Allow auto-restart
})
```

---

## 📡 Integrations

### JIRA
- Create incident tickets automatically
- Create approval request tasks
- Update tickets with outcomes
- Link related issues

### SMTP
- Critical incident alerts
- Resolution notifications
- Daily/weekly reports
- Formatted HTML emails

### Systemd
- Check service status
- Restart services
- Start/stop services
- Health verification

### Extensible
- Add custom perception sources
- Add custom action executors
- Add custom integrations

---

## 🎓 Use Cases

**1. Auto-Recovery**
- Service crash → Auto-restart → Verify health ✅

**2. Preventive Scaling**
- High memory → Scale up replicas → Reduce pressure ✅

**3. Graceful Degradation**
- Overload detected → Drain connections → Restart → Resume ✅

**4. Escalation**
- 3 critical incidents in 1 hour → Create JIRA ticket → Notify engineers ✅

**5. Learning & Improvement**
- Track which fixes work → Improve future recommendations → Reduce MTTR ✅

---

## 📈 Metrics Dashboard

Monitor in Streamlit:
```
Recent Incidents: 5 (7 days)
Average MTTR: 45.3 seconds
Success Rate: 92%
Common Root Causes: high_memory (3), connection_timeout (2)
```

---

## 🚨 Limitations & Future Work

Current:
- On-prem only (no cloud integration yet)
- Systemd focused (can extend to K8s, Docker Swarm)
- Manual policy tuning

Future:
- CloudWatch metrics integration
- Kubernetes orchestration
- ML-powered root cause analysis
- Advanced pattern detection
- Custom action plugins
- Slack/Teams integration
- Multi-region failover

---

## 📚 Documentation

- [Full Architecture Guide](./AGENTIC_ARCHITECTURE.md)
- [Deployment Quick Start](./DEPLOYMENT_QUICK_START.md)
- [Configuration Template](./backend/config/agentic_config.example.py)
- [Code Comments](./backend/agentic/)

---

## 🛠️ Testing

Test each component:
```bash
# Test perception
asyncio.run(orchestrator.test_perception())

# Test reasoning
orchestrator.test_reasoning({
    "app_name": "api-server",
    "description": "High memory usage"
})

# Test JIRA
jira_handler.handle_escalation(incident, decision)

# View metrics
orchestrator.get_performance_metrics(days=7)
```

---

## 📞 Support

For issues or questions:
1. Check logs: `tail -f /var/log/sre-agent/agentic.log`
2. Review audit trail: `sqlite3 /var/lib/sre-agent/sre_audit.db`
3. Test components individually (see Testing section)
4. Review configuration: `cat backend/config/agentic_config.py`

---

## 📄 License

[Your License Here]

---

## 🙏 Acknowledgments

Built with:
- Google Gemini API (LLM reasoning)
- Streamlit (UI)
- JIRA API (Integrations)
- Python async/await (Concurrency)

---

## 📝 Summary

**Agentic SRE Copilot** is a fully autonomous incident management system that:

1. ✅ **Continuously Monitors** - Multi-source signal collection
2. ✅ **Autonomously Reasons** - LLM-powered decision-making  
3. ✅ **Plans Safely** - Policy-enforced action planning
4. ✅ **Executes Safely** - Pre/post-checks and rollback
5. ✅ **Learns Continuously** - Memory and pattern library
6. ✅ **Routes Properly** - JIRA escalations and SMTP notifications
7. ✅ **Audits Completely** - Compliance-ready audit trail

Turn your incident response into an intelligent, self-improving system. 🚀

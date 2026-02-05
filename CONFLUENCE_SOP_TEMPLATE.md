# Agentic Self‑Healing Playbook (EC2 + Docker + Outlook Alerts)

**By Porselvi Baskar**

**Owner:** SRE/Platform  
**Audience:** On‑call engineers, service owners, automation agents  
**Last Reviewed:** 2026-02-05  
**Change Log:** Update this section whenever steps or guardrails change.

---

## 1. Purpose (human)
This page defines how our automation Agent heals services after deployments and during incidents.

It describes:
- What the Agent is allowed to do (cleanup, restart, minimal deploy tasks, health checks)
- Where the Agent is allowed to touch (explicit paths, explicit services)
- How the Agent should behave if information is missing (perform a safe, targeted web search and continue)

---

## 2. Golden Rules (Agent must obey)
1. **Least privilege:** Only touch declared paths, services, and commands in this page.
2. **No surprises:** Never create or delete outside the listed paths; refuse if ambiguous.
3. **Dry‑run mindset:** Prefer a lightweight read/check before a write/delete.
4. **Stop on uncertainty:** If unsure, stop and escalate with current findings.
5. **Log everything:** Record exactly what you did (command, target path, counts, status).
6. **Post‑deploy self‑heal:** After a successful deploy, immediately run the job's self‑heal block.

---

## 3. Global Safety & Scope (for all jobs)

### 3.1 Allowed commands (Agent must reject anything else)
- `/usr/bin/df`
- `/usr/bin/find`
- `/usr/bin/rm`
- `/usr/bin/docker`
- `/usr/bin/systemctl`
- `/usr/bin/curl`

### 3.2 General cleanup policy
- Delete only files (no directories) matching allowed patterns, and only if older than the configured RetentionDays.
- Always run `df -h` before and after cleanup.
- Never expand a relative path; require absolute paths.

### 3.3 Restart policy
- Only restart the listed service for a job (Docker service name or systemd unit).
- One restart attempt. If it fails, stop and escalate.

### 3.4 Health verification policy
- Use the exact commands listed for the job (e.g., `curl -fsS http://localhost:PORT/healthz`).
- Consider the job healthy if all listed verifications succeed.

### 3.5 Notifications
After each run, send an Outlook email (via our Power Automate flow) with:
- Job name, action taken, status (healed/failed).
- `df -h` before/after deltas, number of files deleted per path.
- Restart/health results (first/last lines).
- Any warnings and the relevant log snippets.

---

## 4. Job Catalog (human‑readable; Agent‑parsable)

Add/modify jobs here. Each job block below contains a human explanation plus a machine‑hint section in a JSON code block titled `AGENT‑STEPS`.

The Agent must parse the JSON to plan the execution. If a field is absent, follow the Web Search Fallback policy (§6).

### 4.1 ETL‑DAILY (Post‑deploy disk hygiene + Docker restart)

**What this does (human):**
- Cleans ETL temp/log clutter in two specific directories.
- Restarts the Docker service `etl-svc`.
- Verifies with a local health endpoint and a quick log peek.

**Notes to humans:**
- Review retention (3 days) is safe for current workload; adjust if data patterns change.

**AGENT‑STEPS (strict JSON):**
```json
{
  "job": "ETL-DAILY",
  "reason": "Post-deployment self-heal and disk hygiene",
  "cleanup": {
    "paths": ["/var/tmp/etl", "/data/etl/tmp"],
    "patterns": ["*.tmp", "*.log", "ibtmp*"],
    "retention_days": 3
  },
  "restart": { "kind": "docker", "name": "etl-svc" },
  "verify": {
    "commands": [
      "df -h",
      "curl -fsS http://localhost:9000/healthz"
    ]
  }
}
```

### 4.2 WEBAPI‑PROD (Temp cleanup + systemd restart + HTTP health)

**What this does (human):**
- Cleans temporary files for the web API.
- Restarts the systemd service `webapi`.
- Checks `/health` and recent systemd logs.

**AGENT‑STEPS (strict JSON):**
```json
{
  "job": "WEBAPI-PROD",
  "reason": "Post-deploy self-heal and temp log compaction",
  "cleanup": {
    "paths": ["/var/tmp/webapi"],
    "patterns": ["*.tmp", "*.old"],
    "retention_days": 2
  },
  "restart": { "kind": "systemd", "name": "webapi" },
  "verify": {
    "commands": [
      "curl -fsS http://localhost:8080/health",
      "journalctl -u webapi -n 80 --no-pager | tail -n 40"
    ]
  }
}
```

### 4.nn (Template for new jobs)

**What this does (human):**
Write a 2–3 line summary for humans.

**AGENT‑STEPS (strict JSON):**
```json
{
  "job": "___",
  "reason": "___",
  "cleanup": {
    "paths": ["/absolute/path/one", "/absolute/path/two"],
    "patterns": ["*.tmp", "*.log"],
    "retention_days": 3
  },
  "restart": { "kind": "docker|systemd|k8s", "name": "service-or-deployment" },
  "verify": {
    "commands": [
      "curl -fsS http://localhost:PORT/healthz"
    ]
  }
}
```

---

## 5. Post‑Deployment Auto‑Heal (when to run)

**Trigger:** Immediately after a successful deployment of a job listed above.

**Sequence (Agent):**
1. Read this page → locate the job's `AGENT‑STEPS` block.
2. Validate paths are absolute and within the job's list.
3. Run `df -h` (baseline) → perform cleanup (retention enforced) → run `df -h` again.
4. Restart the declared service (Docker/systemd/k8s exactly as specified).
5. Run all verification commands.
6. Send notification email (success/failure + full summary).
7. Append a one‑line action summary to Incident Notes (§8).

---

## 6. Web Search Fallback (only if something is missing)

### When to use:
- A field in `AGENT‑STEPS` is missing (e.g., `verify.commands` not provided).
- A command consistently fails due to a known change (e.g., health endpoint moved).
- You need the current doc for a standard command usage (e.g., `journalctl` flags).

### How to search (Agent):
1. Construct a minimal, targeted query that includes the tool and intent, e.g.:
   - "systemctl restart service meaning"
   - "docker restart <name> exit codes"
   - "journalctl -u webapi options no-pager"
   - "curl health check examples -k -f -s"

2. Prefer official or high‑reputation results.

3. Confirm at least two independent sources if it changes semantics or safety.

4. Apply the Golden Rules (§2) and Global Safety (§3) before executing.

5. Record the URL titles and what was learned in the notification email.

6. If a search suggests touching paths/services not declared for the job, do not proceed—escalate instead.

---

## 7. Failure Handling & Escalation

- Mark the run **FAILED** if any restart/verification step fails.
- Include the failing command, exit code, and the last ~80 lines of relevant logs in the email.
- Do not attempt repeated restarts or extra cleanup beyond the job's declared scope.
- Escalate to on‑call with your full summary.

---

## 8. Incident Notes (append one‑liner per run)

The Agent should append a single line per run with timestamp, job, action, result, file counts, and key deltas.

**Format:**
```
[YYYY-MM-DD HH:MM:SS] JOB=ETL-DAILY | CLEAN=/var/tmp/etl:12,/data/etl/tmp:7 | RESTART=docker:etl-svc | HEALTH=OK | DISK=68%→54% | LINKS=<optional references>
```

---

## 9. Quick Examples (for humans)

### Example 1 – ETL‑DAILY after deploy
- Expect 10–60 files deleted across `/var/tmp/etl` and `/data/etl/tmp` (varies by day).
- A single `docker restart etl-svc`.
- Health at `http://localhost:9000/healthz` should return HTTP 200 in <2 seconds.

### Example 2 – WEBAPI‑PROD temp churn
- Expect cleanups only under `/var/tmp/webapi`; never touch `/var/log` or app data.
- `systemctl restart webapi` once; verify `curl` to `/health` returns 200.
- Tail recent journal lines for quick sanity.

---

## 10. Appendix — Rationale (human)

- Cleanup plus a controlled restart often removes transient pressure (temp/log bloat).
- Strict scoping and retention make the process safe and repeatable.
- Web Search Fallback allows the Agent to remain effective when runbook details lag real‑world changes—without overruling scope boundaries.

### To add a new job
1. Duplicate the Job block template in §4.
2. Fill in paths, patterns, retention, restart, verify.
3. Communicate the change to on‑call and service owners.

---

## 11. Health Check Monitoring SOP

### Overview
This section describes the automated health check monitoring system that validates service availability, implements retry logic for transient failures, and maintains comprehensive logs of all health check operations.

### Prerequisites
- Access to Monitoring Dashboard (Streamlit UI)
- Health check endpoints configured in `apps.csv`
- Health server running on port 8000 (EC2: http://18.237.102.97:8000)

### Health Check Tab Features

#### 11.1 Available Services
The monitoring system tracks multiple services including:
- **AuthService** - httpbin.org/status/200 (always healthy)
- **PaymentAPI** - httpbin.org/status/500 (always unhealthy)
- **UserService** - httpstat.us/random/200,500 (random)
- **FlakyService** - EC2 /health/flaky (fails first, succeeds on retry)
- **EPAS_Healthy** - EC2 /health/epas (toggleable)

#### 11.2 Health Check Logic
Services are classified as:
- **Healthy** (✅): URL is reachable (HTTP 200-299 status)
- **Unhealthy** (❌): Connection fails or returns error status (4xx, 5xx)

#### 11.3 Retry Mechanism
**Configuration:**
- Enable "Automatically retry failed apps" checkbox
- Set retry delay (default: 2 seconds)

**Behavior:**
1. Run initial health check on all apps
2. For any unhealthy apps:
   - Wait for configured delay
   - Automatically retry once
   - Update status based on retry result

#### 11.4 Demo: Flaky Service Endpoint
**Purpose:** Demonstrates retry behavior for transient failures

**Endpoint:** `http://18.237.102.97:8000/health/flaky`

**Behavior:**
- First attempt: Returns HTTP 500 (FAIL)
- Second attempt: Returns HTTP 200 (SUCCESS)
- Subsequent attempts: Returns HTTP 200

**Test Steps:**
1. Navigate to Health Check tab
2. Enable "Automatically retry failed apps"
3. Set retry delay to 2 seconds
4. Click "Run Health Check"
5. Observe FlakyService:
   - Initial check: ❌ Unhealthy
   - After retry: ✅ Healthy

**Reset:** Restart health_server.py to reset flaky state counter

#### 11.5 Health Check Logs

**Purpose:** Comprehensive audit trail of all health check operations

**Log Events:**
- `RUN_START`: Health check run initiated
- `CHECK_OK`: URL returned success status
- `CHECK_FAIL`: URL failed or unreachable
- `RETRY_START`: Retry initiated for failed app
- `RETRY_OK`: Retry succeeded
- `RETRY_FAIL`: Retry still failed

**Log Format:**
```
[2026-02-05 14:32:15] RUN_START | Running health check for 7 apps
[2026-02-05 14:32:16] CHECK_OK | AuthService: http://httpbin.org/status/200
[2026-02-05 14:32:16] CHECK_FAIL | FlakyService: http://18.237.102.97:8000/health/flaky
[2026-02-05 14:32:18] RETRY_START | FlakyService: Retrying after 2s delay
[2026-02-05 14:32:18] RETRY_OK | FlakyService: Success on retry
```

**Viewing Logs:**
- Last 50 log entries displayed in Health Check tab
- Most recent entries at the top
- Persistent across sessions (stored in session state)

#### 11.6 Test Endpoints Reference

| Endpoint | URL | Expected Behavior |
|----------|-----|-------------------|
| Always OK | http://18.237.102.97:8000/health/ok | Always returns 200 |
| Always Fail | http://18.237.102.97:8000/health/fail | Always returns 500 |
| Flaky | http://18.237.102.97:8000/health/flaky | Fails once, then succeeds |
| EPAS | http://18.237.102.97:8000/health/epas | Toggleable via restart endpoint |
| EPAS Toggle | http://18.237.102.97:8000/epas/restart | Toggles EPAS healthy/unhealthy state |

#### 11.7 Troubleshooting

| Issue | Resolution |
|-------|-----------|
| All apps show unhealthy | Check network connectivity, verify health server running |
| Retry not triggering | Ensure "Automatically retry failed apps" is enabled |
| Logs not showing | Refresh page to reinitialize session state |
| Flaky endpoint always fails | Restart health_server.py to reset counter |

#### 11.8 Operations Runbook

**Daily Operations:**
1. Navigate to Health Check tab
2. Review current health status of all services
3. Enable auto-retry for production checks
4. Review logs for patterns or recurring failures

**Incident Response:**
1. Check Health Check Logs for failure timeline
2. Note which services failed and when
3. Review retry outcomes to identify transient vs persistent issues
4. Escalate persistent failures to service owners

**Maintenance:**
1. Update `apps.csv` when adding/removing services
2. Adjust retry delay based on service characteristics
3. Monitor log growth and consider archival strategy

#### 11.9 Configuration Files

**apps.csv format:**
```csv
app_name,environment,health_check_url
AuthService,prod,http://httpbin.org/status/200
FlakyService,test,http://18.237.102.97:8000/health/flaky
```

**Session State Variables:**
- `health_check_logs`: List of all log entries
- `health_check_results`: Current status of all apps
- `last_check_time`: Timestamp of last health check run

#### 11.10 Integration with Self-Healing

**Post-Deployment Flow:**
1. Deployment completes successfully
2. Automated health check runs with retry enabled
3. Failed services trigger self-heal workflow
4. Health check logs provide audit trail for compliance

**Escalation Criteria:**
- Service fails both initial check and retry → Trigger alert
- Multiple services fail simultaneously → Possible infrastructure issue
- Flaky pattern detected → Review service stability

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-03 | Initial creation | Porselvi Baskar |
| 1.1 | 2026-02-05 | Added Health Check Monitoring SOP (§11) | DevOps Team |

---

**End of page**

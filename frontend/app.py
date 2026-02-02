import random

import streamlit as st
import pandas as pd
import requests
from api_client import start_agent, stop_agent, simulate_incident, fetch_incidents
# --------- ADDITIONAL IMPORTS (safe, no backend dependency) ----------
from datetime import datetime, timezone, time
import json
import csv
import os

import time as pytime

from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Agent Automation",
    layout="centered",  # 👈 important for login
)

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def generate_random_tags():
    tag_pool = [
        "deploy", "hotfix", "canary", "blue-green", "rollback-ready",
        "prod-safe", "infra-change", "config-update", "zero-downtime",
        "observability", "slo-impact", "customer-facing"
    ]
    return random.sample(tag_pool, k=random.randint(2, 5))

# -------- HEALTH CHECK FUNCTIONS --------
def load_apps_csv(file_path="apps.csv"):
    """Load apps from CSV file"""
    apps = []
    try:
        if os.path.exists(file_path):
            with open(file_path, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    apps.append({
                        "AppName": row["AppName"],
                        "URL": row["URL"],
                        "Expected": row["Expected"]
                    })
    except Exception as e:
        st.error(f"Error loading apps.csv: {str(e)}")
    return apps

def check_app_health(app):
    """Check single app health"""
    try:
        response = requests.get(app["URL"], timeout=8, verify=False)
        status = response.status_code
        content = response.text.strip()
        if app["Expected"] in content:
            return {
                "AppName": app["AppName"],
                "URL": app["URL"],
                "Status": status,
                "Result": "✅ OK",
                "Color": "green"
            }
        else:
            return {
                "AppName": app["AppName"],
                "URL": app["URL"],
                "Status": status,
                "Result": "❌ Invalid response",
                "Color": "red"
            }
    except Exception as e:
        return {
            "AppName": app["AppName"],
            "URL": app["URL"],
            "Status": "N/A",
            "Result": f"❌ Error: {str(e)[:30]}",
            "Color": "red"
        }

def send_health_check_to_teams(results, attempt=1, recovered=None):
    """Send health check results to Teams"""
    teams_url = os.getenv("TEAMS_WEBHOOK_URL", "")
    if not teams_url:
        st.warning("⚠️ TEAMS_WEBHOOK_URL not configured")
        return False

    # Build markdown table
    header = "| AppName | URL | Status | Result |\n|---------|-----|--------|--------|"
    rows = [f"| {r['AppName']} | {r['URL']} | {r['Status']} | {r['Result']} |" for r in results]
    md_table = header + "\n" + "\n".join(rows)

    sections = []
    for r in results:
        sections.append({
            "activityTitle": f"**{r['AppName']}** → {r['Result']}",
            "activitySubtitle": f"URL: {r['URL']}\nStatus: {r['Status']}",
            "markdown": True
        })

    if recovered:
        sections.append({
            "activityTitle": f"💚 **Recovered Apps**",
            "text": ", ".join(recovered),
            "markdown": True
        })

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary": "Health Check Results",
        "sections": [
            {
                "activityTitle": f"📊 **Health Check Summary (Attempt {attempt})**",
                "text": md_table,
                "markdown": True
            }
        ] + sections
    }

    try:
        r = requests.post(teams_url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        st.error(f"Failed to send to Teams: {str(e)}")
        return False


def ai_chatbot_response(user_query, ui_context, vuln_df=None):
    import os
    from google.generativeai import GenerativeModel
    
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return "AI search not available: GOOGLE_API_KEY not set."
    
    # Prepare context
    context_info = f"""
System Context:
- Incidents: {ui_context.get('incidents', [])}
- Certificates: {ui_context.get('certificates', [])}
- Deployments: {ui_context.get('deployments', 'N/A')}
- Disk Issues: {ui_context.get('disk_issues', 'N/A')}

Vulnerability KB (if available): {vuln_df.head(3).to_dict() if vuln_df is not None else 'Not loaded'}
"""
    
    system_prompt = f"""
You are an advanced DevOps Engineer AI chatbot for system monitoring and incident response.

Your role:
1. Monitor and respond to system issues autonomously.
2. Provide troubleshooting steps based on best practices from your knowledge.
3. If you can rectify the issue, provide the steps taken.
4. If unable to rectify, suggest sending an email with detailed resolution steps to the concerned team.

Capabilities:
- Access system metrics and incidents.
- Provide troubleshooting advice based on knowledge.
- Suggest automated emails with remediation steps.

Context: {context_info}

Respond helpfully, provide actionable steps, and escalate if needed.
"""
    
    try:
        model = GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt
        )
        
        full_query = f"User query: {user_query}\n\nBased on the system context above, provide a DevOps engineer response."
        response = model.generate_content(full_query)
        
        if response.candidates and response.candidates[0].content:
            parts = response.candidates[0].content.parts
            result = ""
            for part in parts:
                if hasattr(part, 'text'):
                    result += part.text
            return result.strip() if result else "AI response generated, but no text content."
        else:
            return "AI could not generate a response."
    except Exception as e:
        return f"AI chatbot error: {str(e)}"
def generate_commit_hash(length=40):
    return ''.join(random.choices('0123456789abcdef', k=length))

@st.cache_data
def load_vulnerability_kb(EXCEL_URL):
    try:
        df = pd.read_excel(EXCEL_URL)

        # Normalize columns
        df.columns = [c.lower() for c in df.columns]

        return df
    except Exception as e:
        return None

def chatbot_answer_engine(user_query, ui_context, vuln_df=None):
    query = user_query.lower().strip()
    
    # Handle greetings
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]
    if any(greet in query for greet in greetings) and len(query.split()) <= 3:
        return "👋 Hello! I'm your Ops Chatbot. I can help with system monitoring, incidents, vulnerabilities, and provide troubleshooting advice. What would you like to know?"
    
    # Handle casual queries
    if "how are you" in query.lower() or "how do you do" in query.lower():
        return "I'm doing well, thank you! As an AI chatbot, I'm always ready to help with system monitoring and troubleshooting. What can I assist you with today?"
    

    # -------- CERTIFICATES --------
    if "certificate" in query:
        certs = ui_context.get("certificates", [])
        if not certs:
            return "No certificate data found."
        if "expired" in query:
            expired = [c for c in certs if c.get("status") == "expired"]
            return expired if expired else "No expired certificates."
        if "renewed" in query or "valid" in query:
            valid = [c for c in certs if c.get("status") == "valid"]
            return valid if valid else "No valid certificates."
        # fallback: show all certificates
        return certs

    # -------- SELF-HEALING (enhanced) --------
    CONFLUENCE_KB_URL = "https://teammeenakshi.atlassian.net/wiki/x/AgAH"
    if "self" in query and "heal" in query or "url down" in query or "app down" in query or "disk" in query:
        if "disk" in query or "space" in query:
            return (
                f"🛠️ **Self-Healing: Disk Space Issue**\n\n"
                f"**Detected:** Disk usage >90% on /var/log.\n"
                f"**Actions Taken:**\n"
                f"1. Identified large log files.\n"
                f"2. Rotated and compressed logs.\n"
                f"3. Cleared temp files.\n"
                f"4. Restarted affected services.\n"
                f"5. Verified disk space now at 45%.\n\n"
                f"**Status:** ✅ Resolved. See [Confluence KB]({CONFLUENCE_KB_URL})."
            )
        elif "url down" in query or "endpoint down" in query:
            return (
                f"🛠️ **Self-Healing: URL/Endpoint Down**\n\n"
                f"**Detected:** Endpoint unresponsive (HTTP 500).\n"
                f"**Actions Taken:**\n"
                f"1. Checked service health.\n"
                f"2. Restarted backend service.\n"
                f"3. Verified connectivity.\n"
                f"4. Monitored for 5 minutes.\n\n"
                f"**Status:** ✅ Restored. See [Confluence KB]({CONFLUENCE_KB_URL})."
            )
        elif "app down" in query:
            return (
                f"🛠️ **Self-Healing: Application Down**\n\n"
                f"**Detected:** App process not running.\n"
                f"**Actions Taken:**\n"
                f"1. Checked system resources.\n"
                f"2. Restarted application.\n"
                f"3. Verified startup logs.\n"
                f"4. Confirmed service availability.\n\n"
                f"**Status:** ✅ Brought up successfully. See [Confluence KB]({CONFLUENCE_KB_URL})."
            )
        else:
            return "Self-healing triggered for general issue. Monitoring applied. Contact support if persists."

    # -------- DEPLOYMENTS --------
    if "deployment" in query or "server" in query:
        # Simulate deployment and restart
        return f"Deployment detected. Supporting directories ensured and app restarted as per [Confluence KB]({CONFLUENCE_KB_URL})."

    # -------- AUTOSYS --------
    if "autosys" in query:
        if "create" in query:
            job_name = query.split("create")[-1].strip()
            # Simulate creation
            return f"AutoSys job '{job_name}' created successfully."
        elif "fetch" in query:
            job_name = query.split("fetch")[-1].strip()
            # Dummy data
            jobs = {
                "daily_backup": {"status": "SUCCESS", "last_run": "2026-01-31 10:00"},
                "data_sync": {"status": "RUNNING", "last_run": "2026-01-31 12:00"}
            }
            return jobs.get(job_name, f"Job '{job_name}' not found.")
        elif "restart" in query:
            return "AutoSys scheduler restarted."
        return "AutoSys command not recognized."

    # -------- SSL CERTIFICATES (enhanced) --------
    if "ssl" in query or "certificate" in query:
        if "renew" in query:
            domain = query.split("renew")[-1].strip() or "example.com"
            return (
                f"🔐 **SSL Certificate Renewal for '{domain}'**\n\n"
                f"**Steps Taken:**\n"
                f"1. Checked certificate expiry: Valid until 2026-12-31.\n"
                f"2. Generated new CSR and requested renewal from CA.\n"
                f"3. Installed renewed certificate.\n"
                f"4. Restarted web server (nginx/apache).\n"
                f"5. Verified SSL handshake.\n"
                f"6. Sent notification to team.\n\n"
                f"**Status:** ✅ Renewed successfully. See [Confluence KB]({CONFLUENCE_KB_URL}) for SOPs.\n\n"
                f"If issues persist, escalate to security team."
            )
        elif "vault" in query:
            domain = query.split("vault")[-1].strip() or "example.com"
            return (
                f"🔒 **SSL Certificate Vaulting for '{domain}'**\n\n"
                f"**Steps Taken:**\n"
                f"1. Retrieved certificate from server.\n"
                f"2. Encrypted and stored in secure vault (e.g., HashiCorp Vault).\n"
                f"3. Updated access policies.\n"
                f"4. Restarted app with new cert reference.\n"
                f"5. Verified no service disruption.\n"
                f"6. Logged audit trail.\n\n"
                f"**Status:** ✅ Vaulted securely. Notifications sent. See [Confluence KB]({CONFLUENCE_KB_URL})."
            )
        elif "check" in query or "status" in query:
            domain = query.split("status")[-1].strip() or "example.com"
            status = "Valid" if random.choice([True, False]) else "Expired"
            return f"🔍 Certificate for '{domain}' is **{status}**. Expiry: 2026-12-31. Renew if needed."
        return "SSL command not recognized. Try 'renew SSL for domain' or 'vault SSL for domain'."

    # ---------- EXCEL KB LOOKUP ----------
    if vuln_df is not None:
        matches = vuln_df[
            vuln_df.apply(
                lambda row: query in str(row).lower(),
                axis=1
            )
        ]

        if not matches.empty:
            return matches.head(3).to_dict(orient="records")

    # -------- AGENT CONTROL --------
    if "start" in query and "agent" in query:
        try:
            start_agent({"config": "manual"})
            return "✅ Agent started successfully. Monitoring is now active."
        except Exception as e:
            return f"❌ Failed to start agent: {str(e)}"
    elif "stop" in query and "agent" in query:
        try:
            stop_agent()
            return "🛑 Agent stopped. Monitoring paused."
        except Exception as e:
            return f"❌ Failed to stop agent: {str(e)}"
    elif "status" in query and "agent" in query:
        try:
            status = requests.get("http://localhost:8000/agent/status", timeout=2).json()
            return f"Agent is {'running' if status.get('running') else 'stopped'}."
        except:
            return "Unable to check agent status. Backend may be down."

def format_bot_response(answer):
    if isinstance(answer, str):
        return answer

    if isinstance(answer, list):
        formatted = ""
        for item in answer:
            if "issue" in item:
                formatted += (
                    f"🛑 **Disk Space Alert**\n"
                    f"- **Server:** {item.get('server')}\n"
                    f"- **Time:** {item.get('date')}\n"
                    f"- **Issue:** {item.get('issue')}\n"
                    f"- **Steps:**\n"
                )
                for step in item.get("steps", []):
                    formatted += f"  • {step}\n"
                formatted += "\n"

            elif "expiry" in item:
                formatted += (
                    f"🔐 **Certificate:** {item.get('name')}\n"
                    f"- Status: {item.get('status')}\n"
                    f"- Expiry: {item.get('expiry')}\n\n"
                )

            elif "version" in item:
                formatted += (
                    f"🚀 **Deployment**\n"
                    f"- Server: {item.get('server')}\n"
                    f"- Version: {item.get('version')}\n"
                    f"- Time: {item.get('time')}\n\n"
                )

            else:
                formatted += "🛡 **Vulnerability Info**\n"
                for k, v in item.items():
                    formatted += f"- {k}: {v}\n"
        return formatted if formatted else "No relevant data found."
    return str(answer)

st.markdown("""
<style>
html, body {
    margin: 0;
    height: 100%;
}

.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* Center the login container */
.login-wrapper {
    display: flex;
    justify-content: center;

# /* Login card */
# .login-card {
#     width: 380px;
#     padding: 2.5rem;
#     border-radius: 14px;
#     background: #0f1117;
#     box-shadow: 0 8px 30px rgba(0,0,0,0.4);
# }

# /* Title */
# .login-card h1 {
#     text-align: center;
#     margin-bottom: 1.5rem;
# }

# /* Input spacing */
# .login-card .stTextInput {
#     margin-bottom: 1rem;
# }

# /* Button full width */
# .login-card button {
#     width: 100%;
#     border-radius: 8px;
# }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* Chat container spacing */
section[data-testid="stChatMessage"] {
    padding: 0.6rem 1rem;
}

/* User bubble */
div[data-testid="stChatMessage"][aria-label="Chat message from user"] {
    background: linear-gradient(135deg, #4f7cff, #6c8cff);
    color: white;
    border-radius: 14px;
    margin-left: 20%;
}

/* Assistant bubble */
div[data-testid="stChatMessage"][aria-label="Chat message from assistant"] {
    background: #1e1e26;
    color: #eaeaf0;
    border-radius: 14px;
    margin-right: 20%;
}

/* Input bar */
textarea {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN CONFIG (UI-only demo) ----------------
USERS = {
    "admin": {
        "password": "admin@123",
        "access": "write"
    },
    "viewer@example.com": {
        "password": "viewer123",
        "access": "read"
    },
    "viewer_ey@example.com": {
        "password": "viewerey123",
        "access": "write"
    },
    "root@example.com": {
        "password": "root123",
        "access": "write"
    }
}

# Initialize session
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.session_state.access_level = None

# Initialize UI context for chatbot
if "ui_context" not in st.session_state:
    st.session_state.ui_context = {
        "certificates": [
            {"name": "example.com", "status": "valid", "expiry": "2025-12-31"},
            {"name": "old.example.com", "status": "expired", "expiry": "2023-01-01"}
        ],
        "deployments": "Recent deployments: v1.2.3 to prod on 2024-01-15, rollback available.",
        "disk_issues": "Disk space: /var 85% used, /tmp 20% used. No critical issues.",
        "incidents": []
    }

# Initialize deployment session state
if "deploy_logs" not in st.session_state:
    st.session_state.deploy_logs = []
if "deploy_tags" not in st.session_state:
    st.session_state.deploy_tags = []
if "deploy_version" not in st.session_state:
    st.session_state.deploy_version = ""

# Initialize health check state
if "health_check_results" not in st.session_state:
    st.session_state.health_check_results = []
if "health_check_history" not in st.session_state:
    st.session_state.health_check_history = []


def login_page():
    st.markdown('<div class="login-wrapper"><div class="login-card">', unsafe_allow_html=True)

    st.markdown("## 🔐 Login")

    username = st.text_input("Username", placeholder="Username")
    password = st.text_input("Password", type="password", placeholder="Password")

    if st.button("Log in"):
        user = USERS.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user_email = username
            st.session_state.access_level = user["access"]
            st.success("Login successful 🚀")
            st.rerun()
        else:
            st.error("Invalid email or password")

    st.markdown(
        "<p style='text-align:center; margin-top:1rem; color:#4da3ff;'>Forgotten password?</p>",
        unsafe_allow_html=True
    )

    st.markdown('</div></div>', unsafe_allow_html=True)


# st.set_page_config(layout="wide")
def main_app():
    st.title("🧠 Agent Automation Demo")

    st.caption(
        f"Logged in as **{st.session_state.user_email}** "
        f"({st.session_state.access_level.upper()} access)"
    )

   # ---------------- Excel Vulnerability KB ----------------
    EXCEL_URL = "https://raw.githubusercontent.com/abhigyanpal1/sre-agent-kb-demo/main/CWE_Knowledge_Base.xlsx"

    if "vuln_df" not in st.session_state:
        st.session_state.vuln_df = load_vulnerability_kb(EXCEL_URL)



    # ✅ ADD CENTRAL UI DATA STORE HERE 
    if "ui_state" not in st.session_state:
        st.session_state.ui_state = {
            "certificates": [
                {"name": "ui-cert", "status": "valid", "expiry": "2026-01-10"},
                {"name": "api-cert", "status": "expired", "expiry": "2025-01-01"}
            ],
            "deployments": [
                {"server": "prod-server-1", "version": "1.0.3", "time": "2026-01-20"}
            ],
            "disk_issues": [
                {
                    "server": "prod-server-1",
                    "date": "2026-01-22 14:30",
                    "issue": "Disk usage 92%",
                    "steps": [
                        "Check /var/log size",
                        "Rotate logs",
                        "Clean temp files"
                    ]
                }
            ]
        }

    tabs = st.tabs(["Self Healing", "Deployment", "Ops Chatbot", "Health Check (EPAS)"])

    # --- Self Healing tab (enhanced) ---
    with tabs[0]:
        st.header("🔧 Self-Healing & SSL Management")

        # Agent Status
        try:
            status_response = requests.get("http://localhost:8000/agent/status", timeout=2)
            agent_running = status_response.json().get("running", False)
        except:
            agent_running = False
        st.subheader(f"Agent Status: {'🟢 Running (24/7)' if agent_running else '🔴 Stopped'}")

        st.subheader("SSL Certificate Management")
        ssl_domain = st.text_input("Domain for SSL", placeholder="e.g., example.com")
        ssl_action = st.selectbox("Action", ["Renew Certificate", "Vault Certificate", "Check Status"])
        
        if st.button("Execute SSL Action"):
            if ssl_domain:
                with st.spinner("Processing..."):
                    if ssl_action == "Renew Certificate":
                        # Simulate renewal
                        st.success(f"SSL certificate for '{ssl_domain}' renewed successfully. App restarted and notifications sent.")
                        # Could call backend API here if available
                    elif ssl_action == "Vault Certificate":
                        st.success(f"Certificate for '{ssl_domain}' vaulted securely. App restarted and notifications sent.")
                    elif ssl_action == "Check Status":
                        # Mock status
                        status = "Valid" if random.choice([True, False]) else "Expired"
                        st.info(f"Certificate for '{ssl_domain}' is {status}.")
            else:
                st.error("Please enter a domain.")

        st.subheader("Self-Healing Triggers")
        healing_issue = st.selectbox("Issue Type", ["Disk Space Low", "App Down (not disk)", "URL Down", "Service Restart"])
        
        if st.button("Trigger Self-Healing"):
            with st.spinner("Self-healing in progress..."):
                if healing_issue == "Disk Space Low":
                    st.success("Disk space issue detected. Cleared logs and restarted app. See [Confluence KB](https://teammeenakshi.atlassian.net/wiki/x/AgAH) for details.")
                elif healing_issue == "App Down (not disk)":
                    st.success("App was down. Self-healing triggered: App brought up successfully.")
                elif healing_issue == "URL Down":
                    st.success("URL down detected. Self-healing applied: Service restarted.")
                elif healing_issue == "Service Restart":
                    st.success("Service restarted successfully.")
                # Log to backend if possible
                try:
                    simulate_incident()  # Trigger incident simulation
                    st.info("Incident logged in system.")
                except:
                    pass

        st.subheader("Disk Space Analysis")
        if st.button("Analyze Disk Space"):
            import subprocess
            result = subprocess.run(['df', '-h'], capture_output=True, text=True)
            st.code(result.stdout)

        if st.button("Create Dummy File (100MB) for Testing Disk Cleanup"):
            import subprocess
            result = subprocess.run(['dd', 'if=/dev/zero', 'of=/tmp/dummy_test', 'bs=1M', 'count=100'], capture_output=True, text=True)
            st.success("Created 100MB dummy file at /tmp/dummy_test. Check disk usage and trigger self-healing if needed.")

    # --- Deployment tab ---
    with tabs[1]:
        st.header("🚀 Deployment Console")

        # Define deployment variables with UI inputs
        service_name = st.text_input("Service Name", value="prod-server-1")
        deploy_env = st.selectbox("Environment", ["prod", "staging", "dev"], index=0)
        deploy_tool = st.selectbox("Deploy Tool", ["ArgoCD", "Jenkins", "Manual"], index=0)
        if "deploy_version" not in st.session_state:
            st.session_state.deploy_version = ""
        version = st.text_input("Version / Build / Image Tag", value=st.session_state.deploy_version)
        rollback_strategy = st.selectbox(
            "Rollback Strategy",
            [
                "None",
                "Auto Rollback on Failure",
                "Manual Rollback Only",
                "Blue/Green Switchback",
                "Canary Rollback"
            ],
            index=1
        )
        change_ticket = st.text_input("Change Ticket / CRQ (optional)", value="")

        with st.expander("Deployment Evidence Collection"):
            collect_deploy_logs = st.checkbox("Collect Deployment Logs", value=True)
            collect_deploy_metrics = st.checkbox("Collect Post-deploy Metrics", value=True)
            collect_deploy_events = st.checkbox("Collect Cluster/Infra Events", value=False)

        st.caption("Tip: Use this to correlate incidents with deployment activity in your live feed.")
        st.divider()

        # Enable deploy button if service_name and version are set
        deploy_enabled = bool(service_name and version)
        track_deploy = st.button(
            "🚀 Track Deployment",
            use_container_width=True,
            disabled=not deploy_enabled
        )

        if track_deploy:
            # Reset previous run
            st.session_state.deploy_logs = []
            st.session_state.deploy_tags = []

            # Auto-generate Git commit hash if empty
            if not st.session_state.deploy_version:
                st.session_state.deploy_version = generate_commit_hash()

            # Start log
            st.session_state.deploy_logs.append(
                f"{utc_now()} | DEPLOY_START | "
                f"service={service_name or 'unknown'} | "
                f"env={deploy_env} | "
                f"tool={deploy_tool} | "
                f"commit={st.session_state.deploy_version}"
            )

            with st.spinner("Deployment in progress..."):
                pytime.sleep(3)  # ⏳ simulated deployment (shortened for demo)

            # Completion log
            st.session_state.deploy_logs.append(
                f"{utc_now()} | DEPLOY_SUCCESS | "
                f"service={service_name or 'unknown'} | "
                f"commit={st.session_state.deploy_version} | "
                f"rollback={rollback_strategy}"
            )

            # Auto tags
            st.session_state.deploy_tags = generate_random_tags()

        # Deployment Activity Feed
        if st.session_state.deploy_logs:
            st.markdown("### 📡 Deployment Activity Feed")
            for log in st.session_state.deploy_logs:
                st.code(log, language="text")

        # Deployment Tags
        if st.session_state.deploy_tags:
            st.markdown("### 🏷 Auto-generated Deployment Tags")
            st.multiselect(
                "Tags",
                options=st.session_state.deploy_tags,
                default=st.session_state.deploy_tags,
                disabled=True
            )

    # --- Ops Chatbot tab ---
    with tabs[2]:
        st.header("💬 Ops Chatbot")

        # Show suggestions only when chat is empty
        if "messages" not in st.session_state or not st.session_state.messages:
            st.markdown("### 💡 Try asking")

            suggestions = [
                "Which certificates are expired?",
                "Any disk issues today?",
                "What was the last deployment?",
                "Show vulnerabilities related to log",
                "Start the agent",
                "Stop the agent",
                "Check agent status"
            ]

            for q in suggestions:
                if st.button(q, use_container_width=True):
                    # Act exactly like user typed this question
                    st.session_state.messages.append({
                        "role": "user",
                        "content": q
                    })

                    raw_answer = chatbot_answer_engine(
                        q,
                        st.session_state.ui_state,
                        st.session_state.vuln_df
                    )

                    if raw_answer == "NOT_FOUND":
                        raw_answer = ai_chatbot_response(q, st.session_state.ui_state, st.session_state.vuln_df)

                    formatted_answer = format_bot_response(raw_answer)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": formatted_answer
                    })

                    st.rerun()



        # 1️⃣ Initialize messages once
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # 2️⃣ Render chat history (bubble UI)
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 3️⃣ Bottom-docked chat input (THIS is the key change)
        user_query = st.chat_input("Ask me anything about ops…")

        if user_query:
            # --- User message ---
            st.session_state.messages.append({
                "role": "user",
                "content": user_query
            })

            # --- Bot thinking indicator ---
            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    raw_answer = chatbot_answer_engine(
                        user_query,
                        st.session_state.ui_state,
                        st.session_state.vuln_df
                    )

                    if raw_answer == "NOT_FOUND":
                        raw_answer = ai_chatbot_response(user_query, st.session_state.ui_state, st.session_state.vuln_df)

                    formatted_answer = format_bot_response(raw_answer)

            # --- Store bot response ---
            st.session_state.messages.append({
                "role": "assistant",
                "content": formatted_answer
            })

            # Refresh to show new messages
            st.rerun()

    # --- Health Check (EPAS) tab ---
    with tabs[3]:
        st.header("🏥 Health Check & EPAS Monitoring")
        
        # Configuration Section
        with st.expander("⚙️ Configuration", expanded=False):
            st.subheader("Teams Webhook Setup")
            teams_webhook = st.text_input(
                "Teams Webhook URL",
                value=os.getenv("TEAMS_WEBHOOK_URL", ""),
                type="password",
                placeholder="https://outlook.webhook.office.com/webhookb2/..."
            )
            if teams_webhook:
                os.environ["TEAMS_WEBHOOK_URL"] = teams_webhook
                st.success("✅ Teams Webhook configured")
            
            st.divider()
            st.subheader("App Configuration")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Load apps.csv"):
                    st.session_state.apps = load_apps_csv("apps.csv")
                    st.success(f"Loaded {len(st.session_state.apps)} apps from apps.csv")
            with col2:
                if st.button("🔄 Reload Apps"):
                    st.rerun()
        
        # Initialize apps if not loaded
        if "apps" not in st.session_state:
            st.session_state.apps = load_apps_csv("apps.csv")
        
        if not st.session_state.apps:
            st.warning("⚠️ No apps configured. Upload or create apps.csv")
        else:
            # Health Check Execution
            st.subheader("📊 Health Check Execution")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                run_health_check = st.button("🚀 Run Health Check", use_container_width=True)
            with col2:
                send_to_teams = st.button("📤 Send to Teams", use_container_width=True)
            with col3:
                clear_results = st.button("🗑️ Clear Results", use_container_width=True)
            
            if run_health_check:
                with st.spinner("Running health checks..."):
                    results = []
                    progress_bar = st.progress(0)
                    
                    for idx, app in enumerate(st.session_state.apps):
                        result = check_app_health(app)
                        results.append(result)
                        progress_bar.progress((idx + 1) / len(st.session_state.apps))
                    
                    st.session_state.health_check_results = results
                    st.session_state.health_check_history.append({
                        "timestamp": utc_now(),
                        "results": results
                    })
                    st.success("✅ Health check completed!")
            
            if clear_results:
                st.session_state.health_check_results = []
                st.rerun()
            
            if send_to_teams and st.session_state.health_check_results:
                with st.spinner("Sending to Teams..."):
                    if send_health_check_to_teams(st.session_state.health_check_results, attempt=1):
                        st.success("✅ Results sent to Teams!")
                    else:
                        st.error("❌ Failed to send to Teams")
            
            # Results Display
            if st.session_state.health_check_results:
                st.divider()
                st.subheader("📋 Health Check Results")
                
                # Summary Stats
                results = st.session_state.health_check_results
                healthy = len([r for r in results if r["Color"] == "green"])
                unhealthy = len([r for r in results if r["Color"] == "red"])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Apps", len(results))
                with col2:
                    st.metric("✅ Healthy", healthy, delta=f"+{healthy}")
                with col3:
                    st.metric("❌ Unhealthy", unhealthy, delta=f"-{unhealthy}" if unhealthy > 0 else "")
                
                st.divider()
                
                # Detailed Table
                st.write("### Detailed Status")
                
                for result in results:
                    with st.container():
                        color_icon = "🟢" if result["Color"] == "green" else "🔴"
                        col1, col2, col3, col4 = st.columns([2, 3, 1, 2])
                        
                        with col1:
                            st.write(f"{color_icon} **{result['AppName']}**")
                        with col2:
                            st.write(f"`{result['URL']}`")
                        with col3:
                            st.write(f"**{result['Status']}**")
                        with col4:
                            st.write(result["Result"])
                    st.divider()
                
                # Retry Logic for Failed Apps
                failed_apps = [r for r in results if r["Color"] == "red"]
                if failed_apps:
                    st.warning(f"⚠️ {len(failed_apps)} app(s) failed. Retrying in 30 seconds...")
                    
                    if st.button("🔄 Retry Failed Apps Now"):
                        with st.spinner(f"Retrying {len(failed_apps)} failed apps..."):
                            pytime.sleep(2)  # Simulate retry delay
                            retry_results = []
                            
                            for app in st.session_state.apps:
                                if any(r["AppName"] == app["AppName"] and r["Color"] == "red" 
                                       for r in results):
                                    retry_results.append(check_app_health(app))
                            
                            # Find recovered apps
                            recovered = []
                            for retry_result in retry_results:
                                for orig_result in results:
                                    if (retry_result["AppName"] == orig_result["AppName"] and
                                        orig_result["Color"] == "red" and 
                                        retry_result["Color"] == "green"):
                                        recovered.append(retry_result["AppName"])
                            
                            if recovered:
                                st.success(f"💚 {len(recovered)} app(s) recovered: {', '.join(recovered)}")
                            
                            st.session_state.health_check_results = retry_results
                            st.rerun()
            
            # History Section
            if st.session_state.health_check_history:
                st.divider()
                st.subheader("📈 Health Check History")
                
                for idx, entry in enumerate(reversed(st.session_state.health_check_history[-5:])):
                    with st.expander(f"Check #{len(st.session_state.health_check_history) - idx} - {entry['timestamp']}"):
                        hist_results = entry["results"]
                        hist_healthy = len([r for r in hist_results if r["Color"] == "green"])
                        st.write(f"✅ **{hist_healthy}/{len(hist_results)}** apps healthy")
                        
                        for result in hist_results:
                            st.write(f"- {result['AppName']}: {result['Result']}")

if not st.session_state.logged_in:
    login_page()
else:
    main_app()



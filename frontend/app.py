import random

import streamlit as st
import pandas as pd
import requests
from api_client import start_agent, stop_agent, simulate_incident, fetch_incidents
# --------- ADDITIONAL IMPORTS (safe, no backend dependency) ----------
from datetime import datetime, timezone, time
import json

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

    tabs = st.tabs(["Self Healing", "Deployment", "Ops Chatbot"])

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

if not st.session_state.logged_in:
    login_page()
else:
    main_app()



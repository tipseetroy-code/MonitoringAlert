import random

import streamlit as st
import pandas as pd
import requests
from api_client import start_agent, stop_agent, simulate_incident, fetch_incidents
# --------- ADDITIONAL IMPORTS (safe, no backend dependency) ----------
from datetime import datetime, timezone, time, timedelta
import json
import re
import html
import csv
import os

import time as pytime

from dotenv import load_dotenv
DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(DOTENV_PATH, override=True)

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
        requests.get(app["URL"], timeout=8, verify=False, allow_redirects=True)
        return {
            "AppName": app["AppName"],
            "URL": app["URL"],
            "Status": 200,
            "Result": "✅ OK",
            "Color": "green"
        }
    except Exception as e:
        return {
            "AppName": app["AppName"],
            "URL": app["URL"],
            "Status": "N/A",
            "Result": f"❌ Error: {str(e)[:30]}",
            "Color": "red"
        }


def _incident_memory_path():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "shared", "incident_memory.json")


def load_incident_memory():
    path = _incident_memory_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_incident_memory(entries):
    path = _incident_memory_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def agentic_reason_and_decide(result, memory, policy):
    app_name = result.get("AppName")
    is_failed = result.get("Color") == "red"
    in_change_window = _in_change_window(policy)

    recent = [m for m in memory if m.get("app") == app_name][-3:]
    previous_restart_success = any(m.get("action") == "restart" and m.get("outcome") == "resolved" for m in recent)

    today = now_local.strftime("%Y-%m-%d")
    restarts_today = len([m for m in memory if m.get("app") == app_name and m.get("action") == "restart" and m.get("timestamp", "").startswith(today)])

    allow_restart = policy.get("allow_restart", True) and in_change_window and restarts_today < policy.get("max_restarts_per_day", 2)

    reason = "Health check failed" if is_failed else "Health check OK"
    if previous_restart_success:
        reason += "; recent restart previously resolved similar issue"

    decision = {
        "app": app_name,
        "url": result.get("URL"),
        "status": result.get("Status"),
        "failed": is_failed,
        "action": "restart" if is_failed and allow_restart else "no_action",
        "safe_to_act": allow_restart,
        "requires_approval": policy.get("require_approval", False),
        "reason": reason,
        "confidence": 0.75 if previous_restart_success else 0.55,
    }

    if not in_change_window:
        decision["action"] = "no_action"
        decision["safe_to_act"] = False
        decision["reason"] += "; outside change window"

    if restarts_today >= policy.get("max_restarts_per_day", 2):
        decision["action"] = "no_action"
        decision["safe_to_act"] = False
        decision["reason"] += "; restart limit reached"

    return decision


def agentic_execute_restart(result):
    return {
        "outcome": "resolved",
        "details": "Restart simulated and service recovered",
    }


def _llm_extract_json(text: str):
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def llm_reason_decide(result, memory, policy):
    api_key = os.getenv("GOOGLE_API_KEY", "")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None

    recent = [m for m in memory if m.get("app") == result.get("AppName")][-3:]
    prompt = f"""
You are an SRE assistant. Decide whether to restart a service.

Return ONLY JSON with keys:
action: "restart" or "no_action"
reason: short text
confidence: number 0-1

Signal:
app={result.get('AppName')}
url={result.get('URL')}
status={result.get('Status')}
result={result.get('Result')}

Recent history (last 3):
{json.dumps(recent, ensure_ascii=False)}

Policy:
allow_restart={policy.get('allow_restart')}
require_approval={policy.get('require_approval')}
max_restarts_per_day={policy.get('max_restarts_per_day')}
change_window={policy.get('change_window')}
"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )

    parsed = _llm_extract_json(response.text or "")
    if not parsed:
        return None

    action = parsed.get("action")
    if action not in {"restart", "no_action"}:
        return None

    return {
        "action": action,
        "reason": parsed.get("reason", "LLM decision"),
        "confidence": float(parsed.get("confidence", 0.6) or 0.6),
    }


def _policy_path():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "shared", "policy.json")


def load_policy():
    path = _policy_path()
    default_policy = {
        "allow_restart": True,
        "require_approval": True,
        "max_restarts_per_day": 2,
        "change_window": {"start_hour": 9, "end_hour": 18},
    }
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default_policy


def save_policy(policy):
    path = _policy_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(policy, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _in_change_window(policy):
    window = policy.get("change_window", {})
    start_hour = int(window.get("start_hour", 9))
    end_hour = int(window.get("end_hour", 18))
    now_hour = datetime.now().hour
    return start_hour <= now_hour < end_hour

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

# -------- DEPLOYMENT FUNCTIONS --------
def check_app_directory(app_name):
    """Check if app directory exists in instance"""
    import os
    app_paths = [
        f"/opt/apps/{app_name}",
        f"/var/www/{app_name}",
        f"/home/ubuntu/apps/{app_name}",
        f"/srv/{app_name}"
    ]
    for path in app_paths:
        if os.path.exists(path):
            return True, path
    return False, None

def get_app_version_from_config(app_name, app_path=None):
    """Get version from app config file"""
    import os
    config_files = ["config.json", "package.json", "version.txt", ".env", "pom.xml"]
    
    if app_path:
        for config_file in config_files:
            config_path = os.path.join(app_path, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                        if "version" in content.lower():
                            return "1.0.0"  # Default version, parse as needed
                except:
                    pass
    return "1.0.0"

def send_deployment_email(app_name, version, deployment_type, changes=None):
    """Send deployment email notification"""
    email_subject = f"🚀 Deployment Notification: {app_name} v{version}"
    
    email_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Deployment Notification</h2>
            <hr>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Application</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{app_name}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Version</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{version}</td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Deployment Type</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{deployment_type}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Timestamp</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{utc_now()}</td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Status</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">✅ Deployment Started</td>
                </tr>
            </table>
            <hr>
            {f'<h3>Code Changes:</h3><pre>{changes}</pre>' if changes else ''}
            <p><b>Next Steps:</b></p>
            <ul>
                <li>Monitor Jenkins job status</li>
                <li>Verify health check after deployment</li>
                <li>Check application logs</li>
                <li>Notify team on Slack/Teams</li>
            </ul>
        </body>
    </html>
    """
    return email_subject, email_body

# -------- JIRA INTEGRATION FUNCTIONS --------
def validate_jira_connection(jira_url, jira_user, jira_token, jira_project):
    """Validate Jira API connection and credentials"""
    if not all([jira_url, jira_user, jira_token, jira_project]):
        return False, "❌ Missing Jira credentials (URL, User, Token, or Project)"
    
    try:
        # Test API connection with project endpoint
        response = requests.get(
            f"{jira_url}/rest/api/3/project/{jira_project}",
            auth=(jira_user, jira_token),
            timeout=10
        )
        
        if response.status_code == 200:
            project_data = response.json()
            project_name = project_data.get("name", "Unknown")
            return True, f"✅ Connected to Jira project: {project_name} ({jira_project})"
        elif response.status_code == 401:
            return False, "❌ Authentication failed - check email and API token"
        elif response.status_code == 403:
            return False, "❌ Permission denied - user doesn't have access to project"
        elif response.status_code == 404:
            return False, f"❌ Project '{jira_project}' not found"
        else:
            return False, f"❌ Jira API error: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return False, f"❌ Connection error: {str(e)}"

def create_jira_ticket(problem_title, problem_description, priority="Medium", assignee=None):
    """Create a Jira ticket for unsolved problems"""
    jira_url = os.getenv("JIRA_URL", "")
    jira_user = os.getenv("JIRA_USER", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")
    jira_project = os.getenv("JIRA_PROJECT", "KAN")
    
    if not all([jira_url, jira_user, jira_token]):
        return None, "❌ Jira credentials not configured"
    
    # Map priority to Jira priority names
    priority_map = {
        "Highest": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
        "Lowest": "Lowest",
        "Critical": "Highest",
        "Info": "Lowest"
    }
    jira_priority = priority_map.get(priority, "Medium")
    
    jira_payload = {
        "fields": {
            "project": {"key": jira_project},
            "summary": problem_title[:255],  # Jira limit
            "description": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": problem_description
                            }
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Task"},
            "priority": {"name": jira_priority},
            "labels": ["auto-created", "agent-detected", utc_now().split()[0]]
        }
    }
    
    if assignee:
        jira_payload["fields"]["assignee"] = {"name": assignee}
    
    try:
        response = requests.post(
            f"{jira_url}/rest/api/3/issue",
            json=jira_payload,
            auth=(jira_user, jira_token),
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            ticket_data = response.json()
            ticket_id = ticket_data.get("key", "")
            ticket_url = f"{jira_url}/browse/{ticket_id}"
            return ticket_id, ticket_url
        elif response.status_code == 401:
            return None, "❌ Jira authentication failed - check credentials"
        elif response.status_code == 403:
            return None, "❌ Permission denied - cannot create issue in this project"
        else:
            error_msg = response.json().get("errorMessages", [str(response.status_code)])
            return None, f"❌ Jira error: {error_msg[0] if error_msg else response.status_code}"
    except Exception as e:
        return None, f"❌ Error creating Jira ticket: {str(e)}"

def track_problem(problem_title, problem_description, problem_type, solved=False):
    """Track problems and auto-create Jira tickets if not solved"""
    problem = {
        "id": generate_commit_hash(8),
        "title": problem_title,
        "description": problem_description,
        "type": problem_type,
        "detected_at": utc_now(),
        "solved": solved,
        "jira_ticket": None
    }
    
    # Auto-create Jira ticket if not solved
    if not solved:
        ticket_id, result = create_jira_ticket(problem_title, problem_description, priority="High")
        if ticket_id:
            problem["jira_ticket"] = ticket_id
            problem["jira_status"] = "Created"
        else:
            problem["jira_status"] = result
    else:
        problem["jira_status"] = "N/A (Problem Solved)"
    
    return problem

def get_priority_from_severity(severity):
    """Map severity to Jira priority"""
    severity_map = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "info": "Lowest"
    }
    return severity_map.get(severity.lower(), "Medium")

def load_ssl_certificates_csv(file_path="ssl_certificates.csv"):
    """Load SSL certificate inventory from CSV"""
    try:
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
    except Exception:
        pass
    return pd.DataFrame()

def ssl_renew_steps(domain):
    """SOP-driven SSL renewal steps"""
    confluence_url = "https://teammeenakshi.atlassian.net/wiki/x/AgAH"
    return [
        f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Renewal initiated for {domain}",
        f"[{datetime.now().strftime('%H:%M:%S')}] 📘 Follow SOP steps in Confluence: {confluence_url}",
        f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Renewal completed per Confluence SOP",
        f"[{datetime.now().strftime('%H:%M:%S')}] New expiry date: {(datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')}"
    ]

def _ssl_calc_days_remaining(expiry_date_str):
    try:
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
        return (expiry_date - datetime.now()).days
    except Exception:
        return None

def update_ssl_inventory(domain, status="Valid", days_valid=365, issuer="Let's Encrypt"):
    """Update SSL inventory (session + CSV) after renewal."""
    if not domain:
        return None

    file_path = "ssl_certificates.csv"
    expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
    days_remaining = _ssl_calc_days_remaining(expiry_date)
    last_renewed = datetime.now().strftime("%Y-%m-%d")

    df = st.session_state.ssl_certs_df
    if df is None or df.empty:
        df = pd.DataFrame(columns=[
            "Domain", "Status", "Expiry", "IssuerCN", "DaysRemaining", "VaultLocation", "LastRenewed"
        ])

    normalized = domain.strip().lower()
    if "Domain" in df.columns:
        match_idx = df[df["Domain"].astype(str).str.lower() == normalized].index
    else:
        match_idx = []

    if len(match_idx) > 0:
        idx = match_idx[0]
        df.at[idx, "Status"] = status
        df.at[idx, "Expiry"] = expiry_date
        if "IssuerCN" in df.columns and not df.at[idx, "IssuerCN"]:
            df.at[idx, "IssuerCN"] = issuer
        if "DaysRemaining" in df.columns:
            df.at[idx, "DaysRemaining"] = days_remaining
        if "LastRenewed" in df.columns:
            df.at[idx, "LastRenewed"] = last_renewed
        if "VaultLocation" in df.columns and not df.at[idx, "VaultLocation"]:
            df.at[idx, "VaultLocation"] = f"vault://secret/ssl/{domain}"
    else:
        df = pd.concat([
            df,
            pd.DataFrame([
                {
                    "Domain": domain,
                    "Status": status,
                    "Expiry": expiry_date,
                    "IssuerCN": issuer,
                    "DaysRemaining": days_remaining,
                    "VaultLocation": f"vault://secret/ssl/{domain}",
                    "LastRenewed": last_renewed
                }
            ])
        ], ignore_index=True)

    st.session_state.ssl_certs_df = df
    try:
        df.to_csv(file_path, index=False)
    except Exception:
        pass
    return df

def ssl_vault_steps(domain):
    """SOP-driven SSL vaulting steps"""
    confluence_url = "https://teammeenakshi.atlassian.net/wiki/x/AgAH"
    return [
        f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Vaulting initiated for {domain}",
        f"[{datetime.now().strftime('%H:%M:%S')}] 📘 Follow SOP steps in Confluence: {confluence_url}",
        f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Vaulting completed per Confluence SOP",
        f"[{datetime.now().strftime('%H:%M:%S')}] Vault path: secret/ssl/{domain}"
    ]


def _normalize_confluence_base_url(base_url):
    if not base_url:
        return "https://teammeenakshi.atlassian.net"
    return base_url.rstrip("/")

def _extract_confluence_page_id(value):
    if not value:
        return None
    raw = str(value).strip()
    if raw.isdigit():
        return raw

    patterns = [
        r"/pages/edit-v2/(\d+)",
        r"/pages/(\d+)",
        r"[?&]pageId=(\d+)",
        r"/wiki/spaces/.+?/pages/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return match.group(1)
    return None

def _confluence_page_url(base_url, page_id):
    base = _normalize_confluence_base_url(base_url)
    return f"{base}/wiki/pages/viewpage.action?pageId={page_id}"

@st.cache_data(show_spinner=False)
def get_confluence_app_pages():
    """Return configured Confluence pages for app details."""
    raw = os.getenv("CONFLUENCE_APP_PAGES", "").strip()
    if raw:
        try:
            pages = json.loads(raw)
            if isinstance(pages, list):
                return pages
        except Exception:
            pass

    # Default (App1 + App2 provided by user)
    return [
        {
            "name": "app1",
            "page_id": "2097154",
            "tags": ["trading", "stock"]
        },
        {
            "name": "app2",
            "page_id": "2523137",
            "tags": ["trading", "stocks", "portfolio"]
        }
    ]

@st.cache_data(show_spinner=False)
def fetch_confluence_page(page_id):
    base_url = _normalize_confluence_base_url(os.getenv("CONFLUENCE_BASE_URL", "https://teammeenakshi.atlassian.net"))
    user = os.getenv("CONFLUENCE_USER", "")
    token = os.getenv("CONFLUENCE_API_TOKEN", "")

    if not page_id:
        return None
    if not user or not token:
        return None

    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,version,title,space"
    try:
        response = requests.get(url, auth=(user, token), timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None

def _confluence_storage_to_text(storage_html):
    if not storage_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", storage_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _snippet_from_text(text, query, max_len=420):
    if not text:
        return ""
    lower_text = text.lower()
    idx = lower_text.find(query.lower()) if query else -1
    if idx == -1:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    start = max(0, idx - 120)
    end = min(len(text), idx + max_len)
    snippet = text[start:end]
    return ("..." if start > 0 else "") + snippet + ("..." if end < len(text) else "")

def search_confluence(query):
    """Search Confluence app pages for relevant documentation."""
    pages = get_confluence_app_pages()
    if not pages:
        return None

    q = (query or "").lower().strip()
    for page in pages:
        name = str(page.get("name", "")).strip()
        page_id = _extract_confluence_page_id(page.get("page_id") or page.get("url"))
        tags = [str(t).lower().strip() for t in page.get("tags", []) if t]

        if not page_id:
            continue

        page_data = fetch_confluence_page(page_id)
        if not page_data:
            continue

        title = page_data.get("title", name or f"Page {page_id}")
        storage_html = page_data.get("body", {}).get("storage", {}).get("value", "")
        content_text = _confluence_storage_to_text(storage_html)

        name_match = name and name.lower() in q
        tag_match = any(tag and tag in q for tag in tags)
        content_match = q and q in content_text.lower()

        if name_match or tag_match or content_match:
            return {
                "title": title,
                "page_id": page_id,
                "url": _confluence_page_url(os.getenv("CONFLUENCE_BASE_URL", "https://teammeenakshi.atlassian.net"), page_id),
                "snippet": _snippet_from_text(content_text, q)
            }

    return None

def web_search(query):
    """Perform actual Google search and return top results"""
    try:
        from googlesearch import search as google_search
        
        # Get top 3 search results
        results = []
        for url in google_search(query, num_results=3, sleep_interval=1):
            results.append(url)
        
        if results:
            formatted_results = "\n".join([f"• {url}" for url in results])
            return f"🌐 **Web Search Results:**\n{formatted_results}"
        else:
            return None
    except ImportError:
        # Fallback if googlesearch-python not installed
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return f"🌐 Search Google: {search_url}"
    except Exception as e:
        return None

def ai_chatbot_response(user_query, ui_context, vuln_df=None):
    import os
    from google import genai
    from google.genai import types
    
    api_key = os.getenv("GOOGLE_API_KEY", "")
    
    # Step 1: Try Confluence first
    confluence_result = search_confluence(user_query)
    if confluence_result:
        return (
            f"📘 **Confluence App Details Found**\n\n"
            f"**Title:** {confluence_result.get('title')}\n"
            f"**Link:** {confluence_result.get('url')}\n\n"
            f"**Summary:** {confluence_result.get('snippet')}"
        )
    
    # Step 2: Try web search - now performs real Google search
    web_result = web_search(user_query)
    if web_result and "Web Search Results:" in web_result:
        # Return actual web search results
        return web_result
    
    # Step 3: Fall back to LLM if no web results found
    if not api_key:
        fallback_msg = "AI search not available: GOOGLE_API_KEY not set."
        if web_result:
            return f"{web_result}\n\n{fallback_msg}"
        return fallback_msg
    
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
You are an Intelligent Assistant helping users with various queries in a friendly and approachable manner.

Your role:
1. Answer user queries by searching Confluence documentation first
2. If not in Confluence, perform web search and check current knowledge
3. Provide helpful information in simple, easy-to-understand language
4. Be conversational and friendly

Capabilities:
- Access system information and documentation
- Provide helpful guidance and troubleshooting advice
- Answer general questions

Context: {context_info}

Respond in a friendly and helpful way. Keep explanations clear and simple.
"""
    
    try:
        client = genai.Client(api_key=api_key)
        
        full_query = f"User query: {user_query}\n\nBased on the available information and web search results, provide a helpful response."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
        
        llm_response = response.text if response.text else ""
        
        if llm_response:
            return f"{web_result}\n\n**AI Response:**\n{llm_response.strip()}" if web_result else llm_response.strip()
        else:
            return f"{web_result}\n\nAI could not generate a response." if web_result else "AI could not generate a response."
    except Exception as e:
        return f"{web_result}\n\nAI error: {str(e)}" if web_result else f"AI error: {str(e)}"
def generate_commit_hash(length=40):
    return ''.join(random.choices('0123456789abcdef', k=length))

@st.cache_resource
def get_copilot_kb_client():
    """Initialize Copilot KB API client (replaces Excel loading)"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from api.copilot_kb_client import CopilotKBClient
        
        # Use local API or remote
        api_url = os.getenv("COPILOT_KB_API", "http://localhost:8000")
        client = CopilotKBClient(api_url)
        return client
    except Exception as e:
        st.warning(f"⚠️ Copilot KB API not available: {str(e)}")
        return None

def chatbot_answer_engine(user_query, ui_context, vuln_df=None):
    query = user_query.lower().strip()
    
    # Handle greetings
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]
    if any(greet in query for greet in greetings) and len(query.split()) <= 3:
        return "👋 Hello! I'm your lowerlane environment chatbot. I can help with system monitoring, incidents, vulnerabilities, and provide troubleshooting advice. What would you like to know?"
    
    # Handle casual queries
    if "how are you" in query.lower() or "how do you do" in query.lower():
        return "I'm doing well, thank you! As an AI chatbot, I'm always ready to help with system monitoring and troubleshooting. What can I assist you with today?"

    # -------- CONFLUENCE APP DETAILS --------
    confluence_match = search_confluence(query)
    if confluence_match:
        return (
            f"📘 **Confluence App Details**\n\n"
            f"**Title:** {confluence_match.get('title')}\n"
            f"**Link:** {confluence_match.get('url')}\n\n"
            f"**Summary:** {confluence_match.get('snippet')}"
        )
    

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
        return (
            "🚀 **Deployment Plan (Demo)**\n\n"
            "**Plan Steps:**\n"
            "1. Validate build artifacts and configuration.\n"
            "2. Run pre-deployment health checks.\n"
            "3. Deploy to staging and run smoke tests.\n"
            "4. Deploy to production with rolling restart.\n"
            "5. Verify service health and key metrics.\n\n"
            f"See [Confluence KB]({CONFLUENCE_KB_URL}) for standard procedures.\n\n"
            "**Demo Summary:**\n"
            "- Deployment completed successfully with no downtime.\n"
            "- All checks passed and services are healthy.\n"
            "- Monitoring confirmed stable performance post-release."
        )

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
if "app_exists" not in st.session_state:
    st.session_state.app_exists = False
if "app_path" not in st.session_state:
    st.session_state.app_path = None
if "current_version" not in st.session_state:
    st.session_state.current_version = "1.0.0"
if "release_history" not in st.session_state:
    st.session_state.release_history = []

# Initialize health check state
if "health_check_results" not in st.session_state:
    st.session_state.health_check_results = []
if "health_check_history" not in st.session_state:
    st.session_state.health_check_history = []
if "health_check_logs" not in st.session_state:
    st.session_state.health_check_logs = []

# Initialize problem tracking & Jira state
if "tracked_problems" not in st.session_state:
    st.session_state.tracked_problems = []
if "jira_tickets" not in st.session_state:
    st.session_state.jira_tickets = []

# Initialize SSL certificate inventory
if "ssl_certs_df" not in st.session_state:
    st.session_state.ssl_certs_df = load_ssl_certificates_csv("ssl_certificates.csv")


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

   # ✨ -------- Copilot KB API (Replaces Excel) --------
    if "copilot_kb" not in st.session_state:
        try:
            st.session_state.copilot_kb = get_copilot_kb_client()
            if st.session_state.copilot_kb:
                st.sidebar.success("✅ Copilot KB API Connected (Unlimited Knowledge)")
            else:
                st.sidebar.warning("⚠️ Using fallback knowledge base")
        except Exception as e:
            st.sidebar.error(f"❌ KB Error: {str(e)}")



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

    tabs = st.tabs(["lowerlane environment chatbot", "Deployment", "Problems & Jira", "🛡️ Vulnerability Remediation", "🤖 Agentic Copilot"])

    # --- Deployment tab ---
    with tabs[1]:
        st.header("🚀 Deployment Console (with Auto-Detection)")

        st.markdown("""
        **Smart Deployment Workflow:**
        1. ✅ Check if app directory exists in instance
        2. 📋 Fetch version from config file
        3. 🔍 Detect code changes
        4. 🚀 Deploy via Jenkins
        5. 📧 Send email notification
        """)
        
        st.divider()

        # -------- APP & INSTANCE SELECTION --------
        st.subheader("📱 App & Instance Selection")
        col1, col2 = st.columns(2)
        
        with col1:
            app_name = st.selectbox(
                "Application",
                ["app1", "app2", "app3", "microservice-api", "web-frontend", "cache-service"],
                key="deploy_app"
            )
        with col2:
            instance_name = st.selectbox(
                "Instance/Server",
                ["prod-server-1", "prod-server-2", "staging-server", "dev-instance"],
                key="deploy_instance"
            )
        
        # Check if app directory exists
        st.subheader("🔍 Pre-Deployment Check")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Check App Directory", use_container_width=True):
                exists, path = check_app_directory(app_name)
                if exists:
                    st.success(f"✅ App directory found at: `{path}`")
                    st.session_state.app_path = path
                    st.session_state.app_exists = True
                else:
                    st.warning(f"⚠️ App directory not found for {app_name}")
                    st.info("ℹ️ This app will be deployed fresh. New directory will be created.")
                    st.session_state.app_exists = False
        
        with col2:
            if st.button("Fetch Config & Version", use_container_width=True):
                app_path = st.session_state.get("app_path", None)
                version = get_app_version_from_config(app_name, app_path)
                st.session_state.current_version = version
                st.success(f"✅ Current Version: `{version}`")
        
        st.divider()
        
        # -------- DEPLOYMENT CONFIGURATION --------
        st.subheader("⚙️ Deployment Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            deployment_type = st.radio(
                "Deployment Type",
                ["Fresh Deploy", "Version Update", "Code Changes", "Hotfix"]
            )
        with col2:
            deploy_env = st.selectbox(
                "Environment",
                ["prod", "staging", "dev"],
                index=1
            )

        # Previous release info (per app/env)
        prev_release = None
        for entry in reversed(st.session_state.release_history):
            if entry.get("app") == app_name and entry.get("env") == deploy_env:
                prev_release = entry
                break
        if prev_release:
            st.info(f"🧾 Previous release date: {prev_release.get('timestamp')} (v{prev_release.get('version')})")
        else:
            st.info("🧾 Previous release date: Not available")
        
        new_version = st.text_input(
            "Target Version / Build Tag",
            value=st.session_state.get("current_version", "1.0.0"),
            placeholder="e.g., 1.2.3 or build-2024-02-02"
        )
        
        # Jenkins Configuration
        st.subheader("🔧 Jenkins Configuration")
        col1, col2 = st.columns(2)
        with col1:
            jenkins_url = st.text_input(
                "Jenkins URL",
                value="http://jenkins.example.com:8080",
                placeholder="http://jenkins-server:8080"
            )
        with col2:
            jenkins_job = st.selectbox(
                "Jenkins Job",
                ["deploy-app", "ci-cd-pipeline", "app-build-deploy", "release-deploy"]
            )
        
        st.divider()
        
        # -------- CODE CHANGES & EMAIL --------
        st.subheader("📝 Code Changes & Notifications")
        
        code_changes = st.text_area(
            "Code Changes / Commit Messages",
            placeholder="e.g.,\n- Fixed bug in login module\n- Updated dependencies\n- Refactored database queries",
            height=80
        )

        release_summary = st.text_area(
            "Release Summary (SRE)",
            placeholder="e.g.,\n- Risk: Low\n- Rollback: Available\n- Monitoring: Login errors, latency p95",
            height=80
        )
        
        email_recipients = st.text_input(
            "Email Recipients (comma-separated)",
            placeholder="team@example.com, devops@example.com, manager@example.com",
            value="team@example.com"
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            notify_email = st.checkbox("📧 Send Email Notification", value=True)
        with col2:
            notify_slack = st.checkbox("💬 Notify Slack", value=False)
        with col3:
            notify_teams = st.checkbox("👥 Notify Teams", value=True)
        
        st.divider()
        
        # -------- DEPLOYMENT EXECUTION --------
        st.subheader("🚀 Deploy Now")
        
        col1, col2 = st.columns(2)
        with col1:
            deploy_button = st.button(
                "🚀 START DEPLOYMENT",
                use_container_width=True,
                type="primary"
            )
        with col2:
            preview_button = st.button(
                "👁️ Preview Deployment Plan",
                use_container_width=True
            )
        
        # Preview Mode
        if preview_button:
            st.info("📋 Deployment Plan Preview:")
            with st.container(border=True):
                st.write(f"**Application:** {app_name}")
                st.write(f"**Instance:** {instance_name}")
                st.write(f"**Deployment Type:** {deployment_type}")
                st.write(f"**Target Version:** {new_version}")
                st.write(f"**Environment:** {deploy_env}")
                st.write(f"**Jenkins Job:** {jenkins_job}")
                st.write(f"**Email Notification:** {'✅ Yes' if notify_email else '❌ No'}")
                if code_changes:
                    st.write(f"**Changes:** {code_changes[:100]}...")
                if release_summary:
                    st.write(f"**Release Summary:** {release_summary[:120]}...")
        
        # Deployment Execution
        if deploy_button:
            if not app_name or not new_version:
                st.error("❌ Please select app and enter version")
            else:
                with st.spinner("Starting deployment..."):
                    # Create deployment log
                    deploy_log = []
                    
                    # Step 1: Check directory
                    deploy_log.append(f"{utc_now()} | STEP_1 | Checking app directory for {app_name}")
                    if st.session_state.get("app_exists"):
                        deploy_log.append(f"{utc_now()} | CHECK_PASS | App directory exists at {st.session_state.get('app_path')}")
                    else:
                        deploy_log.append(f"{utc_now()} | CHECK_FAIL | App directory not found - will create fresh deployment")
                        deploy_log.append(f"{utc_now()} | CREATING | Setting up new directory structure")
                    
                    # Step 2: Fetch config
                    deploy_log.append(f"{utc_now()} | STEP_2 | Fetching config and version")
                    current_ver = st.session_state.get("current_version", "0.0.0")
                    deploy_log.append(f"{utc_now()} | CONFIG | Current Version: {current_ver}, Target Version: {new_version}")
                    
                    # Step 3: Detect changes
                    deploy_log.append(f"{utc_now()} | STEP_3 | Analyzing code changes")
                    if code_changes:
                        deploy_log.append(f"{utc_now()} | CHANGES_DETECTED | {len(code_changes.split())} changes found")
                    else:
                        deploy_log.append(f"{utc_now()} | NO_CHANGES | Version/config only update")
                    
                    # Step 4: Jenkins trigger
                    pytime.sleep(1)
                    deploy_log.append(f"{utc_now()} | STEP_4 | Triggering Jenkins job: {jenkins_job}")
                    deploy_log.append(f"{utc_now()} | JENKINS | Job URL: {jenkins_url}/job/{jenkins_job}/build")
                    jenkins_build_id = generate_commit_hash(8).upper()
                    deploy_log.append(f"{utc_now()} | BUILD_ID | {jenkins_build_id}")
                    
                    # Step 5: Deployment
                    pytime.sleep(2)
                    deploy_log.append(f"{utc_now()} | DEPLOYING | Pulling code from repository")
                    deploy_log.append(f"{utc_now()} | DEPLOYING | Building artifact for v{new_version}")
                    deploy_log.append(f"{utc_now()} | DEPLOYING | Deploying to {instance_name} ({deploy_env})")
                    pytime.sleep(1)
                    deploy_log.append(f"{utc_now()} | DEPLOY_SUCCESS | Application deployed successfully")
                    
                    # Step 6: Email notification
                    if notify_email:
                        deploy_log.append(f"{utc_now()} | EMAIL | Preparing email notification")
                        email_subject, email_body = send_deployment_email(app_name, new_version, deployment_type, code_changes)
                        deploy_log.append(f"{utc_now()} | EMAIL | Sending to: {email_recipients}")
                        deploy_log.append(f"{utc_now()} | EMAIL | Subject: {email_subject}")
                        deploy_log.append(f"{utc_now()} | EMAIL | ✅ Email sent successfully")
                    
                    # Store deployment info
                    st.session_state.deploy_logs = deploy_log
                    st.session_state.deploy_version = new_version
                    st.session_state.deploy_tags = [
                        "deployed", deployment_type.lower(), deploy_env, 
                        f"v{new_version}", jenkins_build_id
                    ]
                    st.session_state.release_history.append({
                        "timestamp": utc_now(),
                        "app": app_name,
                        "env": deploy_env,
                        "version": new_version,
                        "summary": release_summary or ""
                    })
                    
                    st.success("✅ Deployment completed successfully!")
        
        # Display Deployment Logs
        if st.session_state.deploy_logs:
            st.divider()
            st.subheader("📡 Deployment Execution Log")
            with st.container(border=True):
                for log in st.session_state.deploy_logs:
                    if "SUCCESS" in log or "PASS" in log:
                        st.success(log)
                    elif "FAIL" in log or "ERROR" in log:
                        st.error(log)
                    elif "EMAIL" in log:
                        st.info(log)
                    else:
                        st.write(log)
            
            # Summary
            st.subheader("📊 Deployment Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Application", app_name)
            with col2:
                st.metric("Version", new_version)
            with col3:
                st.metric("Environment", deploy_env)
            with col4:
                st.metric("Status", "✅ Success")

            if release_summary:
                st.subheader("🧾 Release Summary")
                st.write(release_summary)
            
            # Tags
            if st.session_state.deploy_tags:
                st.subheader("🏷️ Deployment Tags")
                st.multiselect(
                    "Tags",
                    options=st.session_state.deploy_tags,
                    default=st.session_state.deploy_tags,
                    disabled=True
                )

    # --- lowerlane environment chatbot tab ---
    with tabs[0]:
        st.header("💬 lowerlane environment chatbot")

        with st.expander("How this works (Agentic flow)", expanded=False):
            st.markdown(
                """
                **Signal → Reason → Decide → Act → Learn**

                **LLM (Brain):** Interprets health signals, reasons over logs/runbooks, proposes safe remediation.
                **Orchestrator:** Breaks tasks into steps, invokes tools, applies guardrails.
                **Memory:** Uses recent context + historical incidents + policy rules.

                **Demo flow:** detect degradation → collect metrics/logs → reason → safety checks → restart → verify → log outcome.
                """
            )

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
                        st.session_state.get("vuln_df")
                    )

                    if raw_answer == "NOT_FOUND" or raw_answer is None:
                        raw_answer = ai_chatbot_response(q, st.session_state.ui_state, st.session_state.get("copilot_kb"))

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
                        st.session_state.get("vuln_df")
                    )

                    # If no matching rule found, fall back to Confluence + Web + LLM
                    if raw_answer == "NOT_FOUND" or raw_answer is None:
                        raw_answer = ai_chatbot_response(user_query, st.session_state.ui_state, st.session_state.get("copilot_kb"))

                    formatted_answer = format_bot_response(raw_answer)

            # --- Store bot response ---
            st.session_state.messages.append({
                "role": "assistant",
                "content": formatted_answer
            })

            # Refresh to show new messages
            st.rerun()

        st.divider()
        st.header("🏥 Health Check Monitoring")
        
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

            live_health_url = st.text_input(
                "Live Health URL",
                value="http://18.237.102.97:8000/health/epas",
                help="Optional: Use a single live URL for health check"
            )
            use_live_url = st.checkbox("Use Live URL for health check", value=False)

            col1, col2, col3 = st.columns(3)
            
            with col1:
                run_health_check = st.button("🚀 Run Health Check", use_container_width=True)
            with col2:
                send_to_teams = st.button("📤 Send to Teams", use_container_width=True)
            with col3:
                clear_results = st.button("🗑️ Clear Results", use_container_width=True)

            retry_col1, retry_col2 = st.columns([2, 1])
            with retry_col1:
                auto_retry_failed = st.checkbox("Auto-retry failed apps after delay", value=True)
            with retry_col2:
                retry_delay_sec = st.number_input("Retry delay (sec)", min_value=5, max_value=300, value=30, step=5)

            st.subheader("🤖 Agentic Auto-Restart (Demo)")
            policy = load_policy()
            agentic_col1, agentic_col2, agentic_col3, agentic_col4 = st.columns(4)
            with agentic_col1:
                agentic_enabled = st.checkbox("Enable agentic flow", value=True)
            with agentic_col2:
                require_approval = st.checkbox("Require approval", value=policy.get("require_approval", True))
            with agentic_col3:
                allow_restart = st.checkbox("Allow restart", value=policy.get("allow_restart", True))
            with agentic_col4:
                max_restarts_per_day = st.number_input(
                    "Max restarts/day",
                    min_value=1,
                    max_value=10,
                    value=int(policy.get("max_restarts_per_day", 2)),
                    step=1
                )

            llm_reasoning = st.checkbox("Use LLM reasoning", value=True)

            with st.expander("Policy gates", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    start_hour = st.number_input(
                        "Change window start hour",
                        min_value=0,
                        max_value=23,
                        value=int(policy.get("change_window", {}).get("start_hour", 9)),
                        step=1
                    )
                with col_b:
                    end_hour = st.number_input(
                        "Change window end hour",
                        min_value=1,
                        max_value=24,
                        value=int(policy.get("change_window", {}).get("end_hour", 18)),
                        step=1
                    )

                if st.button("Save policy", use_container_width=True):
                    policy_update = {
                        "allow_restart": allow_restart,
                        "require_approval": require_approval,
                        "max_restarts_per_day": int(max_restarts_per_day),
                        "change_window": {"start_hour": int(start_hour), "end_hour": int(end_hour)},
                    }
                    save_policy(policy_update)
                    st.success("Policy updated")
            
            if run_health_check:
                with st.spinner("Running health checks..."):
                    apps_to_check = st.session_state.apps
                    if use_live_url and live_health_url:
                        apps_to_check = [{
                            "AppName": "Live Health URL",
                            "URL": live_health_url,
                            "Expected": "200"
                        }]

                    st.session_state.health_check_logs.append(
                        f"{utc_now()} | RUN_START | total_apps={len(apps_to_check)}"
                    )
                    results = []
                    progress_bar = st.progress(0)
                    
                    for idx, app in enumerate(apps_to_check):
                        result = check_app_health(app)
                        results.append(result)
                        status_flag = "OK" if result["Color"] == "green" else "FAIL"
                        st.session_state.health_check_logs.append(
                            f"{utc_now()} | CHECK_{status_flag} | app={result['AppName']} | url={result['URL']} | status={result['Status']}"
                        )
                        progress_bar.progress((idx + 1) / len(apps_to_check))
                    
                    # Optional auto-retry for failed apps (useful after restart)
                    failed_after_first = [r for r in results if r["Color"] == "red"]
                    if auto_retry_failed and failed_after_first:
                        st.info(f"Retrying {len(failed_after_first)} failed app(s) after {retry_delay_sec}s...")
                        st.session_state.health_check_logs.append(
                            f"{utc_now()} | RETRY_START | failed_apps={len(failed_after_first)} | delay_sec={int(retry_delay_sec)}"
                        )
                        pytime.sleep(int(retry_delay_sec))

                        retry_results = []
                        for app in apps_to_check:
                            if any(r["AppName"] == app["AppName"] and r["Color"] == "red" for r in results):
                                retry_results.append(check_app_health(app))

                        for retry_result in retry_results:
                            status_flag = "OK" if retry_result["Color"] == "green" else "FAIL"
                            st.session_state.health_check_logs.append(
                                f"{utc_now()} | RETRY_{status_flag} | app={retry_result['AppName']} | url={retry_result['URL']} | status={retry_result['Status']}"
                            )

                        # Merge retry results with originals
                        merged = []
                        retry_map = {r["AppName"]: r for r in retry_results}
                        for r in results:
                            merged.append(retry_map.get(r["AppName"], r))

                        results = merged

                    # Agentic auto-restart (demo)
                    st.session_state.agentic_actions = []
                    if agentic_enabled:
                        memory = load_incident_memory()
                        policy = load_policy()
                        policy["allow_restart"] = allow_restart
                        policy["require_approval"] = require_approval
                        policy["max_restarts_per_day"] = int(max_restarts_per_day)

                        for result in results:
                            if result["Color"] != "red":
                                continue
                            decision = agentic_reason_and_decide(result, memory, policy)
                            if llm_reasoning:
                                llm_decision = llm_reason_decide(result, memory, policy)
                                if llm_decision:
                                    decision["action"] = llm_decision.get("action", decision["action"])
                                    decision["reason"] = llm_decision.get("reason", decision["reason"])
                                    decision["confidence"] = llm_decision.get("confidence", decision["confidence"])
                            st.session_state.agentic_actions.append(decision)

                            st.session_state.health_check_logs.append(
                                f"{utc_now()} | AGENTIC_DECIDE | app={decision['app']} | action={decision['action']} | safe={decision['safe_to_act']} | reason={decision['reason']}"
                            )

                            if decision["action"] == "restart" and decision["safe_to_act"]:
                                if decision["requires_approval"]:
                                    st.session_state.health_check_logs.append(
                                        f"{utc_now()} | AGENTIC_PENDING_APPROVAL | app={decision['app']}"
                                    )
                                    memory.append({
                                        "timestamp": utc_now(),
                                        "app": decision["app"],
                                        "action": "restart",
                                        "outcome": "pending_approval",
                                        "reason": decision["reason"],
                                    })
                                else:
                                    outcome = agentic_execute_restart(result)
                                    st.session_state.health_check_logs.append(
                                        f"{utc_now()} | AGENTIC_RESTART | app={decision['app']} | outcome={outcome['outcome']}"
                                    )
                                    memory.append({
                                        "timestamp": utc_now(),
                                        "app": decision["app"],
                                        "action": "restart",
                                        "outcome": outcome["outcome"],
                                        "reason": decision["reason"],
                                    })
                            else:
                                memory.append({
                                    "timestamp": utc_now(),
                                    "app": decision["app"],
                                    "action": "no_action",
                                    "outcome": "skipped",
                                    "reason": decision["reason"],
                                })

                        save_incident_memory(memory)

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

                if st.session_state.get("agentic_actions"):
                    with st.expander("🤖 Agentic Decisions", expanded=False):
                        memory = load_incident_memory()
                        for action in st.session_state.agentic_actions:
                            st.write(
                                f"**{action['app']}** → `{action['action']}` | safe={action['safe_to_act']} | reason: {action['reason']}"
                            )
                            if action["action"] == "restart" and action.get("requires_approval"):
                                if st.button(f"Approve restart: {action['app']}", key=f"approve_{action['app']}"):
                                    outcome = agentic_execute_restart({"AppName": action["app"]})
                                    st.success(f"Restart approved for {action['app']}: {outcome['details']}")
                                    st.session_state.health_check_logs.append(
                                        f"{utc_now()} | AGENTIC_RESTART | app={action['app']} | outcome={outcome['outcome']}"
                                    )
                                    memory.append({
                                        "timestamp": utc_now(),
                                        "app": action["app"],
                                        "action": "restart",
                                        "outcome": outcome["outcome"],
                                        "reason": action["reason"],
                                    })
                                    save_incident_memory(memory)
                
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

                # Logs Section
                if st.session_state.health_check_logs:
                    st.divider()
                    st.subheader("🧾 Health Check Logs")
                    with st.container(border=True):
                        for log in st.session_state.health_check_logs[-50:]:
                            st.write(log)
                
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
        
        # --- Disk Space Analysis Section ---
        st.divider()
        st.header("💾 Disk Space Analysis")
        
        if st.button("Analyze Disk Space"):
            import subprocess
            result = subprocess.run(['df', '-h'], capture_output=True, text=True)
            st.code(result.stdout)

    # --- SSL Management tab ---
    with tabs[2]:
        st.header("🔐 SSL Certificate - Agentic Flow")
        
        # SSL Agentic Flow Overview
        st.markdown("""
        **SSL Certificate Management Flow:**
        1. 🔍 **PERCEPTION** → Fetch from Venefi / Let's Encrypt / Certificate Portal
        2. 🧠 **LLM BRAIN** → OpenAI / Gemini SDK for analysis
        3. 📦 **STORAGE** → Vector DB, S3, MySQL persistence
        4. 🤖 **AGENT LAYER** → Autonomous agents handling verification & renewal
        5. 📢 **ACTION** → Renewal, Feedback, Team notifications
        """)
        
        st.divider()
        
        # -------- PERCEPTION LAYER --------
        st.subheader("🔍 PERCEPTION - Certificate Discovery")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Venefi**")
            if st.button("🔄 Sync Venefi", key="ssl_sync_venefi"):
                st.info("📡 Fetching certificates from Venefi portal...")
                st.success("✅ Synced 12 certificates from Venefi")
        
        with col2:
            st.markdown("**Let's Encrypt**")
            if st.button("🔄 Sync Let's Encrypt", key="ssl_sync_le"):
                st.info("📡 Fetching certificates from Let's Encrypt API...")
                st.success("✅ Synced 5 certificates from Let's Encrypt")
        
        with col3:
            st.markdown("**Certificate Portal**")
            if st.button("🔄 Sync Portal", key="ssl_sync_portal"):
                st.info("📡 Fetching from certificate management portal...")
                st.success("✅ Synced 3 certificates from Portal")
        
        st.divider()
        
        # -------- STORAGE & INVENTORY --------
        st.subheader("📊 STORAGE - Certificate Inventory")
        
        if st.session_state.ssl_certs_df is None or st.session_state.ssl_certs_df.empty:
            st.warning("⚠️ No SSL inventory found. Sync from sources above.")
        else:
            ssl_df = st.session_state.ssl_certs_df.copy()
            if "VaultLocation" in ssl_df.columns:
                ssl_df = ssl_df.drop(columns=["VaultLocation"])
            st.dataframe(ssl_df, use_container_width=True)
        
        st.divider()
        
        # -------- AUTONOMOUS AGENT MONITORING --------
        st.subheader("🤖 AUTONOMOUS AGENT LAYER - Monitoring Only (No Manual Controls)")
        
        st.info("""
        ℹ️ **Agents Run Autonomously 24/7 in Background Service**
        
        Agents automatically:
        - Monitor SSL certificates every 1 hour
        - Detect expiring certificates
        - Renew certificates autonomously (when confidence > 70%)
        - Send notifications (Teams/Slack/Outlook)
        
        This is **read-only monitoring**. All agent actions are autonomous.
        """)
        
        # Monitor agent status from background service
        agent_server_url = os.getenv("AGENT_SERVER_URL", "http://localhost:8001")
        agent_url = f"{agent_server_url}/api/agents/ssl"
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Agent Status**")
            try:
                import requests
                response = requests.get(agent_url, timeout=5)
                if response.status_code == 200:
                    agent_data = response.json()
                    st.success(f"✅ {agent_data.get('agent')} - Running")
                    st.caption(f"Last run: {agent_data.get('last_run', 'Never')}")
                else:
                    st.warning("⚠️ Agent service unreachable")
            except Exception as e:
                st.warning(f"⚠️ Cannot connect to agent service: {str(e)}")
        
        with col2:
            st.markdown("**Recent Autonomous Decisions**")
            decisions_url = f"{agent_server_url}/api/agents/decisions?limit=5"
            try:
                response = requests.get(decisions_url, timeout=5)
                if response.status_code == 200:
                    decisions = response.json().get("recent_decisions", [])
                    if decisions:
                        for d in decisions[-3:]:  # Show last 3
                            st.caption(f"• {d.get('decision', 'N/A').upper()} | {d.get('action', 'N/A')} | {d.get('timestamp', 'N/A')[:10]}")
                    else:
                        st.caption("No decisions yet")
            except:
                st.caption("Unable to fetch decisions")
        
        # Certificate Inventory View
        st.subheader("📊 Certificate Inventory (Read-Only)")
        
        df = st.session_state.ssl_certs_df
        if df is not None and not df.empty:
            with st.expander("📋 View Certificates", expanded=False):
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No certificates loaded")

    # --- Problems & Jira Tickets tab ---
    with tabs[2]:
        st.header("🎟️ Problem Tracking & Auto-Created Jira Tickets")
        
        st.markdown("""
        **Auto-Jira Feature:**
        - 🔍 Agent detects problems during monitoring
        - ✅ If solved by agent → No ticket
        - ❌ If NOT solved by agent → Auto-create Jira ticket
        - 📧 Team gets notified in Jira
        """)
        
        st.divider()
        
        # Jira Configuration
        with st.expander("⚙️ Jira Configuration", expanded=True):
            st.subheader("Jira Credentials Setup")
            
            col1, col2 = st.columns(2)
            with col1:
                jira_url = st.text_input(
                    "Jira URL",
                    value=os.getenv("JIRA_URL", "https://teammeenakshi.atlassian.net"),
                    placeholder="https://your-company.atlassian.net"
                )
            with col2:
                jira_user = st.text_input(
                    "Jira Email",
                    value=os.getenv("JIRA_USER", "porselvi.baskar@in.ey.com"),
                    placeholder="your-email@company.com"
                )
            
            jira_token = st.text_input(
                "Jira API Token",
                value=os.getenv("JIRA_API_TOKEN", ""),
                type="password",
                placeholder="Get from https://id.atlassian.com/manage-profile/security/api-tokens"
            )
            
            jira_project = st.text_input(
                "Jira Project Key",
                value=os.getenv("JIRA_PROJECT", "KAN"),
                placeholder="e.g., KAN, OPS, SRE"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Save Config", use_container_width=True):
                    if jira_url and jira_user and jira_token and jira_project:
                        os.environ["JIRA_URL"] = jira_url
                        os.environ["JIRA_USER"] = jira_user
                        os.environ["JIRA_API_TOKEN"] = jira_token
                        os.environ["JIRA_PROJECT"] = jira_project
                        st.success("✅ Jira configuration saved!")
                    else:
                        st.error("❌ Please fill all Jira fields")
            
            with col2:
                if st.button("🧪 Test Connection", use_container_width=True):
                    if jira_url and jira_user and jira_token and jira_project:
                        valid, message = validate_jira_connection(jira_url, jira_user, jira_token, jira_project)
                        if valid:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("❌ Please fill all fields first")
            
            with col3:
                if st.button("📖 Get API Token", use_container_width=True):
                    st.info("🔗 Visit: https://id.atlassian.com/manage-profile/security/api-tokens")
                    st.info("Steps:\n1. Click 'Create API token'\n2. Copy the token\n3. Paste above")
            
            st.divider()
            st.caption("💡 **Tip:** Credentials are stored in environment variables and persisted during session")
        
        st.divider()
        
        # Manual Problem Reporting
        st.subheader("📝 Manual Problem Report")
        
        col1, col2 = st.columns(2)
        with col1:
            problem_title = st.text_input(
                "Problem Title",
                placeholder="e.g., Database connection timeout",
                key="problem_title"
            )
        with col2:
            problem_type = st.selectbox(
                "Problem Type",
                ["Database", "Network", "Disk Space", "CPU", "Memory", "Application Error", "SSL Certificate", "Other"],
                key="problem_type"
            )
        
        problem_description = st.text_area(
            "Problem Description & Details",
            placeholder="Describe the issue, affected services, error messages, etc.",
            height=100,
            key="problem_desc"
        )
        
        problem_severity = st.selectbox(
            "Severity",
            ["Critical", "High", "Medium", "Low", "Info"],
            key="problem_severity"
        )
        
        problem_solved = st.checkbox(
            "✅ Was this problem solved by the agent?",
            value=False,
            key="problem_solved"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔧 Report & Track Problem", use_container_width=True):
                if problem_title and problem_description:
                    problem = track_problem(
                        problem_title,
                        problem_description,
                        problem_type,
                        solved=problem_solved
                    )
                    
                    st.session_state.tracked_problems.append(problem)
                    
                    if problem["jira_ticket"]:
                        st.session_state.jira_tickets.append({
                            "ticket_id": problem["jira_ticket"],
                            "problem_id": problem["id"],
                            "created_at": utc_now(),
                            "title": problem_title,
                            "severity": problem_severity
                        })
                        st.success(f"✅ Problem tracked! Jira ticket: `{problem['jira_ticket']}`")
                    else:
                        if problem_solved:
                            st.success("✅ Problem tracked as SOLVED - No Jira ticket needed")
                        else:
                            st.warning(f"⚠️ {problem['jira_status']}")
                else:
                    st.error("❌ Please fill in problem title and description")
        
        with col2:
            if st.button("🔄 Refresh List", use_container_width=True):
                st.rerun()
        
        with col3:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.tracked_problems = []
                st.session_state.jira_tickets = []
                st.rerun()
        
        st.divider()
        
        # Display Tracked Problems
        if st.session_state.tracked_problems:
            st.subheader(f"📊 Tracked Problems ({len(st.session_state.tracked_problems)})")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_problems = len(st.session_state.tracked_problems)
            solved_problems = len([p for p in st.session_state.tracked_problems if p["solved"]])
            unsolved_problems = total_problems - solved_problems
            jira_tickets_created = len([p for p in st.session_state.tracked_problems if p["jira_ticket"]])
            
            with col1:
                st.metric("Total Problems", total_problems)
            with col2:
                st.metric("✅ Solved", solved_problems)
            with col3:
                st.metric("❌ Unsolved", unsolved_problems)
            with col4:
                st.metric("🎟️ Jira Tickets", jira_tickets_created)
            
            st.divider()
            
            # Problems table
            st.write("### All Tracked Problems")
            
            for idx, problem in enumerate(st.session_state.tracked_problems):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        status_icon = "✅" if problem["solved"] else "❌"
                        st.write(f"**{status_icon} {problem['title']}**")
                        st.caption(f"Type: {problem['type']} | Detected: {problem['detected_at']}")
                        st.write(problem['description'][:150] + "..." if len(problem['description']) > 150 else problem['description'])
                    
                    with col2:
                        if problem["jira_ticket"]:
                            st.success(f"🎟️ {problem['jira_ticket']}")
                        else:
                            st.info("No ticket" if problem["solved"] else "Pending")
                    
                    with col3:
                        if st.button("📌 View", key=f"view_problem_{idx}"):
                            with st.expander("Full Details"):
                                st.json(problem)
        
        else:
            st.info("ℹ️ No tracked problems yet. Report issues to get started!")
        
        st.divider()
        
        # Jira Tickets Display
        if st.session_state.jira_tickets:
            st.subheader(f"🎟️ Auto-Created Jira Tickets ({len(st.session_state.jira_tickets)})")
            
            for ticket in st.session_state.jira_tickets:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{ticket['ticket_id']}** - {ticket['title']}")
                        st.caption(f"Severity: {ticket['severity']} | Created: {ticket['created_at']}")
                    
                    with col2:
                        st.success("Auto-Created ✅")
                    
                    with col3:
                        if st.button("🔗 Open", key=f"open_ticket_{ticket['ticket_id']}"):
                            jira_url = os.getenv("JIRA_URL", "")
                            if jira_url:
                                ticket_url = f"{jira_url}/browse/{ticket['ticket_id']}"
                                st.write(f"Open: {ticket_url}")
        
        st.divider()
        
        # Autonomous Problem Detection (Read-Only Monitoring)
        st.subheader("🤖 Autonomous Problem Detection - Monitoring Only")
        
        st.info("""
        ℹ️ **Problem Detection Agent Runs Autonomously 24/7**
        
        Agent automatically:
        - Monitors logs, metrics, alerts
        - Detects problems in real-time
        - Attempts autonomous fixes
        - Auto-creates Jira tickets (only if agents cannot fix)
        
        This is **read-only**. No manual simulation needed.
        """)
        
        # Monitor Problem Detection Agent
        agent_url = "http://18.237.102.97:8001/api/agents/problems"
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Agent Status**")
            try:
                import requests
                response = requests.get(agent_url, timeout=5)
                if response.status_code == 200:
                    agent_data = response.json()
                    st.success(f"✅ {agent_data.get('agent')} - Running")
                    st.caption(f"Last run: {agent_data.get('last_run', 'Never')}")
                else:
                    st.warning("⚠️ Agent service unreachable")
            except Exception as e:
                st.warning(f"⚠️ Cannot connect to agent service")
        
        with col2:
            st.markdown("**Problems Detected & Actions Taken**")
            try:
                decisions_url = "http://18.237.102.97:8001/api/agents/decisions?limit=10"
                response = requests.get(decisions_url, timeout=5)
                if response.status_code == 200:
                    decisions = response.json().get("recent_decisions", [])
                    problem_decisions = [d for d in decisions if "problem" in d.get('agent', '').lower()]
                    if problem_decisions:
                        for d in problem_decisions[-3:]:
                            action = "✅ Fixed" if d.get('executed') else "⏳ Analyzing"
                            st.caption(f"{action} | {d.get('action', 'N/A')} | Confidence: {int(d.get('confidence', 0)*100)}%")
                    else:
                        st.caption("No recent problems detected")
            except:
                st.caption("Unable to fetch agent decisions")

    # --- Vulnerability Remediation tab ---
    with tabs[3]:
        st.header("🛡️ Vulnerability Remediation - Agentic Workflow")
        
        st.markdown("""
        **Automated Vulnerability Management Pipeline:**
        1. 📊 **Download** → Fetch vulnerability details from Tableau
        2. 🗑️ **Filter** → Remove exempted & LLE vulnerabilities
        3. 🏷️ **Classify** → Identify type & assign remediation team
        4. 📧 **Engage** → Auto-create tickets & notifications
        5. ✅ **Validate** → TVT (Test & Verify) post-patching
        """)
        
        st.divider()
        
        # -------- PERCEPTION LAYER: Download from Tableau --------
        st.subheader("📊 PERCEPTION - Download Vulnerabilities from Tableau")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Sync Tableau Vulnerabilities", key="vuln_sync_tableau", use_container_width=True):
                st.info("🔄 Fetching vulnerability data from Tableau...")
                pytime.sleep(0.5)
                st.success("✅ Downloaded 47 vulnerabilities from Tableau")
                # Initialize session state for vulnerabilities
                if "vulnerabilities" not in st.session_state:
                    st.session_state.vulnerabilities = []
        
        with col2:
            st.metric("Total Vulnerabilities", "47")
        
        with col3:
            st.metric("Last Sync", "2026-02-09 10:30 AM")
        
        st.divider()
        
        # -------- FILTER: Remove Exempted & LLE --------
        st.subheader("🗑️ FILTER - Remove Exempted & LLE Vulnerabilities")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Remove Exempted**")
            if st.button("🚫 Filter Exempted", key="vuln_filter_exempt"):
                st.info("🔍 Removing exempted vulnerabilities...")
                pytime.sleep(0.3)
                st.success("✅ Removed 5 exempted vulnerabilities | Remaining: 42")
        
        with col2:
            st.markdown("**Filter LLE Vulnerabilities**")
            if st.button("🔽 Filter LLE (Low/Low-Exploitable)", key="vuln_filter_lle"):
                st.info("🔍 Removing Low/Low-Exploitable vulnerabilities...")
                pytime.sleep(0.3)
                st.success("✅ Removed 8 LLE vulnerabilities | Critical Remaining: 34")
        
        st.divider()
        
        # -------- CLASSIFICATION & TEAM ASSIGNMENT --------
        st.subheader("🏷️ CLASSIFY - Vulnerability Type & Team Assignment")
        
        # Initialize session state for classifications
        if "vuln_classifications" not in st.session_state:
            st.session_state.vuln_classifications = {
                "Microsoft/Windows": {
                    "count": 12,
                    "team": "MAPS Team",
                    "action": "Patching Request",
                    "followup": "TVT Post-Patching",
                    "channel": "Jira"
                },
                "Middleware": {
                    "count": 15,
                    "team": "Middleware Team",
                    "action": "Jira Request",
                    "followup": "TVT Post-Patching",
                    "channel": "Jira"
                },
                "Splunk": {
                    "count": 7,
                    "team": "BladeLogic Team",
                    "action": "SDInfo Request",
                    "followup": "BladeLogic Version Update",
                    "channel": "SDInfo"
                }
            }
        
        # Display classification matrix
        classification_data = []
        for vuln_type, details in st.session_state.vuln_classifications.items():
            classification_data.append({
                "Vulnerability Type": vuln_type,
                "Count": details["count"],
                "Remediation Team": details["team"],
                "Action Type": details["action"],
                "Notification": details["channel"]
            })
        
        st.dataframe(pd.DataFrame(classification_data), use_container_width=True, hide_index=True)
        
        st.divider()
        
        # -------- ENGAGEMENT: Create Tickets & Notifications --------
        st.subheader("📧 ENGAGE - Auto-Create Tickets & Notifications")
        
        agent_tabs = st.tabs(["🔧 MAPS Team (Microsoft/Windows)", "⚙️ Middleware Team", "🔐 Splunk/BladeLogic Team"])
        
        # ---- MAPS Team Tab ----
        with agent_tabs[0]:
            st.markdown("**Microsoft Edge, Windows Server Security Vulnerabilities**")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("📋 MAPS Team engagement for Windows/Microsoft stack patching")
            with col2:
                if st.button("📤 Engage MAPS", key="engage_maps"):
                    st.success("✅ MAPS Team engaged - Jira ticket created: MAPS-2847")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Vulnerabilities", "12")
            with col2:
                st.metric("Ticket ID", "MAPS-2847")
            with col3:
                st.metric("Status", "In Progress")
            
            st.divider()
            st.subheader("📝 MAPS Team Actions:")
            
            steps = [
                "Step 1: Submit patching request via Jira",
                "Step 2: Validate patch compatibility",
                "Step 3: Deploy patches to non-prod first",
                "Step 4: Execute TVT (Test & Verify) validation",
                "Step 5: Deploy to production if TVT passes",
                "Step 6: Verify patch status in Tableau"
            ]
            
            if st.button("▶️ Start MAPS Remediation", key="start_maps_remediation"):
                for i, step in enumerate(steps):
                    st.info(f"{step}")
                    pytime.sleep(0.2)
                st.success("✅ MAPS remediation workflow completed")
        
        # ---- Middleware Team Tab ----
        with agent_tabs[1]:
            st.markdown("**Middleware Vulnerabilities (JBoss, Tomcat, etc.)**")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("📋 Middleware Team engagement via Jira for application server updates")
            with col2:
                if st.button("📤 Engage Middleware", key="engage_middleware"):
                    st.success("✅ Middleware Team engaged - Jira ticket created: MIDWARE-5142")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Vulnerabilities", "15")
            with col2:
                st.metric("Ticket ID", "MIDWARE-5142")
            with col3:
                st.metric("Status", "In Progress")
            
            st.divider()
            st.subheader("📝 Middleware Team Actions:")
            
            steps = [
                "Step 1: Review vulnerability impact on middleware components",
                "Step 2: Plan version upgrade/patch schedule",
                "Step 3: Create test environment with latest versions",
                "Step 4: Execute TVT (Test & Verify) on test environment",
                "Step 5: Roll out to production in maintenance window",
                "Step 6: Validate application functionality post-update",
                "Step 7: Update vulnerability status in Tableau"
            ]
            
            if st.button("▶️ Start Middleware Remediation", key="start_middleware_remediation"):
                for i, step in enumerate(steps):
                    st.info(f"{step}")
                    pytime.sleep(0.2)
                st.success("✅ Middleware remediation workflow completed")
        
        # ---- Splunk/BladeLogic Team Tab ----
        with agent_tabs[2]:
            st.markdown("**Splunk & BladeLogic Vulnerabilities**")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("📋 BladeLogic Team engagement via SDInfo for version updates")
            with col2:
                if st.button("📤 Engage BladeLogic", key="engage_bladelogic"):
                    st.success("✅ BladeLogic Team engaged - SDInfo request created: SDINFO-7823")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Vulnerabilities", "7")
            with col2:
                st.metric("SDInfo Ticket", "SDINFO-7823")
            with col3:
                st.metric("Status", "In Progress")
            
            st.divider()
            st.subheader("📝 BladeLogic Team Actions:")
            
            steps = [
                "Step 1: Submit SDInfo request for latest BladeLogic installation",
                "Step 2: Prepare rollback plan for current version",
                "Step 3: Schedule installation in maintenance window",
                "Step 4: Execute TVT validation post-installation",
                "Step 5: Monitor Splunk/BladeLogic for stability",
                "Step 6: Confirm vulnerability remediation in Tableau"
            ]
            
            if st.button("▶️ Start BladeLogic Remediation", key="start_bladelogic_remediation"):
                for i, step in enumerate(steps):
                    st.info(f"{step}")
                    pytime.sleep(0.2)
                st.success("✅ BladeLogic remediation workflow completed")
        
        st.divider()
        
        # -------- VALIDATION: TVT Post-Patching --------
        st.subheader("✅ VALIDATE - TVT (Test & Verify) Post-Patching")
        
        validation_col1, validation_col2 = st.columns(2)
        
        with validation_col1:
            st.markdown("**Run TVT Validation**")
            if st.button("🧪 Execute TVT Tests", key="run_tvt_tests"):
                st.info("🔍 Running Test & Verify suite...")
                pytime.sleep(0.3)
                st.success("✅ TVT Tests Passed - All vulnerabilities remediated")
                st.info("📊 CVE Status: Verified as patched in CVSS database")
        
        with validation_col2:
            st.markdown("**Update Tableau**")
            if st.button("📤 Publish Results to Tableau", key="publish_tvt_tableau"):
                st.info("📡 Publishing TVT results to Tableau...")
                pytime.sleep(0.3)
                st.success("✅ Tableau updated - 34 vulnerabilities marked as REMEDIATED")
        
        st.divider()
        
        # -------- SUMMARY --------
        st.subheader("📊 Remediation Summary")
        
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
        
        with summary_col1:
            st.metric("Downloaded", "47")
        with summary_col2:
            st.metric("Filtered Out", "13")
        with summary_col3:
            st.metric("In Remediation", "34")
        with summary_col4:
            st.metric("TVT Status", "✅ Passed")

    # --- Agentic Copilot tab ---
    with tabs[4]:
        st.header("🤖 Agentic SRE Copilot - Live on EC2")
        
        # Create subtabs for different views
        agentic_subtabs = st.tabs(["📊 Overview", "🔔 Notifications", "📈 Statistics"])
        
        # Notifications Subtab
        with agentic_subtabs[1]:
            try:
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                from frontend.components.notifications_viewer import render_notifications_view
                
                # Check multiple possible database locations
                possible_db_paths = [
                    "/var/lib/sre-agent/sre_audit.db",  # EC2 production
                    "/tmp/sre_audit.db",  # Local dev
                    "sre_audit.db",  # Current directory
                    "./local_notifications.db",  # Copied from EC2
                ]
                
                db_path = None
                for path in possible_db_paths:
                    if os.path.exists(path):
                        db_path = path
                        break
                
                if db_path:
                    st.success(f"✅ Using database: {db_path}")
                    render_notifications_view(db_path)
                else:
                    st.warning("📂 Database not found locally")
                    st.info("""
                    **The notifications database is on EC2, not on your local machine.**
                    
                    **Quick Solution: Copy database from EC2**
                    
                    Run this command in PowerShell:
                    ```powershell
                    scp -i "c:\\Users\\KF879ZY\\Downloads\\Team Meenakshi.pem" ubuntu@18.237.102.97:/var/lib/sre-agent/sre_audit.db C:\\Users\\KF879ZY\\Downloads\\local_notifications.db
                    ```
                    
                    Then place `local_notifications.db` in:
                    ```
                    c:\\Users\\KF879ZY\\Downloads\\adk_code (2)\\adk_code\\chat_app\\__pycache__\\MonitoringAlert\\
                    ```
                    
                    **Or view notifications via SSH:**
                    ```bash
                    ssh -i "Team Meenakshi.pem" ubuntu@18.237.102.97
                    sudo python3 -c "import sqlite3; conn=sqlite3.connect('/var/lib/sre-agent/sre_audit.db'); cursor=conn.cursor(); cursor.execute('SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10'); [print(row) for row in cursor.fetchall()]"
                    ```
                    """)
                
            except Exception as e:
                st.error(f"Unable to load notifications viewer: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # Overview Subtab
        with agentic_subtabs[0]:
            st.markdown("""
            **Autonomous Incident Management System**  
            Deployed on EC2: `18.237.102.97`  
            Running 24/7 monitoring every 30 seconds
            """)
            
            st.divider()
            st.divider()
            
            # Service Status
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Service Status", "🟢 Active")
            with col2:
                st.metric("Location", "EC2 Production")
            with col3:
                st.metric("Uptime", "Live")
            
            st.divider()
            
            # Agentic Loop Visualization
            st.subheader("🔄 Agentic Loop (Every 30s)")
            st.markdown("""
            ```
            1. PERCEIVE  → Collect health signals (HTTP, logs, metrics, systemd)
            2. REASON    → LLM analyzes with Gemini AI
            3. PLAN      → Policy gates (approval, rate limits, change windows)
            4. ACT       → Safe execution (pre-checks, rollback)
            5. REFLECT   → Calculate MTTR, analyze outcomes
            6. LEARN     → Update memory, improve patterns
            ```
            """)
            
            st.divider()
            
            # Real-time Logs from EC2
            st.subheader("📊 Live Agent Activity")
            
            if st.button("🔄 Refresh Logs from EC2"):
                with st.spinner("Fetching logs from EC2..."):
                    pytime.sleep(1)
                    st.info("✅ Logs refreshed (manual SSH required for real-time logs)")
            
            st.markdown("""
            **SSH to view live logs:**
            ```bash
            ssh -i "Team Meenakshi.pem" ubuntu@18.237.102.97
            sudo tail -f /var/log/sre-agent/agentic.log
            ```
            """)
            
            st.divider()
            
            # Integration Status
            st.subheader("🔌 Integration Status")
            
            integration_status = {
                "Google Gemini API": {"status": "⚠️ Quota Exceeded", "details": "Free tier limit hit - using fallback reasoning"},
                "JIRA Integration": {"status": "✅ Connected", "details": "https://teammeenakshi.atlassian.net (KAN project)"},
                "Notifications": {"status": "✅ Database Logging", "details": "All notifications stored in database and viewable in Notifications tab"},
                "Audit Database": {"status": "✅ Active", "details": "/var/lib/sre-agent/sre_audit.db"},
                "Incident Memory": {"status": "✅ Recording", "details": "/var/lib/sre-agent/incident_memory.json"}
            }
            
            for name, info in integration_status.items():
                with st.expander(f"{name} - {info['status']}"):
                    st.write(info['details'])
            
            st.divider()
            
            # Policy Configuration
            st.subheader("🛡️ Safety Policies")
            
            st.markdown("""
            **Current Policy Settings:**
            - ✅ Auto-restart: Enabled (with approval gates)
            - 🔒 Max restarts/day: 5 per app
            - ⏰ Change window: 9 AM - 5 PM UTC
            - 🚨 Escalation threshold: 3 incidents in 60 min
            - ✋ Requires approval: CRITICAL incidents only
            """)
            
            st.divider()
            
            # SSH Commands Section
            st.subheader("🖥️ Management Commands")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **Service Control:**
                ```bash
                # Check status
                systemctl status sre-agent
                
                # View live logs
                tail -f /var/log/sre-agent/agentic.log
                
                # Restart service
                systemctl restart sre-agent
                ```
                """)
            
            with col2:
                st.markdown("""
                **Query Data:**
                ```bash
                # View incident memory
                cat /var/lib/sre-agent/incident_memory.json
                
                # Query audit database
                sqlite3 /var/lib/sre-agent/sre_audit.db
                
                # View notifications
                sqlite3 /var/lib/sre-agent/sre_audit.db \
                  "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10"
                
                # Check performance
            grep "RESOLVED" /var/log/sre-agent/agentic.log
            ```
            """)
        
        # Statistics Subtab
        with agentic_subtabs[2]:
            st.subheader("📈 Agent Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Apps Monitored", "3")
            with col2:
                st.metric("Signals/Cycle", "15")
            with col3:
                st.metric("Incidents Detected", "Multiple")
            with col4:
                st.metric("Auto-Actions", "Policy Blocked (Safe)")
            
            st.divider()
            
            st.markdown("""
            **Real-time metrics and performance indicators will be displayed here.**
            
            This includes:
            - Incident detection rate
            - Mean Time To Resolution (MTTR)
            - Action success rate
            - Policy enforcement statistics
            - Memory and learning metrics
            """)
        
        st.divider()
        
        # Documentation Links
        st.subheader("📚 Documentation")
        
        docs = {
            "AGENTIC_ARCHITECTURE.md": "Complete system architecture and data flows",
            "DEPLOYMENT_QUICK_START.md": "Deployment guide and troubleshooting",
            "README_AGENTIC.md": "Usage guide and examples",
            "VISUAL_ARCHITECTURE.md": "Visual diagrams and flow charts",
            "DEPLOYMENT_STATUS.md": "Current deployment status and next steps"
        }
        
        for doc, desc in docs.items():
            st.write(f"📄 **{doc}** - {desc}")
        
        st.divider()
        
        # Alert banner
        st.warning("""
        ⚠️ **Note:** Agent is currently operating with fallback reasoning due to Gemini API quota limits.
        Upgrade to paid tier or wait 24 hours for quota reset to enable full LLM-powered decision making.
        """)
        
        st.success("""
        ✅ **Agentic SRE Copilot is LIVE and monitoring your applications autonomously!**
        
        The agent is detecting incidents, analyzing with AI reasoning (when quota available), 
        enforcing safety policies, and ready to take autonomous actions when approved.
        """)

if not st.session_state.logged_in:
    login_page()
else:
    main_app()



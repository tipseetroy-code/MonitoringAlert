import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="SSL Certificate & Vault Management POC",
    layout="wide",
    page_icon="🔐"
)

# Sample vault operations (mock)
class VaultManager:
    """Mock HashiCorp Vault Manager"""
    
    def __init__(self):
        self.vault_url = "https://vault.example.com:8200"
        self.token = "s.mock_token_demo"
        self.mounted = True
    
    def store_certificate(self, domain, cert_data):
        """Store certificate in vault"""
        vault_path = f"secret/ssl/{domain}"
        
        # Mock vault storage
        payload = {
            "certificate": cert_data.get("cert", ""),
            "private_key": cert_data.get("key", ""),
            "chain": cert_data.get("chain", ""),
            "stored_at": datetime.now().isoformat(),
            "expiry": cert_data.get("expiry", "")
        }
        
        return True, vault_path
    
    def retrieve_certificate(self, domain):
        """Retrieve certificate from vault"""
        vault_path = f"secret/ssl/{domain}"
        
        # Mock retrieval
        return {
            "certificate": f"-----BEGIN CERTIFICATE-----\nMOCK_CERT_FOR_{domain}\n-----END CERTIFICATE-----",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK_KEY\n-----END PRIVATE KEY-----",
            "retrieved_at": datetime.now().isoformat()
        }

def check_ssl_status(domain):
    """Check SSL certificate status for a domain"""
    try:
        # Mock SSL check (in production, use OpenSSL or cryptography library)
        import random
        
        days_remaining = random.randint(-100, 400)
        
        if days_remaining < 0:
            status = "Expired"
        elif days_remaining < 30:
            status = "Expiring Soon"
        else:
            status = "Valid"
        
        expiry_date = (datetime.now() + timedelta(days=days_remaining)).strftime("%Y-%m-%d")
        
        return {
            "domain": domain,
            "status": status,
            "expiry": expiry_date,
            "days_remaining": days_remaining,
            "issuer": "Let's Encrypt",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return None

def renew_certificate(domain):
    """Renew SSL certificate"""
    steps = []
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Checking current certificate for {domain}")
    time.sleep(0.5)
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Generating new CSR (Certificate Signing Request)")
    time.sleep(0.5)
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Requesting certificate from CA (Let's Encrypt)")
    time.sleep(0.5)
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Certificate issued successfully")
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Installing certificate on server")
    time.sleep(0.5)
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Restarting web server (nginx/apache)")
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Verifying SSL handshake")
    time.sleep(0.5)
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Certificate renewed successfully!")
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] New expiry date: {(datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')}")
    
    return steps

def vault_certificate(domain, vault_manager):
    """Vault SSL certificate"""
    steps = []
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Retrieving certificate from server: {domain}")
    time.sleep(0.5)
    
    cert_data = {
        "cert": f"-----BEGIN CERTIFICATE-----\nCERT_DATA_FOR_{domain}\n-----END CERTIFICATE-----",
        "key": "-----BEGIN PRIVATE KEY-----\nKEY_DATA\n-----END PRIVATE KEY-----",
        "chain": "-----BEGIN CERTIFICATE-----\nINTERMEDIATE_CERT\n-----END CERTIFICATE-----",
        "expiry": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    }
    
    steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Encrypting certificate data")
    time.sleep(0.5)
    
    success, vault_path = vault_manager.store_certificate(domain, cert_data)
    
    if success:
        steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Certificate stored in vault")
        steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Vault path: {vault_path}")
        steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Updating access policies")
        time.sleep(0.5)
        steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] Restarting application with vault reference")
        steps.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Vaulting complete - Certificate secured")
    
    return steps, vault_path

# Main App
st.title("🔐 SSL Certificate & Vault Management - POC")

st.markdown("""
**Features:**
- 📊 Load certificates from CSV
- 🔍 Real-time SSL status checking
- 🔄 Certificate renewal automation
- 🔒 HashiCorp Vault integration (mock)
- ⚙️ Automated certificate rotation
""")

# Initialize vault manager
if "vault_manager" not in st.session_state:
    st.session_state.vault_manager = VaultManager()

# Initialize certificates
if "certificates" not in st.session_state:
    try:
        df = pd.read_csv("ssl_certificates.csv")
        st.session_state.certificates = df
    except:
        st.session_state.certificates = pd.DataFrame()

tabs = st.tabs(["📊 Certificate Dashboard", "🔄 Renew SSL", "🔒 Vault Certificate", "🔍 Check Status"])

# Tab 1: Dashboard
with tabs[0]:
    st.header("SSL Certificate Dashboard")
    
    if not st.session_state.certificates.empty:
        # Summary metrics
        total_certs = len(st.session_state.certificates)
        expired = len(st.session_state.certificates[st.session_state.certificates['Status'] == 'Expired'])
        expiring_soon = len(st.session_state.certificates[st.session_state.certificates['Status'] == 'Expiring Soon'])
        valid = len(st.session_state.certificates[st.session_state.certificates['Status'] == 'Valid'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Certificates", total_certs)
        with col2:
            st.metric("✅ Valid", valid, delta=f"+{valid}")
        with col3:
            st.metric("⚠️ Expiring Soon", expiring_soon, delta=f"-{expiring_soon}" if expiring_soon > 0 else "")
        with col4:
            st.metric("❌ Expired", expired, delta=f"-{expired}" if expired > 0 else "")
        
        st.divider()
        
        # Certificate table
        st.subheader("Certificate Details")
        
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=st.session_state.certificates['Status'].unique(),
                default=st.session_state.certificates['Status'].unique()
            )
        with col2:
            search_domain = st.text_input("Search Domain", placeholder="e.g., example.com")
        
        # Apply filters
        filtered_df = st.session_state.certificates[st.session_state.certificates['Status'].isin(status_filter)]
        if search_domain:
            filtered_df = filtered_df[filtered_df['Domain'].str.contains(search_domain, case=False)]
        
        # Display table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "Domain": st.column_config.TextColumn("Domain", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Expiry": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD"),
                "DaysRemaining": st.column_config.NumberColumn("Days Left", format="%d days"),
                "VaultLocation": st.column_config.TextColumn("Vault Path", width="large")
            }
        )
        
        # Export option
        if st.button("📥 Export Certificate Report"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"ssl_certificates_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.warning("No certificates loaded. Please upload ssl_certificates.csv")

# Tab 2: Renew SSL
with tabs[1]:
    st.header("🔄 SSL Certificate Renewal")
    
    st.markdown("""
    **Automated SSL Renewal Process:**
    1. Check current certificate status
    2. Generate new CSR
    3. Request certificate from CA
    4. Install on server
    5. Restart services
    6. Verify SSL handshake
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        domain_to_renew = st.text_input(
            "Domain to Renew",
            placeholder="example.com",
            key="renew_domain"
        )
    
    with col2:
        ca_provider = st.selectbox(
            "Certificate Authority",
            ["Let's Encrypt", "DigiCert", "GlobalSign", "Comodo"]
        )
    
    if st.button("🚀 Start Renewal Process", type="primary", use_container_width=True):
        if domain_to_renew:
            with st.spinner("Renewing certificate..."):
                renewal_steps = renew_certificate(domain_to_renew)
                
                st.success(f"✅ Certificate renewed for {domain_to_renew}")
                
                st.subheader("Renewal Process Log")
                for step in renewal_steps:
                    if "✅" in step:
                        st.success(step)
                    else:
                        st.info(step)
                
                # Auto-vault option
                if st.checkbox("🔒 Auto-vault renewed certificate"):
                    vault_steps, vault_path = vault_certificate(domain_to_renew, st.session_state.vault_manager)
                    st.subheader("Vaulting Process")
                    for step in vault_steps:
                        if "✅" in step:
                            st.success(step)
                        else:
                            st.info(step)
        else:
            st.error("Please enter a domain name")

# Tab 3: Vault Certificate
with tabs[2]:
    st.header("🔒 Vault Certificate Management")
    
    st.markdown("""
    **HashiCorp Vault Integration:**
    - Secure storage for SSL certificates
    - Encrypted private keys
    - Access control policies
    - Audit logging
    - Automatic rotation support
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Store Certificate")
        
        domain_to_vault = st.text_input(
            "Domain",
            placeholder="secure.example.com",
            key="vault_domain"
        )
        
        if st.button("🔒 Vault Certificate", use_container_width=True):
            if domain_to_vault:
                with st.spinner("Vaulting certificate..."):
                    vault_steps, vault_path = vault_certificate(domain_to_vault, st.session_state.vault_manager)
                    
                    st.success(f"✅ Certificate vaulted for {domain_to_vault}")
                    
                    for step in vault_steps:
                        if "✅" in step:
                            st.success(step)
                        else:
                            st.info(step)
                    
                    st.code(f"Vault Path: {vault_path}", language="bash")
            else:
                st.error("Please enter a domain")
    
    with col2:
        st.subheader("Retrieve Certificate")
        
        domain_to_retrieve = st.text_input(
            "Domain to Retrieve",
            placeholder="example.com",
            key="retrieve_domain"
        )
        
        if st.button("📥 Retrieve from Vault", use_container_width=True):
            if domain_to_retrieve:
                with st.spinner("Retrieving from vault..."):
                    time.sleep(1)
                    cert_data = st.session_state.vault_manager.retrieve_certificate(domain_to_retrieve)
                    
                    st.success(f"✅ Certificate retrieved for {domain_to_retrieve}")
                    
                    st.code(cert_data["certificate"], language="text")
                    st.caption(f"Retrieved at: {cert_data['retrieved_at']}")
            else:
                st.error("Please enter a domain")

# Tab 4: Check Status
with tabs[3]:
    st.header("🔍 Real-time SSL Status Check")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        domain_to_check = st.text_input(
            "Domain to Check",
            placeholder="www.example.com",
            key="check_domain"
        )
    
    with col2:
        st.write("")
        st.write("")
        check_button = st.button("🔍 Check SSL", use_container_width=True)
    
    if check_button:
        if domain_to_check:
            with st.spinner("Checking SSL certificate..."):
                time.sleep(1)
                result = check_ssl_status(domain_to_check)
                
                if result:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        status_icon = "✅" if result["status"] == "Valid" else ("⚠️" if result["status"] == "Expiring Soon" else "❌")
                        st.metric("Status", f"{status_icon} {result['status']}")
                    
                    with col2:
                        st.metric("Expiry Date", result["expiry"])
                    
                    with col3:
                        delta_text = f"+{result['days_remaining']}" if result['days_remaining'] > 0 else f"{result['days_remaining']}"
                        st.metric("Days Remaining", result["days_remaining"], delta=delta_text)
                    
                    with col4:
                        st.metric("Issuer", result["issuer"])
                    
                    st.divider()
                    
                    # Recommendations
                    if result["status"] == "Expired":
                        st.error(f"⚠️ **Action Required:** Certificate has expired! Renew immediately.")
                        if st.button("🔄 Renew Now"):
                            st.switch_page
                    elif result["status"] == "Expiring Soon":
                        st.warning(f"⚠️ **Warning:** Certificate expires in {result['days_remaining']} days. Plan renewal.")
                    else:
                        st.success(f"✅ Certificate is valid for {result['days_remaining']} more days.")
        else:
            st.error("Please enter a domain")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Vault Settings")
    vault_url = st.text_input("Vault URL", value="https://vault.example.com:8200")
    vault_token = st.text_input("Vault Token", value="s.mock_token", type="password")
    
    st.divider()
    
    st.subheader("📊 Quick Stats")
    if not st.session_state.certificates.empty:
        st.metric("Vaulted Certificates", len(st.session_state.certificates[st.session_state.certificates['VaultLocation'] != 'Not Vaulted']))
        st.metric("Pending Vaulting", len(st.session_state.certificates[st.session_state.certificates['VaultLocation'] == 'Not Vaulted']))
    
    st.divider()
    
    if st.button("🔄 Reload Certificates"):
        st.rerun()

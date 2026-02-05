# SSL Certificate & Vault Management - Standard Operating Procedures

## 1. SSL Certificate Renewal SOP

### Overview
This SOP describes the process for renewing SSL/TLS certificates to prevent service interruption from expired certificates.

### Prerequisites
- Access to domain registrar/hosting provider
- Access to certificate authority account (Let's Encrypt, DigiCert, etc.)
- SSH access to production servers
- Administrator privileges on web servers (nginx/apache)

### Step-by-Step Process

#### Step 1: Check Current Certificate Status
```bash
# Check certificate expiry
openssl x509 -in /path/to/cert.pem -noout -dates

# Or via domain
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
```

**Expected Output:**
- `notBefore=Jan 15 12:00:00 2025 GMT`
- `notAfter=Jan 15 12:00:00 2026 GMT`

#### Step 2: Generate Certificate Signing Request (CSR)
```bash
# Generate private key and CSR
openssl req -new -newkey rsa:2048 -nodes -keyout domain.key -out domain.csr \
  -subj "/C=US/ST=State/L=City/O=Company/CN=example.com"

# View CSR
cat domain.csr
```

#### Step 3: Request Certificate from CA
**For Let's Encrypt (Certbot):**
```bash
sudo certbot certonly --standalone -d example.com -d www.example.com
```

**For Commercial CAs:**
1. Log in to CA account
2. Upload CSR from Step 2
3. Complete domain validation (DNS/Email)
4. Download certificate

#### Step 4: Install Certificate on Server

**For nginx:**
```bash
# Copy certificate and key to nginx config directory
sudo cp /path/to/new/cert.crt /etc/nginx/ssl/example.com.crt
sudo cp /path/to/new/private.key /etc/nginx/ssl/example.com.key

# Set correct permissions
sudo chmod 600 /etc/nginx/ssl/example.com.key
sudo chown nginx:nginx /etc/nginx/ssl/example.com.*

# Update nginx config
```
**For Apache:**
```bash
# Copy certificate and key
sudo cp /path/to/new/cert.crt /etc/apache2/ssl/example.com.crt
sudo cp /path/to/new/private.key /etc/apache2/ssl/example.com.key

# Update Apache config

#### Step 5: Verify Configuration
```bash
# For nginx
sudo nginx -t

# For Apache
sudo apachectl configtest
```

**Expected Output:** `syntax is ok` or `Syntax OK`

#### Step 6: Restart Web Server

**For nginx:**
```bash
sudo systemctl restart nginx
```

**For Apache:**
```bash
sudo systemctl restart apache2
```

# Test SSL connection
openssl s_client -connect example.com:443 -servername example.com

# https://www.ssllabs.com/ssltest/analyze.html?d=example.com
```
- Certificate chain displays correctly

#### Step 8: Update DNS/CAA Records (if required)
```bash
# Verify CAA records allow your CA
dig example.com CAA

# Expected output shows your CA is authorized
# e.g., IN CAA 0 issue "letsencrypt.org"
```

#### Step 9: Notify Team
- Send notification to team@example.com
- Subject: "SSL Certificate Renewed - example.com"
- Include: New expiry date, validation results

#### Step 10: Update Monitoring/Alerts
```bash
# Update monitoring configuration
# Update certificate tracking in your SSL management dashboard
# Update renewal reminders (typically 30 days before expiry)
```

### Troubleshooting

| Issue | Resolution |
|-------|-----------|
| CSR validation fails | Verify domain ownership, check registrar settings |
| Certificate installation error | Verify file permissions, check config syntax |
| SSL connection fails | Ensure firewall allows 443, check web server logs |
| Mixed content warnings | Update http→https redirects in config |
| Certificate chain incomplete | Ensure intermediate certificates are included |

### Rollback Plan
```bash
# If new certificate causes issues, revert to old certificate
sudo cp /path/to/old/cert.crt /etc/nginx/ssl/example.com.crt
sudo cp /path/to/old/private.key /etc/nginx/ssl/example.com.key
sudo systemctl restart nginx
```

### Timeline
- **T-60 days:** Identify certificates expiring soon
- **T-30 days:** Begin renewal process
- **T-7 days:** Test renewal in staging environment
- **T-1 day:** Prepare production renewal
- **T-0:** Execute renewal during maintenance window

---

## 2. Certificate Vaulting SOP (HashiCorp Vault)

### Overview
This SOP describes how to securely store SSL certificates in HashiCorp Vault to centralize certificate management, enforce access control, and maintain audit trails.

### Prerequisites
- HashiCorp Vault instance running and accessible
- Vault CLI installed
- Vault token with write permissions to `secret/ssl/*` path
- SSL certificate files (cert, private key, chain)

### Step-by-Step Process

#### Step 1: Authenticate to Vault
```bash
# Authenticate with token
vault login s.your_token_here

# Or with username/password
vault login -method=userpass username=your_username
```

**Verify:**
```bash
vault token lookup
```

#### Step 2: Create SSL Secret Path
```bash
# Enable secret engine (if not already enabled)
vault secrets enable -version=2 -path=secret kv

# Verify path exists
vault secrets list
```

#### Step 3: Retrieve SSL Certificate Files
```bash
# Locate existing certificates
ls -la /etc/nginx/ssl/example.com.*

# Or generate new CSR and get certificates (see SSL Renewal SOP)
```

#### Step 4: Prepare Certificate Data
```bash
# Read certificate files
cat /etc/nginx/ssl/example.com.crt
cat /etc/nginx/ssl/example.com.key
cat /etc/nginx/ssl/example.com-chain.crt  # Intermediate certificates
```

#### Step 5: Store Certificate in Vault

**Using Vault CLI:**
```bash
# Store all certificate components
vault kv put secret/ssl/example.com \
  certificate=@/etc/nginx/ssl/example.com.crt \
  private_key=@/etc/nginx/ssl/example.com.key \
  chain=@/etc/nginx/ssl/example.com-chain.crt \
  expiry="2027-01-15" \
  domain="example.com" \
  issuer="Let's Encrypt" \
  stored_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
```

**Using Raw Text (for inline data):**
```bash
vault kv put secret/ssl/example.com \
  certificate="$(cat /etc/nginx/ssl/example.com.crt)" \
  private_key="$(cat /etc/nginx/ssl/example.com.key)" \
  chain="$(cat /etc/nginx/ssl/example.com-chain.crt)"
```

#### Step 6: Verify Certificate Storage
```bash
# List all certificates in vault
vault kv list secret/ssl/

# Read specific certificate
vault kv get secret/ssl/example.com

# Read specific field
vault kv get -field=certificate secret/ssl/example.com
```

#### Step 7: Set Access Control Policies

**Create policy file (`ssl-policy.hcl`):**
```hcl
path "secret/data/ssl/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/ssl/*" {
  capabilities = ["list", "read"]
}
```

**Apply policy:**
```bash
vault policy write ssl-team ssl-policy.hcl

# Assign policy to user/role
vault write auth/userpass/users/devops password="password" policies="ssl-team"
```

#### Step 8: Retrieve Certificate from Vault (For Application Use)

**For nginx startup script:**
```bash
#!/bin/bash

# Login to Vault
export VAULT_TOKEN=$(vault login -method=userpass username=devops password=password -format=json | jq -r '.auth.client_token')

# Retrieve certificate
vault kv get -field=certificate secret/ssl/example.com > /etc/nginx/ssl/example.com.crt
vault kv get -field=private_key secret/ssl/example.com > /etc/nginx/ssl/example.com.key
vault kv get -field=chain secret/ssl/example.com > /etc/nginx/ssl/example.com-chain.crt

# Set permissions
chmod 600 /etc/nginx/ssl/example.com.key
chown nginx:nginx /etc/nginx/ssl/example.com.*

# Restart nginx
systemctl restart nginx
```

#### Step 9: Enable Audit Logging

**Check audit status:**
```bash
vault audit list
```

**Enable file audit:**
```bash
vault audit enable file file_path=/var/log/vault-audit.log
```

**Review audit logs:**
```bash
# View who accessed certificates
tail -f /var/log/vault-audit.log | jq .

# Filter for SSL access
grep "secret/ssl" /var/log/vault-audit.log
```

#### Step 10: Configure Certificate Rotation

**Create renewal schedule:**
```bash
# Set Vault reminder for renewal
vault kv put secret/ssl/example.com renewal_date="2026-12-15"

# Create cron job for automatic checks
# 0 0 * * * /usr/local/bin/check-cert-expiry.sh
```

#### Step 11: Update Application Configuration

**Update nginx/apache config:**
```bash
# Add dynamic certificate loading from Vault
# Or use Vault Agent to automatically inject certificates

# Example with Vault Agent (vault-agent.hcl)
vault_agent {
  listener "unix" {
    address = "/tmp/vault.sock"
  }

  listener "tcp" {
    address = "127.0.0.1:8100"
  }

  cache {
    use_auto_auth_token = true
  }
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/var/run/vault/.role-id"
      secret_id_file_path = "/var/run/vault/.secret-id"
    }
  }
}

template {
  source = "/etc/vault/templates/nginx.tpl"
  destination = "/etc/nginx/ssl/certs.conf"
  command = "systemctl restart nginx"
}
```

#### Step 12: Verify End-to-End Flow

**Test complete flow:**
```bash
# 1. Authenticate
vault login

# 2. Retrieve certificate
cert=$(vault kv get -field=certificate secret/ssl/example.com)

# 3. Verify certificate validity
echo "$cert" | openssl x509 -text -noout | grep "Not After"

# 4. Confirm expiry is correct
echo "$cert" | openssl x509 -noout -dates
```

### Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Authentication fails | Verify token/credentials, check Vault status |
| Permission denied | Verify policy assignment, check ACLs |
| Certificate format error | Ensure PEM format, check line endings |
| Retrieval fails | Verify path exists, check network connectivity |
| Rotation fails | Verify cron job, check logs, test manually |

### Backup & Disaster Recovery

**Backup Vault data:**
```bash
# Enable snapshot backup
vault operator raft snapshot save /backups/vault-snapshot.snap

# List snapshots
ls -lah /backups/
```

**Restore from backup:**
```bash
# Stop Vault
systemctl stop vault

# Restore snapshot
vault operator raft snapshot restore /backups/vault-snapshot.snap

# Start Vault
systemctl start vault
```

### Security Best Practices

1. **Access Control:** Limit Vault access to authorized personnel only
2. **Audit:** Enable and regularly review audit logs
3. **Encryption:** Ensure Vault is sealed when not in use
4. **Rotation:** Rotate Vault tokens regularly
5. **Backup:** Maintain secure backups of Vault data
6. **Network:** Restrict Vault access to private network/VPN

### Performance Metrics

- **Storage Time:** < 2 seconds per certificate
- **Retrieval Time:** < 1 second per certificate
- **Audit Log Growth:** ~500 KB per 1000 operations

---

## 3. Quick Reference

### Common Commands

```bash
# SSL Renewal
sudo certbot certonly --standalone -d example.com

# Check certificate
openssl x509 -in cert.pem -text -noout

# Vault Login
vault login s.token_here

# Store Certificate
vault kv put secret/ssl/domain certificate=@cert.pem private_key=@key.pem

# Retrieve Certificate
vault kv get secret/ssl/domain

# Verify SSL
openssl s_client -connect example.com:443
```

### Contact & Escalation

- **Certificate Issues:** contact devops@example.com
- **Vault Issues:** contact vault-team@example.com
- **Emergency:** PagerDuty escalation

### Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-03 | Initial creation | DevOps Team |
| 1.1 | TBD | Updates | TBD |

# ThreatActix Production API Deployment Guide (api.threatactix.com)

Production deployment instructions for hosting the **ThreatActix Darknet Threat Intelligence API** on Ubuntu Server VM behind an Nginx reverse proxy with Let's Encrypt SSL, MongoDB, and decoupled Telethon background ingestion.

---

## Architecture Overview

```text
External Customer / SIEM / SOAR
             │
             ▼ HTTPS (Port 443)
       api.threatactix.com
             │
      [ Office Router ]
  (Port Forward 80 & 443 to Ubuntu VM)
             │
     [ Nginx Reverse Proxy ]
  (Rate limiting: 60 req/min, DDoS protection, SSL Termination)
             │
      ┌──────┴──────────────────────────┐
      ▼                                 ▼
[ FastAPI Backend ]            [ Telethon Ingestion Worker ]
(darknet-backend.service)       (darknet-worker.service)
  Port 127.0.0.1:8000             24/7 Channel Sweeping & Live Listener
      │                                 │
      └────────────────┬────────────────┘
                       ▼
              [ MongoDB Database ]
             (127.0.0.1:27017, auth)
```

---

## Step 1: DNS Configuration for `api.threatactix.com`

Log in to the DNS manager where `threatactix.com` is hosted (cPanel / GoDaddy / Cloudflare / Namecheap):
1. Navigate to **DNS Zone Editor / DNS Records**.
2. Add a new **A Record**:
   * **Name / Host**: `api` (resolves to `api.threatactix.com`)
   * **Type**: `A`
   * **Value / Points To**: `<Your Office Public IPv4 Address>`
   * **TTL**: `300` seconds (5 minutes)

---

## Step 2: Router Port Forwarding

In your office router management console (e.g., `http://192.168.1.1`):
1. Reserve a static local IP for the Ubuntu VM (e.g. `192.168.1.150`).
2. Add two Port Forwarding (Virtual Server) rules:
   * **HTTP**: External Port `80` (TCP) ➔ `<Ubuntu_VM_IP>`: Port `80`
   * **HTTPS**: External Port `443` (TCP) ➔ `<Ubuntu_VM_IP>`: Port `443`

---

## Step 3: Migrate MongoDB Threat Intelligence Data

Before cutting over, export the 108,000+ darknet messages from the Windows development environment:

### On Windows Laptop (Source):
```cmd
backend\.venv\Scripts\python.exe deployment\backup_and_restore.py export --url mongodb://localhost:27017 --db darknet_monitor --out data\backups
```
*(The export archive is created under `data/backups/darknet_monitor_backup_<timestamp>.json.gz`).*

Transfer this `.json.gz` file to your Ubuntu VM via `scp` or USB:
```bash
scp data/backups/*.json.gz username@<Ubuntu_VM_IP>:/tmp/
```

### On Ubuntu Server (Target):
```bash
cd /var/www/darknet
python3 deployment/backup_and_restore.py restore --url mongodb://localhost:27017 --db darknet_monitor --file /tmp/darknet_monitor_backup_*.json.gz --drop
```

---

## Step 4: Ubuntu Server Installation & Service Setup

On the Ubuntu Server VM:

1. **Copy project code to `/var/www/darknet`**:
   ```bash
   sudo mkdir -p /var/www/darknet
   sudo chown -R $USER:$USER /var/www/darknet
   ```

2. **Set up Python Virtual Environment**:
   ```bash
   cd /var/www/darknet/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Run Automated Nginx & Service Installer**:
   ```bash
   cd /var/www/darknet
   chmod +x deployment/setup_nginx_ubuntu.sh
   sudo bash deployment/setup_nginx_ubuntu.sh
   ```

4. **Verify Both Systemd Services Are Active**:
   ```bash
   sudo systemctl status darknet-backend
   sudo systemctl status darknet-worker
   ```

---

## Step 5: Issue Free SSL Certificate (HTTPS)

Once DNS propagation completes (`nslookup api.threatactix.com` points to your public IP), run Certbot on Ubuntu:

```bash
sudo certbot --nginx -d api.threatactix.com
```

Certbot will:
1. Validate ownership of `api.threatactix.com`.
2. Issue a trusted Let's Encrypt SSL/TLS certificate.
3. Automatically configure HTTPS on port 443 with modern ciphers and HTTP-to-HTTPS redirect.

---

## Step 6: Production Verification Suite

### 1. Local Health Check (on VM)
```bash
curl -i http://localhost/api/v1/stats
```
*Expected: HTTP 200 OK*

### 2. HTTPS Customer Threat Feed Verification (from Internet/Mobile)
```bash
curl -X GET "https://api.threatactix.com/api/v1/threats?min_level=HIGH&limit=5" \
     -H "X-API-Key: dnet_live_YOUR_CUSTOMER_KEY"
```
*Expected: HTTP 200 OK with recent darknet intelligence records*

### 3. Rate Limit Test
Send more than 20 rapid bursts:
```bash
for i in {1..25}; do curl -s -o /dev/null -w "%{http_code}\n" https://api.threatactix.com/api/v1/stats; done
```
*Expected: Initial requests return `200`, subsequent burst requests return `503 Service Temporarily Unavailable`*

### 4. Admin Endpoint Lockdown Test
```bash
curl -i https://api.threatactix.com/admin
curl -i https://api.threatactix.com/.env
```
*Expected: `403 Forbidden` or `404 Not Found` (Protected from public access)*

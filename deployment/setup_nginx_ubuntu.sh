#!/usr/bin/env bash
# ==============================================================================
# One-Click Nginx & Systemd Setup for Darknet Threat Intelligence API (Ubuntu)
# Run as root or with sudo: sudo bash deployment/setup_nginx_ubuntu.sh
# ==============================================================================

set -e

echo "=================================================================="
echo "🛡️ Setting up Nginx Reverse Proxy for Darknet API on Ubuntu"
echo "=================================================================="

# 1. Install Nginx and Certbot (for SSL)
echo "📦 Installing Nginx, Certbot, and Python Certbot plugin..."
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# 2. Copy Nginx Configuration
echo "⚙️ Configuring Nginx reverse proxy (Direct Public IP & API)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sudo cp "${SCRIPT_DIR}/nginx/darknet_api.conf" /etc/nginx/sites-available/darknet_api.conf

# 3. Enable site and disable default site
sudo ln -sf /etc/nginx/sites-available/darknet_api.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 4. Test Nginx syntax
echo "🧪 Testing Nginx configuration syntax..."
sudo nginx -t

# 5. Restart Nginx
echo "🔄 Reloading Nginx service..."
sudo systemctl restart nginx
sudo systemctl enable nginx

# 6. Copy and enable Systemd services for Backend & Ingestion Worker
if [ -f "${SCRIPT_DIR}/systemd/darknet-backend.service" ]; then
    echo "⚙️ Setting up 24/7 background service for FastAPI Backend..."
    sudo cp "${SCRIPT_DIR}/systemd/darknet-backend.service" /etc/systemd/system/darknet-backend.service
fi
if [ -f "${SCRIPT_DIR}/systemd/darknet-worker.service" ]; then
    echo "⚙️ Setting up 24/7 background service for Telethon Worker..."
    sudo cp "${SCRIPT_DIR}/systemd/darknet-worker.service" /etc/systemd/system/darknet-worker.service
fi
sudo systemctl daemon-reload
sudo systemctl enable darknet-backend || true
sudo systemctl enable darknet-worker || true

echo "=================================================================="
echo "✅ Nginx is now successfully configured and running!"
echo "➡️  Local tests: curl http://localhost/api/v1/stats"
echo "🔒 To add free SSL (HTTPS) with Let's Encrypt, run:"
echo "    sudo certbot --nginx -d api.threatactix.com"
echo "=================================================================="

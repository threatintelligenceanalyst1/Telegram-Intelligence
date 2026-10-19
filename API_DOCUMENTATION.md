# Telegram Darknet Threat Intelligence API — Developer Documentation (v1)

Welcome to the **Telegram Darknet Threat Intelligence API**. This API provides real-time access to darknet chatter, cyber threat feeds, extracted Indicators of Compromise (IOCs), and forensic threat data scraped from 28+ monitored darknet Telegram channels.

---

## 1. Quick Start & Base URL

* **Live Base URL (Production / Cloudflare Tunnel)**:  
  `https://set-represents-suggested-leader.trycloudflare.com`
* **Local LAN Base URL**:  
  `http://192.168.1.60:8000`
* **Interactive Swagger UI**:  
  `https://set-represents-suggested-leader.trycloudflare.com/docs`
* **Data Format**: `application/json` (UTF-8)

---

## 2. Authentication

Every API request requires a valid Customer API Key with the `dnet_live_` prefix.

You can provide your API key using any of the following three methods:

### Method A: HTTP Header (Recommended)
```http
X-API-Key: dnet_live_YOUR_API_KEY
```

### Method B: Bearer Token Header
```http
Authorization: Bearer dnet_live_YOUR_API_KEY
```

### Method C: URL Query Parameter (Browser & Quick Testing)
```text
https://set-represents-suggested-leader.trycloudflare.com/api/v1/stats?api_key=dnet_live_YOUR_API_KEY
```

---

## 3. Rate Limiting & Quotas

### Do we have rate limiting? **YES.**

1. **Enforced Per Key**: Every API key has a strict rate limit (typically **120 requests/minute**, or customized by the administrator).
2. **Sliding Window**: Uses a 60-second sliding window to prevent burst floods and abuse.
3. **HTTP 429 Status**: If you exceed your quota, the API responds with:
   * **Status Code**: `429 Too Many Requests`
   * **Header**: `Retry-After: <seconds>`
   * **JSON Body**:
     ```json
     {
       "detail": {
         "error": "Rate Limit Exceeded",
         "message": "Rate limit of 120 requests/minute exceeded for this API key.",
         "retry_after_seconds": 24
       }
     }
     ```

---

## 4. API Endpoints Reference

### 1. `GET /api/v1/stats` — Service Status & Message Counts
Checks API connectivity and returns total indexed darknet messages.

* **Parameters**: None
* **Sample Response (`200 OK`)**:
```json
{
  "status": "online",
  "client": "Acme Cybersecurity Corp",
  "server_time_utc": "2026-10-18T15:45:00.000000+00:00",
  "total_intercepted_messages": 108845,
  "active_monitored_channels": 28,
  "supported_formats": ["JSON", "SIEM-compatible alerts", "IOC lists"]
}
```

---

### 2. `GET /api/v1/threats` — Live Threat Intelligence Feed
Exports actionable threat alerts filtered for SIEM/SOAR/TIP systems.

* **Query Parameters**:
  * `min_level` *(optional, default: `HIGH`)*: Severity filter (`ALL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  * `sector` *(optional)*: Filter by target industry (e.g. `Banking`, `Healthcare`, `Government`).
  * `keyword` *(optional)*: Search term inside threat text or entities.
  * `limit` *(optional, default: `50`, max: `200`)*: Records per page.
  * `page` *(optional, default: `1`)*: Page number.

* **Sample Response (`200 OK`)**:
```json
{
  "status": "success",
  "count": 2,
  "page": 1,
  "limit": 50,
  "total_matches": 1420,
  "threats": [
    {
      "id": "msg_984210",
      "channel_username": "CyberThreatIntel",
      "threat_level": "CRITICAL",
      "date": "2026-10-18T14:22:00Z",
      "text": "New zero-day exploit leaked targeting banking gateway VPNs. Database dump posted below.",
      "detected_sector": "Banking / Finance",
      "iocs": ["194.26.29.112", "https://darkleak-onion.to/bank.sql"],
      "views": 4200
    }
  ]
}
```

---

### 3. `GET /api/v1/iocs` — Indicators of Compromise Feed
Exports extracted IPs, Bitcoin wallets, MD5/SHA256 hashes, and onion URLs.

* **Query Parameters**:
  * `ioc_type` *(optional, default: `ALL`)*: `ALL`, `IP`, `DOMAIN`, `URL`, `HASH`, `WALLET`.
  * `limit` *(optional, default: `100`, max: `500`)*: Maximum records.

* **Sample Response (`200 OK`)**:
```json
{
  "status": "success",
  "total_iocs": 85,
  "iocs": [
    {
      "indicator": "185.220.101.5",
      "type": "IPv4",
      "first_seen": "2026-10-18T11:00:00Z",
      "channel": "ransomware_news"
    },
    {
      "indicator": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
      "type": "Bitcoin Wallet",
      "first_seen": "2026-10-18T12:15:00Z",
      "channel": "extortion_network"
    }
  ]
}
```

---

### 4. `POST /api/v1/ioc-check` — Search Indicator in Chatter
Quick lookup to verify if an IP, domain, hash, or wallet was mentioned in darknet logs.

* **Request Body**:
```json
{
  "indicator": "194.26.29.112"
}
```
* **Sample Response (`200 OK`)**:
```json
{
  "indicator": "194.26.29.112",
  "found": true,
  "total_mentions": 4,
  "first_seen": "2026-10-17T08:20:00Z",
  "highest_threat_level": "CRITICAL"
}
```

---

### 5. Forensic Evidence & Cryptographic Verification Endpoints

#### A. `GET /api/v1/threats/{id}/evidence`
Retrieve authentic Playwright evidence capture status, SHA-256 hashes (screenshot & canonical JSON), manifest digest, and chain-of-custody audit logs.

* **Sample Response (`200 OK`)**:
```json
{
  "status": "success",
  "client": "Enterprise Security Team",
  "evidence": {
    "record_id": "ev_0b4d9fa249a5",
    "message_id": "ch1_104",
    "capture_status": "captured",
    "captured_at": "2026-10-19T10:45:00Z",
    "embed_url": "https://t.me/darknet_channel/104?embed=1",
    "screenshot_sha256": "8f3b1456a64b971a80d56b4f74d08c5c7619a9a3b6f8490a12cf6287950c4765",
    "message_sha256": "4b971a80d56b4f74d08c5c7619a9a3b6f8490a12cf6287950c47658f3b1456a6",
    "manifest_sha256": "c7619a9a3b6f8490a12cf6287950c47658f3b1456a64b971a80d56b4f74d08c5",
    "screenshot_url": "/api/v1/threats/ch1_104/evidence/screenshot",
    "bundle_url": "/api/v1/threats/ch1_104/evidence/bundle",
    "chain_of_custody": [
      {
        "log_id": "aud_19283746",
        "event": "captured",
        "actor": "system",
        "timestamp": "2026-10-19T10:45:02Z",
        "status": "captured"
      }
    ]
  }
}
```

#### B. `GET /api/v1/threats/{id}/evidence/screenshot`
Direct stream of the genuine Telegram web embed PNG image captured by headless Chromium. Content-Type: `image/png`.

#### C. `GET /api/v1/threats/{id}/evidence/verify`
Recomputes SHA-256 content hashes of the message JSON and screenshot PNG on disk. Verifies them against the immutable manifest in the evidence repository.

* **Sample Response (`200 OK`)**:
```json
{
  "status": "success",
  "client": "Enterprise Security Team",
  "verification": {
    "message_id": "ch1_104",
    "is_valid": true,
    "verified": true,
    "screenshot_hash_match": true,
    "message_hash_match": true,
    "manifest_hash_match": true,
    "verified_at": "2026-10-19T11:00:00Z",
    "audit_trail_summary": "Record verified using SHA-256 content hashes"
  }
}
```

#### D. `GET /api/v1/threats/{id}/evidence/bundle`
Downloads a self-contained, authenticated forensic ZIP bundle (`application/zip`) suitable for chain-of-custody submission in court or compliance audits. Contains:
- `screenshot.png` (genuine web render)
- `message.json` (canonical raw data)
- `manifest.json` (cryptographic fingerprints and capture metadata)
- `README.txt` (CLI verification commands for Linux, macOS, and Windows PowerShell)

#### E. `POST /api/v1/threats/{id}/evidence/recapture` (Admin Only)
Requires administrative authorization header (`X-Admin-Secret`). Forces immediate re-capture of the web embed via headless Chromium and updates the audit log.

---

## 6. Code Integration Examples


### Python (using `requests`)
```python
import requests

API_URL = "https://set-represents-suggested-leader.trycloudflare.com/api/v1/threats"
HEADERS = {
    "X-API-Key": "dnet_live_YOUR_KEY_HERE"
}
PARAMS = {
    "min_level": "HIGH",
    "limit": 20
}

response = requests.get(API_URL, headers=HEADERS, params=PARAMS)

if response.status_code == 200:
    data = response.json()
    print(f"Retrieved {len(data['threats'])} threats:")
    for threat in data["threats"]:
        print(f"[{threat['threat_level']}] {threat['channel_username']}: {threat['text'][:80]}...")
elif response.status_code == 429:
    print(f"Rate limit exceeded! Retry after {response.headers.get('Retry-After')} seconds.")
else:
    print(f"Error {response.status_code}: {response.text}")
```

---

### JavaScript / Node.js (using `axios`)
```javascript
const axios = require('axios');

async function fetchDarknetThreats() {
  try {
    const res = await axios.get('https://set-represents-suggested-leader.trycloudflare.com/api/v1/threats', {
      headers: {
        'X-API-Key': 'dnet_live_YOUR_KEY_HERE'
      },
      params: { min_level: 'CRITICAL', limit: 10 }
    });
    console.log('Total Threats:', res.data.count);
    console.log(res.data.threats);
  } catch (err) {
    if (err.response && err.response.status === 429) {
      console.error('Rate limit exceeded. Please wait.');
    } else {
      console.error('API Error:', err.message);
    }
  }
}

fetchDarknetThreats();
```

---

### cURL (Command Line / Shell Script)
```bash
curl -X GET "https://set-represents-suggested-leader.trycloudflare.com/api/v1/threats?min_level=HIGH&limit=10" \
     -H "X-API-Key: dnet_live_YOUR_KEY_HERE"
```

---

## 6. HTTP Status Codes Reference

| Code | Meaning | Explanation |
|---|---|---|
| **`200 OK`** | Success | Request was successful, JSON payload returned. |
| **`400 Bad Request`** | Invalid Request | Invalid parameters or malformed JSON body. |
| **`401 Unauthorized`** | Missing API Key | No `X-API-Key` or `Authorization` header found. |
| **`403 Forbidden`** | Invalid Key | API key does not exist or has been disabled. |
| **`429 Too Many Requests`**| Rate Limited | Exceeded allowed requests per minute. Slow down. |
| **`500 Internal Error`** | Server Error | Database or backend processing exception. |

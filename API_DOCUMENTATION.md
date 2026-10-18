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

## 5. Code Integration Examples

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

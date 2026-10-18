#!/usr/bin/env python3
"""
Darknet Threat Intelligence Client Tool
Fetches the latest 100 scraped Telegram messages using your Customer API Key.
Works from any computer or operating system across the internet.
"""

import sys
import json
import requests
from datetime import datetime

# Your Live Cloudflare API Endpoint
API_BASE_URL = "https://set-represents-suggested-leader.trycloudflare.com"
ENDPOINT = f"{API_BASE_URL}/api/v1/threats"


def main():
    print("=" * 70)
    print("🛡️  TELEGRAM DARKNET THREAT INTELLIGENCE — CLIENT FEED")
    print("=" * 70)

    # 1. Prompt for API key
    if len(sys.argv) > 1:
        api_key = sys.argv[1].strip()
    else:
        api_key = input("Enter your API Key (dnet_live_...): ").strip()

    if not api_key:
        print("❌ Error: API Key is required.")
        sys.exit(1)

    print(f"\n📡 Connecting to API Gateway: {API_BASE_URL}...")
    headers = {
        "X-API-Key": api_key,
        "User-Agent": "DarknetThreatClient/1.0"
    }
    params = {
        "min_level": "ALL",   # Get all messages regardless of severity
        "limit": 100,         # Fetch latest 100 messages
        "page": 1
    }

    try:
        response = requests.get(ENDPOINT, headers=headers, params=params, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Connection Error: {e}")
        sys.exit(1)

    # 2. Check for authentication errors
    if response.status_code == 401 or response.status_code == 403:
        error_msg = response.json().get("detail", {}).get("message", "Invalid or revoked key")
        print(f"\n❌ Authentication Failed ({response.status_code}): {error_msg}")
        sys.exit(1)
    elif response.status_code != 200:
        print(f"\n❌ API Error ({response.status_code}): {response.text}")
        sys.exit(1)

    data = response.json()
    threats = data.get("threats", [])
    total_matches = data.get("total_matches", len(threats))

    print(f"\n✅ SUCCESS! Retrieved {len(threats)} messages (Total in database: {total_matches:,})\n")
    print("-" * 70)

    # 3. Display the messages
    for idx, msg in enumerate(threats, start=1):
        level = msg.get("threat_level", "LOW")
        channel = msg.get("channel_username") or msg.get("channel_id") or "Unknown Channel"
        date_str = msg.get("date", "Unknown Date")
        text = msg.get("text", "").strip().replace("\n", " ")
        preview = (text[:120] + "...") if len(text) > 120 else text
        iocs = msg.get("iocs", [])

        # Color-coded badge for severity
        badge = f"[{level}]"
        print(f"#{idx:03d} | {badge:<10} | Channel: @{channel}")
        print(f"     Time:    {date_str}")
        print(f"     Message: {preview if preview else '[Media / Empty Message]'}")
        if iocs:
            print(f"     IOCs:    {', '.join(iocs[:5])}")
        print("-" * 70)

    # 4. Save full JSON export locally
    output_filename = "latest_100_darknet_messages.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(threats, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Saved all 100 full records with complete metadata to: {output_filename}")
    print("=" * 70)


if __name__ == "__main__":
    main()

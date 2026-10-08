import asyncio
import logging
import json
from datetime import datetime, timedelta, timezone
from ..db.mongodb import store, get_channel_dir
from ..scrapers.telegram_scraper import telegram_scraper
from ..llm.threat_analyzer import analyzer
from ..reports.report_generator import report_generator

logger = logging.getLogger("darknet_monitor.scheduler")

scheduler_active = True
IST = timezone(timedelta(hours=5, minutes=30))

def append_raw_chats_to_daily_log(channel_id: str, channel_title: str, messages: list):
    """Placeholder to maintain daily running transcript log logic without double-logging."""
    pass

async def run_mini_ai_analysis_cycle(channel_id: str):
    """Run an incremental AI analysis cycle, statefully updating daily JSON database and compiling the clean markdown report ledger."""
    ch = store.channels.get(channel_id)
    if not ch:
        return
        
    try:
        from ..config import settings
        date_str = datetime.now(IST).strftime("%Y-%m-%d")
        channel_reports_dir = get_channel_dir(channel_id, ch["title"]) / "reports"
        channel_reports_dir.mkdir(parents=True, exist_ok=True)
        
        state_path = channel_reports_dir / f"ChatLog_{channel_id}_{date_str}.state.json"
        log_path = channel_reports_dir / f"ChatLog_{channel_id}_{date_str}.md"
        
        # 1. Fetch channel messages for today that have not been analyzed in a mini-cycle yet
        msgs = [m for m in store.messages.values() if m.get("channel_id") == channel_id]
        unspent_msgs = []
        today_msgs = []
        for m in msgs:
            msg_date = m.get("date", "")
            try:
                msg_utc = datetime.fromisoformat(msg_date.replace("Z", "+00:00"))
                msg_ist = msg_utc.astimezone(IST)
                is_today = msg_ist.strftime("%Y-%m-%d") == date_str
                if is_today:
                    today_msgs.append(m)
                    if not m.get("ai_analyzed_in_cycle"):
                        unspent_msgs.append(m)
            except Exception:
                if msg_date.startswith(date_str):
                    today_msgs.append(m)
                    if not m.get("ai_analyzed_in_cycle"):
                        unspent_msgs.append(m)
                    
        if not unspent_msgs:
            logger.info(f"[Scheduler] No new messages to analyze in this cycle for '{ch['title']}'")
            return
            
        telegram_scraper.log(f"🧠 Running CTI stateful cycle analysis on {len(unspent_msgs)} messages...")
        
        # 2. Query LLM JSON extraction in separate thread
        extracted = await asyncio.to_thread(analyzer.extract_cycle_threats, unspent_msgs, ch["title"])
        
        # Check if fallback was triggered and log warning to Scraper Console
        if extracted.get("fallback_triggered"):
            telegram_scraper.log(f"⚠ Local LLM Offline/Failed: {extracted.get('fallback_reason')}. Running fallback regex threat extraction.")
            store.add_notification("warning", f"⚠ LLM Offline: Fallback CTI run for '{ch['title']}' ({len(unspent_msgs)} msgs)")
        else:
            store.add_notification("analysis", f"🧠 CTI daily ledger updated for '{ch['title']}' ({len(unspent_msgs)} msgs)")
        
        # Mark messages as analyzed in memory
        for m in unspent_msgs:
            m["ai_analyzed_in_cycle"] = True
            
        # 3. Load or Initialize existing Daily State JSON database
        state = {
            "executive_summary": "CTI automated ledger monitor active.",
            "threat_alerts": [],
            "suspicious_users": [],
            "urls": [],
            "onions": [],
            "iocs": [],
            "topics": [],
            "timeline": []
        }
        
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as rf:
                    state = json.load(rf)
            except Exception as e:
                logger.error(f"Error reading JSON state: {e}")
                
        now_time_str = datetime.now(IST).strftime("%H:%M:%S IST")
        
        # 4. Merge Extracted Threat telemetry statefully (deduplicating and incrementing counts)
        if extracted.get("executive_summary") and isinstance(extracted["executive_summary"], str):
            state["executive_summary"] = extracted["executive_summary"]
            
        if extracted.get("topics") and isinstance(extracted["topics"], list):
            for t in extracted["topics"]:
                if isinstance(t, str) and t not in state["topics"]:
                    state["topics"].append(t)
                    
        # Normalise alerts
        raw_alerts = extracted.get("threat_alerts") or []
        normalized_alerts = []
        if isinstance(raw_alerts, list):
            for alert in raw_alerts:
                if isinstance(alert, str):
                    normalized_alerts.append({"title": alert, "severity": "MEDIUM", "description": ""})
                elif isinstance(alert, dict) and alert.get("title"):
                    normalized_alerts.append({
                        "title": str(alert["title"]),
                        "severity": str(alert.get("severity") or "MEDIUM"),
                        "description": str(alert.get("description") or "")
                    })
                    
        for alert in normalized_alerts:
            found = False
            for exist in state["threat_alerts"]:
                if exist["title"].lower() == alert["title"].lower():
                    exist["count"] = exist.get("count", 1) + 1
                    exist["last_seen"] = now_time_str
                    found = True
                    break
            if not found:
                state["threat_alerts"].append({
                    "title": alert["title"],
                    "severity": alert["severity"],
                    "description": alert["description"],
                    "count": 1,
                    "last_seen": now_time_str
                })
                
        # Normalise suspicious users
        raw_users = extracted.get("suspicious_users") or []
        normalized_users = []
        if isinstance(raw_users, list):
            for user in raw_users:
                if isinstance(user, str):
                    normalized_users.append({"username": user, "malicious_context": "Flagged by AI threat scanner"})
                elif isinstance(user, dict):
                    user_val = user.get("username") or user.get("actor") or user.get("user")
                    if user_val:
                        normalized_users.append({
                            "username": str(user_val),
                            "malicious_context": str(user.get("malicious_context") or user.get("activity") or user.get("context") or "Malicious behavior detected")
                        })
                        
        for user in normalized_users:
            found = False
            for exist in state["suspicious_users"]:
                if exist["username"].lower() == user["username"].lower():
                    exist["count"] = exist.get("count", 1) + 1
                    exist["last_seen"] = now_time_str
                    exist["activity"] = user["malicious_context"]
                    found = True
                    break
            if not found:
                state["suspicious_users"].append({
                    "username": user["username"],
                    "activity": user["malicious_context"],
                    "count": 1,
                    "last_seen": now_time_str
                })
                
        # Normalise URLs
        raw_urls = extracted.get("urls") or []
        normalized_urls = []
        if isinstance(raw_urls, list):
            for item in raw_urls:
                if isinstance(item, str):
                    normalized_urls.append({"url": item, "purpose": "Web link shared in chat"})
                elif isinstance(item, dict):
                    url_val = item.get("url") or item.get("link")
                    if url_val:
                        normalized_urls.append({
                            "url": str(url_val),
                            "purpose": str(item.get("purpose") or item.get("description") or "Shared web link")
                        })
                        
        for item in normalized_urls:
            found = False
            for exist in state["urls"]:
                if exist["url"].lower() == item["url"].lower():
                    exist["count"] = exist.get("count", 1) + 1
                    exist["last_seen"] = now_time_str
                    found = True
                    break
            if not found:
                state["urls"].append({
                    "url": item["url"],
                    "purpose": item["purpose"],
                    "count": 1,
                    "last_seen": now_time_str
                })
                
        # Normalise Onions
        raw_onions = extracted.get("onions") or []
        normalized_onions = []
        if isinstance(raw_onions, list):
            for item in raw_onions:
                if isinstance(item, str):
                    normalized_onions.append({"url": item, "purpose": "Onion link shared in chat"})
                elif isinstance(item, dict):
                    url_val = item.get("url") or item.get("link") or item.get("onion")
                    if url_val:
                        normalized_onions.append({
                            "url": str(url_val),
                            "purpose": str(item.get("purpose") or item.get("description") or "Onion leak index")
                        })
                        
        for item in normalized_onions:
            found = False
            for exist in state["onions"]:
                if exist["url"].lower() == item["url"].lower():
                    exist["count"] = exist.get("count", 1) + 1
                    exist["last_seen"] = now_time_str
                    found = True
                    break
            if not found:
                state["onions"].append({
                    "url": item["url"],
                    "purpose": item["purpose"],
                    "count": 1,
                    "last_seen": now_time_str
                })
                
        # Normalise IOCs
        raw_iocs = extracted.get("iocs") or []
        normalized_iocs = []
        if isinstance(raw_iocs, list):
            for item in raw_iocs:
                if isinstance(item, str):
                    import re
                    ioc_type = "Indicator"
                    if "cve-" in item.lower():
                        ioc_type = "CVE"
                    elif re.match(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", item):
                        ioc_type = "IP"
                    normalized_iocs.append({"type": ioc_type, "value": item})
                elif isinstance(item, dict):
                    val = item.get("value") or item.get("indicator")
                    if val:
                        normalized_iocs.append({
                            "type": str(item.get("type") or "Indicator"),
                            "value": str(val)
                        })
                        
        for item in normalized_iocs:
            found = False
            for exist in state["iocs"]:
                if exist["value"].lower() == item["value"].lower():
                    exist["count"] = exist.get("count", 1) + 1
                    exist["last_seen"] = now_time_str
                    found = True
                    break
            if not found:
                state["iocs"].append({
                    "type": item["type"],
                    "value": item["value"],
                    "count": 1,
                    "last_seen": now_time_str
                })
                
        # Timeline
        for alert in normalized_alerts:
            state["timeline"].append({
                "time": now_time_str,
                "event": f"[{alert['severity']}] {alert['title']} - {alert['description']}"
            })
            
        # Save daily state database JSON
        with open(state_path, "w", encoding="utf-8") as wf:
            json.dump(state, wf, indent=2)
            
        # 5. Compile Markdown daily report layout
        md_lines = [
            f"# 🛡️ Cyber Threat Intelligence Daily Report: {ch['title']}",
            f"**Date:** {date_str}",
            f"**Channel ID:** {channel_id}",
            "",
            "## 📑 1. Executive Summary",
            state["executive_summary"],
            "",
            "## 🚨 2. Threat Alerts",
        ]
        
        if state["threat_alerts"]:
            md_lines.append("| Severity | Alert Title | Description | Count | Last Seen |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for alert in state["threat_alerts"]:
                md_lines.append(f"| **{alert['severity']}** | {alert['title']} | {alert['description']} | {alert['count']} | {alert['last_seen']} |")
        else:
            md_lines.append("_No critical threat alerts flagged today._")
            
        md_lines.append("\n## 🌐 3. Shared URLs")
        if state["urls"]:
            md_lines.append("| URL Link | Domain Purpose | Mention Count | Last Seen |")
            md_lines.append("| :--- | :--- | :--- | :--- |")
            for url in state["urls"]:
                md_lines.append(f"| [{url['url']}]({url['url']}) | {url['purpose']} | {url['count']} | {url['last_seen']} |")
        else:
            md_lines.append("_No standard web URLs extracted today._")
            
        md_lines.append("\n## 🧅 4. Onion Links")
        if state["onions"]:
            md_lines.append("| Onion URL | Target Purpose | Mention Count | Last Seen |")
            md_lines.append("| :--- | :--- | :--- | :--- |")
            for onion in state["onions"]:
                md_lines.append(f"| `{onion['url']}` | {onion['purpose']} | {onion['count']} | {onion['last_seen']} |")
        else:
            md_lines.append("_No onion links detected today._")
            
        md_lines.append("\n## 👤 5. Suspicious Usernames & Threat Actors")
        if state["suspicious_users"]:
            md_lines.append("| Username | Suspicious Activity Context | Mention Count | Last Seen |")
            md_lines.append("| :--- | :--- | :--- | :--- |")
            for user in state["suspicious_users"]:
                md_lines.append(f"| **{user['username']}** | {user['activity']} | {user['count']} | {user['last_seen']} |")
        else:
            md_lines.append("_No suspicious usernames flagged in this period._")
            
        md_lines.append("\n## 🛡️ 6. Indicators of Compromise (IOCs)")
        if state["iocs"]:
            md_lines.append("| IOC Type | Indicator Value | Count | Last Seen |")
            md_lines.append("| :--- | :--- | :--- | :--- |")
            for ioc in state["iocs"]:
                md_lines.append(f"| {ioc['type']} | `{ioc['value']}` | {ioc['count']} | {ioc['last_seen']} |")
        else:
            md_lines.append("_No IOCs (IPs, CVEs, Wallets) extracted today._")
            
        md_lines.append("\n## 💬 7. Key Topics Discussed")
        if state["topics"]:
            for t in state["topics"]:
                md_lines.append(f"- {t}")
        else:
            md_lines.append("_No primary topics logged yet._")
            
        md_lines.append("\n## 📈 8. Daily Statistics")
        md_lines.append(f"- **Total Suspicious Users Flagged:** {len(state['suspicious_users'])}")
        md_lines.append(f"- **Total Unique Shared Link Assets:** {len(state['urls']) + len(state['onions'])}")
        md_lines.append(f"- **Total Threat Indicators/IOCs:** {len(state['iocs'])}")
        
        md_lines.append("\n## ⏳ 9. Timeline of New Events")
        if state["timeline"]:
            for event in state["timeline"]:
                md_lines.append(f"* **{event['time']}** - {event['event']}")
        else:
            md_lines.append("_No timelines events logged today yet._")
            
        md_lines.append("\n## 📖 10. Hourly Chat Logs Transcript (Evidence Block)")
        
        # Build transcripts evidence table
        transcript_table = [
            "| Time (IST) | Sender | Chat Message Log / Post Excerpt |",
            "| :--- | :--- | :--- |"
        ]
        today_msgs.sort(key=lambda x: x.get("id"))
        for m in today_msgs:
            m_date = m.get("date", "")
            try:
                m_utc = datetime.fromisoformat(m_date.replace("Z", "+00:00"))
                m_ist = m_utc.astimezone(IST)
                m_time = m_ist.strftime("%H:%M:%S")
            except Exception:
                m_time = m_date[11:19]
            sender = m.get("sender", "unknown")
            text = m.get("text", "").replace("\n", " ").replace("|", "\\|")
            transcript_table.append(f"| {m_time} | **{sender}** | {text} |")
            
        merged_md = "\n".join(md_lines) + "\n" + "\n".join(transcript_table)
        
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(merged_md)
            
        telegram_scraper.log(f"✓ Stateful CTI Ledger updated: data/{channel_id}/reports/{log_path.name}")
    except Exception as e:
        logger.error(f"Error in stateful AI analysis cycle: {e}")
        telegram_scraper.log(f"⚠ Stateful AI Analysis cycle failed for '{ch['title']}': {e}")

async def generate_auto_report_task(channel_id: str):
    """Compiles the daily markdown log file (with all cycle analyses) into a final page-numbered PDF report."""
    ch = store.channels.get(channel_id)
    if not ch:
        return
        
    logger.info(f"[Scheduler] Generating final compiled report for '{ch['title']}'...")
    telegram_scraper.log(f"📋 Triggering final PDF report compilation for '{ch['title']}'")
    
    try:
        from ..config import settings
        date_str = datetime.now(IST).strftime("%Y-%m-%d")
        channel_reports_dir = get_channel_dir(channel_id, ch["title"]) / "reports"
        log_path = channel_reports_dir / f"ChatLog_{channel_id}_{date_str}.md"
        
        if not log_path.exists():
            telegram_scraper.log(f"⚠ PDF report skipped for '{ch['title']}': Daily log file not found.")
            return
            
        # 1. Read daily log file contents
        with open(log_path, "r", encoding="utf-8") as f:
            report_md = f.read()
            
        # 2. Get today's messages
        msgs = [m for m in store.messages.values() if m.get("channel_id") == channel_id]
        today_msgs = []
        for m in msgs:
            msg_date = m.get("date", "")
            try:
                msg_utc = datetime.fromisoformat(msg_date.replace("Z", "+00:00"))
                msg_ist = msg_utc.astimezone(IST)
                if msg_ist.strftime("%Y-%m-%d") == date_str:
                    today_msgs.append(m)
            except Exception:
                if msg_date.startswith(date_str):
                    today_msgs.append(m)
                    
        # 3. Compile PDF report using ReportLab
        timestamp_str = datetime.now(IST).strftime("%Y-%m-%d_%H%M%S")
        pdf_path = channel_reports_dir / f"AI_Report_{channel_id}_{timestamp_str}.pdf"
        
        from ..reports.pdf_generator import create_detailed_pdf_report
        
        await asyncio.to_thread(
            create_detailed_pdf_report,
            ch["title"],
            date_str,
            date_str,
            today_msgs,
            report_md,
            pdf_path
        )
        
        # 4. Save report metadata to database store
        report_id = f"rep_pdf_{timestamp_str}"
        store.reports[report_id] = {
            "id": report_id,
            "title": f"Daily Compiled PDF Report - {ch['title']}",
            "created_at": datetime.now(IST).isoformat(),
            "period": "daily_compiled",
            "channels_analyzed": [ch["title"]],
            "total_messages": len(today_msgs),
            "total_threats": 1,
            "markdown_path": str(log_path.relative_to(settings.BASE_DIR)),
            "pdf_path": str(pdf_path.relative_to(settings.BASE_DIR)),
            "summary": f"Final daily threat intelligence briefing PDF compiled for '{ch['title']}'."
        }
        
        telegram_scraper.log(f"✓ Final Daily PDF Report compiled successfully: data/{channel_id}/reports/{pdf_path.name}")
        store.add_notification("report", f"📄 PDF Report compiled for '{ch['title']}'")
    except Exception as e:
        logger.error(f"Error compiling daily PDF report: {e}")
        telegram_scraper.log(f"⚠ PDF Report compilation failed: {e}")
        store.add_notification("error", f"⚠ PDF compilation failed for '{ch['title']}': {e}")

class AutoMonitorState:
    def __init__(self):
        from ..config import settings
        self.enabled: bool = getattr(settings, "AUTO_MONITOR_24_7", True)
        self.interval_minutes: int = getattr(settings, "AUTO_MONITOR_INTERVAL_MINUTES", 1440)
        self.last_sweep_at: str = ""
        self.next_sweep_at: str = ""
        self.is_sweeping: bool = False
        self.channels_swept: int = 0
        self.total_messages_collected: int = 0
        self.last_status: str = "24/7 Autonomous Monitor active."

auto_monitor = AutoMonitorState()

def enable_all_channels_247() -> int:
    """Turn ON 24/7 monitoring, auto AI cycles, and reporting for all current channels."""
    count = 0
    for ch in store.channels.values():
        ch["is_monitored"] = True
        ch["is_auto_monitoring"] = True
        ch["monitoring_interval_value"] = 24 if auto_monitor.interval_minutes == 1440 else auto_monitor.interval_minutes
        ch["monitoring_interval_unit"] = "hours" if auto_monitor.interval_minutes == 1440 else "minutes"
        ch["is_auto_ai"] = True
        ch["ai_interval_value"] = 30
        ch["ai_interval_unit"] = "minutes"
        ch["is_auto_report"] = True
        ch["report_interval_value"] = 24
        ch["report_interval_unit"] = "hours"
        count += 1
    auto_monitor.enabled = True
    auto_monitor.last_status = f"24/7 Auto-Monitoring active across {count} channels (24h sweep interval)."
    logger.info(f"✓ Enabled 24/7 automated monitoring for all {count} channels (Sweep interval: 24h).")
    return count

def get_auto_monitor_status() -> dict:
    """Return live telemetry status of the 24/7 autonomous monitor."""
    monitored_channels = [c for c in store.channels.values() if c.get("is_monitored")]
    interval_display = "24h" if auto_monitor.interval_minutes == 1440 else (
        f"{auto_monitor.interval_minutes // 60}h" if auto_monitor.interval_minutes % 60 == 0
        else f"{auto_monitor.interval_minutes}m"
    )
    return {
        "enabled": auto_monitor.enabled,
        "interval_minutes": auto_monitor.interval_minutes,
        "interval_display": interval_display,
        "is_sweeping": auto_monitor.is_sweeping,
        "last_sweep_at": auto_monitor.last_sweep_at,
        "next_sweep_at": auto_monitor.next_sweep_at,
        "monitored_channels_count": len(monitored_channels),
        "total_channels_count": len(store.channels),
        "total_messages_collected": auto_monitor.total_messages_collected,
        "live_listener_active": telegram_scraper.live_listener_active,
        "status_message": auto_monitor.last_status
    }

async def run_247_autonomous_sweep():
    """Perform a continuous background sweep across all monitored channels without user clicks."""
    if not auto_monitor.enabled or auto_monitor.is_sweeping:
        return

    # If manual scraping is running in UI, yield to it
    if telegram_scraper.is_scraping:
        return

    channels_to_sweep = [c for c in store.channels.values() if c.get("is_monitored", True)]
    if not channels_to_sweep:
        return

    auto_monitor.is_sweeping = True
    auto_monitor.last_status = f"Sweeping {len(channels_to_sweep)} channels in background..."
    logger.info(f"🔄 Starting 24/7 auto-sweep across {len(channels_to_sweep)} channels...")

    sweep_new_msgs = 0
    channels_with_new_data = []

    try:
        for ch in channels_to_sweep:
            if not auto_monitor.enabled or not scheduler_active:
                break
            # Skip if user initiated manual scrape
            if telegram_scraper.is_scraping:
                break

            ch_id = ch["id"]
            new_msgs = await telegram_scraper.scrape_single_channel_incremental(ch)
            if new_msgs:
                sweep_new_msgs += len(new_msgs)
                channels_with_new_data.append(ch_id)

            # Polite pause to prevent Telegram flood-wait rate limits
            await asyncio.sleep(1.5)

        now = datetime.now(IST)
        auto_monitor.last_sweep_at = now.strftime("%Y-%m-%d %H:%M:%S IST")
        auto_monitor.next_sweep_at = (now + timedelta(minutes=auto_monitor.interval_minutes)).strftime("%Y-%m-%d %H:%M:%S IST")
        auto_monitor.total_messages_collected += sweep_new_msgs
        auto_monitor.channels_swept = len(channels_to_sweep)
        auto_monitor.last_status = f"Last sweep completed at {now.strftime('%H:%M:%S')} (+{sweep_new_msgs} new messages)."

        if sweep_new_msgs > 0:
            logger.info(f"✓ 24/7 Auto-Sweep complete: Ingested {sweep_new_msgs} new messages across {len(channels_with_new_data)} channels.")
            # Trigger stateful AI cycle analysis on channels that got new data
            for ch_id in channels_with_new_data:
                asyncio.create_task(run_mini_ai_analysis_cycle(ch_id))

    except Exception as e:
        logger.error(f"Error during 24/7 auto-sweep: {e}")
        auto_monitor.last_status = f"Sweep encountered error: {e}"
    finally:
        auto_monitor.is_sweeping = False

async def scrape_channel_silent(channel_id: str):
    """Scrapes a channel silently and appends raw transcripts to the daily log."""
    ch = store.channels.get(channel_id)
    if not ch:
        return
    
    logger.info(f"[Scheduler] Auto-scraping channel '{ch['title']}'...")
    telegram_scraper.log(f"⏰ Auto-scrape triggered for channel '{ch['title']}'")
    
    try:
        messages = await telegram_scraper.scrape_channels([ch])
        threat_intels = []
        
        for msg in messages:
            store.messages[msg["id"]] = msg
            intel = await asyncio.to_thread(analyzer.analyze_message, msg)
            store.threat_intel[intel["id"]] = intel
            threat_intels.append(intel)

        if messages:
            # 1. Standard telemetry report
            rep_meta = await asyncio.to_thread(
                report_generator.generate_report, 
                messages, 
                threat_intels, 
                [ch.get("username", ch.get("title"))]
            )
            store.reports[rep_meta["id"]] = rep_meta
            telegram_scraper.log(f"✓ Auto-scrape finished for '{ch['title']}'. Collected {len(messages)} messages.")
    except Exception as e:
        logger.error(f"Error during auto-scrape task for {channel_id}: {e}")

async def run_scheduler():
    """Persistent background task to scan and run 24/7 auto-sweeps, live listener checks, and AI timers."""
    global scheduler_active
    from ..config import settings
    logger.info("Initializing 24/7 automated target channel monitoring scheduler...")

    # Wait briefly for startup initializations
    await asyncio.sleep(5)

    # Auto-enable 24/7 monitoring across all channels if configured
    if getattr(settings, "AUTO_MONITOR_24_7", True):
        enable_all_channels_247()

    # Start live event listener immediately if authorized
    if getattr(settings, "LIVE_LISTENER_ENABLED", True):
        asyncio.create_task(telegram_scraper.start_live_listener())

    next_sweep_time = datetime.now(IST) + timedelta(seconds=10)
    auto_monitor.next_sweep_at = next_sweep_time.strftime("%Y-%m-%d %H:%M:%S IST")
    
    while scheduler_active:
        try:
            now = datetime.now(IST)

            # Ensure live listener is connected
            if not telegram_scraper.live_listener_active and getattr(settings, "LIVE_LISTENER_ENABLED", True):
                asyncio.create_task(telegram_scraper.start_live_listener())

            # 1. Run 24/7 Autonomous Sweep across all monitored channels
            if auto_monitor.enabled and now >= next_sweep_time and not auto_monitor.is_sweeping:
                next_sweep_time = now + timedelta(minutes=auto_monitor.interval_minutes)
                auto_monitor.next_sweep_at = next_sweep_time.strftime("%Y-%m-%d %H:%M:%S IST")
                asyncio.create_task(run_247_autonomous_sweep())

            # 2. Check per-channel Auto-AI and Auto-Report schedules
            for ch_id, ch in list(store.channels.items()):
                # Check Auto-AI Analysis Schedule
                if ch.get("is_auto_ai"):
                    next_ai = ch.get("next_ai_at")
                    if isinstance(next_ai, str):
                        try:
                            next_ai = datetime.fromisoformat(next_ai.replace("Z", "+00:00"))
                        except Exception:
                            next_ai = None

                    if not next_ai or now >= next_ai:
                        ai_val = ch.get("ai_interval_value", 30)
                        ai_unit = ch.get("ai_interval_unit", "minutes")
                        delta = timedelta(days=ai_val) if ai_unit == "days" else (timedelta(hours=ai_val) if ai_unit == "hours" else timedelta(minutes=ai_val))
                        ch["next_ai_at"] = now + delta
                        asyncio.create_task(run_mini_ai_analysis_cycle(ch_id))

                # Check Auto-PDF Report Schedule
                if ch.get("is_auto_report"):
                    next_report = ch.get("next_report_at")
                    if isinstance(next_report, str):
                        try:
                            next_report = datetime.fromisoformat(next_report.replace("Z", "+00:00"))
                        except Exception:
                            next_report = None

                    if not next_report or now >= next_report:
                        rep_val = ch.get("report_interval_value", 24)
                        rep_unit = ch.get("report_interval_unit", "hours")
                        delta = timedelta(days=rep_val) if rep_unit == "days" else (timedelta(hours=rep_val) if rep_unit == "hours" else timedelta(minutes=rep_val))
                        ch["next_report_at"] = now + delta
                        asyncio.create_task(generate_auto_report_task(ch_id))

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            
        await asyncio.sleep(15)  # Scan every 15 seconds

def stop_scheduler():
    global scheduler_active
    scheduler_active = False
    logger.info("Scheduler loop stopped.")

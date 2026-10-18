"""
Standalone Background Ingestion Worker for Telegram Threat Channels.
Runs 24/7 as an independent systemd service (darknet-worker.service).
Holds the exclusive Telethon SQLite session lock so the FastAPI web service never encounters database locks.
"""

import asyncio
import signal
import sys
import logging
from app.config import settings
from app.db.mongodb import connect_to_mongo
from app.main import _migrate_session_file, _migrate_numeric_folders_to_titles, _migrate_csv_messages_to_db
from app.scrapers.telegram_scraper import telegram_scraper
from app.scrapers.scheduler import run_scheduler, stop_scheduler, enable_all_channels_247

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("darknet_worker")

stop_event = asyncio.Event()


def handle_shutdown(sig, frame):
    logger.info(f"Received termination signal ({sig}). Initiating graceful shutdown...")
    stop_event.set()


async def run_worker():
    logger.info("══════════════════════════════════════════════════════════")
    logger.info("  Telegram Darknet Monitor — Background Ingestion Worker   ")
    logger.info("══════════════════════════════════════════════════════════")

    # 1. Connect to MongoDB
    connected = await connect_to_mongo()
    if connected:
        logger.info("✓ Connected to MongoDB database successfully.")
    else:
        logger.warning("⚠ MongoDB unavailable; operating in local storage mode.")

    # 2. Migrate session files if needed
    _migrate_session_file()

    # 3. Check Telegram Authentication
    try:
        auth_status = await telegram_scraper.check_auth_status()
        if not auth_status.get("is_authorized"):
            logger.error("❌ Telegram session is not authorized! Please log in via the dashboard first.")
            return

        user = auth_status.get("user", {})
        username = user.get("username") or user.get("first_name") or "User"
        logger.info(f"✓ Telegram session active — logged in as @{username}.")

        # 4. Sync monitored channels
        channels = await telegram_scraper.sync_user_dialogs()
        logger.info(f"✓ Monitored channels synchronized: {len(channels)} active channels.")
        _migrate_numeric_folders_to_titles()
        asyncio.create_task(_migrate_csv_messages_to_db())

        # 5. Enable 24/7 automated sweeps
        if getattr(settings, "AUTO_MONITOR_24_7", True):
            count = enable_all_channels_247()
            logger.info(f"🟢 Autonomous monitoring active across {count} channels.")

        # 6. Start real-time live message listener
        if getattr(settings, "LIVE_LISTENER_ENABLED", True):
            logger.info("📡 Starting real-time Telegram message listener...")
            asyncio.create_task(telegram_scraper.start_live_listener())

        # 7. Start scheduled channel sweep loop
        logger.info("⏱️  Starting automated channel sweep scheduler...")
        asyncio.create_task(run_scheduler())

        logger.info("🚀 Background Ingestion Worker is fully operational. Monitoring live chatter...")

        # Wait until shutdown signal
        while not stop_event.is_set():
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Fatal error in ingestion worker: {e}", exc_info=True)
    finally:
        logger.info("Stopping scheduler and closing Telethon session...")
        try:
            stop_scheduler()
            if telegram_scraper.client:
                await telegram_scraper.client.disconnect()
                logger.info("✓ Telethon client disconnected cleanly.")
        except Exception as e:
            logger.warning(f"Error during worker cleanup: {e}")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        pass

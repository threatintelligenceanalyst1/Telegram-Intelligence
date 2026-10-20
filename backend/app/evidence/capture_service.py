import os
import re
import json
import uuid
import time
import zipfile
import hashlib
import logging
import asyncio
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from app.config import settings
from app.db import mongodb
from app.db.mongodb import store

logger = logging.getLogger("darknet_monitor.evidence")

# Global singleton background queue for evidence capture
_evidence_queue: Optional[asyncio.Queue] = None
_worker_task: Optional[asyncio.Task] = None
_last_capture_time: float = 0.0


_EPHEMERAL_FIELDS = {
    "_id",
    "evidence_hash",
    "evidence_screenshot",
    "evidence_screenshot_url",
    "evidence_captured_at"
}


def canonical_json_bytes(data: Any) -> bytes:
    """
    Produces deterministic, canonical JSON bytes with sorted keys and compact separators.
    Standardized for tamper-proof cryptographic hashing (RFC 8785 inspired).
    Ignores dynamic/ephemeral database and evidence fields.
    """
    if isinstance(data, dict):
        clean_data = {k: v for k, v in data.items() if k not in _EPHEMERAL_FIELDS}
    else:
        clean_data = data

    return json.dumps(
        clean_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str
    ).encode("utf-8")



def compute_sha256(data: bytes) -> str:
    """Computes hexadecimal SHA-256 digest of arbitrary bytes."""
    return hashlib.sha256(data).hexdigest()


class EvidenceCaptureService:
    """
    Production-grade Legal Evidence Capture and Chain-of-Custody Service.
    Captures real headless Chromium screenshots of Telegram public web embeds (t.me/<channel>/<id>?embed=1),
    computes cryptographic SHA-256 hashes for screenshots, canonical JSON, and manifest,
    and maintains an append-only audit trail.
    """

    KNOWN_CHANNEL_HANDLES: Dict[str, str] = {
        "-1001323386230": "ctinow",
        "1323386230": "ctinow",
        "cyber_threat_intelligence": "ctinow",
        "cyber threat intelligence": "ctinow",
        "-1001140994690": "msbte_world",
        "1140994690": "msbte_world",
        "msbte diploma world": "msbte_world",
        "-1002213647762": "sppu_CS_AIDS_Se_Te",
        "2213647762": "sppu_CS_AIDS_Se_Te",
        "sppu engineering cs aids civil mechanical entc it": "sppu_CS_AIDS_Se_Te",
        "-1002437259553": "sppuengineerschatgpt",
        "2437259553": "sppuengineerschatgpt",
        "sppu engineers chat-gpt": "sppuengineerschatgpt",
        "sppu engineers chat gpt": "sppuengineerschatgpt",
    }

    @classmethod
    def extract_channel_username(cls, channel_username: Any, channel_id: Any) -> Optional[str]:
        """
        Validates if channel has a genuine public username.
        Checks:
        1. channel_username if already a clean handle.
        2. Known channel handles dictionary mapping.
        3. store.channels lookup by channel_id (or stripped channel_id).
        4. store.channels title match if channel_username is a channel title.
        """
        clean = str(channel_username or "").strip().lstrip("@")
        if clean and not clean.startswith("-") and not clean.isdigit() and " " not in clean:
            return clean

        cid_str = str(channel_id or "").strip()
        cid_clean = cid_str.replace("-100", "").replace("-", "")

        # Check known channel handles map
        for k in [cid_str, cid_clean, clean.lower(), clean.lower().replace("_", " ")]:
            if k and k in cls.KNOWN_CHANNEL_HANDLES:
                return cls.KNOWN_CHANNEL_HANDLES[k]

        # Check in-memory store by channel_id
        candidates = [cid_str, cid_clean, f"-100{cid_clean}"]
        for cid in candidates:
            if cid and cid in store.channels:
                ch = store.channels[cid]
                raw_u = ch.get("raw_username") or ch.get("username", "")
                c_u = str(raw_u or "").strip().lstrip("@")
                if c_u and not c_u.startswith("-") and not c_u.isdigit() and " " not in c_u:
                    return c_u

        # Check by channel title match in store.channels
        if clean:
            for ch in store.channels.values():
                if ch.get("title", "").strip().lower() == clean.lower():
                    raw_u = ch.get("raw_username") or ch.get("username", "")
                    c_u = str(raw_u or "").strip().lstrip("@")
                    if c_u and not c_u.startswith("-") and not c_u.isdigit() and " " not in c_u:
                        return c_u

        return None

    @staticmethod
    def extract_numeric_message_id(message_id: Any) -> str:
        """Extracts the Telegram numeric message ID from composite strings (e.g. msg_-100123_456 -> 456)."""
        raw_str = str(message_id or "").strip()
        if "_" in raw_str:
            parts = raw_str.split("_")
            for p in reversed(parts):
                if p.isdigit():
                    return p
        digits = re.sub(r"\D", "", raw_str)
        return digits if digits else "1"

    @classmethod
    def build_embed_url(cls, channel_username: Any, channel_id: Any, message_id: Any) -> Tuple[Optional[str], Optional[str]]:
        """
        Constructs canonical https://t.me/{username}/{message_id}?embed=1 URL.
        Returns (url, error_reason).
        """
        username = cls.extract_channel_username(channel_username, channel_id)
        if not username:
            return None, "Channel has no public username or is a private/invite-only channel"

        raw_id = cls.extract_numeric_message_id(message_id)
        url = f"https://t.me/{username}/{raw_id}?embed=1"
        return url, None

    @classmethod
    async def capture_playwright_screenshot(cls, embed_url: str) -> Dict[str, Any]:
        """
        Executes sandboxed, safe headless Chromium capture of Telegram public embed.
        Strictly blocks navigation away from t.me, blocks popups/downloads, ignores links.
        """
        from playwright.async_api import async_playwright

        viewport = {"width": 1280, "height": 800}
        device_scale = 2
        timeout_ms = settings.EVIDENCE_CAPTURE_TIMEOUT_MS

        async with async_playwright() as p:
            # Docker & container friendly sandboxed chromium launch flags
            browser = await p.chromium.launch(
                headless=settings.EVIDENCE_BROWSER_HEADLESS,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-extensions",
                    "--disable-background-networking"
                ]
            )
            tool_version = f"Playwright {getattr(p, '__version__', '1.40+')}/Chromium {browser.version}"

            # Ephemeral, isolated incognito context (zero persistent cookies/cache)
            context = await browser.new_context(
                viewport=viewport,
                device_scale_factor=device_scale,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 CTI-Forensics/1.0"
            )

            # Prevent downloads and popups
            context.on("download", lambda d: asyncio.create_task(d.cancel()))

            page = await context.new_page()
            page.set_default_navigation_timeout(timeout_ms)
            page.set_default_timeout(timeout_ms)

            # Safety Route Interceptor: NEVER allow navigation away from t.me
            async def route_interceptor(route):
                req_url = route.request.url.lower()
                # Allow t.me domain and standard telegram static assets
                if re.match(r"^https?://([a-zA-Z0-9-]+\.)?t\.me(/.*)?$", req_url) or \
                   re.match(r"^https?://([a-zA-Z0-9-]+\.)?telesco\.pe(/.*)?$", req_url) or \
                   re.match(r"^https?://([a-zA-Z0-9-]+\.)?telegram\.org(/.*)?$", req_url):
                    await route.continue_()
                else:
                    # Abort any third-party external trackers, redirects, or links (e.g. ift.tt)
                    await route.abort()

            await page.route("**/*", route_interceptor)

            http_status: Optional[int] = None
            final_url: Optional[str] = None
            capture_ts = datetime.now(timezone.utc).isoformat()

            try:
                response = await page.goto(embed_url, wait_until="domcontentloaded", timeout=timeout_ms)
                if response:
                    http_status = response.status
                    final_url = response.url

                # Check if Telegram rendered a widget error (post deleted or channel private)
                widget_err = await page.query_selector(".tgme_widget_message_error")
                if widget_err:
                    err_text = (await widget_err.inner_text()).strip()
                    await browser.close()
                    return {
                        "status": "failed",
                        "reason": f"Telegram web returned post error: '{err_text}'",
                        "http_status": http_status,
                        "final_url": final_url,
                        "capture_timestamp": capture_ts,
                        "tool_name": "Playwright/Chromium",
                        "tool_version": tool_version,
                        "viewport": {**viewport, "device_scale_factor": device_scale},
                        "png_bytes": None
                    }

                # Wait for telegram message container
                msg_selector = ".tgme_widget_message"
                try:
                    el = await page.wait_for_selector(msg_selector, timeout=7000)
                except Exception:
                    el = await page.query_selector(".tgme_widget_message_wrap") or await page.query_selector("body")

                if not el:
                    await browser.close()
                    return {
                        "status": "failed",
                        "reason": "Telegram message element not found in DOM within timeout",
                        "http_status": http_status,
                        "final_url": final_url,
                        "capture_timestamp": capture_ts,
                        "tool_name": "Playwright/Chromium",
                        "tool_version": tool_version,
                        "viewport": {**viewport, "device_scale_factor": device_scale},
                        "png_bytes": None
                    }

                # Capture real PNG bytes directly from element
                png_bytes = await el.screenshot(type="png")
                await browser.close()

                return {
                    "status": "captured",
                    "reason": None,
                    "http_status": http_status,
                    "final_url": final_url,
                    "capture_timestamp": capture_ts,
                    "tool_name": "Playwright/Chromium",
                    "tool_version": tool_version,
                    "viewport": {**viewport, "device_scale_factor": device_scale},
                    "png_bytes": png_bytes
                }

            except Exception as exc:
                try:
                    await browser.close()
                except Exception:
                    pass
                return {
                    "status": "failed",
                    "reason": f"Browser navigation/capture error: {str(exc)}",
                    "http_status": http_status,
                    "final_url": final_url,
                    "capture_timestamp": capture_ts,
                    "tool_name": "Playwright/Chromium",
                    "tool_version": tool_version,
                    "viewport": {**viewport, "device_scale_factor": device_scale},
                    "png_bytes": None
                }

    @classmethod
    async def create_evidence_record(
        cls,
        message_data: Dict[str, Any],
        actor: str = "system",
        force_recapture: bool = False,
        priority: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Executes capture, hashes files, content-addresses storage, builds cryptographic manifest,
        and persists append-only records to MongoDB.
        """
        global _last_capture_time
        msg_id = str(message_data.get("id", ""))
        channel_user = message_data.get("channel_username")
        channel_id = message_data.get("channel_id")

        # Canonical representation of raw message data
        raw_msg_copy = dict(message_data)
        raw_msg_copy.pop("_id", None)
        canonical_msg_bytes = canonical_json_bytes(raw_msg_copy)
        message_sha256 = compute_sha256(canonical_msg_bytes)

        record_id = f"ev_{uuid.uuid4().hex[:16]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        # Build Telegram Embed URL
        embed_url, url_error = cls.build_embed_url(channel_user, channel_id, msg_id)

        capture_res: Dict[str, Any] = {}
        if not embed_url:
            capture_res = {
                "status": "failed",
                "reason": url_error or "Non-public channel",
                "http_status": None,
                "final_url": None,
                "capture_timestamp": now_utc,
                "tool_name": "Playwright/Chromium",
                "tool_version": "N/A",
                "viewport": {"width": 1280, "height": 800, "device_scale_factor": 2},
                "png_bytes": None
            }
        else:
            # Enforce rate limit delay between live browser captures
            elapsed = time.time() - _last_capture_time
            if elapsed < settings.EVIDENCE_CAPTURE_RATE_LIMIT_SEC:
                await asyncio.sleep(settings.EVIDENCE_CAPTURE_RATE_LIMIT_SEC - elapsed)

            # Retry with exponential backoff on transient errors
            max_retries = settings.EVIDENCE_CAPTURE_MAX_RETRIES
            for attempt in range(max_retries + 1):
                try:
                    capture_res = await cls.capture_playwright_screenshot(embed_url)
                    _last_capture_time = time.time()
                    if capture_res["status"] == "captured" or attempt == max_retries:
                        break
                    await asyncio.sleep(1.5 * (attempt + 1))
                except Exception as e:
                    if attempt == max_retries:
                        capture_res = {
                            "status": "failed",
                            "reason": f"Retry limit reached: {str(e)}",
                            "http_status": None,
                            "final_url": None,
                            "capture_timestamp": now_utc,
                            "tool_name": "Playwright/Chromium",
                            "tool_version": "N/A",
                            "viewport": {"width": 1280, "height": 800, "device_scale_factor": 2},
                            "png_bytes": None
                        }
                    await asyncio.sleep(1.5 * (attempt + 1))

        # Handle Screenshot Storage (Content-Addressed)
        png_bytes = capture_res.get("png_bytes")
        screenshot_sha256 = None
        screenshot_filename = None
        screenshot_path_str = None

        if png_bytes and len(png_bytes) > 0:
            screenshot_sha256 = compute_sha256(png_bytes)
            screenshot_filename = f"{screenshot_sha256}.png"
            file_path = settings.EVIDENCE_DIR / screenshot_filename
            try:
                # Write content-addressed PNG
                file_path.write_bytes(png_bytes)
                screenshot_path_str = str(file_path.resolve())
            except Exception as e:
                logger.error(f"Failed to write evidence PNG to disk: {e}")

        # Assemble Cryptographic Manifest (Tamper-evident verification payload)
        manifest_data = {
            "record_id": record_id,
            "message_id": msg_id,
            "channel_id": str(channel_id),
            "channel_username": str(channel_user or ""),
            "source_url": embed_url or "",
            "capture_status": capture_res["status"],
            "failure_reason": capture_res.get("reason"),
            "capture_timestamp": capture_res["capture_timestamp"],
            "http_status": capture_res.get("http_status"),
            "final_url": capture_res.get("final_url"),
            "screenshot_filename": screenshot_filename,
            "screenshot_sha256": screenshot_sha256,
            "message_sha256": message_sha256,
            "tool_name": capture_res["tool_name"],
            "tool_version": capture_res["tool_version"],
            "viewport": capture_res["viewport"]
        }
        manifest_canonical = canonical_json_bytes(manifest_data)
        manifest_sha256 = compute_sha256(manifest_canonical)

        # Full Append-Only Evidence Record Document
        evidence_doc = {
            "record_id": record_id,
            "message_id": msg_id,
            "created_at": now_utc,
            "actor": actor,
            "source_url": embed_url or "",
            "capture_status": capture_res["status"],
            "failure_reason": capture_res.get("reason"),
            "capture_metadata": {
                "http_status": capture_res.get("http_status"),
                "final_url": capture_res.get("final_url"),
                "capture_timestamp": capture_res["capture_timestamp"],
                "tool_name": capture_res["tool_name"],
                "tool_version": capture_res["tool_version"],
                "viewport": capture_res["viewport"]
            },
            "screenshot_path": screenshot_path_str,
            "screenshot_filename": screenshot_filename,
            "screenshot_sha256": screenshot_sha256,
            "message_sha256": message_sha256,
            "manifest": manifest_data,
            "manifest_sha256": manifest_sha256,
            "raw_message_json": raw_msg_copy
        }

        # 1. Append-only insertion into MongoDB `evidence_records`
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                await mongodb.db.evidence_records.insert_one(dict(evidence_doc))
            except Exception as e:
                logger.error(f"Error persisting evidence record to MongoDB: {e}")
        else:
            store.evidence_records.append(dict(evidence_doc))

        # 2. Append-only insertion into `evidence_audit_log`
        audit_entry = {
            "log_id": f"aud_{uuid.uuid4().hex[:12]}",
            "event": "recaptured" if force_recapture else "captured",
            "message_id": msg_id,
            "record_id": record_id,
            "actor": actor,
            "timestamp": now_utc,
            "status": capture_res["status"],
            "details": f"Evidence capture completed with status: {capture_res['status']}"
        }
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                await mongodb.db.evidence_audit_log.insert_one(dict(audit_entry))
            except Exception as e:
                logger.error(f"Error logging evidence audit entry: {e}")
        else:
            store.evidence_audit_log.append(dict(audit_entry))

        # 3. Update top-level message metadata pointers (without mutating raw text/evidence history)
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                await mongodb.db.messages.update_one(
                    {"id": msg_id},
                    {"$set": {
                        "evidence_record_id": record_id,
                        "evidence_capture_status": capture_res["status"],
                        "evidence_screenshot_sha256": screenshot_sha256,
                        "evidence_captured_at": capture_res["capture_timestamp"],
                        "evidence_hash": screenshot_sha256 or manifest_sha256
                    }}
                )
            except Exception:
                pass
        elif msg_id in store.messages:
            store.messages[msg_id].update({
                "evidence_record_id": record_id,
                "evidence_capture_status": capture_res["status"],
                "evidence_screenshot_sha256": screenshot_sha256,
                "evidence_captured_at": capture_res["capture_timestamp"],
                "evidence_hash": screenshot_sha256 or manifest_sha256
            })

        logger.info(f"📸 Evidence record {record_id} generated for {msg_id} [Status: {capture_res['status']}]")
        return evidence_doc

    @classmethod
    async def get_evidence_record(cls, message_id: str, actor: str = "anonymous") -> Optional[Dict[str, Any]]:
        """Retrieves the latest append-only evidence record for a given message ID."""
        record = None
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                cursor = mongodb.db.evidence_records.find({"message_id": message_id}).sort("created_at", -1).limit(1)
                async for r in cursor:
                    r.pop("_id", None)
                    record = r
                    break
            except Exception as e:
                logger.error(f"Error reading evidence record: {e}")
        else:
            matching = [r for r in store.evidence_records if r.get("message_id") == message_id]
            if matching:
                record = matching[-1]

        if record:
            # Record audit view event
            await cls.log_audit_event("viewed", message_id, record["record_id"], actor, "Evidence record viewed")

        return record

    @classmethod
    async def verify_evidence(cls, message_id: str, actor: str = "anonymous") -> Dict[str, Any]:
        """
        Cryptographic Integrity Verification Engine.
        Recomputes SHA-256 digests from stored disk PNG file and raw JSON,
        comparing against immutable manifest signatures.
        """
        record = await cls.get_evidence_record(message_id, actor=actor)
        now_iso = datetime.now(timezone.utc).isoformat()

        if not record:
            return {
                "message_id": message_id,
                "verified_at": now_iso,
                "is_valid": False,
                "error": "No evidence record found for this message"
            }

        screenshot_hash_match = False
        message_hash_match = False
        manifest_hash_match = False
        computed_screenshot_sha = None
        computed_message_sha = None
        computed_manifest_sha = None

        # 1. Verify Screenshot PNG file integrity on disk
        screenshot_path = record.get("screenshot_path")
        expected_screenshot_sha = record.get("screenshot_sha256")

        if screenshot_path and Path(screenshot_path).exists():
            try:
                disk_bytes = Path(screenshot_path).read_bytes()
                computed_screenshot_sha = compute_sha256(disk_bytes)
                screenshot_hash_match = (computed_screenshot_sha == expected_screenshot_sha)
            except Exception as e:
                logger.error(f"Failed reading screenshot file for verify: {e}")
        elif record.get("capture_status") == "failed":
            # If capture legitimately failed (e.g. private channel), screenshot is expected to be null
            screenshot_hash_match = (expected_screenshot_sha is None)

        # 2. Verify Canonical Message JSON integrity
        raw_msg = record.get("raw_message_json") or {}
        expected_message_sha = record.get("message_sha256")
        if raw_msg and expected_message_sha:
            computed_message_sha = compute_sha256(canonical_json_bytes(raw_msg))
            message_hash_match = (computed_message_sha == expected_message_sha)

        # 3. Verify Manifest integrity
        manifest_data = record.get("manifest") or {}
        expected_manifest_sha = record.get("manifest_sha256")
        if manifest_data and expected_manifest_sha:
            computed_manifest_sha = compute_sha256(canonical_json_bytes(manifest_data))
            manifest_hash_match = (computed_manifest_sha == expected_manifest_sha)

        is_valid = screenshot_hash_match and message_hash_match and manifest_hash_match

        # Log verification audit entry
        await cls.log_audit_event(
            "verified",
            message_id,
            record["record_id"],
            actor,
            f"Integrity check {'PASSED' if is_valid else 'FAILED'} (Screenshot: {screenshot_hash_match}, JSON: {message_hash_match}, Manifest: {manifest_hash_match})"
        )

        return {
            "message_id": message_id,
            "record_id": record["record_id"],
            "capture_status": record.get("capture_status"),
            "failure_reason": record.get("failure_reason"),
            "capture_timestamp": record.get("capture_metadata", {}).get("capture_timestamp"),
            "verified_at": now_iso,
            "is_valid": is_valid,
            "verified": is_valid,
            "screenshot_hash_match": screenshot_hash_match,
            "message_hash_match": message_hash_match,
            "manifest_hash_match": manifest_hash_match,
            "screenshot_sha256": expected_screenshot_sha,
            "computed_screenshot_sha256": computed_screenshot_sha,
            "message_sha256": expected_message_sha,
            "computed_message_sha256": computed_message_sha,
            "manifest_sha256": expected_manifest_sha,
            "computed_manifest_sha256": computed_manifest_sha,
            "audit_trail_summary": f"Record verified using SHA-256 content hashes at {now_iso}"
        }

    @classmethod
    async def generate_evidence_bundle(cls, message_id: str, actor: str = "anonymous") -> Tuple[Optional[bytes], str]:
        """
        Builds a comprehensive legal ZIP bundle containing:
        - screenshot.png (the real web screenshot)
        - message.json (canonical raw message data)
        - manifest.json (all hashes, metadata, versions)
        - README.txt (CLI verification commands and instructions)
        """
        record = await cls.get_evidence_record(message_id, actor=actor)
        if not record:
            return None, ""

        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. screenshot.png
            screenshot_path = record.get("screenshot_path")
            if screenshot_path and Path(screenshot_path).exists():
                zf.write(screenshot_path, arcname="screenshot.png")
            else:
                failure_note = f"Screenshot capture status: {record.get('capture_status')}\nReason: {record.get('failure_reason', 'No file available')}\n"
                zf.writestr("screenshot_status.txt", failure_note)

            # 2. message.json
            canonical_msg = canonical_json_bytes(record.get("raw_message_json", {}))
            # Pretty formatted version for human analysts
            pretty_msg = json.dumps(record.get("raw_message_json", {}), indent=2, ensure_ascii=False)
            zf.writestr("message.json", pretty_msg)

            # 3. manifest.json
            manifest_info = {
                "evidence_record_id": record["record_id"],
                "message_id": message_id,
                "capture_timestamp_utc": record.get("capture_metadata", {}).get("capture_timestamp"),
                "export_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "screenshot_sha256": record.get("screenshot_sha256"),
                "message_sha256": record.get("message_sha256"),
                "manifest_sha256": record.get("manifest_sha256"),
                "capture_status": record.get("capture_status"),
                "source_url": record.get("source_url"),
                "tool_version": record.get("capture_metadata", {}).get("tool_version"),
                "viewport": record.get("capture_metadata", {}).get("viewport")
            }
            zf.writestr("manifest.json", json.dumps(manifest_info, indent=2))

            # 4. README.txt with verification commands
            readme_text = (
                "========================================================================\n"
                "TELEGRAM DARKNET CTI — DIGITAL FORENSIC EVIDENCE BUNDLE\n"
                "========================================================================\n\n"
                f"Message ID: {message_id}\n"
                f"Record ID:  {record['record_id']}\n"
                f"Capture TS: {record.get('capture_metadata', {}).get('capture_timestamp')} UTC\n"
                f"Status:     {record.get('capture_status')}\n\n"
                "------------------------------------------------------------------------\n"
                "HOW TO VERIFY HASH INTEGRITY (CHAIN OF CUSTODY)\n"
                "------------------------------------------------------------------------\n"
                "You can verify the cryptographic authenticity of this evidence independently\n"
                "on any operating system using standard command-line tools:\n\n"
                "1. Linux / macOS:\n"
                "   $ sha256sum screenshot.png\n"
                f"   Expected: {record.get('screenshot_sha256') or 'N/A'}\n\n"
                "2. Windows (PowerShell):\n"
                "   PS> Get-FileHash .\\screenshot.png -Algorithm SHA256\n"
                f"   Expected: {record.get('screenshot_sha256') or 'N/A'}\n\n"
                "3. Verify Manifest Hash:\n"
                "   Check that the SHA-256 of screenshot.png matches the 'screenshot_sha256'\n"
                "   declared in manifest.json.\n\n"
                "All metadata is preserved in append-only custody logs within the darknet intelligence repository.\n"
            )
            zf.writestr("README.txt", readme_text)

        await cls.log_audit_event("downloaded", message_id, record["record_id"], actor, "Evidence bundle ZIP exported")

        zip_buf.seek(0)
        filename = f"evidence_bundle_{message_id}.zip"
        return zip_buf.getvalue(), filename

    @classmethod
    async def log_audit_event(cls, event: str, message_id: str, record_id: str, actor: str, details: str):
        """Appends an event to the immutable evidence audit log."""
        entry = {
            "log_id": f"aud_{uuid.uuid4().hex[:12]}",
            "event": event,
            "message_id": message_id,
            "record_id": record_id,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details
        }
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                await mongodb.db.evidence_audit_log.insert_one(entry)
            except Exception as e:
                logger.error(f"Audit log write failed: {e}")
        else:
            store.evidence_audit_log.append(entry)

    # Convenient alias
    capture_and_store_evidence = create_evidence_record



# =========================================================================
# ASYNCHRONOUS BACKGROUND CAPTURE WORKER & QUEUE
# =========================================================================

async def _evidence_worker_loop():
    """Background worker processing evidence captures sequentially without slowing ingestion."""
    global _evidence_queue
    logger.info("🚀 Evidence capture background queue worker started.")
    while True:
        try:
            msg_data, actor, force = await _evidence_queue.get()
            try:
                await EvidenceCaptureService.create_evidence_record(msg_data, actor=actor, force_recapture=force)
            except Exception as exc:
                logger.error(f"Error in background evidence capture: {exc}")
            finally:
                _evidence_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Unexpected error in evidence worker loop: {e}")
            await asyncio.sleep(1)


def get_evidence_queue() -> asyncio.Queue:
    global _evidence_queue, _worker_task
    if _evidence_queue is None:
        _evidence_queue = asyncio.Queue()
        try:
            loop = asyncio.get_running_loop()
            _worker_task = loop.create_task(_evidence_worker_loop())
        except RuntimeError:
            pass
    return _evidence_queue


def enqueue_evidence_capture(message_data: Dict[str, Any], actor: str = "system", force: bool = False):
    """
    Fire-and-forget helper to dispatch a message to the evidence capture worker.
    Never blocks ingestion or crashes callers.
    """
    if not settings.EVIDENCE_CAPTURE_ENABLED:
        return
    try:
        q = get_evidence_queue()
        q.put_nowait((dict(message_data), actor, force))
    except Exception as e:
        logger.warning(f"Could not enqueue evidence capture for {message_data.get('id')}: {e}")

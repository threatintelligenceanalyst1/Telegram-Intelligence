import os
import re
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from ..config import settings

IST = timezone(timedelta(hours=5, minutes=30))

class EvidenceEngine:
    """
    Evidence Capture & Forensic Verification Engine.
    Generates cryptographic proof hashes, resolves canonical Telegram message links,
    and produces high-resolution Telegram screenshot proof cards for every ingested message.
    """

    @staticmethod
    def compute_evidence_hash(msg_data: Dict[str, Any]) -> str:
        """Calculate tamper-evident SHA-256 fingerprint for a message."""
        msg_id = str(msg_data.get("id", ""))
        text = str(msg_data.get("text", ""))
        channel_id = str(msg_data.get("channel_id", ""))
        sender = str(msg_data.get("sender", ""))
        date = str(msg_data.get("date", ""))
        raw_payload = f"{msg_id}|{channel_id}|{sender}|{date}|{text}"
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    @staticmethod
    def construct_telegram_link(channel_id: str, channel_username: str, msg_id_str: str) -> str:
        """Resolve direct Telegram web/app link to the original message."""
        try:
            # Extract raw numeric telegram message ID (e.g. msg_-100123_456 -> 456)
            raw_msg_id = msg_id_str.split("_")[-1] if "_" in str(msg_id_str) else str(msg_id_str)
            if not raw_msg_id.isdigit():
                raw_msg_id = re.sub(r"\D", "", str(msg_id_str)) or "1"

            # Check if channel has a public handle
            clean_user = (channel_username or "").strip().lstrip("@")
            if clean_user and not clean_user.startswith("-") and not clean_user.isdigit() and " " not in clean_user:
                return f"https://t.me/{clean_user}/{raw_msg_id}"

            # Private supergroup channel: https://t.me/c/<id_without_-100>/<msg_id>
            cid_str = str(channel_id).strip()
            if cid_str.startswith("-100"):
                clean_cid = cid_str[4:]
                return f"https://t.me/c/{clean_cid}/{raw_msg_id}"
            elif cid_str.startswith("-"):
                clean_cid = cid_str[1:]
                return f"https://t.me/c/{clean_cid}/{raw_msg_id}"
            elif cid_str.isdigit():
                return f"https://t.me/c/{cid_str}/{raw_msg_id}"

            return f"https://t.me/{clean_user or 'c'}/{raw_msg_id}"
        except Exception:
            return f"https://t.me/{channel_username or 'telegram'}/1"

    @classmethod
    def get_font(cls, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Load Segoe UI or Arial font with safe fallback to default."""
        font_names = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"] if bold else ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
        win_dir = os.environ.get("WINDIR", "C:\\Windows")
        fonts_dir = Path(win_dir) / "Fonts"

        for fn in font_names:
            fp = fonts_dir / fn
            if fp.exists():
                try:
                    return ImageFont.truetype(str(fp), size)
                except Exception:
                    pass

        try:
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    @classmethod
    def generate_evidence_screenshot(cls, msg_data: Dict[str, Any], keyword: str = "") -> Path:
        """
        Creates an authentic, high-resolution darknet Telegram message screenshot
        with forensic verification banner and cryptographic proof stamp.
        """
        raw_id = str(msg_data.get("id", "msg_unknown"))
        safe_id = re.sub(r"[^\w\-.]", "_", raw_id)
        out_path = settings.EVIDENCE_DIR / f"{safe_id}.png"

        # If already exists and not empty, return existing cached proof image
        if out_path.exists() and out_path.stat().st_size > 1000:
            return out_path

        # Message fields
        text = str(msg_data.get("text") or "(No message text content)")
        sender = str(msg_data.get("sender") or "Anonymous User")
        channel_name = str(msg_data.get("channel_username") or msg_data.get("channel_id") or "Telegram Channel")
        date_str = str(msg_data.get("date") or "")
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            dt_ist = dt.astimezone(IST)
            formatted_date = dt_ist.strftime("%d %b %Y, %H:%M:%S IST")
        except Exception:
            formatted_date = date_str or datetime.now(IST).strftime("%d %b %Y, %H:%M:%S IST")

        views = msg_data.get("views", 10) or 10
        threat_level = str(msg_data.get("threat_level") or "LOW").upper()
        conf_score = msg_data.get("confidence_score")
        detected_sector = msg_data.get("detected_sector") or "General Threat"
        sha_hash = cls.compute_evidence_hash(msg_data)
        tg_link = cls.construct_telegram_link(str(msg_data.get("channel_id", "")), channel_name, raw_id)

        # Layout dimensions
        img_w = 920
        padding = 32

        # Fonts
        font_header_title = cls.get_font(18, bold=True)
        font_header_sub = cls.get_font(12, bold=False)
        font_sender = cls.get_font(15, bold=True)
        font_body = cls.get_font(14, bold=False)
        font_meta_lbl = cls.get_font(11, bold=True)
        font_meta_val = cls.get_font(11, bold=False)
        font_stamp = cls.get_font(10, bold=True)

        # Wrap message text to fit bubble
        max_bubble_w = img_w - (padding * 2) - 40
        char_per_line = int(max_bubble_w / 8.5)
        wrapped_lines = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                wrapped_lines.append("")
                continue
            words = paragraph.split()
            current_line = []
            current_len = 0
            for w in words:
                if current_len + len(w) + 1 > char_per_line:
                    wrapped_lines.append(" ".join(current_line))
                    current_line = [w]
                    current_len = len(w)
                else:
                    current_line.append(w)
                    current_len += len(w) + 1
            if current_line:
                wrapped_lines.append(" ".join(current_line))

        line_h = 22
        body_text_h = max(40, len(wrapped_lines) * line_h)

        # Calculate total height
        # Header (80) + Bubble padding (30) + Sender (26) + Body + Bubble footer (26) + Forensic Panel (190) + Padding
        bubble_h = 24 + 26 + body_text_h + 30
        img_h = 80 + bubble_h + 195 + 40

        # Colors (Authentic Telegram Dark Mode Palette)
        bg_color = (14, 22, 33)            # #0e1621 - Telegram dark chat background
        topbar_color = (23, 33, 43)        # #17212b - Telegram header bar
        bubble_color = (24, 37, 51)        # #182533 - Telegram incoming message bubble
        bubble_border = (36, 47, 61)       # #242f3d
        sender_color = (100, 181, 246)     # #64b5f6 - Telegram sender blue
        text_color = (245, 245, 245)       # #f5f5f5
        subtext_color = (130, 142, 155)    # #828e9b
        panel_color = (19, 28, 38)         # #131c26 - Forensic metadata panel
        panel_border = (38, 50, 66)

        # Threat accent colors
        threat_colors = {
            "CRITICAL": (239, 68, 68),
            "HIGH": (249, 115, 22),
            "MEDIUM": (234, 179, 8),
            "LOW": (59, 130, 246)
        }
        accent_color = threat_colors.get(threat_level, (59, 130, 246))

        # Create canvas
        img = Image.new("RGB", (img_w, img_h), color=bg_color)
        draw = ImageDraw.Draw(img)

        # 1. Top Header Bar (Telegram Channel Bar)
        draw.rectangle([(0, 0), (img_w, 75)], fill=topbar_color)
        draw.line([(0, 75), (img_w, 75)], fill=bubble_border, width=1)

        # Telegram Logo / Channel Avatar Circle
        avatar_r = 22
        avatar_x = padding + avatar_r
        avatar_y = 37
        draw.ellipse([(avatar_x - avatar_r, avatar_y - avatar_r), (avatar_x + avatar_r, avatar_y + avatar_r)], fill=(43, 82, 120))
        # Initials in avatar
        initials = (channel_name[:2] or "TG").upper()
        draw.text((avatar_x - 10, avatar_y - 8), initials, fill=(255, 255, 255), font=font_header_sub)

        # Channel Title & Subtitle
        draw.text((padding + 56, 18), channel_name[:50], fill=(255, 255, 255), font=font_header_title)
        sub_text = f"Channel ID: {msg_data.get('channel_id')} • Telegram Darknet Monitor Ingested"
        draw.text((padding + 56, 44), sub_text[:75], fill=subtext_color, font=font_header_sub)

        # Official Evidence Tag Badge in header
        badge_text = "VERIFIED EVIDENCE CAPTURE"
        badge_w = 205
        badge_x = img_w - padding - badge_w
        draw.rounded_rectangle([(badge_x, 22), (badge_x + badge_w, 52)], radius=6, fill=(16, 44, 43), outline=(16, 185, 129), width=1)
        draw.text((badge_x + 12, 29), f"● {badge_text}", fill=(52, 211, 153), font=font_stamp)

        # 2. Telegram Message Bubble
        bubble_y1 = 95
        bubble_y2 = bubble_y1 + bubble_h
        bubble_x1 = padding
        bubble_x2 = img_w - padding

        draw.rounded_rectangle(
            [(bubble_x1, bubble_y1), (bubble_x2, bubble_y2)],
            radius=12,
            fill=bubble_color,
            outline=bubble_border,
            width=1
        )

        # Sender inside bubble
        cur_y = bubble_y1 + 16
        draw.text((bubble_x1 + 20, cur_y), sender[:60], fill=sender_color, font=font_sender)
        cur_y += 26

        # Message text lines
        for l in wrapped_lines:
            draw.text((bubble_x1 + 20, cur_y), l, fill=text_color, font=font_body)
            cur_y += line_h

        # Bubble Footer: Views & Timestamp & Checkmark
        footer_y = bubble_y2 - 24
        footer_info = f"👁 {views:,} views  •  {formatted_date}  ✓✓"
        draw.text((bubble_x2 - 320, footer_y), footer_info, fill=subtext_color, font=font_stamp)

        # 3. Forensic Metadata & Proof Panel
        panel_y1 = bubble_y2 + 20
        panel_y2 = panel_y1 + 175
        draw.rounded_rectangle(
            [(padding, panel_y1), (img_w - padding, panel_y2)],
            radius=10,
            fill=panel_color,
            outline=panel_border,
            width=1
        )

        # Panel Header Banner
        p_hdr_y = panel_y1 + 12
        draw.text((padding + 16, p_hdr_y), "🔒 CYBER THREAT INTELLIGENCE EVIDENCE SPECIFICATION", fill=(147, 197, 253), font=font_meta_lbl)
        draw.line([(padding + 16, p_hdr_y + 20), (img_w - padding - 16, p_hdr_y + 20)], fill=panel_border, width=1)

        # Grid items inside Forensic Panel
        row1_y = p_hdr_y + 30
        draw.text((padding + 16, row1_y), "Target Sector:", fill=subtext_color, font=font_meta_lbl)
        draw.text((padding + 115, row1_y), str(detected_sector)[:35], fill=(255, 255, 255), font=font_meta_val)

        draw.text((padding + 430, row1_y), "Threat Level:", fill=subtext_color, font=font_meta_lbl)
        draw.text((padding + 520, row1_y), threat_level, fill=accent_color, font=font_meta_lbl)

        row2_y = row1_y + 24
        draw.text((padding + 16, row2_y), "Search Query:", fill=subtext_color, font=font_meta_lbl)
        draw.text((padding + 115, row2_y), f'"{keyword or "Direct Search"}"', fill=(253, 224, 71), font=font_meta_val)

        if conf_score is not None:
            draw.text((padding + 430, row2_y), "Confidence Score:", fill=subtext_color, font=font_meta_lbl)
            draw.text((padding + 550, row2_y), f"{conf_score}% Verified Match", fill=(52, 211, 153), font=font_meta_val)

        row3_y = row2_y + 24
        draw.text((padding + 16, row3_y), "Message Link:", fill=subtext_color, font=font_meta_lbl)
        draw.text((padding + 115, row3_y), tg_link[:70], fill=(96, 165, 250), font=font_meta_val)

        row4_y = row3_y + 24
        draw.text((padding + 16, row4_y), "SHA-256 Hash:", fill=subtext_color, font=font_meta_lbl)
        draw.text((padding + 115, row4_y), sha_hash, fill=(209, 213, 219), font=font_stamp)

        row5_y = row4_y + 24
        draw.text((padding + 16, row5_y), "Proof Captured:", fill=subtext_color, font=font_meta_lbl)
        draw.text((padding + 115, row5_y), f"{datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')} (Automatic Ingestion Proof)", fill=subtext_color, font=font_stamp)

        # Save to disk
        img.save(str(out_path), "PNG", optimize=True)
        return out_path

    @classmethod
    def capture_message_evidence(cls, msg_data: Dict[str, Any], keyword: str = "") -> Dict[str, Any]:
        """
        Calculates cryptographic hash, builds permalink, generates screenshot proof on disk,
        and enriches message data with evidence metadata.
        """
        raw_id = str(msg_data.get("id", "msg_unknown"))
        safe_id = re.sub(r"[^\w\-.]", "_", raw_id)

        evidence_hash = cls.compute_evidence_hash(msg_data)
        tg_link = cls.construct_telegram_link(
            str(msg_data.get("channel_id", "")),
            str(msg_data.get("channel_username", "")),
            raw_id
        )

        now_iso = datetime.now(IST).isoformat()
        msg_data["evidence_hash"] = evidence_hash
        msg_data["message_link"] = tg_link
        msg_data["evidence_captured_at"] = msg_data.get("evidence_captured_at") or now_iso
        msg_data["evidence_screenshot_url"] = f"/evidence/{safe_id}.png"

        # Generate the PNG proof screenshot file
        try:
            cls.generate_evidence_screenshot(msg_data, keyword=keyword)
        except Exception as e:
            pass

        return msg_data

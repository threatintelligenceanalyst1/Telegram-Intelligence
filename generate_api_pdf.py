#!/usr/bin/env python3
"""
Generates an executive-ready, highly polished PDF documentation for the
Telegram Darknet Threat Intelligence API and Enterprise Integration Architecture.
"""

import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = "Telegram_Darknet_API_Integration_Documentation.pdf"


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that calculates total pages and draws running headers and footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(54, 755, "TELEGRAM DARKNET CTI — ENTERPRISE API INTEGRATION SPECIFICATION")
            self.setFont("Helvetica", 8)
            self.drawRightString(558, 755, "TLP:WHITE | v1.0")

            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.75)
            self.line(54, 747, 558, 747)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 32, "Confidential Threat Intelligence Feed • Telegram Darknet Intelligence Framework")
        self.drawRightString(558, 32, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom color palette
    c_primary = colors.HexColor("#0f172a")      # Slate 900
    c_accent = colors.HexColor("#1d4ed8")       # Blue 700
    c_teal = colors.HexColor("#0284c7")         # Cyan/Sky 600
    c_emerald = colors.HexColor("#047857")      # Green 700
    c_text = colors.HexColor("#1e293b")         # Slate 800
    c_subtext = colors.HexColor("#64748b")      # Slate 500
    c_bg_code = colors.HexColor("#f8fafc")      # Slate 50
    c_border_code = colors.HexColor("#cbd5e1")  # Slate 300

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=c_primary,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceAfter=15,
    )

    h1_style = ParagraphStyle(
        "Header1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Header2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=c_text,
        spaceAfter=6,
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    code_kw_style = ParagraphStyle(
        "CodeKw",
        parent=code_style,
        textColor=colors.HexColor("#1e40af"),
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    story = []

    # =========================================================================
    # COVER / HEADER BANNER
    # =========================================================================
    header_meta = [
        [
            Paragraph("<b>TELEGRAM DARKNET CTI API</b>", ParagraphStyle("MetaL", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#1e3a8a"))),
            Paragraph("<b>STATUS:</b> PRODUCTION READY • <b>DATE:</b> OCTOBER 2026", ParagraphStyle("MetaR", fontName="Helvetica", fontSize=9, alignment=2, textColor=c_subtext))
        ]
    ]
    t_meta = Table(header_meta, colWidths=[250, 254])
    t_meta.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_meta)
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=4, spaceAfter=14))

    story.append(Paragraph("Threat Intelligence API Specification & Integration Guide", title_style))
    story.append(Paragraph("Enterprise Developer Manual for Customer Ingestion, SIEM/SOC Feeds, and Automated Pipelines", subtitle_style))

    # Executive Summary Box
    exec_summary_text = (
        "<b>Executive Summary:</b> This document provides the complete technical specification for consuming the "
        "<b>Telegram Darknet Cyber Threat Intelligence (CTI) API (v1)</b>. The system continuously scrapes over 28 "
        "monitored underground Telegram threat actor channels, executing real-time NLP classification, severity scoring, "
        "and indicator extraction (malicious URLs, crypto wallets, CVE exploits, and forensic evidence). "
        "Through this REST API, external security operation centers (SOCs), SIEM platforms (Splunk, Microsoft Sentinel), "
        "and customer automated scripts can ingest high-fidelity threat telemetry programmatically."
    )
    t_summary = Table([[Paragraph(exec_summary_text, body_style)]], colWidths=[504])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 1: SYSTEM ARCHITECTURE & INTEGRATION TOPOLOGY
    # =========================================================================
    story.append(Paragraph("1. System Architecture & High-Level Ingestion Flow", h1_style))
    story.append(Paragraph(
        "The architecture is built upon a defense-in-depth model that ensures high availability, strict client isolation, "
        "and total protection of the core database infrastructure:",
        body_style
    ))

    arch_data = [
        ["Component", "Role", "Security & Protocol Details"],
        ["Scraper Core", "Autonomous Crawler", "Monitors 28+ channels 24/7; extracts chat text, media, metadata."],
        ["Forensic LLM & Regex", "Analysis Pipeline", "Extracts IOCs (CVEs, IPs, BTC/ETH wallets, hashes, phishing links)."],
        ["Database Tier", "Primary Storage", "Encrypted MongoDB + SQLite fallback. <b>Direct customer access is blocked.</b>"],
        ["API Gateway (FastAPI)", "Customer Endpoint", "Enforces API key auth, per-key rate limits, request telemetry."],
        ["Cloudflare Tunnel", "Secure Egress Gateway", "Zero open router ports; DDoS shield; TLS 1.3 encrypted transit."]
    ]
    t_arch = Table(arch_data, colWidths=[110, 120, 274])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('LEADING', (0,0), (-1,-1), 11),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 2: AUTHENTICATION & SECURITY GOVERNANCE
    # =========================================================================
    story.append(Paragraph("2. Authentication, Rate Limiting & Security Governance", h1_style))
    story.append(Paragraph(
        "Every request to the Customer API must be authenticated using a customer-specific API key possessing the "
        "<code>dnet_live_</code> prefix. The key can be passed via three supported mechanisms:",
        body_style
    ))

    auth_table_data = [
        ["Authentication Method", "Format / Syntax", "Best For"],
        [
            "HTTP Header (Recommended)",
            "<code>X-API-Key: dnet_live_&lt;token&gt;</code>",
            "Production SIEM, Python, Node.js, Go scripts"
        ],
        [
            "Bearer Authorization",
            "<code>Authorization: Bearer dnet_live_&lt;token&gt;</code>",
            "Standard REST/OAuth2 compatible clients"
        ],
        [
            "URL Query Parameter",
            "<code>?api_key=dnet_live_&lt;token&gt;</code>",
            "Ad-hoc browser inspection and curl testing"
        ]
    ]
    t_auth = Table([[Paragraph(c, body_style) for c in row] for row in auth_table_data], colWidths=[130, 224, 150])
    t_auth.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_auth)
    story.append(Spacer(1, 10))

    # Security Guarantees Callout Box
    sec_box = (
        "<b>Key Security Guarantees for Infrastructure Protection:</b><br/>"
        "• <b>Strict Read-Only Access:</b> All customer endpoints expose solely HTTP GET methods. External keys have "
        "zero write, update, or deletion privileges on the database.<br/>"
        "• <b>Administrative Guard (AdminGuard):</b> Management endpoints (key creation, quota editing, telemetry reset) "
        "are strictly restricted to internal localhost/LAN access and are automatically blocked for tunnel callers.<br/>"
        "• <b>Sliding-Window Rate Limiting:</b> Each key is capped at 120 requests/minute. Excessive traffic triggers an "
        "HTTP 429 Too Many Requests response with a dynamic <code>Retry-After</code> countdown header.<br/>"
        "• <b>Cryptographic Hashing:</b> API keys are stored exclusively as one-way SHA-256 hashes in MongoDB. Cleartext keys "
        "are never retrievable from the database."
    )
    t_sec = Table([[Paragraph(sec_box, body_style)]], colWidths=[504])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#93c5fd")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sec)
    story.append(Spacer(1, 14))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: API ENDPOINT REFERENCE
    # =========================================================================
    story.append(Paragraph("3. Customer API Endpoint Reference (v1)", h1_style))
    story.append(Paragraph(
        "<b>Base Live Production URL:</b> <code>https://set-represents-suggested-leader.trycloudflare.com</code><br/>"
        "<b>Local Development Base URL:</b> <code>http://localhost:8000</code>",
        body_style
    ))
    story.append(Spacer(1, 6))

    endpoints_data = [
        ["Method", "Endpoint Path", "Parameters & Filters", "Description / Output"],
        [
            "GET",
            "/api/v1/threats",
            "min_level (ALL, LOW, MED, HIGH, CRITICAL)<br/>limit (1-200, default 50)<br/>page, keyword, sector",
            "Fetches real-time darknet threat alerts and scraped messages sorted chronologically with full severity tags."
        ],
        [
            "GET",
            "/api/v1/threats/{id}",
            "id: Message ID string",
            "Retrieves full forensic details, IOCs, entities, and screenshot evidence for a specific message."
        ],
        [
            "GET",
            "/api/v1/iocs",
            "type (all, wallet, url, cve, ip)<br/>limit (1-500, default 100)",
            "High-speed stream of extracted Indicators of Compromise optimized for firewall and SIEM blocklist ingestion."
        ],
        [
            "GET",
            "/api/v1/stats",
            "None",
            "Provides high-level CTI metadata, channel counts, active monitoring metrics, and severity distributions."
        ]
    ]
    t_endpoints = Table([[Paragraph(c, body_style) for c in row] for row in endpoints_data], colWidths=[48, 110, 150, 196])
    t_endpoints.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_endpoints)
    story.append(Spacer(1, 14))

    # Sample JSON Response Payload Box
    story.append(Paragraph("Sample API Response Payload (<code>GET /api/v1/threats?limit=1</code>):", h2_style))
    sample_json = (
        "{\n"
        '  "status": "success",\n'
        '  "total_returned": 1,\n'
        '  "threats": [\n'
        "    {\n"
        '      "id": "1002341991_4291",\n'
        '      "channel": "DarknetExploits_Daily",\n'
        '      "text": "New 0-day exploit released targeting CVE-2026-1189. Send 0.25 BTC to bc1qxy...",\n'
        '      "threat_level": "CRITICAL",\n'
        '      "category": "Zero-Day Exploit / Ransomware",\n'
        '      "iocs": {\n'
        '        "cves": ["CVE-2026-1189"],\n'
        '        "crypto_wallets": ["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"],\n'
        '        "urls": ["http://darkleak5h482hfe.onion/payload.bin"]\n'
        "      },\n"
        '      "timestamp": "2026-10-19T13:45:00Z"\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    t_code = Table([[Paragraph(sample_json.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)]], colWidths=[504])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#38bdf8")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#1e293b")),
    ]))
    story.append(t_code)
    story.append(Spacer(1, 14))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 4: ENTERPRISE INTEGRATION PATTERNS
    # =========================================================================
    story.append(Paragraph("4. How It Will Be Integrated (Practical Production Patterns)", h1_style))
    story.append(Paragraph(
        "Customers and internal stakeholders can integrate the CTI feed into their infrastructure through any of the "
        "following proven architectural models:",
        body_style
    ))

    # Pattern A: Python Continuous Polling Pipeline
    story.append(Paragraph("<b>Integration Pattern 1: Automated Continuous Ingestion Pipeline (Python / Worker)</b>", h2_style))
    story.append(Paragraph(
        "Ideal for internal security data lakes, threat analysis databases, or custom analyst alerting systems. "
        "The script queries the API every 60 seconds, gracefully handles rate limits, and ingests newly posted intelligence.",
        body_style
    ))

    py_code = (
        "import time, requests\n\n"
        'API_URL = "https://set-represents-suggested-leader.trycloudflare.com/api/v1/threats"\n'
        'HEADERS = {"X-API-Key": "dnet_live_YOUR_CUSTOMER_KEY"}\n\n'
        "def fetch_latest_threats():\n"
        "    params = {'limit': 50, 'min_level': 'HIGH'}\n"
        "    try:\n"
        "        resp = requests.get(API_URL, headers=HEADERS, params=params, timeout=15)\n"
        "        if resp.status_code == 200:\n"
        "            threats = resp.json().get('threats', [])\n"
        "            for threat in threats:\n"
        "                # Ingest into customer database or Slack/PagerDuty notification\n"
        "                print(f\"[{threat['threat_level']}] {threat['channel']}: {threat['id']}\")\n"
        "        elif resp.status_code == 429:\n"
        "            wait_sec = int(resp.headers.get('Retry-After', 10))\n"
        "            print(f'Rate limit reached. Backing off for {wait_sec}s.')\n"
        "            time.sleep(wait_sec)\n"
        "    except requests.RequestException as err:\n"
        "        print(f'Network error: {err}')\n"
    )
    t_py = Table([[Paragraph(py_code.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)]], colWidths=[504])
    t_py.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_code),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('BORDER', (0,0), (-1,-1), 1, c_border_code),
    ]))
    story.append(t_py)
    story.append(Spacer(1, 12))

    # Pattern B: SIEM / SOAR Ingestion
    story.append(Paragraph("<b>Integration Pattern 2: Enterprise SIEM / SOAR Ingestion (Splunk, Sentinel, QRadar)</b>", h2_style))
    story.append(Paragraph(
        "SOC teams configure their SIEM's Threat Intelligence Ingestion Add-on or HTTP Event Collector (HEC) "
        "to poll the <code>/api/v1/iocs</code> endpoint on an hourly or daily schedule. Extracted indicators (malicious domains, "
        "ransomware wallet addresses, CVE identifiers) are immediately pushed to firewalls (Palo Alto, Fortinet) "
        "and Web Application Firewalls (WAFs) for automated zero-touch blocking.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Pattern C: Web Application / Node.js Microservice
    story.append(Paragraph("<b>Integration Pattern 3: Custom Customer Portal / Microservice (Node.js / TypeScript)</b>", h2_style))
    js_code = (
        "// Node.js 18+ native fetch example\n"
        "const response = await fetch('https://set-represents-suggested-leader.trycloudflare.com/api/v1/threats?limit=25', {\n"
        "  headers: {\n"
        "    'X-API-Key': 'dnet_live_YOUR_CUSTOMER_KEY',\n"
        "    'Accept': 'application/json'\n"
        "  }\n"
        "});\n"
        "const data = await response.json();\n"
        "console.log(`Retrieved ${data.threats.length} threat records.`);"
    )
    t_js = Table([[Paragraph(js_code.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)]], colWidths=[504])
    t_js.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_code),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('BORDER', (0,0), (-1,-1), 1, c_border_code),
    ]))
    story.append(t_js)
    story.append(Spacer(1, 14))

    story.append(PageBreak())

    # =========================================================================
    # SECTION 5: STEP-BY-STEP VERIFICATION & TESTING PROTOCOL
    # =========================================================================
    story.append(Paragraph("5. Step-by-Step Verification Protocol for Leadership & QA", h1_style))
    story.append(Paragraph(
        "To satisfy project stakeholders and confirm the deployment readiness of the API, execute the following "
        "four-stage validation checklist:",
        body_style
    ))

    qa_steps = [
        ["Step", "Validation Objective", "Action & Command", "Expected Result"],
        [
            "1",
            "Interactive Swagger Exploration",
            "Navigate to <code>/docs</code> in browser, click <b>Authorize</b>, enter API Key, execute <code>GET /api/v1/threats</code>.",
            "HTTP 200 OK with live Telegram threat JSON payload."
        ],
        [
            "2",
            "Command-Line Tool Validation",
            "Run <code>python fetch_threats.py dnet_live_YOUR_KEY</code> from any workstation across the web.",
            "Formatted terminal output listing the top 100 messages."
        ],
        [
            "3",
            "Security & Auth Rejection",
            "Pass an invalid token: <code>curl -H 'X-API-Key: bad_key' &lt;URL&gt;/api/v1/threats</code>.",
            "HTTP 401 Unauthorized with descriptive JSON error."
        ],
        [
            "4",
            "Telemetry & Metrics Verification",
            "Check Web Dashboard at <code>/api-keys</code> after running steps 1 & 2.",
            "The <i>Usage & Requests</i> counter increments from '0 calls' to '2 calls'."
        ]
    ]
    t_qa = Table([[Paragraph(c, body_style) for c in row] for row in qa_steps], colWidths=[30, 114, 180, 180])
    t_qa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_qa)
    story.append(Spacer(1, 14))

    # Contact & Document Signoff
    signoff_box = (
        "<b>Document Sign-off & Support:</b><br/>"
        "• <b>Engineering Team:</b> Telegram Darknet Threat Intelligence Engineering Division<br/>"
        "• <b>API Version:</b> 1.0 (Stable)<br/>"
        "• <b>Support Contact:</b> Security Operations Center / Threat Intelligence Lead<br/>"
        "• <b>Classification:</b> TLP:WHITE — Approved for Customer Distribution & Partner Integration"
    )
    t_signoff = Table([[Paragraph(signoff_box, body_style)]], colWidths=[504])
    t_signoff.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_signoff)

    # Build PDF with custom NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Successfully compiled PDF to: {filename}")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else PDF_OUTPUT_PATH
    build_pdf(out_file)

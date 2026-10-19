import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.auth.api_keys import verify_customer_api_key
from app.db import mongodb
from app.db.mongodb import store
from app.evidence.generator import EvidenceEngine
from app.llm.regex_extractors import extract_indicators_with_regex

router = APIRouter(prefix="/v1", tags=["Customer Integration API (v1)"])


@router.get("/threats", summary="Feed of high-priority Darknet threat alerts")
async def get_threat_feed(
    min_level: str = Query("HIGH", description="Filter severity: ALL, LOW, MEDIUM, HIGH, CRITICAL"),
    sector: Optional[str] = Query(None, description="Industry sector filter (e.g. Banking, Healthcare, Government)"),
    keyword: Optional[str] = Query(None, description="Search keyword in threat content"),
    limit: int = Query(50, ge=1, le=200, description="Results per page (max 200)"),
    page: int = Query(1, ge=1, description="Page number"),
    client: Dict[str, Any] = Depends(verify_customer_api_key)
):
    """
    Export actionable threat intelligence alerts filtered for SIEM/SOAR/TIP systems.
    Requires header: X-API-Key: dnet_live_...
    """
    levels_map = {
        "ALL": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "LOW": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "MEDIUM": ["MEDIUM", "HIGH", "CRITICAL"],
        "HIGH": ["HIGH", "CRITICAL"],
        "CRITICAL": ["CRITICAL"]
    }
    clean_level = min_level.upper() if isinstance(min_level, str) else "HIGH"
    allowed_levels = levels_map.get(clean_level, ["HIGH", "CRITICAL"])
    query: Dict[str, Any] = {"threat_level": {"$in": allowed_levels}}

    if isinstance(sector, str) and sector.strip() and sector.lower() not in ("all", "all sectors"):
        query["detected_sector"] = {"$regex": re.escape(sector.strip()), "$options": "i"}

    if isinstance(keyword, str) and keyword.strip():
        clean_kw = keyword.strip()
        query["$or"] = [
            {"text": {"$regex": re.escape(clean_kw), "$options": "i"}},
            {"entities": {"$elemMatch": {"$regex": re.escape(clean_kw), "$options": "i"}}},
            {"iocs": {"$elemMatch": {"$regex": re.escape(clean_kw), "$options": "i"}}}
        ]

    skip = (page - 1) * limit
    raw_threats: List[Dict[str, Any]] = []
    total_count = 0

    if mongodb.mongo_available and mongodb.db is not None:
        try:
            total_count = await mongodb.db.messages.count_documents(query)
            cursor = mongodb.db.messages.find(query).sort("date", -1).skip(skip).limit(limit)
            async for m in cursor:
                m.pop("_id", None)
                raw_threats.append(m)
        except Exception as e:
            # Fallback to in-memory store
            raw_threats = []

    if not raw_threats:
        mem_filtered = [
            m for m in store.messages.values()
            if m.get("threat_level", "").upper() in allowed_levels
        ]
        if isinstance(sector, str) and sector.strip() and sector.lower() not in ("all", "all sectors"):
            sec_low = sector.strip().lower()
            mem_filtered = [m for m in mem_filtered if sec_low in str(m.get("detected_sector", "")).lower()]
        if isinstance(keyword, str) and keyword.strip():
            kw_low = keyword.strip().lower()
            mem_filtered = [m for m in mem_filtered if kw_low in str(m.get("text", "")).lower()]

        mem_filtered.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        total_count = len(mem_filtered)
        raw_threats = mem_filtered[skip : skip + limit]

    # Format structured items for customer consumption
    formatted_threats = []
    for t in raw_threats:
        # Ensure evidence proof exists
        try:
            EvidenceEngine.capture_message_evidence(t, keyword=keyword or "")
        except Exception:
            pass

        formatted_threats.append({
            "id": t.get("id"),
            "channel_title": t.get("channel_title") or t.get("channel_username") or "Telegram Channel",
            "channel_id": t.get("channel_id"),
            "threat_level": t.get("threat_level", "LOW"),
            "detected_sector": t.get("detected_sector") or "General Cyber Threat",
            "confidence_score": t.get("confidence_score") or 85,
            "date": t.get("date"),
            "text": t.get("text", ""),
            "iocs": t.get("iocs", []),
            "entities": t.get("entities", []),
            "evidence": {
                "hash_sha256": t.get("evidence_hash"),
                "telegram_link": t.get("telegram_link"),
                "screenshot_url": t.get("evidence_screenshot")
            }
        })

    return {
        "status": "success",
        "client": client.get("client_name"),
        "page": page,
        "limit": limit,
        "total_records": total_count,
        "returned": len(formatted_threats),
        "threats": formatted_threats
    }


# Module-level precision patterns for indicator validation
_IPV4_PATTERN = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
_CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.I)
_HASH_PATTERN = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")
_WALLET_PATTERN = re.compile(r"^(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$|^0x[a-fA-F0-9]{40}$|^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$")
_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+\.(?:onion|com|net|org|ru|to|xyz|cc|top|io|biz|info|site|tech|online)$", re.I)


def _clean_and_classify_ioc(val: str, hint_type: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Cleans whitespace/punctuation and strictly validates IOCs without misclassifying noise.
    Returns (ioc_type, clean_value) or (None, None).
    """
    s = val.strip().strip("<>\"'(),;:#*`")
    if not s or len(s) < 3:
        return None, None

    if _CVE_PATTERN.match(s):
        return "cve", s.upper()
    if _IPV4_PATTERN.match(s):
        if s not in ("0.0.0.0", "255.255.255.255"):
            return "ip", s
    if _HASH_PATTERN.match(s):
        return "hash", s.lower()
    if _WALLET_PATTERN.match(s):
        return "wallet", s
    if _EMAIL_PATTERN.match(s):
        return "email", s.lower()
    if _DOMAIN_PATTERN.match(s):
        clean_d = s.lstrip(".").rstrip(".")
        if "." in clean_d and not clean_d.startswith("-") and "/" not in clean_d:
            return "domain", clean_d.lower()
    if hint_type == "domain" and "." in s and "/" not in s and " " not in s and not s.startswith("-"):
        clean_d = s.lstrip(".").rstrip(".")
        if len(clean_d.split(".")[-1]) >= 2:
            return "domain", clean_d.lower()
    return None, None


@router.get("/iocs", summary="Structured Indicators of Compromise (IOC) Feed")
async def get_iocs_feed(
    ioc_type: str = Query("all", description="Filter IOC type: ip, domain, cve, hash, wallet, email, or all"),
    threat_level: Optional[str] = Query(None, description="Optional filter by threat level: HIGH, CRITICAL"),
    limit: int = Query(100, ge=1, le=500, description="Max IOCs to retrieve (up to 500)"),
    client: Dict[str, Any] = Depends(verify_customer_api_key)
):
    """
    Export deduplicated Indicators of Compromise (IOCs) for direct blocklist/SIEM ingestion.
    Extracts from persisted iocs or dynamically from message text when persisted data is absent.
    """
    normalized_type = (ioc_type.strip().lower() if isinstance(ioc_type, str) else "all") or "all"
    clean_threat_level = threat_level.strip().upper() if isinstance(threat_level, str) and threat_level.strip() else None
    effective_limit = min(500, max(1, limit))

    # Build targeted bounded MongoDB query
    mongo_query: Dict[str, Any] = {"text": {"$exists": True, "$ne": ""}}
    if clean_threat_level:
        mongo_query["threat_level"] = clean_threat_level

    if normalized_type == "cve":
        mongo_query["text"] = {"$regex": r"CVE-\d{4}", "$options": "i"}
    elif normalized_type == "ip":
        mongo_query["text"] = {"$regex": r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"}
    elif normalized_type == "hash":
        mongo_query["text"] = {"$regex": r"\b[a-fA-F0-9]{32,64}\b"}
    elif normalized_type == "wallet":
        mongo_query["text"] = {"$regex": r"(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}|0x[a-fA-F0-9]{40}"}
    elif normalized_type == "email":
        mongo_query["text"] = {"$regex": r"@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
    elif normalized_type == "domain":
        mongo_query["text"] = {"$regex": r"\.(?:onion|com|net|org|ru|to|xyz|cc|top|io)\b", "$options": "i"}
    else:
        # "all" - hints regex matches messages containing typical cyber threat indicators
        mongo_query["text"] = {
            "$regex": r"(?:CVE-\d{4}|https?://|(?:[0-9]{1,3}\.){3}[0-9]{1,3}|\.[a-zA-Z]{2,}\b|[a-fA-F0-9]{32,64}|(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}|0x[a-fA-F0-9]{40})",
            "$options": "i"
        }

    iocs_found = []
    seen = set()

    # 1. First, check in-memory threat intelligence store for recent items
    if hasattr(store, "threat_intel") and store.threat_intel:
        for intel in store.threat_intel.values():
            if clean_threat_level and intel.get("threat_level", "").upper() != clean_threat_level:
                continue
            m_id = str(intel.get("message_id") or intel.get("id", ""))
            m_ch = str(intel.get("channel_username", ""))
            m_date = str(intel.get("timestamp", ""))
            m_threat = str(intel.get("threat_level", "LOW"))

            candidates = []
            for cve in intel.get("cves", []): candidates.append((cve, "cve"))
            for h in intel.get("iocs", []): candidates.append((h, "hash"))
            for w in intel.get("crypto_wallets", []): candidates.append((w, "wallet"))
            for em in intel.get("emails", []): candidates.append((em, "email"))
            for dip in intel.get("domains_ips", []): candidates.append((dip, None))

            for raw_val, hint in candidates:
                v_type, clean_val = _clean_and_classify_ioc(str(raw_val), hint)
                if not v_type or not clean_val:
                    continue
                if normalized_type != "all" and v_type.lower() != normalized_type:
                    continue
                dedup_key = f"{v_type}:{clean_val.lower()}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                iocs_found.append({
                    "type": v_type,
                    "value": clean_val,
                    "threat_level": m_threat,
                    "source_channel": m_ch,
                    "first_seen": m_date,
                    "source_message_id": m_id
                })
                if len(iocs_found) >= effective_limit:
                    break
            if len(iocs_found) >= effective_limit:
                break

    # 2. Query MongoDB with bounded limit if more IOCs are needed
    if len(iocs_found) < effective_limit and mongodb.mongo_available and mongodb.db is not None:
        try:
            # Bounded scan: query at most max(200, effective_limit * 4) messages
            scan_limit = max(200, effective_limit * 4)
            cursor = mongodb.db.messages.find(mongo_query).sort("date", -1).limit(scan_limit)
            async for m in cursor:
                m_id = str(m.get("id", ""))
                m_ch = str(m.get("channel_title") or m.get("channel_username") or m.get("channel_id", ""))
                m_date = str(m.get("date", ""))
                m_threat = str(m.get("threat_level", "LOW"))

                raw_candidates = []
                # Check persisted iocs list if available
                if isinstance(m.get("iocs"), list) and m.get("iocs"):
                    for item in m["iocs"]:
                        raw_candidates.append((str(item), None))
                else:
                    # Dynamically extract from message text
                    text = m.get("text", "")
                    if text:
                        extracted = extract_indicators_with_regex(text)
                        for cve in extracted.get("cves", []): raw_candidates.append((cve, "cve"))
                        for h in extracted.get("iocs", []): raw_candidates.append((h, "hash"))
                        for w in extracted.get("crypto_wallets", []): raw_candidates.append((w, "wallet"))
                        for em in extracted.get("emails", []): raw_candidates.append((em, "email"))
                        for dip in extracted.get("domains_ips", []): raw_candidates.append((dip, None))
                        for u in extracted.get("urls", []):
                            try:
                                netloc = urlparse(u).netloc
                                if netloc and "." in netloc and ":" not in netloc:
                                    raw_candidates.append((netloc, "domain"))
                            except Exception:
                                pass

                for raw_val, hint in raw_candidates:
                    v_type, clean_val = _clean_and_classify_ioc(str(raw_val), hint)
                    if not v_type or not clean_val:
                        continue
                    if normalized_type != "all" and v_type.lower() != normalized_type:
                        continue
                    dedup_key = f"{v_type}:{clean_val.lower()}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)
                    iocs_found.append({
                        "type": v_type,
                        "value": clean_val,
                        "threat_level": m_threat,
                        "source_channel": m_ch,
                        "first_seen": m_date,
                        "source_message_id": m_id
                    })
                    if len(iocs_found) >= effective_limit:
                        break
                if len(iocs_found) >= effective_limit:
                    break
        except Exception:
            pass

    # 3. Fallback to in-memory messages if needed and MongoDB returned nothing
    if len(iocs_found) < effective_limit and not iocs_found and hasattr(store, "messages") and store.messages:
        for m in list(store.messages.values())[:max(100, effective_limit * 2)]:
            if clean_threat_level and m.get("threat_level", "").upper() != clean_threat_level:
                continue
            m_id = str(m.get("id", ""))
            m_ch = str(m.get("channel_title") or m.get("channel_username") or m.get("channel_id", ""))
            m_date = str(m.get("date", ""))
            m_threat = str(m.get("threat_level", "LOW"))

            raw_candidates = []
            if isinstance(m.get("iocs"), list) and m.get("iocs"):
                for item in m["iocs"]:
                    raw_candidates.append((str(item), None))
            else:
                text = m.get("text", "")
                if text:
                    extracted = extract_indicators_with_regex(text)
                    for cve in extracted.get("cves", []): raw_candidates.append((cve, "cve"))
                    for h in extracted.get("iocs", []): raw_candidates.append((h, "hash"))
                    for w in extracted.get("crypto_wallets", []): raw_candidates.append((w, "wallet"))
                    for em in extracted.get("emails", []): raw_candidates.append((em, "email"))
                    for dip in extracted.get("domains_ips", []): raw_candidates.append((dip, None))

            for raw_val, hint in raw_candidates:
                v_type, clean_val = _clean_and_classify_ioc(str(raw_val), hint)
                if not v_type or not clean_val:
                    continue
                if normalized_type != "all" and v_type.lower() != normalized_type:
                    continue
                dedup_key = f"{v_type}:{clean_val.lower()}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                iocs_found.append({
                    "type": v_type,
                    "value": clean_val,
                    "threat_level": m_threat,
                    "source_channel": m_ch,
                    "first_seen": m_date,
                    "source_message_id": m_id
                })
                if len(iocs_found) >= effective_limit:
                    break
            if len(iocs_found) >= effective_limit:
                break

    return {
        "status": "success",
        "client": client.get("client_name"),
        "ioc_type": ioc_type,
        "count": len(iocs_found),
        "iocs": iocs_found
    }


@router.get("/evidence/{message_id}", summary="Cryptographic evidence verification record")
async def get_message_evidence_record(
    message_id: str,
    client: Dict[str, Any] = Depends(verify_customer_api_key)
):
    """
    Verify the chain of custody and retrieve cryptographic proof for an intercepted message.
    """
    msg = None
    if mongodb.mongo_available and mongodb.db is not None:
        try:
            msg = await mongodb.db.messages.find_one({"id": message_id})
            if msg:
                msg.pop("_id", None)
        except Exception:
            pass

    if not msg:
        msg = store.messages.get(message_id)

    if not msg:
        for m in store.messages.values():
            if m.get("id") == message_id:
                msg = m
                break

    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message ID '{message_id}' not found."
        )

    # Compute & verify evidence proof
    evidence = EvidenceEngine.capture_message_evidence(msg)

    return {
        "status": "verified",
        "client": client.get("client_name"),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "message_id": msg.get("id"),
        "channel_title": msg.get("channel_title"),
        "channel_id": msg.get("channel_id"),
        "sender": msg.get("sender"),
        "timestamp": msg.get("date"),
        "text": msg.get("text"),
        "threat_level": msg.get("threat_level"),
        "detected_sector": msg.get("detected_sector"),
        "iocs": msg.get("iocs", []),
        "evidence": {
            "algorithm": "SHA-256",
            "hash": evidence.get("evidence_hash"),
            "telegram_deep_link": evidence.get("telegram_link"),
            "screenshot_proof_url": evidence.get("evidence_screenshot")
        }
    }


@router.get("/stats", summary="Telemetry & Integration Health Statistics")
async def get_integration_stats(
    client: Dict[str, Any] = Depends(verify_customer_api_key)
):
    """
    System statistics for client health monitoring and ingestion pipelines.
    """
    total_messages = 0
    total_channels = 0
    critical_threats = 0

    if mongodb.mongo_available and mongodb.db is not None:
        try:
            total_messages = await mongodb.db.messages.count_documents({})
            total_channels = await mongodb.db.channels.count_documents({})
            critical_threats = await mongodb.db.messages.count_documents({"threat_level": "CRITICAL"})
        except Exception:
            pass

    if total_messages == 0:
        total_messages = len(store.messages)
        total_channels = len(store.channels)
        critical_threats = sum(1 for m in store.messages.values() if m.get("threat_level") == "CRITICAL")

    return {
        "status": "online",
        "client": client.get("client_name"),
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "total_intercepted_messages": total_messages,
        "active_monitored_channels": total_channels,
        "critical_threats_logged": critical_threats,
        "supported_formats": ["JSON", "SIEM-compatible alerts", "IOC lists"]
    }

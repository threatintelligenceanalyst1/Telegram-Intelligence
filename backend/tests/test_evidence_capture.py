import json
import zipfile
import pytest
from pathlib import Path
from app.evidence.capture_service import (
    EvidenceCaptureService,
    canonical_json_bytes,
    compute_sha256
)
from app.db import mongodb
from app.db.mongodb import store
from app.config import settings



def test_canonical_json_bytes_and_sha256():
    """Verify that canonical JSON excludes ephemeral fields and produces identical SHA-256."""
    doc1 = {
        "id": "ch1_100",
        "channel_id": "-100123",
        "sender": "ThreatActor",
        "text": "DB dump for sale",
        "date": "2026-10-19T10:00:00Z",
        "evidence_hash": "should_be_ignored",
        "evidence_screenshot": "also_ignored.png"
    }

    doc2 = {
        "date": "2026-10-19T10:00:00Z",
        "text": "DB dump for sale",
        "sender": "ThreatActor",
        "channel_id": "-100123",
        "id": "ch1_100",
        "_id": "mongo_object_id_ignored"
    }

    b1 = canonical_json_bytes(doc1)
    b2 = canonical_json_bytes(doc2)

    assert b1 == b2, "Canonical bytes should match regardless of key order or ephemeral fields"
    h1 = compute_sha256(b1)
    h2 = compute_sha256(b2)
    assert h1 == h2
    assert len(h1) == 64


def test_build_embed_url_validation():
    """Verify URL construction rules and rejection of private channel IDs."""
    assert EvidenceCaptureService.extract_channel_username("darknet_leaks", None) == "darknet_leaks"
    assert EvidenceCaptureService.extract_channel_username("@darknet_leaks", None) == "darknet_leaks"
    assert EvidenceCaptureService.extract_channel_username("-1001234567890", None) is None
    assert EvidenceCaptureService.extract_channel_username("1234567", None) is None
    assert EvidenceCaptureService.extract_channel_username("invalid username with space", None) is None

    # Valid public username
    url, err = EvidenceCaptureService.build_embed_url("telegram_news", None, "12345")
    assert url == "https://t.me/telegram_news/12345?embed=1"
    assert err is None

    # Strips leading @
    url2, err2 = EvidenceCaptureService.build_embed_url("@telegram_news", None, "ch_12345")
    assert url2 == "https://t.me/telegram_news/12345?embed=1"
    assert err2 is None

    # Private numeric ID returns None
    url_private, err_priv = EvidenceCaptureService.build_embed_url("-100192837465", "-100192837465", "100")
    assert url_private is None
    assert "public username" in err_priv



@pytest.mark.asyncio
async def test_evidence_creation_and_verification_private_channel():
    """Verify graceful handling and audit logging when channel is private."""
    msg_id = "test_private_msg_001"
    msg_doc = {
        "id": msg_id,
        "channel_id": "-100123456789",
        "channel_username": "-100123456789",
        "sender": "Anonymous",
        "text": "Private channel alert message",
        "date": "2026-10-19T12:00:00Z",
        "threat_level": "HIGH"
    }
    store.messages[msg_id] = msg_doc

    record = await EvidenceCaptureService.capture_and_store_evidence(msg_doc, priority=True)

    assert record["message_id"] == msg_id
    assert record["capture_status"] == "failed"
    assert "public username" in record["failure_reason"]
    assert record["message_sha256"] is not None
    assert record["manifest_sha256"] is not None

    # Check custody log
    custody = store.evidence_audit_log
    assert any(log.get("message_id") == msg_id and log.get("event") == "captured" for log in custody)

    # Verify integrity passes for message data even if screenshot wasn't captured
    verification = await EvidenceCaptureService.verify_evidence(msg_id)
    assert verification["verified"] is True
    assert verification["message_hash_match"] is True
    assert verification["manifest_hash_match"] is True
    assert verification["is_valid"] is True



@pytest.mark.asyncio
async def test_evidence_tamper_detection(tmp_path):
    """Verify that tampering with stored raw message JSON triggers a verification failure."""
    msg_id = "test_tamper_msg_002"
    msg_doc = {
        "id": msg_id,
        "channel_id": "-100999888",
        "channel_username": "secure_intel",
        "sender": "Insider",
        "text": "Original authentic message content",
        "date": "2026-10-19T12:00:00Z",
        "threat_level": "CRITICAL"
    }
    store.messages[msg_id] = msg_doc

    record = await EvidenceCaptureService.capture_and_store_evidence(msg_doc)
    assert record["capture_status"] in ("captured", "failed")

    # Tamper with raw message data in the stored record
    if mongodb.mongo_available and mongodb.db is not None:
        await mongodb.db.evidence_records.update_one(
            {"message_id": msg_id},
            {"$set": {"raw_message_json.text": "TAMPERED ILLEGAL CONTENT"}}
        )
    else:
        for r in store.evidence_records:
            if r.get("message_id") == msg_id:
                r["raw_message_json"]["text"] = "TAMPERED ILLEGAL CONTENT"
                break

    # Re-run verification
    verification = await EvidenceCaptureService.verify_evidence(msg_id)
    assert verification["verified"] is False
    assert verification["message_hash_match"] is False
    assert verification["is_valid"] is False


@pytest.mark.asyncio
async def test_evidence_bundle_generation():
    """Verify ZIP bundle generation contains expected files and manifest."""
    from io import BytesIO
    msg_id = "test_bundle_msg_003"
    msg_doc = {
        "id": msg_id,
        "channel_id": "-100777",
        "channel_username": "threat_exchange",
        "sender": "CyberAnalyst",
        "text": "Leaked credentials list",
        "date": "2026-10-19T12:00:00Z",
        "threat_level": "HIGH"
    }
    store.messages[msg_id] = msg_doc

    await EvidenceCaptureService.capture_and_store_evidence(msg_doc)
    zip_bytes, filename = await EvidenceCaptureService.generate_evidence_bundle(msg_id)

    assert zip_bytes is not None
    assert len(zip_bytes) > 0
    assert filename.endswith(".zip")

    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "message.json" in namelist
        assert "manifest.json" in namelist
        assert "README.txt" in namelist

        manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest_data["message_id"] == msg_id
        assert "message_sha256" in manifest_data



def test_api_evidence_endpoints(client):
    """Test REST API evidence routes."""
    msg_id = "test_api_msg_004"
    store.messages[msg_id] = {
        "id": msg_id,
        "channel_id": "-100555",
        "channel_username": "darknet_hub",
        "sender": "HackerX",
        "text": "Ransomware payload distributed",
        "date": "2026-10-19T14:00:00Z",
        "threat_level": "CRITICAL"
    }

    # 1. GET /api/v1/threats/{id}/evidence
    res_ev = client.get(f"/api/v1/threats/{msg_id}/evidence")
    assert res_ev.status_code == 200
    data = res_ev.json()
    assert data["status"] == "success"
    assert data["evidence"]["message_id"] == msg_id

    # 2. GET /api/v1/threats/{id}/evidence/verify
    res_vf = client.get(f"/api/v1/threats/{msg_id}/evidence/verify")
    assert res_vf.status_code == 200
    vf_data = res_vf.json()
    assert vf_data["status"] == "success"
    assert vf_data["verification"]["verified"] is True

    # 3. GET /api/v1/threats/{id}/evidence/bundle
    res_bd = client.get(f"/api/v1/threats/{msg_id}/evidence/bundle")
    assert res_bd.status_code == 200
    assert res_bd.headers["content-type"] == "application/zip"

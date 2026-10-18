import hashlib
import secrets
import uuid
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import Security, HTTPException, status, Header
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from ..db import mongodb
from ..db.mongodb import store

logger = logging.getLogger("darknet_monitor.auth")

# In-memory sliding window rate-limit tracker: { key_id: [timestamp, timestamp, ...] }
_rate_limit_tracker: Dict[str, List[float]] = defaultdict(list)

# Fallback store initialization
if not hasattr(store, "api_keys"):
    store.api_keys = {}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


class ApiKeyService:
    """Service to create, validate, and revoke customer/client integration API keys."""

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def create_key(
        cls,
        client_name: str,
        description: str = "",
        scopes: Optional[List[str]] = None,
        rate_limit: int = 120
    ) -> Dict[str, Any]:
        """
        Generates a new secure API key with prefix 'dnet_live_'.
        The raw key is returned ONCE for the user to copy.
        Only the SHA-256 hash is stored for verification.
        """
        if not client_name or not client_name.strip():
            raise ValueError("Client or tool name is required.")

        raw_secret = secrets.token_hex(20)
        raw_key = f"dnet_live_{raw_secret}"
        key_hash = cls.hash_key(raw_key)
        key_id = f"key_{uuid.uuid4().hex[:12]}"
        masked_key = f"dnet_live_{raw_secret[:4]}...{raw_secret[-4:]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        doc = {
            "id": key_id,
            "client_name": client_name.strip(),
            "description": description.strip() if description else "Customer SIEM/API Integration",
            "key_hash": key_hash,
            "key_masked": masked_key,
            "key_prefix": raw_key[:14],
            "scopes": scopes or ["read:all"],
            "is_active": True,
            "created_at": now_iso,
            "last_used_at": None,
            "total_requests": 0,
            "rate_limit_per_minute": rate_limit
        }

        # Store in MongoDB if available
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                await mongodb.db.api_keys.insert_one(dict(doc))
            except Exception as e:
                logger.error(f"Failed to persist API key to MongoDB: {e}")

        # Always mirror in memory for zero-downtime access (store untouched copy)
        store.api_keys[key_id] = dict(doc)

        logger.info(f"🔑 Created new API key '{masked_key}' for client '{client_name}'")

        # Return document copy with raw_key for initial display
        result = dict(doc)
        result.pop("key_hash", None)
        result.pop("_id", None)
        result["raw_key"] = raw_key
        return result

    @classmethod
    async def list_keys(cls) -> List[Dict[str, Any]]:
        """List all active and revoked API keys (safely masked)."""
        keys_list: List[Dict[str, Any]] = []

        if mongodb.mongo_available and mongodb.db is not None:
            try:
                cursor = mongodb.db.api_keys.find({}).sort("created_at", -1)
                async for k in cursor:
                    safe_k = dict(k)
                    safe_k.pop("_id", None)
                    safe_k.pop("key_hash", None)
                    keys_list.append(safe_k)
                return keys_list
            except Exception as e:
                logger.error(f"Error querying API keys from MongoDB: {e}")

        # Fallback to in-memory store
        for k in store.api_keys.values():
            safe_k = dict(k)
            safe_k.pop("key_hash", None)
            safe_k.pop("_id", None)
            keys_list.append(safe_k)

        keys_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return keys_list

    @classmethod
    async def delete_key(cls, key_id: str) -> bool:
        """Permanently delete an API key."""
        deleted = False
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                res = await mongodb.db.api_keys.delete_one({"id": key_id})
                deleted = res.deleted_count > 0
            except Exception as e:
                logger.error(f"Failed to delete API key {key_id} from MongoDB: {e}")

        if key_id in store.api_keys:
            del store.api_keys[key_id]
            deleted = True

        return deleted

    @classmethod
    async def toggle_key_status(cls, key_id: str) -> Optional[Dict[str, Any]]:
        """Enable or disable an API key."""
        target = None
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                target = await mongodb.db.api_keys.find_one({"id": key_id})
                if target:
                    new_status = not target.get("is_active", True)
                    await mongodb.db.api_keys.update_one(
                        {"id": key_id},
                        {"$set": {"is_active": new_status}}
                    )
                    target["is_active"] = new_status
            except Exception as e:
                logger.error(f"Error toggling key {key_id} in MongoDB: {e}")

        if not target and key_id in store.api_keys:
            target = store.api_keys[key_id]
            target["is_active"] = not target.get("is_active", True)

        if target:
            if key_id in store.api_keys:
                store.api_keys[key_id]["is_active"] = target["is_active"]
            # Create a shallow copy before stripping sensitive/internal fields
            clean_target = dict(target)
            clean_target.pop("_id", None)
            clean_target.pop("key_hash", None)
            return clean_target
        return None

    @classmethod
    async def verify_raw_key(cls, raw_key: str) -> Optional[Dict[str, Any]]:
        """Verify raw API key, check active status, and update telemetry."""
        if not raw_key or not raw_key.startswith("dnet_live_"):
            return None

        key_hash = cls.hash_key(raw_key)
        now_iso = datetime.now(timezone.utc).isoformat()

        target = None
        if mongodb.mongo_available and mongodb.db is not None:
            try:
                target = await mongodb.db.api_keys.find_one({"key_hash": key_hash})
                if target:
                    if not target.get("is_active", True):
                        return None
                    # Update usage telemetry asynchronously
                    await mongodb.db.api_keys.update_one(
                        {"id": target["id"]},
                        {
                            "$set": {"last_used_at": now_iso},
                            "$inc": {"total_requests": 1}
                        }
                    )
                    target["last_used_at"] = now_iso
                    target["total_requests"] = target.get("total_requests", 0) + 1
            except Exception as e:
                logger.error(f"MongoDB verification error: {e}")

        # Fallback / In-Memory match
        if not target:
            for k in store.api_keys.values():
                if k.get("key_hash") == key_hash and k.get("is_active", True):
                    k["last_used_at"] = now_iso
                    k["total_requests"] = k.get("total_requests", 0) + 1
                    target = k
                    break

        if target:
            # Create a shallow copy so original stored dict in memory retains key_hash
            clean_target = dict(target)
            clean_target.pop("_id", None)
            clean_target.pop("key_hash", None)
            return clean_target
        return None


async def verify_customer_api_key(
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    FastAPI security dependency to authenticate customer tool requests.
    Supports:
      1. X-API-Key: dnet_live_...
      2. Authorization: Bearer dnet_live_...
      3. ?api_key=dnet_live_...
    """
    key_candidate = header_key or query_key

    if not key_candidate and authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            key_candidate = parts[1]
        elif len(parts) == 1 and parts[0].startswith("dnet_live_"):
            key_candidate = parts[0]

    if not key_candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Missing API Key",
                "message": "Authenticate using header 'X-API-Key: dnet_live_...', 'Authorization: Bearer <key>', or query '?api_key=<key>'."
            }
        )

    client_record = await ApiKeyService.verify_raw_key(key_candidate)
    if not client_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Invalid or Revoked API Key",
                "message": "The provided API key does not exist or has been disabled by the administrator."
            }
        )

    # Active Rate Limiting Enforcement (Sliding 60-second window)
    key_id = client_record.get("id")
    rate_limit = int(client_record.get("rate_limit_per_minute", 120))
    now = time.time()
    window_start = now - 60.0

    # Prune timestamps older than 60 seconds
    timestamps = [t for t in _rate_limit_tracker[key_id] if t > window_start]
    if len(timestamps) >= rate_limit:
        retry_after = max(1, int(60 - (now - timestamps[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate Limit Exceeded",
                "message": f"Rate limit of {rate_limit} requests/minute exceeded for this API key.",
                "retry_after_seconds": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )

    timestamps.append(now)
    _rate_limit_tracker[key_id] = timestamps

    return client_record

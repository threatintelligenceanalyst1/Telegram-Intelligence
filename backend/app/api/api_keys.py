from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from app.auth.api_keys import ApiKeyService
from app.auth.admin_guard import verify_admin_access

router = APIRouter(
    prefix="/api-keys",
    tags=["API Key Management"],
    dependencies=[Depends(verify_admin_access)]
)


class CreateApiKeyRequest(BaseModel):
    client_name: str = Field(..., description="Customer, team, or SIEM tool name (e.g. 'Bank SOC Splunk Ingestion')")
    description: Optional[str] = Field(default="", description="Integration details or notes")
    scopes: Optional[List[str]] = Field(default=["read:all"], description="Allowed API scopes")
    rate_limit: Optional[int] = Field(default=120, description="Max requests per minute")


@router.get("", summary="List all customer API keys")
async def list_api_keys():
    """Retrieve list of generated customer API keys with safe masking."""
    keys = await ApiKeyService.list_keys()
    return {"keys": keys, "total": len(keys)}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Generate new customer API key")
async def create_api_key(req: CreateApiKeyRequest):
    """
    Generate a new customer API key (dnet_live_...).
    NOTE: The raw key will only be shown ONCE in this response.
    """
    try:
        new_key_data = await ApiKeyService.create_key(
            client_name=req.client_name,
            description=req.description or "",
            scopes=req.scopes or ["read:all"],
            rate_limit=req.rate_limit or 120
        )
        return {
            "success": True,
            "message": "API Key generated successfully. Save this key now; it will not be displayed again.",
            "api_key": new_key_data
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate API key: {e}")


@router.patch("/{key_id}/toggle", summary="Toggle active status of an API key")
async def toggle_api_key(key_id: str):
    """Enable or disable an API key."""
    updated = await ApiKeyService.toggle_key_status(key_id)
    if not updated:
        raise HTTPException(status_code=404, detail="API key not found.")
    return {
        "success": True,
        "is_active": updated.get("is_active"),
        "key": updated
    }


@router.delete("/{key_id}", summary="Revoke and delete an API key")
async def delete_api_key(key_id: str):
    """Permanently delete an API key."""
    success = await ApiKeyService.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found.")
    return {"success": True, "message": "API key revoked and deleted successfully."}

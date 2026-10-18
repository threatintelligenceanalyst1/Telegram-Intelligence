import os
from fastapi import Request, HTTPException, status

ADMIN_API_SECRET = os.getenv("ADMIN_API_SECRET", "").strip()


async def verify_admin_access(request: Request):
    """
    Security Guard for Administrative Endpoints (/api/api-keys, channel operations).
    Enforces strict access isolation:
    1. Rejects any public customer attempting to manage API keys or database records.
    2. Calls arriving over the public internet / Cloudflare Tunnel are automatically blocked
       unless a valid X-Admin-Secret header is provided.
    3. Local development and internal dashboard calls (127.0.0.1 / localhost) remain permitted.
    """
    # Detect if traffic arrived through Cloudflare Tunnel or public reverse proxy
    is_public_proxy = bool(
        request.headers.get("cf-connecting-ip")
        or request.headers.get("cf-ray")
        or request.headers.get("x-forwarded-for")
    )
    client_host = request.client.host if request.client else ""

    admin_header = request.headers.get("X-Admin-Secret", "").strip()

    # 1. If an ADMIN_API_SECRET is configured in environment, validate it
    if ADMIN_API_SECRET:
        if admin_header and admin_header == ADMIN_API_SECRET:
            return True
        # If no header, only allow true loopback without public proxy
        if client_host in ("127.0.0.1", "::1", "localhost") and not is_public_proxy:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Forbidden",
                "message": "Administrative access denied. Invalid or missing X-Admin-Secret header."
            }
        )

    # 2. If no ADMIN_API_SECRET is set, strictly block all public proxy / tunnel requests
    if is_public_proxy:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Forbidden",
                "message": "Administrative management endpoints are restricted from public internet access."
            }
        )

    return True

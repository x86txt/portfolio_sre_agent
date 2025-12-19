from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.triage.rate_limit import rate_limiter

router = APIRouter()


@router.post("/admin/unblock-ip")
async def unblock_ip(ip_address: str = Query(..., description="IP address to unblock")) -> JSONResponse:
    """
    Admin endpoint to unblock/reset rate limit for a specific IP address.
    
    This removes all rate limit entries for the given IP, effectively resetting
    their rate limit counter to 0.
    
    **Note**: This endpoint has no authentication. In production, you should
    add authentication or restrict access to trusted IPs.
    """
    if not ip_address or not ip_address.strip():
        raise HTTPException(status_code=400, detail="IP address cannot be empty")
    
    ip_address = ip_address.strip()
    
    # Basic IP format validation (simple check)
    if not ip_address.replace(".", "").replace(":", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    
    success = rate_limiter.unblock_ip(ip_address)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to unblock IP address. Rate limiting may be unavailable.",
        )
    
    return JSONResponse(
        content={
            "success": True,
            "message": f"IP address {ip_address} has been unblocked. Rate limit reset.",
            "ip_address": ip_address,
        }
    )


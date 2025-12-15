"""
Camera Discovery API Endpoints (Story P5-2.1)

ONVIF WS-Discovery endpoints for camera auto-discovery:
- POST /api/v1/cameras/discover - Trigger network scan for ONVIF cameras

Architecture Reference: docs/architecture/phase-5-additions.md
PRD Reference: docs/PRD-phase5.md (FR13, FR14)
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.discovery import (
    DiscoveredDevice,
    DiscoveryRequest,
    DiscoveryResponse,
)
from app.services.onvif_discovery_service import (
    get_onvif_discovery_service,
    WSDISCOVERY_AVAILABLE,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["discovery"])


class DiscoveryStatusResponse(BaseModel):
    """Response for discovery status check."""
    available: bool = Field(..., description="Whether ONVIF discovery is available")
    library_installed: bool = Field(..., description="Whether WSDiscovery is installed")
    message: str = Field(..., description="Status message")


@router.get(
    "/discover/status",
    response_model=DiscoveryStatusResponse,
    summary="Check discovery availability",
    description="Check if ONVIF camera discovery feature is available"
)
async def get_discovery_status() -> DiscoveryStatusResponse:
    """
    Check if ONVIF discovery is available.

    Returns availability status and whether required libraries are installed.
    """
    service = get_onvif_discovery_service()

    if service.is_available:
        return DiscoveryStatusResponse(
            available=True,
            library_installed=True,
            message="ONVIF camera discovery is available"
        )
    else:
        return DiscoveryStatusResponse(
            available=False,
            library_installed=False,
            message=(
                "ONVIF discovery unavailable: WSDiscovery package not installed. "
                "Install with: pip install WSDiscovery"
            )
        )


@router.post(
    "/discover",
    response_model=DiscoveryResponse,
    summary="Discover ONVIF cameras",
    description="Scan local network for ONVIF-compatible cameras using WS-Discovery"
)
async def discover_cameras(
    request: Optional[DiscoveryRequest] = None
) -> DiscoveryResponse:
    """
    Discover ONVIF cameras on the local network.

    Sends WS-Discovery probes to multicast address 239.255.255.250:3702
    and collects responses from ONVIF Network Video Transmitters.

    Args:
        request: Optional discovery parameters (timeout)

    Returns:
        DiscoveryResponse with list of discovered devices

    Raises:
        503: If discovery service is unavailable
        500: If discovery fails due to network error
    """
    service = get_onvif_discovery_service()

    # Check availability
    if not service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "discovery_unavailable",
                "message": (
                    "ONVIF discovery unavailable: WSDiscovery package not installed. "
                    "Install with: pip install WSDiscovery"
                )
            }
        )

    # Get timeout from request or use default
    timeout = 10
    if request and request.timeout:
        timeout = request.timeout

    logger.info(f"Starting ONVIF camera discovery (timeout: {timeout}s)")

    try:
        result = await service.discover_cameras_with_result(timeout=timeout)

        return DiscoveryResponse(
            status=result.status,
            duration_ms=result.duration_ms,
            devices=result.devices,
            device_count=len(result.devices),
            error_message=result.error
        )

    except Exception as e:
        logger.error(f"Discovery endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "discovery_failed",
                "message": f"Discovery failed: {str(e)}"
            }
        )


@router.post(
    "/discover/clear-cache",
    summary="Clear discovery cache",
    description="Clear cached discovery results to force a fresh scan"
)
async def clear_discovery_cache() -> dict:
    """
    Clear the discovery results cache.

    Forces the next discovery scan to perform a fresh network probe
    instead of returning cached results.

    Returns:
        Success message
    """
    service = get_onvif_discovery_service()
    service.clear_cache()

    logger.info("Discovery cache cleared")

    return {"status": "success", "message": "Discovery cache cleared"}

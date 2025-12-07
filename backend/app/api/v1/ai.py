"""
AI Service API endpoints

Provides:
- GET /ai/usage - Usage statistics and cost tracking
- GET /ai/capabilities - Provider capability information (Story P3-4.1)
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
import logging

from app.schemas.ai import AIUsageStatsResponse, AICapabilitiesResponse
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/usage", response_model=AIUsageStatsResponse)
async def get_ai_usage_stats(
    start_date: Optional[str] = Query(
        None,
        description="Start date filter (ISO 8601 format: YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date filter (ISO 8601 format: YYYY-MM-DD)"
    )
):
    """
    Get AI usage statistics and cost tracking.

    Returns aggregated statistics including:
    - Total API calls (successful and failed)
    - Token usage
    - Cost estimates
    - Average response time
    - Per-provider breakdown

    Supports optional date range filtering.

    Example:
        GET /api/v1/ai/usage
        GET /api/v1/ai/usage?start_date=2025-11-01&end_date=2025-11-16
    """
    # Parse dates if provided
    start_datetime = datetime.fromisoformat(start_date) if start_date else None
    end_datetime = datetime.fromisoformat(end_date) if end_date else None

    # Get stats from AI service
    stats = ai_service.get_usage_stats(start_datetime, end_datetime)

    logger.info(
        f"AI usage stats requested: {stats['total_calls']} calls, "
        f"${stats['total_cost']:.4f} cost"
    )

    return AIUsageStatsResponse(**stats)


@router.get("/capabilities", response_model=AICapabilitiesResponse)
async def get_ai_capabilities():
    """
    Get AI provider capabilities (Story P3-4.1).

    Returns capability information for all AI providers, including:
    - Whether provider supports native video input
    - Maximum video duration and file size limits
    - Supported video formats
    - Maximum images for multi-frame analysis
    - Whether provider has an API key configured

    This endpoint helps determine which analysis modes are available
    based on the current provider configuration.

    Example:
        GET /api/v1/ai/capabilities

    Response:
        {
            "providers": {
                "openai": {"video": true, "max_video_duration": 60, ...},
                "claude": {"video": false, ...},
                ...
            }
        }
    """
    # Get capabilities from AI service
    capabilities = ai_service.get_all_capabilities()

    # Count video-capable providers
    video_providers = [p for p, caps in capabilities.items() if caps.get("video")]
    configured_video_providers = [
        p for p, caps in capabilities.items()
        if caps.get("video") and caps.get("configured")
    ]

    logger.info(
        f"AI capabilities requested: {len(video_providers)} video-capable providers, "
        f"{len(configured_video_providers)} configured",
        extra={
            "video_capable_providers": video_providers,
            "configured_video_providers": configured_video_providers
        }
    )

    return AICapabilitiesResponse(providers=capabilities)

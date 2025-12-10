"""
Push Notification API endpoints (Story P4-1.1)

Endpoints for Web Push subscription management:
- GET /api/v1/push/vapid-public-key - Get VAPID public key for frontend
- POST /api/v1/push/subscribe - Register push subscription
- DELETE /api/v1/push/subscribe - Unsubscribe
- GET /api/v1/push/subscriptions - List subscriptions (admin)
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.push_subscription import PushSubscription
from app.utils.vapid import get_vapid_public_key
from app.services.push_notification_service import PushNotificationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/push",
    tags=["push-notifications"]
)


# ============================================================================
# Pydantic Schemas
# ============================================================================


class SubscriptionKeys(BaseModel):
    """Browser push subscription keys."""
    p256dh: str = Field(..., description="P-256 public key for message encryption")
    auth: str = Field(..., description="Authentication secret")


class SubscribeRequest(BaseModel):
    """Request body for push subscription registration."""
    endpoint: str = Field(..., description="Push service endpoint URL")
    keys: SubscriptionKeys = Field(..., description="Encryption keys")
    user_agent: Optional[str] = Field(None, description="Browser user agent")

    class Config:
        json_schema_extra = {
            "example": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/abc123...",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_...",
                    "auth": "tBHItJI5svbpez7KI4CCXg=="
                },
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0...)"
            }
        }


class UnsubscribeRequest(BaseModel):
    """Request body for push unsubscription."""
    endpoint: str = Field(..., description="Push service endpoint URL to unsubscribe")


class SubscriptionResponse(BaseModel):
    """Response for subscription operations."""
    id: str = Field(..., description="Subscription UUID")
    endpoint: str = Field(..., description="Truncated endpoint for display")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "endpoint": "https://fcm.googleapis.com/...xyz",
                "created_at": "2025-12-10T10:30:00Z"
            }
        }


class VapidPublicKeyResponse(BaseModel):
    """Response containing VAPID public key."""
    public_key: str = Field(..., description="VAPID public key in URL-safe base64")


class SubscriptionListItem(BaseModel):
    """Single subscription in list response."""
    id: str
    user_id: Optional[str]
    endpoint: str
    user_agent: Optional[str]
    created_at: Optional[str]
    last_used_at: Optional[str]


class SubscriptionsListResponse(BaseModel):
    """Response listing all subscriptions."""
    subscriptions: List[SubscriptionListItem]
    total: int


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_key(db: Session = Depends(get_db)):
    """
    Get VAPID public key for push subscription.

    The frontend uses this key as the `applicationServerKey` when calling
    `pushManager.subscribe()`. Keys are generated automatically on first request.

    **Response:**
    ```json
    {
        "public_key": "BEl62iUYgUivxIkv69yViEuiBIa-..."
    }
    ```

    **Status Codes:**
    - 200: Success
    - 500: Key generation failed
    """
    try:
        public_key = get_vapid_public_key(db)

        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get or generate VAPID keys"
            )

        return VapidPublicKeyResponse(public_key=public_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting VAPID public key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve VAPID public key"
        )


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    request: SubscribeRequest,
    db: Session = Depends(get_db)
):
    """
    Register a push subscription.

    Stores the browser's push subscription for receiving notifications.
    If the endpoint already exists, the subscription is updated (upsert).

    **Request Body:**
    ```json
    {
        "endpoint": "https://fcm.googleapis.com/fcm/send/...",
        "keys": {
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_...",
            "auth": "tBHItJI5svbpez7KI4CCXg=="
        },
        "user_agent": "Mozilla/5.0 (iPhone; ...)"
    }
    ```

    **Response:**
    ```json
    {
        "id": "uuid",
        "endpoint": "https://fcm.googleapis.com/...xyz",
        "created_at": "2025-12-10T10:30:00Z"
    }
    ```

    **Status Codes:**
    - 201: Subscription created
    - 200: Existing subscription updated
    - 400: Invalid subscription data
    - 500: Internal server error
    """
    try:
        # Validate endpoint format
        if not request.endpoint.startswith(('https://', 'http://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid endpoint URL format"
            )

        # Check for existing subscription (upsert)
        existing = db.query(PushSubscription).filter(
            PushSubscription.endpoint == request.endpoint
        ).first()

        if existing:
            # Update existing subscription
            existing.p256dh_key = request.keys.p256dh
            existing.auth_key = request.keys.auth
            existing.user_agent = request.user_agent
            db.commit()

            logger.info(
                f"Updated push subscription",
                extra={
                    "subscription_id": existing.id,
                    "endpoint_preview": request.endpoint[:50] + "..."
                }
            )

            # Truncate endpoint for response
            endpoint_truncated = _truncate_endpoint(existing.endpoint)

            return SubscriptionResponse(
                id=existing.id,
                endpoint=endpoint_truncated,
                created_at=existing.created_at.isoformat()
            )

        # Create new subscription
        subscription = PushSubscription(
            endpoint=request.endpoint,
            p256dh_key=request.keys.p256dh,
            auth_key=request.keys.auth,
            user_agent=request.user_agent,
            # user_id is nullable - can be associated with user later
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        logger.info(
            f"Created new push subscription",
            extra={
                "subscription_id": subscription.id,
                "endpoint_preview": request.endpoint[:50] + "..."
            }
        )

        # Truncate endpoint for response
        endpoint_truncated = _truncate_endpoint(subscription.endpoint)

        return SubscriptionResponse(
            id=subscription.id,
            endpoint=endpoint_truncated,
            created_at=subscription.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating push subscription: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create push subscription"
        )


@router.delete("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    request: UnsubscribeRequest,
    db: Session = Depends(get_db)
):
    """
    Unsubscribe from push notifications.

    Removes the push subscription from the database.

    **Request Body:**
    ```json
    {
        "endpoint": "https://fcm.googleapis.com/fcm/send/..."
    }
    ```

    **Status Codes:**
    - 204: Successfully unsubscribed
    - 404: Subscription not found
    - 500: Internal server error
    """
    try:
        subscription = db.query(PushSubscription).filter(
            PushSubscription.endpoint == request.endpoint
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        subscription_id = subscription.id
        db.delete(subscription)
        db.commit()

        logger.info(
            f"Deleted push subscription",
            extra={
                "subscription_id": subscription_id,
                "endpoint_preview": request.endpoint[:50] + "..."
            }
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting push subscription: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete push subscription"
        )


@router.get("/subscriptions", response_model=SubscriptionsListResponse)
async def list_subscriptions(
    db: Session = Depends(get_db)
):
    """
    List all push subscriptions (admin endpoint).

    Returns all registered push subscriptions for debugging and administration.
    Endpoints are truncated for security.

    **Response:**
    ```json
    {
        "subscriptions": [
            {
                "id": "uuid",
                "user_id": "uuid-or-null",
                "endpoint": "...truncated...",
                "user_agent": "Mozilla/5.0...",
                "created_at": "2025-12-10T10:30:00Z",
                "last_used_at": "2025-12-10T14:22:00Z"
            }
        ],
        "total": 42
    }
    ```

    **Status Codes:**
    - 200: Success
    - 500: Internal server error
    """
    try:
        subscriptions = db.query(PushSubscription).order_by(
            PushSubscription.created_at.desc()
        ).all()

        items = []
        for sub in subscriptions:
            items.append(SubscriptionListItem(
                id=sub.id,
                user_id=sub.user_id,
                endpoint=_truncate_endpoint(sub.endpoint),
                user_agent=sub.user_agent,
                created_at=sub.created_at.isoformat() if sub.created_at else None,
                last_used_at=sub.last_used_at.isoformat() if sub.last_used_at else None,
            ))

        return SubscriptionsListResponse(
            subscriptions=items,
            total=len(items)
        )

    except Exception as e:
        logger.error(f"Error listing push subscriptions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list push subscriptions"
        )


# ============================================================================
# Helper Functions
# ============================================================================


def _truncate_endpoint(endpoint: str) -> str:
    """
    Truncate endpoint URL for display/logging security.

    Push endpoints contain sensitive tokens that should not be fully exposed.
    """
    if not endpoint:
        return ""

    if len(endpoint) > 60:
        return endpoint[:30] + "..." + endpoint[-20:]
    return endpoint


# ============================================================================
# Test Notification Endpoint (Story P4-1.2)
# ============================================================================


class TestNotificationResult(BaseModel):
    """Result for a single subscription in test."""
    subscription_id: str
    success: bool
    error: Optional[str] = None


class TestNotificationResponse(BaseModel):
    """Response from test notification endpoint."""
    success: bool
    message: str
    results: Optional[List[TestNotificationResult]] = None


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    db: Session = Depends(get_db)
):
    """
    Send a test push notification to all subscribed devices.

    Used to verify push notification setup is working correctly.
    Sends a sample notification to all registered subscriptions.

    **Response:**
    ```json
    {
        "success": true,
        "message": "Test notification sent to 2 subscriptions",
        "results": [
            {"subscription_id": "uuid", "success": true},
            {"subscription_id": "uuid", "success": false, "error": "expired"}
        ]
    }
    ```

    **Status Codes:**
    - 200: Test completed (check individual results for delivery status)
    - 500: Internal server error
    """
    try:
        service = PushNotificationService(db)

        # Send test notification to all subscriptions
        notification_results = await service.broadcast_notification(
            title="Test Notification",
            body="If you see this, push notifications are working correctly!",
            data={
                "type": "test",
                "url": "/settings"
            },
            tag="test-notification"
        )

        if not notification_results:
            return TestNotificationResponse(
                success=True,
                message="No push subscriptions found. Enable notifications first.",
                results=[]
            )

        # Convert results to response format
        results = [
            TestNotificationResult(
                subscription_id=r.subscription_id,
                success=r.success,
                error=r.error if not r.success else None
            )
            for r in notification_results
        ]

        success_count = sum(1 for r in results if r.success)
        total_count = len(results)

        return TestNotificationResponse(
            success=success_count > 0,
            message=f"Test notification sent to {success_count}/{total_count} subscriptions",
            results=results
        )

    except Exception as e:
        logger.error(f"Error sending test notification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )

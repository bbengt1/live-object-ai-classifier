"""
Push Notification Service for Web Push notifications (Story P4-1.1, P4-1.3)

Handles sending push notifications to subscribed browsers with:
- VAPID authentication
- Retry logic with exponential backoff
- Automatic cleanup of invalid subscriptions
- Delivery tracking and metrics
- Rich notifications with thumbnails, actions, and deep links (P4-1.3)
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from pywebpush import webpush, WebPushException
from py_vapid import Vapid
from sqlalchemy.orm import Session

from app.models.push_subscription import PushSubscription
from app.utils.vapid import ensure_vapid_keys
from app.core.database import SessionLocal
from app.core.metrics import record_push_notification_sent, update_push_subscription_count

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2  # Exponential backoff: 2s, 4s, 8s
VAPID_CLAIMS_EMAIL = "mailto:admin@liveobject.local"


@dataclass
class NotificationResult:
    """Result of a notification delivery attempt."""
    subscription_id: str
    success: bool
    error: Optional[str] = None
    status_code: Optional[int] = None
    retries: int = 0


class PushNotificationService:
    """
    Service for sending Web Push notifications.

    Features:
    - VAPID authentication with automatic key management
    - Exponential backoff retry for transient failures
    - Automatic removal of invalid/expired subscriptions
    - Async notification sending (non-blocking)
    - Delivery success/failure tracking

    Usage:
        service = PushNotificationService(db_session)
        result = await service.send_notification(
            subscription_id="...",
            title="Motion Detected",
            body="Person at front door",
            data={"event_id": "..."}
        )
    """

    def __init__(self, db: Session):
        """
        Initialize PushNotificationService.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._vapid_private_key: Optional[str] = None
        self._vapid_public_key: Optional[str] = None

    def _ensure_vapid_keys(self) -> tuple[str, str]:
        """
        Ensure VAPID keys are loaded (lazy loading).

        Returns:
            Tuple of (private_key, public_key)
        """
        if not self._vapid_private_key or not self._vapid_public_key:
            self._vapid_private_key, self._vapid_public_key = ensure_vapid_keys(self.db)
        return self._vapid_private_key, self._vapid_public_key

    async def send_notification(
        self,
        subscription_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        icon: str = "/icons/notification-192.svg",
        badge: str = "/icons/badge-72.svg",
        tag: Optional[str] = None,
        image: Optional[str] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        renotify: bool = True,
    ) -> NotificationResult:
        """
        Send a push notification to a specific subscription.

        Args:
            subscription_id: UUID of the push subscription
            title: Notification title
            body: Notification body text
            data: Additional data payload (event_id, url, etc.)
            icon: Icon URL for notification
            badge: Badge icon URL
            tag: Tag for notification grouping/collapse
            image: Large image URL for rich notification (P4-1.3)
            actions: List of action buttons [{action, title, icon}] (P4-1.3)
            renotify: Alert again even if same tag (P4-1.3)

        Returns:
            NotificationResult with success status and details
        """
        # Get subscription
        subscription = self.db.query(PushSubscription).filter(
            PushSubscription.id == subscription_id
        ).first()

        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return NotificationResult(
                subscription_id=subscription_id,
                success=False,
                error="Subscription not found"
            )

        return await self._send_to_subscription(
            subscription=subscription,
            title=title,
            body=body,
            data=data,
            icon=icon,
            badge=badge,
            tag=tag,
            image=image,
            actions=actions,
            renotify=renotify
        )

    async def broadcast_notification(
        self,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        icon: str = "/icons/notification-192.svg",
        badge: str = "/icons/badge-72.svg",
        tag: Optional[str] = None,
        image: Optional[str] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        renotify: bool = True,
    ) -> List[NotificationResult]:
        """
        Send a push notification to all subscriptions.

        Args:
            title: Notification title
            body: Notification body text
            data: Additional data payload
            icon: Icon URL for notification
            badge: Badge icon URL
            tag: Tag for notification grouping/collapse
            image: Large image URL for rich notification (P4-1.3)
            actions: List of action buttons [{action, title, icon}] (P4-1.3)
            renotify: Alert again even if same tag (P4-1.3)

        Returns:
            List of NotificationResult for each subscription
        """
        subscriptions = self.db.query(PushSubscription).all()

        if not subscriptions:
            logger.info("No push subscriptions to broadcast to")
            return []

        logger.info(f"Broadcasting notification to {len(subscriptions)} subscriptions")

        # Send notifications concurrently
        tasks = [
            self._send_to_subscription(
                subscription=sub,
                title=title,
                body=body,
                data=data,
                icon=icon,
                badge=badge,
                tag=tag,
                image=image,
                actions=actions,
                renotify=renotify
            )
            for sub in subscriptions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        notification_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Broadcast exception for subscription: {result}")
                notification_results.append(NotificationResult(
                    subscription_id=subscriptions[i].id,
                    success=False,
                    error=str(result)
                ))
            else:
                notification_results.append(result)

        # Log summary
        success_count = sum(1 for r in notification_results if r.success)
        logger.info(
            f"Broadcast complete: {success_count}/{len(subscriptions)} successful",
            extra={
                "total_subscriptions": len(subscriptions),
                "successful_deliveries": success_count,
                "failed_deliveries": len(subscriptions) - success_count
            }
        )

        return notification_results

    async def _send_to_subscription(
        self,
        subscription: PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]],
        icon: str,
        badge: str,
        tag: Optional[str],
        image: Optional[str] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        renotify: bool = True,
    ) -> NotificationResult:
        """
        Send notification to a single subscription with retry logic.

        Implements exponential backoff for transient failures.
        Automatically removes invalid/expired subscriptions.
        Supports rich notifications with images, actions, and collapse (P4-1.3).
        """
        private_key, _ = self._ensure_vapid_keys()

        # Build notification payload (P4-1.3: add rich notification fields)
        payload = {
            "title": title,
            "body": body,
            "icon": icon,
            "badge": badge,
            "renotify": renotify,
        }
        if tag:
            payload["tag"] = tag
        if data:
            payload["data"] = data
        if image:
            payload["image"] = image
        if actions:
            payload["actions"] = actions

        payload_json = json.dumps(payload)

        # Get subscription info in pywebpush format
        subscription_info = subscription.get_subscription_info()

        retries = 0
        last_error = None
        last_status_code = None
        start_time = time.time()

        # Create Vapid instance from PEM key once (outside retry loop)
        # Using Vapid.from_pem() is more reliable than passing raw key string
        vapid_instance = Vapid.from_pem(private_key.encode('utf-8'))

        while retries <= MAX_RETRIES:
            try:
                # Send notification using pywebpush
                # Run in executor since webpush is synchronous
                loop = asyncio.get_event_loop()

                # Define sync function to call webpush (avoids lambda capture issues)
                def send_push():
                    return webpush(
                        subscription_info=subscription_info,
                        data=payload_json,
                        vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
                        vapid_private_key=vapid_instance,  # Pass the Vapid instance
                    )

                await loop.run_in_executor(None, send_push)

                # Success - update last_used_at
                subscription.last_used_at = datetime.now(timezone.utc)
                self.db.commit()

                # Record metrics
                duration = time.time() - start_time
                record_push_notification_sent("success", duration)

                logger.info(
                    f"Push notification sent successfully",
                    extra={
                        "subscription_id": subscription.id,
                        "title": title,
                        "retries": retries,
                        "duration_seconds": duration
                    }
                )

                return NotificationResult(
                    subscription_id=subscription.id,
                    success=True,
                    retries=retries
                )

            except WebPushException as e:
                last_error = str(e)
                last_status_code = e.response.status_code if e.response else None

                # Check if subscription is invalid/expired (should not retry)
                if last_status_code in (404, 410):
                    # 404: Not Found, 410: Gone - subscription is invalid
                    duration = time.time() - start_time
                    record_push_notification_sent("failure", duration)

                    logger.warning(
                        f"Removing invalid subscription (HTTP {last_status_code})",
                        extra={
                            "subscription_id": subscription.id,
                            "status_code": last_status_code
                        }
                    )
                    self.db.delete(subscription)
                    self.db.commit()

                    return NotificationResult(
                        subscription_id=subscription.id,
                        success=False,
                        error=f"Subscription expired/invalid (HTTP {last_status_code})",
                        status_code=last_status_code,
                        retries=retries
                    )

                # Retry for transient errors (5xx, network issues)
                if retries < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY_SECONDS * (2 ** retries)
                    logger.warning(
                        f"Push notification failed, retrying in {delay}s",
                        extra={
                            "subscription_id": subscription.id,
                            "attempt": retries + 1,
                            "max_retries": MAX_RETRIES,
                            "error": last_error,
                            "status_code": last_status_code
                        }
                    )
                    await asyncio.sleep(delay)
                    retries += 1
                else:
                    break

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Unexpected error sending push notification: {e}",
                    exc_info=True,
                    extra={"subscription_id": subscription.id}
                )

                if retries < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY_SECONDS * (2 ** retries)
                    await asyncio.sleep(delay)
                    retries += 1
                else:
                    break

        # All retries exhausted - record failure metric
        duration = time.time() - start_time
        record_push_notification_sent("failure", duration)

        logger.error(
            f"Push notification failed after {MAX_RETRIES} retries",
            extra={
                "subscription_id": subscription.id,
                "error": last_error,
                "status_code": last_status_code,
                "duration_seconds": duration
            }
        )

        return NotificationResult(
            subscription_id=subscription.id,
            success=False,
            error=last_error,
            status_code=last_status_code,
            retries=retries
        )


# ============================================================================
# Global service accessor
# ============================================================================

_push_service: Optional[PushNotificationService] = None


def get_push_notification_service(db: Optional[Session] = None) -> PushNotificationService:
    """
    Get the PushNotificationService instance.

    Args:
        db: Optional database session. If not provided, creates new session.

    Returns:
        PushNotificationService instance
    """
    if db is None:
        db = SessionLocal()

    return PushNotificationService(db)


# ============================================================================
# Rich Notification Helpers (Story P4-1.3)
# ============================================================================

# Default action buttons for event notifications
DEFAULT_NOTIFICATION_ACTIONS = [
    {"action": "view", "title": "View", "icon": "/icons/view-24.svg"},
    {"action": "dismiss", "title": "Dismiss", "icon": "/icons/dismiss-24.svg"},
]


def format_rich_notification(
    event_id: str,
    camera_id: str,
    camera_name: str,
    description: str,
    thumbnail_url: Optional[str] = None,
    smart_detection_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format a rich notification payload for an event (Story P4-1.3).

    Creates a notification with:
    - Descriptive title based on smart detection type
    - Truncated body text
    - Thumbnail image URL
    - Action buttons (View, Dismiss)
    - Deep link URL
    - Tag for notification collapse per camera

    Args:
        event_id: UUID of the event
        camera_id: UUID of the camera (used for collapse tag)
        camera_name: Display name of the camera
        description: AI-generated event description
        thumbnail_url: Optional URL to event thumbnail image
        smart_detection_type: Optional smart detection type (person, vehicle, etc.)

    Returns:
        Dict with notification payload fields
    """
    # Build title based on detection type
    if smart_detection_type:
        detection_labels = {
            "person": "Person Detected",
            "vehicle": "Vehicle Detected",
            "package": "Package Detected",
            "animal": "Animal Detected",
            "ring": "Doorbell Ring",
            "motion": "Motion Detected",
        }
        detection_label = detection_labels.get(smart_detection_type, "Motion Detected")
        title = f"{camera_name}: {detection_label}"
    else:
        title = f"{camera_name}: Motion Detected"

    # Truncate description if too long
    body = description
    if len(body) > 100:
        body = body[:97] + "..."

    # Build deep link URL
    url = f"/events?highlight={event_id}"

    # Build data payload
    data = {
        "event_id": event_id,
        "camera_id": camera_id,
        "camera_name": camera_name,
        "url": url,
    }
    if smart_detection_type:
        data["smart_detection_type"] = smart_detection_type

    # Build full notification payload
    notification = {
        "title": title,
        "body": body,
        "data": data,
        "tag": camera_id,  # Use camera_id for collapse (AC4)
        "actions": DEFAULT_NOTIFICATION_ACTIONS,
        "renotify": True,  # Alert on updates even with same tag
    }

    # Add thumbnail image if available (AC1, AC8)
    if thumbnail_url:
        notification["image"] = thumbnail_url

    return notification


async def send_event_notification(
    event_id: str,
    camera_name: str,
    description: str,
    thumbnail_url: Optional[str] = None,
    camera_id: Optional[str] = None,
    smart_detection_type: Optional[str] = None,
    db: Optional[Session] = None
) -> List[NotificationResult]:
    """
    Convenience function to send rich notification for a new event (P4-1.3).

    This is the main entry point for event pipeline integration.
    Sends to all subscriptions with event context, thumbnail, and action buttons.

    Args:
        event_id: UUID of the event
        camera_name: Name of the camera that detected the event
        description: AI-generated event description
        thumbnail_url: Optional URL to event thumbnail
        camera_id: Optional camera UUID (for notification collapse)
        smart_detection_type: Optional smart detection type (person, vehicle, etc.)
        db: Optional database session

    Returns:
        List of NotificationResult for each subscription
    """
    if db is None:
        db = SessionLocal()

    try:
        service = PushNotificationService(db)

        # Use camera_id for collapse tag, fallback to event_id
        collapse_tag = camera_id or event_id

        # Format rich notification (P4-1.3)
        notification = format_rich_notification(
            event_id=event_id,
            camera_id=collapse_tag,
            camera_name=camera_name,
            description=description,
            thumbnail_url=thumbnail_url,
            smart_detection_type=smart_detection_type,
        )

        return await service.broadcast_notification(
            title=notification["title"],
            body=notification["body"],
            data=notification["data"],
            tag=notification["tag"],
            image=notification.get("image"),
            actions=notification["actions"],
            renotify=notification["renotify"],
        )

    except Exception as e:
        logger.error(f"Error sending event notification: {e}", exc_info=True)
        return []
    finally:
        if db:
            db.close()

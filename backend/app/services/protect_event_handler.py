"""
UniFi Protect Event Handler Service (Story P2-3.1)

Handles real-time motion/smart detection events from Protect WebSocket.
Implements event filtering based on per-camera configuration and
deduplication with cooldown logic.

Event Flow:
    uiprotect WebSocket Event
            ↓
    ProtectEventHandler.handle_event()
            ↓
    1. Parse event type (motion, smart_detect_*, ring)
            ↓
    2. Look up camera by protect_camera_id
            ↓
    3. Check camera.is_enabled
            ↓ (if not enabled → discard)
    4. Load smart_detection_types filter
            ↓
    5. Check event type matches filter
            ↓ (if not matching → discard)
    6. Check deduplication cooldown
            ↓ (if duplicate → discard)
    7. Pass to next stage (snapshot retrieval - Story P2-3.2)
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.camera import Camera
from app.services.snapshot_service import get_snapshot_service, SnapshotResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Event deduplication cooldown in seconds (Story P2-3.1 AC10)
# Default 60 seconds, matches motion_cooldown from Camera model
EVENT_COOLDOWN_SECONDS = 60

# WebSocket message type for motion events (for future broadcast to frontend)
PROTECT_MOTION_EVENT = "PROTECT_MOTION_EVENT"

# Event type mapping from Protect to filter types (Story P2-3.1 AC2)
# Protect sends: motion, smart_detect_person, smart_detect_vehicle, etc.
# Filters use: motion, person, vehicle, package, animal, ring
EVENT_TYPE_MAPPING = {
    "motion": "motion",
    "smart_detect_person": "person",
    "smart_detect_vehicle": "vehicle",
    "smart_detect_package": "package",
    "smart_detect_animal": "animal",
    "ring": "ring",
}

# Valid event types we process
VALID_EVENT_TYPES = set(EVENT_TYPE_MAPPING.keys())


class ProtectEventHandler:
    """
    Handles real-time events from UniFi Protect WebSocket (Story P2-3.1).

    Responsibilities:
    - Parse event types from uiprotect WSMessage
    - Look up camera by protect_camera_id and check if enabled
    - Filter events based on camera's smart_detection_types configuration
    - Deduplicate events using per-camera cooldown
    - Pass qualifying events to snapshot retrieval (Story P2-3.2)

    Attributes:
        _last_event_times: Dict tracking last event timestamp per camera
    """

    def __init__(self):
        """Initialize event handler with empty event tracking."""
        # Track last event time per camera for deduplication (AC9)
        self._last_event_times: Dict[str, datetime] = {}

    async def handle_event(
        self,
        controller_id: str,
        msg: Any
    ) -> bool:
        """
        Handle a WebSocket event from uiprotect (Story P2-3.1 AC1).

        Processes motion/smart detection events through filtering and
        deduplication before passing to next stage.

        Args:
            controller_id: Controller UUID
            msg: WebSocket message from uiprotect (WSSubscriptionMessage)

        Returns:
            True if event was processed, False if filtered/skipped
        """
        try:
            # Extract new_obj from message
            new_obj = getattr(msg, 'new_obj', None)
            if not new_obj:
                return False

            # Only process Camera or Doorbell events
            model_type = type(new_obj).__name__
            if model_type not in ('Camera', 'Doorbell'):
                return False

            # Extract protect_camera_id
            protect_camera_id = str(getattr(new_obj, 'id', ''))
            if not protect_camera_id:
                return False

            # Parse event types from the message (AC2)
            event_types = self._parse_event_types(new_obj, model_type)
            if not event_types:
                return False

            # Look up camera in database (AC3)
            db = SessionLocal()
            try:
                camera = self._get_camera_by_protect_id(db, protect_camera_id)

                # Check if camera is enabled for AI analysis (AC3, AC4)
                if not camera:
                    logger.debug(
                        "Event from unregistered camera - discarding",
                        extra={
                            "event_type": "protect_event_unknown_camera",
                            "controller_id": controller_id,
                            "protect_camera_id": protect_camera_id
                        }
                    )
                    return False

                if not camera.is_enabled or camera.source_type != 'protect':
                    logger.debug(
                        f"Event from disabled camera '{camera.name}' - discarding",
                        extra={
                            "event_type": "protect_event_disabled_camera",
                            "controller_id": controller_id,
                            "camera_id": camera.id,
                            "camera_name": camera.name,
                            "is_enabled": camera.is_enabled,
                            "source_type": camera.source_type
                        }
                    )
                    return False

                # Log event received (AC11)
                logger.info(
                    f"Event received from camera '{camera.name}': {', '.join(event_types)}",
                    extra={
                        "event_type": "protect_event_received",
                        "controller_id": controller_id,
                        "camera_id": camera.id,
                        "camera_name": camera.name,
                        "detected_types": event_types,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )

                # Load and check smart_detection_types filter (AC5, AC6, AC7, AC8)
                smart_detection_types = self._load_smart_detection_types(camera)

                for event_type in event_types:
                    # Map event type to filter type
                    filter_type = EVENT_TYPE_MAPPING.get(event_type)
                    if not filter_type:
                        continue

                    # Check if event should be processed
                    if not self._should_process_event(filter_type, smart_detection_types, camera.name):
                        continue

                    # Check deduplication cooldown (AC9, AC10)
                    if self._is_duplicate_event(camera.id, camera.name):
                        continue

                    # Event passed all filters - update tracking and proceed
                    self._last_event_times[camera.id] = datetime.now(timezone.utc)

                    logger.info(
                        f"Event passed filters for camera '{camera.name}': {event_type}",
                        extra={
                            "event_type": "protect_event_passed",
                            "controller_id": controller_id,
                            "camera_id": camera.id,
                            "camera_name": camera.name,
                            "detected_type": event_type,
                            "filter_type": filter_type
                        }
                    )

                    # Story P2-3.2: Retrieve snapshot for AI processing
                    snapshot_result = await self._retrieve_snapshot(
                        controller_id,
                        camera.protect_camera_id,
                        camera.id,
                        camera.name,
                        event_type
                    )

                    # TODO: Story P2-3.3 - Pass snapshot to AI pipeline
                    # if snapshot_result:
                    #     await self._submit_to_ai_pipeline(snapshot_result, camera, event_type)

                    return snapshot_result is not None

                return False

            finally:
                db.close()

        except Exception as e:
            logger.warning(
                f"Error handling Protect event: {e}",
                extra={
                    "event_type": "protect_event_handler_error",
                    "controller_id": controller_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return False

    def _parse_event_types(self, obj: Any, model_type: str) -> List[str]:
        """
        Parse event types from uiprotect object (Story P2-3.1 AC2).

        Extracts motion and smart detection types from the camera object.

        Args:
            obj: Camera or Doorbell object from uiprotect
            model_type: "Camera" or "Doorbell"

        Returns:
            List of event type strings (e.g., ["motion", "smart_detect_person"])
        """
        event_types = []

        # Check for motion detection
        is_motion_detected = getattr(obj, 'is_motion_detected', False)
        if is_motion_detected:
            event_types.append("motion")

        # Check for smart detection types
        # uiprotect provides smart_detect_types as a list of detected types
        smart_detect_types = getattr(obj, 'smart_detect_types', None)
        if smart_detect_types:
            for detect_type in smart_detect_types:
                # Convert to our event type format
                event_key = f"smart_detect_{detect_type.lower()}"
                if event_key in VALID_EVENT_TYPES:
                    event_types.append(event_key)

        # Check for doorbell ring (specific to doorbells)
        if model_type == 'Doorbell':
            is_ringing = getattr(obj, 'is_ringing', False)
            if is_ringing:
                event_types.append("ring")

        return event_types

    def _get_camera_by_protect_id(
        self,
        db: Session,
        protect_camera_id: str
    ) -> Optional[Camera]:
        """
        Look up camera by protect_camera_id (Story P2-3.1 AC3).

        Args:
            db: Database session
            protect_camera_id: Native Protect camera ID

        Returns:
            Camera model or None if not found
        """
        return db.query(Camera).filter(
            Camera.protect_camera_id == protect_camera_id
        ).first()

    def _load_smart_detection_types(self, camera: Camera) -> List[str]:
        """
        Load smart_detection_types from camera record (Story P2-3.1 AC5).

        Parses JSON array from camera.smart_detection_types field.

        Args:
            camera: Camera model instance

        Returns:
            List of filter types (e.g., ["person", "vehicle"])
            Empty list if not configured (enables "all motion" mode)
        """
        if not camera.smart_detection_types:
            return []

        try:
            types = json.loads(camera.smart_detection_types)
            if isinstance(types, list):
                return types
            return []
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                f"Invalid smart_detection_types JSON for camera '{camera.name}'",
                extra={
                    "event_type": "protect_invalid_filter_config",
                    "camera_id": camera.id,
                    "camera_name": camera.name
                }
            )
            return []

    def _should_process_event(
        self,
        filter_type: str,
        smart_detection_types: List[str],
        camera_name: str
    ) -> bool:
        """
        Check if event type should be processed based on filter config (Story P2-3.1 AC6, AC7, AC8).

        "All Motion" mode (AC8): Empty array or ["motion"] processes all event types.

        Args:
            filter_type: Mapped filter type (e.g., "person", "vehicle")
            smart_detection_types: Camera's configured filter types
            camera_name: Camera name for logging

        Returns:
            True if event should proceed, False if filtered out
        """
        # AC8: Empty array means "all motion" mode - process everything
        if not smart_detection_types:
            logger.debug(
                f"Event passed filter for camera '{camera_name}': all-motion mode (empty config)",
                extra={
                    "event_type": "protect_filter_passed",
                    "camera_name": camera_name,
                    "filter_type": filter_type,
                    "filter_reason": "all_motion_mode"
                }
            )
            return True

        # AC8: ["motion"] also means process all event types
        if smart_detection_types == ["motion"]:
            logger.debug(
                f"Event passed filter for camera '{camera_name}': all-motion mode ([\"motion\"])",
                extra={
                    "event_type": "protect_filter_passed",
                    "camera_name": camera_name,
                    "filter_type": filter_type,
                    "filter_reason": "all_motion_mode"
                }
            )
            return True

        # AC6: Check if event type is in configured filters
        if filter_type in smart_detection_types:
            logger.debug(
                f"Event passed filter for camera '{camera_name}': {filter_type} in filters",
                extra={
                    "event_type": "protect_filter_passed",
                    "camera_name": camera_name,
                    "filter_type": filter_type,
                    "configured_filters": smart_detection_types
                }
            )
            return True

        # AC7: Event type not in filters - discard silently
        logger.debug(
            f"Event filtered for camera '{camera_name}': {filter_type} not in {smart_detection_types}",
            extra={
                "event_type": "protect_filter_rejected",
                "camera_name": camera_name,
                "filter_type": filter_type,
                "configured_filters": smart_detection_types,
                "filter_reason": "type_not_configured"
            }
        )
        return False

    def _is_duplicate_event(self, camera_id: str, camera_name: str) -> bool:
        """
        Check if event is a duplicate based on cooldown (Story P2-3.1 AC9, AC10).

        Uses configurable cooldown period (default 60 seconds) to prevent
        duplicate event processing for the same camera.

        Args:
            camera_id: Camera UUID
            camera_name: Camera name for logging

        Returns:
            True if event should be skipped (duplicate), False if should proceed
        """
        last_event_time = self._last_event_times.get(camera_id)

        if last_event_time is None:
            # First event for this camera
            return False

        elapsed = (datetime.now(timezone.utc) - last_event_time).total_seconds()

        if elapsed < EVENT_COOLDOWN_SECONDS:
            logger.debug(
                f"Event deduplicated for camera '{camera_name}': {elapsed:.1f}s since last event (cooldown: {EVENT_COOLDOWN_SECONDS}s)",
                extra={
                    "event_type": "protect_event_deduplicated",
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "seconds_since_last": elapsed,
                    "cooldown_seconds": EVENT_COOLDOWN_SECONDS
                }
            )
            return True

        return False

    async def _retrieve_snapshot(
        self,
        controller_id: str,
        protect_camera_id: str,
        camera_id: str,
        camera_name: str,
        event_type: str
    ) -> Optional[SnapshotResult]:
        """
        Retrieve snapshot from Protect camera (Story P2-3.2).

        Args:
            controller_id: Controller UUID
            protect_camera_id: Native Protect camera ID
            camera_id: Internal camera UUID
            camera_name: Camera name for logging
            event_type: Type of event that triggered snapshot

        Returns:
            SnapshotResult if successful, None otherwise
        """
        try:
            snapshot_service = get_snapshot_service()
            result = await snapshot_service.get_snapshot(
                controller_id=controller_id,
                protect_camera_id=protect_camera_id,
                camera_id=camera_id,
                camera_name=camera_name,
                timestamp=datetime.now(timezone.utc)
            )

            if result:
                logger.info(
                    f"Snapshot retrieved for camera '{camera_name}' ({event_type})",
                    extra={
                        "event_type": "protect_snapshot_retrieved",
                        "controller_id": controller_id,
                        "camera_id": camera_id,
                        "camera_name": camera_name,
                        "detected_type": event_type,
                        "thumbnail_path": result.thumbnail_path,
                        "image_dimensions": f"{result.width}x{result.height}"
                    }
                )
            else:
                logger.warning(
                    f"Snapshot retrieval failed for camera '{camera_name}' ({event_type})",
                    extra={
                        "event_type": "protect_snapshot_failed",
                        "controller_id": controller_id,
                        "camera_id": camera_id,
                        "camera_name": camera_name,
                        "detected_type": event_type
                    }
                )

            return result

        except Exception as e:
            logger.error(
                f"Snapshot retrieval error for camera '{camera_name}': {e}",
                extra={
                    "event_type": "protect_snapshot_error",
                    "controller_id": controller_id,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return None

    def clear_event_tracking(self, camera_id: Optional[str] = None) -> None:
        """
        Clear event tracking data (useful for testing).

        Args:
            camera_id: Specific camera to clear, or None to clear all
        """
        if camera_id:
            self._last_event_times.pop(camera_id, None)
        else:
            self._last_event_times.clear()


# Global singleton instance
_protect_event_handler: Optional[ProtectEventHandler] = None


def get_protect_event_handler() -> ProtectEventHandler:
    """Get the global ProtectEventHandler singleton instance."""
    global _protect_event_handler
    if _protect_event_handler is None:
        _protect_event_handler = ProtectEventHandler()
    return _protect_event_handler

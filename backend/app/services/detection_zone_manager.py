"""
Detection Zone Manager - Singleton service for zone filtering logic

Features:
- Zone filtering for motion detection
- Bounding box intersection with polygon zones
- Thread-safe singleton pattern
- Performance optimized (<5ms overhead)
"""
import cv2
import numpy as np
import json
import threading
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class DetectionZoneManager:
    """
    Singleton service for detection zone filtering

    Thread Safety:
    - Thread-safe for concurrent access from multiple camera threads
    - No shared mutable state (stateless filtering)

    Performance:
    - Target: <5ms overhead per frame
    - Short-circuit optimization: return True on first zone match
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern: Only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize service (only runs once due to singleton pattern)"""
        if self._initialized:
            return

        self._initialized = True
        logger.info("DetectionZoneManager initialized (singleton)")

    def is_motion_in_zones(
        self,
        camera_id: str,
        bounding_box: Optional[Dict[str, int]],
        detection_zones: Optional[str]
    ) -> bool:
        """
        Check if motion bounding box intersects any enabled detection zone

        Args:
            camera_id: Camera UUID (for logging)
            bounding_box: Motion bounding box {"x": int, "y": int, "width": int, "height": int}
            detection_zones: JSON string from database (array of DetectionZone objects)

        Returns:
            True if motion is in any enabled zone OR no zones defined
            False if zones exist but motion is outside all enabled zones

        Performance: <5ms overhead (critical requirement)

        Edge Cases:
            - No zones defined (None or empty) → True (detect anywhere)
            - No bounding box (None) → True (allow event)
            - All zones disabled → True (detect anywhere)
            - Invalid JSON → True (fail open, log error)
        """
        # Edge case: No bounding box provided
        if bounding_box is None:
            logger.debug(f"Camera {camera_id}: No bounding box, allowing motion")
            return True

        # Edge case: No zones defined (detect motion anywhere)
        if not detection_zones:
            logger.debug(f"Camera {camera_id}: No zones defined, allowing motion")
            return True

        # Parse detection zones JSON
        try:
            zones = json.loads(detection_zones)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(
                f"Camera {camera_id}: Invalid detection_zones JSON: {e}. "
                f"Failing open (allowing motion)"
            )
            return True

        # Edge case: Empty zones array
        if not zones or len(zones) == 0:
            logger.debug(f"Camera {camera_id}: Empty zones array, allowing motion")
            return True

        # Filter for enabled zones only
        enabled_zones = [z for z in zones if z.get('enabled', True)]

        # Edge case: All zones disabled
        if not enabled_zones:
            logger.debug(f"Camera {camera_id}: All zones disabled, allowing motion")
            return True

        # Calculate bounding box center point
        center_x = bounding_box['x'] + (bounding_box['width'] // 2)
        center_y = bounding_box['y'] + (bounding_box['height'] // 2)
        center_point = (center_x, center_y)

        logger.debug(
            f"Camera {camera_id}: Checking motion at ({center_x}, {center_y}) "
            f"against {len(enabled_zones)} enabled zones"
        )

        # Check each enabled zone (short-circuit on first match)
        for zone in enabled_zones:
            zone_id = zone.get('id', 'unknown')
            zone_name = zone.get('name', 'Unnamed')
            vertices = zone.get('vertices', [])

            # Validate zone has vertices
            if not vertices or len(vertices) < 3:
                logger.warning(
                    f"Camera {camera_id}: Zone {zone_id} ({zone_name}) has "
                    f"invalid vertices, skipping"
                )
                continue

            # Convert vertices to numpy array for OpenCV
            # Format: [(x1, y1), (x2, y2), ...]
            try:
                poly_points = np.array(
                    [[v['x'], v['y']] for v in vertices],
                    dtype=np.int32
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(
                    f"Camera {camera_id}: Zone {zone_id} ({zone_name}) has "
                    f"malformed vertices: {e}, skipping"
                )
                continue

            # Use OpenCV pointPolygonTest to check if center is inside polygon
            # Returns: positive (inside), 0 (on edge), negative (outside)
            result = cv2.pointPolygonTest(poly_points, center_point, measureDist=False)

            if result >= 0:  # Inside or on edge
                logger.debug(
                    f"Camera {camera_id}: Motion inside zone {zone_id} ({zone_name})"
                )
                return True  # Short-circuit: motion detected in zone

        # No zones matched
        logger.debug(
            f"Camera {camera_id}: Motion outside all {len(enabled_zones)} enabled zones, "
            f"ignoring event"
        )
        return False


# Singleton instance for import
detection_zone_manager = DetectionZoneManager()

"""Unit tests for DetectionZoneManager service"""
import pytest
import json
import time
from app.services.detection_zone_manager import detection_zone_manager, DetectionZoneManager


class TestDetectionZoneManager:
    """Test suite for DetectionZoneManager zone filtering logic"""

    def test_singleton_pattern(self):
        """Test that DetectionZoneManager follows singleton pattern"""
        instance1 = DetectionZoneManager()
        instance2 = DetectionZoneManager()

        assert instance1 is instance2
        assert instance1 is detection_zone_manager

    def test_is_motion_in_zones_returns_true_when_no_zones_defined(self):
        """Test that motion is allowed when no zones are configured"""
        bounding_box = {"x": 100, "y": 100, "width": 50, "height": 50}

        # Test with None
        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones=None
        )
        assert result is True

        # Test with empty string
        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones=""
        )
        assert result is True

        # Test with empty JSON array
        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones="[]"
        )
        assert result is True

    def test_is_motion_in_zones_returns_true_when_bounding_box_center_in_enabled_zone(self):
        """Test that motion inside an enabled zone returns True"""
        # Zone covering 100,100 to 200,200
        zone = {
            "id": "zone-1",
            "name": "Test Zone",
            "vertices": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 100},
                {"x": 200, "y": 200},
                {"x": 100, "y": 200}
            ],
            "enabled": True
        }
        detection_zones = json.dumps([zone])

        # Bounding box with center at (125, 125) - inside zone
        bounding_box = {"x": 100, "y": 100, "width": 50, "height": 50}

        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones=detection_zones
        )
        assert result is True

    def test_is_motion_in_zones_returns_false_when_bounding_box_outside_all_zones(self):
        """Test that motion outside all zones returns False"""
        # Zone covering 100,100 to 200,200
        zone = {
            "id": "zone-1",
            "name": "Test Zone",
            "vertices": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 100},
                {"x": 200, "y": 200},
                {"x": 100, "y": 200}
            ],
            "enabled": True
        }
        detection_zones = json.dumps([zone])

        # Bounding box with center at (350, 350) - outside zone
        bounding_box = {"x": 300, "y": 300, "width": 100, "height": 100}

        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones=detection_zones
        )
        assert result is False

    def test_is_motion_in_zones_ignores_disabled_zones(self):
        """Test that disabled zones are not checked"""
        # Disabled zone covering 100,100 to 200,200
        zone = {
            "id": "zone-1",
            "name": "Disabled Zone",
            "vertices": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 100},
                {"x": 200, "y": 200},
                {"x": 100, "y": 200}
            ],
            "enabled": False
        }
        detection_zones = json.dumps([zone])

        # Bounding box with center at (125, 125) - would be inside if enabled
        bounding_box = {"x": 100, "y": 100, "width": 50, "height": 50}

        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones=detection_zones
        )
        # Should return True because all zones are disabled (detect anywhere)
        assert result is True

    def test_is_motion_in_zones_handles_multiple_zones_returns_true_on_first_match(self):
        """Test that multiple zones work correctly with short-circuit optimization"""
        zones = [
            {
                "id": "zone-1",
                "name": "Zone 1",
                "vertices": [
                    {"x": 0, "y": 0},
                    {"x": 100, "y": 0},
                    {"x": 100, "y": 100},
                    {"x": 0, "y": 100}
                ],
                "enabled": True
            },
            {
                "id": "zone-2",
                "name": "Zone 2",
                "vertices": [
                    {"x": 200, "y": 200},
                    {"x": 300, "y": 200},
                    {"x": 300, "y": 300},
                    {"x": 200, "y": 300}
                ],
                "enabled": True
            }
        ]
        detection_zones = json.dumps(zones)

        # Bounding box with center in zone 1
        bounding_box = {"x": 25, "y": 25, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

        # Bounding box with center in zone 2
        bounding_box = {"x": 225, "y": 225, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

        # Bounding box with center in neither zone
        bounding_box = {"x": 500, "y": 500, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is False

    def test_is_motion_in_zones_handles_rectangular_zone_as_polygon(self):
        """Test that rectangular zones (4 vertices) are handled correctly"""
        # Rectangle zone
        zone = {
            "id": "rect-zone",
            "name": "Rectangle",
            "vertices": [
                {"x": 50, "y": 50},
                {"x": 150, "y": 50},
                {"x": 150, "y": 150},
                {"x": 50, "y": 150}
            ],
            "enabled": True
        }
        detection_zones = json.dumps([zone])

        # Center inside rectangle
        bounding_box = {"x": 75, "y": 75, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

        # Center outside rectangle
        bounding_box = {"x": 0, "y": 0, "width": 40, "height": 40}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is False

    def test_is_motion_in_zones_handles_none_bounding_box(self):
        """Test that None bounding box returns True (fail open)"""
        zone = {
            "id": "zone-1",
            "name": "Test Zone",
            "vertices": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 100},
                {"x": 200, "y": 200},
                {"x": 100, "y": 200}
            ],
            "enabled": True
        }
        detection_zones = json.dumps([zone])

        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=None,
            detection_zones=detection_zones
        )
        assert result is True

    def test_is_motion_in_zones_parses_json_detection_zones_from_database(self):
        """Test that JSON string from database is correctly parsed"""
        zones = [
            {
                "id": "db-zone-1",
                "name": "Database Zone",
                "vertices": [
                    {"x": 10, "y": 10},
                    {"x": 50, "y": 10},
                    {"x": 50, "y": 50},
                    {"x": 10, "y": 50}
                ],
                "enabled": True
            }
        ]
        detection_zones = json.dumps(zones)

        # Motion inside zone
        bounding_box = {"x": 20, "y": 20, "width": 10, "height": 10}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

    def test_is_motion_in_zones_handles_invalid_json_gracefully(self):
        """Test that invalid JSON fails open (returns True)"""
        invalid_json = "{ this is not valid json }"

        bounding_box = {"x": 100, "y": 100, "width": 50, "height": 50}
        result = detection_zone_manager.is_motion_in_zones(
            camera_id="test-cam",
            bounding_box=bounding_box,
            detection_zones=invalid_json
        )
        # Should fail open (allow motion) on JSON parse error
        assert result is True

    def test_is_motion_in_zones_handles_malformed_vertices_gracefully(self):
        """Test that zones with malformed vertices are skipped"""
        zones = [
            {
                "id": "bad-zone",
                "name": "Bad Zone",
                "vertices": [
                    {"x": 100},  # Missing 'y'
                    {"y": 100},  # Missing 'x'
                    {"x": 100, "y": 100}
                ],
                "enabled": True
            },
            {
                "id": "good-zone",
                "name": "Good Zone",
                "vertices": [
                    {"x": 200, "y": 200},
                    {"x": 300, "y": 200},
                    {"x": 300, "y": 300},
                    {"x": 200, "y": 300}
                ],
                "enabled": True
            }
        ]
        detection_zones = json.dumps(zones)

        # Bounding box in good zone
        bounding_box = {"x": 225, "y": 225, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

    def test_is_motion_in_zones_performance_under_5ms(self):
        """Benchmark test: zone filtering should complete in <5ms"""
        # Create 5 enabled zones (realistic max use case)
        zones = []
        for i in range(5):
            zones.append({
                "id": f"zone-{i}",
                "name": f"Zone {i}",
                "vertices": [
                    {"x": i * 100, "y": i * 100},
                    {"x": i * 100 + 80, "y": i * 100},
                    {"x": i * 100 + 80, "y": i * 100 + 80},
                    {"x": i * 100, "y": i * 100 + 80}
                ],
                "enabled": True
            })
        detection_zones = json.dumps(zones)

        # Bounding box outside all zones (worst case: check all zones)
        bounding_box = {"x": 1000, "y": 1000, "width": 50, "height": 50}

        # Run 100 iterations and measure time
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            detection_zone_manager.is_motion_in_zones(
                "test-cam", bounding_box, detection_zones
            )

        elapsed_time = (time.time() - start_time) / iterations * 1000  # ms

        # Should average <5ms per call
        assert elapsed_time < 5.0, f"Zone filtering took {elapsed_time:.2f}ms (exceeds 5ms limit)"

    def test_is_motion_on_zone_edge(self):
        """Test that motion on zone edge is considered inside"""
        zone = {
            "id": "edge-zone",
            "name": "Edge Test",
            "vertices": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 100},
                {"x": 200, "y": 200},
                {"x": 100, "y": 200}
            ],
            "enabled": True
        }
        detection_zones = json.dumps([zone])

        # Bounding box with center exactly on left edge (x=100)
        bounding_box = {"x": 80, "y": 120, "width": 40, "height": 40}  # Center at (100, 140)
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

    def test_mixed_enabled_disabled_zones(self):
        """Test behavior with mix of enabled and disabled zones"""
        zones = [
            {
                "id": "disabled-zone",
                "name": "Disabled",
                "vertices": [
                    {"x": 0, "y": 0},
                    {"x": 100, "y": 0},
                    {"x": 100, "y": 100},
                    {"x": 0, "y": 100}
                ],
                "enabled": False
            },
            {
                "id": "enabled-zone",
                "name": "Enabled",
                "vertices": [
                    {"x": 200, "y": 200},
                    {"x": 300, "y": 200},
                    {"x": 300, "y": 300},
                    {"x": 200, "y": 300}
                ],
                "enabled": True
            }
        ]
        detection_zones = json.dumps(zones)

        # Motion in disabled zone - should return False
        bounding_box = {"x": 25, "y": 25, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is False

        # Motion in enabled zone - should return True
        bounding_box = {"x": 225, "y": 225, "width": 50, "height": 50}
        assert detection_zone_manager.is_motion_in_zones(
            "test-cam", bounding_box, detection_zones
        ) is True

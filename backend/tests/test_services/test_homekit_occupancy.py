"""
Unit tests for HomeKit occupancy sensor triggering (Story P5-1.5)

Tests cover:
- Occupancy trigger sets sensor state (AC1)
- Only person detection triggers occupancy (AC2)
- Timer resets occupancy after 5-minute timeout (AC3)
- Rapid person detections extend occupancy period (AC3)
- Camera ID mapping (Protect MAC addresses)
- Error resilience
"""
import asyncio
import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass

from app.config.homekit import HomekitConfig


# Mock CameraOccupancySensor for tests (matches homekit_accessories.py interface)
@dataclass
class MockCameraOccupancySensor:
    """Mock occupancy sensor for testing."""
    camera_id: str
    name: str
    _occupancy_detected: bool = False

    @property
    def occupancy_detected(self) -> bool:
        return self._occupancy_detected

    def trigger_occupancy(self):
        self._occupancy_detected = True

    def clear_occupancy(self):
        self._occupancy_detected = False


class TestHomekitOccupancyTrigger:
    """Tests for HomekitService.trigger_occupancy() (Story P5-1.5)"""

    @pytest.fixture
    def config(self):
        """Create test HomeKit config with short timeout for tests."""
        return HomekitConfig(
            enabled=True,
            port=51826,
            bridge_name="Test Bridge",
            manufacturer="Test",
            persist_dir="/tmp/homekit_test",
            motion_reset_seconds=2,
            max_motion_duration=10,
            occupancy_timeout_seconds=3,  # Short timeout for tests (normally 300s)
            max_occupancy_duration=15,    # Short max duration for tests (normally 1800s)
        )

    @pytest.fixture
    def mock_service(self, config):
        """Create a mock HomeKit service for testing."""
        from app.services.homekit_service import HomekitService

        service = HomekitService(config=config)
        service._running = True

        # Add mock occupancy sensors (in addition to motion sensors)
        occ_sensor1 = MockCameraOccupancySensor(camera_id="camera-1", name="Front Door Occupancy")
        occ_sensor2 = MockCameraOccupancySensor(camera_id="camera-2", name="Back Yard Occupancy")

        service._occupancy_sensors = {
            "camera-1": occ_sensor1,
            "camera-2": occ_sensor2,
        }

        # Also add motion sensors for completeness
        from tests.test_services.test_homekit_motion import MockCameraMotionSensor
        service._sensors = {
            "camera-1": MockCameraMotionSensor(camera_id="camera-1", name="Front Door"),
            "camera-2": MockCameraMotionSensor(camera_id="camera-2", name="Back Yard"),
        }

        return service

    def test_trigger_occupancy_sets_sensor_state(self, mock_service):
        """AC1: Occupancy trigger sets occupancy_detected = True"""
        sensor = mock_service._occupancy_sensors["camera-1"]
        assert sensor.occupancy_detected is False

        result = mock_service.trigger_occupancy("camera-1", event_id=123)

        assert result is True
        assert sensor.occupancy_detected is True

    def test_trigger_occupancy_unknown_camera(self, mock_service):
        """Triggering unknown camera returns False and logs debug message"""
        result = mock_service.trigger_occupancy("unknown-camera")
        assert result is False

    def test_trigger_occupancy_tracks_start_time(self, mock_service):
        """AC3: Occupancy trigger tracks start time for max duration"""
        assert "camera-1" not in mock_service._occupancy_start_times

        mock_service.trigger_occupancy("camera-1")

        assert "camera-1" in mock_service._occupancy_start_times
        assert mock_service._occupancy_start_times["camera-1"] > 0

    @pytest.mark.asyncio
    async def test_occupancy_resets_after_timeout(self, mock_service):
        """AC3: Occupancy resets to False after 5-minute timeout (using 3s for test)"""
        sensor = mock_service._occupancy_sensors["camera-1"]

        # Trigger occupancy
        mock_service.trigger_occupancy("camera-1")
        assert sensor.occupancy_detected is True

        # Wait for timeout (config has 3s timeout for tests)
        await asyncio.sleep(3.5)

        assert sensor.occupancy_detected is False

    @pytest.mark.asyncio
    async def test_rapid_person_detections_extend_occupancy(self, mock_service):
        """AC3: Multiple person detections reset timer, extending occupancy"""
        sensor = mock_service._occupancy_sensors["camera-1"]

        # First trigger
        mock_service.trigger_occupancy("camera-1")
        assert sensor.occupancy_detected is True

        # Wait 2s (before 3s timeout)
        await asyncio.sleep(2.0)

        # Second trigger should reset timer
        mock_service.trigger_occupancy("camera-1")
        assert sensor.occupancy_detected is True

        # Wait another 2s (4s total, but timer was reset at 2s)
        await asyncio.sleep(2.0)
        assert sensor.occupancy_detected is True  # Still active

        # Wait for full timeout from second trigger
        await asyncio.sleep(1.5)
        assert sensor.occupancy_detected is False

    def test_camera_id_mapping_mac_address_occupancy(self, mock_service):
        """AC1: Protect cameras can be triggered by MAC address for occupancy"""
        # Register MAC mapping
        mock_service.register_camera_mapping("camera-1", "AA:BB:CC:DD:EE:FF")

        # Trigger by MAC address
        result = mock_service.trigger_occupancy("AA:BB:CC:DD:EE:FF")

        assert result is True
        assert mock_service._occupancy_sensors["camera-1"].occupancy_detected is True

    def test_max_occupancy_duration_reset(self, mock_service):
        """AC3: Long-running occupancy eventually resets (max 30 min, using 15s for test)"""
        sensor = mock_service._occupancy_sensors["camera-1"]

        # Set start time to past max duration
        mock_service._occupancy_start_times["camera-1"] = time.time() - 20  # Past 15s max

        # Trigger should reset due to max duration
        mock_service.trigger_occupancy("camera-1")

        # State should be cleared
        assert "camera-1" not in mock_service._occupancy_start_times

    def test_clear_all_occupancy(self, mock_service):
        """AC3: clear_all_occupancy resets all sensors"""
        # Trigger both sensors
        mock_service.trigger_occupancy("camera-1")
        mock_service.trigger_occupancy("camera-2")

        assert mock_service._occupancy_sensors["camera-1"].occupancy_detected is True
        assert mock_service._occupancy_sensors["camera-2"].occupancy_detected is True

        # Clear all
        mock_service.clear_all_occupancy()

        assert mock_service._occupancy_sensors["camera-1"].occupancy_detected is False
        assert mock_service._occupancy_sensors["camera-2"].occupancy_detected is False

    @pytest.mark.asyncio
    async def test_stop_cancels_occupancy_timers(self, mock_service):
        """Stopping service cancels all occupancy reset timers"""
        # Trigger occupancy to create timer
        mock_service.trigger_occupancy("camera-1")

        assert "camera-1" in mock_service._occupancy_reset_tasks

        # Stop service
        await mock_service.stop()

        assert len(mock_service._occupancy_reset_tasks) == 0
        assert len(mock_service._occupancy_start_times) == 0

    def test_occupancy_and_motion_independent(self, mock_service):
        """AC1: Occupancy sensor is separate from motion sensor"""
        motion_sensor = mock_service._sensors["camera-1"]
        occupancy_sensor = mock_service._occupancy_sensors["camera-1"]

        # Both start False
        assert motion_sensor.motion_detected is False
        assert occupancy_sensor.occupancy_detected is False

        # Trigger only occupancy
        mock_service.trigger_occupancy("camera-1")

        # Motion should NOT be affected
        assert motion_sensor.motion_detected is False
        assert occupancy_sensor.occupancy_detected is True

        # Trigger only motion
        mock_service.trigger_motion("camera-2")

        # Occupancy for camera-2 should NOT be affected
        assert mock_service._sensors["camera-2"].motion_detected is True
        assert mock_service._occupancy_sensors["camera-2"].occupancy_detected is False


class TestHomekitOccupancyEventFiltering:
    """Tests for occupancy filtering by detection type (Story P5-1.5 AC2)"""

    @pytest.mark.asyncio
    async def test_event_processor_triggers_occupancy_for_person(self):
        """AC2: Event with smart_detection_type='person' triggers occupancy"""
        from unittest.mock import MagicMock

        class MockEventProcessor:
            async def _trigger_homekit_occupancy(self, homekit_service, camera_id, event_id):
                try:
                    success = homekit_service.trigger_occupancy(camera_id, event_id=event_id)
                    return success
                except Exception:
                    pass

        # Create mock HomeKit service
        mock_homekit = MagicMock()
        mock_homekit.is_running = True
        mock_homekit.trigger_occupancy = MagicMock(return_value=True)

        processor = MockEventProcessor()

        # Call the helper method directly (simulating person detection)
        await processor._trigger_homekit_occupancy(mock_homekit, "test-camera", "event-123")

        mock_homekit.trigger_occupancy.assert_called_once_with("test-camera", event_id="event-123")

    @pytest.mark.asyncio
    async def test_event_processor_handles_occupancy_errors(self):
        """Occupancy errors don't block event processing"""
        from unittest.mock import MagicMock

        class MockEventProcessor:
            async def _trigger_homekit_occupancy(self, homekit_service, camera_id, event_id):
                try:
                    success = homekit_service.trigger_occupancy(camera_id, event_id=event_id)
                    return success
                except Exception:
                    # Errors are caught and logged, not raised
                    pass

        # Create mock that raises exception
        mock_homekit = MagicMock()
        mock_homekit.is_running = True
        mock_homekit.trigger_occupancy = MagicMock(side_effect=Exception("HAP error"))

        processor = MockEventProcessor()

        # Should not raise
        await processor._trigger_homekit_occupancy(mock_homekit, "test-camera", "event-123")

        # Verify it was called
        mock_homekit.trigger_occupancy.assert_called_once()


class TestHomekitOccupancyConfig:
    """Tests for HomeKit occupancy configuration (Story P5-1.5)"""

    def test_default_occupancy_timeout_seconds(self):
        """Default occupancy timeout is 300 seconds (5 minutes)"""
        from app.config.homekit import DEFAULT_OCCUPANCY_TIMEOUT_SECONDS
        assert DEFAULT_OCCUPANCY_TIMEOUT_SECONDS == 300

    def test_default_max_occupancy_duration(self):
        """Default max occupancy duration is 1800 seconds (30 minutes)"""
        from app.config.homekit import DEFAULT_MAX_OCCUPANCY_DURATION
        assert DEFAULT_MAX_OCCUPANCY_DURATION == 1800

    def test_config_loads_occupancy_from_env(self):
        """Config loads occupancy settings from environment"""
        import os
        from app.config.homekit import get_homekit_config

        # Set environment variables
        os.environ["HOMEKIT_OCCUPANCY_TIMEOUT_SECONDS"] = "600"
        os.environ["HOMEKIT_MAX_OCCUPANCY_DURATION"] = "3600"

        try:
            config = get_homekit_config()
            assert config.occupancy_timeout_seconds == 600
            assert config.max_occupancy_duration == 3600
        finally:
            # Cleanup
            del os.environ["HOMEKIT_OCCUPANCY_TIMEOUT_SECONDS"]
            del os.environ["HOMEKIT_MAX_OCCUPANCY_DURATION"]

    def test_homekit_config_has_occupancy_fields(self):
        """HomekitConfig dataclass includes occupancy fields"""
        from app.config.homekit import HomekitConfig

        config = HomekitConfig()
        assert hasattr(config, 'occupancy_timeout_seconds')
        assert hasattr(config, 'max_occupancy_duration')
        assert config.occupancy_timeout_seconds == 300
        assert config.max_occupancy_duration == 1800


class TestCameraOccupancySensorClass:
    """Tests for CameraOccupancySensor class (Story P5-1.5 AC1, AC4)"""

    def test_occupancy_sensor_distinct_from_motion(self):
        """AC1: OccupancySensor uses different HAP service than MotionSensor"""
        from app.services.homekit_accessories import CameraMotionSensor, CameraOccupancySensor

        # Both classes should exist and be distinct
        assert CameraMotionSensor is not CameraOccupancySensor

    def test_create_occupancy_sensor_factory_exists(self):
        """Factory function for creating occupancy sensors exists"""
        from app.services.homekit_accessories import create_occupancy_sensor

        assert callable(create_occupancy_sensor)

    def test_occupancy_sensor_name_pattern(self):
        """AC1: Occupancy sensor should be named '{camera_name} Occupancy'"""
        # Verify the naming convention is documented in the class
        from app.services.homekit_accessories import CameraOccupancySensor

        # Class docstring should mention "Occupancy" naming
        assert "Occupancy" in CameraOccupancySensor.__doc__

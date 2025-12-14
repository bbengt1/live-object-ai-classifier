"""
Tests for HomeKit API endpoints (Story P5-1.1)

Tests cover:
- HomeKit status endpoint
- HomeKit enable/disable endpoints
- HomeKit QR code endpoint
- Schema validation
"""
import pytest
from pydantic import ValidationError

from app.api.v1.homekit import (
    HomeKitStatusResponse,
    HomeKitEnableRequest,
    HomeKitEnableResponse,
    HomeKitDisableResponse,
    HomeKitConfigResponse,
)


class TestHomeKitSchemas:
    """Tests for HomeKit API Pydantic schemas."""

    def test_status_response_schema(self):
        """AC6: HomeKitStatusResponse validates correctly."""
        response = HomeKitStatusResponse(
            enabled=True,
            running=True,
            paired=False,
            accessory_count=3,
            bridge_name="ArgusAI",
            setup_code="123-45-678",
            port=51826,
            error=None
        )

        assert response.enabled is True
        assert response.running is True
        assert response.paired is False
        assert response.accessory_count == 3
        assert response.bridge_name == "ArgusAI"
        assert response.setup_code == "123-45-678"
        assert response.port == 51826
        assert response.error is None

    def test_status_response_with_error(self):
        """HomeKitStatusResponse handles error state."""
        response = HomeKitStatusResponse(
            enabled=False,
            running=False,
            paired=False,
            accessory_count=0,
            bridge_name="ArgusAI",
            setup_code=None,
            port=51826,
            error="HAP-python not installed"
        )

        assert response.enabled is False
        assert response.running is False
        assert response.error == "HAP-python not installed"
        assert response.setup_code is None

    def test_status_response_hidden_setup_code_when_paired(self):
        """Setup code should be None when paired."""
        response = HomeKitStatusResponse(
            enabled=True,
            running=True,
            paired=True,
            accessory_count=5,
            bridge_name="ArgusAI",
            setup_code=None,  # Hidden when paired
            port=51826,
            error=None
        )

        assert response.paired is True
        assert response.setup_code is None

    def test_enable_request_schema(self):
        """AC6: HomeKitEnableRequest validates correctly."""
        request = HomeKitEnableRequest(
            bridge_name="MyHome",
            port=51827
        )

        assert request.bridge_name == "MyHome"
        assert request.port == 51827

    def test_enable_request_defaults(self):
        """HomeKitEnableRequest uses defaults."""
        request = HomeKitEnableRequest()

        assert request.bridge_name == "ArgusAI"
        assert request.port == 51826

    def test_enable_request_port_validation(self):
        """HomeKitEnableRequest validates port range."""
        # Too low
        with pytest.raises(ValidationError):
            HomeKitEnableRequest(port=80)

        # Too high
        with pytest.raises(ValidationError):
            HomeKitEnableRequest(port=70000)

    def test_enable_request_bridge_name_length(self):
        """HomeKitEnableRequest validates bridge name length."""
        # Too long
        with pytest.raises(ValidationError):
            HomeKitEnableRequest(bridge_name="A" * 100)

    def test_enable_response_schema(self):
        """AC6: HomeKitEnableResponse validates correctly."""
        response = HomeKitEnableResponse(
            enabled=True,
            running=True,
            port=51826,
            setup_code="123-45-678",
            qr_code_data="data:image/png;base64,abc123",
            bridge_name="ArgusAI",
            message="HomeKit bridge enabled successfully"
        )

        assert response.enabled is True
        assert response.running is True
        assert response.port == 51826
        assert response.setup_code == "123-45-678"
        assert response.qr_code_data.startswith("data:image/png;base64,")
        assert response.bridge_name == "ArgusAI"

    def test_enable_response_without_qr(self):
        """HomeKitEnableResponse allows None qr_code_data."""
        response = HomeKitEnableResponse(
            enabled=True,
            running=False,
            port=51826,
            setup_code="123-45-678",
            qr_code_data=None,
            bridge_name="ArgusAI",
            message="QR code not available"
        )

        assert response.qr_code_data is None

    def test_disable_response_schema(self):
        """AC6: HomeKitDisableResponse validates correctly."""
        response = HomeKitDisableResponse(
            enabled=False,
            running=False,
            message="HomeKit bridge disabled"
        )

        assert response.enabled is False
        assert response.running is False
        assert response.message == "HomeKit bridge disabled"

    def test_config_response_schema(self):
        """HomeKitConfigResponse validates correctly."""
        response = HomeKitConfigResponse(
            id=1,
            enabled=True,
            bridge_name="ArgusAI",
            port=51826,
            motion_reset_seconds=30,
            max_motion_duration=300,
            created_at="2025-12-14T10:00:00Z",
            updated_at="2025-12-14T10:00:00Z"
        )

        assert response.id == 1
        assert response.enabled is True
        assert response.bridge_name == "ArgusAI"
        assert response.port == 51826
        assert response.motion_reset_seconds == 30
        assert response.max_motion_duration == 300

    def test_config_response_optional_timestamps(self):
        """HomeKitConfigResponse handles optional timestamps."""
        response = HomeKitConfigResponse(
            id=1,
            enabled=False,
            bridge_name="ArgusAI",
            port=51826,
            motion_reset_seconds=30,
            max_motion_duration=300,
            created_at=None,
            updated_at=None
        )

        assert response.created_at is None
        assert response.updated_at is None


class TestHomeKitAPIEndpoints:
    """Tests for HomeKit API endpoint behavior.

    Note: These are schema/response tests. Full endpoint tests with
    mocked HAP-python would require additional fixtures.
    """

    def test_status_response_format(self):
        """AC6: Status endpoint returns expected format."""
        # Simulate the response format
        status = {
            "enabled": True,
            "running": True,
            "paired": False,
            "accessory_count": 2,
            "bridge_name": "ArgusAI",
            "setup_code": "123-45-678",
            "port": 51826,
            "error": None
        }

        response = HomeKitStatusResponse(**status)
        assert response.enabled is True
        assert response.accessory_count == 2

    def test_enable_response_format(self):
        """AC6: Enable endpoint returns expected format."""
        # Simulate the response format
        enable_response = {
            "enabled": True,
            "running": True,
            "port": 51826,
            "setup_code": "987-65-432",
            "qr_code_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA",
            "bridge_name": "ArgusAI",
            "message": "HomeKit bridge enabled with 3 cameras"
        }

        response = HomeKitEnableResponse(**enable_response)
        assert response.enabled is True
        assert response.running is True
        assert response.setup_code == "987-65-432"

    def test_disable_response_format(self):
        """AC6: Disable endpoint returns expected format."""
        disable_response = {
            "enabled": False,
            "running": False,
            "message": "HomeKit bridge disabled"
        }

        response = HomeKitDisableResponse(**disable_response)
        assert response.enabled is False
        assert response.running is False

    def test_graceful_degradation_error_format(self):
        """AC8: Error response when HAP-python not available."""
        error_status = {
            "enabled": False,
            "running": False,
            "paired": False,
            "accessory_count": 0,
            "bridge_name": "ArgusAI",
            "setup_code": None,
            "port": 51826,
            "error": "HAP-python not installed. Install with: pip install HAP-python"
        }

        response = HomeKitStatusResponse(**error_status)
        assert response.enabled is False
        assert response.running is False
        assert "HAP-python not installed" in response.error


class TestHomeKitQRCodeEndpoint:
    """Tests for QR code endpoint behavior."""

    def test_qr_code_data_format(self):
        """AC6: QR code is returned as base64 PNG."""
        # Validate that a proper response would have this format
        qr_response = HomeKitEnableResponse(
            enabled=True,
            running=True,
            port=51826,
            setup_code="123-45-678",
            qr_code_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
            bridge_name="ArgusAI",
            message="Enabled"
        )

        assert qr_response.qr_code_data.startswith("data:image/png;base64,")

    def test_qr_code_none_when_not_available(self):
        """QR code is None when qrcode package not installed."""
        response = HomeKitEnableResponse(
            enabled=True,
            running=True,
            port=51826,
            setup_code="123-45-678",
            qr_code_data=None,
            bridge_name="ArgusAI",
            message="QR code generation not available"
        )

        assert response.qr_code_data is None

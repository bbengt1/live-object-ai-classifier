"""
API Integration Tests for ONVIF Camera Discovery (Story P5-2.1)

Tests the discovery API endpoints:
- POST /api/v1/cameras/discover
- GET /api/v1/cameras/discover/status
- POST /api/v1/cameras/discover/clear-cache
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.schemas.discovery import DiscoveredDevice, DiscoveryResponse
from app.services.onvif_discovery_service import (
    ONVIFDiscoveryService,
    DiscoveryResult,
)


@pytest.fixture
def client():
    """Create test client with mocked discovery service."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_discovery_service():
    """Create mock discovery service."""
    mock_service = MagicMock(spec=ONVIFDiscoveryService)
    mock_service.is_available = True
    return mock_service


class TestDiscoverEndpoint:
    """Tests for POST /api/v1/cameras/discover."""

    def test_discover_returns_devices(self, client, mock_discovery_service):
        """AC5: Test discovery endpoint returns device list."""
        mock_device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=["onvif://www.onvif.org/type/NVT"],
            types=["tdn:NetworkVideoTransmitter"],
            metadata_version="1"
        )

        mock_result = DiscoveryResult(
            devices=[mock_device],
            duration_ms=5234,
            status="complete",
            error=None
        )

        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "complete"
        assert data["duration_ms"] == 5234
        assert data["device_count"] == 1
        assert len(data["devices"]) == 1
        assert data["devices"][0]["endpoint_url"] == "http://192.168.1.100:80/onvif/device_service"

    def test_discover_with_custom_timeout(self, client, mock_discovery_service):
        """AC5: Test custom timeout parameter."""
        mock_result = DiscoveryResult(
            devices=[],
            duration_ms=15000,
            status="complete"
        )

        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post(
                "/api/v1/cameras/discover",
                json={"timeout": 15}
            )

        assert response.status_code == 200
        mock_discovery_service.discover_cameras_with_result.assert_called_once_with(timeout=15)

    def test_discover_empty_results(self, client, mock_discovery_service):
        """AC5: Test empty discovery results."""
        mock_result = DiscoveryResult(
            devices=[],
            duration_ms=10000,
            status="complete"
        )

        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "complete"
        assert data["device_count"] == 0
        assert data["devices"] == []

    def test_discover_multiple_devices(self, client, mock_discovery_service):
        """AC5: Test discovery with multiple devices."""
        devices = [
            DiscoveredDevice(
                endpoint_url="http://192.168.1.100:80/onvif/device_service",
                scopes=[],
                types=["tdn:NetworkVideoTransmitter"]
            ),
            DiscoveredDevice(
                endpoint_url="http://192.168.1.101:80/onvif/device_service",
                scopes=[],
                types=["tdn:NetworkVideoTransmitter"]
            ),
            DiscoveredDevice(
                endpoint_url="http://192.168.1.102:80/onvif/device_service",
                scopes=[],
                types=["tdn:NetworkVideoTransmitter"]
            ),
        ]

        mock_result = DiscoveryResult(
            devices=devices,
            duration_ms=8500,
            status="complete"
        )

        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        assert response.status_code == 200
        data = response.json()

        assert data["device_count"] == 3
        assert len(data["devices"]) == 3

    def test_discover_service_unavailable(self, client, mock_discovery_service):
        """AC5: Test 503 when discovery service unavailable."""
        mock_discovery_service.is_available = False

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        assert response.status_code == 503
        data = response.json()
        assert "discovery_unavailable" in str(data["detail"])

    def test_discover_service_error(self, client, mock_discovery_service):
        """AC5: Test error handling for service exceptions."""
        mock_discovery_service.discover_cameras_with_result.side_effect = Exception(
            "Network error"
        )

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        assert response.status_code == 500
        data = response.json()
        assert "discovery_failed" in str(data["detail"])

    def test_discover_default_timeout(self, client, mock_discovery_service):
        """AC5: Test default timeout when not specified."""
        mock_result = DiscoveryResult(
            devices=[],
            duration_ms=10000,
            status="complete"
        )

        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        assert response.status_code == 200
        # Default timeout is 10 seconds
        mock_discovery_service.discover_cameras_with_result.assert_called_once_with(timeout=10)


class TestDiscoveryStatusEndpoint:
    """Tests for GET /api/v1/cameras/discover/status."""

    def test_status_available(self, client, mock_discovery_service):
        """Test status returns available when library installed."""
        mock_discovery_service.is_available = True

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.get("/api/v1/cameras/discover/status")

        assert response.status_code == 200
        data = response.json()

        assert data["available"] is True
        assert data["library_installed"] is True
        assert "available" in data["message"].lower()

    def test_status_unavailable(self, client, mock_discovery_service):
        """Test status returns unavailable when library not installed."""
        mock_discovery_service.is_available = False

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.get("/api/v1/cameras/discover/status")

        assert response.status_code == 200
        data = response.json()

        assert data["available"] is False
        assert data["library_installed"] is False
        assert "unavailable" in data["message"].lower()


class TestClearCacheEndpoint:
    """Tests for POST /api/v1/cameras/discover/clear-cache."""

    def test_clear_cache_success(self, client, mock_discovery_service):
        """Test cache clear returns success."""
        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover/clear-cache")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        mock_discovery_service.clear_cache.assert_called_once()


class TestDiscoveryResponseSchema:
    """Test DiscoveryResponse schema validation."""

    def test_response_schema(self, client, mock_discovery_service):
        """Verify response matches DiscoveryResponse schema."""
        mock_device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=["scope1", "scope2"],
            types=["type1"],
            metadata_version="1"
        )

        mock_result = DiscoveryResult(
            devices=[mock_device],
            duration_ms=5000,
            status="complete"
        )

        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            response = client.post("/api/v1/cameras/discover")

        data = response.json()

        # Validate all expected fields exist
        assert "status" in data
        assert "duration_ms" in data
        assert "devices" in data
        assert "device_count" in data

        # Validate device fields
        device = data["devices"][0]
        assert "endpoint_url" in device
        assert "scopes" in device
        assert "types" in device

    def test_timeout_validation(self, client, mock_discovery_service):
        """Test timeout parameter validation."""
        mock_result = DiscoveryResult(devices=[], duration_ms=0, status="complete")
        mock_discovery_service.discover_cameras_with_result.return_value = mock_result

        with patch(
            'app.api.v1.discovery.get_onvif_discovery_service',
            return_value=mock_discovery_service
        ):
            # Valid timeout
            response = client.post("/api/v1/cameras/discover", json={"timeout": 30})
            assert response.status_code == 200

            # Timeout too high (max 60)
            response = client.post("/api/v1/cameras/discover", json={"timeout": 120})
            assert response.status_code == 422  # Validation error

            # Timeout too low (min 1)
            response = client.post("/api/v1/cameras/discover", json={"timeout": 0})
            assert response.status_code == 422  # Validation error

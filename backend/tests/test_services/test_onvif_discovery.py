"""
Unit Tests for ONVIF WS-Discovery Service (Story P5-2.1)

Tests the ONVIFDiscoveryService for:
- WS-Discovery probe message generation
- Response parsing and device extraction
- Timeout behavior
- Deduplication of devices
- Cache behavior
- Error handling for malformed responses
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from app.schemas.discovery import DiscoveredDevice
from app.services.onvif_discovery_service import (
    ONVIFDiscoveryService,
    get_onvif_discovery_service,
    DiscoveryResult,
    MULTICAST_GROUP,
    MULTICAST_PORT,
    DEFAULT_TIMEOUT,
    ONVIF_NVT_TYPE,
)


class MockService:
    """Mock WS-Discovery service response."""

    def __init__(
        self,
        xaddrs: List[str],
        scopes: List[str] = None,
        types: List[str] = None,
        metadata_version: str = "1"
    ):
        self._xaddrs = xaddrs
        self._scopes = scopes or []
        self._types = types or [ONVIF_NVT_TYPE]
        self._metadata_version = metadata_version

    def getXAddrs(self):
        return self._xaddrs

    def getScopes(self):
        return self._scopes

    def getTypes(self):
        return self._types

    def getMetadataVersion(self):
        return self._metadata_version


class TestONVIFDiscoveryConstants:
    """Test discovery constants are correctly defined."""

    def test_multicast_group(self):
        """AC1: Verify multicast group is standard WS-Discovery address."""
        assert MULTICAST_GROUP == "239.255.255.250"

    def test_multicast_port(self):
        """AC1: Verify multicast port is standard WS-Discovery port."""
        assert MULTICAST_PORT == 3702

    def test_default_timeout(self):
        """AC2: Verify default timeout is 10 seconds per PRD."""
        assert DEFAULT_TIMEOUT == 10

    def test_onvif_nvt_type(self):
        """AC1: Verify ONVIF NVT type for camera targeting."""
        assert "NetworkVideoTransmitter" in ONVIF_NVT_TYPE


class TestONVIFDiscoveryServiceInit:
    """Test service initialization."""

    def test_create_service(self):
        """Test service can be instantiated."""
        service = ONVIFDiscoveryService()
        assert service is not None

    def test_singleton_instance(self):
        """Test get_onvif_discovery_service returns singleton."""
        service1 = get_onvif_discovery_service()
        service2 = get_onvif_discovery_service()
        assert service1 is service2

    def test_cache_initialized_empty(self):
        """Test cache is initially empty."""
        service = ONVIFDiscoveryService()
        assert service._cached_devices == []
        assert service._last_discovery_time is None


class TestDiscoveryServiceAvailability:
    """Test service availability checks."""

    def test_is_available_property(self):
        """Test is_available reflects library availability."""
        service = ONVIFDiscoveryService()
        # This depends on whether WSDiscovery is installed
        # At minimum, property should be accessible
        assert isinstance(service.is_available, bool)


class TestSyncDiscovery:
    """Test synchronous discovery method with mocked WS-Discovery.

    These tests require WSDiscovery to be installed. They are skipped
    if the library is not available.
    """

    @pytest.fixture(autouse=True)
    def check_wsdiscovery(self):
        """Skip tests if WSDiscovery not installed."""
        from app.services.onvif_discovery_service import WSDISCOVERY_AVAILABLE
        if not WSDISCOVERY_AVAILABLE:
            pytest.skip("WSDiscovery library not installed")

    def test_discover_single_camera(self):
        """AC4: Test discovery returns single camera correctly."""
        from app.services.onvif_discovery_service import ThreadedWSDiscovery

        with patch.object(ThreadedWSDiscovery, '__init__', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'start', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'stop', return_value=None):

            mock_service = MockService(
                xaddrs=["http://192.168.1.100:80/onvif/device_service"],
                scopes=["onvif://www.onvif.org/type/NetworkVideoTransmitter"],
                types=["tdn:NetworkVideoTransmitter"]
            )

            with patch.object(ThreadedWSDiscovery, 'searchServices', return_value=[mock_service]):
                service = ONVIFDiscoveryService()
                devices = service._sync_discover(timeout=5)

                assert len(devices) == 1
                assert devices[0].endpoint_url == "http://192.168.1.100:80/onvif/device_service"
                assert "onvif://www.onvif.org/type/NetworkVideoTransmitter" in devices[0].scopes

    def test_discover_multiple_cameras(self):
        """AC3: Test discovery handles multiple cameras."""
        from app.services.onvif_discovery_service import ThreadedWSDiscovery

        with patch.object(ThreadedWSDiscovery, '__init__', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'start', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'stop', return_value=None):

            mock_services = [
                MockService(xaddrs=["http://192.168.1.100:80/onvif/device_service"]),
                MockService(xaddrs=["http://192.168.1.101:80/onvif/device_service"]),
                MockService(xaddrs=["http://192.168.1.102:80/onvif/device_service"]),
            ]

            with patch.object(ThreadedWSDiscovery, 'searchServices', return_value=mock_services):
                service = ONVIFDiscoveryService()
                devices = service._sync_discover(timeout=5)

                assert len(devices) == 3
                urls = [d.endpoint_url for d in devices]
                assert "http://192.168.1.100:80/onvif/device_service" in urls
                assert "http://192.168.1.101:80/onvif/device_service" in urls
                assert "http://192.168.1.102:80/onvif/device_service" in urls

    def test_discover_deduplicates_same_endpoint(self):
        """AC3: Test deduplication of devices found on multiple interfaces."""
        from app.services.onvif_discovery_service import ThreadedWSDiscovery

        with patch.object(ThreadedWSDiscovery, '__init__', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'start', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'stop', return_value=None):

            # Same camera responding twice (from different interfaces)
            same_url = "http://192.168.1.100:80/onvif/device_service"
            mock_services = [
                MockService(xaddrs=[same_url]),
                MockService(xaddrs=[same_url]),  # Duplicate
            ]

            with patch.object(ThreadedWSDiscovery, 'searchServices', return_value=mock_services):
                service = ONVIFDiscoveryService()
                devices = service._sync_discover(timeout=5)

                # Should only have one device after deduplication
                assert len(devices) == 1
                assert devices[0].endpoint_url == same_url

    def test_discover_empty_response(self):
        """AC2: Test graceful handling of no responses."""
        from app.services.onvif_discovery_service import ThreadedWSDiscovery

        with patch.object(ThreadedWSDiscovery, '__init__', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'start', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'stop', return_value=None):

            with patch.object(ThreadedWSDiscovery, 'searchServices', return_value=[]):
                service = ONVIFDiscoveryService()
                devices = service._sync_discover(timeout=5)

                assert devices == []

    def test_discover_skips_empty_xaddrs(self):
        """AC3: Test devices with no XAddrs are skipped."""
        from app.services.onvif_discovery_service import ThreadedWSDiscovery

        with patch.object(ThreadedWSDiscovery, '__init__', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'start', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'stop', return_value=None):

            mock_services = [
                MockService(xaddrs=[]),  # No XAddrs
                MockService(xaddrs=["http://192.168.1.100:80/onvif/device_service"]),
            ]

            with patch.object(ThreadedWSDiscovery, 'searchServices', return_value=mock_services):
                service = ONVIFDiscoveryService()
                devices = service._sync_discover(timeout=5)

                assert len(devices) == 1

    def test_discover_handles_malformed_service(self):
        """AC3: Test graceful handling of malformed responses."""
        from app.services.onvif_discovery_service import ThreadedWSDiscovery

        with patch.object(ThreadedWSDiscovery, '__init__', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'start', return_value=None), \
             patch.object(ThreadedWSDiscovery, 'stop', return_value=None):

            # Service that raises exception on getXAddrs
            bad_service = MagicMock()
            bad_service.getXAddrs.side_effect = Exception("Malformed response")

            good_service = MockService(
                xaddrs=["http://192.168.1.100:80/onvif/device_service"]
            )

            with patch.object(ThreadedWSDiscovery, 'searchServices', return_value=[bad_service, good_service]):
                service = ONVIFDiscoveryService()
                devices = service._sync_discover(timeout=5)

                # Should still get the good device
                assert len(devices) == 1
                assert devices[0].endpoint_url == "http://192.168.1.100:80/onvif/device_service"


class TestAsyncDiscovery:
    """Test async discovery methods."""

    @pytest.mark.asyncio
    @patch('app.services.onvif_discovery_service.WSDISCOVERY_AVAILABLE', True)
    async def test_discover_cameras_with_result(self):
        """AC4, AC5: Test discover_cameras_with_result returns DiscoveryResult."""
        service = ONVIFDiscoveryService()

        # Mock _sync_discover
        with patch.object(service, '_sync_discover', return_value=[]):
            result = await service.discover_cameras_with_result(timeout=5)

        assert isinstance(result, DiscoveryResult)
        assert result.status in ["complete", "error"]
        assert result.duration_ms >= 0
        assert isinstance(result.devices, list)

    @pytest.mark.asyncio
    @patch('app.services.onvif_discovery_service.WSDISCOVERY_AVAILABLE', True)
    async def test_discover_cameras_returns_list(self):
        """AC4: Test discover_cameras returns device list."""
        service = ONVIFDiscoveryService()

        mock_device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=["onvif://www.onvif.org/type/NVT"],
            types=["tdn:NVT"]
        )

        with patch.object(service, '_sync_discover', return_value=[mock_device]):
            devices = await service.discover_cameras(timeout=5, use_cache=False)

        assert len(devices) == 1
        assert devices[0].endpoint_url == "http://192.168.1.100:80/onvif/device_service"

    @pytest.mark.asyncio
    @patch('app.services.onvif_discovery_service.WSDISCOVERY_AVAILABLE', False)
    async def test_discover_raises_when_unavailable(self):
        """Test discovery raises RuntimeError when library unavailable."""
        service = ONVIFDiscoveryService()

        with pytest.raises(RuntimeError) as exc_info:
            await service.discover_cameras()

        assert "WSDiscovery" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.onvif_discovery_service.WSDISCOVERY_AVAILABLE', False)
    async def test_discover_with_result_returns_error_when_unavailable(self):
        """Test discover_cameras_with_result returns error when library unavailable."""
        service = ONVIFDiscoveryService()

        result = await service.discover_cameras_with_result(timeout=5)

        assert result.status == "error"
        assert "WSDiscovery" in result.error


class TestDiscoveryCache:
    """Test caching behavior."""

    @pytest.mark.asyncio
    @patch('app.services.onvif_discovery_service.WSDISCOVERY_AVAILABLE', True)
    async def test_cache_is_used(self):
        """Test cached results are returned when cache is valid."""
        service = ONVIFDiscoveryService()

        mock_device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=[],
            types=[]
        )

        call_count = 0

        def mock_sync_discover(timeout):
            nonlocal call_count
            call_count += 1
            return [mock_device]

        with patch.object(service, '_sync_discover', side_effect=mock_sync_discover):
            # First call should invoke discovery
            devices1 = await service.discover_cameras(timeout=5, use_cache=True)
            # Second call should use cache
            devices2 = await service.discover_cameras(timeout=5, use_cache=True)

        assert call_count == 1  # Only one actual discovery
        assert devices1 == devices2

    @pytest.mark.asyncio
    @patch('app.services.onvif_discovery_service.WSDISCOVERY_AVAILABLE', True)
    async def test_cache_bypass(self):
        """Test use_cache=False bypasses cache."""
        service = ONVIFDiscoveryService()

        mock_device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=[],
            types=[]
        )

        call_count = 0

        def mock_sync_discover(timeout):
            nonlocal call_count
            call_count += 1
            return [mock_device]

        with patch.object(service, '_sync_discover', side_effect=mock_sync_discover):
            await service.discover_cameras(timeout=5, use_cache=False)
            await service.discover_cameras(timeout=5, use_cache=False)

        assert call_count == 2  # Discovery called both times

    def test_clear_cache(self):
        """Test clear_cache resets cache state."""
        service = ONVIFDiscoveryService()

        # Simulate cached state
        service._cached_devices = [
            DiscoveredDevice(endpoint_url="http://test", scopes=[], types=[])
        ]
        import time
        service._last_discovery_time = time.time()

        service.clear_cache()

        assert service._cached_devices == []
        assert service._last_discovery_time is None


class TestDiscoveredDeviceSchema:
    """Test DiscoveredDevice Pydantic model."""

    def test_create_device(self):
        """Test DiscoveredDevice creation."""
        device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=["onvif://www.onvif.org/type/NVT"],
            types=["tdn:NetworkVideoTransmitter"],
            metadata_version="1"
        )

        assert device.endpoint_url == "http://192.168.1.100:80/onvif/device_service"
        assert len(device.scopes) == 1
        assert len(device.types) == 1
        assert device.metadata_version == "1"

    def test_device_defaults(self):
        """Test DiscoveredDevice default values."""
        device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service"
        )

        assert device.scopes == []
        assert device.types == []
        assert device.metadata_version is None

    def test_device_serialization(self):
        """Test DiscoveredDevice JSON serialization."""
        device = DiscoveredDevice(
            endpoint_url="http://192.168.1.100:80/onvif/device_service",
            scopes=["scope1"],
            types=["type1"]
        )

        json_data = device.model_dump()

        assert json_data["endpoint_url"] == "http://192.168.1.100:80/onvif/device_service"
        assert json_data["scopes"] == ["scope1"]
        assert json_data["types"] == ["type1"]

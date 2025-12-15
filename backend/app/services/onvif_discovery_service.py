"""
ONVIF WS-Discovery Service (Story P5-2.1)

Discovers ONVIF-compatible cameras on the local network using WS-Discovery protocol.
Sends UDP multicast probes to 239.255.255.250:3702 and collects ProbeMatch responses.

Usage:
    service = ONVIFDiscoveryService()
    devices = await service.discover_cameras(timeout=10)

Architecture Reference: docs/architecture/phase-5-additions.md (ONVIF Discovery Architecture)
PRD Reference: docs/PRD-phase5.md (FR13, FR14)
"""
import asyncio
import logging
import time
from typing import List, Optional, Set
from dataclasses import dataclass, field

from app.schemas.discovery import DiscoveredDevice

logger = logging.getLogger(__name__)

# Try to import WSDiscovery
try:
    from wsdiscovery import WSDiscovery
    from wsdiscovery.discovery import ThreadedWSDiscovery
    WSDISCOVERY_AVAILABLE = True
except ImportError:
    WSDISCOVERY_AVAILABLE = False
    logger.warning("WSDiscovery not installed. ONVIF camera discovery will be unavailable.")


# WS-Discovery constants per spec
MULTICAST_GROUP = "239.255.255.250"
MULTICAST_PORT = 3702
DEFAULT_TIMEOUT = 10  # seconds

# ONVIF-specific types to search for
# NetworkVideoTransmitter (NVT) is the main camera type
ONVIF_NVT_TYPE = "dn:NetworkVideoTransmitter"
ONVIF_NVT_ALT_TYPE = "tdn:NetworkVideoTransmitter"

# ONVIF scope patterns
ONVIF_SCOPE_PREFIX = "onvif://www.onvif.org"


@dataclass
class DiscoveryResult:
    """Internal result from discovery operation."""
    devices: List[DiscoveredDevice] = field(default_factory=list)
    duration_ms: int = 0
    error: Optional[str] = None
    status: str = "complete"


class ONVIFDiscoveryService:
    """
    ONVIF WS-Discovery service for camera auto-discovery.

    Uses WS-Discovery protocol to find ONVIF-compatible network cameras.
    Discovery process:
    1. Send WS-Discovery Probe message to UDP multicast address
    2. Wait for ProbeMatch responses from devices
    3. Parse responses and extract device service URLs
    4. Deduplicate devices found on multiple network interfaces

    Example:
        >>> service = ONVIFDiscoveryService()
        >>> devices = await service.discover_cameras(timeout=10)
        >>> for device in devices:
        ...     print(f"Found: {device.endpoint_url}")
    """

    def __init__(self):
        """Initialize the discovery service."""
        self._discovery_lock = asyncio.Lock()
        self._last_discovery_time: Optional[float] = None
        self._cached_devices: List[DiscoveredDevice] = []
        self._cache_ttl = 30  # seconds - cache discovery results briefly

    @property
    def is_available(self) -> bool:
        """Check if WS-Discovery library is available."""
        return WSDISCOVERY_AVAILABLE

    async def discover_cameras(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        use_cache: bool = True
    ) -> List[DiscoveredDevice]:
        """
        Discover ONVIF cameras on the local network.

        Sends WS-Discovery probes and collects responses from ONVIF devices.
        Results are cached for a short period to avoid excessive network traffic.

        Args:
            timeout: Discovery timeout in seconds (default: 10)
            use_cache: Whether to use cached results if available (default: True)

        Returns:
            List of discovered ONVIF devices with their service URLs

        Raises:
            RuntimeError: If WS-Discovery library is not available
        """
        if not WSDISCOVERY_AVAILABLE:
            logger.error("WS-Discovery library not installed")
            raise RuntimeError(
                "ONVIF discovery unavailable: WSDiscovery package not installed. "
                "Install with: pip install WSDiscovery"
            )

        # Check cache
        if use_cache and self._is_cache_valid():
            logger.debug(
                f"Returning cached discovery results: {len(self._cached_devices)} devices"
            )
            return self._cached_devices.copy()

        # Use lock to prevent concurrent discovery scans
        async with self._discovery_lock:
            # Double-check cache after acquiring lock
            if use_cache and self._is_cache_valid():
                return self._cached_devices.copy()

            result = await self._run_discovery(timeout)

            # Update cache
            self._cached_devices = result.devices
            self._last_discovery_time = time.time()

            return result.devices

    async def discover_cameras_with_result(
        self,
        timeout: int = DEFAULT_TIMEOUT
    ) -> DiscoveryResult:
        """
        Discover cameras and return full result including timing and errors.

        This is the method used by the API endpoint to get complete response data.

        Args:
            timeout: Discovery timeout in seconds

        Returns:
            DiscoveryResult with devices, duration, status, and any error
        """
        if not WSDISCOVERY_AVAILABLE:
            return DiscoveryResult(
                devices=[],
                duration_ms=0,
                status="error",
                error="ONVIF discovery unavailable: WSDiscovery package not installed"
            )

        async with self._discovery_lock:
            result = await self._run_discovery(timeout)

            # Update cache
            self._cached_devices = result.devices
            self._last_discovery_time = time.time()

            return result

    async def _run_discovery(self, timeout: int) -> DiscoveryResult:
        """
        Execute the actual WS-Discovery scan.

        Uses ThreadedWSDiscovery which handles:
        - Sending probe messages to multicast address
        - Listening on all network interfaces
        - Collecting and deduplicating responses

        Args:
            timeout: Maximum time to wait for responses

        Returns:
            DiscoveryResult with found devices
        """
        start_time = time.time()

        try:
            logger.info(
                f"Starting ONVIF discovery scan (timeout: {timeout}s, "
                f"multicast: {MULTICAST_GROUP}:{MULTICAST_PORT})"
            )

            # Run blocking discovery in thread pool
            devices = await asyncio.get_event_loop().run_in_executor(
                None,
                self._sync_discover,
                timeout
            )

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Discovery complete: found {len(devices)} ONVIF device(s) "
                f"in {duration_ms}ms"
            )

            return DiscoveryResult(
                devices=devices,
                duration_ms=duration_ms,
                status="complete"
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Discovery failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return DiscoveryResult(
                devices=[],
                duration_ms=duration_ms,
                status="error",
                error=error_msg
            )

    def _sync_discover(self, timeout: int) -> List[DiscoveredDevice]:
        """
        Synchronous discovery using WSDiscovery library.

        This runs in a thread pool to avoid blocking the event loop.

        Args:
            timeout: Discovery timeout in seconds

        Returns:
            List of discovered devices
        """
        wsd = ThreadedWSDiscovery()
        discovered_devices: List[DiscoveredDevice] = []
        seen_endpoints: Set[str] = set()  # For deduplication

        try:
            wsd.start()

            # Search for ONVIF Network Video Transmitters
            # Pass types to filter for ONVIF cameras only
            services = wsd.searchServices(
                timeout=timeout,
                types=[ONVIF_NVT_TYPE]
            )

            logger.debug(f"WS-Discovery returned {len(services)} service(s)")

            for service in services:
                try:
                    # Get XAddrs (service endpoints)
                    xaddrs = service.getXAddrs()
                    if not xaddrs:
                        continue

                    # Use first endpoint URL
                    endpoint_url = xaddrs[0]

                    # Skip if already seen (deduplication)
                    if endpoint_url in seen_endpoints:
                        logger.debug(f"Skipping duplicate endpoint: {endpoint_url}")
                        continue

                    seen_endpoints.add(endpoint_url)

                    # Extract scopes
                    scopes = []
                    raw_scopes = service.getScopes()
                    if raw_scopes:
                        scopes = [str(s) for s in raw_scopes]

                    # Extract types
                    types = []
                    raw_types = service.getTypes()
                    if raw_types:
                        types = [str(t) for t in raw_types]

                    # Get metadata version if available
                    metadata_version = None
                    try:
                        metadata_version = str(service.getMetadataVersion())
                    except Exception:
                        pass

                    device = DiscoveredDevice(
                        endpoint_url=endpoint_url,
                        scopes=scopes,
                        types=types,
                        metadata_version=metadata_version
                    )

                    discovered_devices.append(device)
                    logger.debug(
                        f"Discovered ONVIF device: {endpoint_url} "
                        f"(types: {types}, scopes: {len(scopes)})"
                    )

                except Exception as e:
                    logger.warning(f"Error parsing discovery response: {e}")
                    continue

        finally:
            try:
                wsd.stop()
            except Exception as e:
                logger.warning(f"Error stopping WS-Discovery: {e}")

        return discovered_devices

    def _is_cache_valid(self) -> bool:
        """Check if cached results are still valid."""
        if self._last_discovery_time is None:
            return False
        return (time.time() - self._last_discovery_time) < self._cache_ttl

    def clear_cache(self) -> None:
        """Clear cached discovery results."""
        self._cached_devices = []
        self._last_discovery_time = None
        logger.debug("Discovery cache cleared")


# Singleton instance
_discovery_service: Optional[ONVIFDiscoveryService] = None


def get_onvif_discovery_service() -> ONVIFDiscoveryService:
    """
    Get the singleton ONVIFDiscoveryService instance.

    Returns:
        The shared discovery service instance
    """
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = ONVIFDiscoveryService()
    return _discovery_service

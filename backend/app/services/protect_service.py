"""
UniFi Protect Service for controller connection management (Story P2-1.4)

Provides functionality to:
- Test controller connections before saving
- Manage persistent WebSocket connections for real-time events
- Auto-reconnect with exponential backoff on disconnect
- Broadcast connection status changes to frontend
- Discover cameras from connected controllers (future stories)
"""
import asyncio
import ssl
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp
from uiprotect import ProtectApiClient
from uiprotect.exceptions import BadRequest, NotAuthorized, NvrError

from app.core.database import SessionLocal
from app.services.websocket_manager import get_websocket_manager

if TYPE_CHECKING:
    from app.models.protect_controller import ProtectController

logger = logging.getLogger(__name__)

# Connection timeout in seconds (NFR3)
CONNECTION_TIMEOUT = 10.0

# Exponential backoff delays in seconds (AC3)
BACKOFF_DELAYS = [1, 2, 4, 8, 16, 30]  # max 30 seconds

# WebSocket message type for connection status (AC6)
PROTECT_CONNECTION_STATUS = "PROTECT_CONNECTION_STATUS"


@dataclass
class ConnectionTestResult:
    """Result of a controller connection test"""
    success: bool
    message: str
    firmware_version: Optional[str] = None
    camera_count: Optional[int] = None
    error_type: Optional[str] = None


class ProtectService:
    """
    Service class for UniFi Protect controller operations (Story P2-1.4).

    Handles connection testing, WebSocket connection management, and
    real-time event streaming from UniFi Protect controllers.

    Features:
    - Test controller connections before saving
    - Maintain persistent WebSocket connections
    - Auto-reconnect with exponential backoff on disconnect
    - Broadcast connection status changes to frontend
    - Graceful shutdown with cleanup

    Attributes:
        _connections: Dict mapping controller_id to ProtectApiClient
        _listener_tasks: Dict mapping controller_id to asyncio.Task
        _shutdown_event: Event to signal shutdown to all listeners
    """

    def __init__(self):
        """Initialize the ProtectService with empty connection dictionaries."""
        # Active client connections (AC9: stored for lifecycle management)
        self._connections: Dict[str, ProtectApiClient] = {}
        # Background WebSocket listener tasks
        self._listener_tasks: Dict[str, asyncio.Task] = {}
        # Shutdown signal for graceful cleanup
        self._shutdown_event = asyncio.Event()

    async def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        verify_ssl: bool = False
    ) -> ConnectionTestResult:
        """
        Test connection to a UniFi Protect controller.

        Attempts to connect to the controller, authenticate, and retrieve
        basic information (firmware version, camera count).

        Args:
            host: Controller IP address or hostname
            port: HTTPS port (default 443)
            username: Protect authentication username
            password: Protect authentication password
            verify_ssl: Whether to verify SSL certificates

        Returns:
            ConnectionTestResult with success status and details

        Note:
            This method does not persist any data - test-only operation.
            Connection is closed after test regardless of outcome.
        """
        # Log connection attempt (no credentials)
        logger.info(
            f"Testing Protect controller connection",
            extra={
                "event_type": "protect_connection_test_start",
                "host": host,
                "port": port,
                "verify_ssl": verify_ssl
            }
        )

        client = None
        try:
            # Create client with SSL verification setting
            client = ProtectApiClient(
                host=host,
                port=port,
                username=username,
                password=password,
                verify_ssl=verify_ssl
            )

            # Attempt login and update with timeout
            async def connect_and_update():
                await client.update()  # uiprotect handles login internally in update()

            await asyncio.wait_for(
                connect_and_update(),
                timeout=CONNECTION_TIMEOUT
            )

            # Extract controller info
            firmware_version = None
            camera_count = 0

            if client.bootstrap:
                if client.bootstrap.nvr:
                    # Convert Version object to string
                    firmware_version = str(client.bootstrap.nvr.version)
                camera_count = len(client.bootstrap.cameras) if client.bootstrap.cameras else 0

            logger.info(
                f"Protect controller connection successful",
                extra={
                    "event_type": "protect_connection_test_success",
                    "host": host,
                    "firmware_version": firmware_version,
                    "camera_count": camera_count
                }
            )

            return ConnectionTestResult(
                success=True,
                message="Connected successfully",
                firmware_version=firmware_version,
                camera_count=camera_count
            )

        except asyncio.TimeoutError:
            logger.warning(
                f"Protect controller connection timed out",
                extra={
                    "event_type": "protect_connection_test_timeout",
                    "host": host,
                    "timeout_seconds": CONNECTION_TIMEOUT
                }
            )
            return ConnectionTestResult(
                success=False,
                message=f"Connection timed out after {int(CONNECTION_TIMEOUT)} seconds",
                error_type="timeout"
            )

        except NotAuthorized:
            logger.warning(
                f"Protect controller authentication failed",
                extra={
                    "event_type": "protect_connection_test_auth_failed",
                    "host": host
                }
            )
            return ConnectionTestResult(
                success=False,
                message="Authentication failed",
                error_type="auth_error"
            )

        except aiohttp.ClientConnectorCertificateError as e:
            logger.warning(
                f"Protect controller SSL certificate error",
                extra={
                    "event_type": "protect_connection_test_ssl_error",
                    "host": host,
                    "error_type": "ssl_certificate"
                }
            )
            return ConnectionTestResult(
                success=False,
                message="SSL certificate verification failed",
                error_type="ssl_error"
            )

        except ssl.SSLError as e:
            logger.warning(
                f"Protect controller SSL error",
                extra={
                    "event_type": "protect_connection_test_ssl_error",
                    "host": host,
                    "error_type": "ssl"
                }
            )
            return ConnectionTestResult(
                success=False,
                message="SSL certificate verification failed",
                error_type="ssl_error"
            )

        except aiohttp.ClientConnectorError as e:
            logger.warning(
                f"Protect controller host unreachable",
                extra={
                    "event_type": "protect_connection_test_unreachable",
                    "host": host
                }
            )
            return ConnectionTestResult(
                success=False,
                message=f"Host unreachable: {host}",
                error_type="connection_error"
            )

        except (BadRequest, NvrError) as e:
            logger.warning(
                f"Protect controller error",
                extra={
                    "event_type": "protect_connection_test_error",
                    "host": host,
                    "error_type": type(e).__name__
                }
            )
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {type(e).__name__}",
                error_type="nvr_error"
            )

        except Exception as e:
            logger.error(
                f"Protect controller unexpected error",
                extra={
                    "event_type": "protect_connection_test_error",
                    "host": host,
                    "error_type": type(e).__name__
                }
            )
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {type(e).__name__}",
                error_type="unknown"
            )

        finally:
            # Always close the client connection
            if client:
                try:
                    await client.close()
                except Exception:
                    pass  # Ignore errors during cleanup

    # =========================================================================
    # Connection Management Methods (Story P2-1.4)
    # =========================================================================

    async def connect(self, controller: "ProtectController") -> bool:
        """
        Establish a persistent WebSocket connection to a Protect controller (AC1).

        Creates a ProtectApiClient, connects to the controller, starts a
        background WebSocket listener task, and updates the database state.

        Args:
            controller: ProtectController model instance with connection details

        Returns:
            True if connection established successfully, False otherwise

        Note:
            On success, broadcasts PROTECT_CONNECTION_STATUS to frontend (AC6)
            and updates database fields is_connected, last_connected_at (AC2).
        """
        controller_id = str(controller.id)

        # Check if already connected
        if controller_id in self._connections:
            logger.info(
                "Controller already connected",
                extra={
                    "event_type": "protect_connect_already_connected",
                    "controller_id": controller_id,
                    "controller_name": controller.name
                }
            )
            return True

        # Broadcast connecting status (AC6)
        await self._broadcast_status(controller_id, "connecting")

        logger.info(
            "Connecting to Protect controller",
            extra={
                "event_type": "protect_connect_start",
                "controller_id": controller_id,
                "controller_name": controller.name,
                "host": controller.host
            }
        )

        try:
            # Create client with decrypted password
            client = ProtectApiClient(
                host=controller.host,
                port=controller.port,
                username=controller.username,
                password=controller.get_decrypted_password(),
                verify_ssl=controller.verify_ssl
            )

            # Connect with timeout
            await asyncio.wait_for(
                client.update(),
                timeout=CONNECTION_TIMEOUT
            )

            # Store the connected client (AC9)
            self._connections[controller_id] = client

            # Update database state (AC2)
            await self._update_controller_state(
                controller_id,
                is_connected=True,
                last_connected_at=datetime.now(timezone.utc),
                last_error=None
            )

            # Start background WebSocket listener task
            task = asyncio.create_task(
                self._websocket_listener(controller),
                name=f"protect_ws_{controller_id}"
            )
            self._listener_tasks[controller_id] = task

            # Broadcast connected status (AC6)
            await self._broadcast_status(controller_id, "connected")

            logger.info(
                "Protect controller connected successfully",
                extra={
                    "event_type": "protect_connect_success",
                    "controller_id": controller_id,
                    "controller_name": controller.name
                }
            )

            return True

        except asyncio.TimeoutError:
            error_msg = f"Connection timed out after {int(CONNECTION_TIMEOUT)} seconds"
            await self._handle_connection_error(controller_id, error_msg, "timeout")
            return False

        except NotAuthorized:
            error_msg = "Authentication failed - check credentials"
            await self._handle_connection_error(controller_id, error_msg, "auth_error")
            return False

        except aiohttp.ClientConnectorCertificateError:
            error_msg = "SSL certificate verification failed"
            await self._handle_connection_error(controller_id, error_msg, "ssl_error")
            return False

        except ssl.SSLError:
            error_msg = "SSL certificate verification failed"
            await self._handle_connection_error(controller_id, error_msg, "ssl_error")
            return False

        except aiohttp.ClientConnectorError:
            error_msg = f"Host unreachable: {controller.host}"
            await self._handle_connection_error(controller_id, error_msg, "connection_error")
            return False

        except (BadRequest, NvrError) as e:
            error_msg = f"Controller error: {type(e).__name__}"
            await self._handle_connection_error(controller_id, error_msg, "nvr_error")
            return False

        except asyncio.CancelledError:
            # Graceful shutdown - don't treat as error
            logger.info(
                "Connection cancelled during shutdown",
                extra={
                    "event_type": "protect_connect_cancelled",
                    "controller_id": controller_id
                }
            )
            raise

        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}"
            await self._handle_connection_error(controller_id, error_msg, "unknown")
            return False

    async def disconnect(self, controller_id: str) -> None:
        """
        Disconnect from a Protect controller and cleanup resources (AC5).

        Cancels the WebSocket listener task, closes the client connection,
        and updates the database state.

        Args:
            controller_id: UUID of the controller to disconnect

        Note:
            Safe to call even if not connected (no-op).
            Updates is_connected to False in database.
            Broadcasts disconnected status to frontend.
        """
        logger.info(
            "Disconnecting from Protect controller",
            extra={
                "event_type": "protect_disconnect_start",
                "controller_id": controller_id
            }
        )

        # Cancel listener task if exists
        if controller_id in self._listener_tasks:
            task = self._listener_tasks.pop(controller_id)
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        # Close client connection if exists
        if controller_id in self._connections:
            client = self._connections.pop(controller_id)
            try:
                await client.close()
            except Exception:
                pass  # Ignore errors during cleanup

        # Update database state (AC5)
        await self._update_controller_state(
            controller_id,
            is_connected=False,
            last_error=None
        )

        # Broadcast disconnected status (AC6)
        await self._broadcast_status(controller_id, "disconnected")

        logger.info(
            "Protect controller disconnected",
            extra={
                "event_type": "protect_disconnect_complete",
                "controller_id": controller_id
            }
        )

    async def disconnect_all(self, timeout: float = 10.0) -> None:
        """
        Disconnect all controllers gracefully (AC5).

        Used during application shutdown to cleanly close all connections.

        Args:
            timeout: Maximum time to wait for all disconnections
        """
        logger.info(
            "Disconnecting all Protect controllers",
            extra={
                "event_type": "protect_disconnect_all_start",
                "controller_count": len(self._connections)
            }
        )

        # Signal shutdown to all listeners
        self._shutdown_event.set()

        # Disconnect each controller
        controller_ids = list(self._connections.keys())
        disconnect_tasks = [
            self.disconnect(controller_id)
            for controller_id in controller_ids
        ]

        if disconnect_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*disconnect_tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout during disconnect_all",
                    extra={
                        "event_type": "protect_disconnect_all_timeout",
                        "timeout_seconds": timeout
                    }
                )

        # Clear any remaining references
        self._connections.clear()
        self._listener_tasks.clear()

        logger.info(
            "All Protect controllers disconnected",
            extra={"event_type": "protect_disconnect_all_complete"}
        )

    async def _websocket_listener(self, controller: "ProtectController") -> None:
        """
        Background task that maintains WebSocket connection (AC1, AC3, AC4).

        Subscribes to controller events and handles reconnection on disconnect.
        Runs until cancelled or shutdown event is set.

        Args:
            controller: ProtectController model instance
        """
        controller_id = str(controller.id)

        while not self._shutdown_event.is_set():
            try:
                client = self._connections.get(controller_id)
                if not client:
                    logger.warning(
                        "No client found for listener",
                        extra={
                            "event_type": "protect_listener_no_client",
                            "controller_id": controller_id
                        }
                    )
                    break

                # Subscribe to WebSocket events
                def event_callback(msg):
                    # Event handling will be implemented in Story P2-3.1
                    # For now, just acknowledge receipt
                    pass

                unsub = client.subscribe_websocket(event_callback)

                try:
                    # Keep alive until disconnected or shutdown
                    while not self._shutdown_event.is_set():
                        await asyncio.sleep(1)

                        # Check if client is still valid
                        if controller_id not in self._connections:
                            break

                finally:
                    # Unsubscribe from events
                    if unsub:
                        unsub()

            except asyncio.CancelledError:
                logger.info(
                    "WebSocket listener cancelled",
                    extra={
                        "event_type": "protect_listener_cancelled",
                        "controller_id": controller_id
                    }
                )
                break

            except Exception as e:
                # Connection lost - attempt reconnect with backoff (AC3, AC4)
                logger.warning(
                    "WebSocket connection lost, will reconnect",
                    extra={
                        "event_type": "protect_listener_error",
                        "controller_id": controller_id,
                        "error_type": type(e).__name__
                    }
                )

                # Update state and broadcast reconnecting status
                await self._update_controller_state(
                    controller_id,
                    is_connected=False,
                    last_error=f"Connection lost: {type(e).__name__}"
                )
                await self._broadcast_status(controller_id, "reconnecting")

                # Remove current client
                if controller_id in self._connections:
                    old_client = self._connections.pop(controller_id)
                    try:
                        await old_client.close()
                    except Exception:
                        pass

                # Attempt reconnect with exponential backoff
                if not self._shutdown_event.is_set():
                    await self._reconnect_with_backoff(controller)

    async def _reconnect_with_backoff(self, controller: "ProtectController") -> None:
        """
        Attempt to reconnect with exponential backoff (AC3, AC4).

        Delays: 1s, 2s, 4s, 8s, 16s, 30s (max). Unlimited attempts.
        First attempt within 5 seconds of disconnect (NFR3/AC4).

        Args:
            controller: ProtectController model instance to reconnect
        """
        controller_id = str(controller.id)
        attempt = 0

        logger.info(
            "Starting reconnection with backoff",
            extra={
                "event_type": "protect_reconnect_start",
                "controller_id": controller_id,
                "controller_name": controller.name
            }
        )

        while not self._shutdown_event.is_set():
            # Calculate delay using exponential backoff
            delay = BACKOFF_DELAYS[min(attempt, len(BACKOFF_DELAYS) - 1)]

            logger.info(
                f"Reconnect attempt {attempt + 1} in {delay}s",
                extra={
                    "event_type": "protect_reconnect_attempt",
                    "controller_id": controller_id,
                    "attempt": attempt + 1,
                    "delay_seconds": delay
                }
            )

            # Wait before attempting (first wait is 1s, satisfies AC4 < 5s)
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=delay
                )
                # Shutdown event was set - exit
                break
            except asyncio.TimeoutError:
                # Timeout expired - continue with reconnect attempt
                pass

            # Attempt reconnection
            try:
                # Refresh controller from database in case credentials changed
                db = SessionLocal()
                try:
                    from app.models.protect_controller import ProtectController as PC
                    fresh_controller = db.query(PC).filter(PC.id == controller_id).first()
                    if not fresh_controller:
                        logger.error(
                            "Controller no longer exists",
                            extra={
                                "event_type": "protect_reconnect_controller_gone",
                                "controller_id": controller_id
                            }
                        )
                        break
                finally:
                    db.close()

                # Create new client
                client = ProtectApiClient(
                    host=fresh_controller.host,
                    port=fresh_controller.port,
                    username=fresh_controller.username,
                    password=fresh_controller.get_decrypted_password(),
                    verify_ssl=fresh_controller.verify_ssl
                )

                # Connect with timeout
                await asyncio.wait_for(
                    client.update(),
                    timeout=CONNECTION_TIMEOUT
                )

                # Success - store client and update state
                self._connections[controller_id] = client

                await self._update_controller_state(
                    controller_id,
                    is_connected=True,
                    last_connected_at=datetime.now(timezone.utc),
                    last_error=None
                )

                await self._broadcast_status(controller_id, "connected")

                logger.info(
                    "Reconnection successful",
                    extra={
                        "event_type": "protect_reconnect_success",
                        "controller_id": controller_id,
                        "attempts": attempt + 1
                    }
                )

                return  # Exit backoff loop on success

            except asyncio.CancelledError:
                raise

            except Exception as e:
                logger.warning(
                    f"Reconnect attempt {attempt + 1} failed",
                    extra={
                        "event_type": "protect_reconnect_failed",
                        "controller_id": controller_id,
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__
                    }
                )

                await self._update_controller_state(
                    controller_id,
                    is_connected=False,
                    last_error=f"Reconnect failed: {type(e).__name__}"
                )

            attempt += 1

    async def _handle_connection_error(
        self,
        controller_id: str,
        error_msg: str,
        error_type: str
    ) -> None:
        """
        Handle connection error by updating state and broadcasting (AC7).

        Args:
            controller_id: Controller UUID
            error_msg: Human-readable error message
            error_type: Error classification for logging
        """
        logger.warning(
            f"Protect connection error: {error_msg}",
            extra={
                "event_type": "protect_connection_error",
                "controller_id": controller_id,
                "error_type": error_type
                # Note: No credentials logged (AC7)
            }
        )

        # Update database state (AC7)
        await self._update_controller_state(
            controller_id,
            is_connected=False,
            last_error=error_msg
        )

        # Broadcast error status (AC6)
        await self._broadcast_status(controller_id, "error", error_msg)

    async def _update_controller_state(
        self,
        controller_id: str,
        is_connected: Optional[bool] = None,
        last_connected_at: Optional[datetime] = None,
        last_error: Optional[str] = None
    ) -> None:
        """
        Update controller state in database (AC2, AC7).

        Uses SessionLocal for background task database operations.

        Args:
            controller_id: Controller UUID
            is_connected: New connection status (optional)
            last_connected_at: Timestamp of successful connection (optional)
            last_error: Error message or None to clear (optional)
        """
        db = SessionLocal()
        try:
            from app.models.protect_controller import ProtectController as PC
            controller = db.query(PC).filter(PC.id == controller_id).first()

            if controller:
                if is_connected is not None:
                    controller.is_connected = is_connected
                if last_connected_at is not None:
                    controller.last_connected_at = last_connected_at
                if last_error is not None or last_error == "":
                    controller.last_error = last_error if last_error else None

                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(
                f"Failed to update controller state",
                extra={
                    "event_type": "protect_state_update_error",
                    "controller_id": controller_id,
                    "error": str(e)
                }
            )
        finally:
            db.close()

    async def _broadcast_status(
        self,
        controller_id: str,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Broadcast connection status to frontend via WebSocket (AC6).

        Message format:
        {
            "type": "PROTECT_CONNECTION_STATUS",
            "data": {
                "controller_id": "uuid",
                "status": "connected|disconnected|connecting|reconnecting|error",
                "error": "optional error message"
            },
            "timestamp": "ISO8601"  // Added by WebSocketManager
        }

        Args:
            controller_id: Controller UUID
            status: Connection status string
            error: Optional error message for error status
        """
        message = {
            "type": PROTECT_CONNECTION_STATUS,
            "data": {
                "controller_id": controller_id,
                "status": status
            }
        }

        if error:
            message["data"]["error"] = error

        websocket_manager = get_websocket_manager()
        await websocket_manager.broadcast(message)

    def get_connection_status(self, controller_id: str) -> Dict[str, Any]:
        """
        Get current connection status for a controller.

        Args:
            controller_id: Controller UUID

        Returns:
            Dict with 'connected' boolean and 'has_task' boolean
        """
        return {
            "connected": controller_id in self._connections,
            "has_task": controller_id in self._listener_tasks and not self._listener_tasks[controller_id].done()
        }

    def get_all_connection_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get connection status for all tracked controllers (AC9).

        Returns:
            Dict mapping controller_id to status dict
        """
        statuses = {}
        for controller_id in set(list(self._connections.keys()) + list(self._listener_tasks.keys())):
            statuses[controller_id] = self.get_connection_status(controller_id)
        return statuses


# Singleton instance for the service
_protect_service: Optional[ProtectService] = None


def get_protect_service() -> ProtectService:
    """Get the singleton ProtectService instance."""
    global _protect_service
    if _protect_service is None:
        _protect_service = ProtectService()
    return _protect_service

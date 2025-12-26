"""
Cloudflare Tunnel Service

Manages cloudflared tunnel subprocess for secure remote access.
Story P11-1.1: Implement Cloudflare Tunnel Integration

This service provides:
- Async subprocess management for cloudflared tunnel
- Connection status monitoring via stdout/stderr parsing
- Graceful start/stop with lifecycle management
- Token validation and security
"""
import asyncio
import re
import logging
from typing import Optional
from enum import Enum


logger = logging.getLogger(__name__)


class TunnelStatus(str, Enum):
    """Tunnel connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class TunnelService:
    """
    Manages cloudflared tunnel subprocess for secure remote access.

    Usage:
        service = TunnelService()
        await service.start(token="your-tunnel-token")

        # Check status
        if service.is_connected:
            print(f"Connected: {service.hostname}")

        # Stop tunnel
        await service.stop()
    """

    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._status: TunnelStatus = TunnelStatus.DISCONNECTED
        self._hostname: Optional[str] = None
        self._error_message: Optional[str] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def status(self) -> TunnelStatus:
        """Current tunnel connection status."""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Whether tunnel is currently connected."""
        return self._status == TunnelStatus.CONNECTED

    @property
    def hostname(self) -> Optional[str]:
        """Connected tunnel hostname, if available."""
        return self._hostname

    @property
    def error_message(self) -> Optional[str]:
        """Last error message, if any."""
        return self._error_message

    @property
    def is_running(self) -> bool:
        """Whether the tunnel process is running."""
        return self._process is not None and self._process.returncode is None

    def _validate_token(self, token: str) -> bool:
        """
        Validate tunnel token format to prevent command injection.

        Cloudflare tunnel tokens are base64-encoded and follow a specific format.
        We reject any token containing shell metacharacters.

        Args:
            token: The tunnel token to validate

        Returns:
            True if token format is valid, False otherwise
        """
        if not token:
            return False

        # Cloudflare tunnel tokens are base64-encoded JWT-like strings
        # They should only contain alphanumeric chars, hyphens, underscores, and dots
        # No shell metacharacters allowed
        invalid_chars = re.compile(r'[;&|`$(){}[\]<>!#\'\"\\\n\r\t]')
        if invalid_chars.search(token):
            logger.warning(
                "Invalid characters in tunnel token",
                extra={"event_type": "tunnel_token_validation_failed"}
            )
            return False

        # Token should be reasonably long (typical JWT is 100+ chars)
        if len(token) < 50:
            logger.warning(
                "Tunnel token too short",
                extra={"event_type": "tunnel_token_validation_failed"}
            )
            return False

        return True

    async def start(self, token: str) -> bool:
        """
        Start the cloudflared tunnel with the given token.

        Args:
            token: Cloudflare tunnel token (from Cloudflare Zero Trust dashboard)

        Returns:
            True if tunnel started successfully, False otherwise
        """
        async with self._lock:
            if self.is_running:
                logger.warning(
                    "Tunnel already running, stop first",
                    extra={"event_type": "tunnel_already_running"}
                )
                return False

            # Validate token format
            if not self._validate_token(token):
                self._status = TunnelStatus.ERROR
                self._error_message = "Invalid tunnel token format"
                return False

            self._status = TunnelStatus.CONNECTING
            self._error_message = None

            try:
                # Start cloudflared process
                # Never log the token value
                logger.info(
                    "Starting cloudflared tunnel",
                    extra={"event_type": "tunnel_starting"}
                )

                self._process = await asyncio.create_subprocess_exec(
                    "cloudflared",
                    "tunnel",
                    "run",
                    "--token",
                    token,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Start monitoring task
                self._monitor_task = asyncio.create_task(self._monitor_output())

                # Wait briefly to check for immediate failures
                await asyncio.sleep(2)

                if self._process.returncode is not None:
                    # Process exited immediately - likely error
                    self._status = TunnelStatus.ERROR
                    return False

                logger.info(
                    "Cloudflared tunnel process started",
                    extra={
                        "event_type": "tunnel_process_started",
                        "pid": self._process.pid
                    }
                )

                return True

            except FileNotFoundError:
                self._status = TunnelStatus.ERROR
                self._error_message = "cloudflared not found - please install it"
                logger.error(
                    "cloudflared executable not found",
                    extra={"event_type": "tunnel_cloudflared_not_found"}
                )
                return False
            except Exception as e:
                self._status = TunnelStatus.ERROR
                self._error_message = str(e)
                logger.error(
                    f"Failed to start tunnel: {e}",
                    extra={"event_type": "tunnel_start_failed", "error": str(e)}
                )
                return False

    async def _monitor_output(self):
        """
        Monitor cloudflared stdout/stderr for status updates.

        Parses output to detect connection status and extract hostname.
        """
        if not self._process:
            return

        try:
            while self._process.returncode is None:
                # Read from stderr (cloudflared logs to stderr)
                if self._process.stderr:
                    line = await asyncio.wait_for(
                        self._process.stderr.readline(),
                        timeout=30
                    )
                    if line:
                        line_str = line.decode('utf-8', errors='replace').strip()
                        await self._parse_log_line(line_str)
                else:
                    await asyncio.sleep(1)
        except asyncio.TimeoutError:
            # No output for 30 seconds, just continue
            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                f"Error monitoring tunnel output: {e}",
                extra={"event_type": "tunnel_monitor_error", "error": str(e)}
            )
        finally:
            if self._process and self._process.returncode is not None:
                self._status = TunnelStatus.DISCONNECTED
                logger.info(
                    "Cloudflared tunnel process exited",
                    extra={
                        "event_type": "tunnel_process_exited",
                        "return_code": self._process.returncode
                    }
                )

    async def _parse_log_line(self, line: str):
        """
        Parse cloudflared log line for status information.

        Args:
            line: Log line from cloudflared stderr
        """
        # Don't log the full line as it may contain sensitive info
        # Just look for specific patterns

        # Connection established
        if "Connection" in line and "registered" in line:
            self._status = TunnelStatus.CONNECTED
            logger.info(
                "Cloudflared tunnel connected",
                extra={"event_type": "tunnel_connected"}
            )

        # Extract hostname if present
        # Pattern like: "Registered tunnel connection ... origin=https://example.cloudflare.com"
        hostname_match = re.search(r'origin=https?://([^\s,]+)', line)
        if hostname_match:
            self._hostname = hostname_match.group(1)
            logger.info(
                "Tunnel hostname detected",
                extra={"event_type": "tunnel_hostname", "hostname": self._hostname}
            )

        # Also look for ingress rules with URLs
        # Pattern: "Ingress ... URL https://something.trycloudflare.com"
        url_match = re.search(r'https://([a-zA-Z0-9\-\.]+\.(?:trycloudflare\.com|cloudflare\.com|cfargotunnel\.com))', line)
        if url_match and not self._hostname:
            self._hostname = url_match.group(1)
            logger.info(
                "Tunnel hostname detected from URL",
                extra={"event_type": "tunnel_hostname", "hostname": self._hostname}
            )

        # Error detection
        if "error" in line.lower() or "failed" in line.lower():
            if "retrying" not in line.lower():  # Ignore transient retry messages
                self._error_message = line[:200]  # Truncate for safety
                logger.warning(
                    "Tunnel error detected",
                    extra={"event_type": "tunnel_error"}
                )

    async def stop(self, timeout: float = 10.0) -> bool:
        """
        Stop the cloudflared tunnel gracefully.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown

        Returns:
            True if tunnel stopped successfully
        """
        async with self._lock:
            if not self._process:
                self._status = TunnelStatus.DISCONNECTED
                return True

            logger.info(
                "Stopping cloudflared tunnel",
                extra={"event_type": "tunnel_stopping", "pid": self._process.pid}
            )

            # Cancel monitor task
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Try graceful shutdown first
            try:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(
                        "Tunnel did not stop gracefully, killing",
                        extra={"event_type": "tunnel_force_kill"}
                    )
                    self._process.kill()
                    await self._process.wait()
            except ProcessLookupError:
                # Process already exited
                pass

            self._process = None
            self._status = TunnelStatus.DISCONNECTED
            self._hostname = None
            self._error_message = None

            logger.info(
                "Cloudflared tunnel stopped",
                extra={"event_type": "tunnel_stopped"}
            )

            return True

    def get_status_dict(self) -> dict:
        """
        Get tunnel status as a dictionary for API responses.

        Returns:
            Dict with status, hostname, and error information
        """
        return {
            "status": self._status.value,
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "hostname": self._hostname,
            "error": self._error_message,
        }


# Global singleton instance
_tunnel_service: Optional[TunnelService] = None


def get_tunnel_service() -> TunnelService:
    """Get the global TunnelService singleton."""
    global _tunnel_service
    if _tunnel_service is None:
        _tunnel_service = TunnelService()
    return _tunnel_service

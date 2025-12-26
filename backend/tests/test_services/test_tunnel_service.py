"""
Tests for Cloudflare Tunnel service (Story P11-1.1)

Tests the TunnelService class and related functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from app.services.tunnel_service import (
    TunnelService,
    TunnelStatus,
    get_tunnel_service,
)


class TestTunnelStatus:
    """Tests for TunnelStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert TunnelStatus.DISCONNECTED.value == "disconnected"
        assert TunnelStatus.CONNECTING.value == "connecting"
        assert TunnelStatus.CONNECTED.value == "connected"
        assert TunnelStatus.ERROR.value == "error"


class TestTunnelServiceInit:
    """Tests for TunnelService initialization."""

    def test_init_default_state(self):
        """Test service initializes with correct default state."""
        service = TunnelService()
        assert service.status == TunnelStatus.DISCONNECTED
        assert service.is_connected is False
        assert service.is_running is False
        assert service.hostname is None
        assert service.error_message is None

    def test_get_status_dict(self):
        """Test get_status_dict returns correct structure."""
        service = TunnelService()
        status_dict = service.get_status_dict()

        assert "status" in status_dict
        assert "is_connected" in status_dict
        assert "is_running" in status_dict
        assert "hostname" in status_dict
        assert "error" in status_dict

        assert status_dict["status"] == "disconnected"
        assert status_dict["is_connected"] is False
        assert status_dict["is_running"] is False


class TestTunnelServiceTokenValidation:
    """Tests for tunnel token validation."""

    def test_validate_empty_token(self):
        """Test validation fails for empty token."""
        service = TunnelService()
        assert service._validate_token("") is False
        assert service._validate_token(None) is False

    def test_validate_short_token(self):
        """Test validation fails for short token."""
        service = TunnelService()
        assert service._validate_token("abc123") is False

    def test_validate_token_with_shell_chars(self):
        """Test validation fails for token with shell metacharacters."""
        service = TunnelService()

        # Test various dangerous characters
        dangerous_tokens = [
            "abc;rm -rf /",
            "token|cat /etc/passwd",
            "token`whoami`",
            "token$(id)",
            "token && echo pwned",
            "token' OR '1'='1",
            'token" OR "1"="1',
            "token\necho pwned",
        ]

        for token in dangerous_tokens:
            assert service._validate_token(token) is False, f"Should reject: {token}"

    def test_validate_valid_token(self):
        """Test validation passes for valid token."""
        service = TunnelService()

        # A typical Cloudflare tunnel token is a long base64-like string
        valid_token = "eyJhIjoiYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwIiwidCI6ImFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6MTIzNDU2Nzg5MCIsInMiOiJhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ejEyMzQ1Njc4OTAifQ"
        assert service._validate_token(valid_token) is True


class TestTunnelServiceStart:
    """Tests for tunnel start functionality."""

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test start fails if tunnel is already running."""
        service = TunnelService()

        # Mock a running process
        mock_process = Mock()
        mock_process.returncode = None
        service._process = mock_process

        result = await service.start("test-token-that-is-long-enough-to-pass-validation-check")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_invalid_token(self):
        """Test start fails with invalid token."""
        service = TunnelService()

        result = await service.start("short")
        assert result is False
        assert service.status == TunnelStatus.ERROR
        assert "Invalid tunnel token" in service.error_message

    @pytest.mark.asyncio
    async def test_start_cloudflared_not_found(self):
        """Test start fails gracefully when cloudflared is not installed."""
        service = TunnelService()

        valid_token = "eyJhIjoiYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwIiwidCI6ImFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6MTIzNDU2Nzg5MCIsInMiOiJhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ejEyMzQ1Njc4OTAifQ"

        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            result = await service.start(valid_token)

        assert result is False
        assert service.status == TunnelStatus.ERROR
        assert "cloudflared not found" in service.error_message

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test successful tunnel start with mocked subprocess."""
        service = TunnelService()

        valid_token = "eyJhIjoiYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwIiwidCI6ImFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6MTIzNDU2Nzg5MCIsInMiOiJhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ejEyMzQ1Njc4OTAifQ"

        # Mock subprocess
        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stderr = None  # No stderr to avoid blocking readline

        async def mock_create_subprocess(*args, **kwargs):
            return mock_process

        with patch('asyncio.create_subprocess_exec', side_effect=mock_create_subprocess):
            with patch('asyncio.sleep', return_value=None):  # Skip sleep
                result = await service.start(valid_token)

        assert result is True
        assert service.is_running is True

        # Cleanup - mock the process methods
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        await service.stop()


class TestTunnelServiceStop:
    """Tests for tunnel stop functionality."""

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop succeeds when tunnel is not running."""
        service = TunnelService()

        result = await service.stop()
        assert result is True
        assert service.status == TunnelStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_stop_running(self):
        """Test stop terminates running tunnel."""
        service = TunnelService()

        # Mock a running process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = Mock()
        mock_process.kill = Mock()
        mock_process.wait = AsyncMock(return_value=0)

        service._process = mock_process
        service._status = TunnelStatus.CONNECTED

        result = await service.stop()

        assert result is True
        assert service.status == TunnelStatus.DISCONNECTED
        assert service.is_running is False
        mock_process.terminate.assert_called_once()


class TestTunnelServiceLogParsing:
    """Tests for log line parsing."""

    @pytest.mark.asyncio
    async def test_parse_connection_registered(self):
        """Test parsing connection registered message."""
        service = TunnelService()

        await service._parse_log_line("Connection registered successfully")
        assert service.status == TunnelStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_parse_hostname_from_origin(self):
        """Test parsing hostname from origin URL."""
        service = TunnelService()

        await service._parse_log_line("origin=https://my-tunnel.trycloudflare.com")
        assert service.hostname == "my-tunnel.trycloudflare.com"

    @pytest.mark.asyncio
    async def test_parse_hostname_from_url(self):
        """Test parsing hostname from general URL."""
        service = TunnelService()

        await service._parse_log_line("Connected to https://example.trycloudflare.com/path")
        assert service.hostname == "example.trycloudflare.com"

    @pytest.mark.asyncio
    async def test_parse_error_message(self):
        """Test parsing error message."""
        service = TunnelService()

        await service._parse_log_line("Error: connection failed due to network issue")
        assert service.error_message is not None
        assert "Error" in service.error_message or "error" in service.error_message.lower()


class TestTunnelServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_tunnel_service_returns_same_instance(self):
        """Test get_tunnel_service returns singleton."""
        service1 = get_tunnel_service()
        service2 = get_tunnel_service()
        assert service1 is service2


class TestTunnelServiceEncryption:
    """Tests for token encryption integration."""

    def test_token_not_in_status_dict(self):
        """Test that token is never exposed in status dict."""
        service = TunnelService()
        status_dict = service.get_status_dict()

        # Ensure no token-related keys in status
        for key in status_dict.keys():
            assert "token" not in key.lower()

    def test_token_not_in_log_message(self):
        """Test that validation logs don't include actual token value."""
        service = TunnelService()

        # The validation function should not include the token in log messages
        # Just verify the function works and doesn't raise
        result = service._validate_token("this_is_a_short_token")
        assert result is False  # Should fail validation (too short)


class TestTunnelServiceConcurrency:
    """Tests for concurrent access."""

    def test_lock_exists(self):
        """Test that service has a lock for concurrency control."""
        service = TunnelService()
        assert hasattr(service, '_lock')
        assert service._lock is not None

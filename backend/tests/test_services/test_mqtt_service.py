"""
Tests for MQTT Service (Story P4-2.1)

Tests cover:
- MQTTService initialization and configuration
- Connection and disconnection
- Auto-reconnect with exponential backoff
- Message publishing with QoS
- Event payload serialization
- Connection status tracking
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
import asyncio
import json

from app.services.mqtt_service import (
    MQTTService,
    get_mqtt_service,
    serialize_event_for_mqtt,
    RECONNECT_DELAYS,
)
from app.models.mqtt_config import MQTTConfig


class TestMQTTServiceInit:
    """Tests for MQTT service initialization."""

    def test_init_creates_empty_service(self):
        """MQTTService initializes with default values."""
        service = MQTTService()

        assert service._client is None
        assert service._config is None
        assert service._connected is False
        assert service._should_reconnect is True
        assert service._messages_published == 0

    def test_get_mqtt_service_returns_singleton(self):
        """get_mqtt_service returns the same instance."""
        # Clear singleton for test
        import app.services.mqtt_service as mqtt_module
        mqtt_module._mqtt_service = None

        service1 = get_mqtt_service()
        service2 = get_mqtt_service()

        assert service1 is service2

    def test_is_connected_property(self):
        """is_connected returns connection status."""
        service = MQTTService()

        assert service.is_connected is False

        service._connected = True
        assert service.is_connected is True

    def test_messages_published_property(self):
        """messages_published returns count."""
        service = MQTTService()

        assert service.messages_published == 0

        service._messages_published = 42
        assert service.messages_published == 42


class TestMQTTConfig:
    """Tests for MQTT configuration model."""

    def test_config_defaults(self, db_session):
        """MQTTConfig has correct defaults when persisted."""
        config = MQTTConfig(broker_host="test.local")
        db_session.add(config)
        db_session.flush()

        assert config.broker_port == 1883
        assert config.topic_prefix == "liveobject"
        assert config.discovery_prefix == "homeassistant"
        assert config.discovery_enabled is True
        assert config.qos == 1
        assert config.enabled is False
        assert config.retain_messages is True
        assert config.use_tls is False
        assert config.is_connected is False

    def test_config_qos_validation(self):
        """QoS validation rejects invalid values."""
        config = MQTTConfig()

        # Valid QoS values
        config.qos = 0
        assert config.qos == 0
        config.qos = 1
        assert config.qos == 1
        config.qos = 2
        assert config.qos == 2

        # Invalid QoS value
        with pytest.raises(ValueError):
            config.qos = 3

    def test_config_port_validation(self):
        """Port validation rejects invalid values."""
        config = MQTTConfig()

        # Valid port
        config.broker_port = 1883
        assert config.broker_port == 1883

        config.broker_port = 8883
        assert config.broker_port == 8883

        # Invalid ports
        with pytest.raises(ValueError):
            config.broker_port = 0

        with pytest.raises(ValueError):
            config.broker_port = 65536

    def test_config_password_encryption(self, db_session):
        """Password is encrypted when set."""
        from app.models.mqtt_config import MQTTConfig

        config = MQTTConfig(
            broker_host="test.local",
            broker_port=1883,
            password="my_secret_password"
        )

        # Password should be encrypted
        assert config.password is not None
        assert config.password.startswith("encrypted:")
        assert "my_secret_password" not in config.password

    def test_config_password_decryption(self, db_session):
        """Decrypted password matches original."""
        from app.models.mqtt_config import MQTTConfig

        config = MQTTConfig(
            broker_host="test.local",
            broker_port=1883,
            password="my_secret_password"
        )

        # Decrypt and verify
        decrypted = config.get_decrypted_password()
        assert decrypted == "my_secret_password"

    def test_config_to_dict(self):
        """to_dict returns correct representation."""
        config = MQTTConfig(
            broker_host="test.local",
            broker_port=1883,
            username="test_user",
            topic_prefix="liveobject"
        )

        result = config.to_dict()

        assert result["broker_host"] == "test.local"
        assert result["broker_port"] == 1883
        assert result["username"] == "test_user"
        assert "password" not in result  # Password excluded

    def test_config_to_dict_with_password_flag(self):
        """to_dict includes has_password when requested."""
        config = MQTTConfig(
            broker_host="test.local",
            password="secret"
        )

        result = config.to_dict(include_password=True)

        assert result["has_password"] is True


class TestEventSerialization:
    """Tests for event payload serialization."""

    def test_serialize_basic_event(self):
        """Serialize event with basic fields."""
        # Create mock event
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Person detected at front door"
        mock_event.objects_detected = '["person"]'
        mock_event.confidence = 85
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime(2025, 12, 10, 14, 30, 0, tzinfo=timezone.utc)
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = None
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Front Door")

        assert payload["event_id"] == "event-123"
        assert payload["camera_id"] == "camera-456"
        assert payload["camera_name"] == "Front Door"
        assert payload["description"] == "Person detected at front door"
        assert payload["objects_detected"] == ["person"]
        assert payload["confidence"] == 85
        assert payload["source_type"] == "protect"
        assert payload["timestamp"] == "2025-12-10T14:30:00+00:00"
        assert "thumbnail_url" in payload

    def test_serialize_event_with_smart_detection(self):
        """Serialize event with smart detection type."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Package delivered"
        mock_event.objects_detected = '["package"]'
        mock_event.confidence = 90
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime.now(timezone.utc)
        mock_event.ai_confidence = 92
        mock_event.smart_detection_type = "package"
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = "openai"
        mock_event.analysis_mode = "multi_frame"
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Driveway")

        assert payload["ai_confidence"] == 92
        assert payload["smart_detection_type"] == "package"
        assert payload["provider_used"] == "openai"
        assert payload["analysis_mode"] == "multi_frame"

    def test_serialize_doorbell_event(self):
        """Serialize doorbell ring event."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Doorbell ring detected"
        mock_event.objects_detected = '[]'
        mock_event.confidence = 100
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime.now(timezone.utc)
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = "ring"
        mock_event.is_doorbell_ring = True
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Front Door Doorbell")

        assert payload["is_doorbell_ring"] is True
        assert payload["smart_detection_type"] == "ring"

    def test_serialize_low_confidence_event(self):
        """Serialize low confidence event."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Unclear motion detected"
        mock_event.objects_detected = '["unknown"]'
        mock_event.confidence = 40
        mock_event.source_type = "rtsp"
        mock_event.timestamp = datetime.now(timezone.utc)
        mock_event.ai_confidence = 35
        mock_event.smart_detection_type = None
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = "gemini"
        mock_event.analysis_mode = "single_frame"
        mock_event.low_confidence = True
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Back Yard")

        assert payload["low_confidence"] is True
        assert payload["ai_confidence"] == 35

    def test_serialize_correlated_event(self):
        """Serialize event with correlation group."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Person moving through property"
        mock_event.objects_detected = '["person"]'
        mock_event.confidence = 88
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime.now(timezone.utc)
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = "person"
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = "corr-789"

        payload = serialize_event_for_mqtt(mock_event, "Side Gate")

        assert payload["correlation_group_id"] == "corr-789"

    def test_serialize_custom_api_base_url(self):
        """Serialize with custom API base URL."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Test event"
        mock_event.objects_detected = '[]'
        mock_event.confidence = 50
        mock_event.source_type = "usb"
        mock_event.timestamp = datetime.now(timezone.utc)
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = None
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(
            mock_event,
            "Test Camera",
            api_base_url="https://myhost.local:8443"
        )

        assert payload["thumbnail_url"] == "https://myhost.local:8443/api/v1/events/event-123/thumbnail"

    def test_serialize_handles_list_objects_detected(self):
        """Serialize handles list format objects_detected."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Test"
        mock_event.objects_detected = ["person", "vehicle"]  # Already a list
        mock_event.confidence = 75
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime.now(timezone.utc)
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = None
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Camera")

        assert payload["objects_detected"] == ["person", "vehicle"]


class TestMQTTServiceConnection:
    """Tests for MQTT connection management."""

    @pytest.mark.asyncio
    async def test_connect_without_config_raises(self):
        """Connect without config raises ValueError."""
        service = MQTTService()

        with pytest.raises(ValueError, match="configuration not set"):
            await service.connect()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Disconnect when not connected is safe."""
        service = MQTTService()

        # Should not raise
        await service.disconnect()

        assert service._connected is False

    def test_get_status_no_config(self):
        """get_status with no config returns safe defaults."""
        service = MQTTService()

        status = service.get_status()

        assert status["connected"] is False
        assert status["broker"] is None
        assert status["messages_published"] == 0

    def test_get_status_with_config(self):
        """get_status with config returns broker info."""
        service = MQTTService()
        service._config = MQTTConfig(broker_host="test.local", broker_port=1883)
        service._connected = True
        service._messages_published = 100

        status = service.get_status()

        assert status["connected"] is True
        assert status["broker"] == "test.local:1883"
        assert status["messages_published"] == 100


class TestMQTTServicePublish:
    """Tests for MQTT message publishing."""

    @pytest.mark.asyncio
    async def test_publish_when_not_connected(self):
        """Publish when not connected returns False."""
        service = MQTTService()

        result = await service.publish("test/topic", {"message": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_serializes_payload(self):
        """Publish serializes dict payload to JSON."""
        service = MQTTService()
        service._connected = True
        service._config = MQTTConfig(broker_host="test.local", qos=1, retain_messages=True)

        # Mock client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mock_client.publish.return_value = mock_result
        service._client = mock_client

        payload = {"event_id": "123", "description": "Test event"}
        result = await service.publish("test/topic", payload)

        assert result is True
        mock_client.publish.assert_called_once()

        # Verify JSON payload
        call_args = mock_client.publish.call_args
        published_message = call_args[0][1]
        parsed = json.loads(published_message)
        assert parsed["event_id"] == "123"


class TestReconnectLogic:
    """Tests for auto-reconnect behavior."""

    def test_reconnect_delays_exponential(self):
        """Reconnect delays follow exponential pattern."""
        assert RECONNECT_DELAYS[0] == 1
        assert RECONNECT_DELAYS[1] == 2
        assert RECONNECT_DELAYS[2] == 4
        assert RECONNECT_DELAYS[-1] == 60  # Max delay

    def test_reconnect_delays_length(self):
        """Reconnect delays has expected length."""
        assert len(RECONNECT_DELAYS) == 7


class TestEventTopicFormatting:
    """Tests for MQTT event topic formatting (Story P4-2.3, AC1)."""

    def test_get_event_topic_basic(self):
        """get_event_topic returns correct format."""
        service = MQTTService()
        service._config = MQTTConfig(
            broker_host="test.local",
            topic_prefix="liveobject"
        )

        topic = service.get_event_topic("camera-123")
        assert topic == "liveobject/camera/camera-123/event"

    def test_get_event_topic_custom_prefix(self):
        """get_event_topic uses custom topic prefix."""
        service = MQTTService()
        service._config = MQTTConfig(
            broker_host="test.local",
            topic_prefix="myhome"
        )

        topic = service.get_event_topic("front-door-cam")
        assert topic == "myhome/camera/front-door-cam/event"

    def test_get_event_topic_sanitizes_camera_id(self):
        """get_event_topic removes special characters from camera_id."""
        service = MQTTService()
        service._config = MQTTConfig(
            broker_host="test.local",
            topic_prefix="liveobject"
        )

        # Test with special characters that should be removed
        topic = service.get_event_topic("camera/with/slashes")
        assert "/" not in topic.split("/")[-2]  # camera_id part shouldn't have slashes
        assert topic == "liveobject/camera/camerawithslashes/event"

        # Test with UUID-style ID (hyphens allowed)
        topic = service.get_event_topic("abc-123-def")
        assert topic == "liveobject/camera/abc-123-def/event"

    def test_get_event_topic_no_config_uses_default(self):
        """get_event_topic uses default prefix when no config."""
        service = MQTTService()
        service._config = None

        topic = service.get_event_topic("camera-456")
        assert topic == "liveobject/camera/camera-456/event"


class TestApiBaseUrlConfiguration:
    """Tests for API base URL configuration (Story P4-2.3, AC3)."""

    def test_get_api_base_url_default(self, monkeypatch):
        """get_api_base_url returns default when no env var."""
        monkeypatch.delenv("API_BASE_URL", raising=False)

        service = MQTTService()
        url = service.get_api_base_url()

        assert url == "http://localhost:8000"

    def test_get_api_base_url_from_env(self, monkeypatch):
        """get_api_base_url reads from environment variable."""
        monkeypatch.setenv("API_BASE_URL", "https://myhost.local:8443")

        service = MQTTService()
        url = service.get_api_base_url()

        assert url == "https://myhost.local:8443"

    def test_get_api_base_url_strips_trailing_slash(self, monkeypatch):
        """get_api_base_url removes trailing slash."""
        monkeypatch.setenv("API_BASE_URL", "https://myhost.local:8443/")

        service = MQTTService()
        url = service.get_api_base_url()

        assert url == "https://myhost.local:8443"
        assert not url.endswith("/")


class TestEventPublishingIntegration:
    """Tests for event publishing to MQTT (Story P4-2.3)."""

    @pytest.mark.asyncio
    async def test_publish_event_when_not_connected(self):
        """Event publish returns False when not connected (AC6)."""
        service = MQTTService()
        service._connected = False

        result = await service.publish(
            "liveobject/camera/test/event",
            {"event_id": "123", "description": "Test"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_uses_config_qos(self):
        """Event publish uses QoS from config (AC4)."""
        service = MQTTService()
        service._connected = True
        service._config = MQTTConfig(
            broker_host="test.local",
            qos=2,  # QoS 2 from config
            retain_messages=False
        )

        # Mock client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        service._client = mock_client

        await service.publish(
            "liveobject/camera/test/event",
            {"event_id": "123"}
        )

        # Verify QoS 2 was used
        call_args = mock_client.publish.call_args
        assert call_args.kwargs.get("qos") == 2 or call_args[1].get("qos") == 2

    @pytest.mark.asyncio
    async def test_publish_event_respects_retain_setting(self):
        """Event publish uses retain setting from config."""
        service = MQTTService()
        service._connected = True
        service._config = MQTTConfig(
            broker_host="test.local",
            qos=1,
            retain_messages=False  # Don't retain
        )

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rc = 0
        mock_client.publish.return_value = mock_result
        service._client = mock_client

        await service.publish(
            "liveobject/camera/test/event",
            {"event_id": "123"}
        )

        # Verify retain=False was used
        call_args = mock_client.publish.call_args
        assert call_args.kwargs.get("retain") is False or call_args[1].get("retain") is False


class TestSerializationCompleteness:
    """Tests for complete event serialization (Story P4-2.3, AC2, AC7)."""

    def test_serialize_event_has_all_required_fields(self):
        """Serialized event includes all required fields (AC2)."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Person detected"
        mock_event.objects_detected = '["person"]'
        mock_event.confidence = 85
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime(2025, 12, 11, 14, 30, 0, tzinfo=timezone.utc)
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = None
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Front Door")

        # Check all required fields per AC2
        required_fields = [
            "event_id", "camera_id", "camera_name", "description",
            "objects_detected", "confidence", "source_type",
            "timestamp", "thumbnail_url"
        ]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

    def test_serialize_event_includes_all_optional_fields(self):
        """Serialized event includes optional fields when present (AC7)."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Person with package"
        mock_event.objects_detected = '["person", "package"]'
        mock_event.confidence = 90
        mock_event.source_type = "protect"
        mock_event.timestamp = datetime(2025, 12, 11, 14, 30, 0, tzinfo=timezone.utc)
        # All optional fields set
        mock_event.ai_confidence = 92
        mock_event.smart_detection_type = "person"
        mock_event.is_doorbell_ring = True
        mock_event.provider_used = "openai"
        mock_event.analysis_mode = "multi_frame"
        mock_event.low_confidence = False
        mock_event.correlation_group_id = "corr-789"

        payload = serialize_event_for_mqtt(mock_event, "Front Door")

        # Check all optional fields per AC7
        assert payload["smart_detection_type"] == "person"
        assert payload["is_doorbell_ring"] is True
        assert payload["provider_used"] == "openai"
        assert payload["analysis_mode"] == "multi_frame"
        assert payload["ai_confidence"] == 92
        assert payload["correlation_group_id"] == "corr-789"

    def test_serialize_event_omits_none_optional_fields(self):
        """Serialized event omits optional fields when None."""
        mock_event = MagicMock()
        mock_event.id = "event-123"
        mock_event.camera_id = "camera-456"
        mock_event.description = "Motion detected"
        mock_event.objects_detected = '[]'
        mock_event.confidence = 50
        mock_event.source_type = "rtsp"
        mock_event.timestamp = datetime.now(timezone.utc)
        # All optional fields None/False
        mock_event.ai_confidence = None
        mock_event.smart_detection_type = None
        mock_event.is_doorbell_ring = False
        mock_event.provider_used = None
        mock_event.analysis_mode = None
        mock_event.low_confidence = False
        mock_event.correlation_group_id = None

        payload = serialize_event_for_mqtt(mock_event, "Back Yard")

        # Optional fields should not be present when None/False
        assert "smart_detection_type" not in payload
        assert "is_doorbell_ring" not in payload  # False is not included
        assert "provider_used" not in payload
        assert "analysis_mode" not in payload
        assert "ai_confidence" not in payload
        assert "correlation_group_id" not in payload

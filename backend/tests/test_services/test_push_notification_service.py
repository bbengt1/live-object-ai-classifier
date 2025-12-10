"""
Tests for Push Notification Service (Story P4-1.1, P4-1.3)

Tests cover:
- VAPID key generation and management
- PushNotificationService send methods
- Retry logic with exponential backoff
- Invalid subscription cleanup
- Delivery tracking
- Rich notification formatting (P4-1.3)
- Thumbnail embedding (P4-1.3)
- Notification collapse (P4-1.3)
- Action buttons (P4-1.3)
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from app.services.push_notification_service import (
    PushNotificationService,
    NotificationResult,
    send_event_notification,
    format_rich_notification,
    DEFAULT_NOTIFICATION_ACTIONS,
    MAX_RETRIES,
)
from app.models.push_subscription import PushSubscription
from app.utils.vapid import (
    generate_vapid_keys,
    ensure_vapid_keys,
    get_vapid_keys,
    save_vapid_keys,
    VAPID_PRIVATE_KEY_SETTING,
    VAPID_PUBLIC_KEY_SETTING,
)


class TestVapidKeyGeneration:
    """Tests for VAPID key generation."""

    def test_generate_vapid_keys_returns_tuple(self):
        """Generate VAPID keys returns private and public key."""
        private_key, public_key = generate_vapid_keys()

        assert private_key is not None
        assert public_key is not None
        # Accept both EC PRIVATE KEY and PRIVATE KEY formats
        assert "-----BEGIN PRIVATE KEY-----" in private_key or "-----BEGIN EC PRIVATE KEY-----" in private_key
        assert len(public_key) > 0

    def test_generate_vapid_keys_unique_each_call(self):
        """Each call generates unique keys."""
        keys1 = generate_vapid_keys()
        keys2 = generate_vapid_keys()

        assert keys1[0] != keys2[0]  # Private keys different
        assert keys1[1] != keys2[1]  # Public keys different


class TestVapidKeyStorage:
    """Tests for VAPID key storage in database."""

    def test_save_and_get_vapid_keys(self, db_session):
        """Save and retrieve VAPID keys from database."""
        from app.models.system_setting import SystemSetting

        # Generate keys
        private_key, public_key = generate_vapid_keys()

        # Save keys
        save_vapid_keys(db_session, private_key, public_key)

        # Retrieve keys
        retrieved_private, retrieved_public = get_vapid_keys(db_session)

        assert retrieved_private == private_key
        assert retrieved_public == public_key

    def test_get_vapid_keys_when_not_set(self, db_session):
        """Get VAPID keys returns None when not set."""
        private_key, public_key = get_vapid_keys(db_session)

        assert private_key is None
        assert public_key is None

    def test_ensure_vapid_keys_creates_new(self, db_session):
        """ensure_vapid_keys creates new keys if none exist."""
        private_key, public_key = ensure_vapid_keys(db_session)

        assert private_key is not None
        assert public_key is not None

        # Verify stored in database
        stored_private, stored_public = get_vapid_keys(db_session)
        assert stored_private == private_key
        assert stored_public == public_key

    def test_ensure_vapid_keys_returns_existing(self, db_session):
        """ensure_vapid_keys returns existing keys."""
        # Create keys first
        original_private, original_public = ensure_vapid_keys(db_session)

        # Call again - should return same keys
        second_private, second_public = ensure_vapid_keys(db_session)

        assert second_private == original_private
        assert second_public == original_public


class TestPushSubscriptionModel:
    """Tests for PushSubscription database model."""

    def test_create_push_subscription(self, db_session):
        """Create a push subscription."""
        subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/abc123",
            p256dh_key="BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_example",
            auth_key="tBHItJI5svbpez7KI4CCXg==",
            user_agent="Mozilla/5.0 Test Browser"
        )

        db_session.add(subscription)
        db_session.commit()

        assert subscription.id is not None
        assert subscription.created_at is not None

    def test_subscription_get_subscription_info(self, db_session):
        """get_subscription_info returns pywebpush format."""
        subscription = PushSubscription(
            endpoint="https://example.com/push",
            p256dh_key="test_p256dh",
            auth_key="test_auth"
        )

        info = subscription.get_subscription_info()

        assert info["endpoint"] == "https://example.com/push"
        assert info["keys"]["p256dh"] == "test_p256dh"
        assert info["keys"]["auth"] == "test_auth"

    def test_subscription_to_dict_truncates_endpoint(self, db_session):
        """to_dict truncates long endpoints for security."""
        long_endpoint = "https://fcm.googleapis.com/" + "x" * 100

        subscription = PushSubscription(
            endpoint=long_endpoint,
            p256dh_key="test",
            auth_key="test"
        )

        result = subscription.to_dict()

        # Endpoint should be truncated
        assert len(result["endpoint"]) < len(long_endpoint)
        assert "..." in result["endpoint"]


class TestPushNotificationService:
    """Tests for PushNotificationService."""

    @pytest.fixture
    def service(self, db_session):
        """Create PushNotificationService instance."""
        return PushNotificationService(db_session)

    @pytest.fixture
    def sample_subscription(self, db_session):
        """Create a sample push subscription."""
        subscription = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/test123",
            p256dh_key="BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_test",
            auth_key="tBHItJI5svbpez7KI4CCXg=="
        )
        db_session.add(subscription)
        db_session.commit()
        return subscription

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_send_notification_success(self, mock_webpush, service, sample_subscription, db_session):
        """Successful notification delivery."""
        # Ensure VAPID keys exist
        ensure_vapid_keys(db_session)

        mock_webpush.return_value = MagicMock()  # Success

        result = await service.send_notification(
            subscription_id=sample_subscription.id,
            title="Test Title",
            body="Test Body"
        )

        assert result.success is True
        assert result.subscription_id == sample_subscription.id
        assert result.retries == 0
        mock_webpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_subscription_not_found(self, service):
        """Notification fails when subscription not found."""
        result = await service.send_notification(
            subscription_id="non-existent-id",
            title="Test",
            body="Test"
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_send_notification_updates_last_used_at(
        self, mock_webpush, service, sample_subscription, db_session
    ):
        """Successful delivery updates last_used_at timestamp."""
        ensure_vapid_keys(db_session)
        mock_webpush.return_value = MagicMock()

        assert sample_subscription.last_used_at is None

        await service.send_notification(
            subscription_id=sample_subscription.id,
            title="Test",
            body="Test"
        )

        db_session.refresh(sample_subscription)
        assert sample_subscription.last_used_at is not None

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_send_notification_removes_expired_subscription(
        self, mock_webpush, service, sample_subscription, db_session
    ):
        """410 response removes subscription from database."""
        from pywebpush import WebPushException

        ensure_vapid_keys(db_session)

        # Mock 410 Gone response
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_webpush.side_effect = WebPushException(
            "Gone",
            response=mock_response
        )

        subscription_id = sample_subscription.id

        result = await service.send_notification(
            subscription_id=subscription_id,
            title="Test",
            body="Test"
        )

        assert result.success is False
        assert result.status_code == 410

        # Verify subscription was deleted
        deleted = db_session.query(PushSubscription).filter(
            PushSubscription.id == subscription_id
        ).first()
        assert deleted is None

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    @patch('app.services.push_notification_service.asyncio.sleep', new_callable=AsyncMock)
    async def test_send_notification_retries_on_failure(
        self, mock_sleep, mock_webpush, service, sample_subscription, db_session
    ):
        """Notification retries on transient failures."""
        from pywebpush import WebPushException

        ensure_vapid_keys(db_session)

        # Mock 500 error first two times, then succeed
        mock_response = MagicMock()
        mock_response.status_code = 500

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WebPushException("Server Error", response=mock_response)
            return MagicMock()  # Success on 3rd try

        mock_webpush.side_effect = side_effect

        result = await service.send_notification(
            subscription_id=sample_subscription.id,
            title="Test",
            body="Test"
        )

        assert result.success is True
        assert result.retries == 2  # Succeeded on 3rd attempt
        assert mock_sleep.call_count == 2  # Waited twice

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_broadcast_notification_to_multiple(self, mock_webpush, service, db_session):
        """Broadcast sends to all subscriptions."""
        ensure_vapid_keys(db_session)
        mock_webpush.return_value = MagicMock()

        # Create multiple subscriptions
        for i in range(3):
            sub = PushSubscription(
                endpoint=f"https://example.com/push/{i}",
                p256dh_key=f"key_{i}",
                auth_key=f"auth_{i}"
            )
            db_session.add(sub)
        db_session.commit()

        results = await service.broadcast_notification(
            title="Broadcast Test",
            body="Test Body"
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_webpush.call_count == 3

    @pytest.mark.asyncio
    async def test_broadcast_notification_empty_subscriptions(self, service):
        """Broadcast with no subscriptions returns empty list."""
        results = await service.broadcast_notification(
            title="Test",
            body="Test"
        )

        assert results == []


class TestSendEventNotification:
    """Tests for send_event_notification convenience function."""

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_formats_correctly(self, MockService, db_session):
        """send_event_notification formats notification correctly."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[
            NotificationResult(subscription_id="test", success=True)
        ])
        MockService.return_value = mock_instance

        results = await send_event_notification(
            event_id="event-123",
            camera_name="Front Door",
            description="Person with package at front door",
            thumbnail_url="/api/v1/thumbnails/2025-12-10/event-123.jpg",
            db=db_session
        )

        assert len(results) == 1
        mock_instance.broadcast_notification.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs
        assert "Front Door" in call_kwargs["title"]
        assert call_kwargs["data"]["event_id"] == "event-123"
        assert call_kwargs["tag"] == "event-123"

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_truncates_long_description(self, MockService, db_session):
        """Long descriptions are truncated."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        long_description = "A" * 200  # 200 chars

        await send_event_notification(
            event_id="event-123",
            camera_name="Test",
            description=long_description,
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs
        assert len(call_kwargs["body"]) <= 100
        assert call_kwargs["body"].endswith("...")


class TestNotificationPayload:
    """Tests for notification payload structure."""

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_notification_payload_structure(self, mock_webpush, db_session):
        """Verify notification payload has correct structure."""
        import json

        ensure_vapid_keys(db_session)

        # Capture the payload sent to webpush
        captured_payload = None
        def capture_webpush(**kwargs):
            nonlocal captured_payload
            captured_payload = json.loads(kwargs['data'])
            return MagicMock()

        mock_webpush.side_effect = capture_webpush

        subscription = PushSubscription(
            endpoint="https://test.com/push",
            p256dh_key="test",
            auth_key="test"
        )
        db_session.add(subscription)
        db_session.commit()

        service = PushNotificationService(db_session)
        await service.send_notification(
            subscription_id=subscription.id,
            title="Test Title",
            body="Test Body",
            data={"event_id": "123", "url": "/events"},
            icon="/icons/test.png",
            badge="/icons/badge.png",
            tag="test-tag"
        )

        assert captured_payload is not None
        assert captured_payload["title"] == "Test Title"
        assert captured_payload["body"] == "Test Body"
        assert captured_payload["icon"] == "/icons/test.png"
        assert captured_payload["badge"] == "/icons/badge.png"
        assert captured_payload["tag"] == "test-tag"
        assert captured_payload["data"]["event_id"] == "123"
        assert captured_payload["data"]["url"] == "/events"


# ============================================================================
# Story P4-1.3: Rich Notification Formatting Tests
# ============================================================================

class TestFormatRichNotification:
    """Tests for format_rich_notification helper function (Story P4-1.3)."""

    def test_format_rich_notification_basic(self):
        """Basic notification formatting without thumbnail."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Front Door",
            description="Person detected at front door",
        )

        assert result["title"] == "Front Door: Motion Detected"
        assert result["body"] == "Person detected at front door"
        assert result["tag"] == "camera-456"  # Camera ID for collapse
        assert result["renotify"] is True
        assert result["actions"] == DEFAULT_NOTIFICATION_ACTIONS
        assert result["data"]["event_id"] == "event-123"
        assert result["data"]["camera_id"] == "camera-456"
        assert result["data"]["url"] == "/events?highlight=event-123"
        assert "image" not in result  # No thumbnail

    def test_format_rich_notification_with_thumbnail(self):
        """Notification includes thumbnail URL when provided (AC1)."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Front Door",
            description="Delivery driver",
            thumbnail_url="/api/v1/thumbnails/2025-12-10/event-123.jpg",
        )

        assert result["image"] == "/api/v1/thumbnails/2025-12-10/event-123.jpg"

    def test_format_rich_notification_without_thumbnail_graceful(self):
        """Notification works gracefully without thumbnail (AC8)."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Test Camera",
            description="Motion detected",
            thumbnail_url=None,
        )

        # Should not raise, should not include image field
        assert "image" not in result
        assert result["title"] is not None
        assert result["body"] is not None

    def test_format_rich_notification_person_detection(self):
        """Title reflects person detection type."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Front Porch",
            description="Person with package",
            smart_detection_type="person",
        )

        assert result["title"] == "Front Porch: Person Detected"
        assert result["data"]["smart_detection_type"] == "person"

    def test_format_rich_notification_vehicle_detection(self):
        """Title reflects vehicle detection type."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Driveway",
            description="Car arriving",
            smart_detection_type="vehicle",
        )

        assert result["title"] == "Driveway: Vehicle Detected"

    def test_format_rich_notification_package_detection(self):
        """Title reflects package detection type."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Front Door",
            description="Package delivered",
            smart_detection_type="package",
        )

        assert result["title"] == "Front Door: Package Detected"

    def test_format_rich_notification_doorbell_ring(self):
        """Title reflects doorbell ring event."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Doorbell",
            description="Someone at the door",
            smart_detection_type="ring",
        )

        assert result["title"] == "Doorbell: Doorbell Ring"

    def test_format_rich_notification_truncates_long_description(self):
        """Long descriptions are truncated at 100 chars."""
        long_description = "A" * 200

        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Test",
            description=long_description,
        )

        assert len(result["body"]) == 100
        assert result["body"].endswith("...")

    def test_format_rich_notification_collapse_tag_is_camera_id(self):
        """Tag uses camera_id for notification collapse (AC4)."""
        result = format_rich_notification(
            event_id="event-789",
            camera_id="camera-unique-id",
            camera_name="Test Camera",
            description="Motion detected",
        )

        assert result["tag"] == "camera-unique-id"

    def test_format_rich_notification_includes_actions(self):
        """Notification includes action buttons (AC2, AC3)."""
        result = format_rich_notification(
            event_id="event-123",
            camera_id="camera-456",
            camera_name="Test",
            description="Test event",
        )

        assert "actions" in result
        assert len(result["actions"]) == 2

        # Verify View action
        view_action = next(a for a in result["actions"] if a["action"] == "view")
        assert view_action["title"] == "View"

        # Verify Dismiss action
        dismiss_action = next(a for a in result["actions"] if a["action"] == "dismiss")
        assert dismiss_action["title"] == "Dismiss"

    def test_format_rich_notification_deep_link_url(self):
        """Data includes deep link URL (AC5)."""
        result = format_rich_notification(
            event_id="event-abc-123",
            camera_id="camera-456",
            camera_name="Test",
            description="Test",
        )

        assert result["data"]["url"] == "/events?highlight=event-abc-123"


class TestRichNotificationPayload:
    """Tests for rich notification payload structure sent via Web Push (Story P4-1.3)."""

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_notification_includes_image_field(self, mock_webpush, db_session):
        """Verify image field is included in payload when provided."""
        import json

        ensure_vapid_keys(db_session)

        captured_payload = None
        def capture_webpush(**kwargs):
            nonlocal captured_payload
            captured_payload = json.loads(kwargs['data'])
            return MagicMock()

        mock_webpush.side_effect = capture_webpush

        subscription = PushSubscription(
            endpoint="https://test.com/push",
            p256dh_key="test",
            auth_key="test"
        )
        db_session.add(subscription)
        db_session.commit()

        service = PushNotificationService(db_session)
        await service.send_notification(
            subscription_id=subscription.id,
            title="Test",
            body="Test",
            image="/thumbnails/test.jpg",
        )

        assert captured_payload is not None
        assert captured_payload["image"] == "/thumbnails/test.jpg"

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_notification_includes_actions_field(self, mock_webpush, db_session):
        """Verify actions array is included in payload."""
        import json

        ensure_vapid_keys(db_session)

        captured_payload = None
        def capture_webpush(**kwargs):
            nonlocal captured_payload
            captured_payload = json.loads(kwargs['data'])
            return MagicMock()

        mock_webpush.side_effect = capture_webpush

        subscription = PushSubscription(
            endpoint="https://test.com/push",
            p256dh_key="test",
            auth_key="test"
        )
        db_session.add(subscription)
        db_session.commit()

        actions = [
            {"action": "view", "title": "View Event"},
            {"action": "dismiss", "title": "Dismiss"},
        ]

        service = PushNotificationService(db_session)
        await service.send_notification(
            subscription_id=subscription.id,
            title="Test",
            body="Test",
            actions=actions,
        )

        assert captured_payload is not None
        assert captured_payload["actions"] == actions

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.webpush')
    async def test_notification_includes_renotify_field(self, mock_webpush, db_session):
        """Verify renotify field is included in payload."""
        import json

        ensure_vapid_keys(db_session)

        captured_payload = None
        def capture_webpush(**kwargs):
            nonlocal captured_payload
            captured_payload = json.loads(kwargs['data'])
            return MagicMock()

        mock_webpush.side_effect = capture_webpush

        subscription = PushSubscription(
            endpoint="https://test.com/push",
            p256dh_key="test",
            auth_key="test"
        )
        db_session.add(subscription)
        db_session.commit()

        service = PushNotificationService(db_session)
        await service.send_notification(
            subscription_id=subscription.id,
            title="Test",
            body="Test",
            tag="camera-123",
            renotify=True,
        )

        assert captured_payload is not None
        assert captured_payload["renotify"] is True


class TestSendEventNotificationRich:
    """Tests for send_event_notification with rich payload (Story P4-1.3)."""

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_with_camera_id(self, MockService, db_session):
        """send_event_notification uses camera_id for collapse tag (AC4)."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        await send_event_notification(
            event_id="event-123",
            camera_name="Front Door",
            description="Person detected",
            thumbnail_url="/thumbnails/test.jpg",
            camera_id="camera-456",
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs

        # Tag should be camera_id for collapse
        assert call_kwargs["tag"] == "camera-456"

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_with_smart_detection_type(self, MockService, db_session):
        """send_event_notification includes smart detection in title."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        await send_event_notification(
            event_id="event-123",
            camera_name="Front Door",
            description="Delivery person",
            smart_detection_type="person",
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs

        # Title should reflect detection type
        assert "Person Detected" in call_kwargs["title"]

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_includes_actions(self, MockService, db_session):
        """send_event_notification includes action buttons."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        await send_event_notification(
            event_id="event-123",
            camera_name="Test",
            description="Test",
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs

        assert call_kwargs["actions"] == DEFAULT_NOTIFICATION_ACTIONS

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_includes_image(self, MockService, db_session):
        """send_event_notification includes thumbnail as image (AC1)."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        await send_event_notification(
            event_id="event-123",
            camera_name="Test",
            description="Test",
            thumbnail_url="/thumbnails/event-123.jpg",
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs

        assert call_kwargs["image"] == "/thumbnails/event-123.jpg"

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_renotify_enabled(self, MockService, db_session):
        """send_event_notification has renotify=True for updates."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        await send_event_notification(
            event_id="event-123",
            camera_name="Test",
            description="Test",
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs

        assert call_kwargs["renotify"] is True

    @pytest.mark.asyncio
    @patch('app.services.push_notification_service.PushNotificationService')
    async def test_send_event_notification_deep_link_in_data(self, MockService, db_session):
        """send_event_notification includes deep link URL (AC5)."""
        mock_instance = MagicMock()
        mock_instance.broadcast_notification = AsyncMock(return_value=[])
        MockService.return_value = mock_instance

        await send_event_notification(
            event_id="event-abc-123",
            camera_name="Test",
            description="Test",
            db=db_session
        )

        call_kwargs = mock_instance.broadcast_notification.call_args.kwargs

        assert call_kwargs["data"]["url"] == "/events?highlight=event-abc-123"

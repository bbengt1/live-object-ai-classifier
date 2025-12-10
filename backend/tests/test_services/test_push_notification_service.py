"""
Tests for Push Notification Service (Story P4-1.1)

Tests cover:
- VAPID key generation and management
- PushNotificationService send methods
- Retry logic with exponential backoff
- Invalid subscription cleanup
- Delivery tracking
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from app.services.push_notification_service import (
    PushNotificationService,
    NotificationResult,
    send_event_notification,
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

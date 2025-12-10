"""
API Tests for Push Notification endpoints (Stories P4-1.1 & P4-1.2)

Tests cover:
- GET /api/v1/push/vapid-public-key
- POST /api/v1/push/subscribe
- DELETE /api/v1/push/subscribe
- GET /api/v1/push/subscriptions
- POST /api/v1/push/test
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import models and setup after database is configured
from main import app
from app.core.database import Base, get_db
from app.models.push_subscription import PushSubscription


# Create test database (file-based to avoid threading issues)
test_db_fd, test_db_path = tempfile.mkstemp(suffix=".db")
os.close(test_db_fd)

TEST_DATABASE_URL = f"sqlite:///{test_db_path}"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Override database dependency
app.dependency_overrides[get_db] = override_get_db

# Create tables once
Base.metadata.create_all(bind=engine)

# Create test client
client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def cleanup_push_subscriptions(db_session):
    """Clean up push subscriptions before each test."""
    db_session.query(PushSubscription).delete()
    db_session.commit()
    yield


class TestVapidPublicKeyEndpoint:
    """Tests for GET /api/v1/push/vapid-public-key."""

    def test_get_vapid_public_key_success(self):
        """Successfully get VAPID public key."""
        response = client.get("/api/v1/push/vapid-public-key")

        assert response.status_code == 200
        data = response.json()
        assert "public_key" in data
        assert len(data["public_key"]) > 0

    def test_get_vapid_public_key_consistent(self):
        """Same key returned on multiple requests."""
        response1 = client.get("/api/v1/push/vapid-public-key")
        response2 = client.get("/api/v1/push/vapid-public-key")

        assert response1.json()["public_key"] == response2.json()["public_key"]


class TestSubscribeEndpoint:
    """Tests for POST /api/v1/push/subscribe."""

    @pytest.fixture
    def valid_subscription_data(self):
        """Valid subscription request data."""
        return {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test_subscription_123",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_test_key",
                "auth": "tBHItJI5svbpez7KI4CCXg=="
            },
            "user_agent": "Mozilla/5.0 Test Browser"
        }

    def test_subscribe_creates_subscription(self, db_session, valid_subscription_data):
        """POST creates new subscription."""
        response = client.post("/api/v1/push/subscribe", json=valid_subscription_data)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "endpoint" in data
        assert "created_at" in data

        # Verify in database - use fresh session to see committed data
        with TestingSessionLocal() as check_db:
            subscription = check_db.query(PushSubscription).filter(
                PushSubscription.id == data["id"]
            ).first()
            assert subscription is not None
            assert subscription.p256dh_key == valid_subscription_data["keys"]["p256dh"]
            assert subscription.auth_key == valid_subscription_data["keys"]["auth"]

    def test_subscribe_updates_existing(self, valid_subscription_data):
        """POST updates existing subscription with same endpoint."""
        # Create initial subscription
        response1 = client.post("/api/v1/push/subscribe", json=valid_subscription_data)
        assert response1.status_code == 201
        original_id = response1.json()["id"]

        # Update with same endpoint, different keys
        updated_data = valid_subscription_data.copy()
        updated_data["keys"] = {
            "p256dh": "updated_p256dh_key",
            "auth": "updated_auth_key"
        }
        response2 = client.post("/api/v1/push/subscribe", json=updated_data)

        # Should succeed (upsert)
        assert response2.status_code == 201
        assert response2.json()["id"] == original_id

        # Verify keys updated
        with TestingSessionLocal() as check_db:
            subscription = check_db.query(PushSubscription).filter(
                PushSubscription.id == original_id
            ).first()
            assert subscription.p256dh_key == "updated_p256dh_key"

    def test_subscribe_invalid_endpoint_format(self):
        """POST rejects invalid endpoint URL."""
        invalid_data = {
            "endpoint": "not-a-valid-url",
            "keys": {
                "p256dh": "test",
                "auth": "test"
            }
        }

        response = client.post("/api/v1/push/subscribe", json=invalid_data)

        assert response.status_code == 400
        assert "endpoint" in response.json()["detail"].lower()

    def test_subscribe_missing_keys(self):
        """POST rejects missing keys."""
        invalid_data = {
            "endpoint": "https://example.com/push"
            # Missing keys
        }

        response = client.post("/api/v1/push/subscribe", json=invalid_data)

        assert response.status_code == 422  # Validation error

    def test_subscribe_truncates_endpoint_in_response(self):
        """Response truncates long endpoint."""
        long_endpoint = "https://fcm.googleapis.com/" + "x" * 100
        data = {
            "endpoint": long_endpoint,
            "keys": {
                "p256dh": "test",
                "auth": "test"
            }
        }

        response = client.post("/api/v1/push/subscribe", json=data)

        assert response.status_code == 201
        # Response endpoint should be truncated
        assert len(response.json()["endpoint"]) < len(long_endpoint)


class TestUnsubscribeEndpoint:
    """Tests for DELETE /api/v1/push/subscribe."""

    def test_unsubscribe_removes_subscription(self, db_session):
        """DELETE removes subscription by endpoint."""
        # Create subscription first
        subscription = PushSubscription(
            endpoint="https://example.com/push/to_delete",
            p256dh_key="test",
            auth_key="test"
        )
        db_session.add(subscription)
        db_session.commit()

        response = client.request(
            "DELETE",
            "/api/v1/push/subscribe",
            json={"endpoint": "https://example.com/push/to_delete"}
        )

        assert response.status_code == 204

        # Verify deleted
        with TestingSessionLocal() as check_db:
            deleted = check_db.query(PushSubscription).filter(
                PushSubscription.endpoint == "https://example.com/push/to_delete"
            ).first()
            assert deleted is None

    def test_unsubscribe_not_found(self):
        """DELETE returns 404 for non-existent subscription."""
        response = client.request(
            "DELETE",
            "/api/v1/push/subscribe",
            json={"endpoint": "https://example.com/non_existent"}
        )

        assert response.status_code == 404


class TestListSubscriptionsEndpoint:
    """Tests for GET /api/v1/push/subscriptions."""

    def test_list_subscriptions_empty(self):
        """GET returns empty list when no subscriptions."""
        response = client.get("/api/v1/push/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert data["subscriptions"] == []
        assert data["total"] == 0

    def test_list_subscriptions_returns_all(self, db_session):
        """GET returns all subscriptions."""
        # Create multiple subscriptions
        for i in range(3):
            sub = PushSubscription(
                endpoint=f"https://example.com/push/{i}",
                p256dh_key=f"key_{i}",
                auth_key=f"auth_{i}"
            )
            db_session.add(sub)
        db_session.commit()

        response = client.get("/api/v1/push/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["subscriptions"]) == 3

    def test_list_subscriptions_truncates_endpoints(self, db_session):
        """GET truncates endpoints in response."""
        long_endpoint = "https://fcm.googleapis.com/" + "x" * 100
        sub = PushSubscription(
            endpoint=long_endpoint,
            p256dh_key="test",
            auth_key="test"
        )
        db_session.add(sub)
        db_session.commit()

        response = client.get("/api/v1/push/subscriptions")

        assert response.status_code == 200
        endpoint_in_response = response.json()["subscriptions"][0]["endpoint"]
        assert len(endpoint_in_response) < len(long_endpoint)


class TestTestNotificationEndpoint:
    """Tests for POST /api/v1/push/test (Story P4-1.2)."""

    def test_send_test_no_subscriptions(self):
        """POST returns message when no subscriptions exist."""
        response = client.post("/api/v1/push/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "No push subscriptions" in data["message"]
        assert data["results"] == []

    def test_send_test_with_subscriptions(self, db_session):
        """POST sends to all subscriptions and returns results."""
        # Create test subscriptions
        for i in range(2):
            sub = PushSubscription(
                endpoint=f"https://fcm.googleapis.com/fcm/send/test_{i}",
                p256dh_key=f"test_p256dh_{i}",
                auth_key=f"test_auth_{i}"
            )
            db_session.add(sub)
        db_session.commit()

        # Mock the PushNotificationService to avoid actual push sending
        with patch('app.api.v1.push.PushNotificationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            # Create mock notification results
            from app.services.push_notification_service import NotificationResult
            mock_results = [
                NotificationResult(subscription_id="sub1", success=True),
                NotificationResult(subscription_id="sub2", success=True),
            ]
            # Use AsyncMock for async method
            mock_service.broadcast_notification = AsyncMock(return_value=mock_results)

            response = client.post("/api/v1/push/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "2/2" in data["message"]
        assert len(data["results"]) == 2

    def test_send_test_partial_success(self, db_session):
        """POST reports partial success when some notifications fail."""
        # Create test subscription
        sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/test",
            p256dh_key="test_p256dh",
            auth_key="test_auth"
        )
        db_session.add(sub)
        db_session.commit()

        # Mock the service with partial failure
        with patch('app.api.v1.push.PushNotificationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            from app.services.push_notification_service import NotificationResult
            mock_results = [
                NotificationResult(subscription_id="sub1", success=True),
                NotificationResult(subscription_id="sub2", success=False, error="expired"),
            ]
            # Use AsyncMock for async method
            mock_service.broadcast_notification = AsyncMock(return_value=mock_results)

            response = client.post("/api/v1/push/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True  # At least one succeeded
        assert "1/2" in data["message"]
        # Check error is included for failed subscription
        failed = [r for r in data["results"] if not r["success"]]
        assert len(failed) == 1
        assert failed[0]["error"] == "expired"

    def test_send_test_response_structure(self, db_session):
        """POST returns correct response structure."""
        # Create test subscription
        sub = PushSubscription(
            endpoint="https://fcm.googleapis.com/fcm/send/test",
            p256dh_key="test_p256dh",
            auth_key="test_auth"
        )
        db_session.add(sub)
        db_session.commit()

        with patch('app.api.v1.push.PushNotificationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            from app.services.push_notification_service import NotificationResult
            mock_results = [
                NotificationResult(subscription_id="test-uuid", success=True),
            ]
            # Use AsyncMock for async method
            mock_service.broadcast_notification = AsyncMock(return_value=mock_results)

            response = client.post("/api/v1/push/test")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "message" in data
        assert "results" in data
        assert isinstance(data["results"], list)

        if data["results"]:
            result = data["results"][0]
            assert "subscription_id" in result
            assert "success" in result

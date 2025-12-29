# Epic Technical Specification: P14-3 Backend Testing Infrastructure

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-3
Status: Draft
Priority: P2-P3

---

## Overview

Epic P14-3 addresses gaps in backend test coverage, focusing on six services with 0% unit test coverage and improvements to testing infrastructure. The codebase currently has 3,400+ tests across 130 test files, but critical services like `protect_service.py` and `protect_event_handler.py` lack dedicated unit tests.

## Current State Analysis

### Test Coverage Summary

| Category | Files | Tests |
|----------|-------|-------|
| Service tests | 67 | ~2,100 |
| API tests | 41 | ~800 |
| Integration tests | 18 | ~350 |
| Model tests | 5 | ~75 |
| Other | 9 | ~100 |
| **Total** | **130** | **~3,425** |

### Services Without Unit Tests

| Service | Lines | Complexity | Priority |
|---------|-------|------------|----------|
| `protect_service.py` | ~900 | High | P1 |
| `protect_event_handler.py` | ~3100 | Very High | P1 |
| `snapshot_service.py` | ~200 | Medium | P2 |
| `reprocessing_service.py` | ~400 | Medium | P2 |
| `websocket_manager.py` | ~150 | Medium | P2 |
| `api_key_service.py` | ~200 | Low | P3 |

### Current Test Infrastructure

**Fixtures:**
```python
# conftest.py - Session-scoped
@pytest.fixture(scope="session", autouse=True)
def clear_app_overrides(): ...

# conftest.py - Function-scoped
@pytest.fixture(scope="function")
def db_session(): ...  # In-memory SQLite

@pytest.fixture(scope="function")
def temp_db_file(): ...
```

**Issues:**
- Some fixtures defined per-test file rather than in conftest.py
- Inconsistent use of parametrization
- Duplicate fixture definitions across test files

## Objectives and Scope

### In Scope

- Add unit tests for 6 services with 0% coverage
- Achieve 80%+ line coverage for each new test file
- Increase use of `@pytest.mark.parametrize`
- Consolidate fixture definitions to conftest.py
- Add missing API route tests
- Add E2E integration tests for critical paths

### Out of Scope

- Frontend test coverage (covered in P14-4)
- Load/stress testing
- Security penetration testing
- Code coverage CI enforcement

## Detailed Design

### Story P14-3.1: Add Unit Tests for ProtectService

**Target File:** `backend/app/services/protect_service.py` (~900 lines)

**Key Methods to Test:**

| Method | Purpose | Test Cases |
|--------|---------|------------|
| `connect()` | Connect to Protect controller | Success, invalid credentials, timeout, SSL error |
| `disconnect()` | Gracefully disconnect | Already disconnected, error during disconnect |
| `get_cameras()` | Fetch camera list | Success, empty list, connection error |
| `subscribe_events()` | Set up WebSocket subscription | Success, reconnection |
| `_handle_event()` | Process incoming event | Each event type, malformed data |
| `get_snapshot()` | Fetch camera snapshot | Success, camera offline, timeout |

**Test File Structure:**
```python
# backend/tests/test_services/test_protect_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.protect_service import ProtectService

@pytest.fixture
def mock_uiprotect():
    """Mock uiprotect library."""
    with patch('app.services.protect_service.ProtectApiClient') as mock:
        yield mock

@pytest.fixture
def protect_service(mock_uiprotect, db_session):
    """Create ProtectService instance with mocked dependencies."""
    return ProtectService(db=db_session)

class TestProtectServiceConnection:
    """Tests for connection management."""

    async def test_connect_success(self, protect_service, mock_uiprotect):
        """Test successful connection to Protect controller."""
        mock_uiprotect.return_value.connect = AsyncMock()
        mock_uiprotect.return_value.api.bootstrap = MagicMock(cameras=[])

        result = await protect_service.connect(
            host="192.168.1.1",
            username="admin",
            password="password"
        )

        assert result.success is True
        mock_uiprotect.return_value.connect.assert_called_once()

    async def test_connect_invalid_credentials(self, protect_service, mock_uiprotect):
        """Test connection with invalid credentials."""
        mock_uiprotect.return_value.connect = AsyncMock(
            side_effect=AuthenticationError("Invalid credentials")
        )

        result = await protect_service.connect(...)

        assert result.success is False
        assert "credentials" in result.error.lower()

    @pytest.mark.parametrize("error,expected_msg", [
        (ConnectionTimeout("timeout"), "timeout"),
        (SSLError("certificate"), "ssl"),
        (ConnectionRefused("refused"), "connection"),
    ])
    async def test_connect_network_errors(
        self, protect_service, mock_uiprotect, error, expected_msg
    ):
        """Test various network error scenarios."""
        mock_uiprotect.return_value.connect = AsyncMock(side_effect=error)

        result = await protect_service.connect(...)

        assert result.success is False
        assert expected_msg in result.error.lower()

class TestProtectServiceCameras:
    """Tests for camera operations."""
    # ... similar pattern

class TestProtectServiceEvents:
    """Tests for event handling."""
    # ... similar pattern
```

### Story P14-3.2: Add Unit Tests for ProtectEventHandler

**Target File:** `backend/app/services/protect_event_handler.py` (~3100 lines)

**Key Methods to Test:**

| Method | Purpose | Test Cases |
|--------|---------|------------|
| `handle_event()` | Main event entry point | Each event type, filtering, deduplication |
| `_filter_event()` | Apply event type filters | Camera-specific filters, global filters |
| `_deduplicate_event()` | Prevent duplicate processing | Time window, same camera, different camera |
| `_enrich_event()` | Add metadata to event | Camera info, timestamp normalization |
| `_queue_for_processing()` | Add to processing queue | Success, queue full |
| `_handle_smart_detection()` | Process smart events | person, vehicle, package, animal |
| `_handle_doorbell_ring()` | Process doorbell events | Ring, press, hold |

**Test File Structure:**
```python
# backend/tests/test_services/test_protect_event_handler.py

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from app.services.protect_event_handler import ProtectEventHandler

@pytest.fixture
def sample_protect_events():
    """Factory for creating sample Protect events."""
    def _create_event(
        event_type="motion",
        camera_id="cam1",
        timestamp=None,
        smart_types=None
    ):
        return {
            "id": f"event_{event_type}_{camera_id}",
            "type": event_type,
            "camera": {"id": camera_id, "name": "Front Door"},
            "start": timestamp or datetime.now(timezone.utc).isoformat(),
            "smartDetectTypes": smart_types or [],
        }
    return _create_event

class TestEventFiltering:
    """Tests for event filtering logic."""

    @pytest.mark.parametrize("event_type,enabled,expected", [
        ("motion", True, True),
        ("motion", False, False),
        ("smartDetect", True, True),
        ("ring", True, True),
        ("ring", False, False),
    ])
    def test_filter_by_event_type(
        self, handler, sample_protect_events, event_type, enabled, expected
    ):
        """Test filtering events by type setting."""
        event = sample_protect_events(event_type=event_type)
        handler.camera_settings = {event["camera"]["id"]: {"motion_enabled": enabled}}

        result = handler._filter_event(event)

        assert result == expected

class TestDeduplication:
    """Tests for event deduplication."""

    def test_deduplicate_same_event_within_window(
        self, handler, sample_protect_events
    ):
        """Test that same event within time window is deduplicated."""
        event = sample_protect_events()

        # First call should process
        assert handler._should_process(event) is True

        # Second call within window should skip
        assert handler._should_process(event) is False

class TestSmartDetection:
    """Tests for smart detection event handling."""

    @pytest.mark.parametrize("smart_type", [
        "person", "vehicle", "package", "animal"
    ])
    async def test_handle_each_smart_type(
        self, handler, sample_protect_events, smart_type
    ):
        """Test handling of each smart detection type."""
        event = sample_protect_events(
            event_type="smartDetect",
            smart_types=[smart_type]
        )

        result = await handler.handle_event(event)

        assert result.smart_detection_type == smart_type
```

### Story P14-3.3: Add Unit Tests for SnapshotService

**Target File:** `backend/app/services/snapshot_service.py` (~200 lines)

**Key Methods:**
- `get_snapshot()` - Fetch snapshot from Protect
- `_resize_snapshot()` - Resize for thumbnails
- `_cache_snapshot()` - Cache management

```python
# backend/tests/test_services/test_snapshot_service.py

class TestSnapshotService:
    @pytest.mark.parametrize("camera_status", ["online", "offline", "disconnected"])
    async def test_get_snapshot_camera_states(self, snapshot_service, camera_status):
        """Test snapshot retrieval for different camera states."""
        # ...

    async def test_snapshot_resize_quality(self, snapshot_service):
        """Test thumbnail generation maintains quality."""
        # ...

    async def test_snapshot_caching(self, snapshot_service):
        """Test snapshot cache hit/miss behavior."""
        # ...
```

### Story P14-3.4: Add Unit Tests for ReprocessingService

**Target File:** `backend/app/services/reprocessing_service.py` (~400 lines)

**Key Methods:**
- `start_reprocessing()` - Begin batch reprocess
- `process_batch()` - Process event batch
- `_update_progress()` - WebSocket progress updates
- `cancel_reprocessing()` - Stop in-progress job

```python
# backend/tests/test_services/test_reprocessing_service.py

class TestReprocessingService:
    async def test_start_reprocessing_validates_date_range(self, service):
        """Test date range validation."""
        # ...

    async def test_process_batch_respects_batch_size(self, service):
        """Test batch processing respects configured size."""
        # ...

    async def test_progress_updates_sent_to_websocket(self, service, mock_ws):
        """Test WebSocket progress updates."""
        # ...

    async def test_cancel_stops_processing(self, service):
        """Test cancellation stops active job."""
        # ...
```

### Story P14-3.5: Add Unit Tests for WebSocketManager

**Target File:** `backend/app/services/websocket_manager.py` (~150 lines)

**Key Methods:**
- `connect()` - Add WebSocket connection
- `disconnect()` - Remove connection
- `broadcast()` - Send to all connections
- `send_to_user()` - Send to specific user

```python
# backend/tests/test_services/test_websocket_manager.py

class TestWebSocketManager:
    async def test_connect_adds_to_pool(self, manager, mock_websocket):
        """Test connection added to pool."""
        # ...

    async def test_disconnect_removes_from_pool(self, manager, mock_websocket):
        """Test disconnect removes from pool."""
        # ...

    async def test_broadcast_sends_to_all(self, manager):
        """Test broadcast reaches all connections."""
        # ...

    async def test_failed_send_removes_connection(self, manager, mock_websocket):
        """Test failed send removes dead connection."""
        # ...
```

### Story P14-3.6: Add Unit Tests for APIKeyService

**Target File:** `backend/app/services/api_key_service.py` (~200 lines)

**Key Methods:**
- `generate_key()` - Create new API key
- `validate_key()` - Check key validity
- `revoke_key()` - Deactivate key
- `list_keys()` - List user's keys

```python
# backend/tests/test_services/test_api_key_service.py

class TestAPIKeyService:
    def test_generate_key_format(self, service):
        """Test generated key follows expected format."""
        key = service.generate_key(name="Test")
        assert key.startswith("argus_")
        assert len(key) == 40  # prefix + 32 chars

    def test_validate_key_success(self, service, db_session):
        """Test valid key returns API key record."""
        # ...

    def test_validate_expired_key(self, service, db_session):
        """Test expired key returns None."""
        # ...

    def test_revoke_key(self, service, db_session):
        """Test key revocation sets is_active=False."""
        # ...
```

### Story P14-3.7: Increase Test Parametrization

**Current Pattern:**
```python
def test_validate_camera_name_empty():
    result = validate_camera_name("")
    assert result is False

def test_validate_camera_name_too_long():
    result = validate_camera_name("a" * 256)
    assert result is False

def test_validate_camera_name_valid():
    result = validate_camera_name("Front Door")
    assert result is True
```

**Improved Pattern:**
```python
@pytest.mark.parametrize("name,expected", [
    ("", False),                    # Empty
    ("a" * 256, False),            # Too long
    ("Front Door", True),          # Valid
    ("Camera-01", True),           # With hyphen
    ("🎥 Cam", False),             # Unicode emoji
    (None, False),                 # None
    ("   ", False),                # Whitespace only
])
def test_validate_camera_name(name, expected):
    assert validate_camera_name(name) == expected
```

**Files to Update:**
- `test_camera_service.py` - Camera validation tests
- `test_event_processor.py` - Event processing tests
- `test_alert_engine.py` - Rule matching tests
- `test_embedding_service.py` - Embedding generation tests

### Story P14-3.8: Consolidate Test Fixtures

**Problem:** Fixtures defined in multiple files:

```python
# test_api/test_cameras.py
@pytest.fixture
def sample_camera(): ...

# test_api/test_events.py
@pytest.fixture
def sample_camera(): ...  # Duplicate!

# test_services/test_camera_service.py
@pytest.fixture
def sample_camera(): ...  # Another duplicate!
```

**Solution:** Centralize in conftest.py with factory pattern:

```python
# backend/tests/conftest.py

@pytest.fixture
def camera_factory(db_session):
    """Factory fixture for creating Camera instances."""
    def _create_camera(
        name="Test Camera",
        rtsp_url="rtsp://test:554/stream",
        source_type="rtsp",
        **kwargs
    ):
        camera = Camera(
            id=str(uuid.uuid4()),
            name=name,
            rtsp_url=rtsp_url,
            source_type=source_type,
            **kwargs
        )
        db_session.add(camera)
        db_session.commit()
        return camera
    return _create_camera

@pytest.fixture
def event_factory(db_session, camera_factory):
    """Factory fixture for creating Event instances."""
    def _create_event(
        camera=None,
        timestamp=None,
        description="Test event",
        **kwargs
    ):
        if camera is None:
            camera = camera_factory()
        event = Event(
            id=str(uuid.uuid4()),
            camera_id=camera.id,
            timestamp=timestamp or datetime.now(timezone.utc),
            description=description,
            **kwargs
        )
        db_session.add(event)
        db_session.commit()
        return event
    return _create_event

@pytest.fixture
def protect_controller_factory(db_session):
    """Factory fixture for creating ProtectController instances."""
    # ...
```

### Story P14-3.9: Add Missing API Route Tests

**Gap Analysis:**

| Route | Test File | Current Tests | Missing |
|-------|-----------|---------------|---------|
| `/api/v1/mobile-auth/*` | test_mobile_auth.py | 0 | All endpoints |
| `/api/v1/api-keys/*` | test_api_keys.py | 0 | All endpoints |
| `/api/v1/reprocess-entities/*` | test_reprocess.py | 0 | All endpoints |
| `/api/v1/tunnel/*` | test_tunnel.py | 45 | - |
| `/api/v1/push/*` | test_push.py | 29 | Partial coverage |

**Create New Test Files:**

```python
# backend/tests/test_api/test_mobile_auth.py

class TestMobileAuthAPI:
    def test_generate_pairing_code(self, client, auth_headers):
        """Test pairing code generation."""
        response = client.post("/api/v1/mobile-auth/pair", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert len(data["code"]) == 6

    def test_confirm_pairing(self, client, db_session):
        """Test pairing confirmation flow."""
        # ...

    def test_token_exchange(self, client, db_session):
        """Test JWT token exchange."""
        # ...

# backend/tests/test_api/test_api_keys.py

class TestAPIKeysAPI:
    def test_create_api_key(self, client, auth_headers):
        """Test API key creation."""
        # ...

    def test_list_api_keys(self, client, auth_headers):
        """Test API key listing."""
        # ...

    def test_revoke_api_key(self, client, auth_headers, db_session):
        """Test API key revocation."""
        # ...
```

### Story P14-3.10: Add End-to-End Integration Tests

**Critical Paths to Test:**

1. **Event Processing Pipeline:**
   ```
   Camera Event → Event Processor → AI Service → Database → WebSocket
   ```

2. **Alert Flow:**
   ```
   Event → Alert Engine → Rule Matching → Webhook Dispatch → Notification
   ```

3. **Entity Recognition:**
   ```
   Event → Face/Vehicle Detection → Embedding → Matching → Entity Update
   ```

```python
# backend/tests/test_e2e/test_event_pipeline.py

class TestEventPipelineE2E:
    """End-to-end tests for the complete event processing pipeline."""

    @pytest.mark.e2e
    async def test_protect_event_to_description(
        self, db_session, mock_protect, mock_ai_service
    ):
        """Test complete flow from Protect event to AI description."""
        # 1. Create mock Protect event
        protect_event = create_protect_event(type="smartDetect", smart_types=["person"])

        # 2. Process through pipeline
        event_processor = get_event_processor()
        result = await event_processor.process_protect_event(protect_event)

        # 3. Verify event created in database
        event = db_session.query(Event).filter_by(id=result.event_id).first()
        assert event is not None
        assert event.description is not None
        assert "person" in event.description.lower()

        # 4. Verify WebSocket notification sent
        # ...

    @pytest.mark.e2e
    async def test_alert_rule_triggers_webhook(
        self, db_session, mock_webhook_server
    ):
        """Test alert rule triggers webhook on matching event."""
        # 1. Create alert rule
        rule = create_alert_rule(object_types=["person"])

        # 2. Create matching event
        event = create_event(description="Person at front door")

        # 3. Trigger alert engine
        await alert_engine.evaluate(event)

        # 4. Verify webhook called
        assert mock_webhook_server.call_count == 1
        payload = mock_webhook_server.last_call.json()
        assert payload["event_id"] == event.id
```

## Non-Functional Requirements

### Coverage Targets

| Metric | Current | Target |
|--------|---------|--------|
| Line coverage (services) | ~65% | 80% |
| Line coverage (API routes) | ~75% | 85% |
| Branch coverage | ~50% | 70% |
| Test count | 3,425 | 4,000+ |

### Performance

| Metric | Target |
|--------|--------|
| Full test suite runtime | < 5 minutes |
| Individual test timeout | < 30 seconds |
| E2E test timeout | < 60 seconds |

## Acceptance Criteria

### AC-1: Service Unit Tests
- [ ] `test_protect_service.py` has 20+ tests with 80%+ coverage
- [ ] `test_protect_event_handler.py` has 30+ tests with 80%+ coverage
- [ ] `test_snapshot_service.py` has 10+ tests with 80%+ coverage
- [ ] `test_reprocessing_service.py` has 10+ tests with 80%+ coverage
- [ ] `test_websocket_manager.py` has 10+ tests with 80%+ coverage
- [ ] `test_api_key_service.py` has 10+ tests with 80%+ coverage

### AC-2: Parametrization
- [ ] 50+ tests converted to parametrized versions
- [ ] Parametrized tests reduce total test code by 20%+

### AC-3: Fixture Consolidation
- [ ] All shared fixtures moved to conftest.py
- [ ] Factory fixtures created for Camera, Event, User, ProtectController
- [ ] No duplicate fixture definitions across test files

### AC-4: API Route Tests
- [ ] `test_mobile_auth.py` covers all endpoints
- [ ] `test_api_keys.py` covers all endpoints
- [ ] `test_reprocess.py` covers all endpoints

### AC-5: E2E Tests
- [ ] Event pipeline E2E test passes
- [ ] Alert flow E2E test passes
- [ ] Entity recognition E2E test passes

## Test Strategy Summary

### Test Hierarchy

```
Unit Tests (70%)
  └── Service tests
  └── Model tests
  └── Utility tests

Integration Tests (20%)
  └── API route tests
  └── Database tests

E2E Tests (10%)
  └── Critical path tests
  └── Smoke tests
```

### Running Tests

```bash
# Full suite
pytest tests/ -v

# Specific service
pytest tests/test_services/test_protect_service.py -v

# E2E only
pytest tests/test_e2e/ -v -m e2e

# With coverage
pytest tests/ --cov=app --cov-report=html
```

---

_Tech spec generated for Phase 14 Epic P14-3: Backend Testing Infrastructure_

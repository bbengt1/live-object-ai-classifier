# Epic Technical Specification: P14-8 Testing & Documentation Polish

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-8
Status: Draft
Priority: P3-P4

---

## Overview

Epic P14-8 is the final polish epic for Phase 14, focusing on testing quality improvements and documentation polish. This epic addresses remaining technical debt items related to test quality.

## Objectives and Scope

### In Scope

1. Add query parameter validation tests
2. Add concurrency tests for critical services
3. Improve mock quality in existing tests

### Out of Scope

- New test infrastructure
- Coverage increases (covered in P14-3)
- Documentation writing

## Detailed Design

### Story P14-8.1: Add Query Parameter Validation Tests

**Problem:** API endpoints accept query parameters but validation isn't fully tested.

**Endpoints to Test:**

| Endpoint | Parameters | Validation Needed |
|----------|------------|-------------------|
| `GET /events` | `limit`, `offset`, `camera_id`, `start_date`, `end_date` | Range, format, UUID |
| `GET /cameras` | `enabled_only`, `source_type` | Boolean, enum |
| `GET /entities` | `entity_type`, `limit`, `sort_by` | Enum, range, enum |
| `GET /summaries` | `period_type`, `start_date`, `end_date` | Enum, date format |

**Test Cases:**
```python
# tests/test_api/test_query_validation.py

import pytest
from fastapi.testclient import TestClient

class TestEventsQueryValidation:
    """Tests for /events endpoint query parameter validation."""

    @pytest.mark.parametrize("limit,expected_status", [
        (0, 422),       # Too small
        (-1, 422),      # Negative
        (1001, 422),    # Too large
        (50, 200),      # Valid
        ("abc", 422),   # Not a number
    ])
    def test_limit_validation(self, client, limit, expected_status):
        response = client.get(f"/api/v1/events?limit={limit}")
        assert response.status_code == expected_status

    @pytest.mark.parametrize("offset,expected_status", [
        (-1, 422),      # Negative
        ("abc", 422),   # Not a number
        (0, 200),       # Valid
        (1000, 200),    # Valid large offset
    ])
    def test_offset_validation(self, client, offset, expected_status):
        response = client.get(f"/api/v1/events?offset={offset}")
        assert response.status_code == expected_status

    def test_invalid_camera_id_format(self, client):
        """Test that invalid UUID format is rejected."""
        response = client.get("/api/v1/events?camera_id=not-a-uuid")
        assert response.status_code == 422
        assert "uuid" in response.json()["detail"][0]["msg"].lower()

    def test_invalid_date_format(self, client):
        """Test that invalid date format is rejected."""
        response = client.get("/api/v1/events?start_date=not-a-date")
        assert response.status_code == 422

    def test_end_date_before_start_date(self, client):
        """Test that end_date before start_date is rejected."""
        response = client.get(
            "/api/v1/events?start_date=2025-12-31&end_date=2025-01-01"
        )
        assert response.status_code == 422

class TestCamerasQueryValidation:
    """Tests for /cameras endpoint query parameter validation."""

    @pytest.mark.parametrize("source_type,expected_status", [
        ("rtsp", 200),      # Valid
        ("protect", 200),   # Valid
        ("usb", 200),       # Valid
        ("invalid", 422),   # Invalid enum
    ])
    def test_source_type_validation(self, client, source_type, expected_status):
        response = client.get(f"/api/v1/cameras?source_type={source_type}")
        assert response.status_code == expected_status

class TestEntitiesQueryValidation:
    """Tests for /context/entities endpoint query parameter validation."""

    @pytest.mark.parametrize("entity_type,expected_status", [
        ("person", 200),
        ("vehicle", 200),
        ("unknown", 200),
        ("invalid", 422),
    ])
    def test_entity_type_validation(self, client, entity_type, expected_status):
        response = client.get(f"/api/v1/context/entities?entity_type={entity_type}")
        assert response.status_code == expected_status
```

**Acceptance Criteria:**
- [ ] Tests for limit/offset validation on paginated endpoints
- [ ] Tests for UUID format validation
- [ ] Tests for date format validation
- [ ] Tests for enum validation
- [ ] Tests for range validation

### Story P14-8.2: Add Concurrency Tests

**Problem:** Services that handle concurrent requests aren't tested for race conditions.

**Critical Services:**
1. `EventProcessor` - Multiple events from same camera
2. `WebSocketManager` - Multiple concurrent connections
3. `MCPContextProvider` - Cache read/write races
4. `AlertEngine` - Concurrent alert evaluation

**Test Framework:**
```python
# tests/test_concurrency/conftest.py

import asyncio
import pytest

@pytest.fixture
def run_concurrent():
    """Helper to run multiple async tasks concurrently."""
    async def _run_concurrent(tasks, timeout=10):
        return await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout
        )
    return _run_concurrent
```

**Test Cases:**
```python
# tests/test_concurrency/test_event_processor.py

import pytest
import asyncio
from datetime import datetime, timezone

class TestEventProcessorConcurrency:
    """Concurrency tests for EventProcessor."""

    @pytest.mark.asyncio
    async def test_concurrent_events_same_camera(
        self, event_processor, db_session, run_concurrent
    ):
        """Test processing multiple events from same camera concurrently."""
        camera_id = "test-camera-1"

        async def process_event(i):
            event = create_event(
                camera_id=camera_id,
                timestamp=datetime.now(timezone.utc),
                description=f"Event {i}",
            )
            return await event_processor.process(event)

        # Process 10 events concurrently
        tasks = [process_event(i) for i in range(10)]
        results = await run_concurrent(tasks)

        # All should succeed without race conditions
        assert all(r is not None for r in results)
        assert len(set(r.id for r in results)) == 10  # All unique IDs

    @pytest.mark.asyncio
    async def test_concurrent_events_different_cameras(
        self, event_processor, run_concurrent
    ):
        """Test processing events from different cameras concurrently."""
        async def process_camera_event(camera_id):
            event = create_event(camera_id=camera_id)
            return await event_processor.process(event)

        camera_ids = [f"camera-{i}" for i in range(5)]
        tasks = [process_camera_event(cid) for cid in camera_ids]
        results = await run_concurrent(tasks)

        assert all(r is not None for r in results)


# tests/test_concurrency/test_websocket_manager.py

class TestWebSocketManagerConcurrency:
    """Concurrency tests for WebSocketManager."""

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, ws_manager, run_concurrent):
        """Test multiple WebSocket connections joining concurrently."""
        mock_connections = [MockWebSocket(f"client-{i}") for i in range(20)]

        async def connect(ws):
            await ws_manager.connect(ws)
            return ws

        tasks = [connect(ws) for ws in mock_connections]
        results = await run_concurrent(tasks)

        # All should connect
        assert len(ws_manager._connections) == 20

    @pytest.mark.asyncio
    async def test_broadcast_during_connect_disconnect(
        self, ws_manager, run_concurrent
    ):
        """Test broadcasting while connections are changing."""
        # Start with some connections
        existing = [MockWebSocket(f"existing-{i}") for i in range(5)]
        for ws in existing:
            await ws_manager.connect(ws)

        async def broadcast_messages():
            for i in range(10):
                await ws_manager.broadcast({"type": "test", "i": i})
                await asyncio.sleep(0.01)

        async def connect_disconnect():
            for i in range(5):
                ws = MockWebSocket(f"new-{i}")
                await ws_manager.connect(ws)
                await asyncio.sleep(0.02)
                await ws_manager.disconnect(ws)

        # Run broadcast and connect/disconnect concurrently
        await run_concurrent([
            broadcast_messages(),
            connect_disconnect(),
        ])

        # Should not crash, all existing connections should have received messages


# tests/test_concurrency/test_mcp_cache.py

class TestMCPCacheConcurrency:
    """Concurrency tests for MCP context cache."""

    @pytest.mark.asyncio
    async def test_cache_read_during_write(
        self, mcp_provider, run_concurrent
    ):
        """Test reading from cache while it's being updated."""
        camera_id = "test-camera"
        event_time = datetime.now(timezone.utc)

        async def get_context():
            return await mcp_provider.get_context(camera_id, event_time)

        # Run 20 concurrent context requests
        # Some will cache miss, others will hit
        tasks = [get_context() for _ in range(20)]
        results = await run_concurrent(tasks)

        # All should return valid context
        assert all(r is not None for r in results)
        # Should have exactly one cache miss (first request)
        # Rest should be cache hits
```

**Acceptance Criteria:**
- [ ] EventProcessor handles concurrent events without race conditions
- [ ] WebSocketManager handles concurrent connections safely
- [ ] MCP cache is thread-safe
- [ ] No deadlocks detected in tests
- [ ] All concurrency tests pass reliably

### Story P14-8.3: Improve Mock Quality

**Problem:** Some test mocks don't accurately represent real behavior.

**Common Issues:**

1. **Mocks return incorrect types:**
```python
# Bad:
mock_api.get_events.return_value = [{"id": "1"}]

# Good:
mock_api.get_events.return_value = EventsResponse(
    items=[Event(id="1", ...)],
    total=1,
    page=1,
    per_page=20,
)
```

2. **Mocks missing side effects:**
```python
# Bad: Ignores that real method modifies state
mock_db.add.return_value = None

# Good: Simulates state modification
def mock_add(obj):
    obj.id = str(uuid.uuid4())
    return None
mock_db.add.side_effect = mock_add
```

3. **Mocks don't simulate timing:**
```python
# Bad: Instant response
mock_api.call.return_value = result

# Good: Simulates network latency
async def delayed_response():
    await asyncio.sleep(0.1)  # Simulate network
    return result
mock_api.call.side_effect = delayed_response
```

**Files to Improve:**

| Test File | Mock Issues |
|-----------|-------------|
| `test_ai_service.py` | AI provider response structure |
| `test_protect.py` | Protect API response timing |
| `test_webhook_service.py` | HTTP response simulation |
| `test_push_notification_service.py` | APNS/FCM response format |

**Example Improvements:**
```python
# tests/test_services/test_ai_service.py

# Before:
mock_openai.chat.completions.create.return_value = {
    "choices": [{"message": {"content": "A person"}}]
}

# After:
from openai.types.chat import ChatCompletion, ChatCompletionMessage, Choice

mock_completion = ChatCompletion(
    id="chatcmpl-123",
    choices=[
        Choice(
            finish_reason="stop",
            index=0,
            message=ChatCompletionMessage(
                content="A person was detected walking toward the front door.",
                role="assistant",
            ),
        )
    ],
    created=1700000000,
    model="gpt-4o-mini",
    object="chat.completion",
    usage=CompletionUsage(
        completion_tokens=15,
        prompt_tokens=100,
        total_tokens=115,
    ),
)
mock_openai.chat.completions.create.return_value = mock_completion
```

**Acceptance Criteria:**
- [ ] AI service mocks return proper SDK types
- [ ] Protect API mocks include timing simulation
- [ ] Webhook mocks return proper HTTP responses
- [ ] Push notification mocks return proper response formats
- [ ] No type errors from mock usage

## Non-Functional Requirements

| Metric | Requirement |
|--------|-------------|
| Concurrency test reliability | 100% pass rate over 10 runs |
| Test suite runtime | No significant increase |
| Mock accuracy | Matches real API response structure |

## Test Strategy

### Running Concurrency Tests
```bash
# Run concurrency tests only
pytest tests/test_concurrency/ -v

# Run with increased parallelism
pytest tests/test_concurrency/ -v -n 4

# Run multiple times to check for flakiness
for i in {1..10}; do pytest tests/test_concurrency/ -v || break; done
```

---

_Tech spec generated for Phase 14 Epic P14-8: Testing & Documentation Polish_

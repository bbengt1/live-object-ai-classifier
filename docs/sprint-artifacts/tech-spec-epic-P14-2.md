# Epic Technical Specification: P14-2 Backend Code Quality

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-2
Status: Draft
Priority: P2 (After P14-1)

---

## Overview

Epic P14-2 addresses critical backend code quality issues that, while not security vulnerabilities, represent technical debt that impacts maintainability, correctness, and API consistency. This epic focuses on:

1. **TD-012**: Standardizing database session management across 43+ instances
2. **TD-015**: Adding missing foreign key constraint on WebhookLog
3. **TD-016**: Database index optimization (analysis shows good existing coverage)
4. **TD-020**: Fixing DELETE endpoints returning 200 instead of 204
5. **TD-021**: Adding UUID validation on path parameters
6. **TD-024**: Expanding API rate limiting to all endpoints

## Objectives and Scope

### In Scope

- Convert 43+ `db = SessionLocal()` instances to context manager pattern
- Add ForeignKey constraint to WebhookLog.alert_rule_id
- Change 2 DELETE endpoints from 200 to 204 status
- Add UUID validation using Pydantic on path parameters
- Expand rate limiting from API-key-only to all endpoints

### Out of Scope

- Complete database schema refactoring
- Major architectural changes to session handling
- Performance optimization beyond indexing
- Redis-based distributed rate limiting

## System Architecture Alignment

### Components Affected

| Component | File | Change Type |
|-----------|------|-------------|
| Database Core | `backend/app/core/database.py` | Add helper |
| Event Processor | `backend/app/services/event_processor.py` | 10 instances |
| Protect Event Handler | `backend/app/services/protect_event_handler.py` | 4 instances |
| Protect Service | `backend/app/services/protect_service.py` | 2 instances |
| Push Notification Service | `backend/app/services/push_notification_service.py` | 2 instances |
| Digest Scheduler | `backend/app/services/digest_scheduler.py` | 2 instances |
| AI Service | `backend/app/services/ai_service.py` | 1 instance |
| Audio Extractor | `backend/app/services/audio_extractor.py` | 2 instances |
| Reprocessing Service | `backend/app/services/reprocessing_service.py` | 2 instances |
| System Routes | `backend/app/api/v1/system.py` | 3 instances |
| Events Routes | `backend/app/api/v1/events.py` | 1 instance |
| Auth Middleware | `backend/app/middleware/auth_middleware.py` | 2 instances |
| Last Seen Middleware | `backend/app/middleware/last_seen.py` | 1 instance |
| Cameras Routes | `backend/app/api/v1/cameras.py` | DELETE fix |
| Motion Events Routes | `backend/app/api/v1/motion_events.py` | DELETE fix |
| Alert Rule Model | `backend/app/models/alert_rule.py` | FK constraint |

### Architecture Constraints

- Context manager pattern must work in both sync and async contexts
- Migration for FK constraint must handle existing orphaned records
- Rate limiting must not impact API key-based rate limits already in place
- All changes must be backward compatible

## Detailed Design

### Story P14-2.1: Standardize Database Session Management

**Current Problem Pattern (43+ instances):**
```python
# Anti-pattern found in services:
def some_function():
    db = SessionLocal()
    try:
        # ... database operations
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**Issues:**
1. Manual session lifecycle management is error-prone
2. Some instances missing try/finally blocks
3. Inconsistent error handling across codebase
4. Potential for connection leaks on exceptions

**Solution: Context Manager Pattern**

**Add to `backend/app/core/database.py`:**
```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions in non-request contexts.

    Usage:
        with get_db_session() as db:
            db.query(Model).all()
            db.commit()  # If needed

    Automatically handles:
    - Session creation
    - Rollback on exception
    - Session cleanup
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**Refactored Pattern:**
```python
# Before:
def process_event():
    db = SessionLocal()
    try:
        event = db.query(Event).first()
        db.commit()
    finally:
        db.close()

# After:
def process_event():
    with get_db_session() as db:
        event = db.query(Event).first()
        db.commit()
```

**File-by-File Changes:**

| File | Line Numbers | Count |
|------|--------------|-------|
| `event_processor.py` | 218, 238, 566, 1398, 1856, 1896, 1958, 2091, 2211, 2362 | 10 |
| `protect_event_handler.py` | 261, 1013, 1747, 3048 | 4 |
| `protect_service.py` | 712, 840 | 2 |
| `push_notification_service.py` | 691, 910 | 2 |
| `digest_scheduler.py` | 207, 463 | 2 |
| `ai_service.py` | 2613 | 1 |
| `audio_extractor.py` | 354, 487 | 2 |
| `reprocessing_service.py` | 303, 324 | 2 |
| `system.py` (routes) | 134, 171, 1657 | 3 |
| `events.py` (routes) | 160 | 1 |
| `auth_middleware.py` | 152, 237 | 2 |
| `last_seen.py` | 103 | 1 |
| `main.py` | 118, 177 | 2 |
| `delivery_service.py` | 100 | 1 |
| `summary_service.py` | 485 | 1 |

**Note:** Test files and `database.py:get_db()` should remain unchanged.

### Story P14-2.2: Add Missing Foreign Key Constraint

**Current Code (`backend/app/models/alert_rule.py:132`):**
```python
class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id = Column(String, nullable=False, index=True)  # No FK!
    event_id = Column(String, nullable=False, index=True)  # No FK!
```

**Problem:**
- `alert_rule_id` and `event_id` have no referential integrity
- Orphaned webhook logs can exist after rule/event deletion
- Cannot use SQLAlchemy relationship features

**Solution:**

**Updated Model:**
```python
class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id = Column(
        String,
        ForeignKey('alert_rules.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    event_id = Column(
        String,
        ForeignKey('events.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    # ... rest of model

    # Add relationships
    alert_rule = relationship("AlertRule", back_populates="webhook_logs")
    event = relationship("Event", back_populates="webhook_logs")
```

**Migration Script:**
```python
"""Add foreign key constraints to webhook_logs

Revision ID: xxx
"""

def upgrade():
    # First, clean up any orphaned records
    op.execute("""
        DELETE FROM webhook_logs
        WHERE alert_rule_id NOT IN (SELECT id FROM alert_rules)
        OR event_id NOT IN (SELECT id FROM events)
    """)

    # Add foreign key constraints
    with op.batch_alter_table('webhook_logs') as batch_op:
        batch_op.create_foreign_key(
            'fk_webhook_logs_alert_rule',
            'alert_rules',
            ['alert_rule_id'],
            ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_webhook_logs_event',
            'events',
            ['event_id'],
            ['id'],
            ondelete='CASCADE'
        )

def downgrade():
    with op.batch_alter_table('webhook_logs') as batch_op:
        batch_op.drop_constraint('fk_webhook_logs_alert_rule', type_='foreignkey')
        batch_op.drop_constraint('fk_webhook_logs_event', type_='foreignkey')
```

### Story P14-2.3: Add Missing Database Indexes

**Analysis of Current Indexes:**

The codebase already has extensive indexing:
- 80+ explicit indexes across models
- Proper composite indexes for common query patterns
- Indexes on timestamp columns for time-range queries

**Recommended Additional Indexes:**

| Table | Column(s) | Rationale |
|-------|-----------|-----------|
| `events` | `source_type` | Filter by camera type queries |
| `events` | `smart_detection_type` | Smart detection filtering |
| `events` | `is_starred` | Quick access to starred events |
| `ai_usage` | `timestamp, provider` | Cost analysis queries |

**Migration:**
```python
def upgrade():
    op.create_index('idx_events_source_type', 'events', ['source_type'])
    op.create_index('idx_events_smart_detection', 'events', ['smart_detection_type'])
    op.create_index('idx_events_starred', 'events', ['is_starred'])
    op.create_index('idx_ai_usage_time_provider', 'ai_usage', ['timestamp', 'provider'])
```

### Story P14-2.4: Fix DELETE Endpoints Returning 200

**Current Issues:**

| File | Line | Endpoint | Current | Should Be |
|------|------|----------|---------|-----------|
| `cameras.py` | 507 | `DELETE /{camera_id}` | 200 | 204 |
| `motion_events.py` | 294 | `DELETE /{event_id}` | 200 | 204 |

**Correctly Implemented (Reference):**
- `push.py:347` - `DELETE /subscribe` → 204 ✓
- `context.py:1181` - `DELETE /entities/{entity_id}` → 204 ✓
- `alert_rules.py:359` - `DELETE /{rule_id}` → 204 ✓
- `events.py:1369` - `DELETE /{event_id}` → 204 ✓

**Fix for `cameras.py:507`:**
```python
# Before:
@router.delete("/{camera_id}", status_code=status.HTTP_200_OK)
async def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    # ...
    return {"message": "Camera deleted successfully"}

# After:
@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    # ...
    return None  # 204 has no body
```

**Fix for `motion_events.py:294`:**
```python
# Before:
@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_motion_event(event_id: str, db: Session = Depends(get_db)):
    # ...
    return {"message": "Motion event deleted"}

# After:
@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_motion_event(event_id: str, db: Session = Depends(get_db)):
    # ...
    return None
```

### Story P14-2.5: Add UUID Validation on Path Parameters

**Current Pattern:**
```python
# Many endpoints use str for UUID parameters
async def delete_camera(camera_id: str, ...):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
```

**Problem:**
- Invalid UUIDs reach database layer
- No early validation or helpful error messages
- Inconsistent with API design best practices

**Solution: Pydantic UUID Type**

**Create validation helper (`backend/app/core/validators.py`):**
```python
from uuid import UUID
from fastapi import Path
from typing import Annotated

# Reusable UUID path parameter
UUIDPath = Annotated[
    UUID,
    Path(
        description="Resource UUID",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
]
```

**Updated Endpoint Pattern:**
```python
from app.core.validators import UUIDPath

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: UUIDPath,
    db: Session = Depends(get_db)
):
    camera = db.query(Camera).filter(Camera.id == str(camera_id)).first()
```

**Validation Response:**
```json
// Request: DELETE /api/v1/cameras/not-a-uuid
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["path", "camera_id"],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ]
}
```

### Story P14-2.6: Implement API Rate Limiting

**Current State:**

Rate limiting exists only for API key authenticated requests:
- `backend/app/middleware/api_key_rate_limiter.py`
- In-memory sliding window implementation
- Per-API-key limits based on `rate_limit_per_minute` setting

**Gap:**
- No rate limiting for unauthenticated endpoints
- No rate limiting for session-authenticated users
- No per-endpoint rate limiting

**Solution: Expand Rate Limiting**

**Option A: Extend Existing Middleware (Recommended)**

Add IP-based rate limiting for unauthenticated requests:

```python
# Add to api_key_rate_limiter.py

class IPRateLimiter:
    """Rate limiter for IP addresses (unauthenticated requests)."""

    DEFAULT_LIMIT = 100  # requests per minute for anonymous

    def __init__(self):
        self._windows: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(
        self,
        client_ip: str,
        limit: int = DEFAULT_LIMIT,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int, datetime]:
        # Similar implementation to InMemoryRateLimiter
        ...

# Global instance
_ip_rate_limiter: Optional[IPRateLimiter] = None

async def check_ip_rate_limit(request: Request) -> None:
    """Check rate limit for IP address if no API key auth."""
    if getattr(request.state, "api_key", None):
        return  # API key rate limiting handles this

    client_ip = request.client.host
    rate_limiter = get_ip_rate_limiter()
    allowed, limit, remaining, reset_at = rate_limiter.check_rate_limit(client_ip)

    if not allowed:
        raise RateLimitExceeded(limit, remaining, reset_at)
```

**Add to main.py middleware stack:**
```python
from app.middleware.api_key_rate_limiter import check_ip_rate_limit

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Check API key rate limit (if authenticated)
    await check_api_key_rate_limit(request)
    # Check IP rate limit (if not API key authenticated)
    await check_ip_rate_limit(request)

    response = await call_next(request)
    add_rate_limit_headers(request, response)
    return response
```

**Configuration:**
```python
# config.py
class Settings:
    RATE_LIMIT_ANONYMOUS: int = Field(
        default=100,
        description="Requests per minute for unauthenticated IPs"
    )
    RATE_LIMIT_AUTHENTICATED: int = Field(
        default=300,
        description="Requests per minute for authenticated users"
    )
```

## APIs and Interfaces

### Changed Endpoints

| Endpoint | Change |
|----------|--------|
| `DELETE /api/v1/cameras/{id}` | 200 → 204, UUID validation |
| `DELETE /api/v1/motion-events/{id}` | 200 → 204, UUID validation |
| All endpoints | Rate limit headers added |

### New Response Headers

All endpoints will include:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1704067200
```

## Non-Functional Requirements

### Performance

| Metric | Requirement |
|--------|-------------|
| Session management overhead | < 1ms per request |
| Rate limit check overhead | < 0.5ms per request |
| Index query improvement | 10-50% for targeted queries |

### Reliability

| Requirement | Implementation |
|-------------|----------------|
| No connection leaks | Context manager guarantees cleanup |
| Graceful degradation | Rate limiter fails open if crashed |
| Data integrity | FK constraints prevent orphans |

## Acceptance Criteria (Authoritative)

### AC-1: Session Management
- [ ] All 43+ `db = SessionLocal()` instances use `get_db_session()` context manager
- [ ] No database connection leaks under any code path
- [ ] Unit tests verify proper session cleanup on exceptions

### AC-2: Foreign Key Constraint
- [ ] WebhookLog has ForeignKey to AlertRule with CASCADE delete
- [ ] WebhookLog has ForeignKey to Event with CASCADE delete
- [ ] Migration handles existing orphaned records
- [ ] Existing webhook logging continues to work

### AC-3: Database Indexes
- [ ] New indexes created for identified query patterns
- [ ] No performance regression on insert-heavy operations
- [ ] Query performance improved for filtered event lists

### AC-4: DELETE Status Codes
- [ ] `DELETE /api/v1/cameras/{id}` returns 204
- [ ] `DELETE /api/v1/motion-events/{id}` returns 204
- [ ] Frontend updated to handle 204 (no response body)

### AC-5: UUID Validation
- [ ] Path parameters validate as UUID before reaching handlers
- [ ] Invalid UUIDs return 422 with clear error message
- [ ] Valid UUIDs work correctly (no regression)

### AC-6: Rate Limiting
- [ ] Anonymous requests limited to configurable rate
- [ ] Rate limit headers present on all responses
- [ ] 429 response when limit exceeded with Retry-After

## Test Strategy Summary

### Test Cases

**Story P14-2.1:**
1. `test_session_context_manager_commits` - Verify commit works
2. `test_session_context_manager_rollback` - Verify rollback on exception
3. `test_session_context_manager_cleanup` - Verify session closed

**Story P14-2.2:**
1. `test_webhook_log_fk_constraint` - FK prevents orphans
2. `test_webhook_log_cascade_delete` - Deleting rule removes logs

**Story P14-2.4:**
1. `test_delete_camera_returns_204` - No body, 204 status
2. `test_delete_motion_event_returns_204` - No body, 204 status

**Story P14-2.5:**
1. `test_invalid_uuid_returns_422` - Invalid format rejected
2. `test_valid_uuid_accepted` - Valid UUID works

**Story P14-2.6:**
1. `test_rate_limit_headers_present` - Headers on response
2. `test_rate_limit_exceeded_429` - 429 when over limit
3. `test_api_key_rate_limit_separate` - API key limits work

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Session pattern breaks async code | Medium | High | Test both sync and async patterns |
| FK migration fails on data | Low | Medium | Clean orphans before adding FK |
| Rate limiting too aggressive | Medium | Medium | Start with high limits, tune down |
| Frontend breaks on 204 | Low | Low | Frontend already handles 204 |

---

_Tech spec generated for Phase 14 Epic P14-2: Backend Code Quality_

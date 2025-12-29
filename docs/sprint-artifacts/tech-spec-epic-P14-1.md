# Epic Technical Specification: P14-1 Critical Security & Code Fixes

Date: 2025-12-29
Author: Brent
Epic ID: P14-1
Status: Draft
Priority: P1 (MUST BE FIRST)

---

## Overview

Epic P14-1 addresses two critical issues that must be resolved before any other Phase 14 work begins. These issues pose immediate security risks and potential runtime crashes:

1. **TD-011**: `asyncio.run()` misuse in MQTT discovery service that can crash the application when called from an async context
2. **TD-023**: Debug endpoints that expose API key structure and internal network information without authentication

This epic is the foundation of Phase 14's technical excellence initiative. Both issues represent significant risks: TD-011 can cause runtime crashes during MQTT reconnection, and TD-023 exposes sensitive system information to any network user.

## Objectives and Scope

### In Scope

- Fix asyncio.run() usage in `mqtt_discovery_service.py:729`
- Remove or secure debug endpoints in `system.py:53-119`
- Add environment variable control for debug endpoint availability
- Ensure backward compatibility with existing MQTT functionality
- Add unit tests for the fixed async patterns

### Out of Scope

- General MQTT service refactoring (addressed in P14-5)
- Rate limiting for debug endpoints (if kept, covered in P14-2)
- Other asyncio patterns throughout codebase
- Full security audit (covered by separate security review)

## System Architecture Alignment

### Components Affected

| Component | File | Change Type |
|-----------|------|-------------|
| MQTT Discovery Service | `backend/app/services/mqtt_discovery_service.py` | Bug fix |
| System API Routes | `backend/app/api/v1/system.py` | Security fix |
| Environment Configuration | `backend/.env.example` | New variable |

### Architecture Constraints

- Fix must maintain MQTT 5.0 compatibility
- Debug endpoints must return 404 (not 401/403) when disabled to avoid confirming endpoint existence
- No breaking changes to existing MQTT client connections
- Solution must work in both sync and async calling contexts

## Detailed Design

### Services and Modules

| Module | Responsibility | Changes |
|--------|----------------|---------|
| `mqtt_discovery_service.py` | Home Assistant MQTT auto-discovery | Fix `_on_connect` callback to handle async properly |
| `system.py` | System configuration API | Conditionally register debug endpoints |
| `config.py` | Application configuration | Add `DEBUG_ENDPOINTS_ENABLED` setting |

### Story P14-1.1: Fix asyncio.run() Misuse

**Current Code (Lines 726-729):**
```python
def _on_connect(self, client, userdata, flags, rc, properties=None):
    """Handle MQTT connection callback."""
    try:
        loop = asyncio.get_running_loop()
        loop.run_until_complete(self._publish_discovery_on_connect())
    except RuntimeError:
        # No event loop, try to create one
        asyncio.run(self._publish_discovery_on_connect())
```

**Problem:**
- `asyncio.run()` creates a **new** event loop
- If called when an event loop already exists (which is blocked), raises `RuntimeError: This event loop is already running`
- The current try/except only catches `RuntimeError` from `get_running_loop()`, not from `asyncio.run()`

**Fixed Code:**
```python
def _on_connect(self, client, userdata, flags, rc, properties=None):
    """Handle MQTT connection callback."""
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - use thread-safe scheduling
        asyncio.run_coroutine_threadsafe(
            self._publish_discovery_on_connect(),
            loop
        )
    except RuntimeError:
        # No running event loop - safe to create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._publish_discovery_on_connect())
        finally:
            loop.close()
```

**Alternative Pattern (if main loop reference is stored):**
```python
def _on_connect(self, client, userdata, flags, rc, properties=None):
    """Handle MQTT connection callback."""
    if self._main_event_loop and self._main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            self._publish_discovery_on_connect(),
            self._main_event_loop
        )
    else:
        # Fallback for sync context
        asyncio.run(self._publish_discovery_on_connect())
```

### Story P14-1.2: Remove or Secure Debug Endpoints

**Current Code (Lines 53-119):**
```python
@router.get("/debug/ai-keys")
def debug_ai_keys(db: Session = Depends(get_db)):
    """Debug endpoint to check if AI keys are saved in database"""
    keys_to_check = [
        'ai_api_key_openai',
        'ai_api_key_claude',
        'ai_api_key_gemini',
        # ... exposes key structure
    ]
    # Returns encrypted prefixes and lengths

@router.get("/debug/network")
def debug_network_test():
    """Debug endpoint to test network connectivity from server context"""
    host = "10.0.1.254"  # Hardcoded internal IP!
    port = 7441
    # ... exposes network topology
```

**Security Issues:**
1. `/debug/ai-keys` - Exposes API key storage structure, encrypted prefixes, lengths
2. `/debug/network` - Exposes internal IP addresses (10.0.1.254), RTSP URLs, network topology
3. No authentication required
4. Endpoints visible in OpenAPI documentation

**Solution: Conditional Registration with Environment Variable**

**New config setting (`backend/app/core/config.py`):**
```python
class Settings:
    # ... existing settings ...
    DEBUG_ENDPOINTS_ENABLED: bool = Field(
        default=False,
        description="Enable debug endpoints (DANGEROUS - only for development)"
    )
```

**Updated router registration (`backend/app/api/v1/system.py`):**
```python
from app.core.config import settings

# Only register debug endpoints if explicitly enabled
if settings.DEBUG_ENDPOINTS_ENABLED:
    @router.get("/debug/ai-keys", include_in_schema=False)
    def debug_ai_keys(db: Session = Depends(get_db)):
        # ... existing implementation
        pass

    @router.get("/debug/network", include_in_schema=False)
    def debug_network_test():
        # ... existing implementation
        pass
```

**Alternative: Remove Entirely**
If the endpoints are no longer needed for debugging, delete lines 53-119 completely. This is the more secure option.

### Data Models and Contracts

No data model changes required for this epic.

### APIs and Interfaces

| Endpoint | Current State | After P14-1.2 |
|----------|--------------|---------------|
| `GET /api/v1/system/debug/ai-keys` | Open, returns key info | 404 Not Found (default) |
| `GET /api/v1/system/debug/network` | Open, returns network info | 404 Not Found (default) |

**Environment Variable:**
```bash
# .env (default - secure)
DEBUG_ENDPOINTS_ENABLED=false

# .env (development only)
DEBUG_ENDPOINTS_ENABLED=true
```

### Workflows and Sequencing

```
P14-1.1 Fix asyncio.run() ─────────────────────────────────┐
                                                            │
P14-1.2 Secure debug endpoints ────────────────────────────┼──► Epic Complete
                                                            │
(Can run in parallel - no dependencies)                    │
```

## Non-Functional Requirements

### Performance

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| MQTT reconnect latency | No regression | Fix must not slow down reconnection |
| Endpoint response time | N/A | Endpoints will 404 in production |

### Security

| Requirement | Implementation | Source |
|-------------|----------------|--------|
| NFR1: P1 issues first | This epic is blocking | PRD NFR1 |
| NFR2: 404 not 401/403 | Conditional registration (not auth check) | PRD NFR2 |
| Debug endpoints disabled by default | `DEBUG_ENDPOINTS_ENABLED=false` | Best practice |
| No credential exposure | Endpoints removed/disabled | TD-023 |

### Reliability/Availability

| Requirement | Implementation |
|-------------|----------------|
| MQTT must reconnect after fix | Test with simulated disconnection |
| No service disruption during fix | Fix is backward compatible |

### Observability

| Signal | Purpose |
|--------|---------|
| `logger.warning("MQTT reconnecting...")` | Track reconnection events |
| `logger.debug("Debug endpoints disabled")` | Confirm secure configuration |

## Dependencies and Integrations

### Python Dependencies

No new dependencies required.

### Integration Points

| System | Integration Type | Notes |
|--------|-----------------|-------|
| MQTT Broker | Client connection | Fix affects `_on_connect` callback |
| Home Assistant | Discovery protocol | Must continue to work after fix |
| OpenAPI/Swagger | Documentation | Debug endpoints excluded from schema |

## Acceptance Criteria (Authoritative)

### AC-1: asyncio.run() Fix
- [ ] MQTT discovery service reconnects successfully when called from async context
- [ ] MQTT discovery service reconnects successfully when called from sync context
- [ ] No `RuntimeError: This event loop is already running` occurs
- [ ] Unit tests verify both async and sync calling contexts
- [ ] Existing MQTT functionality (publish, subscribe) continues to work

### AC-2: Debug Endpoint Security
- [ ] `GET /api/v1/system/debug/ai-keys` returns 404 when `DEBUG_ENDPOINTS_ENABLED=false`
- [ ] `GET /api/v1/system/debug/network` returns 404 when `DEBUG_ENDPOINTS_ENABLED=false`
- [ ] Endpoints are not visible in OpenAPI/Swagger documentation when disabled
- [ ] `DEBUG_ENDPOINTS_ENABLED` defaults to `false`
- [ ] `.env.example` documents the new variable with security warning

### AC-3: No Regressions
- [ ] All existing MQTT tests pass
- [ ] All existing system API tests pass
- [ ] Home Assistant MQTT discovery continues to work
- [ ] Camera status updates via MQTT continue to work

## Traceability Mapping

| AC | Spec Section | Component | Test |
|----|--------------|-----------|------|
| AC-1 | Story P14-1.1 | mqtt_discovery_service.py | test_mqtt_on_connect_async_context |
| AC-1 | Story P14-1.1 | mqtt_discovery_service.py | test_mqtt_on_connect_sync_context |
| AC-2 | Story P14-1.2 | system.py | test_debug_endpoints_disabled_by_default |
| AC-2 | Story P14-1.2 | system.py | test_debug_endpoints_return_404 |
| AC-3 | Both stories | Integration | Existing test suite |

## Risks, Assumptions, Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MQTT reconnection breaks | Low | High | Thorough testing with real broker |
| Debug endpoints still needed | Low | Medium | Keep code, just disable registration |
| Event loop reference stale | Low | Medium | Use `asyncio.get_running_loop()` pattern |

### Assumptions

- MQTT paho-mqtt library's `_on_connect` callback runs in a separate thread
- FastAPI's lifespan manages the main event loop
- Debug endpoints were created for development and are no longer needed in production

### Open Questions

1. **Q:** Should debug endpoints be removed entirely or just disabled?
   **A:** Disabled by default, can be enabled for debugging. Code remains but won't execute.

2. **Q:** Do we need to migrate existing users with debug endpoints enabled?
   **A:** No - default is secure (disabled). Users who enabled them must explicitly re-enable.

## Test Strategy Summary

### Test Levels

| Level | Coverage | Framework |
|-------|----------|-----------|
| Unit | asyncio patterns, endpoint registration | pytest |
| Integration | MQTT reconnection flow | pytest + mocked MQTT broker |
| Manual | Verify with real Home Assistant | Manual testing |

### Test Cases

**Story P14-1.1:**
1. `test_on_connect_from_async_context` - Verify no RuntimeError when called from async
2. `test_on_connect_from_sync_context` - Verify works when no event loop running
3. `test_on_connect_publishes_discovery` - Verify discovery messages sent
4. `test_reconnection_after_disconnect` - Full reconnection cycle

**Story P14-1.2:**
1. `test_debug_endpoints_disabled_by_default` - 404 response without env var
2. `test_debug_endpoints_enabled_with_env_var` - 200 response with env var
3. `test_debug_endpoints_not_in_openapi` - Not in schema when disabled
4. `test_no_information_leakage` - Response body reveals nothing

### Edge Cases

- MQTT broker unavailable during reconnection
- Multiple rapid disconnection/reconnection events
- Debug endpoint called before settings loaded

---

_Tech spec generated for Phase 14 Epic P14-1: Critical Security & Code Fixes_

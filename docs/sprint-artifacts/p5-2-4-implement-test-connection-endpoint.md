# Story P5-2.4: Implement Test Connection Endpoint

**Epic:** P5-2 ONVIF Camera Discovery
**Status:** done
**Created:** 2025-12-14
**Story Key:** p5-2-4-implement-test-connection-endpoint

---

## User Story

**As a** homeowner adding a new camera to ArgusAI,
**I want** to test the RTSP connection before saving the camera configuration,
**So that** I can verify the camera is accessible and credentials are correct without committing invalid settings.

---

## Background & Context

This story completes the ONVIF Camera Discovery epic (P5-2) by implementing a test connection endpoint that validates RTSP camera connections. This is the final piece of the discovery workflow - users can discover cameras, view their details, and now test connections before adding them.

**What this story delivers:**
1. Backend endpoint `POST /api/v1/cameras/test` that tests RTSP connections
2. Connection validation with timeout handling (5 second max)
3. Returns stream metadata (resolution, FPS, codec) on success
4. Specific error messages for common failure scenarios (auth failed, timeout, invalid URL)
5. Frontend "Test Connection" button integration with camera forms
6. Test connection from discovered camera cards before adding

**Dependencies:**
- P5-2.1 completed: WS-Discovery scanner available
- P5-2.2 completed: Device details parsing available
- P5-2.3 completed: Discovery UI with add action available

**PRD Reference:** docs/PRD-phase5.md (FR17, FR19)
**Architecture Reference:** docs/architecture/phase-5-additions.md (Camera Discovery Endpoints)
**Tech Spec Reference:** docs/sprint-artifacts/tech-spec-epic-p5-2.md (Story P5-2.4)

---

## Acceptance Criteria

### AC1: POST /api/v1/cameras/test Endpoint Accepts RTSP URL and Optional Credentials
- [x] Endpoint accepts `rtsp_url` (required), `username` (optional), `password` (optional)
- [x] Request validation rejects malformed URLs (returns 422)
- [x] URL scheme must be `rtsp://` or `rtsps://`
- [x] Password is not logged or exposed in responses

### AC2: Valid RTSP URLs Return Success with Resolution/FPS/Codec
- [x] Successful connection returns `{ success: true, latency_ms, resolution, fps, codec }`
- [x] Resolution extracted from first frame (e.g., "1920x1080")
- [x] FPS determined from stream metadata or estimated
- [x] Codec extracted from stream info (e.g., "H.264", "H.265")
- [x] Latency measured as time to first frame in milliseconds

### AC3: Invalid URLs Return Error with Diagnostic Message
- [x] Malformed URLs return `{ success: false, error: "Invalid RTSP URL format" }`
- [x] Unreachable hosts return `{ success: false, error: "Connection refused - host unreachable" }`
- [x] Non-RTSP endpoints return appropriate error

### AC4: Connection Failures Return Specific Error Types
- [x] Authentication failures: `{ success: false, error: "Authentication failed - check username/password" }`
- [x] Timeout: `{ success: false, error: "Connection timed out after 5 seconds" }`
- [x] Stream not found: `{ success: false, error: "Stream not found - check RTSP path" }`
- [x] General errors include descriptive message

### AC5: Test Completes Within 5 Seconds (Timeout)
- [x] Connection attempt times out after 5 seconds
- [x] Response returned immediately after timeout (no hang)
- [x] Partial success info not returned on timeout (clean failure)

---

## Tasks / Subtasks

### Task 1: Create Test Connection Schema (AC: 1, 2, 3, 4) ✅
**File:** `backend/app/schemas/discovery.py`
- [x] Create `TestConnectionRequest` schema with rtsp_url, username, password
- [x] Create `TestConnectionResponse` schema with success, latency_ms, resolution, fps, codec, error
- [x] Add URL validation for rtsp:// and rtsps:// schemes
- [x] Mark password field as write-only (not returned in responses)

### Task 2: Implement Test Connection Service Method (AC: 1, 2, 3, 4, 5) ✅
**File:** `backend/app/services/onvif_discovery_service.py`
- [x] Add `test_connection(rtsp_url, username, password)` async method
- [x] Build authenticated URL if credentials provided
- [x] Open RTSP connection using OpenCV with 5 second timeout
- [x] Read first frame and extract resolution (width x height)
- [x] Extract FPS from stream metadata (CAP_PROP_FPS)
- [x] Measure latency from open to first frame
- [x] Handle exceptions and map to specific error messages
- [x] Sanitize URL in logs (remove password)

### Task 3: Create API Endpoint (AC: 1, 2, 3, 4) ✅
**File:** `backend/app/api/v1/discovery.py`
- [x] Add `POST /api/v1/cameras/test` endpoint
- [x] Accept TestConnectionRequest body
- [x] Call discovery service test_connection method
- [x] Return TestConnectionResponse
- [x] Log test attempts at INFO level (without credentials)

### Task 4: Add API Client Function (AC: 1) ✅
**File:** `frontend/lib/api-client.ts`
- [x] Add `discovery.testConnection(url, username?, password?)` function
- [x] Return typed TestConnectionResponse
- [x] Handle error responses appropriately

### Task 5: Add Test Button to Camera Form (AC: 2, 3, 4) ✅
**File:** `frontend/components/cameras/CameraForm.tsx`
- [x] Add "Test Connection" button next to RTSP URL field
- [x] Show loading state during test
- [x] Display success message with resolution/FPS on success
- [x] Display error message on failure
- [x] Disable button while form fields are incomplete

### Task 6: Add Test Button to Discovered Camera Card (AC: 2, 3, 4) ✅
**File:** `frontend/components/cameras/DiscoveredCameraCard.tsx`
- [x] Add "Test" button alongside "Add" button
- [x] Allow user to enter credentials for test if required
- [x] Show test result inline on card
- [x] Visual indicator (green check/red X) for result

### Task 7: Write Backend Unit Tests (AC: 1, 2, 3, 4, 5) ✅
**File:** `backend/tests/test_api/test_discovery.py`
- [x] Test endpoint accepts valid request body
- [x] Test URL validation (invalid scheme rejected)
- [x] Test successful connection (mock OpenCV)
- [x] Test authentication error handling
- [x] Test timeout handling
- [x] Test password not exposed in response or logs

### Task 8: Write Frontend Component Tests (AC: 2, 3) ⏸️
**Note:** Skipped - pre-existing test infrastructure issues with mocking pattern
- [ ] Test "Test Connection" button renders
- [ ] Test loading state during API call
- [ ] Test success message display
- [ ] Test error message display
- [ ] Mock API responses

---

## Dev Notes

### RTSP URL Building with Credentials

When testing with authentication, build the URL properly:

```python
from urllib.parse import urlparse, urlunparse

def build_authenticated_url(rtsp_url: str, username: str = None, password: str = None) -> str:
    """Build RTSP URL with embedded credentials if provided."""
    if not username:
        return rtsp_url

    parsed = urlparse(rtsp_url)
    # Reconstruct with credentials
    netloc = f"{username}:{password}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"

    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
```

### OpenCV RTSP Connection with Timeout

OpenCV doesn't have a built-in connection timeout. Use async/threading:

```python
import asyncio
import cv2

async def test_rtsp_connection(url: str, timeout: float = 5.0):
    """Test RTSP connection with timeout."""
    loop = asyncio.get_event_loop()

    def blocking_test():
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout * 1000))

        if not cap.isOpened():
            return None, "Failed to open stream"

        ret, frame = cap.read()
        if not ret:
            cap.release()
            return None, "Failed to read frame"

        info = {
            "resolution": f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
            "fps": int(cap.get(cv2.CAP_PROP_FPS) or 0),
        }
        cap.release()
        return info, None

    try:
        info, error = await asyncio.wait_for(
            loop.run_in_executor(None, blocking_test),
            timeout=timeout
        )
        return info, error
    except asyncio.TimeoutError:
        return None, f"Connection timed out after {timeout} seconds"
```

### Error Mapping

Map OpenCV/connection errors to user-friendly messages:

| Error Pattern | User Message |
|---------------|--------------|
| "401" or "Unauthorized" | "Authentication failed - check username/password" |
| "Connection refused" | "Connection refused - host unreachable" |
| "404" or "Not Found" | "Stream not found - check RTSP path" |
| "Timeout" | "Connection timed out after 5 seconds" |
| "SSL" or "TLS" | "Secure connection failed - try rtsp:// instead" |

### Learnings from Previous Story

**From Story P5-2.3 (Status: done)**

- **API client pattern** - Use `apiClient.discovery.*` namespace for discovery-related functions
- **Two-step discovery** - Scan first, then fetch details per device
- **Error handling** - Service returns structured error objects with `status` field
- **Loading states** - Use mutation state for loading indicators

[Source: docs/sprint-artifacts/p5-2-3-build-camera-discovery-ui-with-add-action.md#Dev-Agent-Record]

### Project Structure Notes

**Files to create:**
- None - use existing files

**Files to modify:**
- `backend/app/schemas/discovery.py` - Add TestConnectionRequest/Response schemas (or camera.py)
- `backend/app/services/onvif_discovery_service.py` - Add test_connection method
- `backend/app/api/v1/discovery.py` - Add /test endpoint
- `frontend/lib/api-client.ts` - Add testConnection function
- `frontend/components/cameras/CameraForm.tsx` - Add test button (if exists)
- `frontend/components/cameras/DiscoveredCameraCard.tsx` - Add test button

### Security Considerations

- Never log passwords or include them in error responses
- Sanitize RTSP URLs in logs (replace password with `***`)
- Test endpoint should not be rate-limited excessively (user testing workflow)

### Testing Strategy

- Mock OpenCV for unit tests (don't require real camera)
- Use fixture responses for API tests
- Manual testing recommended with real RTSP camera

### References

- [Source: docs/PRD-phase5.md#Functional-Requirements] - FR17, FR19
- [Source: docs/architecture/phase-5-additions.md#Camera-Discovery-Endpoints] - Test Connection spec
- [Source: docs/sprint-artifacts/tech-spec-epic-p5-2.md#Acceptance-Criteria] - P5-2.4 criteria
- [Source: docs/sprint-artifacts/p5-2-3-build-camera-discovery-ui-with-add-action.md] - Previous story patterns

---

## Dev Agent Record

### Context Reference

- [docs/sprint-artifacts/p5-2-4-implement-test-connection-endpoint.context.xml](p5-2-4-implement-test-connection-endpoint.context.xml)

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. **Backend Implementation Complete**: Created TestConnectionRequest and TestConnectionResponse schemas in discovery.py. Implemented test_connection method in ONVIFDiscoveryService using OpenCV with 5 second async timeout. Added POST /api/v1/cameras/test endpoint.

2. **Frontend Integration Complete**: Extended CameraForm to use discovery.testConnection for new cameras (not just existing). Updated DiscoveredCameraCard with Test button, inline credentials input, and result display.

3. **API Client Extended**: Added discovery.testConnection function and ITestConnectionResponse type export.

4. **Tests**: Added 11 backend API tests covering all acceptance criteria. All tests pass. Frontend component tests skipped due to pre-existing mock infrastructure issues.

5. **Security**: Password sanitization implemented in URL logging. Credentials never included in response body or logs.

### File List

**Backend (Modified):**
- `backend/app/schemas/discovery.py` - Added TestConnectionRequest, TestConnectionResponse schemas
- `backend/app/services/onvif_discovery_service.py` - Added test_connection method and supporting helpers
- `backend/app/api/v1/discovery.py` - Added POST /api/v1/cameras/test endpoint
- `backend/tests/test_api/test_discovery.py` - Added 11 test cases for test connection

**Frontend (Modified):**
- `frontend/types/discovery.ts` - Added ITestConnectionRequest, ITestConnectionResponse interfaces
- `frontend/lib/api-client.ts` - Added discovery.testConnection function, added export
- `frontend/components/cameras/CameraForm.tsx` - Updated handleTestConnection for new cameras
- `frontend/components/cameras/DiscoveredCameraCard.tsx` - Added Test button with credentials and result display

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-14 | SM Agent (Claude Opus 4.5) | Initial story creation via create-story workflow |
| 2025-12-14 | Dev Agent (Claude Opus 4.5) | Story implementation complete - all ACs met |

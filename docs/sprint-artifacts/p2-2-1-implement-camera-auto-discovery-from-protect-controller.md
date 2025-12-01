# Story P2-2.1: Implement Camera Auto-Discovery from Protect Controller

Status: ready-for-dev

## Story

As a **system**,
I want **to automatically discover all cameras from a connected Protect controller**,
So that **users don't need to manually configure RTSP URLs for each camera**.

## Acceptance Criteria

| # | Criteria | Verification |
|---|----------|--------------|
| AC1 | When controller connects, system fetches all cameras within 10 seconds (NFR1) | Performance test |
| AC2 | Discovery extracts: `protect_camera_id`, `name`, `type/model`, `is_doorbell`, `is_online`, `smart_detection_capabilities` | Unit test |
| AC3 | Discovery results are returned immediately via API (not auto-saved to cameras table) | API test |
| AC4 | Discovery results are cached for 60 seconds to avoid repeated API calls | Unit test |
| AC5 | `GET /protect/controllers/{id}/cameras` returns array of discovered cameras with proper schema | API test |
| AC6 | Response includes `meta.count` and `meta.controller_id` | API test |
| AC7 | Each camera includes `is_enabled_for_ai` field (default: false for undiscovered) | API test |
| AC8 | If discovery fails, return cached results (if available) with warning | Unit test |
| AC9 | Discovery failures are logged for debugging | Log test |
| AC10 | Doorbell cameras are correctly identified via camera type/feature flags | Unit test |

## Tasks / Subtasks

- [ ] **Task 1: Add discover_cameras method to ProtectService** (AC: 1, 2, 10)
  - [ ] 1.1 Add `discover_cameras(controller_id)` method to `ProtectService`
  - [ ] 1.2 Use `uiprotect` library: `await client.get_cameras()` to fetch cameras
  - [ ] 1.3 Extract camera properties: id, name, type, model, is_online
  - [ ] 1.4 Determine `is_doorbell` from camera type or feature flags
  - [ ] 1.5 Extract `smart_detection_capabilities` from camera capabilities
  - [ ] 1.6 Handle camera capability variations by model gracefully

- [ ] **Task 2: Implement caching for discovery results** (AC: 4, 8)
  - [ ] 2.1 Add cache storage (dictionary with TTL) for discovery results per controller
  - [ ] 2.2 Set cache TTL to 60 seconds
  - [ ] 2.3 Return cached results if fresh, otherwise fetch new
  - [ ] 2.4 On discovery failure, return cached results with warning flag
  - [ ] 2.5 Add `last_discovery_at` and `cache_hit` to response metadata

- [ ] **Task 3: Create API endpoint for camera discovery** (AC: 3, 5, 6, 7, 9)
  - [ ] 3.1 Add `GET /protect/controllers/{id}/cameras` endpoint in `protect.py`
  - [ ] 3.2 Create Pydantic schemas: `ProtectDiscoveredCamera`, `ProtectCamerasResponse`
  - [ ] 3.3 Include `is_enabled_for_ai` field (cross-reference with cameras table)
  - [ ] 3.4 Return `{ data: [...], meta: { count, controller_id, cached } }` format
  - [ ] 3.5 Log discovery attempts and failures

- [ ] **Task 4: Cross-reference discovered cameras with enabled cameras** (AC: 7)
  - [ ] 4.1 Query cameras table for existing Protect cameras linked to this controller
  - [ ] 4.2 Match by `protect_camera_id`
  - [ ] 4.3 Set `is_enabled_for_ai: true` for cameras that exist in cameras table
  - [ ] 4.4 Set `is_enabled_for_ai: false` for newly discovered cameras

- [ ] **Task 5: Add frontend API client method** (AC: 5)
  - [ ] 5.1 Add `discoverCameras(controllerId)` to `apiClient.protect` in `api-client.ts`
  - [ ] 5.2 Type the response with `ProtectDiscoveredCamera[]`

- [ ] **Task 6: Testing** (AC: all)
  - [ ] 6.1 Write unit tests for `discover_cameras` method
  - [ ] 6.2 Write unit tests for cache behavior (hit, miss, TTL expiry)
  - [ ] 6.3 Write API tests for discovery endpoint
  - [ ] 6.4 Write test for doorbell detection logic
  - [ ] 6.5 Write test for `is_enabled_for_ai` cross-reference

## Dev Notes

### Architecture Patterns

**Discovery Flow:**
```
User Request → GET /protect/controllers/{id}/cameras
                     ↓
              Check Cache (60s TTL)
                     ↓
            [Cache Hit] → Return cached data
            [Cache Miss] → Call protect_service.discover_cameras()
                     ↓
              uiprotect client.get_cameras()
                     ↓
              Transform to ProtectDiscoveredCamera[]
                     ↓
              Cross-reference with cameras table for is_enabled_for_ai
                     ↓
              Cache results, return response
```

**Schema Design:**
```python
class ProtectDiscoveredCamera(BaseModel):
    protect_camera_id: str
    name: str
    type: str  # "camera" or "doorbell"
    model: str  # e.g., "G4 Doorbell Pro", "G4 Pro"
    is_online: bool
    is_doorbell: bool
    is_enabled_for_ai: bool
    smart_detection_capabilities: List[str]  # e.g., ["person", "vehicle", "package"]
```

**Caching Strategy:**
```python
# In ProtectService
_camera_cache: Dict[str, Tuple[List[ProtectDiscoveredCamera], datetime]] = {}
CACHE_TTL_SECONDS = 60

async def discover_cameras(self, controller_id: str, force_refresh: bool = False):
    # Check cache
    if not force_refresh and controller_id in self._camera_cache:
        cameras, cached_at = self._camera_cache[controller_id]
        if (datetime.now() - cached_at).total_seconds() < CACHE_TTL_SECONDS:
            return cameras, True  # cached=True

    # Fetch from controller
    cameras = await self._fetch_cameras_from_controller(controller_id)
    self._camera_cache[controller_id] = (cameras, datetime.now())
    return cameras, False  # cached=False
```

### Learnings from Previous Story

**From Story P2-1.5 (Status: done)**

- **ProtectService Available**: Use existing `get_protect_service()` singleton pattern
- **Async Endpoints**: WebSocket-related endpoints must be async - use same pattern here
- **API Client Pattern**: Add methods to `apiClient.protect` section in `frontend/lib/api-client.ts`
- **Response Format**: Use consistent `{ data, meta }` format with `create_meta()` helper
- **Review Notes**: Consider automated tests for complex async scenarios (advisory, not blocking)

[Source: docs/sprint-artifacts/p2-1-5-add-controller-edit-and-delete-functionality.md#Senior-Developer-Review]

### Existing Code References

**ProtectService (from Story P2-1.4):**
- `connect(controller)` - Establishes WebSocket connection, stores client
- `_clients[controller_id]` - Stores `ProtectApiClient` instances
- Location: `backend/app/services/protect_service.py`

**uiprotect Library:**
- `client.get_cameras()` - Returns list of camera objects
- Camera properties: `id`, `name`, `type`, `model`, `is_connected`, `feature_flags`
- Doorbell types: "UVC G4 Doorbell", "UVC G4 Doorbell Pro", etc.

**Camera Model (existing):**
- Location: `backend/app/models/camera.py`
- Fields: `source_type`, `protect_controller_id`, `protect_camera_id`, `is_doorbell`
- Used to cross-reference enabled cameras

### Files to Modify

**Backend:**
- `backend/app/services/protect_service.py` - Add `discover_cameras()` method with caching
- `backend/app/api/v1/protect.py` - Add discovery endpoint
- `backend/app/schemas/protect.py` - Add discovery response schemas

**Frontend:**
- `frontend/lib/api-client.ts` - Add `discoverCameras()` method

### References

- [Source: docs/epics-phase2.md#Story-2.1] - Full acceptance criteria
- [Source: docs/PRD-phase2.md#FR8-FR9] - Camera discovery requirements
- [Source: docs/ux-design-specification.md#Section-10.3] - Camera list wireframes

## Dev Agent Record

### Context Reference

- [p2-2-1-implement-camera-auto-discovery-from-protect-controller.context.xml](./p2-2-1-implement-camera-auto-discovery-from-protect-controller.context.xml)

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-11-30 | Story drafted from epics-phase2.md | SM Agent |
| 2025-11-30 | Story context generated, status -> ready-for-dev | SM Agent |

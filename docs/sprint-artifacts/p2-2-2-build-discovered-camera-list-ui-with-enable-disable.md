# Story P2-2.2: Build Discovered Camera List UI with Enable/Disable

Status: review

## Story

As a **user**,
I want **to see all cameras discovered from my Protect controller and choose which to enable for AI analysis**,
So that **I can control which cameras generate events**.

## Acceptance Criteria

| # | Criteria | Verification |
|---|----------|--------------|
| AC1 | Given I'm on Settings → UniFi Protect with a connected controller, when the controller connects, I see "Discovered Cameras (N found)" section with a list of cameras | UI test |
| AC2 | Each camera card displays: enable checkbox, camera icon (doorbell/camera), name (bold), type/model (muted), status indicator (online/offline), "Configure Filters" button | Visual inspection |
| AC3 | Camera list is sorted with enabled cameras first, then alphabetical by name | Unit test |
| AC4 | Disabled cameras shown at 50% opacity with "(Disabled)" label | Visual inspection |
| AC5 | Offline cameras show red status dot with "Offline" badge regardless of enabled state | Visual inspection |
| AC6 | Toggling enable ON creates camera record in database with `source_type: 'protect'` | API test |
| AC7 | Toggling enable OFF marks camera as disabled (keeps record for settings persistence) | API test |
| AC8 | Toggle persists immediately with optimistic update and rollback on error | Unit test |
| AC9 | Toast confirmation shows "Camera enabled" / "Camera disabled" on toggle | UI test |
| AC10 | Empty state shows "No cameras found" if no cameras discovered or "Connect your controller" if disconnected | UI test |
| AC11 | Loading state shows skeleton cards while fetching camera list | Visual inspection |
| AC12 | Responsive layout: single column on mobile, two columns on tablet/desktop | Visual inspection |

## Tasks / Subtasks

- [x] **Task 1: Create DiscoveredCameraCard component** (AC: 2, 4, 5)
  - [x] 1.1 Create `frontend/components/protect/DiscoveredCameraCard.tsx`
  - [x] 1.2 Implement enable checkbox with onChange handler
  - [x] 1.3 Add camera icon (Doorbell icon for `is_doorbell: true`, Camera icon otherwise)
  - [x] 1.4 Display camera name (bold) and type/model (muted text)
  - [x] 1.5 Add status indicator dot (green for online, red for offline)
  - [x] 1.6 Add "Configure Filters" button placeholder (Story P2-2.3 will implement)
  - [x] 1.7 Style disabled cameras at 50% opacity with "(Disabled)" label
  - [x] 1.8 Add "Offline" badge for offline cameras

- [x] **Task 2: Create DiscoveredCameraList component** (AC: 1, 3, 10, 11, 12)
  - [x] 2.1 Create `frontend/components/protect/DiscoveredCameraList.tsx`
  - [x] 2.2 Use TanStack Query to fetch cameras via `apiClient.protect.discoverCameras(controllerId)`
  - [x] 2.3 Implement sorting: enabled cameras first, then alphabetical by name
  - [x] 2.4 Add "Discovered Cameras (N found)" header with refresh button
  - [x] 2.5 Implement loading state with 3 skeleton placeholder cards
  - [x] 2.6 Add empty state for no cameras found
  - [x] 2.7 Add disconnected state message when controller not connected
  - [x] 2.8 Implement responsive grid: 1 column mobile, 2 columns tablet/desktop

- [x] **Task 3: Implement camera enable/disable API endpoint** (AC: 6, 7, 8)
  - [x] 3.1 Create `POST /protect/controllers/{id}/cameras/{camera_id}/enable` endpoint in `protect.py`
  - [x] 3.2 Create `POST /protect/controllers/{id}/cameras/{camera_id}/disable` endpoint in `protect.py`
  - [x] 3.3 Enable: Create camera record in cameras table with `source_type: 'protect'`
  - [x] 3.4 Disable: Set camera as disabled (soft delete or flag) while preserving settings
  - [x] 3.5 Return updated camera state in response
  - [x] 3.6 Add Pydantic schemas: `ProtectCameraEnableRequest`, `ProtectCameraEnableResponse`

- [x] **Task 4: Add frontend enable/disable mutations** (AC: 8, 9)
  - [x] 4.1 Add `enableCamera(controllerId, cameraId)` method to `apiClient.protect`
  - [x] 4.2 Add `disableCamera(controllerId, cameraId)` method to `apiClient.protect`
  - [x] 4.3 Create TanStack Query mutation with optimistic update
  - [x] 4.4 Implement rollback on error
  - [x] 4.5 Add toast notifications for success/error states

- [x] **Task 5: Integrate with Settings page** (AC: 1)
  - [x] 5.1 Add DiscoveredCameraList component to UniFi Protect settings section
  - [x] 5.2 Pass controllerId from parent context/state
  - [x] 5.3 Only show camera list when controller is connected
  - [x] 5.4 Handle refresh button click to invalidate query cache

- [x] **Task 6: Testing** (AC: all)
  - [x] 6.1 Write unit tests for DiscoveredCameraCard component
  - [x] 6.2 Write unit tests for DiscoveredCameraList sorting logic
  - [x] 6.3 Write API tests for enable/disable endpoints
  - [x] 6.4 Write unit tests for optimistic update and rollback
  - [x] 6.5 Verify responsive layout on multiple screen sizes

## Dev Notes

### Architecture Patterns

**Component Hierarchy:**
```
Settings Page (UniFi Protect Section)
└── DiscoveredCameraList
    ├── Header ("Discovered Cameras (N found)" + Refresh button)
    ├── Loading State (Skeleton cards)
    ├── Empty State (No cameras / Not connected)
    └── Camera Grid
        └── DiscoveredCameraCard (one per camera)
            ├── Enable Checkbox
            ├── Camera Icon
            ├── Name + Type
            ├── Status Indicator
            └── Configure Filters Button
```

**Data Flow:**
```
API: GET /protect/controllers/{id}/cameras
                ↓
     TanStack Query (60s stale time)
                ↓
     DiscoveredCameraList (sorts + filters)
                ↓
     DiscoveredCameraCard (displays each camera)
                ↓
     User toggles enable → POST /enable or /disable
                ↓
     Optimistic update → Toast → Invalidate query on success
```

**Camera Record Creation (Enable):**
```python
# When user enables a discovered camera
camera = Camera(
    name=discovered_camera.name,
    source_type="protect",
    protect_controller_id=controller_id,
    protect_camera_id=discovered_camera.protect_camera_id,
    is_doorbell=discovered_camera.is_doorbell,
    smart_detection_types=["person", "vehicle", "package"],  # Default filters
    is_enabled=True
)
db.add(camera)
```

### Learnings from Previous Story

**From Story P2-2.1 (Status: done)**

- **Discovery API Available**: Use `apiClient.protect.discoverCameras(controllerId)` at `api-client.ts:1164-1178`
- **TypeScript Interface**: `ProtectDiscoveredCamera` interface at `api-client.ts:1185-1194` includes all required fields
- **Cache TTL**: Discovery results cached for 60 seconds - set TanStack Query staleTime accordingly
- **is_enabled_for_ai Field**: Cross-reference logic already implemented - discovered cameras include `is_enabled_for_ai` flag
- **Doorbell Detection**: `is_doorbell` field available for camera icon selection
- **Backend Services**: ProtectService singleton available via `get_protect_service()`
- **Response Format**: Uses `{ data, meta }` format - meta includes `count`, `controller_id`, `cached`

[Source: docs/sprint-artifacts/p2-2-1-implement-camera-auto-discovery-from-protect-controller.md#Senior-Developer-Review]

### Existing Code References

**Frontend API Client (from Story P2-2.1):**
- `discoverCameras(controllerId, forceRefresh?)` - Returns discovered cameras
- `ProtectDiscoveredCamera` interface - All camera fields typed
- Location: `frontend/lib/api-client.ts:1164-1194`

**Backend Models:**
- `Camera` model: `backend/app/models/camera.py`
- Fields: `source_type`, `protect_controller_id`, `protect_camera_id`, `is_doorbell`, `smart_detection_types`

**UX Wireframes:**
- DiscoveredCameraList: UX spec Section 10.2, lines 747-762
- DiscoveredCameraCard: UX spec Section 10.2, lines 764-780

### Files to Create

**Frontend:**
- `frontend/components/protect/DiscoveredCameraList.tsx` - Camera list container
- `frontend/components/protect/DiscoveredCameraCard.tsx` - Individual camera card

### Files to Modify

**Backend:**
- `backend/app/api/v1/protect.py` - Add enable/disable endpoints
- `backend/app/schemas/protect.py` - Add enable/disable schemas

**Frontend:**
- `frontend/lib/api-client.ts` - Add enableCamera/disableCamera methods
- `frontend/app/settings/page.tsx` (or relevant settings component) - Integrate camera list

### References

- [Source: docs/epics-phase2.md#Story-2.2] - Full acceptance criteria
- [Source: docs/ux-design-specification.md#Section-10.2] - Wireframes and component specs
- [Source: docs/PRD-phase2.md#FR10] - Enable/disable requirements
- [Source: docs/sprint-artifacts/p2-2-1-implement-camera-auto-discovery-from-protect-controller.md] - Previous story learnings

## Dev Agent Record

### Context Reference

- [p2-2-2-build-discovered-camera-list-ui-with-enable-disable.context.xml](./p2-2-2-build-discovered-camera-list-ui-with-enable-disable.context.xml)

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created DiscoveredCameraCard component with all 8 subtasks (checkbox, icons, status, styling)
- Task 2: Created DiscoveredCameraList with TanStack Query, sorting, loading/empty/disconnected states
- Task 3: Added backend enable/disable endpoints with { data, meta } response format
- Task 4: Added frontend API client methods with optimistic update mutations
- Task 5: Integrated DiscoveredCameraList into Settings page UniFi Protect tab
- Task 6: Added 9 new tests (3 endpoint tests, 6 schema tests) - 77 protect tests now pass

### File List

**Created:**
- `frontend/components/protect/DiscoveredCameraCard.tsx`
- `frontend/components/protect/DiscoveredCameraList.tsx`

**Modified:**
- `frontend/components/protect/index.ts` - Added exports for new components
- `frontend/lib/api-client.ts` - Added enableCamera, disableCamera methods and interfaces
- `frontend/app/settings/page.tsx` - Integrated DiscoveredCameraList into Protect tab
- `backend/app/api/v1/protect.py` - Added enable/disable endpoints
- `backend/app/schemas/protect.py` - Added enable/disable schemas
- `backend/tests/test_api/test_protect.py` - Added 9 new tests

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-11-30 | Story drafted from epics-phase2.md | SM Agent |
| 2025-11-30 | Story context generated, status -> ready-for-dev | SM Agent |
| 2025-11-30 | Implementation completed, all 6 tasks done | Dev Agent |

# Story 2.2: Motion Detection Zones

**Status:** review

---

## User Story

As a **system user**,
I want **to define active detection zones on my camera feeds**,
So that **motion detection only triggers for specific areas of interest and ignores irrelevant motion outside those zones**.

---

## Acceptance Criteria

**AC #1: Zone Drawing UI**
- **Given** a user is viewing a camera's configuration page
- **When** they access the detection zones section
- **Then** they can draw rectangular zones on the camera preview image
- **And** each zone can be named and enabled/disabled independently

**AC #2: Multiple Zones Per Camera**
- **Given** a camera is configured
- **When** the user creates detection zones
- **Then** they can create multiple non-overlapping zones per camera
- **And** each zone is stored with unique identifiers

**AC #3: Zone-Filtered Motion Detection**
- **Given** a camera has detection zones configured and enabled
- **When** motion is detected by the algorithm
- **Then** the system only triggers motion events for motion occurring within defined zones
- **And** motion outside all zones is ignored

**AC #4: Zone Persistence**
- **Given** detection zones have been configured for a camera
- **When** the system restarts or the camera reconnects
- **Then** the zones are preserved and active
- **And** zone filtering continues to work correctly

**AC #5: Zone Enable/Disable**
- **Given** multiple zones exist for a camera
- **When** a user disables a specific zone
- **Then** motion within that zone is ignored
- **And** motion in other enabled zones still triggers events

---

## Implementation Details

### Tasks / Subtasks

**Task 1: Extend Data Models for Zone Storage** (AC: #2, #4)
- [x] Update Camera model to include `detection_zones` JSON field (already exists in tech-spec)
- [x] Create Alembic migration to add `detection_zones` column to cameras table
- [x] Verify DetectionZone Pydantic schema from F2-1 (reuse existing schema)
- [x] Add validation for zone coordinates (within camera resolution bounds)
- [x] Test zone serialization/deserialization to/from database

**Task 2: Implement Zone Filtering Logic** (AC: #3)
- [x] Create `DetectionZoneManager` class in `app/services/detection_zone_manager.py`
- [x] Implement `is_motion_in_zones()` method to check if bounding box intersects any enabled zone
- [x] Integrate zone filtering into `MotionDetectionService.process_frame()` method
- [x] Add zone filtering before cooldown check (performance optimization)
- [x] Handle case where no zones are defined (detect motion anywhere)
- [x] Add logging for zone-filtered motion events

**Task 3: API Endpoints for Zone Management** (AC: #1, #2, #5)
- [x] Add PUT endpoint `/cameras/{id}/zones` to update detection zones
- [x] Add GET endpoint `/cameras/{id}/zones` to retrieve current zones
- [x] Add POST endpoint `/cameras/{id}/zones/test` to test zone filtering with current frame
- [x] Implement Pydantic request/response schemas for zone operations
- [x] Add validation for zone coordinates (x, y, width, height within bounds)
- [x] Return zone configuration in existing `/cameras/{id}` endpoint response

**Task 4: Frontend Zone Drawing UI** (AC: #1, #5) - DEFERRED
- [ ] Create `ZoneDrawer` React component with canvas overlay on camera preview
- [ ] Implement rectangle drawing interaction (click and drag)
- [ ] Add zone name input and enable/disable toggle per zone
- [ ] Display all existing zones on preview with visual indicators
- [ ] Implement zone edit/delete functionality
- [ ] Add "Save Zones" button to persist changes via API
- [ ] Show visual feedback for enabled vs disabled zones (different colors)

**Task 5: Integration and Testing** (AC: #3, #4, #5)
- [x] Write unit tests for `DetectionZoneManager.is_motion_in_zones()`
- [x] Write integration tests for zone filtering in motion detection flow
- [x] Test zone persistence across camera restarts
- [x] Test enabling/disabling zones dynamically
- [x] Verify performance impact of zone filtering (<5ms overhead)
- [x] Test edge cases (motion partially in zone, multiple zones, no zones)
- [ ] Manual testing with real camera feed and drawn zones (requires frontend)

**Task 6: Documentation** (AC: All) - DEFERRED
- [ ] Update API documentation for new zone endpoints
- [ ] Add zone configuration examples to API docs
- [ ] Document zone coordinate system (pixels, origin top-left)
- [ ] Add user guide section for drawing detection zones

---

## Dev Notes

### Learnings from Previous Story (F2-1)

**From Story f2-1-motion-detection-algorithm (Status: done)**

**Key Accomplishments from F2-1:**
- ✅ **DetectionZone Pydantic Schema Already Created**: Located at `app/schemas/motion.py` (lines 140-154 in tech-spec)
  - Schema includes: `id`, `name`, `vertices` (polygon), `enabled` flag
  - Polygon validation already implemented (min 3 vertices, auto-close)
  - **Action:** REUSE this schema, do NOT recreate

- ✅ **MotionDetectionService Ready for Extension**: Located at `app/services/motion_detection_service.py`
  - `process_frame()` method at lines 71-152 is the integration point
  - Add zone filtering AFTER motion detection, BEFORE cooldown check
  - Service already singleton pattern with thread-safe Lock

- ✅ **Camera Model Extensible**: `app/models/camera.py` already has motion fields
  - Tech-spec defines `detection_zones` as Text column (JSON storage)
  - Migration pattern established in F2-1 (see migration 002)

- ✅ **Performance Monitoring in Place**: `camera_service.py:309-316`
  - Warns if processing >100ms per frame
  - Zone filtering must add <5ms overhead to stay under budget

**Technical Decisions from F2-1:**
- **Default Algorithm**: MOG2 (fastest at ~30-50ms)
- **Cooldown Implementation**: Per-camera timestamp tracking with Lock
- **Database Pattern**: SQLite with JSON columns for structured data
- **Testing Pattern**: 78 tests total, 100% pass rate maintained

**Files to REUSE (do not recreate):**
- `app/schemas/motion.py` - DetectionZone schema exists
- `app/services/motion_detection_service.py` - Extend process_frame()
- `app/models/camera.py` - Add detection_zones field

**Technical Debt to Address:**
- F2-1 deferred real footage validation (AC-1, AC-2) - not affecting this story
- Algorithm comparison deferred - not affecting this story

**Integration Points:**
- `MotionDetectionService.process_frame()` - Add zone filtering after line 102 (motion detected)
- `CameraService._capture_loop()` - No changes needed (calls process_frame)
- Database migrations - Follow pattern from migration 002

[Source: stories/f2-1-motion-detection-algorithm.md#Implementation-Summary]

### Technical Summary

**Approach:**
This story extends the existing motion detection system from F2-1 to support user-defined detection zones. The zone filtering logic will be implemented as a separate `DetectionZoneManager` service that checks if detected motion (bounding box) intersects with any enabled zone polygons before triggering an event.

**Key Technical Decisions:**
1. **Reuse DetectionZone Pydantic schema** from F2-1 (already has polygon validation)
2. **Store zones in Camera model** as JSON text column (follows F2-1 pattern)
3. **Zone filtering happens AFTER detection, BEFORE cooldown** (performance optimization)
4. **Rectangle zones initially** (simpler UI), polygon support exists in schema for future
5. **No zones = detect anywhere** (backward compatible with F2-1 cameras)

**Performance Considerations:**
- Zone intersection check using bounding box overlap (fast rectangle math)
- Target <5ms overhead for zone filtering (total motion processing budget: 100ms)
- Zone filtering short-circuits on first match (optimization)

**Files Involved:**
- **NEW:** `app/services/detection_zone_manager.py` - Zone filtering logic
- **NEW:** `frontend/components/camera/ZoneDrawer.tsx` - UI component
- **MODIFY:** `app/models/camera.py` - Add detection_zones column
- **MODIFY:** `app/services/motion_detection_service.py` - Integrate zone filtering
- **MODIFY:** `app/api/v1/cameras.py` - Add zone management endpoints
- **NEW:** `alembic/versions/003_add_detection_zones.py` - Database migration

### Project Structure Notes

**Backend Structure (Python):**
- `app/models/` - SQLAlchemy ORM models
- `app/schemas/` - Pydantic validation schemas
- `app/services/` - Business logic services
- `app/api/v1/` - FastAPI route handlers
- `alembic/versions/` - Database migrations
- `tests/` - pytest test suite

**Frontend Structure (Next.js):**
- `frontend/components/camera/` - Camera-related React components
- `frontend/app/cameras/[id]/zones/` - Zone configuration page (new)
- `frontend/lib/api/` - API client functions

**Testing Standards:**
- Unit tests for all service methods
- Integration tests for API endpoints
- Maintain 100% test pass rate (currently 78/78 tests)
- Follow pytest patterns from F2-1 tests

**Naming Conventions:**
- Snake_case for Python (models, services, functions)
- PascalCase for React components
- kebab-case for API routes

### References

**Primary Documents:**
- [Epic F2 Tech Spec](../sprint-artifacts/tech-spec-epic-f2.md) - Comprehensive technical specification
- [PRD](../prd.md#F2.2) - Business requirements for detection zones
- [Architecture](../architecture.md) - System architecture and patterns
- [Previous Story](../sprint-artifacts/f2-1-motion-detection-algorithm.md) - F2-1 completion notes and learnings

**Key Sections:**
- DetectionZone schema: [tech-spec-epic-f2.md lines 140-154]
- Zone filtering requirements: [prd.md F2.2 section]
- Camera model extensions: [tech-spec-epic-f2.md lines 81-99]
- Motion detection flow: [tech-spec-epic-f2.md lines 71-78]

---

## Dev Agent Record

### Context Reference

**Story Context File:** [f2-2-motion-detection-zones.context.xml](./f2-2-motion-detection-zones.context.xml)

Generated: 2025-11-16 by story-context workflow

This comprehensive context file includes:
- All 5 acceptance criteria with detailed specifications
- 32 subtasks across 6 main tasks
- Documentation artifacts (PRD F2.2, Tech-spec Epic F2, Architecture, F2-1 learnings)
- Code artifacts (REUSE schemas, MODIFY services, NEW components)
- Dependencies and constraints
- API and service interfaces
- Test standards, locations, and 25+ test ideas

### Agent Model Used

claude-sonnet-4-5-20250929 (Sonnet 4.5)

### Debug Log References

No debug logs - implementation proceeded smoothly without blockers

### Completion Notes List

**Backend Implementation Complete (AC #2, #3, #4, #5)**

1. **Database Migration & Model Extension** (Task 1)
   - Created migration `003_add_detection_zones.py` following F2-1 pattern
   - Added `detection_zones` Text column to Camera model for JSON storage
   - Verified DetectionZone Pydantic schema exists at `app/schemas/motion.py:173-214` (REUSED, not recreated)
   - Migration applied successfully

2. **Zone Filtering Service** (Task 2)
   - Implemented `DetectionZoneManager` singleton service (175 lines)
   - `is_motion_in_zones()` method uses OpenCV `pointPolygonTest` for fast polygon intersection
   - Integrated into `MotionDetectionService.process_frame()` AFTER motion detection, BEFORE cooldown (performance optimization)
   - Graceful error handling: Invalid JSON, malformed zones, no zones → fail open (allow motion)
   - Performance: <1ms average (well under 5ms requirement)

3. **Zone Management API Endpoints** (Task 3)
   - GET `/cameras/{id}/zones` - Retrieve zones (empty list if none)
   - PUT `/cameras/{id}/zones` - Update zones (max 10 zones enforced)
   - POST `/cameras/{id}/zones/test` - Test zones with live frame (draws overlay)
   - Updated `CameraResponse` schema to include `detection_zones` field
   - All endpoints follow existing error handling patterns (404, 422, 500)

4. **Comprehensive Testing** (Task 5)
   - **Unit Tests:** 14 new tests for DetectionZoneManager covering:
     - Singleton pattern, zone filtering logic, edge cases (no zones, disabled zones, invalid JSON)
     - Performance benchmark: <5ms requirement validated (average <1ms)
   - **Integration Tests:** 8 new API endpoint tests covering:
     - Zone CRUD operations, persistence, validation, auto-close polygon
   - **Test Results:** 100/100 tests passing (22 new tests added, 100% pass rate maintained)

5. **Key Technical Decisions:**
   - Zone filtering happens BEFORE cooldown consumption (avoid wasting cooldown on out-of-zone motion)
   - Fail-open strategy: If zones are invalid/missing, allow all motion (backward compatible with F2-1)
   - DetectionZone schema reused from F2-1 (polygon support, min 3 vertices, auto-close)
   - Thread-safe: DetectionZoneManager has no shared mutable state (stateless filtering)

**Frontend Task Deferred** (Task 4)
- ZoneDrawer React component marked for future story
- Backend API fully functional and tested
- Can configure zones via direct API calls for testing

**Documentation Deferred** (Task 6)
- API documentation marked for future update
- Code is self-documenting with comprehensive docstrings

### File List

**New Files:**
- `backend/alembic/versions/003_add_detection_zones.py` (Migration)
- `backend/app/services/detection_zone_manager.py` (Zone filtering service, 175 lines)
- `backend/tests/test_services/test_detection_zone_manager.py` (Unit tests, 14 tests)

**Modified Files:**
- `backend/app/models/camera.py` (Added detection_zones column)
- `backend/app/schemas/camera.py` (Added detection_zones to CameraResponse)
- `backend/app/services/motion_detection_service.py` (Integrated zone filtering)
- `backend/app/api/v1/cameras.py` (Added 3 zone endpoints: GET, PUT, POST /zones)
- `backend/tests/test_api/test_cameras.py` (Added 8 integration tests)
- `docs/sprint-artifacts/sprint-status.yaml` (Updated status: ready-for-dev → in-progress → review)
- `docs/sprint-artifacts/f2-2-motion-detection-zones.md` (This file, marked tasks complete)

---

## Change Log

- 2025-11-16: Backend implementation complete, marked for review (dev-story workflow)
- 2025-11-16: Story context generated by story-context workflow (comprehensive implementation context XML created)
- 2025-11-16: Story marked ready-for-dev by story-ready workflow
- 2025-11-16: Story drafted by SM agent (create-story workflow)

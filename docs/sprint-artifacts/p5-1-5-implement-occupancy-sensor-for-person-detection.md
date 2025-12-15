# Story P5-1.5: Implement Occupancy Sensor for Person Detection

**Epic:** P5-1 Native HomeKit Integration
**Status:** done
**Created:** 2025-12-14
**Story Key:** p5-1-5-implement-occupancy-sensor-for-person-detection

---

## User Story

**As a** HomeKit user with Apple Home app,
**I want** occupancy sensors that only activate when my ArgusAI cameras detect a person (not just any motion),
**So that** I can create HomeKit automations specifically for human presence (e.g., "turn on lights when person detected" vs motion from animals or vehicles).

---

## Background & Context

This story implements a new HomeKit OccupancySensor accessory class that is distinct from the existing MotionSensor. While motion sensors trigger on any detection event (motion, vehicle, animal, package), occupancy sensors specifically respond only to person detection events, providing more precise automation triggers for human presence scenarios.

**Key Difference from Motion Sensors:**
- Motion Sensor: Any motion/detection event triggers, 30-second reset
- Occupancy Sensor: Person detection only, 5-minute timeout (configurable)

**What exists (from P4-6.1/P4-6.2/P5-1.4):**
- `homekit_accessories.py` - CameraMotionSensor class
- `homekit_service.py` - trigger_motion() with auto-reset timer infrastructure
- `event_processor.py` - Smart detection type extraction from events

**What this story adds:**
1. `CameraOccupancySensor` class in `homekit_accessories.py`
2. `trigger_occupancy()` method in `homekit_service.py` with 5-minute timeout
3. Occupancy sensor accessory creation in bridge startup
4. Event routing: person events -> occupancy sensor (in addition to motion)
5. Tests for occupancy sensor functionality

**PRD Reference:** docs/PRD-phase5.md (FR6)
**Tech Spec Reference:** docs/sprint-artifacts/tech-spec-epic-p5-1.md (P5-1.5-1 through P5-1.5-4)

---

## Acceptance Criteria

### AC1: Occupancy Sensor Separate from Motion Sensor
- [x] New `CameraOccupancySensor` class created in `homekit_accessories.py`
- [x] Uses HAP-python OccupancySensor service (not MotionSensor)
- [x] Each camera has separate occupancy sensor accessory alongside motion sensor
- [x] Occupancy sensor named "{camera_name} Occupancy" to distinguish from motion sensor

### AC2: Only Triggers on Person Detection Events
- [x] `trigger_occupancy()` method only called when `smart_detection_type == 'person'`
- [x] Vehicle, animal, package, motion events do NOT trigger occupancy sensor
- [x] Motion sensor still triggers on all event types (unchanged behavior)
- [x] Event routing logic in homekit_service properly filters by detection type

### AC3: Occupancy State Has 5-Minute Timeout Before Reset
- [x] Occupancy sensor state persists for 5 minutes (300 seconds) after last person detection
- [x] Timeout configurable via `HOMEKIT_OCCUPANCY_TIMEOUT_SECONDS` environment variable
- [x] Rapid person detections extend the 5-minute window (reset timer on each detection)
- [x] Max occupancy duration enforced to prevent stuck state (default 30 minutes)

### AC4: Distinct Icon in Home App
- [x] OccupancySensor service used (HAP-python automatically uses correct icon)
- [x] Occupancy sensor shows "Occupied" vs "Not Occupied" state in Home app
- [x] Visual differentiation clear between motion and occupancy sensors

---

## Tasks / Subtasks

### Task 1: Create CameraOccupancySensor Class (AC: 1, 4)
**File:** `backend/app/services/homekit_accessories.py`
- [x] Create `CameraOccupancySensor` class based on `CameraMotionSensor` pattern
- [x] Use HAP-python `OccupancySensor` service instead of `MotionSensor`
- [x] Configure `OccupancyDetected` characteristic (boolean)
- [x] Add `set_occupancy()`, `trigger_occupancy()`, `clear_occupancy()` methods
- [x] Add `create_occupancy_sensor()` factory function

### Task 2: Add Occupancy Configuration Options (AC: 3)
**File:** `backend/app/config/homekit.py`
- [x] Add `DEFAULT_OCCUPANCY_TIMEOUT_SECONDS = 300` constant (5 minutes)
- [x] Add `DEFAULT_MAX_OCCUPANCY_DURATION = 1800` constant (30 minutes)
- [x] Add `occupancy_timeout_seconds` to `HomekitConfig` dataclass
- [x] Add `max_occupancy_duration` to `HomekitConfig` dataclass
- [x] Load from environment variables `HOMEKIT_OCCUPANCY_TIMEOUT_SECONDS`, `HOMEKIT_MAX_OCCUPANCY_DURATION`

### Task 3: Implement trigger_occupancy() in HomeKit Service (AC: 2, 3)
**File:** `backend/app/services/homekit_service.py`
- [x] Add `_occupancy_sensors: Dict[str, CameraOccupancySensor]` storage
- [x] Add `_occupancy_reset_tasks: Dict[str, asyncio.Task]` for reset timers
- [x] Add `_occupancy_start_times: Dict[str, float]` for duration tracking
- [x] Implement `trigger_occupancy(camera_id, event_id)` method with 5-minute timer
- [x] Add `_start_occupancy_reset_timer()` and `_cancel_occupancy_reset_timer()` methods
- [x] Add `_occupancy_reset_coroutine()` for async timer
- [x] Add `clear_all_occupancy()` method
- [x] Update `stop()` to cancel occupancy timers and clear state

### Task 4: Create Occupancy Sensors in Bridge Startup (AC: 1)
**File:** `backend/app/services/homekit_service.py`
- [x] In `start()` method, create occupancy sensor for each camera
- [x] Use name pattern: `f"{camera_name} Occupancy"`
- [x] Add occupancy sensor to bridge: `self._bridge.add_accessory()`
- [x] Update `occupancy_count` in `HomekitStatus` dataclass
- [x] Update `get_status()` to include occupancy sensor count

### Task 5: Integrate with Event Processor (AC: 2)
**File:** `backend/app/services/event_processor.py`
- [x] Add `trigger_homekit_occupancy()` call when `smart_detection_type == 'person'`
- [x] Motion sensor continues to trigger on all detection types
- [x] Add async fire-and-forget pattern for occupancy trigger (same as motion)
- [x] Add logging for occupancy triggers

### Task 6: Write Unit Tests (AC: 1, 2, 3, 4)
**File:** `backend/tests/test_services/test_homekit_occupancy.py`
- [x] Test `CameraOccupancySensor` class creation
- [x] Test `trigger_occupancy()` sets sensor state
- [x] Test person detection triggers occupancy sensor
- [x] Test non-person events do NOT trigger occupancy sensor
- [x] Test 5-minute timeout resets state
- [x] Test rapid detections extend timeout
- [x] Test max occupancy duration enforcement
- [x] Test unknown camera returns False
- [x] Test event processor integration

---

## Dev Notes

### HAP-python OccupancySensor Service

The OccupancySensor service in HAP uses the `OccupancyDetected` characteristic:
- Type: `bool` (0 = Not Occupied, 1 = Occupied)
- Service UUID: `0086` (OccupancySensor)

```python
# Example implementation pattern
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR

class CameraOccupancySensor:
    def __init__(self, driver, camera_id: str, name: str):
        self._accessory = Accessory(driver, name)
        self._accessory.category = CATEGORY_SENSOR

        # Add OccupancySensor service (preloaded in HAP-python)
        self._occupancy_service = self._accessory.add_preload_service("OccupancySensor")
        self._occupancy_char = self._occupancy_service.configure_char(
            "OccupancyDetected",
            value=0  # 0 = Not Occupied
        )

    def trigger_occupancy(self):
        self._occupancy_char.set_value(1)  # 1 = Occupied

    def clear_occupancy(self):
        self._occupancy_char.set_value(0)  # 0 = Not Occupied
```

### Event Routing Logic

The event processor should route events as follows:
```
Event Created
    │
    ├─> trigger_motion() [always, for any detection]
    │
    └─> smart_detection_type == 'person'?
            │
            └─> Yes: trigger_occupancy() [5-minute timeout]
```

### Configuration Options (Environment Variables)

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| occupancy_timeout_seconds | 300 | HOMEKIT_OCCUPANCY_TIMEOUT_SECONDS | Seconds before occupancy resets |
| max_occupancy_duration | 1800 | HOMEKIT_MAX_OCCUPANCY_DURATION | Max continuous occupancy before forced reset |

### Learnings from Previous Story

**From Story P5-1.4 (Status: done)**

- **Validation Story Pattern**: P5-1.4 was primarily validation of P4-6.1/P4-6.2 work
- **CameraMotionSensor class**: Follow same pattern for CameraOccupancySensor
- **Auto-reset timer infrastructure**: Reuse pattern from motion reset timers
- **Fire-and-forget async pattern**: Use `asyncio.create_task()` for non-blocking triggers
- **Configuration via environment variables**: Follow same pattern for occupancy config
- **Test structure**: Follow `test_homekit_motion.py` as template for occupancy tests

[Source: docs/sprint-artifacts/p5-1-4-implement-motion-sensor-accessories.md#Dev-Agent-Record]

### Project Structure Notes

- New class `CameraOccupancySensor` goes in existing `homekit_accessories.py`
- Configuration additions go in existing `app/config/homekit.py`
- New test file `test_homekit_occupancy.py` in `backend/tests/test_services/`
- Event processor integration follows existing HomeKit motion pattern

### References

- HAP-python OccupancySensor: https://github.com/ikalchev/HAP-python
- Tech spec: `docs/sprint-artifacts/tech-spec-epic-p5-1.md` (P5-1.5 section)
- Motion sensor implementation: `backend/app/services/homekit_accessories.py`
- Motion trigger implementation: `backend/app/services/homekit_service.py:734-873`
- Event processor: `backend/app/services/event_processor.py:1036-1045`

---

## Dev Agent Record

### Context Reference

- [docs/sprint-artifacts/p5-1-5-implement-occupancy-sensor-for-person-detection.context.xml](p5-1-5-implement-occupancy-sensor-for-person-detection.context.xml)

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 19 occupancy tests pass (test_homekit_occupancy.py)
- All 17 motion tests pass (test_homekit_motion.py) - no regressions

### Completion Notes List

1. **CameraOccupancySensor class** - Created in `homekit_accessories.py` following CameraMotionSensor pattern
   - Uses HAP-python OccupancySensor service
   - OccupancyDetected characteristic set to 0/1 integer (vs boolean for motion)
   - Factory function `create_occupancy_sensor()` provided

2. **Configuration** - Added to `homekit.py`:
   - DEFAULT_OCCUPANCY_TIMEOUT_SECONDS = 300 (5 minutes)
   - DEFAULT_MAX_OCCUPANCY_DURATION = 1800 (30 minutes)
   - Environment variable loading for both settings

3. **trigger_occupancy() method** - Implemented in `homekit_service.py:734-793`:
   - Resolves camera ID through mapping (supports MAC addresses)
   - 5-minute auto-reset timer with `_occupancy_reset_coroutine()`
   - Max occupancy duration check to prevent stuck state
   - Rapid detections extend timeout (timer reset on each trigger)

4. **Bridge Startup Integration** - Occupancy sensors created at `homekit_service.py:346-357`:
   - Each camera gets both motion AND occupancy sensor
   - Naming pattern: "{camera_name} Occupancy"
   - Added to bridge accessory list
   - `occupancy_count` property added to HomekitStatus

5. **Event Processor Integration** - Added at `event_processor.py:1036-1045`:
   - Only triggers when `smart_detection_type == 'person'`
   - Motion sensor continues to trigger for all events
   - Fire-and-forget async pattern (non-blocking)

6. **Test Suite** - Created `test_homekit_occupancy.py` with 19 tests:
   - TestHomekitOccupancyTrigger (10 tests)
   - TestHomekitOccupancyEventFiltering (2 tests)
   - TestHomekitOccupancyConfig (4 tests)
   - TestCameraOccupancySensorClass (3 tests)

### File List

**NEW Files:**
- `backend/tests/test_services/test_homekit_occupancy.py` - 19 unit tests for occupancy sensor

**MODIFIED Files:**
- `backend/app/services/homekit_accessories.py` - Added CameraOccupancySensor class and factory
- `backend/app/config/homekit.py` - Added occupancy timeout constants and config fields
- `backend/app/services/homekit_service.py` - Added trigger_occupancy() and related methods
- `backend/app/services/event_processor.py` - Added occupancy trigger on person detection

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-14 | SM Agent (Claude Opus 4.5) | Initial story creation |
| 2025-12-14 | Dev Agent (Claude Opus 4.5) | Implementation complete - all 6 tasks done, 19 tests passing |

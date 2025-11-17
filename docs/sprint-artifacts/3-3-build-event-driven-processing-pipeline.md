# Story 3.3: Build Event-Driven Processing Pipeline

Status: drafted

## Story

As a **backend developer**,
I want **an asynchronous event processing pipeline from motion detection to storage**,
so that **the system handles events efficiently without blocking**.

## Acceptance Criteria

1. **Pipeline Architecture** - Async queue-based architecture
   - Use `asyncio.Queue` for event queue (maxsize=50)
   - Separate async tasks for each enabled camera
   - Background worker pool for AI processing (configurable 2-5 workers, default 2)
   - Non-blocking database operations
   - Graceful shutdown with queue draining (30s timeout)

2. **Motion Detection Task** - Continuous camera monitoring per camera
   - Runs continuously for each enabled camera
   - Checks for motion every frame (5-10 FPS based on camera.frame_rate)
   - On motion detected → Capture best frame → Add to processing queue
   - Enforce cooldown (use camera.motion_cooldown, no new events during cooldown)
   - Gracefully handle camera disconnections with retry logic

3. **AI Processing Worker Pool** - Parallel event processing
   - Configurable number of workers (environment variable, default: 2, max: 5)
   - Workers pull events from queue FIFO
   - Each worker processes one event at a time
   - Parallel processing: Multiple events processed simultaneously
   - Queue overflow handling: Drop oldest events if queue full (log warning)

4. **Processing Flow** - Complete event lifecycle
   ```
   Motion detected → Frame captured → Event queued →
   Worker picks event → AI API call → Description received →
   Event stored in database → Alert rules evaluated (Epic 5, stub for now) →
   WebSocket broadcast (Epic 4, stub for now) → Worker ready for next
   ```
   - Integration with Story 3.1 AI Service (`ai_service.generate_description()`)
   - Integration with Story 3.2 Event API (`POST /api/v1/events`)
   - End-to-end latency: <5 seconds (motion → stored event)

5. **Error Handling and Resilience** - Robust failure recovery
   - AI API failures → Handled by Story 3.1 fallback chain
   - Database failures → Log error, retry up to 3 times with exponential backoff
   - Queue overflow → Drop oldest events, log warning with event details
   - Worker crashes → Automatically restart worker (asyncio exception handling)
   - Camera disconnects → Pause processing, log disconnect, resume on reconnect

6. **Monitoring and Metrics** - Operational visibility
   - Track queue depth (current events waiting in queue)
   - Track processing time per event (p50, p95, p99 percentiles)
   - Track success/failure rates (events processed vs failed)
   - Expose metrics via `GET /api/v1/metrics` endpoint
   - Metrics format: JSON with counters and gauges
   - Log all pipeline stages with structured logging

7. **Performance Targets** - Meet architecture SLAs
   - End-to-end latency: <5 seconds p95 (motion detection → stored event)
   - Throughput: Process 10+ events per minute
   - Queue depth: Typically <5 events under normal load
   - CPU usage: <50% on 2-core system (per architecture.md)
   - Memory usage: <1GB for event processing pipeline
   - Graceful shutdown: Complete in-flight events within 30s timeout

## Tasks / Subtasks

**Task 1: Create Event Processor Service** (AC: #1, #4)
- [ ] Create `/backend/app/services/event_processor.py`
- [ ] Implement `EventProcessor` class with asyncio.Queue (maxsize=50)
- [ ] Create `ProcessingEvent` dataclass (camera_id, frame, timestamp, metadata)
- [ ] Implement `start()` method to initialize pipeline
- [ ] Implement `stop()` method for graceful shutdown (drain queue, 30s timeout)
- [ ] Add structured logging for all pipeline stages

**Task 2: Implement Motion Detection Tasks** (AC: #2)
- [ ] Create `MotionDetectionTask` class in event_processor.py
- [ ] Implement continuous frame capture loop (async while True)
- [ ] Integrate with camera service from Epic 2 (camera.frame_rate for FPS)
- [ ] On motion detected → Capture frame → Create ProcessingEvent → Queue.put()
- [ ] Implement cooldown enforcement using camera.motion_cooldown setting
- [ ] Handle camera disconnections with retry logic (log disconnect, retry after 10s)
- [ ] Create one task per enabled camera using asyncio.create_task()

**Task 3: Implement AI Worker Pool** (AC: #3, #4)
- [ ] Create `AIWorker` class for processing events from queue
- [ ] Implement worker loop: Queue.get() → Process → Mark done
- [ ] Integrate Story 3.1 AI Service:
  - [ ] Call `ai_service.generate_description(frame, camera_name, timestamp, detected_objects)`
  - [ ] Handle AIResult response
- [ ] Integrate Story 3.2 Event API:
  - [ ] Build EventCreate payload from AIResult
  - [ ] POST to `/api/v1/events` endpoint (use httpx async client)
  - [ ] Handle response (201 Created or error)
- [ ] Create configurable worker pool (default 2 workers)
- [ ] Add worker restart on exception (catch, log, restart)

**Task 4: Implement Error Handling** (AC: #5)
- [ ] Database retry logic with exponential backoff (2s, 4s, 8s delays)
- [ ] Queue overflow handling (drop oldest, log warning with event metadata)
- [ ] Worker exception handling (log traceback, restart worker)
- [ ] Camera disconnect handling (pause task, log, retry on reconnect)
- [ ] AI API errors already handled by Story 3.1 fallback chain

**Task 5: Implement Metrics and Monitoring** (AC: #6)
- [ ] Create metrics tracking in EventProcessor:
  - [ ] queue_depth: Current queue size
  - [ ] events_processed: Counter (success/failure breakdown)
  - [ ] processing_time_ms: Histogram (p50, p95, p99)
  - [ ] pipeline_errors: Counter by error type
- [ ] Create `GET /api/v1/metrics` endpoint
- [ ] Return JSON metrics response
- [ ] Add structured logging for all pipeline events:
  - [ ] Motion detected (camera_id, timestamp)
  - [ ] Event queued (queue_depth)
  - [ ] Worker started processing (event_id)
  - [ ] AI call completed (response_time, provider)
  - [ ] Event stored (event_id, total_time)
  - [ ] Errors (stage, error_type, details)

**Task 6: Integrate with FastAPI Lifespan** (AC: #1, #7)
- [ ] Modify `backend/main.py` to add lifespan context manager
- [ ] Initialize EventProcessor on startup
- [ ] Start camera tasks for all enabled cameras
- [ ] Start AI worker pool
- [ ] Register shutdown handler for graceful stop
- [ ] Ensure 30s shutdown timeout with queue draining

**Task 7: Testing** (AC: All)
- [ ] Unit tests for EventProcessor class:
  - [ ] Test queue overflow behavior
  - [ ] Test worker pool creation
  - [ ] Test graceful shutdown
- [ ] Integration tests:
  - [ ] Mock camera motion → Queue → Worker → DB flow
  - [ ] Test with Story 3.1 AI Service (mocked)
  - [ ] Test with Story 3.2 Event API (real)
  - [ ] Test error scenarios (AI fail, DB fail, queue overflow)
- [ ] Performance tests:
  - [ ] Measure end-to-end latency (<5s target)
  - [ ] Test throughput (10+ events/min)
  - [ ] Test queue depth under load
- [ ] Manual testing:
  - [ ] Test with real camera connected
  - [ ] Generate motion events
  - [ ] Verify events appear in database
  - [ ] Check metrics endpoint
  - [ ] Test graceful shutdown

## Dev Notes

### Architecture Context

From `docs/architecture.md`:
- **Event-Driven Architecture** (ADR-001): Asynchronous processing triggered by motion detection
- **Background Tasks** (ADR-004): Use FastAPI BackgroundTasks pattern, not Celery/Redis for MVP
- **Performance Target**: <5s end-to-end latency (p95) from motion to stored event
- **Concurrency**: Asyncio-based, not threading - use `async/await` throughout
- **Queue Decision**: `asyncio.Queue` sufficient for single-server MVP, Redis deferred to Phase 2

### Learnings from Previous Stories

**From Story 3.2: Event Storage (Status: done)**

**Integration Points Ready:**
- **Event Creation API**: `POST /api/v1/events` at `backend/app/api/v1/events.py:80`
  - Accepts `EventCreate` schema with validation
  - Returns 201 Created with full event object
  - Response time <100ms verified
  - 40 tests passing (16 model + 24 API)

**Schema to Use:**
```python
from app.schemas.event import EventCreate

event_data = EventCreate(
    camera_id=camera.id,  # UUID string
    timestamp=datetime.now(timezone.utc),  # ISO 8601
    description=ai_result.description,  # From Story 3.1
    confidence=ai_result.confidence,  # 0-100
    objects_detected=ai_result.objects_detected,  # List[str]
    thumbnail_base64=thumbnail_base64,  # Optional base64 JPEG
    alert_triggered=False  # Epic 5 feature, default False for now
)
```

**Database Schema:**
- Events table with 10 columns, 6 indexes, FTS5 full-text search
- Foreign key to cameras.id with CASCADE delete
- CHECK constraint on confidence (0-100)
- Thumbnail storage at `data/thumbnails/{YYYY-MM-DD}/event_{uuid}.jpg`

**Files to Import:**
- `backend/app/schemas/event.py` - EventCreate, EventResponse schemas
- `backend/app/api/v1/events.py` - Events router (already registered in main.py)

[Source: docs/sprint-artifacts/3-2-implement-event-storage-and-retrieval-system.md#Completion-Notes-List]

---

**From Story 3.1: AI Vision API (Status: done)**

**AI Service Ready:**
- **Service Location**: `backend/app/services/ai_service.py:515`
- **Method**: `async generate_description(frame, camera_name, timestamp, detected_objects, sla_timeout_ms=5000) -> AIResult`
- **Returns**: AIResult with description, confidence, objects_detected, provider, tokens_used, response_time_ms, cost_estimate
- **Multi-Provider**: OpenAI → Claude → Gemini fallback chain
- **SLA Enforced**: <5s timeout with explicit tracking
- **Encryption**: Loads API keys from database with Fernet decryption
- **Usage Tracking**: Persists to ai_usage table

**Integration Example:**
```python
from app.services.ai_service import AIService

ai_service = AIService()
ai_service.load_api_keys_from_db(db)  # Load encrypted keys

result = await ai_service.generate_description(
    frame=frame,  # numpy array BGR
    camera_name=camera.name,
    timestamp=timestamp.isoformat(),
    detected_objects=["unknown"]  # From motion detection
)

# result.description - Natural language description
# result.confidence - 0-100 score
# result.objects_detected - Detected object types
# result.success - True if successful
```

**Performance:**
- 18 AI service tests passing
- <5s SLA enforced with timeout tracking
- Handles API failures with automatic fallback

**Files to Import:**
- `backend/app/services/ai_service.py` - AIService class
- Already integrated with encryption and database tracking

[Source: docs/sprint-artifacts/3-1-integrate-ai-vision-api-for-description-generation.md#File-List]

### Technical Implementation Notes

**Expected File Structure:**
```
backend/app/
├── services/
│   ├── ai_service.py           # EXISTS (Story 3.1) - import AIService
│   ├── event_processor.py      # NEW - This story
│   └── camera_service.py       # EXISTS (Epic 2) - camera management
├── api/v1/
│   ├── events.py               # EXISTS (Story 3.2) - POST /events endpoint
│   └── metrics.py              # NEW - This story
└── core/
    └── lifespan.py             # NEW - FastAPI lifespan management
```

**Asyncio Patterns:**
- Use `asyncio.create_task()` for concurrent camera tasks
- Use `asyncio.Queue(maxsize=50)` for event queue
- Worker pattern: `async while True: event = await queue.get()`
- Graceful shutdown: `asyncio.gather(*tasks, return_exceptions=True)`
- Exception handling: `try/except` in workers, restart on failure

**Database Operations:**
- Use httpx AsyncClient for non-blocking POST to `/api/v1/events`
- Alternative: Direct database session (async SQLAlchemy) - prefer API for consistency
- Retry logic: exponential backoff (2s, 4s, 8s) for transient errors

**Logging Strategy:**
- Structured logging with JSON format
- Include: timestamp, camera_id, event_id, stage, duration_ms, error_type
- Log levels: DEBUG (queue operations), INFO (events processed), WARNING (queue overflow), ERROR (failures)
- Per architecture.md: All logs go to backend/data/logs/

**Performance Considerations:**
- Queue size = 50 events → Prevents memory overflow during AI API slowdowns
- Worker count = 2 default → Balance between throughput and resource usage
- Cooldown enforcement → Prevents duplicate events from same motion
- Frame capture → Use best frame from motion detection window (Epic 2)

### Testing Strategy

From `docs/test-design-system.md` (inferred):
- **Unit Tests**: EventProcessor, MotionDetectionTask, AIWorker classes
- **Integration Tests**: Mock camera → Real queue → Mocked AI → Real DB
- **E2E Tests**: Simulated motion → Full pipeline → Verify event in database
- **Performance Tests**: Measure latency with 50+ events, verify <5s p95
- **Load Tests**: 10+ events/minute sustained, verify queue doesn't overflow

**Test Scenarios:**
1. Happy path: Motion → AI → Storage → Success
2. Queue overflow: 51st event drops oldest, logs warning
3. AI failure: Fallback chain works (tested in Story 3.1)
4. Database failure: Retry 3x with backoff
5. Worker crash: Exception caught, worker restarts
6. Graceful shutdown: In-flight events complete, queue drains within 30s

### Prerequisites

- ✅ Story 3.1: AI Vision API integration complete
- ✅ Story 3.2: Event storage and retrieval system complete
- ⚠️ Epic 2: Camera service and motion detection (assumed functional)
- ⏳ Epic 4: WebSocket broadcast (stub for now, implement in Epic 4)
- ⏳ Epic 5: Alert rule evaluation (stub for now, implement in Epic 5)

### References

- [Architecture: Event-Driven Architecture](docs/architecture.md#Event-Driven-Architecture)
- [Architecture: ADR-004 FastAPI BackgroundTasks](docs/architecture.md#ADR-004-FastAPI-BackgroundTasks-vs-External-Queue)
- [Architecture: Performance Targets](docs/architecture.md#Performance-Targets)
- [Epic 3 Story 3.3: Build Event-Driven Processing Pipeline](docs/epics.md#Story-3.3-Build-Event-Driven-Processing-Pipeline)
- [Story 3.1: AI Vision API Integration](docs/sprint-artifacts/3-1-integrate-ai-vision-api-for-description-generation.md)
- [Story 3.2: Event Storage and Retrieval System](docs/sprint-artifacts/3-2-implement-event-storage-and-retrieval-system.md)

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

<!-- Will be filled by dev agent -->

### Debug Log References

<!-- Dev agent will log implementation notes here -->

### Completion Notes List

<!-- Dev agent will document:
- Event processor service created
- Integration with Stories 3.1 and 3.2
- Performance metrics achieved
- Queue behavior under load
- Challenges encountered
-->

### File List

<!-- Dev agent will list:
- NEW: backend/app/services/event_processor.py
- NEW: backend/app/api/v1/metrics.py
- NEW: backend/tests/test_services/test_event_processor.py
- NEW: backend/tests/test_integration/test_pipeline.py
- MODIFIED: backend/main.py (lifespan management)
-->

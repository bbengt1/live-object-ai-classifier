# Story P4-3.3: Recurring Visitor Detection

Status: done

## Story

As a **home security system user**,
I want **the system to automatically recognize and track recurring visitors based on visual similarity**,
so that **I can see when the same person or vehicle has been seen before, with information like "first seen", "last seen", and visit count**.

## Acceptance Criteria

| # | Criteria | Verification |
|---|----------|--------------|
| 1 | System clusters similar event embeddings to identify recurring entities | Integration test with multiple events from same visitor |
| 2 | RecognizedEntity model stores: entity_type, name (nullable), reference_embedding, first_seen_at, last_seen_at, occurrence_count | Model test verifies all fields |
| 3 | EntityEvent junction table links entities to their associated events with similarity scores | Database schema test |
| 4 | `EntityService.match_or_create_entity(event_id, embedding, threshold=0.75)` returns existing entity or creates new one | Unit test with mock embeddings |
| 5 | When new event embedding matches existing entity above threshold, entity is updated: occurrence_count++, last_seen_at updated | Integration test with sequential events |
| 6 | When no existing entity matches above threshold, new entity created with event as first occurrence | Test with isolated/new visitor |
| 7 | API endpoint `GET /api/v1/entities` returns list of all recognized entities with occurrence stats | API test returns proper JSON |
| 8 | API endpoint `GET /api/v1/entities/{id}` returns single entity with all associated events | API test with entity details |
| 9 | API endpoint `PUT /api/v1/entities/{id}` allows naming an entity (e.g., "Mail Carrier") | API test for entity naming |
| 10 | API endpoint `DELETE /api/v1/entities/{id}` removes entity and unlinks associated events | API test for deletion |
| 11 | Entity matching integrated into event processing pipeline (after embedding generation) | Integration test with full pipeline |
| 12 | Entity match results included in event response as `matched_entity: { id, name, occurrence_count, first_seen_at }` | Event API response includes entity data |
| 13 | Performance: Entity matching completes in <200ms with up to 1000 entities | Performance benchmark test |
| 14 | Graceful handling when embedding service unavailable (don't block event processing) | Test with unavailable service |

## Tasks / Subtasks

- [x] **Task 1: Create RecognizedEntity database model** (AC: 2)
  - [x] Create `backend/app/models/recognized_entity.py`
  - [x] Define fields: id (UUID), entity_type (TEXT), name (TEXT nullable), reference_embedding (TEXT - JSON array), first_seen_at, last_seen_at, occurrence_count
  - [x] Add model to `backend/app/models/__init__.py`
  - [x] Create Alembic migration for recognized_entities table

- [x] **Task 2: Create EntityEvent junction model** (AC: 3)
  - [x] Add EntityEvent model to store entity-event relationships
  - [x] Fields: entity_id, event_id (composite PK), similarity_score (FLOAT), created_at
  - [x] Add foreign key constraints to entities and events tables
  - [x] Include in same Alembic migration

- [x] **Task 3: Implement EntityService core methods** (AC: 1, 4, 5, 6)
  - [x] Create `backend/app/services/entity_service.py`
  - [x] Implement `match_or_create_entity(db, event_id, embedding, entity_type='unknown', threshold=0.75)`
  - [x] Load all existing entity reference embeddings
  - [x] Use SimilarityService.batch_cosine_similarity for efficient matching
  - [x] If match found: update occurrence_count and last_seen_at, create EntityEvent link
  - [x] If no match: create new RecognizedEntity, link event
  - [x] Return matched/created entity with similarity score

- [x] **Task 4: Implement entity CRUD operations** (AC: 7, 8, 9, 10)
  - [x] Add `get_all_entities(db, limit, offset)` method
  - [x] Add `get_entity(db, entity_id)` with associated events
  - [x] Add `update_entity(db, entity_id, name)` for naming
  - [x] Add `delete_entity(db, entity_id)` with cascade to EntityEvent
  - [x] Add `get_entity_events(db, entity_id, limit)` for event history

- [x] **Task 5: Create entity API endpoints** (AC: 7, 8, 9, 10)
  - [x] Add routes to `backend/app/api/v1/context.py` (or new `entities.py`)
  - [x] `GET /api/v1/entities` - list entities with pagination
  - [x] `GET /api/v1/entities/{id}` - entity detail with recent events
  - [x] `PUT /api/v1/entities/{id}` - update entity name
  - [x] `DELETE /api/v1/entities/{id}` - delete entity
  - [x] Define Pydantic schemas: EntityResponse, EntityListResponse, EntityUpdateRequest

- [x] **Task 6: Integrate entity matching into event pipeline** (AC: 11, 12)
  - [x] Modify `event_processor.py` to call entity matching after embedding generation
  - [x] Add entity match results to Event model (matched_entity_id field)
  - [x] Include entity data in event API responses
  - [x] Handle errors gracefully - don't block event processing

- [x] **Task 7: Optimize performance** (AC: 13)
  - [x] Cache entity embeddings in memory (invalidate on new entity creation)
  - [x] Use batch similarity calculation for all entities
  - [x] Add timing instrumentation for entity matching
  - [x] Profile with 1000 entities to verify <200ms target

- [x] **Task 8: Handle edge cases and errors** (AC: 14)
  - [x] Graceful fallback if embedding service fails
  - [x] Handle empty entity database (first visitor)
  - [x] Handle duplicate events (idempotency)
  - [x] Log warnings for slow operations

- [x] **Task 9: Write unit tests** (AC: 2, 4, 5, 6)
  - [x] Test RecognizedEntity model creation and validation
  - [x] Test EntityEvent model and relationships
  - [x] Test match_or_create_entity with mock embeddings
  - [x] Test entity update (occurrence increment)
  - [x] Test new entity creation
  - [x] Test threshold filtering
  - [x] Test performance: 1000 entities in <200ms (25 tests passing)

- [x] **Task 10: Write integration tests** (AC: 1, 3, 5, 11)
  - [x] Test entity clustering with real database
  - [x] Test sequential events from same visitor
  - [x] Test pipeline integration end-to-end
  - [x] Test entity deletion cascade (10 tests passing)

- [x] **Task 11: Write API tests** (AC: 7, 8, 9, 10, 12)
  - [x] Test GET /api/v1/entities endpoint
  - [x] Test GET /api/v1/entities/{id} endpoint
  - [x] Test PUT /api/v1/entities/{id} endpoint
  - [x] Test DELETE /api/v1/entities/{id} endpoint
  - [x] Test event response includes entity data (13 tests passing)

## Dev Notes

### Architecture Alignment

This story implements the third component of the Temporal Context Engine (Epic P4-3). It builds on EmbeddingService (P4-3.1) and SimilarityService (P4-3.2) to identify and track recurring visitors across events.

**Component Flow:**
```
New Event → EmbeddingService (P4-3.1) → EntityService (this story)
                                               ↓
                                    Load all entity reference embeddings
                                               ↓
                                    Batch cosine similarity (P4-3.2)
                                               ↓
                               ┌───────────────┴───────────────┐
                               │                               │
                    Match found (>=0.75)            No match (<0.75)
                               │                               │
                    Update existing entity          Create new entity
                    - increment count               - set reference embedding
                    - update last_seen_at           - set first_seen_at
                               │                               │
                               └───────────────┬───────────────┘
                                               ↓
                                    Create EntityEvent link
                                               ↓
                                    Return entity + score
```

**Architecture Decision:**
- Entity reference embedding = first event's embedding (simplest approach)
- Future enhancement: average embedding across multiple sightings for better accuracy
- Threshold 0.75 chosen as balance between false positives/negatives (configurable)

### Key Implementation Details

**RecognizedEntity Model:**
```python
class RecognizedEntity(Base):
    __tablename__ = "recognized_entities"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(Text, nullable=False, default="unknown")  # 'person', 'vehicle', 'unknown'
    name = Column(Text, nullable=True)  # User-assigned name
    reference_embedding = Column(Text, nullable=False)  # JSON array
    first_seen_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    occurrence_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**EntityEvent Junction:**
```python
class EntityEvent(Base):
    __tablename__ = "entity_events"

    entity_id = Column(Text, ForeignKey("recognized_entities.id", ondelete="CASCADE"), primary_key=True)
    event_id = Column(Text, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    similarity_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**EntityService Structure:**
```python
class EntityService:
    """Recognize and track recurring visitors."""

    def __init__(self, similarity_service: SimilarityService):
        self._similarity_service = similarity_service
        self._entity_cache: dict[str, list[float]] = {}  # id -> embedding

    async def match_or_create_entity(
        self,
        db: Session,
        event_id: str,
        embedding: list[float],
        entity_type: str = "unknown",
        threshold: float = 0.75,
    ) -> EntityMatchResult:
        """Match event to existing entity or create new one."""
        # 1. Load entity embeddings (from cache or DB)
        # 2. Calculate batch similarity
        # 3. Find best match above threshold
        # 4. Update or create entity
        # 5. Create EntityEvent link
        # 6. Return result
```

**API Response Schemas:**
```python
class EntityResponse(BaseModel):
    id: str
    entity_type: str
    name: Optional[str]
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int

class EntityDetailResponse(EntityResponse):
    recent_events: list[EventSummary]

class EntityMatchResult(BaseModel):
    entity: EntityResponse
    similarity_score: float
    is_new: bool
```

### Project Structure Notes

**Files to create:**
- `backend/app/models/recognized_entity.py` - Entity and EntityEvent models
- `backend/app/services/entity_service.py` - Entity matching and management
- `backend/tests/test_services/test_entity_service.py` - Unit tests
- `backend/tests/test_integration/test_entity_integration.py` - Integration tests
- `backend/tests/test_api/test_entity_api.py` - API tests
- `backend/alembic/versions/XXXX_add_recognized_entities.py` - Migration

**Files to modify:**
- `backend/app/api/v1/context.py` - Add entity endpoints
- `backend/app/models/__init__.py` - Export new models
- `backend/app/services/event_processor.py` - Integrate entity matching
- `backend/app/schemas/event.py` - Add matched_entity to EventResponse

### Performance Considerations

- Cache entity embeddings in memory for fast matching
- Invalidate cache when new entity created or entity deleted
- Batch similarity calculation with numpy (reuse from SimilarityService)
- Consider limiting active entities for matching (most recent N, or above occurrence threshold)
- Index on recognized_entities(last_seen_at) for efficient ordering

### Testing Strategy

Per testing-strategy.md, target coverage:
- Unit tests: Entity model validation, match logic, threshold handling
- Integration tests: Full pipeline with database, entity clustering over time
- API tests: All CRUD endpoints, error responses, schema validation
- Performance tests: Match 1000 entities in <200ms

### Learnings from Previous Story

**From Story P4-3.2 (Similarity Search) (Status: done)**

- **SimilarityService Available**: Use `get_similarity_service()` for dependency injection - DO NOT recreate
- **Batch Similarity Method**: `batch_cosine_similarity(query, candidates)` returns list of similarity scores
- **Cosine Similarity Function**: `cosine_similarity(vec1, vec2)` for single pair comparison
- **File Created**: `backend/app/services/similarity_service.py` - REUSE batch calculation
- **API Pattern**: Context endpoints in `backend/app/api/v1/context.py` - ADD entity endpoints here
- **Test Coverage**: 54 tests total (29 unit + 11 integration + 14 API) - target similar
- **Performance**: <200ms for 10,000 embeddings - entity matching should be faster (fewer entities)

**From Story P4-3.1 (Event Embedding Generation) (Status: done)**

- **EmbeddingService Available**: Use `get_embedding_service()` - DO NOT recreate
- **Embedding Format**: JSON array stored as Text, use `json.loads()` to deserialize
- **Pipeline Location**: Embeddings generated in Step 9 of event_processor.py - add entity matching after

**Reusable Services (DO NOT RECREATE):**
- `EmbeddingService.get_embedding_vector(db, event_id)` - Get event embedding
- `SimilarityService.batch_cosine_similarity(query, candidates)` - Calculate similarities
- `SimilarityService.find_similar_events(...)` - Find similar events (not needed directly)

[Source: docs/sprint-artifacts/p4-3-2-similarity-search.md#Dev-Agent-Record]
[Source: docs/sprint-artifacts/p4-3-1-event-embedding-generation.md#Dev-Agent-Record]

### References

- [Source: docs/epics-phase4.md#Story-P4-3.3-Recurring-Visitor-Detection]
- [Source: docs/PRD-phase4.md#FR2 - System identifies recurring visitors based on appearance similarity]
- [Source: docs/PRD-phase4.md#FR5 - System maintains a "familiar faces/vehicles" registry]
- [Source: docs/architecture.md#Phase-4-Database-Schema-Additions - recognized_entities table]
- [Source: docs/architecture.md#Phase-4-Service-Architecture - Entity matching flow]
- [Source: docs/sprint-artifacts/p4-3-2-similarity-search.md - SimilarityService patterns]
- [Source: docs/sprint-artifacts/p4-3-1-event-embedding-generation.md - EmbeddingService patterns]

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/p4-3-3-recurring-visitor-detection.context.xml`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-11 | Claude Opus 4.5 | Initial story draft from create-story workflow |

# Epic Technical Specification: AI Context Enhancement (MCP)

Date: 2025-12-25
Author: Brent
Epic ID: P11-3
Status: Draft

---

## Overview

Epic P11-3 implements the MCPContextProvider to enhance AI description accuracy through accumulated context. This builds on the MCP server research from Phase 10 (P10-6.1, docs/research/mcp-server-research.md) and delivers a database-backed context provider that gathers feedback history, entity information, camera patterns, and time-based context to inject into AI prompts.

The goal is to improve AI description accuracy by 5-10% through contextual awareness of past corrections, known entities, and typical activity patterns.

## Objectives and Scope

### In Scope

- MCPContextProvider class with feedback history context
- Entity match context (known people, vehicles)
- Camera and time pattern context
- Integration with existing context_prompt_service.py
- Context caching with 60-second TTL
- Performance metrics and monitoring
- Fail-open design for reliability

### Out of Scope

- Full MCP protocol server (future phase)
- External MCP client support (Claude Desktop)
- Real-time learning/model fine-tuning
- Cross-camera pattern detection

## System Architecture Alignment

This epic implements the MCP architecture from `docs/architecture/phase-11-additions.md`:

- **MCPContextProvider** gathers context via database queries (ADR-P11-003)
- Integrates with existing **context_prompt_service.py**
- Uses existing **EventFeedback**, **Entity**, **Camera** models
- Target: <50ms context gathering (NFR3)

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs |
|----------------|----------------|--------|---------|
| `MCPContextProvider` | Gather and format context | camera_id, event_time | AIContext |
| `FeedbackContext` | Feedback stats/patterns | camera_id | Accuracy, corrections |
| `EntityContext` | Known entity info | entity_id | Name, type, history |
| `CameraContext` | Location/activity hints | camera_id | Patterns, hints |
| `TimeContext` | Time-based patterns | camera_id, time | Unusual flags |
| `context_prompt_service.py` | Integrate context into prompts | AIContext | Enhanced prompt |

### Data Models and Contracts

**AIContext (output):**

```python
@dataclass
class AIContext:
    feedback: Optional[FeedbackContext]
    entity: Optional[EntityContext]
    camera: Optional[CameraContext]
    time_pattern: Optional[TimePatternContext]
```

**FeedbackContext:**

```python
@dataclass
class FeedbackContext:
    accuracy_rate: Optional[float]  # 0.0-1.0
    total_feedback: int
    common_corrections: List[str]  # Top 3 correction patterns
    recent_negative_reasons: List[str]  # Last 5 negative feedback reasons
```

**EntityContext:**

```python
@dataclass
class EntityContext:
    entity_id: str
    name: str
    entity_type: str  # person, vehicle
    attributes: Dict[str, str]  # color, make, etc.
    last_seen: Optional[datetime]
    sighting_count: int
```

**CameraContext:**

```python
@dataclass
class CameraContext:
    camera_id: str
    location_hint: Optional[str]  # e.g., "Front Door", "Driveway"
    typical_objects: List[str]  # Common detections
    false_positive_patterns: List[str]  # Known false positives
```

**TimePatternContext:**

```python
@dataclass
class TimePatternContext:
    hour: int
    typical_activity_level: str  # low, medium, high
    is_unusual: bool
    typical_event_count: float  # Average for this hour
```

**CachedContext:**

```python
@dataclass
class CachedContext:
    context: AIContext
    created_at: datetime

    def is_expired(self, ttl_seconds: int = 60) -> bool:
        return (datetime.utcnow() - self.created_at).total_seconds() > ttl_seconds
```

### APIs and Interfaces

MCPContextProvider is an internal service, not exposed via API. It's called by the AI description pipeline.

**Internal Interface:**

```python
class MCPContextProvider:
    async def get_context(
        self,
        camera_id: str,
        event_time: datetime,
        entity_id: Optional[str] = None,
    ) -> AIContext:
        """Gather context for AI prompt generation."""
        ...

    def format_for_prompt(self, context: AIContext) -> str:
        """Format context as prompt text."""
        ...
```

**Integration Point in context_prompt_service.py:**

```python
async def build_enhanced_prompt(
    event: Event,
    mcp_provider: MCPContextProvider,
) -> str:
    # Get MCP context
    context = await mcp_provider.get_context(
        camera_id=event.camera_id,
        event_time=event.created_at,
        entity_id=event.matched_entity_id,
    )

    # Format context for prompt
    context_text = mcp_provider.format_for_prompt(context)

    # Build full prompt with context
    return f"""
{SYSTEM_PROMPT}

Context from previous observations:
{context_text}

Describe what you see in the following security camera images...
"""
```

### Workflows and Sequencing

**Context Gathering Flow:**

```
1. Event triggers AI description
2. context_prompt_service calls mcp_provider.get_context()
3. Check cache for camera_id:hour key
4. If cached and not expired → return cached
5. Gather context in parallel (asyncio.gather):
   a. _get_feedback_context(camera_id)
   b. _get_entity_context(entity_id) if provided
   c. _get_camera_context(camera_id)
   d. _get_time_context(camera_id, event_time)
6. Any failures → None for that context (fail-open)
7. Build AIContext, cache it
8. Return AIContext
```

**Feedback Context Query:**

```python
async def _get_feedback_context(self, camera_id: str) -> FeedbackContext:
    # Query recent feedback (last 50)
    query = (
        select(EventFeedback)
        .join(Event)
        .where(Event.camera_id == camera_id)
        .order_by(EventFeedback.created_at.desc())
        .limit(50)
    )
    result = await self.db.execute(query)
    feedbacks = result.scalars().all()

    # Calculate accuracy
    total = len(feedbacks)
    positive = sum(1 for f in feedbacks if f.is_positive)
    accuracy = positive / total if total > 0 else None

    # Extract common correction patterns
    corrections = [f.correction_text for f in feedbacks if f.correction_text]
    common = self._extract_common_patterns(corrections)

    return FeedbackContext(
        accuracy_rate=accuracy,
        total_feedback=total,
        common_corrections=common[:3],
        recent_negative_reasons=[
            f.feedback_text for f in feedbacks[:5]
            if not f.is_positive and f.feedback_text
        ],
    )
```

**Entity Context Query:**

```python
async def _get_entity_context(self, entity_id: str) -> EntityContext:
    entity = await self.db.get(Entity, entity_id)
    if not entity:
        return None

    # Count recent sightings
    count_query = (
        select(func.count(Event.id))
        .where(Event.matched_entity_id == entity_id)
        .where(Event.created_at > datetime.utcnow() - timedelta(days=30))
    )
    sighting_count = await self.db.execute(count_query)

    return EntityContext(
        entity_id=entity.id,
        name=entity.name,
        entity_type=entity.entity_type,
        attributes=entity.attributes or {},
        last_seen=entity.last_seen_at,
        sighting_count=sighting_count.scalar() or 0,
    )
```

**Time Pattern Query:**

```python
async def _get_time_context(
    self, camera_id: str, event_time: datetime
) -> TimePatternContext:
    hour = event_time.hour

    # Get average event count for this hour (last 30 days)
    avg_query = (
        select(func.count(Event.id))
        .where(Event.camera_id == camera_id)
        .where(extract('hour', Event.created_at) == hour)
        .where(Event.created_at > datetime.utcnow() - timedelta(days=30))
    )
    total_events = await self.db.execute(avg_query)
    avg_per_day = (total_events.scalar() or 0) / 30

    # Determine activity level
    if avg_per_day < 1:
        level = "low"
    elif avg_per_day < 5:
        level = "medium"
    else:
        level = "high"

    # Check if current event is unusual (outside normal hours or high activity)
    is_unusual = (
        (level == "low" and hour >= 22 or hour <= 6) or
        (level == "low")  # Any activity during low-activity hours
    )

    return TimePatternContext(
        hour=hour,
        typical_activity_level=level,
        is_unusual=is_unusual,
        typical_event_count=avg_per_day,
    )
```

**Prompt Formatting:**

```python
def format_for_prompt(self, context: AIContext) -> str:
    parts = []

    if context.feedback and context.feedback.accuracy_rate is not None:
        parts.append(
            f"Previous accuracy for this camera: {context.feedback.accuracy_rate:.0%}"
        )
        if context.feedback.common_corrections:
            parts.append(
                f"Common corrections: {', '.join(context.feedback.common_corrections)}"
            )

    if context.entity:
        parts.append(
            f"Known entity: {context.entity.name} ({context.entity.entity_type})"
        )
        if context.entity.attributes:
            attrs = ", ".join(f"{k}={v}" for k, v in context.entity.attributes.items())
            parts.append(f"Entity attributes: {attrs}")

    if context.camera and context.camera.location_hint:
        parts.append(f"Camera location: {context.camera.location_hint}")

    if context.time_pattern and context.time_pattern.is_unusual:
        parts.append("Note: This is unusual activity for this time of day")

    return "\n".join(parts) if parts else ""
```

## Non-Functional Requirements

### Performance

| Metric | Target | Source |
|--------|--------|--------|
| Context query (cached) | <5ms | NFR3 |
| Context query (uncached) | <50ms | NFR3 |
| Prompt formatting | <1ms | General |
| Cache hit ratio | >80% | Goal |

### Security

- Context data derived from user's own data only
- No external API calls for context
- Entity names may contain PII - handle appropriately

### Reliability/Availability

- **NFR12**: MCP context fails open - AI works without context
- Individual context queries fail independently
- Cache prevents database overload during bursts

### Observability

- Structured logging:
  - `mcp.context_gathered`: camera_id, duration_ms, has_feedback, has_entity
  - `mcp.cache_hit`: cache_key
  - `mcp.cache_miss`: cache_key
  - `mcp.context_error`: component, error
- Prometheus metrics:
  - `argusai_mcp_context_latency_seconds{cached}`
  - `argusai_mcp_cache_hits_total`
  - `argusai_mcp_cache_misses_total`
  - `argusai_mcp_context_components{component,available}`

## Dependencies and Integrations

| Dependency | Version | Purpose |
|------------|---------|---------|
| SQLAlchemy | existing | Database queries |
| asyncio | stdlib | Parallel gathering |

**Internal Integrations:**
- EventFeedback model (existing)
- Entity model (existing)
- Camera model (existing)
- Event model (existing)
- context_prompt_service.py (existing)

## Acceptance Criteria (Authoritative)

1. **AC-3.1.1**: MCPContextProvider class created in backend/app/services/
2. **AC-3.1.2**: Provider gathers recent feedback (last 50 items)
3. **AC-3.1.3**: Camera-specific accuracy stats included
4. **AC-3.1.4**: Common corrections summarized
5. **AC-3.1.5**: Context formatted for AI prompt injection
6. **AC-3.1.6**: Fail-open design - AI works if context fails
7. **AC-3.2.1**: Entity context includes matched entity details
8. **AC-3.2.2**: Similar entities (by embedding) suggested
9. **AC-3.2.3**: Entity names and attributes included in prompt
10. **AC-3.2.4**: Recent entity sightings provide temporal context
11. **AC-3.2.5**: Context size limited to prevent prompt overflow
12. **AC-3.3.1**: Camera context includes location hints
13. **AC-3.3.2**: Typical activity patterns for camera included
14. **AC-3.3.3**: Time-of-day activity levels provided
15. **AC-3.3.4**: Unusual timing flagged in context
16. **AC-3.3.5**: False positive patterns shared
17. **AC-3.4.1**: Context cached with 60-second TTL
18. **AC-3.4.2**: Cache key based on camera + time window
19. **AC-3.4.3**: Context queries complete within 50ms (p95)
20. **AC-3.4.4**: Metrics track context gathering latency
21. **AC-3.4.5**: Cache hit/miss ratios monitored

## Traceability Mapping

| AC | Spec Section | Component | Test Idea |
|----|--------------|-----------|-----------|
| AC-3.1.1-6 | Services/MCPContextProvider | mcp_context.py | Unit: feedback gathering, fail-open |
| AC-3.2.1-5 | Workflows/Entity | _get_entity_context | Unit: entity lookup, attributes |
| AC-3.3.1-5 | Workflows/Camera,Time | _get_camera_context, _get_time_context | Unit: pattern detection |
| AC-3.4.1-5 | Data Models/Cache | CachedContext | Unit: TTL expiry, performance |

## Risks, Assumptions, Open Questions

### Risks

- **R1**: Database queries slow down event processing
  - *Mitigation*: Caching, parallel queries, query optimization with indexes
- **R2**: Context prompt bloat reduces AI quality
  - *Mitigation*: Limit context to key facts, measure impact
- **R3**: Feedback data sparse for new cameras
  - *Mitigation*: Graceful degradation, no context if insufficient data

### Assumptions

- **A1**: EventFeedback table has sufficient data for accuracy calculation
- **A2**: Camera names/locations provide useful context
- **A3**: Time patterns are meaningful for activity detection

### Open Questions

- **Q1**: How much context improves vs. harms AI accuracy?
  - *Decision*: A/B test with and without context, measure accuracy delta
- **Q2**: Should context include cross-camera patterns?
  - *Decision*: Defer to future - start with per-camera only

## Test Strategy Summary

### Unit Tests

- MCPContextProvider: All context gathering methods
- Cache: TTL expiry, key generation
- Fail-open: Exceptions don't propagate
- Format: Various context combinations

### Integration Tests

- Full context gathering with seeded database
- Integration with context_prompt_service
- Performance test: verify <50ms target

### A/B Testing

- Enable/disable context for subset of events
- Compare AI accuracy with human feedback
- Measure token cost impact

### Test Coverage Target

- Backend: 90%+ for mcp_context.py
- Performance assertions in tests

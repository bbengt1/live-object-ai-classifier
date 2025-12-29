# Epic Technical Specification: P14-6 MCP Context System Enhancement

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-6
Status: Draft
Priority: P2-P3

---

## Overview

Epic P14-6 enhances the MCP (Model Context Protocol) Context System that provides AI context for event descriptions. The system was implemented in Phase 11 (P11-3) and gathers context from feedback history, entities, camera patterns, and time patterns. This epic focuses on:

1. Integrating entity adjustments into context
2. Implementing parallel query execution for performance
3. Fixing async/sync database query mismatches
4. Adding query timeout enforcement
5. Optimizing cache hit ratio
6. Improving pattern extraction algorithms
7. Adding VIP/blocked entity context
8. Adding context metrics dashboard

## Current State Analysis

### Architecture Overview

```
Event → MCPContextProvider.get_context(camera_id, event_time, entity_id)
                                    ↓
                      Check cache for camera:hour key
                                    ↓
                      If cached and not expired → return cached
                                    ↓
                      Query recent feedback (last 50)
                                    ↓
                      Query entity details if entity_id provided
                                    ↓
                      Query camera patterns and location
                                    ↓
                      Calculate time-based activity patterns
                                    ↓
                      Build FeedbackContext, EntityContext, CameraContext, TimePatternContext
                                    ↓
                      Cache and return AIContext
```

### Current Implementation (`mcp_context.py`)

| Component | Lines | Description |
|-----------|-------|-------------|
| `FeedbackContext` | 78-85 | User feedback history |
| `EntityContext` | 87-96 | Entity match information |
| `CameraContext` | 99-106 | Camera location and patterns |
| `TimePatternContext` | 108-115 | Time-of-day patterns |
| `AIContext` | 117-124 | Combined context for AI |
| `CachedContext` | 126-138 | Cache wrapper with TTL |
| `MCPContextProvider` | 141-1089 | Main provider class |

### Current Metrics

| Metric | Purpose |
|--------|---------|
| `argusai_mcp_context_latency_seconds` | Context gathering latency |
| `argusai_mcp_cache_hits_total` | Cache hit count |
| `argusai_mcp_cache_misses_total` | Cache miss count |

### Known Issues

1. **No entity adjustments context** - Manual entity corrections not included
2. **Sequential queries** - Context queries run sequentially, not in parallel
3. **Async/sync mismatch** - Some database queries block event loop
4. **No query timeout** - Long-running queries can block pipeline
5. **Cache efficiency unknown** - No visibility into actual cache performance
6. **Basic pattern extraction** - Could be improved with ML/heuristics

## Objectives and Scope

### In Scope

- Add entity adjustments to context
- Parallelize database queries using `asyncio.gather()`
- Fix async/sync database access patterns
- Add configurable query timeouts
- Add cache hit ratio monitoring
- Improve pattern extraction algorithm
- Add VIP/blocked entity context
- Create metrics dashboard component

### Out of Scope

- Complete MCP server implementation (future epic)
- External MCP integrations
- Major architectural changes
- New AI model integrations

## Detailed Design

### Story P14-6.1: Integrate Entity Adjustments Context

**Problem:** When users manually assign/unlink entities from events, this information is not included in AI context for future events.

**Solution:** Add `EntityAdjustment` query to `_get_entity_context()`:

```python
@dataclass
class EntityContext:
    """Context about a matched entity (Story P11-3.2)."""
    entity_id: str
    name: str
    entity_type: str
    attributes: Dict[str, str]
    last_seen: Optional[datetime]
    sighting_count: int
    similar_entities: List[Dict[str, Any]] = field(default_factory=list)
    # NEW: Manual adjustment history
    manual_assignments: int = 0  # Times manually assigned to events
    manual_unlinks: int = 0  # Times manually unlinked from events
    user_confirmed: bool = False  # Has user confirmed identity

async def _get_entity_context(
    self,
    db: Session,
    entity_id: str,
) -> Optional[EntityContext]:
    """Get context for a matched entity."""
    # Existing entity query...

    # NEW: Query adjustment history
    adjustments = db.query(
        EntityAdjustment.action,
        func.count(EntityAdjustment.id).label('count')
    ).filter(
        EntityAdjustment.new_entity_id == entity_id
    ).group_by(EntityAdjustment.action).all()

    adjustment_counts = {adj.action: adj.count for adj in adjustments}

    return EntityContext(
        # ... existing fields ...
        manual_assignments=adjustment_counts.get('assign', 0),
        manual_unlinks=adjustment_counts.get('unlink', 0),
        user_confirmed=adjustment_counts.get('assign', 0) > 2,  # Confirmed if assigned 3+ times
    )
```

**Prompt Impact:**
```
Context about "John Smith":
- Recognized person, last seen 2 hours ago
- Seen 47 times at this location
- User has manually confirmed this identity (assigned 5 times)
```

### Story P14-6.2: Implement Parallel Query Execution

**Problem:** Context queries run sequentially, increasing latency:

```python
# Current (sequential):
feedback_ctx = await self._safe_get_feedback_context(session, camera_id)
entity_ctx = await self._safe_get_entity_context(session, entity_id)
camera_ctx = await self._safe_get_camera_context(session, camera_id)
time_ctx = await self._safe_get_time_pattern_context(session, camera_id, event_time)
```

**Solution:** Use `asyncio.gather()` for parallel execution:

```python
async def get_context(
    self,
    camera_id: str,
    event_time: datetime,
    entity_id: Optional[str] = None,
    db: Session = None,
) -> AIContext:
    """Gather context with parallel query execution."""
    # ... cache check ...

    # Execute queries in parallel
    tasks = [
        self._safe_get_feedback_context(session, camera_id),
        self._safe_get_camera_context(session, camera_id),
        self._safe_get_time_pattern_context(session, camera_id, event_time),
    ]

    if entity_id:
        tasks.append(self._safe_get_entity_context(session, entity_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    feedback_ctx = results[0] if not isinstance(results[0], Exception) else None
    camera_ctx = results[1] if not isinstance(results[1], Exception) else None
    time_ctx = results[2] if not isinstance(results[2], Exception) else None
    entity_ctx = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None

    # Log any exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Context query {i} failed: {result}")

    return AIContext(
        feedback=feedback_ctx,
        entity=entity_ctx,
        camera=camera_ctx,
        time_pattern=time_ctx,
    )
```

**Expected Performance Improvement:**
- Before: ~200ms (4 sequential queries × 50ms average)
- After: ~60ms (parallel execution, limited by slowest query)

### Story P14-6.3: Fix Async/Sync Database Query Mismatch

**Problem:** MCP context uses synchronous SQLAlchemy session but is called from async context.

**Current Pattern:**
```python
async def _get_feedback_context(self, db: Session, camera_id: str):
    # This blocks the event loop!
    feedback_list = db.query(EventFeedback).filter(...).all()
```

**Solution:** Use async session or run in thread pool:

**Option A: Use async SQLAlchemy (preferred):**
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def _get_feedback_context(
    self,
    db: AsyncSession,
    camera_id: str
) -> Optional[FeedbackContext]:
    """Get feedback context using async queries."""
    result = await db.execute(
        select(EventFeedback)
        .filter(EventFeedback.camera_id == camera_id)
        .order_by(desc(EventFeedback.created_at))
        .limit(50)
    )
    feedback_list = result.scalars().all()
    # ... process feedback ...
```

**Option B: Run in thread pool (fallback):**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

async def _get_feedback_context(
    self,
    db: Session,
    camera_id: str
) -> Optional[FeedbackContext]:
    """Get feedback context in thread pool to avoid blocking."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        self._get_feedback_context_sync,
        db,
        camera_id
    )

def _get_feedback_context_sync(
    self,
    db: Session,
    camera_id: str
) -> Optional[FeedbackContext]:
    """Synchronous feedback context query."""
    feedback_list = db.query(EventFeedback).filter(...).all()
    # ... process feedback ...
```

### Story P14-6.4: Add Query Timeout Enforcement

**Problem:** Long-running database queries can block the AI pipeline.

**Solution:** Add timeout wrapper for all context queries:

```python
from asyncio import timeout

QUERY_TIMEOUT_SECONDS = 5.0

async def _safe_get_feedback_context(
    self,
    db: Session,
    camera_id: str,
) -> Optional[FeedbackContext]:
    """Get feedback context with timeout and error handling."""
    try:
        async with timeout(QUERY_TIMEOUT_SECONDS):
            return await self._get_feedback_context(db, camera_id)
    except asyncio.TimeoutError:
        logger.warning(
            f"Feedback context query timed out for camera {camera_id}",
            extra={
                "event_type": "mcp.query_timeout",
                "query_type": "feedback",
                "camera_id": camera_id,
                "timeout_seconds": QUERY_TIMEOUT_SECONDS,
            }
        )
        return None
    except Exception as e:
        logger.error(f"Feedback context query failed: {e}")
        return None
```

**Configuration:**
```python
# config.py
class Settings:
    MCP_QUERY_TIMEOUT_SECONDS: float = Field(
        default=5.0,
        description="Timeout for MCP context database queries"
    )
```

### Story P14-6.5: Investigate and Optimize Cache Hit Ratio

**Problem:** No visibility into cache effectiveness.

**Solution:** Add detailed cache metrics:

```python
from prometheus_client import Gauge

MCP_CACHE_SIZE = Gauge(
    'argusai_mcp_cache_size',
    'Number of entries in MCP context cache',
    registry=REGISTRY
)
MCP_CACHE_HIT_RATIO = Gauge(
    'argusai_mcp_cache_hit_ratio',
    'MCP context cache hit ratio (rolling window)',
    registry=REGISTRY
)
MCP_CACHE_AGE_SECONDS = Histogram(
    'argusai_mcp_cache_age_seconds',
    'Age of cached context when hit',
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=REGISTRY
)

class MCPContextProvider:
    def __init__(self):
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'window_start': time.time(),
        }

    def _update_cache_metrics(self):
        """Update cache metrics periodically."""
        MCP_CACHE_SIZE.set(len(self._cache))

        total = self._cache_stats['hits'] + self._cache_stats['misses']
        if total > 0:
            ratio = self._cache_stats['hits'] / total
            MCP_CACHE_HIT_RATIO.set(ratio)

        # Reset window every 5 minutes
        if time.time() - self._cache_stats['window_start'] > 300:
            self._cache_stats = {
                'hits': 0,
                'misses': 0,
                'window_start': time.time(),
            }
```

**Cache Optimization Recommendations:**
1. Increase TTL for stable cameras (low activity variance)
2. Pre-warm cache on startup for active cameras
3. Invalidate cache on feedback submission
4. Use LRU eviction when cache exceeds max size

### Story P14-6.6: Improve Pattern Extraction Algorithm

**Problem:** Current pattern extraction is basic string matching.

**Current:**
```python
def _extract_patterns(self, feedback_list) -> List[str]:
    """Extract common correction patterns from feedback."""
    # Simple keyword frequency
    corrections = []
    for fb in feedback_list:
        if fb.correction_type:
            corrections.append(fb.correction_type)
    return Counter(corrections).most_common(3)
```

**Improved:**
```python
def _extract_patterns(
    self,
    feedback_list: List[EventFeedback]
) -> List[PatternMatch]:
    """
    Extract patterns from feedback using improved algorithm.

    Identifies:
    - Temporal patterns (time-of-day errors)
    - Entity confusion patterns (person X often mistaken for Y)
    - Object misclassification (vehicle type errors)
    - False positive patterns (non-events)
    """
    patterns = []

    # Group feedback by hour
    by_hour = defaultdict(list)
    for fb in feedback_list:
        hour = fb.created_at.hour
        by_hour[hour].append(fb)

    # Find hourly error patterns
    for hour, feedbacks in by_hour.items():
        negatives = [f for f in feedbacks if not f.is_positive]
        if len(negatives) >= 3:
            patterns.append(PatternMatch(
                pattern_type="temporal",
                description=f"Higher error rate around {hour}:00",
                confidence=len(negatives) / len(feedbacks),
            ))

    # Find entity confusion patterns
    entity_corrections = [
        fb for fb in feedback_list
        if fb.correction_type == "wrong_entity"
    ]
    if len(entity_corrections) >= 2:
        patterns.append(PatternMatch(
            pattern_type="entity_confusion",
            description="Entity identification needs improvement",
            confidence=len(entity_corrections) / len(feedback_list),
        ))

    return patterns
```

### Story P14-6.7: Add VIP/Blocked Entity Context

**Problem:** AI doesn't know about VIP (always notify) or blocked (ignore) entities.

**Solution:** Add entity status to context:

```python
@dataclass
class EntityContext:
    # ... existing fields ...
    is_vip: bool = False  # User marked as important (always notify)
    is_blocked: bool = False  # User marked to ignore
    alert_rules_count: int = 0  # Number of alert rules for this entity

async def _get_entity_context(self, db, entity_id) -> Optional[EntityContext]:
    entity = db.query(RecognizedEntity).get(entity_id)
    if not entity:
        return None

    # Check for VIP/blocked status
    # (Stored as entity metadata or in alert rules)
    alert_rules = db.query(AlertRule).filter(
        AlertRule.entity_id == entity_id,
        AlertRule.is_enabled == True
    ).all()

    is_vip = any(r.priority == 'high' for r in alert_rules)
    is_blocked = entity.metadata.get('blocked', False) if entity.metadata else False

    return EntityContext(
        # ... existing fields ...
        is_vip=is_vip,
        is_blocked=is_blocked,
        alert_rules_count=len(alert_rules),
    )
```

**Prompt Impact:**
```
Context about "Delivery Person":
- ⚡ VIP: User has high-priority alert rules for this entity
- 3 active alert rules configured
```

### Story P14-6.8: Add Context Metrics Dashboard

**Create:** `frontend/components/settings/MCPMetricsDashboard.tsx`

```typescript
interface MCPMetrics {
  cache_hit_ratio: number;
  cache_size: number;
  avg_latency_ms: number;
  queries_per_minute: number;
  timeout_rate: number;
}

export function MCPMetricsDashboard() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['mcp-metrics'],
    queryFn: () => apiClient.system.getMCPMetrics(),
    refetchInterval: 10000,
  });

  if (isLoading) return <Skeleton className="h-48" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Context System</CardTitle>
        <CardDescription>MCP context gathering performance</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Cache Hit Rate"
            value={`${(metrics.cache_hit_ratio * 100).toFixed(1)}%`}
            trend={metrics.cache_hit_ratio > 0.8 ? 'up' : 'down'}
          />
          <StatCard
            label="Avg Latency"
            value={`${metrics.avg_latency_ms.toFixed(0)}ms`}
            trend={metrics.avg_latency_ms < 100 ? 'up' : 'down'}
          />
          <StatCard
            label="Cache Size"
            value={metrics.cache_size}
          />
          <StatCard
            label="Timeout Rate"
            value={`${(metrics.timeout_rate * 100).toFixed(1)}%`}
            trend={metrics.timeout_rate < 0.01 ? 'up' : 'down'}
          />
        </div>
      </CardContent>
    </Card>
  );
}
```

**Backend Endpoint:**
```python
@router.get("/mcp-metrics")
async def get_mcp_metrics() -> dict:
    """Get MCP context system metrics."""
    provider = get_mcp_context_provider()
    return {
        "cache_hit_ratio": provider.get_cache_hit_ratio(),
        "cache_size": len(provider._cache),
        "avg_latency_ms": provider.get_avg_latency_ms(),
        "queries_per_minute": provider.get_queries_per_minute(),
        "timeout_rate": provider.get_timeout_rate(),
    }
```

## Acceptance Criteria

### AC-1: Entity Adjustments
- [ ] Manual assignment count included in EntityContext
- [ ] Manual unlink count included in EntityContext
- [ ] User-confirmed flag derived from assignment count
- [ ] Adjustments appear in AI prompt context

### AC-2: Parallel Queries
- [ ] Context queries execute in parallel
- [ ] Query failures don't block other queries
- [ ] Latency reduced by 60%+ on cache miss

### AC-3: Async/Sync Fix
- [ ] No blocking database calls in async functions
- [ ] Event loop not blocked during context gathering
- [ ] Tests verify async behavior

### AC-4: Query Timeout
- [ ] Configurable timeout for all context queries
- [ ] Timeout logged with query details
- [ ] Timeout doesn't crash pipeline (returns None)

### AC-5: Cache Metrics
- [ ] Cache hit ratio metric available
- [ ] Cache size metric available
- [ ] Cache age histogram available
- [ ] Metrics visible at /metrics endpoint

### AC-6: Pattern Extraction
- [ ] Temporal patterns detected
- [ ] Entity confusion patterns detected
- [ ] Pattern confidence scores included

### AC-7: VIP/Blocked Entities
- [ ] VIP flag in EntityContext
- [ ] Blocked flag in EntityContext
- [ ] Alert rules count included
- [ ] Context reflects in AI prompts

### AC-8: Metrics Dashboard
- [ ] Dashboard component created
- [ ] Shows cache hit rate
- [ ] Shows average latency
- [ ] Auto-refreshes every 10 seconds

## Test Strategy

### Unit Tests

```python
# tests/test_services/test_mcp_context_enhanced.py

class TestParallelQueries:
    async def test_queries_run_in_parallel(self, mcp_provider, mock_db):
        """Test that queries execute concurrently."""
        query_start_times = []

        async def mock_query(*args):
            query_start_times.append(time.time())
            await asyncio.sleep(0.1)
            return None

        # Patch all query methods
        # ...

        await mcp_provider.get_context("cam1", datetime.now())

        # All queries should start within 10ms of each other
        assert max(query_start_times) - min(query_start_times) < 0.01

class TestQueryTimeout:
    async def test_timeout_returns_none(self, mcp_provider, mock_db):
        """Test that timeout returns None without crashing."""
        async def slow_query(*args):
            await asyncio.sleep(10)  # Longer than timeout

        mcp_provider._get_feedback_context = slow_query

        context = await mcp_provider.get_context("cam1", datetime.now())

        assert context.feedback is None  # Timed out
        assert context.camera is not None  # Other queries succeeded
```

## Non-Functional Requirements

| Metric | Current | Target |
|--------|---------|--------|
| Cache hit ratio | Unknown | >80% |
| Context latency (cache miss) | ~200ms | <100ms |
| Query timeout rate | Unknown | <1% |
| Memory usage | Unbounded | <50MB |

---

_Tech spec generated for Phase 14 Epic P14-6: MCP Context System Enhancement_

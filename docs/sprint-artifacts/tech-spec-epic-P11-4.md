# Epic Technical Specification: Query-Adaptive Frame Selection

Date: 2025-12-25
Author: Brent
Epic ID: P11-4
Status: Draft

---

## Overview

Epic P11-4 implements query-adaptive frame selection for targeted event re-analysis. Building on the research from Phase 10 (P10-6.2, docs/research/query-adaptive-frames-research.md), this epic extends the existing EmbeddingService to encode text queries, stores frame-level embeddings during extraction, and creates a smart-reanalyze endpoint that selects the most relevant frames based on semantic similarity to the user's question.

This enables users to ask specific questions like "Was there a package?" and have the AI analyze only the frames most likely to contain the answer.

## Objectives and Scope

### In Scope

- Text query encoding in EmbeddingService (reusing CLIP model)
- FrameEmbedding database model for per-frame storage
- Frame embedding generation during extraction pipeline
- POST `/api/v1/events/{id}/smart-reanalyze` endpoint
- Cosine similarity scoring for frame-query matching
- Top-K frame selection for targeted analysis
- Fallback to uniform selection if no embeddings

### Out of Scope

- Re-training or fine-tuning CLIP model
- Multi-modal queries (image + text)
- Cross-event query search
- Real-time frame embedding (only during extraction)

## System Architecture Alignment

This epic implements the query-adaptive architecture from `docs/architecture/phase-11-additions.md`:

- **EmbeddingService** extended for text encoding (ADR-P11-004)
- **FrameEmbedding** model stores 512-dim CLIP embeddings
- Cosine similarity computed in-memory
- Target: <60ms selection overhead (NFR5)

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs |
|----------------|----------------|--------|---------|
| `EmbeddingService.encode_text()` | Text → embedding | Query string | 512-dim vector |
| `FrameEmbedding` model | Frame embedding storage | Event ID, index, embedding | DB record |
| `frame_extraction_service.py` | Generate embeddings | Frames | Stored embeddings |
| `events.py` router | Smart-reanalyze API | Event ID, query | Reanalysis result |

### Data Models and Contracts

**FrameEmbedding Model:**

```python
class FrameEmbedding(Base):
    __tablename__ = "frame_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False)
    frame_index = Column(Integer, nullable=False)
    embedding = Column(JSON, nullable=False)  # List[float], 512 dimensions
    model_version = Column(String(50), nullable=False)  # "clip-vit-base-patch32"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="frame_embeddings")

    __table_args__ = (
        Index('ix_frame_embeddings_event_frame', 'event_id', 'frame_index'),
        UniqueConstraint('event_id', 'frame_index', name='uq_frame_embedding'),
    )
```

**Smart Reanalyze Request:**

```python
class SmartReanalyzeRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)
```

**Smart Reanalyze Response:**

```python
class SmartReanalyzeResponse(BaseModel):
    description: str
    frames_analyzed: int
    frame_scores: List[FrameScore]
    selection_time_ms: float
    analysis_time_ms: float

class FrameScore(BaseModel):
    frame_index: int
    relevance_score: float  # 0.0 to 1.0
    selected: bool
```

### APIs and Interfaces

**POST /api/v1/events/{event_id}/smart-reanalyze**

```yaml
Request:
  Query Parameters:
    query: string (required) - Question to focus analysis on
    top_k: integer (optional, default=5) - Number of frames to analyze

Response 200:
  {
    "description": "A delivery person in brown uniform is placing a package...",
    "frames_analyzed": 5,
    "frame_scores": [
      {"frame_index": 3, "relevance_score": 0.87, "selected": true},
      {"frame_index": 5, "relevance_score": 0.82, "selected": true},
      {"frame_index": 2, "relevance_score": 0.75, "selected": true},
      {"frame_index": 4, "relevance_score": 0.72, "selected": true},
      {"frame_index": 1, "relevance_score": 0.68, "selected": true},
      {"frame_index": 0, "relevance_score": 0.45, "selected": false}
    ],
    "selection_time_ms": 45.2,
    "analysis_time_ms": 1250.0
  }

Response 404:
  {
    "detail": "Event not found"
  }

Response 400:
  {
    "detail": "No frame embeddings available for this event"
  }
```

### Workflows and Sequencing

**Text Encoding Extension:**

```python
class EmbeddingService:
    # Existing image encoding...

    def encode_text(self, query: str) -> np.ndarray:
        """Encode text query to embedding vector."""
        # Preprocess
        query = query.strip().lower()

        # Format short queries for CLIP
        if len(query.split()) <= 3:
            query = f"a photo of {query}"

        # Encode using CLIP text encoder
        text_inputs = self.clip_processor(
            text=[query],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77,  # CLIP max length
        )

        with torch.no_grad():
            text_features = self.clip_model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()[0]  # 512-dim
```

**Frame Embedding Generation (during extraction):**

```python
async def extract_and_embed_frames(
    self,
    video_path: str,
    event_id: str,
    frame_count: int = 5,
) -> List[ExtractedFrame]:
    """Extract frames and generate embeddings."""
    frames = self._extract_frames(video_path, frame_count)

    # Batch encode all frames
    frame_images = [frame.image for frame in frames]
    embeddings = self.embedding_service.encode_batch(frame_images)

    # Store embeddings
    for i, (frame, embedding) in enumerate(zip(frames, embeddings)):
        frame_embedding = FrameEmbedding(
            event_id=event_id,
            frame_index=i,
            embedding=embedding.tolist(),
            model_version=self.embedding_service.model_version,
        )
        self.db.add(frame_embedding)
        frame.embedding = embedding

    await self.db.commit()
    return frames
```

**Smart Reanalyze Flow:**

```
1. Receive POST request with event_id and query
2. Validate event exists
3. Load frame embeddings for event
4. If no embeddings → fallback to uniform selection OR return error
5. Encode query text → query_embedding
6. For each frame embedding:
   - Compute cosine_similarity(query_embedding, frame_embedding)
   - Store (frame_index, score)
7. Sort by score descending
8. Select top-K frames
9. Load frame images from storage
10. Call AI service with selected frames + query
11. Return response with scores and description
```

**Cosine Similarity Calculation:**

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def score_frames(
    query_embedding: np.ndarray,
    frame_embeddings: List[FrameEmbedding],
) -> List[Tuple[int, float]]:
    """Score all frames against query, return sorted list."""
    scores = []
    for fe in frame_embeddings:
        frame_emb = np.array(fe.embedding)
        score = cosine_similarity(query_embedding, frame_emb)
        scores.append((fe.frame_index, score))

    return sorted(scores, key=lambda x: x[1], reverse=True)
```

**Fallback Logic:**

```python
async def smart_reanalyze(
    self,
    event_id: str,
    query: str,
    top_k: int = 5,
) -> SmartReanalyzeResponse:
    # Load embeddings
    embeddings = await self._get_frame_embeddings(event_id)

    if not embeddings:
        logger.warning(f"No embeddings for event {event_id}, using uniform selection")
        # Fallback: select frames uniformly
        frames = await self._get_event_frames(event_id)
        selected_indices = list(range(min(top_k, len(frames))))
        frame_scores = [
            FrameScore(frame_index=i, relevance_score=0.5, selected=True)
            for i in selected_indices
        ]
    else:
        # Normal flow: score and select
        query_embedding = self.embedding_service.encode_text(query)
        scores = score_frames(query_embedding, embeddings)
        selected_indices = [idx for idx, _ in scores[:top_k]]
        frame_scores = [
            FrameScore(frame_index=idx, relevance_score=score, selected=i < top_k)
            for i, (idx, score) in enumerate(scores)
        ]

    # Analyze selected frames
    frames = await self._load_frames(event_id, selected_indices)
    description = await self.ai_service.describe_with_query(frames, query)

    return SmartReanalyzeResponse(
        description=description,
        frames_analyzed=len(selected_indices),
        frame_scores=frame_scores,
        selection_time_ms=selection_time,
        analysis_time_ms=analysis_time,
    )
```

## Non-Functional Requirements

### Performance

| Metric | Target | Source |
|--------|--------|--------|
| Text encoding | <30ms | NFR5 |
| Similarity scoring (10 frames) | <20ms | NFR5 |
| Total selection overhead | <60ms | NFR5 |
| Frame embedding generation | <100ms per frame | Goal |

### Security

- Query text sanitized before processing
- No external API calls for embedding
- Frame images accessed via existing storage permissions

### Reliability/Availability

- Fallback to uniform selection if embeddings missing
- Individual embedding failures don't block extraction
- Embedding storage scales to 100K frames (NFR15)

### Observability

- Structured logging:
  - `embedding.text_encoded`: query_length, duration_ms
  - `embedding.frames_generated`: event_id, frame_count, duration_ms
  - `reanalyze.smart_selection`: event_id, query, top_k, selection_ms
- Prometheus metrics:
  - `argusai_embedding_encode_seconds{type=text|image}`
  - `argusai_frame_embeddings_total`
  - `argusai_smart_reanalyze_requests_total`
  - `argusai_smart_reanalyze_selection_seconds`

## Dependencies and Integrations

| Dependency | Version | Purpose |
|------------|---------|---------|
| transformers | existing | CLIP model |
| torch | existing | Inference |
| numpy | existing | Vector operations |

**Internal Integrations:**
- EmbeddingService (existing, extend)
- FrameExtractionService (existing, extend)
- AIService (existing)
- Event model (existing)

## Acceptance Criteria (Authoritative)

1. **AC-4.1.1**: EmbeddingService.encode_text(query) method added
2. **AC-4.1.2**: Uses same CLIP model as image encoding
3. **AC-4.1.3**: Text embeddings compatible with image embeddings
4. **AC-4.1.4**: Query preprocessing (lowercase, trim)
5. **AC-4.1.5**: "a photo of {query}" formatting for single words
6. **AC-4.2.1**: FrameEmbedding model with event_id, frame_index, embedding, model_version
7. **AC-4.2.2**: Migration creates frame_embeddings table
8. **AC-4.2.3**: Embeddings generated during frame extraction
9. **AC-4.2.4**: Batch generation for efficiency
10. **AC-4.2.5**: Embeddings stored as JSON array
11. **AC-4.3.1**: POST `/api/v1/events/{id}/smart-reanalyze?query=...` available
12. **AC-4.3.2**: Query encoded and compared against frame embeddings
13. **AC-4.3.3**: Cosine similarity scores all frames
14. **AC-4.3.4**: Top-K frames (default 5) selected for analysis
15. **AC-4.3.5**: Selection overhead under 60ms
16. **AC-4.3.6**: Falls back to uniform selection if no embeddings

## Traceability Mapping

| AC | Spec Section | Component | Test Idea |
|----|--------------|-----------|-----------|
| AC-4.1.1-5 | Workflows/TextEncoding | embedding_service.py | Unit: encode text, verify dims |
| AC-4.2.1-5 | Data Models | FrameEmbedding, migration | Unit: CRUD, batch insert |
| AC-4.3.1-6 | APIs/Workflows | events.py, smart_reanalyze | API: selection accuracy, timing |

## Risks, Assumptions, Open Questions

### Risks

- **R1**: CLIP text encoder quality for security-specific queries
  - *Mitigation*: Test with common security queries, consider query reformulation
- **R2**: Embedding storage grows large (10KB per event)
  - *Mitigation*: Cleanup old embeddings, compression options
- **R3**: Selection overhead impacts user experience
  - *Mitigation*: Caching, async loading, progress indicator

### Assumptions

- **A1**: Existing CLIP model suitable for text-image matching
- **A2**: 5 frames sufficient for most queries
- **A3**: Frame storage accessible for re-analysis

### Open Questions

- **Q1**: Should embeddings be generated for all events or on-demand?
  - *Decision*: Generate during extraction (proactive), cheaper than on-demand
- **Q2**: How to handle video-native events without frames?
  - *Decision*: Extract frames retroactively or skip smart-reanalyze

## Test Strategy Summary

### Unit Tests

- EmbeddingService.encode_text: Various query lengths, special characters
- Cosine similarity: Known vectors, edge cases
- Score frames: Ranking correctness
- Fallback logic: Missing embeddings

### Integration Tests

- Full flow: Create event with frames → embeddings → smart reanalyze
- API endpoint: Request validation, response schema
- Performance: Timing assertions for <60ms

### Manual Testing

- Query various security scenarios: "package", "person at door", "car"
- Verify selected frames match query intent
- Compare with uniform selection quality

### Test Coverage Target

- Backend: 90%+ for new code
- API endpoints: 100% coverage
- Performance assertions in CI

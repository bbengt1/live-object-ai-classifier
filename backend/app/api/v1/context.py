"""
Context API endpoints for Temporal Context Engine (Stories P4-3.1, P4-3.2, P4-3.3)

Provides endpoints for:
- Batch processing of embeddings for existing events
- Embedding status retrieval
- Similarity search for finding visually similar past events (P4-3.2)
- Entity management for recurring visitor detection (P4-3.3)
"""
import base64
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event import Event
from app.models.event_embedding import EventEmbedding
from app.services.embedding_service import get_embedding_service, EmbeddingService
from app.services.similarity_service import get_similarity_service, SimilarityService
from app.services.entity_service import get_entity_service, EntityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/context", tags=["context"])


# Request/Response Models
class BatchEmbeddingRequest(BaseModel):
    """Request model for batch embedding generation."""
    limit: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Maximum number of events to process (max 100 per request)"
    )


class BatchEmbeddingResponse(BaseModel):
    """Response model for batch embedding generation."""
    processed: int = Field(description="Number of embeddings successfully generated")
    failed: int = Field(description="Number of embeddings that failed to generate")
    total: int = Field(description="Total number of events processed")
    remaining: int = Field(description="Number of events still without embeddings")


class EmbeddingStatusResponse(BaseModel):
    """Response model for embedding status."""
    event_id: str = Field(description="Event UUID")
    exists: bool = Field(description="Whether an embedding exists for this event")
    model_version: Optional[str] = Field(default=None, description="Model version used")
    created_at: Optional[str] = Field(default=None, description="When the embedding was created")


class EmbeddingStatsResponse(BaseModel):
    """Response model for embedding statistics."""
    total_events: int = Field(description="Total number of events in database")
    events_with_embeddings: int = Field(description="Number of events with embeddings")
    events_without_embeddings: int = Field(description="Number of events without embeddings")
    coverage_percent: float = Field(description="Percentage of events with embeddings")
    model_version: str = Field(description="Current model version")
    embedding_dimension: int = Field(description="Embedding vector dimension")


@router.post("/embeddings/batch", response_model=BatchEmbeddingResponse)
async def batch_generate_embeddings(
    request: BatchEmbeddingRequest = BatchEmbeddingRequest(),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Generate embeddings for events that don't have them yet.

    AC8: Batch processing endpoint for generating embeddings on existing events
    AC9: Batch processing respects rate limiting (max 100 events per request)

    Args:
        request: Batch processing parameters (limit 1-100)
        db: Database session
        embedding_service: Embedding service instance

    Returns:
        BatchEmbeddingResponse with processed/failed/remaining counts
    """
    # AC9: Enforce max 100 events per request
    limit = min(request.limit, 100)

    # Find events without embeddings
    # Subquery to get event_ids that already have embeddings
    events_with_embeddings = db.query(EventEmbedding.event_id).subquery()

    # Get events that don't have embeddings and have thumbnails
    events_without_embeddings = db.query(Event).filter(
        ~Event.id.in_(events_with_embeddings),
        (Event.thumbnail_base64.isnot(None)) | (Event.thumbnail_path.isnot(None))
    ).limit(limit).all()

    processed = 0
    failed = 0

    for event in events_without_embeddings:
        try:
            # Get thumbnail bytes
            thumbnail_bytes = None

            if event.thumbnail_base64:
                # Use base64 thumbnail
                b64_str = event.thumbnail_base64
                if b64_str.startswith("data:"):
                    comma_idx = b64_str.find(",")
                    if comma_idx != -1:
                        b64_str = b64_str[comma_idx + 1:]
                thumbnail_bytes = base64.b64decode(b64_str)

            elif event.thumbnail_path:
                # AC10: Works for file-path thumbnails
                # Resolve file path (handle relative paths like /api/v1/thumbnails/...)
                if event.thumbnail_path.startswith("/api/v1/thumbnails/"):
                    # Extract date and filename from path
                    parts = event.thumbnail_path.split("/")
                    if len(parts) >= 5:
                        date_str = parts[-2]
                        filename = parts[-1]
                        file_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            "data", "thumbnails", date_str, filename
                        )
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                thumbnail_bytes = f.read()

            if thumbnail_bytes:
                # Generate embedding
                embedding_vector = await embedding_service.generate_embedding(thumbnail_bytes)

                # Store embedding
                await embedding_service.store_embedding(
                    db=db,
                    event_id=event.id,
                    embedding=embedding_vector,
                )
                processed += 1
            else:
                # No valid thumbnail
                failed += 1
                logger.warning(
                    f"No valid thumbnail for event {event.id}",
                    extra={"event_id": event.id}
                )

        except Exception as e:
            failed += 1
            logger.error(
                f"Batch embedding failed for event {event.id}: {e}",
                extra={"event_id": event.id, "error": str(e)}
            )

    # Count remaining events without embeddings
    remaining = db.query(Event).filter(
        ~Event.id.in_(db.query(EventEmbedding.event_id)),
        (Event.thumbnail_base64.isnot(None)) | (Event.thumbnail_path.isnot(None))
    ).count()

    logger.info(
        f"Batch embedding complete: {processed} processed, {failed} failed, {remaining} remaining",
        extra={
            "event_type": "batch_embedding_complete",
            "processed": processed,
            "failed": failed,
            "remaining": remaining,
        }
    )

    return BatchEmbeddingResponse(
        processed=processed,
        failed=failed,
        total=len(events_without_embeddings),
        remaining=remaining,
    )


@router.get("/embeddings/{event_id}", response_model=EmbeddingStatusResponse)
async def get_embedding_status(
    event_id: str,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Get embedding status for a specific event.

    AC12: API endpoint to check embedding status for an event

    Args:
        event_id: UUID of the event
        db: Database session
        embedding_service: Embedding service instance

    Returns:
        EmbeddingStatusResponse with embedding metadata

    Raises:
        404: If event not found
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get embedding metadata
    embedding_meta = await embedding_service.get_embedding(db, event_id)

    if embedding_meta:
        return EmbeddingStatusResponse(
            event_id=event_id,
            exists=True,
            model_version=embedding_meta["model_version"],
            created_at=embedding_meta["created_at"],
        )
    else:
        return EmbeddingStatusResponse(
            event_id=event_id,
            exists=False,
            model_version=None,
            created_at=None,
        )


@router.get("/embeddings/stats", response_model=EmbeddingStatsResponse)
async def get_embedding_stats(
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Get statistics about embedding coverage.

    Returns counts of events with/without embeddings and coverage percentage.

    Args:
        db: Database session
        embedding_service: Embedding service instance

    Returns:
        EmbeddingStatsResponse with coverage statistics
    """
    total_events = db.query(Event).count()
    events_with_embeddings = db.query(EventEmbedding).count()
    events_without = total_events - events_with_embeddings

    coverage = (events_with_embeddings / total_events * 100) if total_events > 0 else 0.0

    return EmbeddingStatsResponse(
        total_events=total_events,
        events_with_embeddings=events_with_embeddings,
        events_without_embeddings=events_without,
        coverage_percent=round(coverage, 2),
        model_version=embedding_service.get_model_version(),
        embedding_dimension=embedding_service.get_embedding_dimension(),
    )


# Story P4-3.2: Similarity Search Response Models
class SimilarEventResponse(BaseModel):
    """Response model for a similar event."""
    event_id: str = Field(description="UUID of the similar event")
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Cosine similarity score (0.0 to 1.0, higher is more similar)"
    )
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="URL to event thumbnail image"
    )
    description: str = Field(description="AI-generated description of the event")
    timestamp: datetime = Field(description="When the event occurred")
    camera_name: str = Field(description="Name of the camera that captured the event")
    camera_id: str = Field(description="UUID of the camera")


class SimilarEventsResponse(BaseModel):
    """Response model for similarity search results."""
    source_event_id: str = Field(description="UUID of the source event searched against")
    similar_events: list[SimilarEventResponse] = Field(
        description="List of similar events sorted by similarity score (highest first)"
    )
    total_results: int = Field(description="Number of similar events found")
    query_params: dict = Field(description="Query parameters used for the search")


@router.get("/similar/{event_id}", response_model=SimilarEventsResponse)
async def find_similar_events(
    event_id: str,
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of similar events to return"
    ),
    min_similarity: float = Query(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold (0.0 to 1.0)"
    ),
    time_window_days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days to search back"
    ),
    camera_id: Optional[str] = Query(
        default=None,
        description="Optional camera UUID to filter results to same camera"
    ),
    db: Session = Depends(get_db),
    similarity_service: SimilarityService = Depends(get_similarity_service),
):
    """
    Find events visually similar to the specified event.

    Story P4-3.2: Similarity Search

    Uses CLIP embeddings and cosine similarity to find past events that look
    similar to the source event. Useful for identifying recurring visitors
    or patterns.

    Args:
        event_id: UUID of the source event to find similar events for
        limit: Maximum number of results (1-100, default 10)
        min_similarity: Minimum similarity threshold (0.0-1.0, default 0.7)
        time_window_days: Days to search back (1-365, default 30)
        camera_id: Optional camera filter
        db: Database session
        similarity_service: Similarity service instance

    Returns:
        SimilarEventsResponse with list of similar events

    Raises:
        404: If event not found or event has no embedding
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if embedding exists
    embedding = db.query(EventEmbedding).filter(
        EventEmbedding.event_id == event_id
    ).first()
    if not embedding:
        raise HTTPException(
            status_code=404,
            detail="Event has no embedding. Generate embeddings first using /context/embeddings/batch"
        )

    try:
        # Find similar events
        similar_events = await similarity_service.find_similar_events(
            db=db,
            event_id=event_id,
            limit=limit,
            min_similarity=min_similarity,
            time_window_days=time_window_days,
            camera_id=camera_id,
        )

        # Convert to response models
        similar_responses = [
            SimilarEventResponse(
                event_id=se.event_id,
                similarity_score=se.similarity_score,
                thumbnail_url=se.thumbnail_url,
                description=se.description,
                timestamp=se.timestamp,
                camera_name=se.camera_name,
                camera_id=se.camera_id,
            )
            for se in similar_events
        ]

        return SimilarEventsResponse(
            source_event_id=event_id,
            similar_events=similar_responses,
            total_results=len(similar_responses),
            query_params={
                "limit": limit,
                "min_similarity": min_similarity,
                "time_window_days": time_window_days,
                "camera_id": camera_id,
            },
        )

    except ValueError as e:
        # This shouldn't happen since we checked for embedding above,
        # but handle it gracefully
        logger.error(
            f"Similarity search failed: {e}",
            extra={"event_id": event_id, "error": str(e)}
        )
        raise HTTPException(status_code=404, detail=str(e))


# Story P4-3.3: Entity Management Response Models
class EntitySummary(BaseModel):
    """Summary of an entity for embedding in event responses."""
    id: str = Field(description="Entity UUID")
    entity_type: str = Field(description="Entity type: person, vehicle, or unknown")
    name: Optional[str] = Field(default=None, description="User-assigned name")
    first_seen_at: datetime = Field(description="First occurrence timestamp")
    occurrence_count: int = Field(description="Number of times this entity has been seen")
    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Match similarity score for this occurrence"
    )


class EntityResponse(BaseModel):
    """Response model for an entity."""
    id: str = Field(description="Entity UUID")
    entity_type: str = Field(description="Entity type: person, vehicle, or unknown")
    name: Optional[str] = Field(default=None, description="User-assigned name")
    first_seen_at: datetime = Field(description="First occurrence timestamp")
    last_seen_at: datetime = Field(description="Most recent occurrence timestamp")
    occurrence_count: int = Field(description="Number of times this entity has been seen")


class EventSummaryForEntity(BaseModel):
    """Event summary for entity detail responses."""
    id: str = Field(description="Event UUID")
    timestamp: datetime = Field(description="Event timestamp")
    description: str = Field(description="AI-generated event description")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    camera_id: str = Field(description="Camera UUID")
    similarity_score: float = Field(description="Similarity score when matched")


class EntityDetailResponse(EntityResponse):
    """Detailed entity response with recent events."""
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Record update timestamp")
    recent_events: list[EventSummaryForEntity] = Field(
        default=[],
        description="Recent events associated with this entity"
    )


class EntityListResponse(BaseModel):
    """Response model for entity list."""
    entities: list[EntityResponse] = Field(description="List of entities")
    total: int = Field(description="Total entity count")


class EntityUpdateRequest(BaseModel):
    """Request model for updating an entity."""
    name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="New name for the entity"
    )


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of entities to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination offset"
    ),
    entity_type: Optional[str] = Query(
        default=None,
        description="Filter by entity type (person, vehicle)"
    ),
    named_only: bool = Query(
        default=False,
        description="Only return named entities"
    ),
    db: Session = Depends(get_db),
    entity_service: EntityService = Depends(get_entity_service),
):
    """
    Get all recognized entities with pagination.

    Story P4-3.3: Recurring Visitor Detection (AC7)

    Returns a list of all entities that have been recognized, sorted by
    most recently seen. Supports filtering by type and named-only.

    Args:
        limit: Maximum number of entities (1-100, default 50)
        offset: Pagination offset
        entity_type: Filter by entity type
        named_only: Only return entities that have been named
        db: Database session
        entity_service: Entity service instance

    Returns:
        EntityListResponse with entities and total count
    """
    entities, total = await entity_service.get_all_entities(
        db=db,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        named_only=named_only,
    )

    return EntityListResponse(
        entities=[EntityResponse(**e) for e in entities],
        total=total,
    )


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity(
    entity_id: str,
    event_limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of recent events to include"
    ),
    db: Session = Depends(get_db),
    entity_service: EntityService = Depends(get_entity_service),
):
    """
    Get a single entity with its associated events.

    Story P4-3.3: Recurring Visitor Detection (AC8)

    Returns detailed information about an entity, including recent events
    that have been associated with it.

    Args:
        entity_id: UUID of the entity
        event_limit: Maximum number of recent events (1-50, default 10)
        db: Database session
        entity_service: Entity service instance

    Returns:
        EntityDetailResponse with entity details and recent events

    Raises:
        404: If entity not found
    """
    entity = await entity_service.get_entity(
        db=db,
        entity_id=entity_id,
        include_events=True,
        event_limit=event_limit,
    )

    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return EntityDetailResponse(
        id=entity["id"],
        entity_type=entity["entity_type"],
        name=entity["name"],
        first_seen_at=entity["first_seen_at"],
        last_seen_at=entity["last_seen_at"],
        occurrence_count=entity["occurrence_count"],
        created_at=entity["created_at"],
        updated_at=entity["updated_at"],
        recent_events=[
            EventSummaryForEntity(
                id=e["id"],
                timestamp=e["timestamp"],
                description=e["description"],
                thumbnail_url=e["thumbnail_url"],
                camera_id=e["camera_id"],
                similarity_score=e["similarity_score"],
            )
            for e in entity.get("recent_events", [])
        ],
    )


@router.put("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: str,
    request: EntityUpdateRequest,
    db: Session = Depends(get_db),
    entity_service: EntityService = Depends(get_entity_service),
):
    """
    Update an entity's name.

    Story P4-3.3: Recurring Visitor Detection (AC9)

    Allows users to assign a name to an entity, e.g., "Mail Carrier",
    "Neighbor Bob", "Amazon Van".

    Args:
        entity_id: UUID of the entity
        request: Update request with new name
        db: Database session
        entity_service: Entity service instance

    Returns:
        Updated EntityResponse

    Raises:
        404: If entity not found
    """
    entity = await entity_service.update_entity(
        db=db,
        entity_id=entity_id,
        name=request.name,
    )

    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return EntityResponse(**entity)


@router.delete("/entities/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: str,
    db: Session = Depends(get_db),
    entity_service: EntityService = Depends(get_entity_service),
):
    """
    Delete an entity.

    Story P4-3.3: Recurring Visitor Detection (AC10)

    Deletes an entity and unlinks all associated events. Events themselves
    are not deleted, only the entity-event associations.

    Args:
        entity_id: UUID of the entity
        db: Database session
        entity_service: Entity service instance

    Raises:
        404: If entity not found
    """
    deleted = await entity_service.delete_entity(db=db, entity_id=entity_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Return 204 No Content on success (implicit)

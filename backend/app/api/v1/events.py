"""
Events API endpoints

Provides REST API for AI-generated semantic event management:
- POST /events - Create new event with AI description
- GET /events - List events with filtering, pagination, and full-text search
- GET /events/{id} - Get single event
- GET /events/stats - Get event statistics and aggregations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc, text
from typing import Optional
from datetime import datetime
import logging
import json
import os
import base64
import uuid

from app.core.database import get_db
from app.models.event import Event
from app.schemas.event import (
    EventCreate,
    EventResponse,
    EventListResponse,
    EventStatsResponse,
    EventFilterParams
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# Thumbnail storage directory
THUMBNAIL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'thumbnails')


def _save_thumbnail_to_filesystem(thumbnail_base64: str, event_id: str) -> str:
    """
    Save base64-encoded thumbnail to filesystem

    Args:
        thumbnail_base64: Base64-encoded JPEG image
        event_id: Event UUID for filename

    Returns:
        Relative path to saved thumbnail

    Raises:
        ValueError: If thumbnail data is invalid
    """
    try:
        # Decode base64 to bytes
        thumbnail_bytes = base64.b64decode(thumbnail_base64)

        # Create date-based subdirectory (YYYY-MM-DD)
        date_str = datetime.now().strftime('%Y-%m-%d')
        date_dir = os.path.join(THUMBNAIL_DIR, date_str)
        os.makedirs(date_dir, exist_ok=True)

        # Save to filesystem
        filename = f"event_{event_id}.jpg"
        file_path = os.path.join(date_dir, filename)

        with open(file_path, 'wb') as f:
            f.write(thumbnail_bytes)

        # Return relative path from data directory
        relative_path = f"thumbnails/{date_str}/{filename}"
        logger.debug(f"Saved thumbnail to {relative_path}")

        return relative_path

    except Exception as e:
        logger.error(f"Failed to save thumbnail for event {event_id}: {e}")
        raise ValueError(f"Invalid thumbnail data: {e}")


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db)
):
    """
    Create new AI-generated semantic event

    Args:
        event_data: Event creation data (camera_id, timestamp, description, etc.)
        db: Database session

    Returns:
        Created event with assigned UUID

    Raises:
        400: Invalid input data (e.g., invalid camera_id, bad thumbnail)
        500: Database error

    Examples:
        POST /events
        {
            "camera_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-11-17T14:30:00Z",
            "description": "Person walking towards front door carrying a package",
            "confidence": 85,
            "objects_detected": ["person", "package"],
            "thumbnail_base64": "/9j/4AAQSkZJRg...",
            "alert_triggered": true
        }
    """
    try:
        # Generate UUID for event
        event_id = str(uuid.uuid4())

        # Handle thumbnail storage
        thumbnail_path = None
        thumbnail_base64 = None

        if event_data.thumbnail_base64:
            try:
                # Save to filesystem
                thumbnail_path = _save_thumbnail_to_filesystem(event_data.thumbnail_base64, event_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        elif event_data.thumbnail_path:
            # Use provided filesystem path
            thumbnail_path = event_data.thumbnail_path

        # Convert objects_detected list to JSON string
        objects_detected_json = json.dumps(event_data.objects_detected)

        # Create event model
        event = Event(
            id=event_id,
            camera_id=event_data.camera_id,
            timestamp=event_data.timestamp,
            description=event_data.description,
            confidence=event_data.confidence,
            objects_detected=objects_detected_json,
            thumbnail_path=thumbnail_path,
            thumbnail_base64=thumbnail_base64,
            alert_triggered=event_data.alert_triggered
        )

        # Save to database
        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(
            f"Created event {event_id} for camera {event_data.camera_id} "
            f"(confidence={event_data.confidence}, objects={event_data.objects_detected})"
        )

        return event

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create event: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event"
        )


@router.get("", response_model=EventListResponse)
def list_events(
    camera_id: Optional[str] = Query(None, description="Filter by camera UUID"),
    start_time: Optional[datetime] = Query(None, description="Filter events after this timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter events before this timestamp"),
    min_confidence: Optional[int] = Query(None, ge=0, le=100, description="Minimum confidence score"),
    object_types: Optional[str] = Query(None, description="Comma-separated object types (e.g., 'person,vehicle')"),
    alert_triggered: Optional[bool] = Query(None, description="Filter by alert status"),
    search_query: Optional[str] = Query(None, min_length=1, max_length=500, description="Full-text search in descriptions"),
    limit: int = Query(50, ge=1, le=500, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort by timestamp"),
    db: Session = Depends(get_db)
):
    """
    List events with filtering, pagination, and full-text search

    Args:
        camera_id: Optional filter by camera UUID
        start_time: Filter events after this timestamp (inclusive)
        end_time: Filter events before this timestamp (inclusive)
        min_confidence: Minimum confidence score (0-100)
        object_types: Comma-separated object types to filter
        alert_triggered: Filter by alert status (true/false)
        search_query: Full-text search in event descriptions (uses FTS5)
        limit: Results per page (default 50, max 500)
        offset: Pagination offset (default 0)
        sort_order: Sort order - "asc" or "desc" (default desc - newest first)
        db: Database session

    Returns:
        EventListResponse with events array and pagination metadata

    Examples:
        - GET /events?limit=10
        - GET /events?camera_id=abc123&start_time=2025-11-01T00:00:00Z
        - GET /events?min_confidence=80&object_types=person,vehicle
        - GET /events?search_query=front+door&limit=20
    """
    try:
        # Build base query
        query = db.query(Event)

        # Apply camera filter
        if camera_id:
            query = query.filter(Event.camera_id == camera_id)

        # Apply time range filters
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)

        # Apply confidence filter
        if min_confidence is not None:
            query = query.filter(Event.confidence >= min_confidence)

        # Apply alert filter
        if alert_triggered is not None:
            query = query.filter(Event.alert_triggered == alert_triggered)

        # Apply object type filter
        if object_types:
            object_type_list = [obj.strip() for obj in object_types.split(',')]
            # Use OR logic - match any of the specified object types
            object_filters = [
                Event.objects_detected.like(f'%"{obj}"%') for obj in object_type_list
            ]
            query = query.filter(or_(*object_filters))

        # Apply full-text search using FTS5
        if search_query:
            # Query FTS5 virtual table for matching event IDs
            fts_query = db.execute(
                text("SELECT id FROM events_fts WHERE description MATCH :query"),
                {"query": search_query}
            )
            matching_ids = [row[0] for row in fts_query.fetchall()]

            if matching_ids:
                query = query.filter(Event.id.in_(matching_ids))
            else:
                # No FTS5 matches - return empty result
                return EventListResponse(
                    events=[],
                    total_count=0,
                    has_more=False,
                    next_offset=None,
                    limit=limit,
                    offset=offset
                )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        if sort_order == "desc":
            query = query.order_by(desc(Event.timestamp))
        else:
            query = query.order_by(asc(Event.timestamp))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        events = query.all()

        # Calculate pagination metadata
        has_more = (offset + limit) < total_count
        next_offset = (offset + limit) if has_more else None

        logger.info(
            f"Listed {len(events)} events (total={total_count}, filters: "
            f"camera={camera_id}, search={search_query}, limit={limit}, offset={offset})"
        )

        return EventListResponse(
            events=events,
            total_count=total_count,
            has_more=has_more,
            next_offset=next_offset,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to list events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list events"
        )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """
    Get single event by ID

    Args:
        event_id: Event UUID
        db: Database session

    Returns:
        Event with full details including thumbnail

    Raises:
        404: Event not found
        500: Database error

    Example:
        GET /events/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        event = db.query(Event).filter(Event.id == event_id).first()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found"
            )

        logger.debug(f"Retrieved event {event_id}")

        return event

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get event"
        )


@router.get("/stats/aggregate", response_model=EventStatsResponse)
def get_event_stats(
    camera_id: Optional[str] = Query(None, description="Filter by camera UUID"),
    start_time: Optional[datetime] = Query(None, description="Start of time range"),
    end_time: Optional[datetime] = Query(None, description="End of time range"),
    db: Session = Depends(get_db)
):
    """
    Get event statistics and aggregations

    Args:
        camera_id: Optional filter by camera UUID
        start_time: Start of time range (default: all time)
        end_time: End of time range (default: now)
        db: Database session

    Returns:
        EventStatsResponse with aggregated statistics:
        - total_events: Total event count
        - events_by_camera: Event counts grouped by camera
        - events_by_object_type: Event counts by detected object type
        - average_confidence: Average confidence score
        - alerts_triggered: Number of events that triggered alerts
        - time_range: Actual time range of events

    Examples:
        - GET /events/stats/aggregate
        - GET /events/stats/aggregate?camera_id=abc123
        - GET /events/stats/aggregate?start_time=2025-11-01T00:00:00Z&end_time=2025-11-17T23:59:59Z
    """
    try:
        # Build base query
        query = db.query(Event)

        # Apply filters
        if camera_id:
            query = query.filter(Event.camera_id == camera_id)
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)

        # Total events
        total_events = query.count()

        # Events by camera
        events_by_camera = {}
        if not camera_id:
            camera_counts = db.query(
                Event.camera_id,
                func.count(Event.id).label('count')
            ).group_by(Event.camera_id)

            if start_time:
                camera_counts = camera_counts.filter(Event.timestamp >= start_time)
            if end_time:
                camera_counts = camera_counts.filter(Event.timestamp <= end_time)

            camera_counts = camera_counts.all()
            events_by_camera = {camera_id: count for camera_id, count in camera_counts}
        else:
            events_by_camera[camera_id] = total_events

        # Events by object type (aggregate from JSON arrays)
        events_by_object_type = {}
        all_events = query.all()
        for event in all_events:
            objects = json.loads(event.objects_detected)
            for obj in objects:
                events_by_object_type[obj] = events_by_object_type.get(obj, 0) + 1

        # Average confidence
        avg_result = query.with_entities(
            func.avg(Event.confidence).label('avg_confidence')
        ).first()
        average_confidence = float(avg_result.avg_confidence) if avg_result.avg_confidence else 0.0

        # Alerts triggered
        alerts_triggered = query.filter(Event.alert_triggered == True).count()

        # Actual time range
        time_range_result = query.with_entities(
            func.min(Event.timestamp).label('min_time'),
            func.max(Event.timestamp).label('max_time')
        ).first()

        time_range = {
            "start": time_range_result.min_time if time_range_result.min_time else None,
            "end": time_range_result.max_time if time_range_result.max_time else None
        }

        logger.info(
            f"Event stats: total={total_events}, cameras={len(events_by_camera)}, "
            f"avg_confidence={average_confidence:.1f}, alerts={alerts_triggered}"
        )

        return EventStatsResponse(
            total_events=total_events,
            events_by_camera=events_by_camera,
            events_by_object_type=events_by_object_type,
            average_confidence=average_confidence,
            alerts_triggered=alerts_triggered,
            time_range=time_range
        )

    except Exception as e:
        logger.error(f"Failed to get event stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get event statistics"
        )

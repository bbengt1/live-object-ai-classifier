"""FrameEmbedding SQLAlchemy ORM model for per-frame embeddings (Story P11-4.2)

Stores CLIP ViT-B/32 embeddings (512-dim) for individual video frames to enable
query-adaptive frame selection during event re-analysis.

Unlike EventEmbedding (one per event), FrameEmbedding stores multiple embeddings
per event - one for each extracted frame from the video clip.

Attributes:
    id: UUID primary key
    event_id: Foreign key to events table (multiple embeddings per event)
    frame_index: Index of the frame within the event (0, 1, 2, ...)
    embedding: JSON array of 512 floats (stored as Text for SQLite compatibility)
    model_version: Version string for the embedding model (e.g., "clip-ViT-B-32-v1")
    created_at: Timestamp when embedding was generated (UTC)

Note:
    Embeddings are stored as JSON arrays in a Text column for SQLite compatibility.
    For PostgreSQL with pgvector, this could be migrated to a VECTOR(512) column.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class FrameEmbedding(Base):
    """
    Per-frame embedding model for query-adaptive frame selection.

    Stores 512-dimensional CLIP embeddings as JSON arrays for
    SQLite compatibility (no pgvector required).

    Each event can have multiple frame embeddings (typically 5-10),
    one for each extracted frame from the video clip.

    Relationships:
        event: Many-to-one relationship with Event model
    """

    __tablename__ = "frame_embeddings"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="UUID primary key"
    )
    event_id = Column(
        String,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to events table (multiple embeddings per event)"
    )
    frame_index = Column(
        Integer,
        nullable=False,
        doc="Index of the frame within the event (0, 1, 2, ...)"
    )
    embedding = Column(
        Text,
        nullable=False,
        doc="JSON array of 512 floats representing the CLIP embedding"
    )
    model_version = Column(
        String(50),
        nullable=False,
        doc="Model version string for compatibility tracking (e.g., clip-ViT-B-32-v1)"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when embedding was generated"
    )

    # Relationship to Event model
    event = relationship("Event", back_populates="frame_embeddings")

    __table_args__ = (
        # Composite index for efficient lookups by event and frame
        Index("ix_frame_embeddings_event_frame", "event_id", "frame_index"),
        # Model version index for compatibility queries
        Index("idx_frame_embeddings_model_version", "model_version"),
        # Unique constraint to prevent duplicate embeddings for same frame
        UniqueConstraint("event_id", "frame_index", name="uq_frame_embedding_event_frame"),
    )

    def __repr__(self):
        return (
            f"<FrameEmbedding(id={self.id}, event_id={self.event_id}, "
            f"frame_index={self.frame_index}, model_version={self.model_version})>"
        )

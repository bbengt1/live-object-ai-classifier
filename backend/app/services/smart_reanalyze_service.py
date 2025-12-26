"""
Smart Reanalyze Service for Query-Adaptive Frame Selection (Story P11-4.3)

This module provides query-adaptive re-analysis functionality. When users ask
targeted questions about events (e.g., "Was there a package delivery?"), this
service selects the most relevant frames based on semantic similarity to the
query before sending them to AI for analysis.

Architecture:
    - Text queries encoded via EmbeddingService.encode_text()
    - Frame embeddings scored via batch_cosine_similarity()
    - Top-K relevant frames selected for AI analysis
    - Query context passed to AI for focused analysis

Flow:
    User Query → encode_text() → Query Embedding
                                       ↓
              get_frame_embeddings() → Frame Embeddings
                                       ↓
                  batch_cosine_similarity() → Scores
                                       ↓
                    select_top_k() → Selected Frames
                                       ↓
               AI Analysis (with query context) → New Description
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.similarity_service import batch_cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class ScoredFrame:
    """Data class representing a scored frame."""
    frame_index: int
    similarity_score: float
    embedding_id: str


@dataclass
class SmartReanalyzeResult:
    """Data class representing the result of smart reanalysis."""
    selected_frames: list[int]  # Indices of selected frames
    frame_scores: list[ScoredFrame]  # All frame scores
    query_embedding_time_ms: float
    frame_scoring_time_ms: float


class SmartReanalyzeService:
    """
    Query-adaptive frame selection for event re-analysis.

    This service enables users to ask targeted questions about events
    and get focused AI analysis based on the most relevant frames.

    Attributes:
        DEFAULT_TOP_K: Default number of frames to select (5)
        DEFAULT_MIN_SIMILARITY: Default minimum similarity threshold (0.2)
    """

    DEFAULT_TOP_K = 5
    DEFAULT_MIN_SIMILARITY = 0.2
    DIVERSITY_THRESHOLD = 0.95  # Skip near-duplicate frames

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize SmartReanalyzeService.

        Args:
            embedding_service: EmbeddingService instance for encoding.
                             If None, will use the global singleton.
        """
        self._embedding_service = embedding_service or get_embedding_service()
        logger.info(
            "SmartReanalyzeService initialized",
            extra={"event_type": "smart_reanalyze_service_init"}
        )

    async def select_relevant_frames(
        self,
        db: Session,
        event_id: str,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> SmartReanalyzeResult:
        """
        Select the most relevant frames for a query.

        Args:
            db: SQLAlchemy database session
            event_id: UUID of the event to analyze
            query: User's natural language query
            top_k: Maximum number of frames to select
            min_similarity: Minimum similarity threshold

        Returns:
            SmartReanalyzeResult with selected frame indices and scores

        Raises:
            ValueError: If no frame embeddings exist for the event
        """
        start_time = time.time()

        # Step 1: Encode the query
        query_start = time.time()
        query_embedding = await self._embedding_service.encode_text(query)
        query_time_ms = (time.time() - query_start) * 1000

        # Step 2: Get frame embeddings for the event
        frame_embeddings = await self._embedding_service.get_frame_embeddings(
            db, event_id
        )

        if not frame_embeddings:
            logger.warning(
                f"No frame embeddings found for event {event_id}",
                extra={
                    "event_type": "smart_reanalyze_no_embeddings",
                    "event_id": event_id,
                }
            )
            # Return empty result - caller should fall back to uniform sampling
            return SmartReanalyzeResult(
                selected_frames=[],
                frame_scores=[],
                query_embedding_time_ms=query_time_ms,
                frame_scoring_time_ms=0,
            )

        # Step 3: Score frames against query
        scoring_start = time.time()
        embeddings = [f["embedding"] for f in frame_embeddings]
        similarities = batch_cosine_similarity(query_embedding, embeddings)

        # Build scored frames list
        scored_frames = [
            ScoredFrame(
                frame_index=frame_embeddings[i]["frame_index"],
                similarity_score=round(similarities[i], 4),
                embedding_id=frame_embeddings[i]["id"],
            )
            for i in range(len(frame_embeddings))
        ]

        # Sort by similarity (highest first)
        scored_frames.sort(key=lambda x: x.similarity_score, reverse=True)

        scoring_time_ms = (time.time() - scoring_start) * 1000

        # Step 4: Select top-K frames with diversity filtering
        selected_frames = self._select_diverse_frames(
            scored_frames=scored_frames,
            frame_embeddings=frame_embeddings,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        total_time_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Smart frame selection completed for event {event_id}",
            extra={
                "event_type": "smart_reanalyze_complete",
                "event_id": event_id,
                "query_length": len(query),
                "frames_scored": len(frame_embeddings),
                "frames_selected": len(selected_frames),
                "top_score": scored_frames[0].similarity_score if scored_frames else 0,
                "query_time_ms": round(query_time_ms, 2),
                "scoring_time_ms": round(scoring_time_ms, 2),
                "total_time_ms": round(total_time_ms, 2),
            }
        )

        return SmartReanalyzeResult(
            selected_frames=selected_frames,
            frame_scores=scored_frames,
            query_embedding_time_ms=query_time_ms,
            frame_scoring_time_ms=scoring_time_ms,
        )

    def _select_diverse_frames(
        self,
        scored_frames: list[ScoredFrame],
        frame_embeddings: list[dict],
        top_k: int,
        min_similarity: float,
    ) -> list[int]:
        """
        Select top-K frames with diversity filtering.

        Avoids selecting near-duplicate frames that might contain
        the same visual information.

        Args:
            scored_frames: Frames sorted by similarity score
            frame_embeddings: Original embeddings data for diversity check
            top_k: Maximum number of frames to select
            min_similarity: Minimum similarity threshold

        Returns:
            List of selected frame indices
        """
        selected = []
        selected_embeddings = []

        # Build lookup for frame embeddings by index
        embedding_by_index = {
            f["frame_index"]: f["embedding"]
            for f in frame_embeddings
        }

        for scored in scored_frames:
            # Skip below threshold
            if scored.similarity_score < min_similarity:
                break

            # Check diversity (skip near-duplicates)
            frame_emb = embedding_by_index[scored.frame_index]
            is_diverse = True

            for sel_emb in selected_embeddings:
                similarity = self._cosine_similarity_single(frame_emb, sel_emb)
                if similarity > self.DIVERSITY_THRESHOLD:
                    is_diverse = False
                    break

            if is_diverse:
                selected.append(scored.frame_index)
                selected_embeddings.append(frame_emb)

            if len(selected) >= top_k:
                break

        return selected

    def _cosine_similarity_single(
        self, vec1: list[float], vec2: list[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np

        a = np.array(vec1, dtype=np.float32)
        b = np.array(vec2, dtype=np.float32)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))


# Global singleton instance
_smart_reanalyze_service: Optional[SmartReanalyzeService] = None


def get_smart_reanalyze_service() -> SmartReanalyzeService:
    """
    Get the global SmartReanalyzeService instance.

    Creates the instance on first call (lazy initialization).

    Returns:
        SmartReanalyzeService singleton instance
    """
    global _smart_reanalyze_service

    if _smart_reanalyze_service is None:
        _smart_reanalyze_service = SmartReanalyzeService()
        logger.info(
            "Global SmartReanalyzeService instance created",
            extra={"event_type": "smart_reanalyze_service_singleton_created"}
        )

    return _smart_reanalyze_service


def reset_smart_reanalyze_service() -> None:
    """
    Reset the global SmartReanalyzeService instance.

    Useful for testing to ensure a fresh instance.
    """
    global _smart_reanalyze_service
    _smart_reanalyze_service = None

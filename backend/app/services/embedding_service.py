"""
Embedding Service for Temporal Context Engine (Story P4-3.1)

This module provides image embedding generation using CLIP ViT-B/32 model
via sentence-transformers for finding similar events and recognizing
recurring visitors/vehicles.

Architecture:
    - Lazy model loading on first embedding request
    - 512-dimensional embeddings (CLIP ViT-B/32 output)
    - Target inference time: <200ms per image
    - SQLite-compatible JSON storage (no pgvector required)
    - Graceful fallback if embedding generation fails

Flow:
    Event Created → EventProcessor → EmbeddingService.generate_embedding()
                                              ↓
                                      CLIP Model (ViT-B/32)
                                              ↓
                                      EventEmbedding (DB)
"""
import asyncio
import base64
import io
import json
import logging
import time
from typing import Optional

from PIL import Image
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate image embeddings using CLIP ViT-B/32 model.

    The service uses lazy loading - the CLIP model is only loaded
    on the first embedding request to minimize startup time.

    Attributes:
        MODEL_NAME: sentence-transformers model identifier
        MODEL_VERSION: Version string stored in database for compatibility
        EMBEDDING_DIM: Output embedding dimension (512 for CLIP ViT-B/32)
    """

    MODEL_NAME = "clip-ViT-B-32"
    MODEL_VERSION = "clip-ViT-B-32-v1"
    EMBEDDING_DIM = 512

    def __init__(self):
        """Initialize EmbeddingService with lazy model loading."""
        self._model = None
        self._model_lock = asyncio.Lock()
        logger.info(
            "EmbeddingService initialized",
            extra={
                "event_type": "embedding_service_init",
                "model_name": self.MODEL_NAME,
                "model_version": self.MODEL_VERSION,
                "embedding_dim": self.EMBEDDING_DIM,
            }
        )

    @property
    def model(self):
        """
        Get the CLIP model, loading it lazily on first access.

        Note: This is a synchronous property. For async contexts,
        use _ensure_model_loaded() instead.

        Returns:
            SentenceTransformer model instance
        """
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """
        Load the CLIP model synchronously.

        This is called internally when the model is first needed.
        Loading takes ~2-3 seconds and downloads ~350MB on first use.
        """
        start_time = time.time()
        logger.info(
            "Loading CLIP model (this may take a few seconds on first use)...",
            extra={"event_type": "embedding_model_loading", "model_name": self.MODEL_NAME}
        )

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.MODEL_NAME)

            load_time_ms = (time.time() - start_time) * 1000
            logger.info(
                "CLIP model loaded successfully",
                extra={
                    "event_type": "embedding_model_loaded",
                    "model_name": self.MODEL_NAME,
                    "load_time_ms": load_time_ms,
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to load CLIP model: {e}",
                exc_info=True,
                extra={"event_type": "embedding_model_load_error", "error": str(e)}
            )
            raise

    async def _ensure_model_loaded(self) -> None:
        """
        Ensure the model is loaded in an async-safe manner.

        Uses a lock to prevent multiple concurrent model loads.
        """
        if self._model is None:
            async with self._model_lock:
                if self._model is None:
                    # Run model loading in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._load_model)

    async def generate_embedding(self, image_bytes: bytes) -> list[float]:
        """
        Generate a 512-dimensional embedding from image bytes.

        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)

        Returns:
            List of 512 floats representing the image embedding

        Raises:
            ValueError: If image_bytes is empty or invalid
            Exception: If embedding generation fails
        """
        if not image_bytes:
            raise ValueError("image_bytes cannot be empty")

        start_time = time.time()

        # Ensure model is loaded
        await self._ensure_model_loaded()

        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary (CLIP expects RGB)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Generate embedding in thread pool (CPU-bound operation)
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self._model.encode(image, convert_to_numpy=True)
            )

            # Convert to list for JSON serialization
            embedding_list = embedding.tolist()

            inference_time_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Embedding generated",
                extra={
                    "event_type": "embedding_generated",
                    "inference_time_ms": inference_time_ms,
                    "embedding_dim": len(embedding_list),
                }
            )

            return embedding_list

        except Exception as e:
            inference_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Embedding generation failed: {e}",
                exc_info=True,
                extra={
                    "event_type": "embedding_generation_error",
                    "inference_time_ms": inference_time_ms,
                    "error": str(e),
                }
            )
            raise

    async def generate_embedding_from_base64(self, base64_str: str) -> list[float]:
        """
        Generate embedding from a base64-encoded image string.

        Args:
            base64_str: Base64-encoded image (with or without data URI prefix)

        Returns:
            List of 512 floats representing the image embedding
        """
        # Strip data URI prefix if present (e.g., "data:image/jpeg;base64,")
        if base64_str.startswith("data:"):
            comma_idx = base64_str.find(",")
            if comma_idx != -1:
                base64_str = base64_str[comma_idx + 1:]

        image_bytes = base64.b64decode(base64_str)
        return await self.generate_embedding(image_bytes)

    async def generate_embedding_from_file(self, file_path: str) -> list[float]:
        """
        Generate embedding from an image file path.

        Args:
            file_path: Path to the image file

        Returns:
            List of 512 floats representing the image embedding
        """
        loop = asyncio.get_event_loop()

        def read_file():
            with open(file_path, "rb") as f:
                return f.read()

        image_bytes = await loop.run_in_executor(None, read_file)
        return await self.generate_embedding(image_bytes)

    async def store_embedding(
        self,
        db: Session,
        event_id: str,
        embedding: list[float],
    ) -> str:
        """
        Store an embedding in the database.

        Args:
            db: SQLAlchemy database session
            event_id: UUID of the associated event
            embedding: List of 512 floats

        Returns:
            ID of the created EventEmbedding record
        """
        from app.models.event_embedding import EventEmbedding

        # Serialize embedding to JSON
        embedding_json = json.dumps(embedding)

        event_embedding = EventEmbedding(
            event_id=event_id,
            embedding=embedding_json,
            model_version=self.MODEL_VERSION,
        )

        db.add(event_embedding)
        db.commit()
        db.refresh(event_embedding)

        logger.debug(
            "Embedding stored",
            extra={
                "event_type": "embedding_stored",
                "event_id": event_id,
                "embedding_id": event_embedding.id,
                "model_version": self.MODEL_VERSION,
            }
        )

        return event_embedding.id

    async def get_embedding(self, db: Session, event_id: str) -> Optional[dict]:
        """
        Get embedding metadata for an event.

        Args:
            db: SQLAlchemy database session
            event_id: UUID of the event

        Returns:
            Dict with embedding metadata, or None if not found
        """
        from app.models.event_embedding import EventEmbedding

        embedding = db.query(EventEmbedding).filter(
            EventEmbedding.event_id == event_id
        ).first()

        if embedding is None:
            return None

        return {
            "id": embedding.id,
            "event_id": embedding.event_id,
            "exists": True,
            "model_version": embedding.model_version,
            "created_at": embedding.created_at.isoformat() if embedding.created_at else None,
        }

    async def get_embedding_vector(self, db: Session, event_id: str) -> Optional[list[float]]:
        """
        Get the actual embedding vector for an event.

        Args:
            db: SQLAlchemy database session
            event_id: UUID of the event

        Returns:
            List of 512 floats, or None if not found
        """
        from app.models.event_embedding import EventEmbedding

        embedding = db.query(EventEmbedding).filter(
            EventEmbedding.event_id == event_id
        ).first()

        if embedding is None:
            return None

        return json.loads(embedding.embedding)

    def get_model_version(self) -> str:
        """Get the current model version string."""
        return self.MODEL_VERSION

    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension (512 for CLIP ViT-B/32)."""
        return self.EMBEDDING_DIM


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global EmbeddingService instance.

    Creates the instance on first call (lazy initialization).

    Returns:
        EmbeddingService singleton instance
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        logger.info(
            "Global EmbeddingService instance created",
            extra={"event_type": "embedding_service_singleton_created"}
        )

    return _embedding_service


async def initialize_embedding_service() -> EmbeddingService:
    """
    Initialize the embedding service and optionally preload the model.

    This can be called during application startup to preload the CLIP model,
    reducing latency on the first embedding request.

    Returns:
        EmbeddingService instance
    """
    service = get_embedding_service()

    # Optionally preload the model (uncomment if desired)
    # await service._ensure_model_loaded()
    # logger.info("Embedding service model preloaded")

    return service

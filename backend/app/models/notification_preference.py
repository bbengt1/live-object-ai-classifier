"""Notification Preference SQLAlchemy ORM model (Story P4-1.4)

Stores user notification preferences for push subscriptions including:
- Per-camera enable/disable
- Object type filters
- Quiet hours with timezone support
- Sound enable/disable
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime, timezone


class NotificationPreference(Base):
    """
    Notification preferences for a push subscription.

    Each PushSubscription has one NotificationPreference record (one-to-one).
    Preferences allow users to filter which notifications they receive.

    Attributes:
        id: UUID primary key
        subscription_id: FK to PushSubscription (unique, one-to-one)
        enabled_cameras: JSON array of camera IDs (null = all cameras)
        enabled_object_types: JSON array of object types (null = all types)
        quiet_hours_enabled: Whether quiet hours are active
        quiet_hours_start: Start time in HH:MM format (e.g., "22:00")
        quiet_hours_end: End time in HH:MM format (e.g., "06:00")
        timezone: IANA timezone string (e.g., "America/New_York")
        sound_enabled: Whether notification sound is enabled
        created_at: Record creation timestamp (UTC)
        updated_at: Last update timestamp (UTC)
    """

    __tablename__ = "notification_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(
        String(36),
        ForeignKey("push_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True
    )

    # Camera filtering (null = all cameras enabled)
    enabled_cameras = Column(JSON, nullable=True, default=None)

    # Object type filtering (null = all types enabled)
    # Valid types: person, vehicle, package, animal
    enabled_object_types = Column(JSON, nullable=True, default=None)

    # Quiet hours configuration
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(5), nullable=True)  # "HH:MM" format
    quiet_hours_end = Column(String(5), nullable=True)    # "HH:MM" format
    timezone = Column(String(64), nullable=False, default="UTC")

    # Sound preference
    sound_enabled = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationship back to subscription
    subscription = relationship("PushSubscription", back_populates="preference")

    def __repr__(self):
        return f"<NotificationPreference(id={self.id}, subscription_id={self.subscription_id})>"

    def to_dict(self):
        """Convert preference to dictionary for API responses."""
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "enabled_cameras": self.enabled_cameras,
            "enabled_object_types": self.enabled_object_types,
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "timezone": self.timezone,
            "sound_enabled": self.sound_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_camera_enabled(self, camera_id: str) -> bool:
        """
        Check if a camera is enabled for notifications.

        Args:
            camera_id: UUID of the camera

        Returns:
            True if camera is enabled (or all cameras enabled)
        """
        if self.enabled_cameras is None:
            return True  # null = all cameras enabled
        return camera_id in self.enabled_cameras

    def is_object_type_enabled(self, object_type: str | None) -> bool:
        """
        Check if an object type is enabled for notifications.

        Args:
            object_type: Smart detection type (person, vehicle, package, animal)

        Returns:
            True if object type is enabled (or all types enabled)
        """
        if self.enabled_object_types is None:
            return True  # null = all types enabled
        if object_type is None:
            return True  # No specific type = general motion, always enabled
        return object_type in self.enabled_object_types

    @classmethod
    def create_default(cls, subscription_id: str) -> "NotificationPreference":
        """
        Create default preferences for a new subscription.

        Default: All cameras, all object types, no quiet hours, sound enabled.

        Args:
            subscription_id: UUID of the push subscription

        Returns:
            New NotificationPreference with default values
        """
        return cls(
            subscription_id=subscription_id,
            enabled_cameras=None,  # All cameras
            enabled_object_types=None,  # All types
            quiet_hours_enabled=False,
            quiet_hours_start=None,
            quiet_hours_end=None,
            timezone="UTC",
            sound_enabled=True,
        )

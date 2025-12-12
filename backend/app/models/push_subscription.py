"""Push Subscription SQLAlchemy ORM model for Web Push notifications (Story P4-1.1, P4-1.4)"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime, timezone


class PushSubscription(Base):
    """
    Push subscription model for Web Push notifications.

    Stores browser push subscription data received from the Push API.
    Each subscription represents a unique browser/device that can receive
    push notifications.

    Attributes:
        id: UUID primary key
        user_id: Optional FK to users table (nullable for anonymous subscriptions)
        endpoint: Push service endpoint URL (unique per subscription)
        p256dh_key: Public key for message encryption (P-256 curve)
        auth_key: Authentication secret for message encryption
        user_agent: Browser user agent string (for debugging)
        created_at: Subscription creation timestamp (UTC)
        last_used_at: Last successful notification delivery timestamp (UTC)
    """

    __tablename__ = "push_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    endpoint = Column(Text, nullable=False, unique=True, index=True)
    p256dh_key = Column(Text, nullable=False)
    auth_key = Column(Text, nullable=False)
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # One-to-one relationship with NotificationPreference (Story P4-1.4)
    preference = relationship(
        "NotificationPreference",
        back_populates="subscription",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_push_subscriptions_user', 'user_id'),
        Index('idx_push_subscriptions_created', 'created_at'),
    )

    def __repr__(self):
        # Truncate endpoint for security in logs
        endpoint_preview = self.endpoint[:50] + "..." if self.endpoint and len(self.endpoint) > 50 else self.endpoint
        return f"<PushSubscription(id={self.id}, endpoint={endpoint_preview})>"

    def to_dict(self):
        """Convert subscription to dictionary for API responses."""
        # Truncate endpoint for security
        endpoint_truncated = None
        if self.endpoint:
            if len(self.endpoint) > 60:
                endpoint_truncated = self.endpoint[:30] + "..." + self.endpoint[-20:]
            else:
                endpoint_truncated = self.endpoint

        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": endpoint_truncated,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def get_subscription_info(self):
        """
        Get subscription info in the format expected by pywebpush.

        Returns:
            dict: Subscription info with endpoint and keys
        """
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh_key,
                "auth": self.auth_key
            }
        }

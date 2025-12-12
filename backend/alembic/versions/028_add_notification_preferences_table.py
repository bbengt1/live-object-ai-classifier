"""add_notification_preferences_table

Revision ID: 028_add_notification_prefs
Revises: 8332702b9c11
Create Date: 2025-12-10

Story P4-1.4: Notification Preferences
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028_add_notification_prefs'
down_revision = '8332702b9c11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create notification_preferences table."""
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'subscription_id',
            sa.String(36),
            sa.ForeignKey('push_subscriptions.id', ondelete='CASCADE'),
            nullable=False,
            unique=True
        ),
        sa.Column('enabled_cameras', sa.JSON(), nullable=True),
        sa.Column('enabled_object_types', sa.JSON(), nullable=True),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('quiet_hours_start', sa.String(5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(5), nullable=True),
        sa.Column('timezone', sa.String(64), nullable=False, server_default='UTC'),
        sa.Column('sound_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create index on subscription_id for fast lookups
    op.create_index(
        'idx_notification_preferences_subscription',
        'notification_preferences',
        ['subscription_id']
    )


def downgrade() -> None:
    """Drop notification_preferences table."""
    op.drop_index('idx_notification_preferences_subscription', 'notification_preferences')
    op.drop_table('notification_preferences')

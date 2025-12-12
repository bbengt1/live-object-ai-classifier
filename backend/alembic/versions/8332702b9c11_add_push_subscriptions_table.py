"""add_push_subscriptions_table

Revision ID: 8332702b9c11
Revises: 027_add_analysis_mode_index
Create Date: 2025-12-10 12:35:41.171692

Story P4-1.1: Implement Web Push Backend
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8332702b9c11'
down_revision = '027_add_analysis_mode_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create push_subscriptions table for Web Push notifications."""
    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('endpoint', sa.Text(), nullable=False, unique=True),
        sa.Column('p256dh_key', sa.Text(), nullable=False),
        sa.Column('auth_key', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index('idx_push_subscriptions_user', 'push_subscriptions', ['user_id'])
    op.create_index('idx_push_subscriptions_endpoint', 'push_subscriptions', ['endpoint'])
    op.create_index('idx_push_subscriptions_created', 'push_subscriptions', ['created_at'])


def downgrade() -> None:
    """Drop push_subscriptions table."""
    op.drop_index('idx_push_subscriptions_created', 'push_subscriptions')
    op.drop_index('idx_push_subscriptions_endpoint', 'push_subscriptions')
    op.drop_index('idx_push_subscriptions_user', 'push_subscriptions')
    op.drop_table('push_subscriptions')

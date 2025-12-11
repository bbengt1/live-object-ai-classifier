"""add_recognized_entities_tables

Story P4-3.3: Recurring Visitor Detection

Adds recognized_entities and entity_events tables for storing and tracking
recurring visitors in the Temporal Context Engine.

Revision ID: 030_add_recognized_entities
Revises: 029_add_event_embeddings
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '030_add_recognized_entities'
down_revision = '029_add_event_embeddings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create recognized_entities and entity_events tables."""
    # Create recognized_entities table
    op.create_table(
        'recognized_entities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('reference_embedding', sa.Text(), nullable=False),  # JSON array of 512 floats
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for recognized_entities
    op.create_index('idx_recognized_entities_last_seen', 'recognized_entities', ['last_seen_at'])
    op.create_index('idx_recognized_entities_entity_type', 'recognized_entities', ['entity_type'])

    # Create entity_events junction table
    op.create_table(
        'entity_events',
        sa.Column('entity_id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['entity_id'], ['recognized_entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('entity_id', 'event_id'),
    )

    # Create index for efficient event lookups
    op.create_index('idx_entity_events_event_id', 'entity_events', ['event_id'])


def downgrade() -> None:
    """Drop recognized_entities and entity_events tables."""
    op.drop_index('idx_entity_events_event_id', table_name='entity_events')
    op.drop_table('entity_events')
    op.drop_index('idx_recognized_entities_entity_type', table_name='recognized_entities')
    op.drop_index('idx_recognized_entities_last_seen', table_name='recognized_entities')
    op.drop_table('recognized_entities')

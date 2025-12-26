"""add_frame_embeddings_table

Revision ID: f9c5d7e8a1b2
Revises: e8b4f2d6c7a9
Create Date: 2025-12-26 16:30:00.000000

Story P11-4.2: Implement Frame Embedding Storage and Generation

Creates the frame_embeddings table for storing per-frame CLIP embeddings
to enable query-adaptive frame selection during event re-analysis.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9c5d7e8a1b2'
down_revision = 'e8b4f2d6c7a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create frame_embeddings table."""
    op.create_table(
        'frame_embeddings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('frame_index', sa.Integer(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'frame_index', name='uq_frame_embedding_event_frame')
    )

    # Create indexes
    op.create_index('ix_frame_embeddings_event_id', 'frame_embeddings', ['event_id'])
    op.create_index('ix_frame_embeddings_event_frame', 'frame_embeddings', ['event_id', 'frame_index'])
    op.create_index('idx_frame_embeddings_model_version', 'frame_embeddings', ['model_version'])


def downgrade() -> None:
    """Drop frame_embeddings table."""
    op.drop_index('idx_frame_embeddings_model_version', table_name='frame_embeddings')
    op.drop_index('ix_frame_embeddings_event_frame', table_name='frame_embeddings')
    op.drop_index('ix_frame_embeddings_event_id', table_name='frame_embeddings')
    op.drop_table('frame_embeddings')

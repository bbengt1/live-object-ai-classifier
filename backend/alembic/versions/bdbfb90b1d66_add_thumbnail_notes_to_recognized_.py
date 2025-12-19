"""add_thumbnail_notes_to_recognized_entities

Story P7-4.1: Design Entities Data Model
Adds thumbnail_path and notes columns to recognized_entities table.

Revision ID: bdbfb90b1d66
Revises: 051_homekit_stream_quality
Create Date: 2025-12-19 10:05:22.527178

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdbfb90b1d66'
down_revision = '051_homekit_stream_quality'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add thumbnail_path and notes columns to recognized_entities."""
    op.add_column('recognized_entities', sa.Column('thumbnail_path', sa.String(length=512), nullable=True))
    op.add_column('recognized_entities', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove thumbnail_path and notes columns from recognized_entities."""
    op.drop_column('recognized_entities', 'notes')
    op.drop_column('recognized_entities', 'thumbnail_path')

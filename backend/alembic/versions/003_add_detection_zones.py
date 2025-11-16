"""Add detection_zones to cameras table

Revision ID: 003
Revises: 002
Create Date: 2025-11-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add detection_zones JSON column to cameras table"""

    # Check if column already exists (from partial migration run)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('cameras')]

    if 'detection_zones' not in columns:
        op.add_column('cameras', sa.Column('detection_zones', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove detection_zones column from cameras table"""

    op.drop_column('cameras', 'detection_zones')

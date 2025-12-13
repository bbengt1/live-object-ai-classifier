"""add_object_type_distribution_to_patterns

Story P4-7.1: Baseline Activity Learning

Adds object_type_distribution column to camera_activity_patterns table
for tracking frequency of detected object types per camera. This enables
behavioral anomaly detection by comparing event object types against
historical baselines.

Revision ID: 039_add_object_type_distribution
Revises: 038_add_prompt_fields
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '039_add_object_type_distribution'
down_revision = '038_add_prompt_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add object_type_distribution column to camera_activity_patterns."""
    op.add_column(
        'camera_activity_patterns',
        sa.Column('object_type_distribution', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove object_type_distribution column from camera_activity_patterns."""
    op.drop_column('camera_activity_patterns', 'object_type_distribution')

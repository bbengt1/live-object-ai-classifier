"""Add HomeKit database models (Story P5-1.1)

Revision ID: 044_add_homekit_models
Revises: 043_add_entity_alert_fields
Create Date: 2025-12-14

Adds:
- homekit_config table for persistent HomeKit bridge configuration
- homekit_accessories table for camera-to-accessory mapping
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '044_add_homekit_models'
down_revision = '043_add_entity_alert_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create HomeKit configuration and accessories tables."""

    # Create homekit_config table (singleton - stores bridge configuration)
    op.create_table(
        'homekit_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('bridge_name', sa.String(64), nullable=False, server_default='ArgusAI'),
        sa.Column('pin_code', sa.String(256), nullable=True),  # Fernet encrypted
        sa.Column('port', sa.Integer(), nullable=False, server_default='51826'),
        sa.Column('motion_reset_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_motion_duration', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create homekit_accessories table (maps cameras to HomeKit accessories)
    op.create_table(
        'homekit_accessories',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('config_id', sa.Integer(), sa.ForeignKey('homekit_config.id', ondelete='CASCADE'), nullable=False, server_default='1'),
        sa.Column('camera_id', sa.String(36), sa.ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False),
        sa.Column('accessory_aid', sa.Integer(), nullable=True),
        sa.Column('accessory_type', sa.String(32), nullable=False, server_default='motion'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create indexes for common queries
    op.create_index('idx_homekit_accessories_camera_id', 'homekit_accessories', ['camera_id'])
    op.create_index('idx_homekit_accessories_enabled', 'homekit_accessories', ['enabled'])


def downgrade() -> None:
    """Drop HomeKit tables."""

    # Drop indexes first
    op.drop_index('idx_homekit_accessories_enabled', table_name='homekit_accessories')
    op.drop_index('idx_homekit_accessories_camera_id', table_name='homekit_accessories')

    # Drop tables (accessories first due to FK)
    op.drop_table('homekit_accessories')
    op.drop_table('homekit_config')

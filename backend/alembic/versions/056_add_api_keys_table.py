"""add_api_keys_table

Revision ID: 056
Revises: 055
Create Date: 2025-12-28 10:00:00.000000

Story P13-1.1: Create APIKey Database Model and Migration
- API keys for secure programmatic access
- bcrypt hashed storage (never plaintext)
- Scoped permissions and rate limiting
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '056'
down_revision = '055'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create api_keys table."""
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('prefix', sa.String(8), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('scopes', sa.JSON, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_ip', sa.String(45), nullable=True),
        sa.Column('usage_count', sa.Integer, nullable=False, default=0),
        sa.Column('rate_limit_per_minute', sa.Integer, nullable=False, default=100),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Index for prefix lookup (used during authentication)
    op.create_index('ix_api_keys_prefix', 'api_keys', ['prefix'])

    # Index for listing active keys
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])

    # Index for audit queries by creator
    op.create_index('ix_api_keys_created_by', 'api_keys', ['created_by'])


def downgrade() -> None:
    """Drop api_keys table."""
    op.drop_index('ix_api_keys_created_by', 'api_keys')
    op.drop_index('ix_api_keys_is_active', 'api_keys')
    op.drop_index('ix_api_keys_prefix', 'api_keys')
    op.drop_table('api_keys')

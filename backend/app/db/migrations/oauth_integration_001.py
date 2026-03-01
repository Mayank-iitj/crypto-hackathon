"""Add OAuth fields to User model

Revision ID: oauth_integration_001
Revises: 
Create Date: 2026-03-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'oauth_integration_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add OAuth fields to users table."""
    
    # Make password_hash nullable (for OAuth-only users)
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(255),
                    nullable=True)
    
    # Add OAuth provider fields
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_provider_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('oauth_access_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('oauth_refresh_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('oauth_token_expiry', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    
    # Create indexes for OAuth lookups
    op.create_index('ix_users_oauth_provider', 'users', ['oauth_provider'])
    op.create_index('ix_users_oauth_provider_id', 'users', ['oauth_provider_id'])
    
    # Create unique constraint for OAuth provider + provider_id combination
    op.create_index(
        'ix_users_oauth_unique',
        'users',
        ['oauth_provider', 'oauth_provider_id'],
        unique=True,
        postgresql_where=sa.text("oauth_provider IS NOT NULL AND oauth_provider_id IS NOT NULL")
    )


def downgrade() -> None:
    """Remove OAuth fields from users table."""
    
    # Drop indexes
    op.drop_index('ix_users_oauth_unique', 'users')
    op.drop_index('ix_users_oauth_provider_id', 'users')
    op.drop_index('ix_users_oauth_provider', 'users')
    
    # Drop OAuth columns
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'oauth_token_expiry')
    op.drop_column('users', 'oauth_refresh_token')
    op.drop_column('users', 'oauth_access_token')
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'oauth_provider')
    
    # Make password_hash not nullable again
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(255),
                    nullable=False)

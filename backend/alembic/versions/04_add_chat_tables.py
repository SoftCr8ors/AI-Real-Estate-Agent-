"""Add chat tables for Phase 4: AI Agent

Revision ID: 004_add_chat_tables
Revises: 001_create_tables
Create Date: 2026-10-20

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_chat_tables"
down_revision = "001_create_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Phase 4 enhancements to existing tables and create new columns."""

    # Update conversations table for Phase 4
    op.add_column('conversations', sa.Column('customer_name', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('customer_email', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('customer_phone', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('status', sa.String(), nullable=False, server_default='active'))
    op.add_column('conversations', sa.Column('customer_state', sa.Text(), nullable=True))
    op.add_column('conversations', sa.Column('state_summary', sa.Text(), nullable=True))
    op.add_column('conversations', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # Make customer_id nullable (allow anonymous chats)
    op.alter_column('conversations', 'customer_id',
                    existing_type=sa.Integer(),
                    nullable=True)

    # Update messages table for Phase 4
    op.add_column('messages', sa.Column('token_count', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('status', sa.String(), nullable=False, server_default='completed'))

    # Update leads table for Phase 4
    op.add_column('leads', sa.Column('source', sa.String(), nullable=False, server_default='chat'))
    op.add_column('leads', sa.Column('expected_timeline', sa.String(), nullable=True))
    op.alter_column('leads', 'customer_id',
                    existing_type=sa.Integer(),
                    nullable=True)

    # Update lead_status_history table
    op.add_column('lead_status_history', sa.Column('automated', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('lead_status_history', sa.Column('reason', sa.Text(), nullable=True))

    # Update app_settings table for Phase 4
    op.add_column('app_settings', sa.Column('category', sa.String(), nullable=False, server_default='general'))
    op.add_column('app_settings', sa.Column('updated_by', sa.Integer(), nullable=True))
    op.add_column('app_settings', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('app_settings', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # Create indexes for better performance
    op.create_index('ix_conversations_status', 'conversations', ['status'])
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', 'created_at'])
    op.create_index('ix_leads_status_created', 'leads', ['status', 'created_at'])


def downgrade() -> None:
    """Remove Phase 4 enhancements."""

    # Drop indexes
    op.drop_index('ix_leads_status_created', 'leads')
    op.drop_index('ix_messages_conversation_created', 'messages')
    op.drop_index('ix_conversations_status', 'conversations')

    # Remove app_settings columns
    op.drop_column('app_settings', 'created_at')
    op.drop_column('app_settings', 'updated_at')
    op.drop_column('app_settings', 'updated_by')
    op.drop_column('app_settings', 'category')

    # Remove lead_status_history columns
    op.drop_column('lead_status_history', 'reason')
    op.drop_column('lead_status_history', 'automated')

    # Remove leads columns
    op.alter_column('leads', 'customer_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    op.drop_column('leads', 'expected_timeline')
    op.drop_column('leads', 'source')

    # Remove messages columns
    op.drop_column('messages', 'status')
    op.drop_column('messages', 'token_count')

    # Remove conversations columns
    op.alter_column('conversations', 'customer_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    op.drop_column('conversations', 'updated_at')
    op.drop_column('conversations', 'state_summary')
    op.drop_column('conversations', 'customer_state')
    op.drop_column('conversations', 'status')
    op.drop_column('conversations', 'customer_phone')
    op.drop_column('conversations', 'customer_email')
    op.drop_column('conversations', 'customer_name')

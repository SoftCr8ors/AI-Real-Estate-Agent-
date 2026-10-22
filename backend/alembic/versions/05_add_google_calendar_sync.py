"""add google calendar sync fields

Revision ID: 005
Revises: 004_add_chat_tables
Create Date: 2026-10-22
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004_add_chat_tables"
branch_labels = None
depends_on = None


def upgrade():
    """Add Google Calendar sync fields to appointments table"""

    # Add new columns to appointments table
    op.add_column(
        "appointments",
        sa.Column("google_event_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "appointments",
        sa.Column("google_calendar_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "appointments",
        sa.Column(
            "sync_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="pending, synced, failed"
        )
    )
    op.add_column(
        "appointments",
        sa.Column("sync_error", sa.Text(), nullable=True)
    )
    op.add_column(
        "appointments",
        sa.Column("last_sync_attempt", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "appointments",
        sa.Column("sync_retry_count", sa.Integer(), nullable=False, server_default="0")
    )

    # Create indexes for performance
    op.create_index(
        "ix_appointments_google_event_id",
        "appointments",
        ["google_event_id"],
        unique=False
    )
    op.create_index(
        "ix_appointments_sync_status",
        "appointments",
        ["sync_status"],
        unique=False
    )

    # Add check constraint for sync_status
    op.create_check_constraint(
        "valid_sync_status",
        "appointments",
        "sync_status IN ('pending', 'synced', 'failed')"
    )


def downgrade():
    """Remove Google Calendar sync fields"""

    # Drop constraints and indexes
    op.drop_constraint("valid_sync_status", "appointments", type_="check")
    op.drop_index("ix_appointments_sync_status", table_name="appointments")
    op.drop_index("ix_appointments_google_event_id", table_name="appointments")

    # Drop columns
    op.drop_column("appointments", "sync_retry_count")
    op.drop_column("appointments", "last_sync_attempt")
    op.drop_column("appointments", "sync_error")
    op.drop_column("appointments", "sync_status")
    op.drop_column("appointments", "google_calendar_id")
    op.drop_column("appointments", "google_event_id")

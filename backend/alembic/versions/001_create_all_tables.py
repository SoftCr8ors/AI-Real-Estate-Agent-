"""create all tables

Revision ID: 001_create_tables
Revises: 2e852fcdb884
Create Date: 2024-10-11 02:45:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_create_tables"
down_revision = "2e852fcdb884"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enums safely (skip if already exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('admin', 'agent');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE propertytype AS ENUM ('apartment', 'villa', 'townhouse', 'penthouse', 'studio');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE listingtype AS ENUM ('buy', 'rent');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE availabilitystatus AS ENUM ('available', 'sold', 'rented', 'unavailable');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rentperiod AS ENUM ('yearly', 'monthly');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE leadstatus AS ENUM ('new', 'warm', 'hot', 'qualified', 'viewing_scheduled', 'converted', 'lost');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE appointmentstatus AS ENUM ('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # admin_users table
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", postgresql.ENUM(name="userrole", create_type=False), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_users_id"), "admin_users", ["id"], unique=False)
    op.create_index(op.f("ix_admin_users_email"), "admin_users", ["email"], unique=True)

    # amenities table
    op.create_table(
        "amenities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_amenities_id"), "amenities", ["id"], unique=False)
    op.create_index(op.f("ix_amenities_name"), "amenities", ["name"], unique=True)

    # customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("whatsapp_id", sa.String(), nullable=True),
        sa.Column("preferred_contact", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_id"), "customers", ["id"], unique=False)
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=False)
    op.create_index(op.f("ix_customers_phone"), "customers", ["phone"], unique=False)
    op.create_index(op.f("ix_customers_whatsapp_id"), "customers", ["whatsapp_id"], unique=True)

    # properties table
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("property_type", postgresql.ENUM(name="propertytype", create_type=False), nullable=False),
        sa.Column("listing_type", postgresql.ENUM(name="listingtype", create_type=False), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="AED"),
        sa.Column("rent_period", postgresql.ENUM(name="rentperiod", create_type=False), nullable=True),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("community", sa.String(), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
        sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Integer(), nullable=False),
        sa.Column("size_sqft", sa.Integer(), nullable=False),
        sa.Column("furnished", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("listing_url", sa.String(), nullable=True),
        sa.Column("availability", postgresql.ENUM(name="availabilitystatus", create_type=False), nullable=False, server_default="available"),
        sa.Column("is_demo", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_properties_id"), "properties", ["id"], unique=False)
    op.create_index(op.f("ix_properties_reference"), "properties", ["reference"], unique=True)
    op.create_index(op.f("ix_properties_property_type"), "properties", ["property_type"], unique=False)
    op.create_index(op.f("ix_properties_listing_type"), "properties", ["listing_type"], unique=False)
    op.create_index(op.f("ix_properties_location"), "properties", ["location"], unique=False)
    op.create_index(op.f("ix_properties_community"), "properties", ["community"], unique=False)
    op.create_index(op.f("ix_properties_bedrooms"), "properties", ["bedrooms"], unique=False)
    op.create_index(op.f("ix_properties_availability"), "properties", ["availability"], unique=False)

    # property_images table
    op.create_table(
        "property_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("display_order", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_property_images_id"), "property_images", ["id"], unique=False)

    # property_amenities association table
    op.create_table(
        "property_amenities",
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("amenity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["amenity_id"], ["amenities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", "amenity_id"),
    )

    # conversations table
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_id"), "conversations", ["id"], unique=False)
    op.create_index(op.f("ix_conversations_customer_id"), "conversations", ["customer_id"], unique=False)
    op.create_index(op.f("ix_conversations_session_id"), "conversations", ["session_id"], unique=True)

    # messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)

    # leads table
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("status", postgresql.ENUM(name="leadstatus", create_type=False), nullable=False, server_default="new"),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leads_id"), "leads", ["id"], unique=False)
    op.create_index(op.f("ix_leads_customer_id"), "leads", ["customer_id"], unique=False)
    op.create_index(op.f("ix_leads_conversation_id"), "leads", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_leads_status"), "leads", ["status"], unique=False)
    op.create_index(op.f("ix_leads_assigned_to"), "leads", ["assigned_to"], unique=False)

    # lead_properties association table
    op.create_table(
        "lead_properties",
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("interested", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("lead_id", "property_id"),
    )

    # lead_status_history table
    op.create_table(
        "lead_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("old_status", postgresql.ENUM(name="leadstatus", create_type=False), nullable=True),
        sa.Column("new_status", postgresql.ENUM(name="leadstatus", create_type=False), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lead_status_history_id"), "lead_status_history", ["id"], unique=False)
    op.create_index(op.f("ix_lead_status_history_lead_id"), "lead_status_history", ["lead_id"], unique=False)

    # working_hours table
    op.create_table(
        "working_hours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="valid_day_of_week"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_working_hours_id"), "working_hours", ["id"], unique=False)

    # blocked_times table
    op.create_table(
        "blocked_times",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blocked_times_id"), "blocked_times", ["id"], unique=False)
    op.create_index(op.f("ix_blocked_times_date"), "blocked_times", ["date"], unique=False)

    # appointments table
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("status", postgresql.ENUM(name="appointmentstatus", create_type=False), nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("duration_minutes > 0", name="positive_duration"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_appointments_id"), "appointments", ["id"], unique=False)
    op.create_index(op.f("ix_appointments_lead_id"), "appointments", ["lead_id"], unique=False)
    op.create_index(op.f("ix_appointments_property_id"), "appointments", ["property_id"], unique=False)
    op.create_index(op.f("ix_appointments_agent_id"), "appointments", ["agent_id"], unique=False)
    op.create_index(op.f("ix_appointments_scheduled_at"), "appointments", ["scheduled_at"], unique=False)
    op.create_index(op.f("ix_appointments_status"), "appointments", ["status"], unique=False)

    # handoffs table
    op.create_table(
        "handoffs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_handoffs_id"), "handoffs", ["id"], unique=False)
    op.create_index(op.f("ix_handoffs_conversation_id"), "handoffs", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_handoffs_lead_id"), "handoffs", ["lead_id"], unique=False)
    op.create_index(op.f("ix_handoffs_agent_id"), "handoffs", ["agent_id"], unique=False)

    # notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("related_entity_type", sa.String(), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["recipient_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_recipient_id"), "notifications", ["recipient_id"], unique=False)
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)

    # app_settings table
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("is_encrypted", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_app_settings_id"), "app_settings", ["id"], unique=False)
    op.create_index(op.f("ix_app_settings_key"), "app_settings", ["key"], unique=True)

    # webhook_events table
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("processed", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_events_id"), "webhook_events", ["id"], unique=False)
    op.create_index(op.f("ix_webhook_events_source"), "webhook_events", ["source"], unique=False)
    op.create_index(op.f("ix_webhook_events_event_type"), "webhook_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_webhook_events_processed"), "webhook_events", ["processed"], unique=False)


def downgrade() -> None:
    # Drop all tables
    op.drop_table("webhook_events")
    op.drop_table("app_settings")
    op.drop_table("notifications")
    op.drop_table("handoffs")
    op.drop_table("appointments")
    op.drop_table("blocked_times")
    op.drop_table("working_hours")
    op.drop_table("lead_status_history")
    op.drop_table("lead_properties")
    op.drop_table("leads")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("property_amenities")
    op.drop_table("property_images")
    op.drop_table("properties")
    op.drop_table("customers")
    op.drop_table("amenities")
    op.drop_table("admin_users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS appointmentstatus")
    op.execute("DROP TYPE IF EXISTS leadstatus")
    op.execute("DROP TYPE IF EXISTS rentperiod")
    op.execute("DROP TYPE IF EXISTS availabilitystatus")
    op.execute("DROP TYPE IF EXISTS listingtype")
    op.execute("DROP TYPE IF EXISTS propertytype")
    op.execute("DROP TYPE IF EXISTS userrole")

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models._types import enum_values


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, default=45, nullable=False)
    status = Column(
        SQLEnum(AppointmentStatus, name="appointmentstatus", create_constraint=False, values_callable=enum_values),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    notes = Column(String, nullable=True)

    # Google Calendar sync fields
    google_event_id = Column(String(255), nullable=True, index=True)
    google_calendar_id = Column(String(255), nullable=True)
    sync_status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        comment="pending, synced, failed"
    )
    sync_error = Column(Text, nullable=True)
    last_sync_attempt = Column(DateTime(timezone=True), nullable=True)
    sync_retry_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="appointments")
    property = relationship("Property")
    agent = relationship("AdminUser")

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="positive_duration"),
        CheckConstraint(
            "sync_status IN ('pending', 'synced', 'failed')",
            name="valid_sync_status"
        ),
    )

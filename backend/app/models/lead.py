"""
Lead models - capture and track customer interest through conversation.
Phase 4: Automated lead creation and status progression rules.
"""

import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models._types import enum_values


class LeadStatus(str, enum.Enum):
    """
    Lead status progression (automated by backend rules):
    NEW → WARM → HOT → QUALIFIED → VIEWING_SCHEDULED → CONVERTED/LOST
    """
    NEW = "new"                          # Lead created, minimal info
    WARM = "warm"                        # Buy/rent + location or budget known, 1+ details viewed
    HOT = "hot"                          # Viewing/handoff requested OR contact given with <3mo timeline
    QUALIFIED = "qualified"              # Name + phone/email + buy/rent + budget + location + selected property
    VIEWING_SCHEDULED = "viewing_scheduled"  # Appointment booked
    CONVERTED = "converted"              # Deal closed
    LOST = "lost"                        # Customer lost or inactive


class LeadSource(str, enum.Enum):
    """How the lead was created"""
    CHAT = "chat"                        # From AI chat conversation
    FORM = "form"                        # Direct form submission
    PHONE = "phone"                      # Phone inquiry
    WALK_IN = "walk_in"                  # Office visit
    REFERRAL = "referral"                # Referred by someone


class Lead(Base):
    """
    A potential customer captured from conversation.
    Created automatically when serious interest is detected.
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # Links
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True,
index=True)

    # Lead information
    source = Column(
        SQLEnum(LeadSource, name="leadsource", create_constraint=False, values_callable=enum_values,
native_enum=False),
        default=LeadSource.CHAT,
        nullable=False
    )

    status = Column(
        SQLEnum(LeadStatus, name="leadstatus", create_constraint=False, values_callable=enum_values,
native_enum=False),
        default=LeadStatus.NEW,
        nullable=False,
        index=True
    )

    # Customer requirements (captured from conversation)
    requirements = Column(Text, nullable=True)  # JSON: {"listing_type": "buy", "location": "...", ...}
    notes = Column(Text, nullable=True)

    # Assignment
    assigned_to = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Timeline
    expected_timeline = Column(String, nullable=True)  # "within_1_month", "1-3_months", "3-6_months", "6+_months"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="lead")
    customer = relationship("Customer", backref="leads")
    status_history = relationship("LeadStatusHistory", back_populates="lead", cascade="all, delete-orphan")


class LeadProperty(Base):
    """Properties the customer has shown interest in"""
    __tablename__ = "lead_properties"

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    interested = Column(Integer, default=0, nullable=False)  # 0=viewed, 1=interested


class LeadStatusHistory(Base):
    """Audit log of all status changes"""
    __tablename__ = "lead_status_history"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)

    old_status = Column(
        SQLEnum(LeadStatus, name="leadstatus", create_constraint=False, values_callable=enum_values,
native_enum=False),
        nullable=True
    )
    new_status = Column(
        SQLEnum(LeadStatus, name="leadstatus", create_constraint=False, values_callable=enum_values,
native_enum=False),
        nullable=False
    )

    # Who/what triggered the change
    changed_by = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    automated = Column(Integer, default=1, nullable=False)  # 1=auto by rules, 0=manual by admin

    reason = Column(Text, nullable=True)  # Why status changed
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="status_history")

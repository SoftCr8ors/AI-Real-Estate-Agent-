from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class LeadStatus(str, enum.Enum):
    NEW = "new"
    WARM = "warm"
    HOT = "hot"
    QUALIFIED = "qualified"
    VIEWING_SCHEDULED = "viewing_scheduled"
    CONVERTED = "converted"
    LOST = "lost"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True)
    requirements = Column(Text, nullable=True)  # Summary of what customer wants
    notes = Column(Text, nullable=True)
    assigned_to = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeadProperty(Base):
    """Association table with extra fields for lead-property relationship"""
    __tablename__ = "lead_properties"

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    interested = Column(Integer, default=0)  # 0=just viewed, 1=expressed interest


class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(SQLEnum(LeadStatus), nullable=True)
    new_status = Column(SQLEnum(LeadStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
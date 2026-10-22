"""
Conversation model - tracks chat sessions with AI agent state.
Enhanced for Phase 4: AI Agent & Chat API
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Conversation(Base):
    """
    A conversation session with a customer.
    Each session tracks the full chat history and customer state.
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Session identification
    session_id = Column(String, unique=True, nullable=False, index=True)
    
    # Link to customer (if they exist, optional for anonymous chats)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Customer identification (may be collected during chat)
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    
    # Conversation metadata
    channel = Column(String, default="web", nullable=False)  # web, whatsapp, etc.
    status = Column(String, default="active", nullable=False)  # active, ended, transferred
    
    # AI Agent State (NEW for Phase 4)
    # Customer state (JSON-serialized knowledge we've gathered)
    # Format: {"listing_type": "buy", "location": "Dubai Marina", "budget": 1500000, ...}
    customer_state = Column(Text, nullable=True)  # JSON string
    
    # Summary of what we know/don't know (for AI context)
    state_summary = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
order_by="Message.created_at")
    lead = relationship("Lead", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
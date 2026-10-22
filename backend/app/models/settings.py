"""
Application settings model - stores encrypted AI provider keys and config.
Phase 4: Secure storage for Gemini, Groq, OpenAI API keys.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class AppSettings(Base):
    """
    Key-value store for application settings.
    AI provider keys are stored encrypted.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Setting identification
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    
    # Security
    is_encrypted = Column(Integer, default=0, nullable=False)  # 0=plain, 1=encrypted
    
    # Metadata
    description = Column(String, nullable=True)
    category = Column(String, default="general", nullable=False)  # "ai_provider", "email", "general"
    
    # Audit
    updated_by = Column(Integer, nullable=True)  # Admin user ID who last updated
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
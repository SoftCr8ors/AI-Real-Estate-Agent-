from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)  # whatsapp, zapier, etc.
    event_type = Column(String, nullable=False, index=True)
    payload = Column(Text, nullable=False)  # JSON string
    processed = Column(Integer, default=0, index=True)  # 0=pending, 1=processed
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
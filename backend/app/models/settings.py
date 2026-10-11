from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    is_encrypted = Column(Integer, default=0)  # 0=plain, 1=encrypted
    description = Column(String, nullable=True)
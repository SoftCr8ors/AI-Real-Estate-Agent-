import enum

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.sql import func

from app.core.database import Base
from app.models._types import enum_values


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(
        SQLEnum(UserRole, name="userrole", create_constraint=False, values_callable=enum_values),
        nullable=False,
        default=UserRole.AGENT,
    )
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PropertyType(str, enum.Enum):
    APARTMENT = "apartment"
    VILLA = "villa"
    TOWNHOUSE = "townhouse"
    PENTHOUSE = "penthouse"
    STUDIO = "studio"


class ListingType(str, enum.Enum):
    BUY = "buy"
    RENT = "rent"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    RENTED = "rented"
    UNAVAILABLE = "unavailable"


class RentPeriod(str, enum.Enum):
    YEARLY = "yearly"
    MONTHLY = "monthly"


# Association table for property amenities (many-to-many)
property_amenities = Table(
    "property_amenities",
    Base.metadata,
    Column("property_id", Integer, ForeignKey("properties.id", ondelete="CASCADE")),
    Column("amenity_id", Integer, ForeignKey("amenities.id", ondelete="CASCADE")),
)


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    property_type = Column(postgresql.ENUM(name="propertytype", create_type=False), nullable=False, index=True)
    listing_type = Column(postgresql.ENUM(name="listingtype", create_type=False), nullable=False, index=True)

    # Price
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, default="AED", nullable=False)
    rent_period = Column(postgresql.ENUM(name="rentperiod", create_type=False), nullable=True)

    # Location
    location = Column(String, nullable=False, index=True)
    community = Column(String, nullable=False, index=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Details
    bedrooms = Column(Integer, nullable=False, index=True)
    bathrooms = Column(Integer, nullable=False)
    size_sqft = Column(Integer, nullable=False)
    furnished = Column(Integer, default=0)  # 0=unfurnished, 1=furnished

    # Description
    description = Column(Text, nullable=False)
    listing_url = Column(String, nullable=True)

    # Status
    availability = Column(
        postgresql.ENUM(name="availabilitystatus", create_type=False),
        default=AvailabilityStatus.AVAILABLE,
        nullable=False,
        index=True,
    )
    is_demo = Column(Integer, default=0)  # 0=real, 1=demo
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # AI embedding
    embedding = Column(Vector(768), nullable=True)

    # Timestamps
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    amenities = relationship("Amenity", secondary=property_amenities)

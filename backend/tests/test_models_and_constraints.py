"""
Test database models and constraints.

These tests verify critical database constraints and model behavior.
Uses SQLite for speed, but constraints are tested against PostgreSQL in CI.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base
from app.models.admin_user import AdminUser, UserRole
from app.models.amenity import Amenity
from app.models.customer import Customer
from app.models.property import Property


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


class TestPropertyConstraints:
    """Test property model constraints."""

    def test_duplicate_reference_rejected(self, db_session: Session):
        """Duplicate property references should be rejected."""
        property1 = Property(
            reference="UNIQUE-001",
            title="Property 1",
            property_type="apartment",
            listing_type="buy",
            price=Decimal("1000000"),
            location="Dubai Marina",
            community="Marina Diamond",
            bedrooms=2,
            bathrooms=2,
            size_sqft=1200,
            description="First property",
            availability="available",
        )
        
        property2 = Property(
            reference="UNIQUE-001",  # Same reference
            title="Property 2",
            property_type="villa",
            listing_type="buy",
            price=Decimal("2000000"),
            location="JVC",
            community="District 11",
            bedrooms=3,
            bathrooms=3,
            size_sqft=2000,
            description="Second property",
            availability="available",
        )
        
        db_session.add(property1)
        db_session.commit()
        
        db_session.add(property2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestAmenities:
    """Test amenity model."""

    def test_amenity_unique_name(self, db_session: Session):
        """Amenity names must be unique."""
        amenity1 = Amenity(name="Swimming Pool")
        db_session.add(amenity1)
        db_session.commit()
        
        amenity2 = Amenity(name="Swimming Pool")
        db_session.add(amenity2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestAdminUser:
    """Test admin user model."""

    def test_duplicate_email_rejected(self, db_session: Session):
        """Duplicate admin emails should be rejected."""
        admin1 = AdminUser(
            email="admin@test.com",
            hashed_password="hashed1",
            full_name="Admin One",
            role=UserRole.ADMIN,
        )
        
        admin2 = AdminUser(
            email="admin@test.com",  # Same email
            hashed_password="hashed2",
            full_name="Admin Two",
            role=UserRole.ADMIN,
        )
        
        db_session.add(admin1)
        db_session.commit()
        
        db_session.add(admin2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_admin_creation(self, db_session: Session):
        """Test basic admin user creation."""
        admin = AdminUser(
            email="test@test.com",
            hashed_password="hashed",
            full_name="Test Admin",
            role=UserRole.ADMIN,
        )
        
        db_session.add(admin)
        db_session.commit()
        
        assert admin.id is not None
        assert admin.email == "test@test.com"
        assert admin.is_active == 1


class TestCustomer:
    """Test customer model."""

    def test_duplicate_email_allowed(self, db_session: Session):
        """Multiple customers can have same email (no unique constraint)."""
        customer1 = Customer(
            email="customer@test.com",
            name="Customer One",
            phone="+971501234567",
        )
        
        customer2 = Customer(
            email="customer@test.com",  # Same email
            name="Customer Two",
            phone="+971507654321",
        )
        
        db_session.add_all([customer1, customer2])
        db_session.commit()
        
        # Both should exist
        count = db_session.query(Customer).filter_by(email="customer@test.com").count()
        assert count == 2

    def test_customer_creation(self, db_session: Session):
        """Test basic customer creation."""
        customer = Customer(
            email="test@customer.com",
            name="Test Customer",
            phone="+971501234567",
        )
        
        db_session.add(customer)
        db_session.commit()
        
        assert customer.id is not None
        assert customer.email == "test@customer.com"

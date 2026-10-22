"""
Tests for booking service (Phase 5).

Tests cover:
- Atomic booking transaction
- Customer validation (name + contact)
- Property and slot re-validation
- Double-booking prevention
- Lead status progression
- Google Calendar sync (mocked)
- Retry mechanism
- Cancellation
"""

import sys
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base
from app.models.appointment import Appointment, AppointmentStatus
from app.models.customer import Customer
from app.models.lead import Lead, LeadStatus
from app.models.property import Property
from app.services.booking import (
    BookingError,
    book_viewing,
    cancel_appointment,
    retry_failed_syncs,
)

# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

LOCAL_TZ = ZoneInfo("Asia/Dubai")


def local_slot(days_ahead: int = 1, hour: int = 14) -> datetime:
    """Return a working-hours slot as a UTC instant for DB storage."""
    day = (datetime.now(UTC) + timedelta(days=days_ahead)).astimezone(LOCAL_TZ).date()
    return datetime.combine(day, time(hour, 0), tzinfo=LOCAL_TZ).astimezone(UTC)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_customer(db_session: Session) -> Customer:
    """Create a sample customer with contact info."""
    customer = Customer(
        name="John Doe",
        email="john@example.com",
        phone="+971501234567",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def sample_lead(db_session: Session, sample_customer: Customer) -> Lead:
    """Create a sample lead."""
    lead = Lead(
        customer_id=sample_customer.id,
        status=LeadStatus.QUALIFIED,
        source="chat",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


@pytest.fixture
def sample_property(db_session: Session) -> Property:
    """Create a sample available property."""
    prop = Property(
        reference="TEST-BOOK-001",
        title="Test Villa",
        property_type="villa",
        listing_type="buy",
        location="Test Location",
        community="Test Community",
        bedrooms=3,
        bathrooms=2,
        size_sqft=2500,
        description="Test property for booking",
        price=1000000,
        availability="available",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)
    return prop


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar service."""
    with patch("app.services.booking.get_calendar_service") as mock_service:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.create_event.return_value = "test_event_id_123"
        mock_service.return_value = mock_instance
        yield mock_instance


class TestBookingValidation:
    """Test booking validation logic."""

    def test_requires_lead_with_customer(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that booking requires a lead with customer info."""
        slot_time = local_slot()

        # Try to book with non-existent lead
        with pytest.raises(BookingError, match="Lead .* not found"):
            book_viewing(
                db=db_session,
                lead_id=99999,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )

    def test_requires_customer_name(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that booking requires customer name."""
        # Create customer without name
        customer = Customer(
            email="test@example.com",
            phone="+971501234567",
        )
        db_session.add(customer)
        db_session.commit()

        lead = Lead(
            customer_id=customer.id,
            status=LeadStatus.QUALIFIED,
        )
        db_session.add(lead)
        db_session.commit()

        slot_time = local_slot()

        with pytest.raises(BookingError, match="Customer name required"):
            book_viewing(
                db=db_session,
                lead_id=lead.id,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )

    def test_requires_customer_contact(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that booking requires phone or email."""
        # Create customer without contact
        customer = Customer(
            name="John Doe",
        )
        db_session.add(customer)
        db_session.commit()

        lead = Lead(
            customer_id=customer.id,
            status=LeadStatus.QUALIFIED,
        )
        db_session.add(lead)
        db_session.commit()

        slot_time = local_slot()

        with pytest.raises(BookingError, match="phone or email required"):
            book_viewing(
                db=db_session,
                lead_id=lead.id,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )

    def test_rejects_unavailable_property(
        self,
        db_session: Session,
        sample_lead: Lead,
        mock_google_calendar,
    ):
        """Test that booking rejects unavailable property."""
        # Create sold property
        prop = Property(
            reference="TEST-BOOK-SOLD",
            title="Sold Villa",
            property_type="villa",
            listing_type="buy",
            location="Test",
            community="Test Community",
            bedrooms=3,
            bathrooms=2,
            size_sqft=2500,
            description="Sold property",
            price=1000000,
            availability="sold",
        )
        db_session.add(prop)
        db_session.commit()

        slot_time = local_slot()

        with pytest.raises(BookingError, match="not available for viewing"):
            book_viewing(
                db=db_session,
                lead_id=sample_lead.id,
                property_id=prop.id,
                scheduled_at=slot_time,
            )


class TestDoubleBookingPrevention:
    """Test that double booking is impossible."""

    def test_prevents_double_booking_same_time(
        self,
        db_session: Session,
        sample_lead: Lead,
        sample_property: Property,
        sample_customer: Customer,
        mock_google_calendar,
    ):
        """Test that two bookings for same time slot fail."""
        slot_time = local_slot()

        # First booking succeeds
        with patch("app.services.slots.get_calendar_service") as mock_slot_service:
            mock_slot_service.return_value.is_available.return_value = False

            appointment1 = book_viewing(
                db=db_session,
                lead_id=sample_lead.id,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )

            assert appointment1.id is not None

        # Create second lead
        lead2 = Lead(
            customer_id=sample_customer.id,
            status=LeadStatus.QUALIFIED,
        )
        db_session.add(lead2)
        db_session.commit()

        # Second booking for same time should fail
        with pytest.raises(BookingError, match="already booked"):
            book_viewing(
                db=db_session,
                lead_id=lead2.id,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )


class TestAtomicTransaction:
    """Test that booking is atomic (survives Google Calendar failure)."""

    def test_appointment_saved_even_if_google_fails(
        self,
        db_session: Session,
        sample_lead: Lead,
        sample_property: Property,
    ):
        """Test that appointment is saved even if Google Calendar sync fails."""
        slot_time = local_slot()

        # Mock Google Calendar to fail
        with patch("app.services.booking.get_calendar_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            mock_instance.create_event.side_effect = Exception("Google API error")
            mock_service.return_value = mock_instance

            with patch("app.services.slots.get_calendar_service") as mock_slot_service:
                mock_slot_service.return_value.is_available.return_value = False

                # Booking should still succeed
                appointment = book_viewing(
                    db=db_session,
                    lead_id=sample_lead.id,
                    property_id=sample_property.id,
                    scheduled_at=slot_time,
                )

                # Appointment saved
                assert appointment.id is not None
                assert appointment.status == AppointmentStatus.SCHEDULED

                # But sync failed
                assert appointment.sync_status == "failed"
                assert "Google API error" in appointment.sync_error


class TestLeadStatusProgression:
    """Test that lead status updates to VIEWING_SCHEDULED."""

    def test_updates_lead_status_to_viewing_scheduled(
        self,
        db_session: Session,
        sample_lead: Lead,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that booking updates lead status."""
        assert sample_lead.status == LeadStatus.QUALIFIED

        slot_time = local_slot()

        with patch("app.services.slots.get_calendar_service") as mock_slot_service:
            mock_slot_service.return_value.is_available.return_value = False

            book_viewing(
                db=db_session,
                lead_id=sample_lead.id,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )

        # Refresh lead from database
        db_session.refresh(sample_lead)

        assert sample_lead.status == LeadStatus.VIEWING_SCHEDULED


class TestGoogleCalendarSync:
    """Test Google Calendar sync functionality."""

    def test_creates_google_calendar_event(
        self,
        db_session: Session,
        sample_lead: Lead,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that booking creates Google Calendar event."""
        slot_time = local_slot()

        with patch("app.services.slots.get_calendar_service") as mock_slot_service:
            mock_slot_service.return_value.is_available.return_value = False

            appointment = book_viewing(
                db=db_session,
                lead_id=sample_lead.id,
                property_id=sample_property.id,
                scheduled_at=slot_time,
            )

        # Verify Google Calendar was called
        mock_google_calendar.create_event.assert_called_once()

        # Verify appointment has Google event ID
        assert appointment.google_event_id == "test_event_id_123"
        assert appointment.sync_status == "synced"

    def test_retry_mechanism_works(
        self,
        db_session: Session,
        sample_lead: Lead,
        sample_property: Property,
    ):
        """Test that failed syncs can be retried."""
        slot_time = local_slot()

        # Create appointment with failed sync
        appointment = Appointment(
            lead_id=sample_lead.id,
            property_id=sample_property.id,
            scheduled_at=slot_time,
            duration_minutes=45,
            status=AppointmentStatus.SCHEDULED,
            sync_status="failed",
            sync_error="Previous error",
            sync_retry_count=0,
        )
        db_session.add(appointment)
        db_session.commit()

        # Mock successful Google Calendar sync
        with patch("app.services.booking.get_calendar_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            mock_instance.create_event.return_value = "retry_event_id"
            mock_service.return_value = mock_instance

            # Retry failed syncs
            stats = retry_failed_syncs(db_session)

            assert stats["attempted"] == 1
            assert stats["succeeded"] == 1
            assert stats["failed"] == 0

        # Verify appointment is now synced
        db_session.refresh(appointment)
        assert appointment.sync_status == "synced"
        assert appointment.google_event_id == "retry_event_id"


class TestCancellation:
    """Test appointment cancellation."""

    def test_cancels_appointment_and_removes_from_google(
        self,
        db_session: Session,
        sample_lead: Lead,
        sample_property: Property,
    ):
        """Test that cancellation removes event from Google Calendar."""
        # Create synced appointment
        appointment = Appointment(
            lead_id=sample_lead.id,
            property_id=sample_property.id,
            scheduled_at=datetime.now(UTC) + timedelta(days=1),
            duration_minutes=45,
            status=AppointmentStatus.SCHEDULED,
            sync_status="synced",
            google_event_id="test_event_123",
        )
        db_session.add(appointment)
        db_session.commit()

        # Mock Google Calendar
        with patch("app.services.booking.get_calendar_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            mock_service.return_value = mock_instance

            # Cancel appointment
            cancelled = cancel_appointment(
                db=db_session,
                appointment_id=appointment.id,
                reason="Customer request",
            )

            # Verify status changed
            assert cancelled.status == AppointmentStatus.CANCELLED

            # Verify Google Calendar delete was called
            mock_instance.delete_event.assert_called_once_with("test_event_123")



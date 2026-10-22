"""
Tests for slot generation service (Phase 5).

Tests cover:
- 45-minute slot grid
- 1-hour advance rule
- Filtering booked appointments
- Filtering blocked times
- Google Calendar busy times (mocked)
- Overlap detection
"""

import sys
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base
from app.models.appointment import Appointment, AppointmentStatus
from app.models.property import Property
from app.models.schedule import BlockedTime
from app.services.slots import (
    SLOT_DURATION_MINUTES,
    WORK_END_HOUR,
    WORK_START_HOUR,
    check_slot_available,
    generate_time_slots,
)

# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

LOCAL_TZ = ZoneInfo("Asia/Dubai")


def local_day(days_ahead: int = 1) -> datetime:
    """Return the same time-of-day N days from now, in the business timezone."""
    return (datetime.now(UTC) + timedelta(days=days_ahead)).astimezone(LOCAL_TZ)


def local_at(day: datetime, hour: int, minute: int = 0) -> datetime:
    """Build a business-timezone datetime on the given day."""
    return datetime.combine(day.date(), time(hour, minute), tzinfo=LOCAL_TZ)


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
def sample_property(db_session: Session) -> Property:
    """Create a sample available property."""
    prop = Property(
        reference="TEST-SLOT-001",
        title="Test Villa",
        property_type="villa",
        listing_type="buy",
        location="Test Location",
        community="Test Community",
        bedrooms=3,
        bathrooms=2,
        size_sqft=2500,
        description="Test property for slot generation",
        price=1000000,
        availability="available",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)
    return prop


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar service to return no busy times."""
    with patch("app.services.slots.get_calendar_service") as mock_service:
        mock_service.return_value.is_available.return_value = False
        yield mock_service


class TestSlotGeneration:
    """Test slot generation logic."""

    def test_generates_45_minute_slots(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that slots are 45 minutes long."""
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        slots = generate_time_slots(
            db=db_session,
            property_id=sample_property.id,
            start_date=tomorrow,
            end_date=tomorrow + timedelta(days=1),
        )

        # Check first available slot
        for slot in slots:
            if slot["available"]:
                start = datetime.fromisoformat(slot["start"])
                end = datetime.fromisoformat(slot["end"])
                duration = (end - start).total_seconds() / 60
                assert duration == SLOT_DURATION_MINUTES
                break

    def test_slots_within_working_hours(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that all slots are between 10:00 and 17:30."""
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        slots = generate_time_slots(
            db=db_session,
            property_id=sample_property.id,
            start_date=tomorrow,
            end_date=tomorrow + timedelta(days=1),
        )

        for slot in slots:
            start = datetime.fromisoformat(slot["start"])
            end = datetime.fromisoformat(slot["end"])

            # Start should be >= 10:00
            assert start.hour >= WORK_START_HOUR

            # End should be <= 17:30
            assert (
                end.hour < WORK_END_HOUR
                or (end.hour == WORK_END_HOUR and end.minute <= 30)
            )

    def test_slots_use_business_timezone(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Working hours must be 10:00-17:30 Dubai time (+04:00)."""
        tomorrow = local_day()
        slots = generate_time_slots(
            db=db_session,
            property_id=sample_property.id,
            start_date=tomorrow,
            end_date=tomorrow + timedelta(days=1),
        )

        first = datetime.fromisoformat(slots[0]["start"])
        assert first.utcoffset() == timedelta(hours=4)
        assert first.hour == WORK_START_HOUR
        assert first.minute == 0

    def test_filters_past_slots(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that slots at least 1 hour in the future are included."""
        now = datetime.now(UTC)
        start = now - timedelta(days=1)  # Start from yesterday
        end = now + timedelta(days=2)

        slots = generate_time_slots(
            db=db_session,
            property_id=sample_property.id,
            start_date=start,
            end_date=end,
        )

        # All returned slots should be at least 1 hour in the future
        min_time = now + timedelta(hours=1)
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            assert slot_start >= min_time

    def test_filters_booked_appointments(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that booked appointment slots are marked unavailable."""
        # Create a booked appointment for tomorrow at 10:00 local time
        tomorrow = local_day()
        booked_time = local_at(tomorrow, 10).astimezone(UTC)

        appointment = Appointment(
            lead_id=1,
            property_id=sample_property.id,
            scheduled_at=booked_time,
            duration_minutes=45,
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(appointment)
        db_session.commit()

        # Generate slots
        slots = generate_time_slots(
            db=db_session,
            property_id=sample_property.id,
            start_date=tomorrow.replace(hour=0, minute=0),
            end_date=tomorrow + timedelta(days=1),
        )

        # Find the 10:00 slot and verify it's unavailable
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            if slot_start.hour == 10 and slot_start.minute == 0 and slot_start.date() == tomorrow.date():
                assert not slot["available"], "Booked slot should be unavailable"
                break
        else:
            pytest.fail("10:00 slot not found in results")

    def test_filters_blocked_times(
        self,
        db_session: Session,
        sample_property: Property,
        mock_google_calendar,
    ):
        """Test that blocked times are marked unavailable."""
        # Block tomorrow 14:00 to 15:00 local time
        tomorrow = local_day()
        blocked_date = tomorrow.date()

        blocked_time = BlockedTime(
            date=blocked_date,
            start_time=datetime.strptime("14:00", "%H:%M").time(),
            end_time=datetime.strptime("15:00", "%H:%M").time(),
            reason="Staff meeting",
        )
        db_session.add(blocked_time)
        db_session.commit()

        # Generate slots
        slots = generate_time_slots(
            db=db_session,
            property_id=sample_property.id,
            start_date=tomorrow.replace(hour=0, minute=0),
            end_date=tomorrow + timedelta(days=1),
        )

        # Find the slots overlapping 14:00-15:00 and verify they're unavailable
        # (45-minute grid: 13:45-14:30 and 14:30-15:15 both overlap)
        found = 0
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            if slot_start.date() == blocked_date and (
                (slot_start.hour == 13 and slot_start.minute == 45)
                or (slot_start.hour == 14 and slot_start.minute == 30)
            ):
                assert not slot["available"], "Blocked slot should be unavailable"
                found += 1
        assert found == 2, "Expected the 13:45 and 14:30 slots in results"

    def test_filters_google_busy_times(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        """Test that Google Calendar busy times are filtered."""
        tomorrow = local_day()
        busy_start = local_at(tomorrow, 11)
        busy_end = busy_start + timedelta(hours=1)

        # Mock Google Calendar to return busy time
        with patch("app.services.slots.get_calendar_service") as mock_service:
            mock_service.return_value.is_available.return_value = True
            mock_service.return_value.get_busy_times.return_value = [
                (busy_start, busy_end)
            ]

            # Generate slots
            slots = generate_time_slots(
                db=db_session,
                property_id=sample_property.id,
                start_date=tomorrow.replace(hour=0, minute=0),
                end_date=tomorrow + timedelta(days=1),
            )

            # Find the slots overlapping 11:00-12:00 and verify they're unavailable
            # (45-minute grid: 10:45-11:30 and 11:30-12:15 both overlap)
            found = 0
            for slot in slots:
                slot_start = datetime.fromisoformat(slot["start"])
                if slot_start.date() == tomorrow.date() and (
                    (slot_start.hour == 10 and slot_start.minute == 45)
                    or (slot_start.hour == 11 and slot_start.minute == 30)
                ):
                    assert not slot["available"], "Google busy slot should be unavailable"
                    found += 1
            assert found == 2, "Expected the 10:45 and 11:30 slots in results"

    def test_property_not_found(
        self,
        db_session: Session,
        mock_google_calendar,
    ):
        """Test error when property doesn't exist."""
        tomorrow = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(ValueError, match="Property 99999 not found"):
            generate_time_slots(
                db=db_session,
                property_id=99999,
                start_date=tomorrow,
                end_date=tomorrow + timedelta(days=1),
            )

    def test_property_not_available(
        self,
        db_session: Session,
        mock_google_calendar,
    ):
        """Test error when property is not available."""
        # Create unavailable property
        prop = Property(
            reference="TEST-SLOT-SOLD",
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

        tomorrow = datetime.now(UTC) + timedelta(days=1)

        with pytest.raises(ValueError, match="not available for viewing"):
            generate_time_slots(
                db=db_session,
                property_id=prop.id,
                start_date=tomorrow,
                end_date=tomorrow + timedelta(days=1),
            )


class TestSlotAvailabilityCheck:
    """Test individual slot availability checking."""

    def test_available_slot_passes(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        """Test that available slot passes validation."""
        tomorrow = local_day()
        slot_time = local_at(tomorrow, 14).astimezone(UTC)

        with patch("app.services.slots.get_calendar_service") as mock_service:
            mock_service.return_value.is_available.return_value = False

            is_available, error = check_slot_available(
                db=db_session,
                property_id=sample_property.id,
                slot_start=slot_time,
            )

            assert is_available
            assert error is None

    def test_rejects_past_slot(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        """Test that past slots are rejected."""
        past_time = datetime.now(UTC) - timedelta(hours=1)

        is_available, error = check_slot_available(
            db=db_session,
            property_id=sample_property.id,
            slot_start=past_time,
        )

        assert not is_available
        assert "at least 1 hour in the future" in error

    def test_rejects_overlapping_appointment(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        """Test that overlapping appointment prevents booking."""
        tomorrow = local_day()
        slot_time = local_at(tomorrow, 14).astimezone(UTC)

        # Create existing appointment
        appointment = Appointment(
            lead_id=1,
            property_id=sample_property.id,
            scheduled_at=slot_time,
            duration_minutes=45,
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(appointment)
        db_session.commit()

        # Try to book same slot
        is_available, error = check_slot_available(
            db=db_session,
            property_id=sample_property.id,
            slot_start=slot_time,
        )

        assert not is_available
        assert "already booked" in error

    def test_rejects_blocked_time(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        """Test that blocked time prevents booking."""
        tomorrow = local_day()
        slot_time = local_at(tomorrow, 14).astimezone(UTC)

        # Create blocked time
        blocked = BlockedTime(
            date=tomorrow.date(),
            start_time=datetime.strptime("14:00", "%H:%M").time(),
            end_time=datetime.strptime("15:00", "%H:%M").time(),
            reason="Test block",
        )
        db_session.add(blocked)
        db_session.commit()

        # Try to book blocked slot
        is_available, error = check_slot_available(
            db=db_session,
            property_id=sample_property.id,
            slot_start=slot_time,
        )

        assert not is_available
        assert "blocked" in error



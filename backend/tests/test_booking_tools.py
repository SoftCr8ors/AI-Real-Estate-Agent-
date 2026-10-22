"""
Integration tests for the Phase 5 agent tools.

Covers the wiring the AI relies on:
- get_available_slots returns bookable slot IDs (real service, not a stub)
- get_available_slots fails closed when the calendar is unreachable
- book_viewing persists customer details and links them to the lead
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agent.tools.booking import book_viewing_tool
from app.agent.tools.slots import get_available_slots_tool
from app.core.database import Base
from app.models.appointment import Appointment
from app.models.conversation import Conversation
from app.models.lead import Lead, LeadStatus
from app.models.property import Property


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_property(db_session: Session) -> Property:
    prop = Property(
        reference="TEST-TOOL-001",
        title="Test Villa",
        property_type="villa",
        listing_type="buy",
        location="Dubai Marina",
        community="Dubai Marina",
        bedrooms=3,
        bathrooms=2,
        size_sqft=2200,
        description="Test property for tool wiring",
        price=1500000,
        availability="available",
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)
    return prop


@pytest.fixture
def lead_without_customer(db_session: Session) -> Lead:
    conversation = Conversation(session_id="test-session-1")
    db_session.add(conversation)
    db_session.commit()

    lead = Lead(
        customer_id=None,
        conversation_id=conversation.id,
        status=LeadStatus.QUALIFIED,
        source="chat",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


class TestGetAvailableSlotsTool:
    def test_returns_bookable_slots_for_inclusive_date_range(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()

        with patch("app.services.slots.get_calendar_service") as mock_service:
            mock_service.return_value.is_available.return_value = False

            result = get_available_slots_tool(
                db_session,
                {
                    "property_id": sample_property.id,
                    "date_from": tomorrow,
                    "date_to": tomorrow,
                },
            )

        assert result.slots, "Expected slots for a single-day date_to range"
        for slot in result.slots:
            assert slot.available is True
            assert slot.slot_id.startswith(f"slot_{sample_property.id}_")
            assert slot.datetime.tzinfo is not None

    def test_fails_closed_when_calendar_is_unreachable(
        self,
        db_session: Session,
        sample_property: Property,
    ):
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()

        with patch(
            "app.agent.tools.slots.generate_time_slots",
            side_effect=RuntimeError("calendar down"),
        ):
            result = get_available_slots_tool(
                db_session,
                {
                    "property_id": sample_property.id,
                    "date_from": tomorrow,
                    "date_to": tomorrow,
                },
            )

        assert result.slots == []


class TestBookViewingTool:
    def test_creates_customer_and_links_lead(
        self,
        db_session: Session,
        sample_property: Property,
        lead_without_customer: Lead,
    ):
        slot_start = datetime.now(UTC) + timedelta(days=1)
        slot_start = slot_start.replace(hour=10, minute=0, second=0, microsecond=0)
        slot_id = f"slot_{sample_property.id}_{slot_start.strftime('%Y%m%d_%H%M')}"

        with patch("app.services.booking.get_calendar_service") as mock_booking_cal:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            mock_instance.create_event.return_value = "event_from_tool"
            mock_booking_cal.return_value = mock_instance

            with patch("app.services.slots.get_calendar_service") as mock_slot_cal:
                mock_slot_cal.return_value.is_available.return_value = False

                result = book_viewing_tool(
                    db_session,
                    {
                        "lead_id": lead_without_customer.id,
                        "property_id": sample_property.id,
                        "slot_id": slot_id,
                        "customer_name": "Jane Buyer",
                        "customer_phone": "+971509998888",
                    },
                )

        assert result.confirmed is True
        assert result.booking_id > 0

        db_session.refresh(lead_without_customer)
        assert lead_without_customer.customer_id is not None
        assert lead_without_customer.customer.name == "Jane Buyer"
        assert lead_without_customer.customer.phone == "+971509998888"

        conversation = db_session.get(Conversation, lead_without_customer.conversation_id)
        assert conversation.customer_name == "Jane Buyer"
        assert conversation.customer_phone == "+971509998888"

        appointment = db_session.get(Appointment, result.booking_id)
        assert appointment is not None
        assert appointment.google_event_id == "event_from_tool"
        assert appointment.sync_status == "synced"

    def test_rejects_slot_belonging_to_another_property(
        self,
        db_session: Session,
        sample_property: Property,
        lead_without_customer: Lead,
    ):
        slot_start = datetime.now(UTC) + timedelta(days=1)
        slot_start = slot_start.replace(hour=10, minute=0, second=0, microsecond=0)
        slot_id = f"slot_{sample_property.id + 1}_{slot_start.strftime('%Y%m%d_%H%M')}"

        with pytest.raises(ValueError, match="does not belong to property"):
            book_viewing_tool(
                db_session,
                {
                    "lead_id": lead_without_customer.id,
                    "property_id": sample_property.id,
                    "slot_id": slot_id,
                    "customer_name": "Jane Buyer",
                    "customer_phone": "+971509998888",
                },
            )

    def test_requires_phone_or_email(
        self,
        db_session: Session,
        sample_property: Property,
        lead_without_customer: Lead,
    ):
        slot_id = f"slot_{sample_property.id}_20300101_1000"

        with pytest.raises(ValueError, match="customer_phone or customer_email"):
            book_viewing_tool(
                db_session,
                {
                    "lead_id": lead_without_customer.id,
                    "property_id": sample_property.id,
                    "slot_id": slot_id,
                    "customer_name": "Jane Buyer",
                },
            )

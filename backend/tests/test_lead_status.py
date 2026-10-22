"""
Tests for lead status management (Phase 4).
Tests automated lead status progression rules and history tracking.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base
from app.models.lead import Lead, LeadStatus
from app.services.lead_status import (
    auto_progress_lead,
    can_transition,
    evaluate_lead_progression,
    get_lead_status_history,
    update_lead_status,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def new_lead(db_session: Session) -> Lead:
    """Create a lead in NEW status."""
    lead = Lead(status=LeadStatus.NEW)
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


class TestCanTransition:
    """Test status transition validation rules."""

    def test_new_to_warm_allowed(self):
        assert can_transition(LeadStatus.NEW, LeadStatus.WARM) is True

    def test_new_to_lost_allowed(self):
        assert can_transition(LeadStatus.NEW, LeadStatus.LOST) is True

    def test_new_to_converted_blocked(self):
        assert can_transition(LeadStatus.NEW, LeadStatus.CONVERTED) is False

    def test_warm_to_hot_allowed(self):
        assert can_transition(LeadStatus.WARM, LeadStatus.HOT) is True

    def test_warm_to_new_blocked_backward(self):
        assert can_transition(LeadStatus.WARM, LeadStatus.NEW) is False

    def test_hot_to_qualified_allowed(self):
        assert can_transition(LeadStatus.HOT, LeadStatus.QUALIFIED) is True

    def test_qualified_to_viewing_scheduled_allowed(self):
        assert can_transition(LeadStatus.QUALIFIED, LeadStatus.VIEWING_SCHEDULED) is True

    def test_viewing_scheduled_to_converted_allowed(self):
        assert can_transition(LeadStatus.VIEWING_SCHEDULED, LeadStatus.CONVERTED) is True

    def test_same_status_allowed(self):
        assert can_transition(LeadStatus.NEW, LeadStatus.NEW) is True
        assert can_transition(LeadStatus.CONVERTED, LeadStatus.CONVERTED) is True

    @pytest.mark.parametrize("target", [s for s in LeadStatus if s != LeadStatus.CONVERTED])
    def test_converted_is_terminal(self, target):
        assert can_transition(LeadStatus.CONVERTED, target) is False

    @pytest.mark.parametrize("target", [s for s in LeadStatus if s != LeadStatus.LOST])
    def test_lost_is_terminal(self, target):
        assert can_transition(LeadStatus.LOST, target) is False


class TestUpdateLeadStatus:
    """Test status updates with history logging."""

    def test_valid_transition_updates_status(self, db_session, new_lead):
        result = update_lead_status(
            db_session, new_lead.id, LeadStatus.WARM, reason="has location"
        )
        assert result is True
        db_session.refresh(new_lead)
        assert new_lead.status == LeadStatus.WARM

    def test_valid_transition_writes_history(self, db_session, new_lead):
        update_lead_status(db_session, new_lead.id, LeadStatus.WARM)
        history = get_lead_status_history(db_session, new_lead.id)
        assert len(history) == 1
        assert history[0].old_status == LeadStatus.NEW
        assert history[0].new_status == LeadStatus.WARM
        assert history[0].automated == 1

    def test_manual_update_marks_automated_zero(self, db_session, new_lead):
        update_lead_status(
            db_session, new_lead.id, LeadStatus.WARM, changed_by=1, automated=False
        )
        history = get_lead_status_history(db_session, new_lead.id)
        assert history[0].automated == 0
        assert history[0].changed_by == 1

    def test_invalid_transition_rejected(self, db_session, new_lead):
        result = update_lead_status(db_session, new_lead.id, LeadStatus.CONVERTED)
        assert result is False
        db_session.refresh(new_lead)
        assert new_lead.status == LeadStatus.NEW

    def test_invalid_transition_writes_no_history(self, db_session, new_lead):
        update_lead_status(db_session, new_lead.id, LeadStatus.CONVERTED)
        history = get_lead_status_history(db_session, new_lead.id)
        assert len(history) == 0

    def test_missing_lead_returns_false(self, db_session):
        result = update_lead_status(db_session, 99999, LeadStatus.WARM)
        assert result is False

    def test_same_status_no_history(self, db_session, new_lead):
        result = update_lead_status(db_session, new_lead.id, LeadStatus.NEW)
        assert result is True
        db_session.refresh(new_lead)
        assert new_lead.status == LeadStatus.NEW
        assert len(get_lead_status_history(db_session, new_lead.id)) == 0


class TestEvaluateLeadProgression:
    """Test business rules for automatic progression."""

    def test_new_to_warm_with_criteria(self, db_session, new_lead):
        state = {"listing_type": "buy", "location": "Dubai Marina", "properties_viewed": 1}
        assert evaluate_lead_progression(db_session, new_lead, state) == LeadStatus.WARM

    def test_new_no_progression_without_listing_type(self, db_session, new_lead):
        state = {"location": "Dubai Marina", "properties_viewed": 1}
        assert evaluate_lead_progression(db_session, new_lead, state) is None

    def test_new_no_progression_without_properties_viewed(self, db_session, new_lead):
        state = {"listing_type": "buy", "budget": 1500000}
        assert evaluate_lead_progression(db_session, new_lead, state) is None

    def test_warm_to_hot_on_viewing_request(self, db_session, new_lead):
        new_lead.status = LeadStatus.WARM
        db_session.commit()
        state = {"requested_viewing": True}
        assert evaluate_lead_progression(db_session, new_lead, state) == LeadStatus.HOT

    def test_warm_to_hot_on_contact_and_timeline(self, db_session, new_lead):
        new_lead.status = LeadStatus.WARM
        db_session.commit()
        state = {"email": "a@b.com", "timeline": "within_1_month"}
        assert evaluate_lead_progression(db_session, new_lead, state) == LeadStatus.HOT

    def test_warm_no_progression_long_timeline(self, db_session, new_lead):
        new_lead.status = LeadStatus.WARM
        db_session.commit()
        state = {"email": "a@b.com", "timeline": "6+_months"}
        assert evaluate_lead_progression(db_session, new_lead, state) is None

    def test_hot_to_qualified_with_full_info(self, db_session, new_lead):
        new_lead.status = LeadStatus.HOT
        db_session.commit()
        state = {
            "name": "John",
            "email": "a@b.com",
            "listing_type": "buy",
            "budget": 1500000,
            "location": "Dubai Marina",
            "selected_property_id": 1,
        }
        assert evaluate_lead_progression(db_session, new_lead, state) == LeadStatus.QUALIFIED

    def test_hot_no_progression_missing_name(self, db_session, new_lead):
        new_lead.status = LeadStatus.HOT
        db_session.commit()
        state = {
            "email": "a@b.com",
            "listing_type": "buy",
            "budget": 1500000,
            "location": "Dubai Marina",
            "selected_property_id": 1,
        }
        assert evaluate_lead_progression(db_session, new_lead, state) is None

    def test_qualified_to_viewing_scheduled(self, db_session, new_lead):
        new_lead.status = LeadStatus.QUALIFIED
        db_session.commit()
        state = {"appointment_booked": True}
        assert (
            evaluate_lead_progression(db_session, new_lead, state)
            == LeadStatus.VIEWING_SCHEDULED
        )

    def test_converted_lead_no_progression(self, db_session, new_lead):
        new_lead.status = LeadStatus.CONVERTED
        db_session.commit()
        state = {"requested_viewing": True, "appointment_booked": True}
        assert evaluate_lead_progression(db_session, new_lead, state) is None


class TestAutoProgressLead:
    """Test automatic progression applied to database."""

    def test_progresses_when_rules_met(self, db_session, new_lead):
        state = {"listing_type": "buy", "location": "Dubai Marina", "properties_viewed": 1}
        result = auto_progress_lead(db_session, new_lead.id, state)
        assert result == LeadStatus.WARM
        db_session.refresh(new_lead)
        assert new_lead.status == LeadStatus.WARM
        assert len(get_lead_status_history(db_session, new_lead.id)) == 1

    def test_no_progression_when_rules_not_met(self, db_session, new_lead):
        result = auto_progress_lead(db_session, new_lead.id, {})
        assert result is None
        db_session.refresh(new_lead)
        assert new_lead.status == LeadStatus.NEW

    def test_missing_lead_returns_none(self, db_session):
        assert auto_progress_lead(db_session, 99999, {}) is None


class TestStatusHistory:
    """Test status history retrieval ordering."""

    def test_history_ordered_chronologically(self, db_session, new_lead):
        update_lead_status(db_session, new_lead.id, LeadStatus.WARM)
        update_lead_status(db_session, new_lead.id, LeadStatus.HOT)
        history = get_lead_status_history(db_session, new_lead.id)
        assert len(history) == 2
        assert history[0].new_status == LeadStatus.WARM
        assert history[1].new_status == LeadStatus.HOT

    def test_empty_history_for_new_lead(self, db_session, new_lead):
        assert get_lead_status_history(db_session, new_lead.id) == []

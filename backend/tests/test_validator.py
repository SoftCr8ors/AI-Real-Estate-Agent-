"""
Tests for reply validation (Phase 4).
Validates prohibited phrases, property references, prices, and regeneration logic.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.validator import (
    build_correction_prompt,
    check_prohibited_phrases,
    get_safe_fallback_response,
    should_regenerate,
    validate_price_mentions,
    validate_property_references,
    validate_response,
)
from app.core.database import Base
from app.models.property import Property


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
def sample_property(db_session: Session):
    """Create a sample property for reference validation."""
    prop = Property(
        reference="VAL-001",
        title="Marina 2BR Apartment",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1400000"),
        location="Dubai Marina",
        community="Marina Diamond",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1200,
        description="Nice 2BR",
        availability="available",
        is_demo=1,
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)
    return prop


class TestProhibitedPhrases:
    """Test prohibited marketing phrase detection."""

    def test_clean_text_passes(self):
        is_valid, error = check_prohibited_phrases(
            "I found two great apartments in Dubai Marina within your budget."
        )
        assert is_valid is True
        assert error is None

    @pytest.mark.parametrize("phrase", [
        "guaranteed return",
        "guaranteed ROI",
        "100% return",
        "no risk",
        "risk-free",
        "guaranteed profit",
        "double your money",
    ])
    def test_prohibited_phrase_blocked(self, phrase):
        text = f"This investment will give you a {phrase} on your money."
        is_valid, error = check_prohibited_phrases(text)
        assert is_valid is False
        assert phrase.lower() in error.lower()

    def test_case_insensitive(self):
        is_valid, _ = check_prohibited_phrases("This is GUARANTEED RETURN for you")
        assert is_valid is False

    def test_error_message_contains_phrase(self):
        is_valid, error = check_prohibited_phrases("no risk investment")
        assert is_valid is False
        assert "no risk" in error


class TestPropertyReferences:
    """Test property ID reference validation."""

    def test_no_references_passes(self, db_session):
        is_valid, error = validate_property_references(
            db_session, "I found some great options in Downtown."
        )
        assert is_valid is True
        assert error is None

    def test_existing_property_reference_passes(self, db_session, sample_property):
        text = f"I recommend Property #{sample_property.id} in Dubai Marina."
        is_valid, error = validate_property_references(db_session, text)
        assert is_valid is True
        assert error is None

    def test_nonexistent_property_blocked(self, db_session):
        is_valid, error = validate_property_references(
            db_session, "Check out Property #99999 for details."
        )
        assert is_valid is False
        assert "99999" in error

    def test_id_prefix_format_blocked(self, db_session):
        is_valid, error = validate_property_references(
            db_session, "The details for ID: 99999 are below."
        )
        assert is_valid is False


class TestPriceMentions:
    """Test price mention validation."""

    def test_no_prices_passes(self, db_session):
        is_valid, _ = validate_price_mentions(db_session, "What is your budget?")
        assert is_valid is True

    def test_budget_discussion_passes(self, db_session):
        is_valid, _ = validate_price_mentions(
            db_session, "My budget is around AED 1.5M for a 2BR."
        )
        assert is_valid is True

    def test_price_with_property_id_passes(self, db_session):
        is_valid, _ = validate_price_mentions(
            db_session, "Property #1 costs AED 1,400,000."
        )
        assert is_valid is True


class TestValidateResponse:
    """Test full validation pipeline."""

    def test_clean_response_passes(self, db_session):
        is_valid, error = validate_response(
            db_session,
            "I found a great 2BR apartment in Dubai Marina for you.",
            conversation_id=1,
        )
        assert is_valid is True
        assert error is None

    def test_prohibited_phrase_fails(self, db_session):
        is_valid, error = validate_response(
            db_session,
            "This property offers guaranteed returns of 20%.",
            conversation_id=1,
        )
        assert is_valid is False
        assert "guaranteed return" in error

    def test_bad_property_reference_fails(self, db_session):
        is_valid, error = validate_response(
            db_session,
            "Let me show you Property #88888.",
            conversation_id=1,
        )
        assert is_valid is False
        assert "88888" in error


class TestRegenerationLogic:
    """Test regeneration decision and correction prompts."""

    def test_regenerate_first_attempt(self):
        assert should_regenerate(0) is True
        assert should_regenerate(1) is True

    def test_no_regenerate_after_two_attempts(self):
        assert should_regenerate(2) is False
        assert should_regenerate(3) is False

    def test_correction_prompt_contains_error(self):
        prompt = build_correction_prompt("Response contains prohibited phrase: 'guaranteed return'")
        assert "guaranteed return" in prompt
        assert "regenerate" in prompt.lower()

    def test_fallback_for_known_error_types(self):
        for error_type in ["prohibited_phrase", "invalid_property", "invalid_price", "general"]:
            response = get_safe_fallback_response(error_type)
            assert len(response) > 20
            assert any(word in response for word in ["apologize", "verify", "help"])

    def test_fallback_for_unknown_error_type(self):
        response = get_safe_fallback_response("something_unexpected")
        assert len(response) > 20

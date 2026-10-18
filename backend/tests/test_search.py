"""
Tests for property search.
These tests require database access.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base
from app.models.amenity import Amenity
from app.models.image import PropertyImage
from app.models.property import Property
from app.services import search


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
def sample_properties(db_session):
    """Create sample properties for testing."""
    # Amenities
    pool = Amenity(name="Swimming Pool")
    gym = Amenity(name="Gym")
    parking = Amenity(name="Parking")
    balcony = Amenity(name="Balcony")

    db_session.add_all([pool, gym, parking, balcony])
    db_session.commit()

    # Property 1: Perfect match - Marina 2BR 1.4M with pool and gym
    prop1 = Property(
        reference="TEST-001",
        title="Marina 2BR Apartment",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1400000"),
        location="Dubai Marina",
        community="Marina Diamond",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1200,
        furnished=0,
        description="Perfect 2BR",
        availability="available",
        is_demo=1,
    )
    prop1.amenities.extend([pool, gym, parking])

    # Property 2: Within budget - Marina 2BR 1.48M
    prop2 = Property(
        reference="TEST-002",
        title="Marina 2BR Premium",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1480000"),
        location="Dubai Marina",
        community="Marina Heights",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1300,
        furnished=0,
        description="Premium 2BR",
        availability="available",
        is_demo=1,
    )
    prop2.amenities.extend([pool, gym])

    # Property 3: Over budget by 3% - Marina 2BR 1.545M
    prop3 = Property(
        reference="TEST-003",
        title="Marina 2BR Luxury",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1545000"),
        location="Dubai Marina",
        community="Marina Gate",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1400,
        furnished=0,
        description="Luxury 2BR",
        availability="available",
        is_demo=1,
    )
    prop3.amenities.extend([pool, gym, balcony])

    # Property 4: Way over budget - Marina 2BR 2M (should not appear)
    prop4 = Property(
        reference="TEST-004",
        title="Marina 2BR Penthouse",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("2000000"),
        location="Dubai Marina",
        community="Marina Promenade",
        bedrooms=2,
        bathrooms=3,
        size_sqft=2000,
        furnished=0,
        description="Penthouse",
        availability="available",
        is_demo=1,
    )

    # Property 5: Sold (should not appear)
    prop5 = Property(
        reference="TEST-005",
        title="Marina 2BR Sold",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1300000"),
        location="Dubai Marina",
        community="Marina Wharf",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1150,
        furnished=0,
        description="Sold property",
        availability="sold",
        is_demo=1,
    )

    # Property 6: JLT 2BR (different location)
    prop6 = Property(
        reference="TEST-006",
        title="JLT 2BR Apartment",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1200000"),
        location="Jumeirah Lake Towers",
        community="Lake Point",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1100,
        furnished=0,
        description="JLT property",
        availability="available",
        is_demo=1,
    )

    # Add images to prop1
    img1 = PropertyImage(image_url="http://example.com/img1.jpg", display_order=1)
    img1.property = prop1  # Use relationship instead of property_id

    db_session.add_all([prop1, prop2, prop3, prop4, prop5, prop6, img1])
    db_session.commit()

    return {
        "prop1": prop1,
        "prop2": prop2,
        "prop3": prop3,
        "prop4": prop4,
        "prop5": prop5,
        "prop6": prop6,
    }


class TestBasicSearch:
    """Test basic search functionality."""

    def test_search_by_location(self, db_session, sample_properties):
        """Test search by location returns only matching location."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
        )

        assert results["total"] > 0

        # All results should be from Dubai Marina
        for item in results["properties"]:
            prop = item["property"]
            assert "Dubai Marina" in prop.location or "Marina" in prop.community

    def test_search_by_price(self, db_session, sample_properties):
        """Test search by max price."""
        results = search.search_properties(
            db=db_session,
            max_price=Decimal("1500000"),
        )

        # Should include properties up to 1.5M + 5% = 1.575M
        for item in results["properties"]:
            prop = item["property"]
            assert prop.price <= Decimal("1575000")

    def test_search_by_bedrooms(self, db_session, sample_properties):
        """Test search by bedrooms."""
        results = search.search_properties(
            db=db_session,
            bedrooms=2,
        )

        # All results should be 1-3 bedrooms (within one)
        for item in results["properties"]:
            prop = item["property"]
            assert prop.bedrooms >= 1
            assert prop.bedrooms <= 3


class TestFiltering:
    """Test filtering logic."""

    def test_only_available_properties(self, db_session, sample_properties):
        """Test sold/rented/unavailable properties are filtered out."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
        )

        # Should not include the sold property (TEST-005)
        references = [item["property"].reference for item in results["properties"]]
        assert "TEST-005" not in references

    def test_budget_with_5_percent_margin(self, db_session, sample_properties):
        """Test budget includes up to 5% over."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
            max_price=Decimal("1500000"),
        )

        # Should include TEST-003 (1.545M = 3% over)
        references = [item["property"].reference for item in results["properties"]]
        assert "TEST-003" in references

        # Should NOT include TEST-004 (2M = way over)
        assert "TEST-004" not in references

    def test_amenity_filtering(self, db_session, sample_properties):
        """Test amenity filtering."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            amenities=["Swimming Pool", "Gym"],
        )

        # All results should have both amenities
        for item in results["properties"]:
            prop = item["property"]
            amenity_names = [a.name for a in prop.amenities]
            assert "Swimming Pool" in amenity_names
            assert "Gym" in amenity_names


class TestOrdering:
    """Test result ordering."""

    def test_within_budget_first(self, db_session, sample_properties):
        """Test within budget properties come before over budget."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
            max_price=Decimal("1500000"),
        )

        properties = results["properties"]
        assert len(properties) > 0

        # Find first over-budget property
        first_over_budget_index = None
        for i, item in enumerate(properties):
            if item["over_budget"]:
                first_over_budget_index = i
                break

        # All properties before first over-budget should be within budget
        if first_over_budget_index is not None:
            for i in range(first_over_budget_index):
                assert not properties[i]["over_budget"]

    def test_higher_score_first(self, db_session, sample_properties):
        """Test higher scores come first."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
            max_price=Decimal("1500000"),
            amenities=["Swimming Pool", "Gym"],
        )

        properties = results["properties"]

        # Within budget group should be sorted by score
        within_budget = [p for p in properties if not p["over_budget"]]

        if len(within_budget) > 1:
            for i in range(len(within_budget) - 1):
                assert within_budget[i]["score"] >= within_budget[i + 1]["score"]


class TestScoring:
    """Test match scoring."""

    def test_properties_have_scores(self, db_session, sample_properties):
        """Test all properties get match scores."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
        )

        for item in results["properties"]:
            assert "score" in item
            assert 0 <= item["score"] <= 100

    def test_over_budget_flag(self, db_session, sample_properties):
        """Test over budget flag is set correctly."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
            max_price=Decimal("1500000"),
        )

        for item in results["properties"]:
            prop = item["property"]
            if prop.price > Decimal("1500000"):
                assert item["over_budget"] is True
            else:
                assert item["over_budget"] is False


class TestSuggestions:
    """Test no-match suggestions."""

    def test_no_match_returns_suggestions(self, db_session, sample_properties):
        """Test suggestions when no properties match."""
        results = search.search_properties(
            db=db_session,
            location="Downtown Dubai",  # No properties in Downtown
            bedrooms=5,  # No 5BR properties
            max_price=Decimal("500000"),  # Too low budget
        )

        assert results["total"] == 0
        assert results["suggestions"] is not None
        assert len(results["suggestions"]) > 0

    def test_suggestions_are_real_data_based(self, db_session, sample_properties):
        """Test suggestions are based on actual database data."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
            bedrooms=2,
            max_price=Decimal("1000000"),  # Too low
        )

        # Should get suggestion about higher budget
        suggestions = results.get("suggestions", [])
        if suggestions:
            # At least one suggestion should mention budget or price
            assert any("budget" in s.lower() or "price" in s.lower() or "aed" in s.lower() for s in suggestions)


class TestPropertyDetails:
    """Test property detail retrieval."""

    def test_get_existing_property(self, db_session, sample_properties):
        """Test getting details of existing property."""
        prop = sample_properties["prop1"]

        details = search.get_property_details(db_session, prop.id)

        assert details is not None
        assert details.id == prop.id
        assert details.reference == prop.reference

    def test_get_nonexistent_property(self, db_session, sample_properties):
        """Test getting details of non-existent property."""
        details = search.get_property_details(db_session, 99999)

        assert details is None


class TestAvailabilityCheck:
    """Test availability checking."""

    def test_check_available_property(self, db_session, sample_properties):
        """Test checking availability of available property."""
        prop = sample_properties["prop1"]

        availability = search.check_property_availability(db_session, prop.id)

        assert availability == "available"

    def test_check_sold_property(self, db_session, sample_properties):
        """Test checking availability of sold property."""
        prop = sample_properties["prop5"]

        availability = search.check_property_availability(db_session, prop.id)

        assert availability == "sold"

    def test_availability_change_reflected(self, db_session, sample_properties):
        """Test that availability changes are reflected immediately."""
        prop = sample_properties["prop1"]

        # Initial check
        assert search.check_property_availability(db_session, prop.id) == "available"

        # Change availability
        prop.availability = "rented"
        db_session.commit()

        # Check again - should reflect change
        assert search.check_property_availability(db_session, prop.id) == "rented"


class TestCompleteScenario:
    """Test complete search scenarios."""

    def test_marina_2br_under_1_5m(self, db_session, sample_properties):
        """Test: 2BR Dubai Marina under AED 1.5M."""
        results = search.search_properties(
            db=db_session,
            listing_type="buy",
            location="Dubai Marina",
            bedrooms=2,
            max_price=Decimal("1500000"),
        )

        # Should have results
        assert results["total"] > 0

        # Should be Marina properties
        assert results["within_budget"] > 0

        # First result should be within budget
        first = results["properties"][0]
        assert not first["over_budget"]
        assert first["property"].location == "Dubai Marina"
        assert first["property"].bedrooms == 2

    def test_primary_image_included(self, db_session, sample_properties):
        """Test primary image is included in results."""
        results = search.search_properties(
            db=db_session,
            location="Dubai Marina",
        )

        # Find the property with image (TEST-001)
        for item in results["properties"]:
            if item["property"].reference == "TEST-001":
                assert item["primary_image"] is not None
                assert "http" in item["primary_image"]

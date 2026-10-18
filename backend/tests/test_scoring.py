"""
Tests for property scoring.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import scoring


class TestLocationScoring:
    """Test location match scoring."""

    def test_exact_match(self):
        """Test exact location match."""
        score = scoring.score_location(
            property_location="Dubai Marina",
            property_community="Marina Diamond",
            search_location="Dubai Marina",
        )
        assert score == 100.0

    def test_community_match(self):
        """Test community match."""
        score = scoring.score_location(
            property_location="Dubai Marina",
            property_community="Marina Diamond",
            search_location="Marina Diamond",
        )
        assert score == 100.0

    def test_partial_match(self):
        """Test partial match."""
        score = scoring.score_location(
            property_location="Dubai Marina",
            property_community="Marina Diamond",
            search_location="Marina",
        )
        assert score == 100.0

    def test_no_match(self):
        """Test no match."""
        score = scoring.score_location(
            property_location="Dubai Marina",
            property_community="Marina Diamond",
            search_location="JVC",
        )
        assert score == 0.0


class TestBudgetScoring:
    """Test budget match scoring."""

    def test_within_budget(self):
        """Test property within budget."""
        score = scoring.score_budget(
            property_price=Decimal("1400000"),
            max_budget=Decimal("1500000"),
        )
        assert score == 100.0

    def test_at_budget(self):
        """Test property at exact budget."""
        score = scoring.score_budget(
            property_price=Decimal("1500000"),
            max_budget=Decimal("1500000"),
        )
        assert score == 100.0

    def test_slightly_over_budget(self):
        """Test property slightly over budget (within 5%)."""
        score = scoring.score_budget(
            property_price=Decimal("1550000"),  # 3.33% over
            max_budget=Decimal("1500000"),
        )
        assert score >= 50.0  # Should get reduced score
        assert score < 100.0

    def test_way_over_budget(self):
        """Test property way over budget (more than 5%)."""
        score = scoring.score_budget(
            property_price=Decimal("1600000"),  # 6.67% over
            max_budget=Decimal("1500000"),
        )
        assert score == 0.0


class TestBedroomScoring:
    """Test bedroom match scoring."""

    def test_exact_match(self):
        """Test exact bedroom match."""
        score = scoring.score_bedrooms(property_bedrooms=2, search_bedrooms=2)
        assert score == 100.0

    def test_within_one(self):
        """Test within one bedroom."""
        score = scoring.score_bedrooms(property_bedrooms=3, search_bedrooms=2)
        assert score == 100.0
        
        score = scoring.score_bedrooms(property_bedrooms=1, search_bedrooms=2)
        assert score == 100.0

    def test_within_two(self):
        """Test within two bedrooms."""
        score = scoring.score_bedrooms(property_bedrooms=4, search_bedrooms=2)
        assert score == 50.0

    def test_way_off(self):
        """Test way off."""
        score = scoring.score_bedrooms(property_bedrooms=5, search_bedrooms=2)
        assert score == 0.0


class TestAmenityScoring:
    """Test amenity match scoring."""

    def test_all_amenities_match(self):
        """Test all amenities present."""
        score = scoring.score_amenities(
            property_amenities=["Swimming Pool", "Gym", "Parking", "Security"],
            search_amenities=["Swimming Pool", "Gym"],
        )
        assert score == 100.0

    def test_partial_amenities_match(self):
        """Test partial amenity match."""
        score = scoring.score_amenities(
            property_amenities=["Swimming Pool", "Parking"],
            search_amenities=["Swimming Pool", "Gym"],
        )
        assert score == 50.0  # 1 out of 2 match

    def test_no_amenities_match(self):
        """Test no amenities match."""
        score = scoring.score_amenities(
            property_amenities=["Parking", "Security"],
            search_amenities=["Gym", "Pool"],
        )
        assert score == 0.0

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        score = scoring.score_amenities(
            property_amenities=["swimming pool", "GYM"],
            search_amenities=["Swimming Pool", "gym"],
        )
        assert score == 100.0

    def test_no_search_amenities(self):
        """Test when no amenities requested."""
        score = scoring.score_amenities(
            property_amenities=["Swimming Pool", "Gym"],
            search_amenities=[],
        )
        assert score == 100.0  # No requirements = full score


class TestPropertyTypeScoring:
    """Test property type scoring."""

    def test_exact_match(self):
        """Test exact type match."""
        score = scoring.score_property_type(
            property_type="apartment",
            search_type="apartment",
        )
        assert score == 100.0

    def test_case_insensitive(self):
        """Test case insensitive."""
        score = scoring.score_property_type(
            property_type="Apartment",
            search_type="APARTMENT",
        )
        assert score == 100.0

    def test_no_match(self):
        """Test no match."""
        score = scoring.score_property_type(
            property_type="apartment",
            search_type="villa",
        )
        assert score == 0.0


class TestBathroomScoring:
    """Test bathroom scoring."""

    def test_exact_match(self):
        """Test exact bathroom match."""
        score = scoring.score_bathrooms(property_bathrooms=2, search_bathrooms=2)
        assert score == 100.0

    def test_more_bathrooms(self):
        """Test more bathrooms than requested."""
        score = scoring.score_bathrooms(property_bathrooms=3, search_bathrooms=2)
        assert score == 100.0

    def test_one_less_bathroom(self):
        """Test one less bathroom."""
        score = scoring.score_bathrooms(property_bathrooms=1, search_bathrooms=2)
        assert score == 50.0

    def test_two_less_bathrooms(self):
        """Test two or more less bathrooms."""
        score = scoring.score_bathrooms(property_bathrooms=1, search_bathrooms=3)
        assert score == 0.0


class TestSizeScoring:
    """Test size scoring."""

    def test_within_range(self):
        """Test size within range."""
        score = scoring.score_size(
            property_size=1200,
            min_size=1000,
            max_size=1500,
        )
        assert score == 100.0

    def test_below_min(self):
        """Test size below minimum."""
        score = scoring.score_size(
            property_size=800,
            min_size=1000,
            max_size=1500,
        )
        assert score == 0.0

    def test_above_max(self):
        """Test size above maximum."""
        score = scoring.score_size(
            property_size=2000,
            min_size=1000,
            max_size=1500,
        )
        assert score == 0.0

    def test_no_constraints(self):
        """Test no size constraints."""
        score = scoring.score_size(
            property_size=1200,
            min_size=None,
            max_size=None,
        )
        assert score == 100.0


class TestFurnishedScoring:
    """Test furnished scoring."""

    def test_match(self):
        """Test furnished status match."""
        score = scoring.score_furnished(
            property_furnished=True,
            search_furnished=True,
        )
        assert score == 100.0

    def test_mismatch(self):
        """Test furnished status mismatch."""
        score = scoring.score_furnished(
            property_furnished=False,
            search_furnished=True,
        )
        assert score == 0.0

    def test_unknown(self):
        """Test unknown furnished status."""
        score = scoring.score_furnished(
            property_furnished=None,
            search_furnished=True,
        )
        assert score == 50.0


class TestOverallScoring:
    """Test overall match score calculation."""

    def test_perfect_match(self):
        """Test perfect match returns 100."""
        property_data = {
            "location": "Dubai Marina",
            "community": "Marina Diamond",
            "price": Decimal("1400000"),
            "bedrooms": 2,
            "bathrooms": 2,
            "size_sqft": 1200,
            "property_type": "apartment",
            "furnished": True,
            "amenities": ["Swimming Pool", "Gym", "Parking"],
        }
        
        search_criteria = {
            "location": "Dubai Marina",
            "max_price": Decimal("1500000"),
            "bedrooms": 2,
            "bathrooms": 2,
            "property_type": "apartment",
            "furnished": True,
            "amenities": ["Swimming Pool", "Gym"],
        }
        
        score = scoring.calculate_match_score(property_data, search_criteria)
        assert score == 100.0

    def test_missing_amenity(self):
        """Test missing amenity lowers score."""
        property_data = {
            "location": "Dubai Marina",
            "community": "Marina Diamond",
            "price": Decimal("1400000"),
            "bedrooms": 2,
            "property_type": "apartment",
            "amenities": ["Swimming Pool"],  # Missing Gym
        }
        
        search_criteria = {
            "location": "Dubai Marina",
            "max_price": Decimal("1500000"),
            "bedrooms": 2,
            "property_type": "apartment",
            "amenities": ["Swimming Pool", "Gym"],  # Wants both
        }
        
        score = scoring.calculate_match_score(property_data, search_criteria)
        assert score < 100.0  # Should be lower due to missing amenity

    def test_no_criteria(self):
        """Test no criteria gives default score."""
        property_data = {
            "location": "Dubai Marina",
            "price": Decimal("1400000"),
        }
        
        search_criteria = {}
        
        score = scoring.calculate_match_score(property_data, search_criteria)
        assert score == 50.0  # Default when no criteria

    def test_weight_renormalization(self):
        """Test weights are renormalized when some criteria missing."""
        property_data = {
            "location": "Dubai Marina",
            "community": "Marina Diamond",
            "bedrooms": 2,
        }
        
        # Only location and bedrooms criteria (no budget, amenities, etc.)
        search_criteria = {
            "location": "Dubai Marina",
            "bedrooms": 2,
        }
        
        score = scoring.calculate_match_score(property_data, search_criteria)
        assert score == 100.0  # Perfect match on provided criteria
"""
Tests for input normalization.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import normalize


class TestBudgetNormalization:
    """Test budget string conversion."""

    def test_millions(self):
        """Test million format."""
        assert normalize.normalize_budget("1.5M") == Decimal("1500000")
        assert normalize.normalize_budget("1M") == Decimal("1000000")
        assert normalize.normalize_budget("2.5M") == Decimal("2500000")

    def test_thousands(self):
        """Test thousand format."""
        assert normalize.normalize_budget("120k") == Decimal("120000")
        assert normalize.normalize_budget("500K") == Decimal("500000")

    def test_plain_numbers(self):
        """Test plain numbers."""
        assert normalize.normalize_budget("1500000") == Decimal("1500000")
        assert normalize.normalize_budget("150000") == Decimal("150000")

    def test_with_commas(self):
        """Test numbers with commas."""
        assert normalize.normalize_budget("1,500,000") == Decimal("1500000")
        assert normalize.normalize_budget("150,000") == Decimal("150000")

    def test_with_currency(self):
        """Test with AED currency."""
        assert normalize.normalize_budget("AED 1.5M") == Decimal("1500000")
        assert normalize.normalize_budget("AED 1,500,000") == Decimal("1500000")

    def test_invalid(self):
        """Test invalid input."""
        assert normalize.normalize_budget("abc") is None
        assert normalize.normalize_budget("") is None
        assert normalize.normalize_budget(None) is None


class TestLocationNormalization:
    """Test location name normalization."""

    def test_marina_aliases(self):
        """Test Dubai Marina aliases."""
        assert normalize.normalize_location("marina") == "Dubai Marina"
        assert normalize.normalize_location("the marina") == "Dubai Marina"
        assert normalize.normalize_location("Dubai Marina") == "Dubai Marina"

    def test_jvc_aliases(self):
        """Test JVC aliases."""
        assert normalize.normalize_location("jvc") == "Jumeirah Village Circle"
        assert normalize.normalize_location("jumeirah village") == "Jumeirah Village Circle"

    def test_jlt_aliases(self):
        """Test JLT aliases."""
        assert normalize.normalize_location("jlt") == "Jumeirah Lake Towers"
        assert normalize.normalize_location("jumeirah lakes") == "Jumeirah Lake Towers"

    def test_downtown_aliases(self):
        """Test Downtown aliases."""
        assert normalize.normalize_location("downtown") == "Downtown Dubai"
        assert normalize.normalize_location("down town") == "Downtown Dubai"

    def test_unknown_location(self):
        """Test unknown location returns title case."""
        assert normalize.normalize_location("some area") == "Some Area"

    def test_none_input(self):
        """Test None input."""
        assert normalize.normalize_location(None) is None


class TestBedroomsNormalization:
    """Test bedroom count normalization."""

    def test_studio(self):
        """Test studio conversion to 0."""
        assert normalize.normalize_bedrooms("studio") == 0
        assert normalize.normalize_bedrooms("Studio") == 0
        assert normalize.normalize_bedrooms("STUDIO") == 0

    def test_numbers(self):
        """Test number extraction."""
        assert normalize.normalize_bedrooms("2") == 2
        assert normalize.normalize_bedrooms("3") == 3

    def test_with_text(self):
        """Test number extraction from text."""
        assert normalize.normalize_bedrooms("2BR") == 2
        assert normalize.normalize_bedrooms("3 bedrooms") == 3

    def test_none_input(self):
        """Test None input."""
        assert normalize.normalize_bedrooms(None) is None


class TestListingTypeNormalization:
    """Test listing type normalization."""

    def test_buy_variations(self):
        """Test buy variations."""
        assert normalize.normalize_listing_type("buy") == "buy"
        assert normalize.normalize_listing_type("purchase") == "buy"
        assert normalize.normalize_listing_type("buying") == "buy"
        assert normalize.normalize_listing_type("sale") == "buy"

    def test_rent_variations(self):
        """Test rent variations."""
        assert normalize.normalize_listing_type("rent") == "rent"
        assert normalize.normalize_listing_type("rental") == "rent"
        assert normalize.normalize_listing_type("renting") == "rent"
        assert normalize.normalize_listing_type("lease") == "rent"

    def test_none_input(self):
        """Test None input."""
        assert normalize.normalize_listing_type(None) is None


class TestRentPeriodNormalization:
    """Test rent period conversion."""

    def test_monthly_to_yearly(self):
        """Test monthly to yearly conversion."""
        assert normalize.normalize_rent_period(Decimal("10000"), "monthly") == Decimal("120000")
        assert normalize.normalize_rent_period(Decimal("8000"), "month") == Decimal("96000")

    def test_already_yearly(self):
        """Test already yearly."""
        assert normalize.normalize_rent_period(Decimal("120000"), "yearly") == Decimal("120000")
        assert normalize.normalize_rent_period(Decimal("100000"), "year") == Decimal("100000")

    def test_no_period_specified(self):
        """Test auto-detection."""
        # Small amount (< 500k) assumed monthly
        assert normalize.normalize_rent_period(Decimal("10000"), None) == Decimal("120000")
        
        # Large amount (>= 500k) assumed yearly
        assert normalize.normalize_rent_period(Decimal("600000"), None) == Decimal("600000")


class TestFurnishedNormalization:
    """Test furnished status normalization."""

    def test_furnished_true(self):
        """Test furnished true variations."""
        assert normalize.normalize_furnished("furnished") is True
        assert normalize.normalize_furnished("yes") is True
        assert normalize.normalize_furnished("true") is True
        assert normalize.normalize_furnished("1") is True

    def test_furnished_false(self):
        """Test furnished false variations."""
        assert normalize.normalize_furnished("unfurnished") is False
        assert normalize.normalize_furnished("no") is False
        assert normalize.normalize_furnished("false") is False
        assert normalize.normalize_furnished("0") is False

    def test_none_input(self):
        """Test None input."""
        assert normalize.normalize_furnished(None) is None


class TestPropertyTypeNormalization:
    """Test property type normalization."""

    def test_lowercase_conversion(self):
        """Test lowercase conversion."""
        assert normalize.normalize_property_type("APARTMENT") == "apartment"
        assert normalize.normalize_property_type("Villa") == "villa"
        assert normalize.normalize_property_type("Townhouse") == "townhouse"

    def test_none_input(self):
        """Test None input."""
        assert normalize.normalize_property_type(None) is None


class TestAmenityNormalization:
    """Test amenity normalization."""

    def test_title_case(self):
        """Test title case conversion."""
        result = normalize.normalize_amenities(["swimming pool", "GYM", "parking"])
        assert result == ["Swimming Pool", "Gym", "Parking"]

    def test_empty_list(self):
        """Test empty list."""
        assert normalize.normalize_amenities([]) == []
        assert normalize.normalize_amenities(None) == []

    def test_with_whitespace(self):
        """Test trimming whitespace."""
        result = normalize.normalize_amenities(["  pool  ", " gym "])
        assert result == ["Pool", "Gym"]
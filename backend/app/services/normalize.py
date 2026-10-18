"""
Input normalization service.
Cleans and standardizes user input for property search.
"""

import re
from decimal import Decimal

# ============================================================================
# LOCATION NICKNAMES (Can be extended by admin)
# ============================================================================

LOCATION_ALIASES = {
    # Dubai Marina variations
    "marina": "Dubai Marina",
    "the marina": "Dubai Marina",
    "dubai marina": "Dubai Marina",

    # JVC variations
    "jvc": "Jumeirah Village Circle",
    "jumeirah village": "Jumeirah Village Circle",

    # JLT variations
    "jlt": "Jumeirah Lake Towers",
    "jumeirah lakes": "Jumeirah Lake Towers",

    # JBR variations
    "jbr": "Jumeirah Beach Residence",
    "jumeirah beach": "Jumeirah Beach Residence",

    # Downtown variations
    "downtown": "Downtown Dubai",
    "down town": "Downtown Dubai",

    # Business Bay variations
    "business bay": "Business Bay",
    "bb": "Business Bay",

    # Palm Jumeirah variations
    "palm": "Palm Jumeirah",
    "the palm": "Palm Jumeirah",
    "palm jumeirah": "Palm Jumeirah",

    # Dubai Hills variations
    "dubai hills": "Dubai Hills Estate",
    "hills": "Dubai Hills Estate",

    # Arabian Ranches variations
    "arabian ranches": "Arabian Ranches",
    "ranches": "Arabian Ranches",
}


# ============================================================================
# BUDGET NORMALIZATION
# ============================================================================

def normalize_budget(budget_str: str) -> Decimal | None:
    """
    Convert budget string to Decimal amount.

    Examples:
        "1.5M" → 1500000
        "1,500,000" → 1500000
        "120k" → 120000
        "150000" → 150000

    Args:
        budget_str: Budget string from user

    Returns:
        Decimal amount or None if invalid
    """
    if not budget_str:
        return None

    # Remove currency symbols and spaces
    cleaned = budget_str.strip().upper()
    cleaned = cleaned.replace("AED", "").replace("$", "").replace(",", "").strip()

    # Handle M (millions)
    if "M" in cleaned:
        try:
            number = float(cleaned.replace("M", ""))
            return Decimal(str(number * 1_000_000))
        except (ValueError, TypeError):
            return None

    # Handle K (thousands)
    if "K" in cleaned:
        try:
            number = float(cleaned.replace("K", ""))
            return Decimal(str(number * 1_000))
        except (ValueError, TypeError):
            return None

    # Plain number
    try:
        return Decimal(cleaned)
    except (ValueError, TypeError, Exception):
        return None


# ============================================================================
# RENT PERIOD NORMALIZATION
# ============================================================================

def normalize_rent_period(price: Decimal, period: str | None = None) -> Decimal:
    """
    Convert monthly rent to yearly.

    Args:
        price: Rent price
        period: "monthly" or "yearly" or None

    Returns:
        Yearly rent amount
    """
    if not period:
        # Default assumption: if rent < 500k, it's probably monthly
        if price < 500_000:
            return price * 12
        return price

    period_lower = period.lower().strip()

    if period_lower in ["monthly", "month", "per month", "/month"]:
        return price * 12

    # Already yearly
    return price


# ============================================================================
# LOCATION NORMALIZATION
# ============================================================================

def normalize_location(location_str: str | None) -> str | None:
    """
    Normalize location name using aliases.

    Examples:
        "marina" → "Dubai Marina"
        "jvc" → "Jumeirah Village Circle"
        "downtown" → "Downtown Dubai"

    Args:
        location_str: Location string from user

    Returns:
        Normalized location name or original if no match
    """
    if not location_str:
        return None

    location_lower = location_str.lower().strip()

    # Check aliases
    if location_lower in LOCATION_ALIASES:
        return LOCATION_ALIASES[location_lower]

    # Return title case if no alias found
    return location_str.title()


# ============================================================================
# PROPERTY TYPE NORMALIZATION
# ============================================================================

def normalize_property_type(property_type_str: str | None) -> str | None:
    """
    Normalize property type.

    Examples:
        "APARTMENT" → "apartment"
        "Villa" → "villa"

    Args:
        property_type_str: Property type from user

    Returns:
        Lowercase property type
    """
    if not property_type_str:
        return None

    return property_type_str.lower().strip()


# ============================================================================
# BEDROOMS NORMALIZATION
# ============================================================================

def normalize_bedrooms(bedroom_str: str | None) -> int | None:
    """
    Normalize bedroom count.

    Examples:
        "studio" → 0
        "Studio" → 0
        "2" → 2
        "2BR" → 2

    Args:
        bedroom_str: Bedroom string from user

    Returns:
        Bedroom count (0 for studio)
    """
    if not bedroom_str:
        return None

    bedroom_lower = str(bedroom_str).lower().strip()

    # Handle studio
    if "studio" in bedroom_lower:
        return 0

    # Extract number
    numbers = re.findall(r'\d+', bedroom_lower)
    if numbers:
        return int(numbers[0])

    return None


# ============================================================================
# LISTING TYPE NORMALIZATION
# ============================================================================

def normalize_listing_type(listing_type_str: str | None) -> str | None:
    """
    Normalize listing type to "buy" or "rent".

    Examples:
        "purchase" → "buy"
        "rental" → "rent"
        "buying" → "buy"

    Args:
        listing_type_str: Listing type from user

    Returns:
        "buy" or "rent" or None
    """
    if not listing_type_str:
        return None

    listing_lower = listing_type_str.lower().strip()

    # Buy variations
    if any(word in listing_lower for word in ["buy", "purchase", "sale", "buying"]):
        return "buy"

    # Rent variations
    if any(word in listing_lower for word in ["rent", "rental", "lease", "renting"]):
        return "rent"

    return None


# ============================================================================
# FURNISHED NORMALIZATION
# ============================================================================

def normalize_furnished(furnished_str: str | None) -> bool | None:
    """
    Normalize furnished status.

    Args:
        furnished_str: Furnished string from user

    Returns:
        True if furnished, False if unfurnished, None if not specified
    """
    if not furnished_str:
        return None

    furnished_lower = str(furnished_str).lower().strip()

    # Check unfurnished FIRST (more specific)
    if any(word in furnished_lower for word in ["unfurnished", "no", "false", "0"]):
        return False

    # Then check furnished
    if any(word in furnished_lower for word in ["furnished", "yes", "true", "1"]):
        return True

    return None


# ============================================================================
# AMENITY NORMALIZATION
# ============================================================================

def normalize_amenities(amenities_list: list | None) -> list[str]:
    """
    Normalize amenity names.

    Args:
        amenities_list: List of amenity names

    Returns:
        List of normalized amenity names
    """
    if not amenities_list:
        return []

    normalized = []
    for amenity in amenities_list:
        if amenity:
            # Title case and strip
            normalized.append(amenity.strip().title())

    return normalized
